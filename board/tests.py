import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from home.models import SearchHistory, Property, RecommendationCache
from django.utils import timezone
import json
from unittest.mock import patch, MagicMock

User = get_user_model()


@pytest.fixture
def client():
    """테스트 클라이언트"""
    return Client()


@pytest.fixture
def test_user(db):
    """테스트용 사용자"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(client, test_user, db):
    """인증된 클라이언트"""
    client.login(username='testuser', password='testpass123')
    return client


@pytest.fixture
def search_history(test_user, db):
    """테스트용 검색 기록"""
    return SearchHistory.objects.create(
        user=test_user,
        query_text="서울시 강남구 아파트",
        parsed_keywords={"address": "서울시 강남구", "building_type": "아파트"},
        result_count=5,
        redis_key="test_redis_key",
        search_date=timezone.now()
    )


@pytest.fixture
def test_properties(db):
    """테스트용 매물 데이터"""
    properties = []
    for i in range(35):  # 페이지네이션 테스트를 위해 30개 이상 생성
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


class TestBoardViews:
    """Board 앱 뷰 테스트"""

    def test_property_list_view_requires_authentication(self, client, db):
        """PropertyListView가 인증을 요구하는지 테스트"""
        url = reverse('board:property_list', kwargs={'redis_key': 'test_key'})
        response = client.get(url)

        # 인증되지 않은 사용자는 로그인 페이지로 리디렉션
        assert response.status_code == 302
        assert 'login' in response.url

    def test_property_list_view_authenticated_user(self, authenticated_client, search_history, db):
        """인증된 사용자의 PropertyListView 접근 테스트"""
        with patch('board.services.redis_data_service.redis_data_service.check_redis_key_valid') as mock_check:
            with patch('board.services.redis_data_service.redis_data_service.get_combined_results') as mock_results:
                mock_check.return_value = True
                mock_results.return_value = {
                    'recommendations': [],
                    'search_results': [],
                    'total_recommendations': 0,
                    'total_search_results': 0
                }

                url = reverse('board:property_list', kwargs={'redis_key': search_history.redis_key})
                response = authenticated_client.get(url)

                assert response.status_code == 200
                assert 'board/property_list.html' in [t.name for t in response.templates]

    def test_property_list_view_invalid_redis_key(self, authenticated_client, db):
        """잘못된 Redis 키로 PropertyListView 접근 테스트"""
        with patch('board.services.redis_data_service.redis_data_service.check_redis_key_valid') as mock_check:
            mock_check.return_value = False

            url = reverse('board:property_list', kwargs={'redis_key': 'invalid_key'})
            response = authenticated_client.get(url)

            assert response.status_code == 404

    def test_results_view_requires_authentication(self, client, db):
        """ResultsView가 인증을 요구하는지 테스트"""
        url = reverse('board:results')
        response = client.get(url)

        # 인증되지 않은 사용자는 로그인 페이지로 리디렉션
        assert response.status_code == 302
        assert 'login' in response.url

    def test_results_view_with_search_history(self, authenticated_client, search_history, test_properties, db):
        """검색 기록 ID가 있는 ResultsView 테스트"""
        url = reverse('board:results') + f"?search_history_id={search_history.id}"
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert 'board/results.html' in [t.name for t in response.templates]
        assert 'properties' in response.context
        assert 'search_history' in response.context

    def test_results_view_without_search_history(self, authenticated_client, db):
        """검색 기록 ID가 없는 ResultsView 테스트"""
        url = reverse('board:results')
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert response.context['search_history'] is None
        assert response.context['properties'].count() == 0


class TestBoardAPI:
    """Board 앱 API 테스트"""

    def test_api_auth_test_authenticated(self, authenticated_client, test_user, db):
        """인증 테스트 API - 인증된 사용자"""
        url = reverse('board:api_auth_test')
        response = authenticated_client.get(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert data['is_authenticated'] is True
        assert data['username'] == test_user.username
        assert data['user_id'] == test_user.id

    def test_api_auth_test_unauthenticated(self, client, db):
        """인증 테스트 API - 인증되지 않은 사용자"""
        url = reverse('board:api_auth_test')
        response = client.get(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        assert response.status_code == 401

    @patch('board.services.redis_data_service.redis_data_service.check_redis_key_valid')
    @patch('board.services.redis_data_service.redis_data_service.get_properties_from_search_results')
    def test_api_results_success(self, mock_get_properties, mock_check_key, authenticated_client, db):
        """결과 API 성공 테스트"""
        mock_check_key.return_value = True
        mock_get_properties.return_value = [
            {
                "owner_name": "테스트 매물",
                "address": "서울시 강남구",
                "transaction_type": "매매",
                "price": 500000000,
                "building_type": "아파트"
            }
        ]

        url = reverse('board:api_results', kwargs={'redis_key': 'test_key'})
        response = authenticated_client.get(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        assert response.status_code == 200
        data = response.json()
        assert 'results' in data
        assert 'total_count' in data

    @patch('board.services.redis_data_service.redis_data_service.check_redis_key_valid')
    def test_api_results_invalid_key(self, mock_check_key, authenticated_client, db):
        """결과 API 잘못된 키 테스트"""
        mock_check_key.return_value = False

        url = reverse('board:api_results', kwargs={'redis_key': 'invalid_key'})
        response = authenticated_client.get(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        assert response.status_code == 404

    @patch('board.services.redis_data_service.redis_data_service.get_recommendation_properties')
    def test_api_recommendations(self, mock_get_recommendations, authenticated_client, db):
        """추천 API 테스트"""
        mock_get_recommendations.return_value = [
            {
                "owner_name": "추천 매물",
                "address": "서울시 서초구",
                "transaction_type": "매매",
                "price": 700000000,
                "building_type": "아파트",
                "is_recommendation": True,
                "score": 0.95
            }
        ]

        url = reverse('board:api_recommendations')
        response = authenticated_client.get(
            url,
            {'limit': 10, 'type': 'user'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        assert response.status_code == 200
        data = response.json()
        assert 'recommendations' in data
        assert 'total_count' in data

    @patch('board.services.redis_data_service.redis_data_service.check_redis_key_valid')
    @patch('board.services.redis_data_service.redis_data_service.get_properties_from_search_results')
    def test_api_property_detail(self, mock_get_properties, mock_check_key, authenticated_client, db):
        """매물 상세 API 테스트"""
        mock_check_key.return_value = True
        mock_get_properties.return_value = [
            {
                "owner_name": "상세 매물",
                "address": "서울시 강남구",
                "transaction_type": "매매",
                "price": 600000000,
                "building_type": "아파트"
            }
        ]

        url = reverse('board:api_property_detail', kwargs={
            'redis_key': 'test_key',
            'property_index': 0
        })
        response = authenticated_client.get(
            url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        assert response.status_code == 200
        data = response.json()
        assert data['owner_name'] == '상세 매물'


class TestBoardURLs:
    """Board 앱 URL 패턴 테스트"""

    def test_url_patterns_exist(self):
        """모든 board 앱 URL 패턴이 존재하는지 테스트"""
        # URL 이름들이 정상적으로 resolve 되는지 확인
        assert reverse('board:property_list', kwargs={'redis_key': 'test'})
        assert reverse('board:results')
        assert reverse('board:api_auth_test')
        assert reverse('board:api_results', kwargs={'redis_key': 'test'})
        assert reverse('board:api_recommendations')
        assert reverse('board:api_property_detail', kwargs={
            'redis_key': 'test',
            'property_index': 0
        })

    def test_url_patterns_require_authentication(self, client, db):
        """인증이 필요한 URL 패턴들 테스트"""
        protected_urls = [
            reverse('board:property_list', kwargs={'redis_key': 'test'}),
            reverse('board:results'),
            reverse('board:api_auth_test'),
            reverse('board:api_results', kwargs={'redis_key': 'test'}),
            reverse('board:api_recommendations'),
        ]

        for url in protected_urls:
            response = client.get(url)
            # 302 (redirect to login) 또는 401/403 (API endpoints)
            assert response.status_code in [302, 401, 403]


class TestBoardIntegration:
    """Board 앱 통합 테스트"""

    def test_full_board_workflow(self, authenticated_client, test_user, db):
        """전체 Board 워크플로우 테스트"""
        # 1. 검색 기록 생성
        search_history = SearchHistory.objects.create(
            user=test_user,
            query_text="서울시 강남구 아파트",
            parsed_keywords={"address": "서울시 강남구", "building_type": "아파트"},
            result_count=5,
            redis_key="workflow_test_key",
            search_date=timezone.now()
        )

        with patch('board.services.redis_data_service.redis_data_service.check_redis_key_valid') as mock_check:
            with patch('board.services.redis_data_service.redis_data_service.get_combined_results') as mock_results:
                mock_check.return_value = True
                mock_results.return_value = {
                    'recommendations': [],
                    'search_results': [],
                    'total_recommendations': 0,
                    'total_search_results': 0
                }

                # 2. Property List 페이지 접근
                list_url = reverse('board:property_list', kwargs={'redis_key': search_history.redis_key})
                response = authenticated_client.get(list_url)
                assert response.status_code == 200

                # 3. Results 페이지 접근
                results_url = reverse('board:results') + f"?search_history_id={search_history.id}"
                response = authenticated_client.get(results_url)
                assert response.status_code == 200

                # 4. 인증 테스트 API 호출
                auth_url = reverse('board:api_auth_test')
                response = authenticated_client.get(
                    auth_url,
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest'
                )
                assert response.status_code == 200
                assert response.json()['is_authenticated'] is True

    def test_board_pagination(self, authenticated_client, test_properties, db):
        """Board 페이지네이션 테스트"""
        # Results 페이지에서 페이지네이션 테스트
        url = reverse('board:results')

        # 첫 번째 페이지
        response = authenticated_client.get(url + "?page=1")
        assert response.status_code == 200

        # 두 번째 페이지 (매물이 30개 이상 있을 때)
        if len(test_properties) > 30:
            response = authenticated_client.get(url + "?page=2")
            assert response.status_code == 200
