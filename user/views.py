from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.models import User
from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.decorators import method_decorator
from .forms import SignupForm, UserUpdateForm


class SignupView(CreateView):
    """
    회원가입 뷰
    SignupForm을 사용하여 새로운 사용자를 생성
    """
    form_class = SignupForm
    template_name = 'user/signup.html'
    success_url = reverse_lazy('user:login')

    def form_valid(self, form):
        """가입 성공시 성공 메시지 출력"""
        response = super().form_valid(form)
        messages.success(self.request, '회원가입이 완료되었습니다. 로그인해주세요.')
        return response

    def dispatch(self, request, *args, **kwargs):
        """이미 로그인한 사용자는 정보 수정 페이지로 리디렉션 (임시)"""
        if request.user.is_authenticated:
            return redirect('user:update')
        return super().dispatch(request, *args, **kwargs)


class CustomLoginView(LoginView):
    """
    로그인 뷰
    Django의 내장 LoginView를 사용하여 구현
    """
    template_name = 'user/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        """로그인 성공시 홈페이지로 이동"""
        return reverse_lazy('home:home')

    def form_valid(self, form):
        """로그인 성공시 환영 메시지 출력"""
        response = super().form_valid(form)
        messages.success(self.request, f'{self.request.user.username}님, 환영합니다!')
        return response


class CustomLogoutView(LogoutView):
    """
    로그아웃 뷰
    Django의 내장 LogoutView를 사용하여 구현
    """
    next_page = reverse_lazy('user:login')

    def dispatch(self, request, *args, **kwargs):
        """로그아웃시 메시지 출력"""
        if request.user.is_authenticated:
            messages.info(request, '로그아웃 되었습니다.')
        return super().dispatch(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class UserUpdateView(UpdateView):
    """
    사용자 정보 수정 뷰
    로그인한 사용자만 자신의 정보를 수정할 수 있음
    """
    model = User
    form_class = UserUpdateForm
    template_name = 'user/update.html'
    success_url = reverse_lazy('user:update')

    def get_object(self):
        """현재 로그인한 사용자 객체 반환"""
        return self.request.user

    def form_valid(self, form):
        """정보 수정 성공시 성공 메시지 출력"""
        response = super().form_valid(form)
        messages.success(self.request, '정보가 성공적으로 수정되었습니다.')
        return response


@login_required
def user_delete(request):
    """
    회원탈퇴 뷰
    사용자를 실제로 삭제하지 않고 is_active를 False로 설정하여 비활성화
    """
    if request.method == 'POST':
        user = request.user
        user.is_active = False
        user.save()
        messages.success(request, '회원탈퇴가 완료되었습니다.')
        return redirect('user:login')

    return render(request, 'user/delete_confirm.html')
