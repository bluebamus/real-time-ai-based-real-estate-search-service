from django.shortcuts import render, redirect
from django.views.generic import TemplateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Count, Q
from ..models import SearchHistory, PopularSearch
from datetime import datetime, timedelta


class AdvancedSearchView(LoginRequiredMixin, TemplateView):
    """
    고급 검색 기능을 제공하는 뷰
    """
    template_name = 'home/advanced_search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 검색 필터 옵션들
        context.update({
            'property_types': [
                ('apartment', '아파트'),
                ('officetel', '오피스텔'),
                ('villa', '빌라'),
                ('house', '단독주택'),
            ],
            'transaction_types': [
                ('sale', '매매'),
                ('lease', '전세'),
                ('rent', '월세'),
            ],
            'locations': [
                ('gangnam', '강남구'),
                ('seocho', '서초구'),
                ('songpa', '송파구'),
                ('gangdong', '강동구'),
            ],
        })
        return context

    def post(self, request):
        """고급 검색 처리"""
        filters = {
            'property_type': request.POST.get('property_type'),
            'transaction_type': request.POST.get('transaction_type'),
            'location': request.POST.get('location'),
            'min_price': request.POST.get('min_price'),
            'max_price': request.POST.get('max_price'),
            'min_size': request.POST.get('min_size'),
            'max_size': request.POST.get('max_size'),
        }

        # 필터를 쿼리 스트링으로 변환
        query_params = []
        for key, value in filters.items():
            if value:
                query_params.append(f"{key}={value}")

        query_string = "&".join(query_params)

        # 검색 결과 페이지로 리다이렉트
        return redirect(f'/search/?advanced=true&{query_string}')


class SaveSearchView(LoginRequiredMixin, TemplateView):
    """
    검색 조건을 저장하고 관리하는 뷰
    """
    template_name = 'home/saved_searches.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 사용자의 모든 검색 기록 (최근 50개)
        user_searches = SearchHistory.objects.filter(
            user=self.request.user
        ).order_by('-created_at')[:50]

        # 검색어별 그룹화 및 통계
        search_stats = {}
        for search in user_searches:
            key = search.query
            if key in search_stats:
                search_stats[key]['count'] += 1
                if search.created_at > search_stats[key]['last_searched']:
                    search_stats[key]['last_searched'] = search.created_at
            else:
                search_stats[key] = {
                    'query': search.query,
                    'count': 1,
                    'last_searched': search.created_at,
                    'avg_results': search.results_count
                }

        # 검색 빈도순으로 정렬
        frequent_searches = sorted(
            search_stats.values(),
            key=lambda x: x['count'],
            reverse=True
        )[:20]

        context.update({
            'recent_searches': user_searches[:20],
            'frequent_searches': frequent_searches,
        })
        return context

    def post(self, request):
        """검색 기록 삭제 처리"""
        action = request.POST.get('action')

        if action == 'delete_all':
            SearchHistory.objects.filter(user=request.user).delete()
            messages.success(request, '모든 검색 기록이 삭제되었습니다.')

        elif action == 'delete_query':
            query = request.POST.get('query')
            if query:
                SearchHistory.objects.filter(
                    user=request.user,
                    query=query
                ).delete()
                messages.success(request, f'"{query}" 검색 기록이 삭제되었습니다.')

        return redirect('saved_searches')


class SearchAnalyticsView(LoginRequiredMixin, TemplateView):
    """
    사용자의 검색 분석 및 통계를 보여주는 뷰
    """
    template_name = 'home/search_analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        # 기본 통계
        total_searches = SearchHistory.objects.filter(user=user).count()
        unique_queries = SearchHistory.objects.filter(user=user).values('query').distinct().count()

        # 날짜별 검색 통계 (최근 30일)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        daily_searches = SearchHistory.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago
        ).extra({
            'date': "DATE(created_at)"
        }).values('date').annotate(count=Count('id')).order_by('date')

        # 시간대별 검색 패턴
        hourly_searches = SearchHistory.objects.filter(user=user).extra({
            'hour': "EXTRACT(hour FROM created_at)"
        }).values('hour').annotate(count=Count('id')).order_by('hour')

        # 가장 많이 검색한 키워드 top 10
        top_keywords = SearchHistory.objects.filter(user=user).values('query').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        # 검색 결과가 많았던 쿼리 top 10
        high_result_queries = SearchHistory.objects.filter(
            user=user,
            results_count__gt=0
        ).order_by('-results_count')[:10]

        context.update({
            'total_searches': total_searches,
            'unique_queries': unique_queries,
            'daily_searches': list(daily_searches),
            'hourly_searches': list(hourly_searches),
            'top_keywords': list(top_keywords),
            'high_result_queries': high_result_queries,
        })
        return context