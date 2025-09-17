from django.urls import path
from .views import PropertyListView # Import the new view

app_name = 'board'

urlpatterns = [
    path('results/', PropertyListView.as_view(), name='results'), # New URL for property list
    # Remove the old placeholder index view
    # path('', views.index, name='index'),
]
