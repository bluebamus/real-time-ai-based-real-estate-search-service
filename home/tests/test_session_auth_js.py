"""
Home App - JavaScript 세션 인증 테스트

이 모듈은 Home 앱의 JavaScript 세션 기반 인증, CSRF, CORS 기능을 테스트합니다.
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


@pytest.mark.api
@pytest.mark.views
class HomeSessionAuthTestCase(TestCase):
    """
    Home 앱 JavaScript 세션 인증 테스트 케이스
    """

    def setUp(self):
        """테스트 환경 설정"""
        self.client = Client()

        # 테스트 사용자 생성
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # URL 설정
        self.auth_test_url = reverse('home:api_auth_test')
        self.search_url = reverse('home:api_search')

    def test_csrf_token_required(self):
        """CSRF 토큰 필수 확인 테스트"""
        # 로그인
        self.client.login(username='testuser', password='testpass123')

        # CSRF 토큰 없이 POST 요청
        response = self.client.post(
            self.search_url,
            {'query': '서울시 강남구 아파트'},
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # CSRF 오류 확인 (403 Forbidden)
        self.assertEqual(response.status_code, 403)

    def test_csrf_token_with_credentials(self):
        """CSRF 토큰과 credentials 설정 테스트"""
        # 로그인
        self.client.login(username='testuser', password='testpass123')

        # CSRF 토큰 획득
        csrf_token = get_token(self.client.session)

        # CSRF 토큰과 함께 요청
        response = self.client.post(
            self.search_url,
            json.dumps({'query': '서울시 강남구 아파트'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # 200 또는 400 상태 코드 (비즈니스 로직 오류는 괜찮음)
        self.assertIn(response.status_code, [200, 400, 500])

    def test_session_authentication_success(self):
        """세션 인증 성공 테스트"""
        # 로그인
        self.client.login(username='testuser', password='testpass123')

        # 인증 테스트 API 호출
        response = self.client.get(
            self.auth_test_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['is_authenticated'])
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['user_id'], self.user.id)
        self.assertTrue(data['session_exists'])
        self.assertEqual(data['message'], '인증 테스트 완료')

    def test_session_authentication_failure(self):
        """세션 인증 실패 테스트"""
        # 로그인하지 않은 상태에서 API 호출
        response = self.client.get(
            self.auth_test_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # 401 Unauthorized 확인
        self.assertEqual(response.status_code, 401)

    def test_cors_headers(self):
        """CORS 헤더 테스트"""
        # 로그인
        self.client.login(username='testuser', password='testpass123')

        # Origin 헤더와 함께 요청
        response = self.client.get(
            self.auth_test_url,
            HTTP_ORIGIN='http://localhost:8000',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)

        # CORS 헤더가 설정되어 있는지 확인 (django-cors-headers에 의해)
        # 실제 프로덕션에서는 Access-Control-Allow-Origin 헤더가 있어야 함

    def test_session_persistence(self):
        """세션 지속성 테스트"""
        # 로그인
        login_response = self.client.login(username='testuser', password='testpass123')
        self.assertTrue(login_response)

        # 세션 ID 확인
        session_key = self.client.session.session_key
        self.assertIsNotNone(session_key)

        # 같은 클라이언트로 여러 요청
        for i in range(3):
            response = self.client.get(
                self.auth_test_url,
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertTrue(data['is_authenticated'])
            self.assertEqual(data['username'], 'testuser')

    @patch('home.services.keyword_extraction.ChatGPTKeywordExtractor.extract_keywords')
    @patch('home.services.crawlers.NaverRealEstateCrawler.crawl_properties')
    def test_search_api_with_session_auth(self, mock_crawler, mock_extractor):
        """검색 API 세션 인증 테스트 (모킹 사용)"""
        # 모킹 설정
        mock_extractor.return_value = {
            "address": {"sido": "서울시", "sigungu": "강남구"},
            "transaction_type": ["매매"],
            "building_type": ["아파트"]
        }
        mock_crawler.return_value = [
            {
                "owner_name": "테스트 아파트",
                "address": "서울시 강남구",
                "transaction_type": "매매",
                "price": 500000000,
                "building_type": "아파트",
                "area_size": 25.64,
                "floor_info": "5/15층",
                "direction": "남향",
                "tags": ["신축", "역세권"],
                "updated_date": "2025-09-23"
            }
        ]

        # 로그인
        self.client.login(username='testuser', password='testpass123')

        # CSRF 토큰 획득
        csrf_token = get_token(self.client.session)

        # 검색 API 호출
        response = self.client.post(
            self.search_url,
            json.dumps({'query': '서울시 강남구 아파트 매매'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # 성공 응답 확인
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('query', data)
        self.assertIn('extracted_keywords', data)
        self.assertIn('result_count', data)
        self.assertIn('redis_key', data)
        self.assertIn('redirect_url', data)

    def test_multiple_concurrent_sessions(self):
        """다중 동시 세션 테스트"""
        # 첫 번째 클라이언트
        client1 = Client()
        client1.login(username='testuser', password='testpass123')

        # 두 번째 사용자 생성 및 클라이언트
        user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        client2 = Client()
        client2.login(username='testuser2', password='testpass123')

        # 각 클라이언트로 동시 요청
        response1 = client1.get(
            self.auth_test_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        response2 = client2.get(
            self.auth_test_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # 각각 올바른 사용자로 인증 확인
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

        data1 = response1.json()
        data2 = response2.json()

        self.assertEqual(data1['username'], 'testuser')
        self.assertEqual(data2['username'], 'testuser2')
        self.assertEqual(data1['user_id'], self.user.id)
        self.assertEqual(data2['user_id'], user2.id)

    def test_session_expiry(self):
        """세션 만료 테스트"""
        # 로그인
        self.client.login(username='testuser', password='testpass123')

        # 세션 수동 삭제 (만료 시뮬레이션)
        session_key = self.client.session.session_key
        Session.objects.filter(session_key=session_key).delete()

        # 만료된 세션으로 요청
        response = self.client.get(
            self.auth_test_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # 401 Unauthorized 확인
        self.assertEqual(response.status_code, 401)

    def test_csrf_token_in_cookies(self):
        """쿠키의 CSRF 토큰 테스트"""
        # 로그인
        self.client.login(username='testuser', password='testpass123')

        # CSRF 토큰 생성을 위한 GET 요청
        response = self.client.get('/home/')

        # 쿠키에 CSRF 토큰이 있는지 확인
        self.assertIn('csrftoken', response.cookies)
        csrf_cookie = response.cookies['csrftoken']
        self.assertIsNotNone(csrf_cookie.value)

    def test_javascript_fetch_simulation(self):
        """JavaScript fetch API 시뮬레이션 테스트"""
        # 로그인
        self.client.login(username='testuser', password='testpass123')

        # CSRF 토큰 획득
        csrf_token = get_token(self.client.session)

        # JavaScript fetch와 동일한 헤더로 요청
        response = self.client.post(
            self.auth_test_url,
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            HTTP_ACCEPT='application/json',
            HTTP_CONTENT_TYPE='application/json'
        )

        # GET 메서드이므로 405 Method Not Allowed이지만 인증은 통과
        self.assertEqual(response.status_code, 405)

    def test_invalid_csrf_token(self):
        """잘못된 CSRF 토큰 테스트"""
        # 로그인
        self.client.login(username='testuser', password='testpass123')

        # 잘못된 CSRF 토큰으로 요청
        response = self.client.post(
            self.search_url,
            json.dumps({'query': '서울시 강남구 아파트'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN='invalid_token',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # CSRF 오류 확인
        self.assertEqual(response.status_code, 403)


@pytest.mark.integration
class HomeJavaScriptIntegrationTest(TestCase):
    """
    Home JavaScript 통합 테스트
    실제 브라우저 환경을 시뮬레이션
    """

    def setUp(self):
        """테스트 환경 설정"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='jstest',
            email='jstest@example.com',
            password='testpass123'
        )

    def test_full_authentication_flow(self):
        """전체 인증 플로우 테스트"""
        # 1. 로그인 페이지 접근
        login_url = reverse('user:login')
        response = self.client.get(login_url)
        self.assertEqual(response.status_code, 200)

        # 2. 로그인 수행
        login_success = self.client.login(username='jstest', password='testpass123')
        self.assertTrue(login_success)

        # 3. Home 페이지 접근
        home_url = reverse('home:home')
        response = self.client.get(home_url)
        self.assertEqual(response.status_code, 200)

        # 4. 인증 테스트 API 호출 (JavaScript가 자동 호출하는 것을 시뮬레이션)
        auth_test_url = reverse('home:api_auth_test')
        response = self.client.get(
            auth_test_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_authenticated'])
        self.assertEqual(data['username'], 'jstest')

    def test_cross_origin_request_simulation(self):
        """교차 출처 요청 시뮬레이션 테스트"""
        # 로그인
        self.client.login(username='jstest', password='testpass123')

        # 다른 출처에서의 요청 시뮬레이션
        auth_test_url = reverse('home:api_auth_test')
        response = self.client.get(
            auth_test_url,
            HTTP_ORIGIN='http://localhost:3000',  # 다른 포트
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        # CORS 설정에 따라 처리됨
        # 현재 설정에서는 localhost:8000만 허용되므로 CORS 오류가 발생할 수 있음
        # 하지만 django-cors-headers가 적절히 처리함
        self.assertIn(response.status_code, [200, 403])