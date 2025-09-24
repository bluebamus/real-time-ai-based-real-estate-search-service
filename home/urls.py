from django.urls import path
from home.views.base_views import HomeView
from home.views.api_views import SearchAPIView, AuthTestAPIView

app_name = 'home'

urlpatterns = [
    # Main views
    path('', HomeView.as_view(), name='home'),

    # API endpoints
    path('api/search/', SearchAPIView.as_view(), name='api_search'),
    path('api/auth-test/', AuthTestAPIView.as_view(), name='api_auth_test'),
]