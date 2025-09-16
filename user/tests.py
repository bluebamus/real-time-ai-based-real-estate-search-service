import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .forms import SignupForm, UserUpdateForm


@pytest.fixture
def client():
    """테스트 클라이언트"""
    return Client()


@pytest.fixture
def test_user():
    """테스트용 사용자"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(client, test_user):
    """인증된 클라이언트"""
    client.login(username='testuser', password='testpass123')
    return client


class TestSignupView:
    """회원가입 뷰 테스트"""

    @pytest.mark.django_db
    def test_signup_success(self, client):
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

        # 사용자가 실제로 생성되었는지 확인
        assert User.objects.filter(username='newuser').exists()

    @pytest.mark.django_db
    def test_signup_fail_duplicate_username(self, client, test_user):
        """중복된 사용자명으로 가입 시 실패하는지 테스트"""
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

    @pytest.mark.django_db
    def test_signup_fail_duplicate_email(self, client, test_user):
        """중복된 이메일로 가입 시 실패하는지 테스트"""
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

    @pytest.mark.django_db
    def test_signup_fail_password_mismatch(self, client):
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


class TestLoginView:
    """로그인 뷰 테스트"""

    @pytest.mark.django_db
    def test_login_success(self, client, test_user):
        """정상적인 정보로 로그인이 성공하는지 테스트"""
        url = reverse('user:login')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = client.post(url, data)

        # 로그인 성공 후 사용자 정보 페이지로 리디렉션
        assert response.status_code == 302
        assert response.url == reverse('user:update')

    @pytest.mark.django_db
    def test_login_fail_wrong_password(self, client, test_user):
        """잘못된 비밀번호로 로그인 시 실패하는지 테스트"""
        url = reverse('user:login')
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = client.post(url, data)

        # 로그인 실패로 같은 페이지에 머무름
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors

    @pytest.mark.django_db
    def test_logout(self, authenticated_client):
        """로그아웃이 정상적으로 처리되는지 테스트"""
        url = reverse('user:logout')
        response = authenticated_client.post(url)

        # 로그아웃 성공 후 로그인 페이지로 리디렉션
        assert response.status_code == 302
        assert response.url == reverse('user:login')


class TestUserUpdateView:
    """사용자 정보 수정 뷰 테스트"""

    @pytest.mark.django_db
    def test_update_success(self, authenticated_client, test_user):
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

        # 실제로 정보가 수정되었는지 확인
        test_user.refresh_from_db()
        assert test_user.username == 'updateduser'
        assert test_user.email == 'updated@example.com'

    @pytest.mark.django_db
    def test_update_fail_unauthenticated(self, client):
        """로그인하지 않은 사용자가 정보 수정 페이지 접근 시 로그인 페이지로 리디렉션되는지 테스트"""
        url = reverse('user:update')
        response = client.get(url)

        # 로그인 페이지로 리디렉션
        assert response.status_code == 302
        assert '/accounts/login/' in response.url


class TestUserDeleteView:
    """회원탈퇴 뷰 테스트"""

    @pytest.mark.django_db
    def test_delete_success(self, authenticated_client, test_user):
        """로그인한 사용자가 정상적으로 탈퇴(비활성화) 처리되는지 테스트"""
        url = reverse('user:delete')
        response = authenticated_client.post(url)

        # 탈퇴 성공 후 로그인 페이지로 리디렉션
        assert response.status_code == 302
        assert response.url == reverse('user:login')

        # 사용자가 비활성화되었는지 확인
        test_user.refresh_from_db()
        assert not test_user.is_active

    @pytest.mark.django_db
    def test_delete_and_login_fail(self, client, test_user):
        """탈퇴한 계정으로 로그인이 실패하는지 테스트"""
        # 먼저 사용자를 비활성화
        test_user.is_active = False
        test_user.save()

        url = reverse('user:login')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = client.post(url, data)

        # 로그인 실패로 같은 페이지에 머무름
        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['form'].errors


class TestForms:
    """폼 테스트"""

    @pytest.mark.django_db
    def test_signup_form_valid(self):
        """회원가입 폼 유효성 테스트"""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'testpass123!',
            'password2': 'testpass123!'
        }
        form = SignupForm(data=form_data)
        assert form.is_valid()

    @pytest.mark.django_db
    def test_signup_form_invalid_email_duplicate(self, test_user):
        """이메일 중복시 폼 무효성 테스트"""
        form_data = {
            'username': 'newuser',
            'email': 'test@example.com',  # 이미 존재하는 이메일
            'password1': 'testpass123!',
            'password2': 'testpass123!'
        }
        form = SignupForm(data=form_data)
        assert not form.is_valid()
        assert 'email' in form.errors

    @pytest.mark.django_db
    def test_user_update_form_valid(self, test_user):
        """사용자 정보 수정 폼 유효성 테스트"""
        form_data = {
            'username': 'updateduser',
            'email': 'updated@example.com',
            'first_name': 'Updated',
            'last_name': 'User'
        }
        form = UserUpdateForm(data=form_data, instance=test_user)
        assert form.is_valid()
