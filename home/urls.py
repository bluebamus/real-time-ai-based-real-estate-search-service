from django.urls import path
from home.views import HomeView, SearchAPIView # Import specific views directly

app_name = 'home'

urlpatterns = [
    # Main views
    path('', HomeView.as_view(), name='home'),

    # API endpoints
    path('api/search/', SearchAPIView.as_view(), name='api_search'),
]
