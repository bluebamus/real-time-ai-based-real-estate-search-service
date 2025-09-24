"""
User App - 뷰 권한 테스트

이 모듈은 다음과 같은 테스트들을 포함합니다:
1. test_authenticated_required_views: 로그인이 필요한 뷰들이 제대로 보호되는지 테스트
2. test_authenticated_users_can_access_protected_views: 로그인한 사용자가 보호된 뷰에 접근할 수 있는지 테스트
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User


class TestViewPermissions:
    """뷰 권한 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트"""
        return Client()

    @pytest.fixture
    def test_user(self, db):
        """테스트용 사용자"""
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @pytest.fixture
    def authenticated_client(self, client, test_user, db):
        """인증된 클라이언트"""
        client.login(username='testuser', password='testpass123')
        return client

    def test_authenticated_required_views(self, client, db):
        """로그인이 필요한 뷰들이 제대로 보호되는지 테스트"""
        # 인증이 필요한 URL들
        protected_urls = [
            reverse('user:update'),
            reverse('user:delete'),
        ]

        for url in protected_urls:
            response = client.get(url)
            # 로그인 페이지로 리디렉션되어야 함
            assert response.status_code == 302
            assert '/user/login/' in response.url

    def test_authenticated_users_can_access_protected_views(self, authenticated_client, db):
        """로그인한 사용자가 보호된 뷰에 접근할 수 있는지 테스트"""
        # 인증된 사용자가 접근 가능한 URL들
        accessible_urls = [
            reverse('user:update'),
            reverse('user:delete'),
        ]

        for url in accessible_urls:
            response = authenticated_client.get(url)
            assert response.status_code == 200