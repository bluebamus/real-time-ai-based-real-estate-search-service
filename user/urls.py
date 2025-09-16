from django.urls import path
from . import views

app_name = 'user'

urlpatterns = [
    # 회원가입 - /accounts/signup/
    path('signup/', views.SignupView.as_view(), name='signup'),

    # 로그인 - /accounts/login/
    path('login/', views.CustomLoginView.as_view(), name='login'),

    # 로그아웃 - /accounts/logout/
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),

    # 사용자 정보 수정 - /accounts/update/
    path('update/', views.UserUpdateView.as_view(), name='update'),

    # 회원탈퇴 - /accounts/delete/
    path('delete/', views.user_delete, name='delete'),
]