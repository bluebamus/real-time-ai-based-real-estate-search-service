# `user` 앱 작업 가이드

본 문서는 `user` 앱에서 수행해야 할 개발 및 테스트 작업을 정의합니다. 아래 명시된 요구사항과 절차를 엄격히 준수해 주시기 바랍니다.

---

## 핵심 요구사항

-   **기본 사용자 모델 사용**: Django의 내장 `User` 모델(`django.contrib.auth.models.User`)을 직접 사용합니다.
-   **ModelForm 기반 개발**: 모든 사용자 관련 폼(예: 회원가입, 수정)은 `ModelForm` 또는 Django의 내장 폼을 상속받아 구현합니다.
-   **설정 관리**: `user` 앱을 포함한 새로운 앱이나 패키지를 추가할 때, `INSTALLED_APPS` 등록 등 관련 설정을 모두 `config/settings.py`에 명시적으로 추가해야 합니다.
-   **모델 및 마이그레이션**: 기능에 새로운 모델이 필요한 경우, `models.py`에 정의하고 `makemigrations` 및 `migrate` 명령어를 사용하여 데이터베이스 스키마에 적용해야 합니다.
-   **인증 및 데이터 검증**: 모든 뷰는 적절한 인증을 강제해야 하며(예: `@login_required`), 폼을 통해 전달되는 데이터는 철저히 검증되어야 합니다.
-   **관리자 등록**: 개발된 모든 모델은 `admin.py`에 등록하여 관리자 페이지에서 쉽게 확인하고 관리할 수 있도록 해야 합니다.
-   **이미지 처리 제외**: 사용자 프로필 이미지나 기타 이미지 업로드 및 처리 기능은 구현하지 않습니다.

---

## 상세 작업 목록

각 기능은 **폼 → 뷰 → URL → 템플릿 → 테스트 코드 작성** 순서로 개발하는 것을 권장합니다.

### 1. 회원가입

-   [x] **폼 생성**: Django의 `UserCreationForm`을 상속받아 아래 **[회원가입 폼 명세]**를 충족하는 `SignupForm`을 구현합니다.
-   [x] **뷰 생성**: `SignupForm`을 사용하여 새로운 사용자를 생성하는 클래스 기반 `SignupView`를 구현합니다. 성공적인 회원가입 후 로그인 페이지로 리디렉션합니다.
-   [x] **URL 연결**: `SignupView`를 `/accounts/signup/` 경로에 매핑합니다.
-   [x] **템플릿 생성**: **[템플릿 명세]**에 따라 `signup.html` 템플릿을 생성합니다.
-   **Pytest 코드 작성**:
    -   [x] `test_signup_success`: 유효한 정보로 회원가입이 성공하는지 테스트
    -   [x] `test_signup_fail_duplicate_username`: 중복된 `username`으로 가입 시 실패하는지 테스트
    -   [x] `test_signup_fail_duplicate_email`: 중복된 `email`로 가입 시 실패하는지 테스트
    -   [x] `test_signup_fail_password_mismatch`: 두 비밀번호 필드가 일치하지 않을 때 실패하는지 테스트

### 2. 로그인 및 로그아웃

-   [x] **뷰/폼 구현**: Django의 내장 `AuthenticationForm`, `LoginView`, `LogoutView`를 활용합니다.
-   [x] **URL 연결**: `/accounts/login/` 및 `/accounts/logout/` 경로를 설정합니다.
-   [x] **템플릿 생성**: **[템플릿 명세]**에 따라 `login.html` 템플릿을 생성합니다.
-   **Pytest 코드 작성**:
    -   [x] `test_login_success`: 유효한 자격 증명으로 로그인이 성공하는지 테스트
    -   [x] `test_login_fail_wrong_password`: 잘못된 비밀번호로 로그인 실패하는지 테스트
    -   [x] `test_logout`: 로그아웃이 정상적으로 처리되는지 테스트

### 3. 사용자 정보 수정

-   [x] **폼 생성**: `UserChangeForm`을 기반으로 사용자가 수정할 수 있는 필드만 포함하는 `UserUpdateForm`을 구현합니다(예: 이름, 이메일).
-   [x] **뷰 생성**: `@login_required` 데코레이터가 적용된 `UserUpdateView`를 구현하여 로그인한 사용자만 자신의 정보를 수정할 수 있도록 합니다.
-   [x] **URL 연결**: `UserUpdateView`를 `/accounts/update/` 경로에 매핑합니다.
-   [x] **템플릿 생성**: **[템플릿 명세]**에 따라 `update.html` 템플릿을 생성합니다.
-   **Pytest 코드 작성**:
    -   [x] `test_update_success`: 로그인한 사용자가 정보 수정을 성공하는지 테스트
    -   [x] `test_update_fail_unauthenticated`: 인증되지 않은 사용자가 페이지 접근 시 로그인 페이지로 리디렉션되는지 테스트

### 4. 회원탈퇴

-   [x] **뷰 생성**: 실제로 삭제하는 대신 `is_active` 필드를 `False`로 설정하여 사용자를 비활성화하는 `UserDeleteView`를 구현합니다.
-   [x] **URL 연결**: `UserDeleteView`를 `/accounts/delete/` 경로에 매핑하고, 확인 단계를 거치도록 합니다.
-   [x] **템플릿 생성**: **[템플릿 명세]**에 따라 최종 탈퇴 확인을 위한 `delete_confirm.html` 템플릿을 생성합니다.
-   **Pytest 코드 작성**:
    -   [x] `test_delete_success`: 로그인한 사용자가 성공적으로 비활성화되는지 테스트
    -   [x] `test_delete_and_login_fail`: 비활성화된 계정으로 로그인할 수 없는지 테스트

---

## 명세

### **회원가입 폼 명세**

-   **필수 필드**: `username`, `email`, `password`, `password2`
-   **데이터 검증**:
    -   `username`과 `email`은 고유해야 하며 데이터베이스에 이미 존재할 수 없습니다.
    -   `password`와 `password2` 필드의 값이 일치해야 합니다. 일치하지 않으면 검증 오류를 발생시켜야 합니다.
    -   비밀번호는 Django의 기본 비밀번호 검증기를 통과해야 합니다.

### **템플릿 명세**

-   **프레임워크**: 모든 템플릿은 기본 스타일링을 위해 **Bootstrap 5**를 사용해야 합니다(CDN 사용 가능).
-   **구조**: `base.html` 템플릿을 생성합니다. 다른 모든 템플릿은 이를 확장하여 일관된 레이아웃을 유지해야 합니다(예: 내비게이션 바, 푸터).
-   **렌더링 방법**: `django-crispy-forms`와 같은 폼을 자동으로 렌더링하는 **서드파티 패키지를 사용하지 말고**, 순수한 Bootstrap 5의 HTML, CSS, JavaScript를 사용하여 모든 폼과 HTML 컴포넌트를 수동으로 작성해야 합니다.
-   **폼 렌더링**: 적절한 Bootstrap 5 클래스를 사용하여 Django 폼 필드와 오류 메시지를 렌더링합니다(예: `div`, `label`, `input`, `span.text-danger`).

---

## 테스트 코드 작성 가이드라인

-   **즉시 작성**: 기능이 완료되는 즉시 해당 기능에 대한 테스트 코드를 작성합니다.
-   **`conftest.py` 사용**: 일관된 테스트 환경을 유지하기 위해 프로젝트 루트의 `conftest.py`에 정의된 픽스처(예: `client`, `test_user`)를 활용합니다.
-   **단순한 단위 테스트**: 뷰와 폼의 핵심 로직을 검증하는 단순한 단위 테스트에 중점을 둡니다.
-   **하나의 테스트, 하나의 기능 원칙**: 각 테스트 함수는 **하나의 시나리오나 기능만을 검증**해야 합니다(예: `test_user_can_access_update_page`와 `test_guest_cannot_access_update_page`를 분리).