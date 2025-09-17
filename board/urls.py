"""
URL configuration for board app
"""
from django.urls import path
from . import views

app_name = 'board'

urlpatterns = [
    # Placeholder URLs - to be implemented later
    path('', views.index, name='index'),
]