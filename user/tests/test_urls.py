"""
User App - URL 패턴 테스트

이 모듈은 다음과 같은 테스트들을 포함합니다:
1. test_url_patterns_exist: 모든 user 앱 URL 패턴이 존재하는지 테스트
2. test_url_patterns_accessible: URL 패턴들이 접근 가능한지 테스트 (인증 불요한 것들)
"""

import pytest
from django.test import Client
from django.urls import reverse


class TestURLs:
    """URL 패턴 테스트"""

    def test_url_patterns_exist(self):
        """모든 user 앱 URL 패턴이 존재하는지 테스트"""
        # URL 이름들이 정상적으로 resolve 되는지 확인
        assert reverse('user:signup')
        assert reverse('user:login')
        assert reverse('user:logout')
        assert reverse('user:update')
        assert reverse('user:delete')

    def test_url_patterns_accessible(self, client, db):
        """URL 패턴들이 접근 가능한지 테스트 (인증 불요한 것들)"""
        # 회원가입 페이지
        response = client.get(reverse('user:signup'))
        assert response.status_code == 200

        # 로그인 페이지
        response = client.get(reverse('user:login'))
        assert response.status_code == 200

    @pytest.fixture
    def client(self):
        """테스트 클라이언트"""
        return Client()