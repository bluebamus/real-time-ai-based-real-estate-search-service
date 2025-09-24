"""
User App - 폼 테스트

이 모듈은 다음과 같은 테스트들을 포함합니다:
1. test_signup_form_valid: 회원가입 폼 유효성 테스트
2. test_signup_form_invalid_email_duplicate: 이메일 중복시 폼 무효성 테스트
3. test_signup_form_invalid_password_mismatch: 비밀번호 불일치시 폼 무효성 테스트
4. test_user_update_form_valid: 사용자 정보 수정 폼 유효성 테스트
5. test_user_update_form_invalid_duplicate_username: 다른 사용자와 중복된 사용자명으로 수정시 폼 무효성 테스트
"""

import pytest
from django.contrib.auth.models import User
from ..forms import SignupForm, UserUpdateForm


class TestForms:
    """폼 테스트"""

    @pytest.fixture
    def existing_user(self, db):
        """기존 사용자 픽스처"""
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_signup_form_valid(self, db):
        """회원가입 폼 유효성 테스트"""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'testpass123!',
            'password2': 'testpass123!'
        }
        form = SignupForm(data=form_data)
        assert form.is_valid()

    def test_signup_form_invalid_email_duplicate(self, existing_user, db):
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

    def test_signup_form_invalid_password_mismatch(self, db):
        """비밀번호 불일치시 폼 무효성 테스트"""
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'testpass123!',
            'password2': 'differentpass!'
        }
        form = SignupForm(data=form_data)
        assert not form.is_valid()
        assert 'password2' in form.errors

    def test_user_update_form_valid(self, existing_user, db):
        """사용자 정보 수정 폼 유효성 테스트"""
        form_data = {
            'username': 'updateduser',
            'email': 'updated@example.com',
            'first_name': 'Updated',
            'last_name': 'User'
        }
        form = UserUpdateForm(data=form_data, instance=existing_user)
        assert form.is_valid()

    def test_user_update_form_invalid_duplicate_username(self, existing_user, db):
        """다른 사용자와 중복된 사용자명으로 수정시 폼 무효성 테스트"""
        # 다른 사용자 생성
        User.objects.create_user(
            username='anotheruser',
            email='another@example.com',
            password='testpass123'
        )

        form_data = {
            'username': 'anotheruser',  # 이미 존재하는 사용자명
            'email': 'updated@example.com',
            'first_name': 'Updated',
            'last_name': 'User'
        }
        form = UserUpdateForm(data=form_data, instance=existing_user)
        assert not form.is_valid()
        assert 'username' in form.errors