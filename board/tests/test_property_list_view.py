import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from home.models import SearchHistory, Property
from django.utils import timezone
import json

User = get_user_model()

@pytest.fixture
def create_user():
    """Fixture to create a test user."""
    return User.objects.create_user(username='testuser', password='testpassword')

@pytest.fixture
def create_search_history(create_user):
    """Fixture to create a test search history."""
    user = create_user
    return SearchHistory.objects.create(
        user=user,
        query_text="서울시 강남구 아파트",
        parsed_keywords={"address": "서울시 강남구", "building_type": "아파트"},
        result_count=0,
        redis_key="dummy_redis_key",
        search_date=timezone.now()
    )

@pytest.fixture
def create_properties():
    """Fixture to create multiple test properties."""
    properties = []
    for i in range(35): # Create more than paginate_by items
        properties.append(Property.objects.create(
            address=f"서울시 강남구 역삼동 {i+1}번지",
            owner_type="개인",
            transaction_type="매매",
            price=500000000 + i * 1000000,
            building_type="아파트",
            area_pyeong=30.0 + i * 0.1,
            floor_info=f"{i+1}/20층",
            direction="남향",
            tags=["신축", "역세권"],
            updated_date=timezone.now(),
            crawled_date=timezone.now(),
            detail_url=f"http://example.com/detail/{i+1}",
            image_urls=["http://example.com/img/prop.jpg"],
            description=f"테스트 매물 {i+1}"
        ))
    return properties

@pytest.mark.django_db
@pytest.mark.views
@pytest.mark.board_app
class TestPropertyListView:

    def test_property_list_view_requires_login(self, client):
        """Test that PropertyListView redirects unauthenticated users to login."""
        url = reverse('board:results')
        response = client.get(url)
        assert response.status_code == 302 # Redirect to login
        assert 'login' in response.url

    def test_property_list_view_with_valid_search_history(self, client, create_user, create_search_history, create_properties):
        """Test that PropertyListView renders correctly with a valid search history ID."""
        client.login(username='testuser', password='testpassword')
        url = reverse('board:results') + f"?search_history_id={create_search_history.id}"
        response = client.get(url)

        assert response.status_code == 200
        assert 'board/results.html' in [t.name for t in response.templates]
        assert 'properties' in response.context
        assert response.context['properties'].count() == 30 # Default paginate_by
        assert response.context['search_history'].id == create_search_history.id

    def test_property_list_view_pagination(self, client, create_user, create_search_history, create_properties):
        """Test that PropertyListView handles pagination correctly."""
        client.login(username='testuser', password='testpassword')
        
        # Test first page
        url_page1 = reverse('board:results') + f"?page=1&search_history_id={create_search_history.id}"
        response_page1 = client.get(url_page1)
        assert response_page1.status_code == 200
        assert response_page1.context['properties'].count() == 30
        assert response_page1.context['page_obj'].number == 1

        # Test second page
        url_page2 = reverse('board:results') + f"?page=2&search_history_id={create_search_history.id}"
        response_page2 = client.get(url_page2)
        assert response_page2.status_code == 200
        assert response_page2.context['properties'].count() == 5 # 35 total - 30 on first page = 5
        assert response_page2.context['page_obj'].number == 2

    def test_property_list_view_with_invalid_search_history_id(self, client, create_user, create_properties):
        """Test that PropertyListView returns 404 for an invalid search history ID."""
        client.login(username='testuser', password='testpassword')
        url = reverse('board:results') + "?search_history_id=99999" # Non-existent ID
        response = client.get(url)
        assert response.status_code == 404 # Should return 404 if search history not found

    def test_property_list_view_with_missing_search_history_id(self, client, create_user, create_properties):
        """Test that PropertyListView returns an empty queryset if search_history_id is missing."""
        client.login(username='testuser', password='testpassword')
        url = reverse('board:results') # Missing search_history_id
        response = client.get(url)
        assert response.status_code == 200 # Still 200, but properties context should be empty
        assert response.context['properties'].count() == 0
        assert response.context['search_history'] is None
