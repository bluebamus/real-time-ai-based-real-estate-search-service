# AI 기반 자연어 질의형 부동산 매물 추천 서비스

## 프로젝트 개요

본 프로젝트는 **AI 기반 자연어 처리 기술을 활용하여 부동산 매물을 검색하고, 사용자 맞춤형 추천을 제공하는 서비스**입니다. 사용자는 일상 언어로 원하는 부동산 조건을 질의하고, 시스템은 이를 분석하여 실시간 크롤링 데이터를 기반으로 최적의 매물 정보를 제공합니다.

## 주요 기능

*   **자연어 기반 부동산 매물 검색**: 사용자의 자연어 질의를 이해하고 분석하여 검색합니다.
*   **실시간 네이버 부동산 데이터 크롤링**: Playwright를 활용하여 최신 부동산 정보를 수집합니다.
*   **AI 기반 키워드 추출**: OpenAI ChatGPT API를 통해 자연어에서 핵심 검색 키워드를 정확하게 추출합니다.
*   **사용자 인증**: 안전한 서비스 이용을 위한 회원가입, 로그인, 정보 수정 기능을 제공합니다.
*   **확장 가능한 아키텍처**: 향후 추천 시스템, 실거래가 분석, 캐싱, 비동기 처리 등 다양한 기능 확장을 고려하여 설계되었습니다.

## 기술 스택

| 분류         | 기술                                                              |
| :----------- | :---------------------------------------------------------------- |
| **백엔드**   | Django 5.0+, Django REST Framework, Python 3.13+                  |
| **프론트엔드** | Bootstrap 5.3+, Vanilla JavaScript (ES6+), Fetch API              |
| **데이터베이스** | MySQL 8.0+ (주 데이터베이스), Redis 7.0+ (캐시 및 메시지 브로커) |
| **AI/ML**    | OpenAI ChatGPT API (GPT-4o-mini)                                  |
| **웹 크롤링**  | Playwright 1.40+                                                  |
| **패키지 관리**| `uv` (Python 의존성 관리)                                         |

## 프로젝트 구조

```
real-time-ai-based-real-estate-search-service/
├── config/             # Django 프로젝트의 핵심 설정 및 전역 URL 관리
├── user/               # 사용자 인증 (회원가입, 로그인, 로그아웃, 정보 수정 등)
├── home/               # 메인 홈페이지 및 자연어 검색 인터페이스, AI/크롤링 연동 로직
├── board/              # 검색 결과 및 추천 매물 표시
├── utils/              # 공통 유틸리티 함수 및 모듈 (AI, 파싱, 크롤링 등)
├── static/             # 정적 파일 (CSS, JavaScript, 이미지)
├── templates/          # HTML 템플릿 (root 레벨에 통합 관리)
├── pre-test/           # 개발 중 실험적인 스크립트 (예: 크롤링 POC)
├── .gitignore          # Git 버전 관리 제외 파일
├── pyproject.toml      # 프로젝트 의존성 정의 (uv 사용)
├── uv.lock             # uv를 통한 의존성 잠금 파일
└── manage.py           # Django 관리 명령어 실행 스크립트
```

## 특별 문서 파일 안내

이 저장소에는 프로젝트의 개발 및 관리를 돕기 위한 몇 가지 특별한 문서 파일이 포함되어 있습니다.

*   **`Development-Plan-Specification.md` (개발 명세서)**
    *   **목적**: 프로젝트의 전체적인 개발 계획, 시스템 아키텍처, 기술 스택, 데이터베이스 설계, API 명세, 개발 일정, 테스트 계획 등 모든 기술적/기능적 정의를 담고 있는 **최상위 문서**입니다.
    *   **사용법**: 프로젝트의 큰 그림과 상세한 구현 방향을 이해하고자 할 때 참조합니다. 모든 개발 작업은 이 명세서를 기반으로 진행됩니다.

*   **`CLAUDE.md` (Claude 개발 가이드)**
    *   **목적**: AI 개발 도구(특히 Claude)가 이 저장소의 코드를 이해하고 효율적으로 작업할 수 있도록 돕는 **AI 전용 가이드 문서**입니다. 프로젝트 개요, 핵심 기술 스택, 프로젝트 구조, 개발 워크플로우 및 규칙, 코딩 스타일 가이드 등을 AI의 관점에서 설명합니다.
    *   **사용법**: AI 에이전트가 이 저장소에서 작업을 수행하기 전에 반드시 참조해야 하는 문서입니다.

*   **`[앱 이름]/TASKING.md` (앱별 작업 기록)**
    *   **목적**: 각 Django 앱(`user`, `home`, `board`, `utils` 등) 내부에서 수행된 **개별 개발 작업의 상세 내역을 기록**하는 문서입니다. 수정된 파일 목록, 작업 요약, 완료된 체크리스트 등이 포함됩니다.
    *   **사용법**: 특정 앱에서 어떤 작업이 완료되었는지, 어떤 파일이 변경되었는지 등을 추적하고 확인하는 데 사용됩니다. 새로운 작업을 시작하기 전에 해당 앱의 `TASKING.md`를 검토하여 중복 작업을 피하고 진행 상황을 파악합니다.

## 개발 환경 설정

프로젝트를 로컬에서 실행하기 위한 단계별 가이드입니다.

1.  **저장소 클론**:
    ```bash
    git clone https://github.com/your-repo/real-time-ai-based-real-estate-search-service.git
    cd real-time-ai-based-real-estate-search-service
    ```

2.  **Python 가상 환경 설정 및 의존성 설치**:
    이 프로젝트는 `uv`를 패키지 관리자로 사용합니다.
    ```bash
    # uv 설치 (아직 설치되지 않았다면)
    # pip install uv

    # 의존성 설치
    uv sync
    ```

3.  **데이터베이스 설정**:
    MySQL 데이터베이스(`ai_test_prj`)와 사용자(`ai_admin`, 비밀번호 `test1324`)를 생성해야 합니다.
    ```sql
    CREATE DATABASE ai_test_prj CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE USER 'ai_admin'@'%' IDENTIFIED BY 'test1324';
    GRANT ALL PRIVILEGES ON ai_test_prj.* TO 'ai_admin'@'%';
    FLUSH PRIVILEGES;
    ```

4.  **`.env` 파일 설정**:
    프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가합니다. `OPENAI_API_KEY`는 반드시 본인의 키로 교체해야 합니다.
    ```env
    # Django Secret Key (임의의 문자열로 교체)
    SECRET_KEY=your_django_secret_key_here

    # 개발 모드 활성화 (배포 시에는 False로 설정)
    DEBUG=True

    # OpenAI ChatGPT API 설정
    OPENAI_API_KEY=your_openai_api_key_here
    OPENAI_MODEL=gpt-4o-mini
    OPENAI_MAX_TOKENS=150
    OPENAI_TEMPERATURE=0.1

    # 데이터베이스 설정 (기본값 사용 시 생략 가능)
    DB_NAME=ai_test_prj
    DB_USER=ai_admin
    DB_PASSWORD=test1324
    DB_HOST=localhost
    DB_PORT=3306

    # Redis 설정 (기본값 사용 시 생략 가능)
    REDIS_HOST=localhost
    REDIS_PORT=6379
    REDIS_DB=0
    # REDIS_PASSWORD=your_redis_password_here
    ```

5.  **데이터베이스 마이그레이션**:
    ```bash
    uv run python manage.py migrate
    ```

6.  **슈퍼유저 생성**:
    관리자 페이지 접근 및 테스트를 위해 슈퍼유저를 생성합니다.
    ```bash
    uv run python manage.py createsuperuser
    ```

## 서비스 실행

개발 서버를 실행하여 서비스를 시작합니다.

```bash
uv run python manage.py runserver
```

브라우저에서 `http://127.0.0.1:8000/home/` 에 접속하여 서비스를 이용할 수 있습니다. (로그인 필요)

## 테스트

프로젝트의 테스트는 `pytest`를 사용하여 실행합니다.

```bash
pytest
```

## 기여

기여를 환영합니다! 풀 리퀘스트를 보내기 전에 `Development-Plan-Specification.md`와 해당 앱의 `TASKING.md`를 검토하여 프로젝트의 방향성과 기존 작업을 이해해 주시기 바랍니다.

## 라이선스

이 프로젝트는 MIT 라이선스에 따라 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하십시오.

## 소유자

**Lim Dohyun**

---