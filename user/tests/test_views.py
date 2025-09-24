"""
User App - 뷰 테스트

이 모듈은 다음과 같은 테스트들을 포함합니다:
1. test_signup_success: 정상적인 정보로 회원가입이 성공하는지 테스트
2. test_signup_fail_duplicate_username: 중복된 사용자명으로 가입 시 실패하는지 테스트
3. test_signup_fail_duplicate_email: 중복된 이메일로 가입 시 실패하는지 테스트
4. test_signup_fail_password_mismatch: 비밀번호 불일치로 가입 시 실패하는지 테스트
5. test_signup_get_view: 회원가입 페이지 GET 요청 테스트
6. test_login_success: 정상적인 정보로 로그인이 성공하는지 테스트
7. test_login_fail_wrong_password: 잘못된 비밀번호로 로그인 시 실패하는지 테스트
8. test_login_fail_nonexistent_user: 존재하지 않는 사용자로 로그인 시 실패하는지 테스트
9. test_logout: 로그아웃이 정상적으로 처리되는지 테스트
10. test_login_get_view: 로그인 페이지 GET 요청 테스트
11. test_update_success: 로그인한 사용자가 정보 수정을 성공하는지 테스트
12. test_update_fail_unauthenticated: 로그인하지 않은 사용자가 정보 수정 페이지 접근 시 리디렉션 테스트
13. test_update_get_view: 사용자 정보 수정 페이지 GET 요청 테스트
14. test_update_fail_duplicate_username: 다른 사용자와 중복된 사용자명으로 수정 시 실패 테스트
15. test_delete_success: 로그인한 사용자가 정상적으로 탈퇴(비활성화) 처리되는지 테스트
16. test_delete_and_login_fail: 탈퇴한 계정으로 로그인이 실패하는지 테스트
17. test_delete_fail_unauthenticated: 로그인하지 않은 사용자가 탈퇴 시도 시 리디렉션 테스트
18. test_delete_get_view: 탈퇴 확인 페이지 GET 요청 테스트
"""

import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from ..forms import SignupForm, UserUpdateForm


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


class TestSignupView:
    """회원가입 뷰 테스트"""

    def test_signup_success(self, client, db):
        """정상적인 정보로 회원가입이 성공하는지 테스트"""
        url = reverse('user:signup')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'newpass123!',
            'password2': 'newpass123!'
        }
        response = client.post(url, data)

        # 회원가입 성공 후 로그인 페이지로 리디렉션
        assert response.status_code == 302
        assert response.url == reverse('user:login')

    def test_signup_fail_duplicate_username(self, client, db):
        """중복된 사용자명으로 가입 시 실패하는지 테스트"""
        # 기존 사용자 생성
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        url = reverse('user:signup')
        data = {
            'username': 'testuser',  # 이미 존재하는 사용자명
            'email': 'different@example.com',
            'password1': 'newpass123!',
            'password2': 'newpass123!'
        }
        response = client.post(url, data)

        # 가입 실패로 같은 페이지에 머무름
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors

    def test_signup_fail_duplicate_email(self, client, db):
        """중복된 이메일로 가입 시 실패하는지 테스트"""
        # 기존 사용자 생성
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        url = reverse('user:signup')
        data = {
            'username': 'newuser',
            'email': 'test@example.com',  # 이미 존재하는 이메일
            'password1': 'newpass123!',
            'password2': 'newpass123!'
        }
        response = client.post(url, data)

        # 가입 실패로 같은 페이지에 머무름
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors

    def test_signup_fail_password_mismatch(self, client, db):
        """비밀번호 불일치로 가입 시 실패하는지 테스트"""
        url = reverse('user:signup')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'newpass123!',
            'password2': 'differentpass!'
        }
        response = client.post(url, data)

        # 가입 실패로 같은 페이지에 머무름
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors

    def test_signup_get_view(self, client, db):
        """회원가입 페이지 GET 요청 테스트"""
        url = reverse('user:signup')
        response = client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context
        assert isinstance(response.context['form'], SignupForm)


class TestLoginView:
    """로그인 뷰 테스트"""

    def test_login_success(self, client, test_user, db):
        """정상적인 정보로 로그인이 성공하는지 테스트"""
        client.force_login(test_user)

        # 로그인 성공 후 홈 페이지로 리디렉션
        assert client.session['_auth_user_id'] == str(test_user.id)
        assert client.session['_auth_user_backend'] == 'django.contrib.auth.backends.ModelBackend'
        assert client.session['_auth_user_hash'] is not None

        # Check if the user is redirected to the home page after successful login
        response = client.get(reverse('home:home'))
        assert response.status_code == 200

    def test_login_fail_wrong_password(self, client, test_user, db):
        """잘못된 비밀번호로 로그인 시 실패하는지 테스트"""
        url = reverse('user:login')
        data = {
            'username': test_user.username,
            'password': 'wrongpassword'
        }
        response = client.post(url, data)

        # 로그인 실패로 같은 페이지에 머무름
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors

    def test_login_fail_nonexistent_user(self, client, db):
        """존재하지 않는 사용자로 로그인 시 실패하는지 테스트"""
        url = reverse('user:login')
        data = {
            'username': 'nonexistent',
            'password': 'anypassword'
        }
        response = client.post(url, data)

        # 로그인 실패로 같은 페이지에 머무름
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors

    def test_logout(self, authenticated_client, db):
        """로그아웃이 정상적으로 처리되는지 테스트"""
        url = reverse('user:logout')
        response = authenticated_client.post(url)

        # 로그아웃 성공 후 로그인 페이지로 리디렉션
        assert response.status_code == 302
        assert response.url == reverse('user:login')

    def test_login_get_view(self, client, db):
        """로그인 페이지 GET 요청 테스트"""
        url = reverse('user:login')
        response = client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context
        assert isinstance(response.context['form'], AuthenticationForm)


class TestUserUpdateView:
    """사용자 정보 수정 뷰 테스트"""

    def test_update_success(self, authenticated_client, test_user, db):
        """로그인한 사용자가 정보 수정을 성공하는지 테스트"""
        url = reverse('user:update')
        data = {
            'username': 'updateduser',
            'email': 'updated@example.com',
            'first_name': 'Updated',
            'last_name': 'User'
        }
        response = authenticated_client.post(url, data)

        # 정보 수정 성공 후 같은 페이지로 리디렉션
        assert response.status_code == 302
        assert response.url == reverse('user:update')

    def test_update_fail_unauthenticated(self, client, db):
        """로그인하지 않은 사용자가 정보 수정 페이지 접근 시 로그인 페이지로 리디렉션되는지 테스트"""
        url = reverse('user:update')
        response = client.get(url)

        # 로그인 페이지로 리디렉션
        assert response.status_code == 302
        assert '/user/login/' in response.url

    def test_update_get_view(self, authenticated_client, test_user, db):
        """사용자 정보 수정 페이지 GET 요청 테스트"""
        url = reverse('user:update')
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert 'form' in response.context
        assert isinstance(response.context['form'], UserUpdateForm)
        assert response.context['form'].instance == test_user

    def test_update_fail_duplicate_username(self, authenticated_client, test_user, db):
        """다른 사용자와 중복된 사용자명으로 수정 시 실패하는지 테스트"""
        # 다른 사용자 생성
        User.objects.create_user(
            username='anotheruser',
            email='another@example.com',
            password='testpass123'
        )

        url = reverse('user:update')
        data = {
            'username': 'anotheruser',  # 이미 존재하는 사용자명
            'email': 'updated@example.com',
            'first_name': 'Updated',
            'last_name': 'User'
        }
        response = authenticated_client.post(url, data)

        # 수정 실패로 같은 페이지에 머무름
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors


class TestUserDeleteView:
    """회원탈퇴 뷰 테스트"""

    def test_delete_success(self, authenticated_client, test_user, db):
        """로그인한 사용자가 정상적으로 탈퇴(비활성화) 처리되는지 테스트"""
        url = reverse('user:delete')
        response = authenticated_client.post(url)

        # 탈퇴 성공 후 로그인 페이지로 리디렉션
        assert response.status_code == 302
        assert response.url == reverse('user:login')

    def test_delete_and_login_fail(self, client, db):
        """탈퇴한 계정으로 로그인이 실패하는지 테스트"""
        # 비활성화된 사용자 생성
        user = User.objects.create_user(
            username='inactiveuser',
            email='inactive@example.com',
            password='testpass123'
        )
        user.is_active = False
        user.save()

        url = reverse('user:login')
        data = {
            'username': 'inactiveuser',
            'password': 'testpass123'
        }
        response = client.post(url, data)

        # 로그인 실패로 같은 페이지에 머무름
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors

    def test_delete_fail_unauthenticated(self, client, db):
        """로그인하지 않은 사용자가 탈퇴 시도 시 로그인 페이지로 리디렉션되는지 테스트"""
        url = reverse('user:delete')
        response = client.post(url)

        # 로그인 페이지로 리디렉션
        assert response.status_code == 302
        assert '/user/login/' in response.url

    def test_delete_get_view(self, authenticated_client, db):
        """탈퇴 확인 페이지 GET 요청 테스트"""
        url = reverse('user:delete')
        response = authenticated_client.get(url)

        assert response.status_code == 200