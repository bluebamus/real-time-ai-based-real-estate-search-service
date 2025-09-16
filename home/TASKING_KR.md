# Project Tasking & Workflow Guide

이 문서는 프로젝트의 모든 앱에 대한 개발 지침, 작업 목록, 그리고 AI 워크플로우 규칙을 정의합니다.

---

## **Core Workflow & Rules (핵심 작업 절차 및 규칙)**

**중요: 모든 작업을 시작하기 전, 아래 규칙을 반드시 읽고 준수해야 합니다.**

1.  **작업 지시서 확인 (본 파일)**:
    -   모든 Django 앱 관련 작업은 반드시 이 파일에 명시된 내용을 기반으로 수행해야 합니다.
    -   만약 특정 앱에 대한 작업 내용이 없거나 "작업이 아직 정의되지 않았습니다"라고 명시된 경우, **해당 앱에 대해서는 어떠한 작업도 먼저 제안하거나 실행하지 마세요.**

2.  **작업 내역 확인 (`HISTORY.md`)**:
    -   작업을 시작하기 전, `HISTORY.md` 파일을 읽고 이전에 어떤 작업들이 완료되었는지 파악하여 중복 작업을 피하세요.

3.  **작업 내역 기록 (`HISTORY.md`)**:
    -   요청된 작업을 완료한 후에는, 변경된 파일 목록과 작업 요약을 `HISTORY.md` 파일의 최상단에 **반드시 기록해야 합니다.**

---

## user App Tasking Guide

이 문서는 `user` 앱에서 수행할 개발 및 테스트 작업을 정의합니다. 아래 명시된 요구사항과 절차를 엄격히 준수해 주십시오.

### Core Requirements

-   **Use Default User Model**: Django의 내장 `User` 모델(`django.contrib.auth.models.User`)을 직접 사용합니다.
-   **ModelForm-Based Development**: 모든 사용자 관련 폼(회원가입, 수정 등)은 `ModelForm` 또는 Django 내장 폼을 상속하여 구현합니다.
-   **Settings Management**: `user` 앱을 포함한 새로운 앱이나 패키지 추가 시, `INSTALLED_APPS` 등록 등 모든 관련 설정은 `config/settings.py`에 명시적으로 추가해야 합니다.
-   **Models and Migrations**: 기능에 새로운 모델이 필요한 경우, `models.py`에 정의하고 `makemigrations`, `migrate` 명령으로 데이터베이스 스키마에 적용해야 합니다.
-   **Authentication and Data Validation**: 모든 뷰는 `@login_required` 등 적절한 인증을 강제해야 하며, 폼을 통해 전달된 데이터는 철저히 검증해야 합니다.
-   **Admin Registration**: 개발된 모든 모델은 관리자 페이지에서 쉽게 조회하고 관리할 수 있도록 `admin.py`에 등록해야 합니다.
-   **Exclude Image Processing**: 사용자 프로필 이미지나 기타 이미지 업로드 및 처리 기능은 구현하지 않습니다.

### Detailed Task List

각 기능은 **Form → View → URL → Template → 테스트 코드 작성** 순서로 개발하는 것을 권장합니다.

#### 1. Sign Up
-   [ ] **Create Form**: Django의 `UserCreationForm`을 상속받아 아래 **[Sign Up Form Specifications]**를 충족하는 `SignupForm`을 구현합니다.
-   [ ] **Create View**: `SignupForm`을 사용하여 신규 사용자를 생성하는 클래스 기반 `SignupView`를 구현합니다. 가입 성공 시 로그인 페이지로 리디렉션합니다.
-   [ ] **Connect URL**: `SignupView`를 `/accounts/signup/` 경로에 매핑합니다.
-   [ ] **Create Template**: **[Template Specifications]**에 따라 `signup.html` 템플릿을 생성합니다.
-   **Write Pytest Code**:
    -   [ ] `test_signup_success`: 유효한 정보로 회원가입이 성공하는지 테스트합니다.
    -   [ ] `test_signup_fail_duplicate_username`: 중복된 `username`으로 가입 시 실패하는지 테스트합니다.
    -   [ ] `test_signup_fail_duplicate_email`: 중복된 `email`로 가입 시 실패하는지 테스트합니다.
    -   [ ] `test_signup_fail_password_mismatch`: 두 비밀번호 필드가 일치하지 않을 때 실패하는지 테스트합니다.

#### 2. Login & Logout
-   [ ] **Implement View/Form**: Django 내장 `AuthenticationForm`, `LoginView`, `LogoutView`를 활용합니다.
-   [ ] **Connect URL**: `/accounts/login/`, `/accounts/logout/` 경로를 설정합니다.
-   [ ] **Create Template**: **[Template Specifications]**에 따라 `login.html` 템플릿을 생성합니다.
-   **Write Pytest Code**:
    -   [ ] `test_login_success`: 유효한 정보로 로그인이 성공하는지 테스트합니다.
    -   [ ] `test_login_fail_wrong_password`: 잘못된 비밀번호로 로그인 시 실패하는지 테스트합니다.
    -   [ ] `test_logout`: 로그아웃이 정확히 처리되는지 테스트합니다.

#### 3. User Update
-   [ ] **Create Form**: `UserChangeForm` 기반으로 사용자가 수정 가능한 필드(이름, 이메일 등)만 포함하는 `UserUpdateForm`을 구현합니다.
-   [ ] **Create View**: `@login_required` 데코레이터를 사용하여 로그인한 사용자 본인만 정보를 수정할 수 있는 `UserUpdateView`를 구현합니다.
-   [ ] **Connect URL**: `UserUpdateView`를 `/accounts/update/` 경로에 매핑합니다.
-   [ ] **Create Template**: **[Template Specifications]**에 따라 `update.html` 템플릿을 생성합니다.
-   **Write Pytest Code**:
    -   [ ] `test_update_success`: 로그인한 사용자의 정보 수정이 성공하는지 테스트합니다.
    -   [ ] `test_update_fail_unauthenticated`: 미인증 사용자가 페이지 접근 시 로그인 페이지로 리디렉션되는지 테스트합니다.

#### 4. Withdrawal
-   [ ] **Create View**: 사용자를 실제로 삭제하는 대신 `is_active` 필드를 `False`로 변경하여 비활성화하는 `UserDeleteView`를 구현합니다.
-   [ ] **Connect URL**: `UserDeleteView`를 `/accounts/delete/` 경로에 매핑하고, 확인 절차를 거치도록 합니다.
-   [ ] **Create Template**: 최종 탈퇴 확인을 위한 `delete_confirm.html` 템플릿을 **[Template Specifications]**에 따라 생성합니다.
-   **Write Pytest Code**:
    -   [ ] `test_delete_success`: 로그인한 사용자가 성공적으로 비활성화되는지 테스트합니다.
    -   [ ] `test_delete_and_login_fail`: 비활성화된 계정으로 로그인이 불가능한지 테스트합니다.

#### 5. Template URL Verification
-   [ ] **Check Templates**: 모든 템플릿(`signup.html`, `login.html` 등) 내의 URL 링크가 Django의 `{% url %}` 템플릿 태그를 올바르게 사용하고, 정의된 URL 네임스페이스와 이름(예: `'user:signup'`)에 맞게 정확히 매칭되는지 확인합니다.

### Specifications

#### **Sign Up Form Specifications**
-   **Required Fields**: `username`, `email`, `password`, `password2`
-   **Data Validation**:
    -   `username`과 `email`은 고유해야 하며, DB에 이미 존재하면 안 됩니다.
    -   `password`와 `password2` 필드의 값이 일치해야 하며, 불일치 시 유효성 검사 오류를 발생시켜야 합니다.
    -   비밀번호는 Django의 기본 비밀번호 유효성 검사기를 통과해야 합니다.

#### **Template Specifications**
-   **Framework**: 모든 템플릿은 기본 스타일링을 위해 **Bootstrap 5**를 사용해야 합니다 (CDN 사용 가능).
-   **Structure**: `base.html` 템플릿을 생성하고, 다른 모든 템플릿은 이를 상속받아 일관된 레이아웃(네비게이션 바, 푸터 등)을 유지해야 합니다.
-   **Rendering Method**: `django-crispy-forms`와 같이 폼을 자동으로 렌더링하는 서드파티 패키지를 **사용하지 않습니다**. 모든 폼과 HTML 구성 요소는 순수 Bootstrap 5의 HTML, CSS, JavaScript를 사용하여 수동으로 작성해야 합니다.
-   **Form Rendering**: Django 폼 필드와 오류 메시지는 적절한 Bootstrap 5 클래스(예: `div`, `label`, `input`, `span.text-danger`)를 사용하여 렌더링해야 합니다.

### Test Code Writing Guidelines
-   **Write Immediately**: 기능이 완성되는 즉시 해당 기능에 대한 테스트 코드를 작성합니다.
-   **Use `conftest.py`**: 프로젝트 루트의 `conftest.py`에 정의된 픽스처(예: `client`, `test_user`)를 활용하여 일관된 테스트 환경을 유지합니다.
-   **Simple Unit Tests**: View와 Form의 핵심 로직을 검증하는 간단한 단위 테스트에 집중합니다.
-   **One Test, One Function Principle**: 각 테스트 함수는 **하나의 시나리오 또는 기능만** 검증해야 합니다.

---

## home App Tasking Guide

이 문서는 `home` 앱에서 수행할 개발 및 테스트 작업을 정의합니다.

### Core Requirements
-   **Frontend Framework**: 모든 UI 구성 요소는 **Bootstrap 5**를 사용하여 **반응형 웹 디자인**으로 구현해야 합니다.
-   **Asynchronous Communication**: 검색 기능은 JavaScript(`fetch` 또는 AJAX)를 사용하여 **페이지 새로고침 없이** 서버와 통신해야 합니다.
-   **Authentication**: API를 포함한 모든 뷰는 사용자 로그인을 요구해야 합니다. 미인증 접근 시도는 클라이언트와 서버 양쪽에서 적절히 처리되어야 합니다.
-   **Environment Variables**: API 키는 `.env` 파일을 통해 관리해야 하며, 이를 위해 `python-dotenv` 패키지를 사용해야 합니다.
-   **View Separation**: `home` 앱 내에 `views` 폴더를 생성하고, 일반 페이지 뷰와 API 뷰는 각각 다른 파일로 분리해야 합니다 (예: `base_views.py`, `api_views.py`).
-   **API Implementation**: API 뷰는 **Django REST Framework를 사용하지 않고**, 표준 Django 클래스 기반 `View`로 구현해야 합니다.
-   **CSRF Exemption**: 검색어를 수신하는 API 뷰는 CSRF 토큰 검증에서 제외되어야 합니다.

### Detailed Task List

**Backend Setup → View → URL → Template & JavaScript → 테스트 코드 작성** 순서로 개발하는 것을 권장합니다.

#### 1. Environment and Backend Setup
-   [ ] **Install Package**: `python-dotenv` 패키지를 설치합니다. (`uv add python-dotenv`)
-   [ ] **Project Setup**: `.env` 파일의 변수를 로드하도록 `config/settings.py` 또는 `manage.py`를 수정합니다.
-   [ ] **Create View Structure**: `home` 앱에 `views` 폴더를 생성하고 내부에 `__init__.py`, `base_views.py`, `api_views.py` 파일을 생성합니다.

#### 2. View Implementation
-   [ ] **Create Page View**: `home/views/base_views.py`에 메인 채팅 페이지를 렌더링하는 클래스 기반 `HomeView`를 구현합니다. 이 뷰는 로그인을 요구해야 합니다 (`@method_decorator(login_required, name='dispatch')`).
-   [ ] **Create API View**: `home/views/api_views.py`에 클래스 기반 `SearchAPIView`를 구현합니다.
    -   Django의 `View`를 상속받아야 합니다.
    -   로그인을 요구하고 CSRF 검증에서 제외되어야 합니다 (`@method_decorator(csrf_exempt, name='dispatch')`).
    -   `POST` 요청을 처리하고, 요청 본문에서 사용자의 자연어 질의를 받아 서버 콘솔 로그에 출력해야 합니다.

#### 3. URL Configuration
-   [ ] **Connect Page URL**: `HomeView`를 루트 경로(`/`)에 매핑합니다.
-   [ ] **Connect API URL**: `SearchAPIView`를 `/api/search/`와 같은 API 경로에 매핑합니다.

#### 4. Frontend and JavaScript Implementation
-   [ ] **Create Template**: **[Instructional Text Specifications]** 및 **[Template Specifications]**에 따라 `home.html` 템플릿을 생성합니다.
-   [ ] **Implement JavaScript**: 검색 폼 제출 이벤트를 가로채고, 페이지 새로고침을 막은 뒤, `fetch`를 사용하여 `/api/search/` 엔드포인트로 `POST` 요청을 보내는 JavaScript 코드를 작성합니다.

#### 5. Exception Handling
-   [ ] **Implement Server-Side Exception**: `HomeView`와 `SearchAPIView`는 미인증 사용자를 로그인 페이지로 리디렉션해야 합니다 (`@login_required`로 처리).
-   [ ] **Implement Client-Side Exception**: JavaScript는 API 요청 전송 전 사용자의 인증 상태를 확인하여, 미인증 시 로그인하라는 알림을 표시해야 합니다.

#### 6. Write Pytest Code
-   [ ] `test_home_view_authenticated_access`: 로그인한 사용자가 홈 페이지에 성공적으로 접근하는지 테스트합니다 (상태 코드 200).
-   [ ] `test_home_view_unauthenticated_redirect`: 미인증 사용자가 로그인 페이지로 리디렉션되는지 테스트합니다.
-   [ ] `test_search_api_success`: 로그인한 사용자의 `POST` 요청이 성공적으로 처리되고 질의가 로그에 남는지 테스트합니다.
-   [ ] `test_search_api_fail_unauthenticated`: 미인증 사용자의 `POST` 요청이 거부되는지(리디렉션 또는 403 상태) 테스트합니다.

### Specifications

#### **Instructional Text Specifications**
`home.html`의 안내 텍스트 박스는 아래와 같이 사용자 친화적인 내용을 포함해야 하며, 이 텍스트는 HTML에 직접 하드코딩합니다.
```html
<div class="alert alert-info" role="alert">
  <h4 class="alert-heading">어떻게 질문할까요?</h4>
  <p>최상의 결과를 위해 아래 예시처럼 질문해주세요. 정보는 5분 단위로 갱신됩니다!</p>
  <hr>
  <ul>
    <li><strong>정확한 지역</strong>을 알려주세요. (예: 서울시 강남구, 수원시 영통구)</li>
    <li>원하는 <strong>주거 타입</strong>을 하나만 선택해주세요. (예: 아파트, 오피스텔, 빌라)</li>
    <li><strong>거래 종류</strong>를 명시해주세요. (예: 매매, 전세, 월세)</li>
    <li><strong>다양한 조건</strong>을 추가할 수 있어요:
      <ul>
        <li>가격: 3억 이하, 10억 이상</li>
        <li>특징: 올수리, 역세권, 10년차 이내</li>
        <li>구조: 방 3개, 화장실 2개, 30평 이상</li>
      </ul>
    </li>
  </ul>
  <p class="mb-0"><strong>예시)</strong> "수원시 영통구 망포동에서 30평대 아파트 전세 5억 이하로 찾아줘. 방은 3개 이상이고 역세권이면 좋겠어."</p>
</div>