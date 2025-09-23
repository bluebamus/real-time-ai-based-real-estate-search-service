import json
import logging
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, TemplateView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.mixins import LoginRequiredMixin

from home.models import SearchHistory, Property # Import models from home app
from board.services.redis_data_service import redis_data_service
from utils.recommendations import recommendation_engine

logger = logging.getLogger(__name__)

class PropertyListView(LoginRequiredMixin, TemplateView):
    """
    부동산 매물 목록을 표시하는 뷰
    Redis에서 검색 결과 및 추천 매물을 조회하여 Flex 카드 레이아웃으로 표시
    """
    template_name = 'board/results.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # URL에서 Redis 키 추출
        redis_key = kwargs.get('redis_key')

        if not redis_key:
            logger.warning("PropertyListView accessed without redis_key.")
            context['error'] = "검색 결과를 찾을 수 없습니다."
            context['recommendations'] = []
            context['search_results'] = []
            return context

        try:
            # Redis 키 유효성 확인
            if not redis_data_service.check_redis_key_valid(redis_key):
                logger.warning(f"Invalid or expired Redis key: {redis_key}")
                context['error'] = "검색 결과가 만료되었습니다. 다시 검색해주세요."
                context['recommendations'] = []
                context['search_results'] = []
                return context

            # 추천 매물과 검색 결과를 결합하여 조회
            combined_results = redis_data_service.get_combined_results(
                redis_key=redis_key,
                user_id=self.request.user.id,
                recommendation_limit=10,  # 추천 매물 10개
                search_limit=30          # 검색 결과 30개
            )

            context['recommendations'] = combined_results['recommendations']
            context['search_results'] = combined_results['search_results']
            context['total_recommendations'] = combined_results['total_recommendations']
            context['total_search_results'] = combined_results['total_search_results']
            context['redis_key'] = redis_key

            logger.info(f"PropertyListView - 추천: {len(combined_results['recommendations'])}개, "
                       f"검색: {len(combined_results['search_results'])}개")

        except Exception as e:
            logger.error(f"Error retrieving data for redis_key {redis_key}: {e}")
            context['error'] = "데이터 조회 중 오류가 발생했습니다."
            context['recommendations'] = []
            context['search_results'] = []

        return context