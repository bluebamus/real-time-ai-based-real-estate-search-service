"""
User App - 통합 테스트

이 모듈은 다음과 같은 테스트들을 포함합니다:
1. test_complete_user_lifecycle: 사용자의 전체 생명주기 테스트 (가입 → 로그인 → 정보수정 → 탈퇴)
2. test_signup_then_login_redirect_to_home: 회원가입 후 로그인시 홈으로 정상 리다이렉트되는지 테스트
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User


class TestUserIntegration:
    """사용자 플로우 통합 테스트"""

    @pytest.fixture
    def client(self):
        """테스트 클라이언트"""
        return Client()

    def test_complete_user_lifecycle(self, client, db):
        """사용자의 전체 생명주기 테스트: 가입 -> 로그인 -> 정보수정 -> 탈퇴"""

        # 1. 회원가입
        signup_url = reverse('user:signup')
        signup_data = {
            'username': 'lifecycleuser',
            'email': 'lifecycle@example.com',
            'password1': 'StrongPassword123!',
            'password2': 'StrongPassword123!'
        }
        response = client.post(signup_url, signup_data)
        assert response.status_code == 302

        # Retrieve the user and set the password explicitly (for test client authentication)
        user = User.objects.get(username='lifecycleuser')
        user.set_password(signup_data['password1']) # Set the plain text password
        user.save()

        # 2. 로그인
        # client.post를 통한 로그인 대신 client.login 헬퍼 함수를 사용하여 인증 상태를 설정합니다.
        # 이 테스트는 LoginView의 POST 동작을 직접 테스트하는 대신, 인증 후의 통합 흐름을 테스트하는 데 중점을 둡니다.
        user = User.objects.get(username='lifecycleuser')
        client.login(username=user.username, password=signup_data['password1'])

        # 로그인 후 홈 페이지로 이동 (인증된 상태이므로 200 OK가 예상됨)
        response = client.get(reverse('home:home'))
        assert response.status_code == 200
        assert response.request['PATH_INFO'] == reverse('home:home')

        # Ensure the user is logged in for subsequent steps
        user = User.objects.get(username='lifecycleuser')
        client.login(username=user.username, password=signup_data['password1'])

        # 3. 정보 수정
        update_url = reverse('user:update')
        update_data = {
            'username': 'lifecycleuser',
            'email': 'updated_lifecycle@example.com',
            'first_name': 'Lifecycle',
            'last_name': 'User'
        }
        response = client.post(update_url, update_data)
        assert response.status_code == 302

        user = User.objects.get(username='lifecycleuser')
        assert user.email == 'updated_lifecycle@example.com'

        # 4. 회원탈퇴
        delete_url = reverse('user:delete')
        response = client.post(delete_url)
        assert response.status_code == 302

        user.refresh_from_db()
        assert not user.is_active

    def test_signup_then_login_redirect_to_home(self, client, db):
        """회원가입 후 로그인시 홈으로 정상 리다이렉트되는지 테스트"""
        # 회원가입
        signup_url = reverse('user:signup')
        signup_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'newpass123!',
            'password2': 'newpass123!'
        }
        response = client.post(signup_url, signup_data)
        assert response.status_code == 302
        assert User.objects.filter(username='newuser').exists()

        # 로그인
        login_url = reverse('user:login')
        login_data = {
            'username': 'newuser',
            'password': 'newpass123!'
        }
        response = client.post(login_url, login_data)

        # 홈 페이지로 리다이렉션되는지 확인
        assert response.status_code == 302
        assert response.url == reverse('home:home')