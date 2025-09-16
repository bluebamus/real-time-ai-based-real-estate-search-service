# `user` 앱 작업 지시서 (Tasking Guide)

이 문서는 `user` 앱에서 수행해야 할 기능 개발 및 테스트 작업을 정의합니다. 아래 명시된 요구사항과 절차를 반드시 준수하여 작업을 진행해 주세요.

---

## 핵심 요구사항

-   **기본 사용자 모델 사용**: Django의 내장 `User` 모델(`django.contrib.auth.models.User`)을 직접 사용합니다.
-   **ModelForm 기반 개발**: 모든 사용자 관련 Form은 `ModelForm` 또는 Django의 내장 Form을 상속받아 구현합니다.
-   **설정 관리**: `user` 앱을 포함하여 새로운 앱이나 패키지를 추가할 경우, `INSTALLED_APPS` 등록 등 모든 관련 설정은 `config/settings.py`에 명시적으로 추가해야 합니다.
-   **모델 및 마이그레이션**: 기능 구현에 새로운 모델이 필요한 경우, 모델을 `models.py`에 정의하고 `makemigrations` 및 `migrate` 명령을 통해 데이터베이스 스키마에 반영해야 합니다.
-   **인증 및 데이터 검증**: 모든 View는 적절한 인증 절차를 거쳐야 하며, Form을 통해 전달된 데이터의 유효성을 철저히 검증해야 합니다.
-   **Admin 등록**: 개발과 관련된 모든 모델은 `admin.py`에 등록하여 관리자 페이지에서 쉽게 확인하고 관리할 수 있어야 합니다.
-   **이미지 처리 제외**: 사용자 프로필 이미지 등 이미지 업로드 및 처리 기능은 구현하지 않습니다.

---

## 세부 작업 목록

각 기능은 **Form → View → URL → Template → 테스트 코드 작성** 순으로 개발하는 것을 권장합니다.

### 1. 회원가입 (Sign Up)

-   [ ] **Form 생성**: `UserCreationForm`을 상속받아 아래 **[회원가입 Form 명세]**를 충족하는 `SignupForm`을 구현합니다.
-   [ ] **View 생성**: `SignupForm`을 사용하여 신규 사용자를 생성하는 `SignupView`를 클래스 기반 뷰로 구현합니다. 가입 성공 시 로그인 페이지로 리디렉션합니다.
-   [ ] **URL 연결**: `/accounts/signup/` 경로에 `SignupView`를 연결합니다.
-   [ ] **Template 생성**: **[Template 명세]**에 따라 `signup.html` 템플릿을 작성합니다.
-   [ ] **Pytest 코드 작성**:
    -   `test_signup_success`: 정상 정보로 회원가입 성공을 테스트합니다.
    -   `test_signup_fail_duplicate_username`: 중복된 `username`으로 가입 시 실패를 테스트합니다.
    -   `test_signup_fail_duplicate_email`: 중복된 `email`로 가입 시 실패를 테스트합니다.
    -   `test_signup_fail_password_mismatch`: 비밀번호 2개가 일치하지 않을 때 가입 실패를 테스트합니다.

### 2. 로그인 및 로그아웃 (Login & Logout)

-   [ ] **View/Form 구현**: Django 내장 `AuthenticationForm`, `LoginView`, `LogoutView`를 활용합니다.
-   [ ] **URL 연결**: `/accounts/login/`, `/accounts/logout/` 경로를 설정합니다.
-   [ ] **Template 생성**: **[Template 명세]**에 따라 `login.html` 템플릿을 작성합니다.
-   [ ] **Pytest 코드 작성**:
    -   `test_login_success`: 정상 정보로 로그인 성공을 테스트합니다.
    -   `test_login_fail_wrong_password`: 잘못된 비밀번호로 로그인 실패를 테스트합니다.
    -   `test_logout`: 정상적인 로그아웃 처리를 테스트합니다.

### 3. 사용자 정보 업데이트 (User Update)

-   [ ] **Form 생성**: `UserChangeForm`을 기반으로 사용자가 수정할 필드(예: 이름, 이메일)만 포함하는 `UserUpdateForm`을 구현합니다.
-   [ ] **View 생성**: `@login_required`를 적용하여 로그인한 사용자만 정보를 수정할 수 있는 `UserUpdateView`를 구현합니다.
-   [ ] **URL 연결**: `/accounts/update/` 경로에 `UserUpdateView`를 연결합니다.
-   [ ] **Template 생성**: **[Template 명세]**에 따라 `update.html` 템플릿을 작성합니다.
-   [ ] **Pytest 코드 작성**:
    -   `test_update_success`: 로그인 사용자의 정보 수정 성공을 테스트합니다.
    -   `test_update_fail_unauthenticated`: 비로그인 사용자가 접근 시 로그인 페이지로 리디렉션되는지 테스트합니다.

### 4. 회원탈퇴 (Withdrawal)

-   [ ] **View 생성**: 사용자를 삭제하는 대신, `is_active` 필드를 `False`로 변경하여 비활성화하는 `UserDeleteView`를 구현합니다.
-   [ ] **URL 연결**: `/accounts/delete/` 경로에 `UserDeleteView`를 연결하고, 탈퇴 확인 페이지를 거치도록 합니다.
-   [ ] **Template 생성**: **[Template 명세]**에 따라 탈퇴 확인 `delete_confirm.html` 템플릿을 작성합니다.
-   [ ] **Pytest 코드 작성**:
    -   `test_delete_success`: 로그인 사용자의 정상 탈퇴(비활성화) 처리를 테스트합니다.
    -   `test_delete_and_login_fail`: 탈퇴한 계정으로 로그인이 실패하는지 테스트합니다.

---

## 명세 (Specifications)

### **회원가입 Form 명세**

-   **필수 필드**: `username`, `email`, `password`, `password2`
-   **데이터 검증**:
    -   `username`과 `email`은 DB에 이미 존재하는 값과 중복될 수 없습니다.
    -   `password`와 `password2` 필드의 값이 반드시 일치해야 합니다. 일치하지 않을 경우, 검증(validation) 에러를 발생시켜야 합니다.
    -   Django의 기본 비밀번호 검증 로직을 통과해야 합니다.

### **Template 명세**

-   **기반**: 모든 템플릿은 **Bootstrap 5**를 사용하여 기본적인 스타일링을 적용합니다. (CDN 방식 사용)
-   **구조**: `base.html` 템플릿을 생성하고, 다른 모든 템플릿은 이를 상속받아 일관된 레이아웃(네비게이션 바, 푸터 등)을 유지합니다.
-   **렌더링 방식**: `django-crispy-forms`와 같이 폼을 자동으로 렌더링하는 **서드파티 패키지는 사용하지 않습니다.** 모든 폼과 HTML 구성요소는 순수 Bootstrap 5의 HTML, CSS, JavaScript를 사용하여 직접 작성해야 합니다.
-   **폼 렌더링**: Django Form 필드와 에러 메시지를 `div`, `label`, `input`, `span.text-danger` 등의 적절한 Bootstrap 5 클래스를 사용하여 렌더링합니다.

---

## 테스트 코드 작성 지침

-   **즉시 작성**: 하나의 기능 개발이 완료되면, 곧바로 해당 기능에 대한 테스트 코드를 작성합니다.
-   **`conftest.py` 활용**: 프로젝트 root의 `conftest.py`에 정의된 `fixture` (예: `client`, `test_user`)를 활용하여 일관된 테스트 환경을 유지합니다.
-   **단순한 유닛 테스트**: View와 Form의 핵심 로직을 검증하는 간단한 유닛 테스트 위주로 작성합니다.
-   **1 테스트, 1 기능 원칙**: 하나의 테스트 함수는 **오직 하나의 시나리오와 기능만 검증**하도록 명확하게 분리하여 작성합니다.