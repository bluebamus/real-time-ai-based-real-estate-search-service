import json
import logging
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.mixins import LoginRequiredMixin

from home.models import SearchHistory, Property # Import models from home app

logger = logging.getLogger(__name__)

class PropertyListView(LoginRequiredMixin, ListView):
    """
    부동산 매물 목록을 표시하는 뷰
    검색 결과 및 추천 매물을 페이지네이션과 함께 제공
    """
    model = Property
    template_name = 'board/results.html'
    context_object_name = 'properties';
    paginate_by = 30 # As per Development-Plan-Specification.md (30 items per page for search results)

    def get_queryset(self):
        """
        URL에서 search_history_id를 받아 해당 검색 기록에 연결된 매물들을 반환
        """
        search_history_id = self.request.GET.get('search_history_id')
        if not search_history_id:
            logger.warning("PropertyListView accessed without search_history_id.")
            return Property.objects.none() # Return empty queryset if no ID

        try:
            search_history = get_object_or_404(SearchHistory, id=search_history_id, user=self.request.user)
            # For now, let's return the latest properties to make the view functional.
            # A proper linking mechanism (e.g., storing Property IDs in SearchHistory or using Redis keys) will be implemented later.
            return Property.objects.order_by('-crawled_date')[:100] # Return some recent properties

        except Exception as e:
            logger.error(f"Error retrieving properties for search_history_id {search_history_id}: {e}")
            return Property.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_history_id = self.request.GET.get('search_history_id')
        if search_history_id:
            context['search_history'] = get_object_or_404(SearchHistory, id=search_history_id, user=self.request.user)
        else:
            context['search_history'] = None
        return context