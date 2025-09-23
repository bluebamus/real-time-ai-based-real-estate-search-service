from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static # Keep this import
from django.contrib.staticfiles.urls import staticfiles_urlpatterns # New import
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('user/', include('user.urls')),
    path('home/', include('home.urls')),
    path('board/', include('board.urls')),

    # API 문서 URLs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    path('', lambda request: redirect('home:home') if request.user.is_authenticated else redirect('user:login')),
]

# Explicitly serve static files in development
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns() # This will serve files from STATICFILES_DIRS
    # You can also add this if you want to serve media files explicitly
    # urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)