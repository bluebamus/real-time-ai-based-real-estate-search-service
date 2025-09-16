from django.urls import path
from .views import (
    HomeView,
    SearchResultsView,
    TrendingView,
    SearchAPIView,
    AutocompleteAPIView,
    SearchHistoryAPIView,
    AdvancedSearchView,
    SaveSearchView,
    SearchAnalyticsView,
)

app_name = 'home'

urlpatterns = [
    # Main views
    path('', HomeView.as_view(), name='home'),
    path('search/', SearchResultsView.as_view(), name='search_results'),
    path('trending/', TrendingView.as_view(), name='trending'),

    # Advanced search and analytics
    path('advanced/', AdvancedSearchView.as_view(), name='advanced_search'),
    path('saved/', SaveSearchView.as_view(), name='saved_searches'),
    path('analytics/', SearchAnalyticsView.as_view(), name='search_analytics'),

    # API endpoints
    path('api/search/', SearchAPIView.as_view(), name='api_search'),
    path('api/autocomplete/', AutocompleteAPIView.as_view(), name='api_autocomplete'),
    path('api/history/', SearchHistoryAPIView.as_view(), name='api_history'),
]