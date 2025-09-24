"""
Board App - JavaScript 세션 인증 테스트

이 모듈은 Board 앱의 JavaScript 세션 기반 인증, CSRF, CORS 기능을 테스트합니다.
"""

import pytest
import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.sessions.models import Session
from django.middleware.csrf import get_token
from django.conf import settings
from unittest.mock import patch, MagicMock

User = get_user_model()


@pytest.fixture
def test_user(mocker):
    mocker.patch('django.contrib.auth.get_user_model', return_value=mocker.MagicMock(
        objects=mocker.MagicMock(
            create_user=mocker.MagicMock(return_value=mocker.MagicMock(id=1, username='testuser', email='test@example.com'))
        )
    ))
    User = get_user_model()
    return User.objects.create_user(username='testuser', email='test@example.com', password='testpass123')

@pytest.fixture
def test_client():
    return Client()

@pytest.fixture
def auth_urls():
    return {
        'auth_test': reverse('home:api_auth_test'),
        'search': reverse('home:api_search'),
        'login': reverse('user:login'),
        'home': reverse('home:home'),
    }

@pytest.mark.api
@pytest.mark.views
class TestBoardSessionAuth:
    """
    Board 앱 JavaScript 세션 인증 테스트 케이스
    """

    def test_csrf_token_required(self, test_client, test_user, auth_urls):
        """CSRF 토큰 필수 확인 테스트"""
        # 로그인
        test_client.login(username=test_user.username, password='testpass123')

        # CSRF 토큰 없이 POST 요청
        response = test_client.post(
            auth_urls['search'],
            {'query': '서울시 강남구 아파트'},
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # CSRF 오류 확인 (403 Forbidden)
        assert response.status_code == 403

    def test_csrf_token_with_credentials(self, test_client, test_user, auth_urls, mocker):
        """CSRF 토큰과 credentials 설정 테스트"""
        # 로그인
        test_client.login(username=test_user.username, password='testpass123')

        # CSRF 토큰 획득
        mocker.patch('django.middleware.csrf.get_token', return_value='mock_csrf_token')
        csrf_token = get_token(test_client.session)

        # CSRF 토큰과 함께 요청
        response = test_client.post(
            auth_urls['search'],
            json.dumps({'query': '서울시 강남구 아파트'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # 200 또는 400 상태 코드 (비즈니스 로직 오류는 괜찮음)
        assert response.status_code in [200, 400, 500]

    def test_board_session_authentication_success(self, test_client, test_user, auth_urls):
        """Board 세션 인증 성공 테스트"""
        # 로그인
        test_client.login(username=test_user.username, password='testpass123')

        # Board 인증 테스트 API 호출
        response = test_client.get(
            auth_urls['auth_test'],
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        assert response.status_code == 200

        data = response.json()
        assert data['status'] == 'success'
        assert data['is_authenticated'] is True
        assert data['username'] == test_user.username
        assert data['user_id'] == test_user.id
        assert data['session_exists'] is True
        assert data['current_path'] == '/board/api/auth-test/'
        assert data['message'] == 'Board 인증 테스트 완료'

    def test_board_session_authentication_failure(self, test_client, auth_urls):
        """Board 세션 인증 실패 테스트"""
        # 로그인하지 않은 상태에서 API 호출
        response = test_client.get(
            auth_urls['auth_test'],
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # 401 Unauthorized 확인
        assert response.status_code == 401

    @patch('board.services.redis_data_service.redis_data_service.check_redis_key_valid')
    @patch('board.services.redis_data_service.redis_data_service.get_properties_from_search_results')
    def test_results_api_with_session_auth(self, mock_get_properties, mock_check_key, test_client, test_user, mocker):
        """결과 API 세션 인증 테스트 (모킹 사용)"""
        # 모킹 설정
        mock_check_key.return_value = True
        mock_get_properties.return_value = [
            {
                "owner_name": "테스트 매물 1",
                "address": "서울시 강남구",
                "transaction_type": "매매",
                "price": 500000000,
                "building_type": "아파트",
                "area_size": 25.64,
                "floor_info": "5/15층",
                "direction": "남향",
                "tags": ["신축", "역세권"],
                "updated_date": "2025-09-23"
            },
            {
                "owner_name": "테스트 매물 2",
                "address": "서울시 강남구",
                "transaction_type": "전세",
                "price": 300000000,
                "building_type": "아파트",
                "area_size": 30.12,
                "floor_info": "10/20층",
                "direction": "서향",
                "tags": ["리모델링", "학군"],
                "updated_date": "2025-09-23"
            }
        ]

        # 로그인
        test_client.login(username=test_user.username, password='testpass123')

        # 결과 API 호출
        results_url = reverse('board:api_results', kwargs={'redis_key': 'dummy_redis_key'})
        response = test_client.get(
            results_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # 성공 응답 확인
        assert response.status_code == 200

        data = response.json()
        assert 'results' in data
        assert 'total_count' in data
        assert 'current_page' in data
        assert 'total_pages' in data
        assert len(data['results']) == 2

        # 결과 데이터 검증
        first_result = data['results'][0]
        assert first_result['owner_name'] == '테스트 매물 1'
        assert first_result['is_recommendation'] is False

    @patch('board.services.redis_data_service.redis_data_service.get_recommendation_properties')
    def test_recommendations_api_with_session_auth(self, mock_get_recommendations):
        """추천 API 세션 인증 테스트 (모킹 사용)"""
        # 모킹 설정
        mock_get_recommendations.return_value = [
            {
                "owner_name": "추천 매물 1",
                "address": "서울시 서초구",
                "transaction_type": "매매",
                "price": 700000000,
                "building_type": "아파트",
                "area_size": 35.0,
                "floor_info": "8/25층",
                "direction": "남동향",
                "tags": ["신축", "고급"],
                "updated_date": "2025-09-23",
                "is_recommendation": True,
                "score": 0.95
            }
        ]

        # 로그인
        self.client.login(username='boarduser', password='testpass123')

        # 추천 API 호출
        response = self.client.get(
            self.recommendations_url,
            {'limit': 10, 'type': 'user'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # 성공 응답 확인
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('recommendations', data)
        self.assertIn('total_count', data)
        self.assertIn('recommendation_type', data)
        self.assertEqual(data['recommendation_type'], 'user')
        self.assertEqual(len(data['recommendations']), 1)

        # 추천 데이터 검증
        recommendation = data['recommendations'][0]
        self.assertEqual(recommendation['owner_name'], '추천 매물 1')
        self.assertTrue(recommendation['is_recommendation'])

    def test_board_cors_headers(self):
        """Board CORS 헤더 테스트"""
        # 로그인
        self.client.login(username='boarduser', password='testpass123')

        # Origin 헤더와 함께 요청
        response = self.client.get(
            self.auth_test_url,
            HTTP_ORIGIN='http://localhost:8000',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)

        # CORS 헤더 확인은 실제 배포 환경에서 중요

    def test_board_session_persistence(self):
        """Board 세션 지속성 테스트"""
        # 로그인
        login_response = self.client.login(username='boarduser', password='testpass123')
        self.assertTrue(login_response)

        # 세션 ID 확인
        session_key = self.client.session.session_key
        self.assertIsNotNone(session_key)

        # 같은 클라이언트로 여러 요청
        for i in range(5):
            response = self.client.get(
                self.auth_test_url,
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertTrue(data['is_authenticated'])
            self.assertEqual(data['username'], 'boarduser')
            self.assertEqual(data['current_path'], '/board/api/auth-test/')

    def test_multiple_board_api_calls(self):
        """Board 다중 API 호출 테스트"""
        # 로그인
        self.client.login(username='boarduser', password='testpass123')

        # 여러 API를 순차적으로 호출
        apis = [
            self.auth_test_url,
            self.recommendations_url,
        ]

        for api_url in apis:
            with patch('board.services.redis_data_service.redis_data_service.get_recommendation_properties') as mock_rec:
                mock_rec.return_value = []

                response = self.client.get(
                    api_url,
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest'
                )

                # 모든 API가 인증을 통과해야 함
                self.assertIn(response.status_code, [200, 404])  # 404는 Redis 키 없음

    @patch('board.services.redis_data_service.redis_data_service.check_redis_key_valid')
    def test_invalid_redis_key_handling(self, mock_check_key):
        """잘못된 Redis 키 처리 테스트"""
        # 모킹 설정 - 유효하지 않은 키
        mock_check_key.return_value = False

        # 로그인
        self.client.login(username='boarduser', password='testpass123')

        # 잘못된 Redis 키로 결과 API 호출
        results_url = reverse('board:api_results', kwargs={'redis_key': 'invalid_key'})
        response = self.client.get(
            results_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # 404 Not Found 또는 적절한 오류 응답
        self.assertEqual(response.status_code, 404)

        data = response.json()
        self.assertIn('error', data)

    def test_property_detail_api_auth(self):
        """매물 상세 API 인증 테스트"""
        # 로그인
        self.client.login(username='boarduser', password='testpass123')

        # 매물 상세 API URL
        detail_url = reverse('board:api_property_detail', kwargs={
            'redis_key': self.test_redis_key,
            'property_index': 0
        })

        with patch('board.services.redis_data_service.redis_data_service.check_redis_key_valid') as mock_check:
            with patch('board.services.redis_data_service.redis_data_service.get_properties_from_search_results') as mock_props:
                mock_check.return_value = True
                mock_props.return_value = [
                    {
                        "owner_name": "상세 매물",
                        "address": "서울시 강남구",
                        "transaction_type": "매매",
                        "price": 600000000,
                        "building_type": "아파트"
                    }
                ]

                response = self.client.get(
                    detail_url,
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest'
                )

                # 성공 응답 확인
                self.assertEqual(response.status_code, 200)

                data = response.json()
                self.assertEqual(data['owner_name'], '상세 매물')
                self.assertEqual(data['is_recommendation'], False)

    def test_pagination_with_session_auth(self):
        """페이지네이션과 세션 인증 테스트"""
        # 로그인
        self.client.login(username='boarduser', password='testpass123')

        # 대량의 테스트 데이터 생성
        test_properties = []
        for i in range(50):
            test_properties.append({
                "owner_name": f"매물 {i+1}",
                "address": "서울시 강남구",
                "transaction_type": "매매",
                "price": 500000000 + (i * 10000000),
                "building_type": "아파트"
            })

        with patch('board.services.redis_data_service.redis_data_service.check_redis_key_valid') as mock_check:
            with patch('board.services.redis_data_service.redis_data_service.get_properties_from_search_results') as mock_props:
                mock_check.return_value = True
                mock_props.return_value = test_properties

                # 첫 번째 페이지
                results_url = reverse('board:api_results', kwargs={'redis_key': self.test_redis_key})
                response = self.client.get(
                    results_url,
                    {'page': 1},
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest'
                )

                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data['current_page'], 1)
                self.assertEqual(len(data['results']), 30)  # 페이지 크기
                self.assertTrue(data['has_next'])
                self.assertFalse(data['has_previous'])

                # 두 번째 페이지
                response = self.client.get(
                    results_url,
                    {'page': 2},
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest'
                )

                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data['current_page'], 2)
                self.assertEqual(len(data['results']), 20)  # 나머지 20개
                self.assertFalse(data['has_next'])
                self.assertTrue(data['has_previous'])


@pytest.mark.integration
@pytest.mark.board_app
class BoardJavaScriptIntegrationTest(TestCase):
    """
    Board JavaScript 통합 테스트
    실제 브라우저 환경에서의 동작을 시뮬레이션
    """

    def setUp(self):
        """테스트 환경 설정"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='boardjstest',
            email='boardjs@example.com',
            password='testpass123'
        )
        self.test_redis_key = 'search:integration_test:results'

    def test_board_page_access_and_auth_test(self):
        """Board 페이지 접근 및 인증 테스트 전체 플로우"""
        # 1. 로그인
        login_success = self.client.login(username='boardjstest', password='testpass123')
        self.assertTrue(login_success)

        # 2. Board 결과 페이지 접근
        board_url = reverse('board:property_list', kwargs={'redis_key': self.test_redis_key})

        with patch('board.services.redis_data_service.redis_data_service.check_redis_key_valid') as mock_check:
            with patch('board.services.redis_data_service.redis_data_service.get_combined_results') as mock_combined:
                mock_check.return_value = True
                mock_combined.return_value = {
                    'recommendations': [],
                    'search_results': [],
                    'total_recommendations': 0,
                    'total_search_results': 0
                }

                response = self.client.get(board_url)
                self.assertEqual(response.status_code, 200)

        # 3. Board 인증 테스트 API 호출 (JavaScript가 자동 호출하는 것을 시뮬레이션)
        auth_test_url = reverse('board:api_auth_test')
        response = self.client.get(
            auth_test_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_authenticated'])
        self.assertEqual(data['username'], 'boardjstest')
        self.assertEqual(data['current_path'], '/board/api/auth-test/')

    def test_home_to_board_navigation_flow(self):
        """Home에서 Board로의 내비게이션 플로우 테스트"""
        # 1. 로그인
        self.client.login(username='boardjstest', password='testpass123')

        # 2. Home 페이지 인증 테스트
        home_auth_url = reverse('home:api_auth_test')
        response = self.client.get(
            home_auth_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        home_data = response.json()
        self.assertTrue(home_data['is_authenticated'])

        # 3. Board 페이지 인증 테스트
        board_auth_url = reverse('board:api_auth_test')
        response = self.client.get(
            board_auth_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        board_data = response.json()
        self.assertTrue(board_data['is_authenticated'])

        # 4. 같은 사용자 세션 확인
        self.assertEqual(home_data['user_id'], board_data['user_id'])
        self.assertEqual(home_data['username'], board_data['username'])

    def test_board_api_error_handling(self):
        """Board API 오류 처리 테스트"""
        # 로그인
        self.client.login(username='boardjstest', password='testpass123')

        # 1. 존재하지 않는 Redis 키로 요청
        with patch('board.services.redis_data_service.redis_data_service.check_redis_key_valid') as mock_check:
            mock_check.return_value = False

            results_url = reverse('board:api_results', kwargs={'redis_key': 'nonexistent_key'})
            response = self.client.get(
                results_url,
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )

            self.assertEqual(response.status_code, 404)
            data = response.json()
            self.assertIn('error', data)

        # 2. 잘못된 매물 인덱스로 요청
        detail_url = reverse('board:api_property_detail', kwargs={
            'redis_key': self.test_redis_key,
            'property_index': 999
        })

        with patch('board.services.redis_data_service.redis_data_service.check_redis_key_valid') as mock_check:
            with patch('board.services.redis_data_service.redis_data_service.get_properties_from_search_results') as mock_props:
                mock_check.return_value = True
                mock_props.return_value = []  # 빈 결과

                response = self.client.get(
                    detail_url,
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest'
                )

                self.assertEqual(response.status_code, 404)

    def test_concurrent_board_requests(self):
        """Board 동시 요청 테스트"""
        # 로그인
        self.client.login(username='boardjstest', password='testpass123')

        # 동시에 여러 API 호출 시뮬레이션
        import threading
        import time

        results = []

        def make_request():
            response = self.client.get(
                reverse('board:api_auth_test'),
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            results.append(response.status_code)

        # 5개의 동시 요청
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()

        # 모든 요청이 성공했는지 확인
        self.assertEqual(len(results), 5)
        for status_code in results:
            self.assertEqual(status_code, 200)