from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from ..models import SearchHistory, PopularSearch


class HomeView(LoginRequiredMixin, TemplateView):
    """
    메인 홈페이지 뷰 - 검색 인터페이스를 제공
    """
    template_name = 'home/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 사용자의 최근 검색 기록 5개
        recent_searches = SearchHistory.objects.filter(
            user=self.request.user
        ).order_by('-created_at')[:5]

        # 인기 검색어 10개
        popular_searches = PopularSearch.objects.order_by('-search_count')[:10]

        context.update({
            'recent_searches': recent_searches,
            'popular_searches': popular_searches,
        })
        return context


class SearchResultsView(LoginRequiredMixin, ListView):
    """
    검색 결과를 표시하는 뷰
    """
    template_name = 'home/search_results.html'
    context_object_name = 'search_results'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        if not query:
            return []

        # 실제 구현에서는 ChatGPT API를 통해 검색 결과를 가져옴
        # 현재는 더미 데이터 반환
        return self._get_dummy_results(query)

    def _get_dummy_results(self, query):
        """더미 검색 결과 생성 (개발용)"""
        return [
            {
                'id': i,
                'title': f'{query} 관련 부동산 {i}',
                'price': f'{i * 100000}만원',
                'location': f'서울시 강남구 {i}동',
                'type': '아파트',
                'size': f'{20 + i}평',
            }
            for i in range(1, 21)
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')

        # 검색 기록 저장
        if query and self.request.user.is_authenticated:
            SearchHistory.objects.create(
                user=self.request.user,
                query=query,
                results_count=len(context['search_results'])
            )

            # 인기 검색어 업데이트
            PopularSearch.increment_search_count(query)

        context.update({
            'query': query,
            'results_count': len(context['search_results']) if context['search_results'] else 0,
        })
        return context


class TrendingView(LoginRequiredMixin, TemplateView):
    """
    인기 검색어와 트렌딩 지역을 보여주는 뷰
    """
    template_name = 'home/trending.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 인기 검색어 20개
        popular_searches = PopularSearch.objects.order_by('-search_count')[:20]

        # 최근 검색어 트렌드 (최근 7일간)
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        recent_trends = PopularSearch.objects.filter(
            last_searched_at__gte=week_ago
        ).order_by('-search_count')[:10]

        context.update({
            'popular_searches': popular_searches,
            'recent_trends': recent_trends,
        })
        return context