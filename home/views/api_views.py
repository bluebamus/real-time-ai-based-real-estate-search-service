import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView
from ..models import SearchHistory, PopularSearch
from ..utils.chatgpt_client import get_chatgpt_client


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class SearchAPIView(View):
    """
    자연어 검색 쿼리를 처리하는 API 뷰
    """

    def post(self, request):
        try:
            # JSON 데이터 파싱
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
                query = data.get('query', '').strip()
            else:
                query = request.POST.get('query', '').strip()

            if not query:
                return JsonResponse({
                    'success': False,
                    'error': '검색어를 입력해주세요.'
                }, status=400)

            # 입력 검증
            if len(query) > 500:
                return JsonResponse({
                    'success': False,
                    'error': '검색어가 너무 깁니다. (최대 500자)'
                }, status=400)

            # ChatGPT API를 통한 쿼리 처리
            chatgpt_client = get_chatgpt_client()

            # 사용자 컨텍스트 구성
            user_context = {
                'recent_searches': list(SearchHistory.objects.filter(
                    user=request.user
                ).order_by('-created_at')[:5].values_list('query', flat=True))
            }

            processed_result = chatgpt_client.process_real_estate_query(query, user_context)

            # 검색 기록 저장
            SearchHistory.objects.create(
                user=request.user,
                query=query,
                results_count=processed_result.get('results_count', 0)
            )

            # 인기 검색어 업데이트
            PopularSearch.increment_search_count(query)

            return JsonResponse({
                'success': True,
                'data': processed_result
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': '잘못된 JSON 형식입니다.'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': '서버 오류가 발생했습니다.'
            }, status=500)



@method_decorator(login_required, name='dispatch')
class AutocompleteAPIView(View):
    """
    검색 자동완성 API 뷰
    """

    def get(self, request):
        query = request.GET.get('q', '').strip()

        if len(query) < 2:
            return JsonResponse({
                'success': True,
                'suggestions': []
            })

        # 인기 검색어 중에서 매칭되는 것들 찾기
        popular_matches = PopularSearch.objects.filter(
            keyword__icontains=query
        ).order_by('-search_count')[:5]

        # 사용자의 최근 검색어 중에서 매칭되는 것들 찾기
        user_matches = SearchHistory.objects.filter(
            user=request.user,
            query__icontains=query
        ).order_by('-created_at')[:3]

        suggestions = []

        # 인기 검색어 추가
        for search in popular_matches:
            suggestions.append({
                'text': search.keyword,
                'type': 'popular',
                'count': search.search_count
            })

        # 사용자 검색 기록 추가 (중복 제거)
        existing_texts = {s['text'] for s in suggestions}
        for search in user_matches:
            if search.query not in existing_texts:
                suggestions.append({
                    'text': search.query,
                    'type': 'history',
                    'date': search.created_at.isoformat()
                })

        return JsonResponse({
            'success': True,
            'suggestions': suggestions[:8]  # 최대 8개
        })


@method_decorator(login_required, name='dispatch')
class SearchHistoryAPIView(ListView):
    """
    사용자 검색 기록 API 뷰
    """
    model = SearchHistory
    paginate_by = 20

    def get_queryset(self):
        return SearchHistory.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page_size = int(request.GET.get('page_size', self.paginate_by))
        page = int(request.GET.get('page', 1))

        # 페이지네이션
        start = (page - 1) * page_size
        end = start + page_size
        histories = list(queryset[start:end])

        # JSON 응답 생성
        data = []
        for history in histories:
            data.append({
                'id': history.id,
                'query': history.query,
                'results_count': history.results_count,
                'created_at': history.created_at.isoformat(),
            })

        return JsonResponse({
            'success': True,
            'data': data,
            'total_count': queryset.count(),
            'page': page,
            'has_next': len(histories) == page_size
        })