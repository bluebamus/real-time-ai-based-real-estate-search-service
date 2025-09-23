from django.urls import path
from board.views.base_views import PropertyListView
from board.views.api_views import ResultsAPIView, RecommendationAPIView, PropertyDetailAPIView, AuthTestAPIView

app_name = 'board'

urlpatterns = [
    # 메인 뷰 - Redis 키를 URL 파라미터로 받음
    path('results/<str:redis_key>/', PropertyListView.as_view(), name='property_list'),

    # API 뷰들
    path('api/auth-test/', AuthTestAPIView.as_view(), name='api_auth_test'),
    path('api/results/<str:redis_key>/', ResultsAPIView.as_view(), name='api_results'),
    path('api/recommendations/', RecommendationAPIView.as_view(), name='api_recommendations'),
    path('api/results/<str:redis_key>/<int:property_index>/', PropertyDetailAPIView.as_view(), name='api_property_detail'),
]
