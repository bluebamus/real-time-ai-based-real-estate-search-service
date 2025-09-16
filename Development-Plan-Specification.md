# AI 기반 자연어 질의형 부동산 매물 추천·실거래가 분석 서비스 개발 명세서

## 목차
1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [기술 스택](#3-기술-스택)
4. [데이터베이스 설계](#4-데이터베이스-설계)
5. [Django 앱 구조 설계](#5-django-앱-구조-설계)
6. [API 설계](#6-api-설계)
7. [프론트엔드 설계](#7-프론트엔드-설계)
8. [크롤링 시스템 설계](#8-크롤링-시스템-설계)
9. [추천 시스템 설계](#9-추천-시스템-설계)
10. [캐싱 전략](#10-캐싱-전략)
11. [비동기 작업 처리](#11-비동기-작업-처리)
12. [보안 요구사항](#12-보안-요구사항)
13. [개발 일정](#13-개발-일정)
14. [테스트 계획](#14-테스트-계획)
15. [배포 계획](#15-배포-계획)

---

## 1. 프로젝트 개요

### 1.1 프로젝트 목적
자연어 처리 기술을 활용하여 사용자가 일상 언어로 부동산 매물을 검색하고, AI 기반 추천 시스템을 통해 맞춤형 매물을 제공하는 서비스 개발

### 1.2 핵심 기능
- 자연어 기반 부동산 매물 검색
- 실시간 네이버 부동산 데이터 크롤링
- 사용자 맞춤형 매물 추천 시스템
- 실거래가 분석 및 시각화
- Redis 기반 고성능 캐싱 시스템

### 1.3 목표 사용자
- 부동산 매물을 찾는 일반 사용자
- 시세 정보를 필요로 하는 투자자
- 부동산 중개업소

### 1.4 사용자 시나리오 및 구현 기술

#### 1.4.1 홈페이지 방문 및 검색 시작
**시나리오:**
사용자가 홈페이지에 방문하면 ChatGPT 웹 인터페이스와 유사한 중앙 배치 검색 박스를 만난다. 상단에는 자연어 검색 가이드와 예시 문구가 표시된다.

**구현 기술:**
- Bootstrap 5: 반응형 중앙 정렬 레이아웃
- HTML5/CSS3: 시맨틱 마크업 및 스타일링
- JavaScript (ES6+): 동적 UI 상호작용
- Django Templates: 서버 사이드 렌더링

**주요 구성 요소:**
```html
<div class="search-container">
    <div class="search-guide">
        <h3>자연어로 부동산을 검색해보세요</h3>
        <p>예시: "서울시 강남구 30평대 아파트 매매 5억 이하"</p>
    </div>
    <div class="search-input-group">
        <input type="text" placeholder="원하는 조건을 자연어로 입력하세요">
        <button>검색</button>
    </div>
</div>
```

#### 1.4.2 로그인 인증 및 권한 확인
**시나리오:**
비로그인 사용자가 검색 박스를 클릭하면 로그인 요구 팝업이 표시된다. 로그인 후에만 검색 기능에 접근할 수 있다.

**구현 기술:**
- Django Authentication: 사용자 인증 시스템
- JWT (JSON Web Tokens): 토큰 기반 인증
- JavaScript Fetch API: 비동기 인증 상태 확인
- Bootstrap Modal: 팝업 UI 구현
- Django User App: 회원가입, 로그인, 로그아웃, 회원탈퇴, 정보수정

**인증 플로우:**
```javascript
function checkAuthAndSearch() {
    const token = localStorage.getItem('auth_token');
    if (!token) {
        showLoginModal();
        return;
    }
    proceedWithSearch();
}
```

#### 1.4.3 자연어 처리 및 키워드 추출
**시나리오:**
로그인된 사용자가 자연어 검색을 입력하면 Django Home App의 뷰에서 처리된다. API 요청으로 처리되며 화면 전환 없이 로딩 상태를 표시한다.

**구현 기술:**
- Utils App: 공통 유틸리티 클래스 구현
- OpenAI ChatGPT API: 자연어 처리 및 의도 파악
- Django REST Framework: API 엔드포인트 구성
- Redis: 작업 큐 및 결과 캐싱
- JavaScript Async/Await: 비동기 UI 처리

**처리 과정:**
1. 사용자 입력 → Django Home App View
2. `utils.ai.ChatGPTClient` 클래스를 통한 키워드 추출
3. `utils.parsers.KeywordParser` 클래스로 필수 키워드 검증 (시·도 + 시·군·구)
4. 기본값 적용 (누락 키워드)
5. JSON 형식 키워드 반환

**Utils 클래스 구조:**
```python
# utils/ai.py
class ChatGPTClient:
    def extract_keywords(self, query_text: str) -> dict
    def validate_response(self, response: dict) -> bool

# utils/parsers.py
class KeywordParser:
    def validate_required_fields(self, keywords: dict) -> bool
    def apply_defaults(self, keywords: dict) -> dict
```

#### 1.4.4 네이버 부동산 크롤링 및 캐싱
**시나리오:**
추출된 키워드를 기반으로 네이버 부동산 데이터를 크롤링한다. 동일 키워드의 기존 캐시를 확인하고, 없을 경우 새로 크롤링하여 Redis에 5분 TTL로 저장한다.

**구현 기술:**
- Utils App: 크롤링 및 캐시 관리 클래스
- Playwright: 헤드리스 브라우저 자동화 (pre-test/gemini-naver.py 활용)
- Redis: 결과 캐싱 (TTL: 5분)
- Hash 기반 키 생성: 중복 방지

**Utils 클래스 구조:**
```python
# utils/crawlers.py
class NaverRealEstateCrawler:
    def crawl_properties(self, keywords: dict) -> list
    def build_search_url(self, keywords: dict) -> str
    def extract_property_data(self, page) -> list

# utils/cache.py
class RedisCache:
    def get_cached_results(self, cache_key: str) -> list
    def set_cached_results(self, cache_key: str, data: list, ttl: int)
    def generate_cache_key(self, keywords: dict) -> str
```

**크롤링 키워드 구조:**
```python
keywords = {
    'address': '서울시 강남구',
    'owner_type': '개인',
    'transaction_type': '매매',
    'price_max': 500000000,
    'building_type': '아파트',
    'area_pyeong': 30,
    'floor_info': '중층',
    'direction': '남향',
    'tags': ['신축', '역세권'],
    'updated_date': '최근'
}
```

#### 1.4.5 결과 표시 및 추천 시스템
**시나리오:**
크롤링 완료 후 Home App에서 Board App으로 이동하며 Redis 키를 전달한다. Board App은 Bootstrap 5 카드 디자인으로 반응형 결과를 표시한다.

**구현 기술:**
- Django Board App: 결과 표시 전용 앱
- Bootstrap 5 Cards: 매물 정보 카드 UI
- Django Pagination: 커스텀 페이지네이션 클래스
- Redis Sorted Sets: 추천 시스템 구현
- CSS Grid/Flexbox: 반응형 레이아웃

**결과 표시 구조:**
- 추천 매물 (20개): 전체 사용자 기반 10개 + 개별 사용자 기반 10개
- 검색 결과 (30개): 사용자 검색 키워드 기반
- 총 50개 제한 (한 페이지)

#### 1.4.6 추천 알고리즘 및 스코어링
**시나리오:**
Redis Sorted Set을 활용한 간단한 추천 시스템으로 사용자별/전체 사용자별 키워드 스코어를 관리한다.

**구현 기술:**
- Utils App: 추천 시스템 클래스
- Redis Sorted Sets: 키워드 스코어 관리
- Celery Beat: 5분마다 자동 갱신

**Utils 클래스 구조:**
```python
# utils/recommendations.py
class RecommendationEngine:
    def update_user_keyword_score(self, user_id: int, keywords: dict)
    def get_user_recommendations(self, user_id: int) -> list
    def get_global_recommendations(self) -> list
    def extract_top_keywords(self, prefix: str) -> dict

# utils/tasks.py
class RecommendationTasks:
    def update_recommendations_task(self)
    def crawl_and_cache_recommendations(self, keywords: dict)
```

**키 구조:**
```
user:{userID}:keywords:{카테고리}
global:keywords:{카테고리}
```

**예시:**
```
user:12345:keywords:거래타입 → {'매매': 10, '전세': 7, '월세': 3}
global:keywords:거래타입 → {'매매': 1500, '전세': 800, '월세': 300}
```

#### 1.4.7 페이지네이션 및 추가 결과 로딩
**시나리오:**
사용자가 페이지네이션 번호를 클릭하면 해당 페이지의 30개 데이터를 Redis에서 가져와 표시한다.

**구현 기술:**
- Django Custom Pagination Class: 페이지네이션 로직
- JavaScript AJAX: 비동기 페이지 로딩
- Redis LRANGE: 범위별 데이터 조회
- Bootstrap Pagination: UI 컴포넌트

#### 1.4.8 자동 추천 시스템 갱신 및 백업
**시나리오:**
Celery Beat를 통해 5분마다 가장 높은 스코어의 키워드들을 조합하여 자동 크롤링을 수행하고 추천 매물 캐시를 갱신한다. 동시에 Redis 장애에 대비하여 키워드 스코어 데이터를 Database에 백업한다.

**구현 기술:**
- Utils App: 자동 갱신 및 백업 시스템 클래스
- Celery Beat Scheduler: 주기적 작업 실행 (Django 관리)
- Redis 데이터 분석: 스코어 기반 키워드 추출
- Database 백업: Redis 장애 대비 이중화

**Celery Beat 실행 환경:**
```bash
# 3개의 별도 터미널 필요
uv run python manage.py runserver          # Django 서버
uv run celery -A config worker -l info     # Celery Worker
uv run celery -A config beat -l info       # Celery Beat (스케줄러)
```

**Utils 클래스 구조:**
```python
# utils/tasks.py (Celery Tasks)
@shared_task
def update_recommendations():
    # 5분마다 추천 시스템 갱신
    task_handler = RecommendationTasks()
    task_handler.update_recommendations_task()

@shared_task
def backup_redis_scores_to_database():
    # 10분마다 Redis → Database 백업
    KeywordScore.backup_from_redis(redis_client)

# utils/models.py (Database 백업)
class KeywordScore(models.Model):
    # Redis Sorted Sets 백업용 모델
    user, category, keyword, score, updated_at

class RecommendationCache(models.Model):
    # 추천 매물 캐시 백업용 모델
    user, cache_key, properties_data, updated_at
```

**갱신 및 백업 프로세스:**
1. **추천 갱신 (5분마다)**: `utils.tasks.update_recommendations`
   - `utils.scheduler.AutoUpdateScheduler`를 통한 최고 스코어 키워드 추출
   - `utils.crawlers.NaverRealEstateCrawler`로 크롤링 실행
   - `utils.cache.RedisCache`를 통한 추천 매물 캐시 저장 (최대 10개)

2. **데이터 백업 (10분마다)**: `utils.tasks.backup_redis_scores_to_database`
   - Redis Sorted Sets → KeywordScore 모델 저장
   - 추천 캐시 → RecommendationCache 모델 저장
   - upsert 로직으로 중복 방지

3. **자동 복원 (Django 재시작 시)**:
   - KeywordScore 모델 → Redis Sorted Sets 복원
   - RecommendationCache 모델 → Redis 캐시 복원

#### 1.4.9 Redis 장애 대비 시스템
**시나리오:**
Redis 서버 장애나 데이터 손실에 대비하여 중요한 추천 시스템 데이터를 MySQL Database에 이중화하여 저장한다.

**핵심 특징:**
- **실시간 백업**: 10분마다 Redis → Database 자동 동기화
- **자동 복원**: Django 재시작 시 Database → Redis 자동 복원
- **데이터 무결성**: upsert 로직으로 중복 방지 및 일관성 유지
- **관리 인터페이스**: Django Admin에서 백업 데이터 확인 가능

---

## 2. 시스템 아키텍처

### 2.1 전체 아키텍처
```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Client)                     │
│              (Bootstrap 5 + JavaScript)                  │
└─────────────────┬───────────────────────────────────────┘
                  │ HTTP/HTTPS
┌─────────────────▼───────────────────────────────────────┐
│                   Django Web Server                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │   User   │  │   Home   │  │  Board   │             │
│  │   App    │  │   App    │  │   App    │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────┬────────────┬──────────────┬──────────────────────┘
      │            │              │
┌─────▼────────────▼──────────────▼──────────────────────┐
│              Django REST Framework                       │
│                  (API Layer)                            │
└─────┬────────────┬──────────────┬──────────────────────┘
      │            │              │
┌─────▼────────────▼──────────────▼──────────────────────┐
│    PostgreSQL  │    Redis     │   Celery + Redis       │
│    (Main DB)   │   (Cache)    │   (Task Queue)         │
└────────────────┴──────┬───────┴────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│              External Services                          │
│  ┌──────────────┐  ┌────────────────┐                 │
│  │  OpenAI API  │  │  Naver Real    │                 │
│  │  (ChatGPT)   │  │  Estate         │                 │
│  └──────────────┘  └────────────────┘                 │
└─────────────────────────────────────────────────────────┘
```

### 2.2 데이터 플로우
1. 사용자 자연어 입력 → Django Home App
2. ChatGPT API를 통한 자연어 처리 → JSON 변환
3. Playwright 기반 네이버 부동산 크롤링
4. Redis 캐시 저장 (TTL: 5분)
5. Board App에서 결과 표시
6. **Celery Beat 자동 작업**:
   - 추천 시스템 갱신 (5분마다)
   - Redis → Database 백업 (10분마다)
7. **Django 재시작 시**: Database → Redis 자동 복원

### 2.3 고가용성 및 데이터 보호
- **Redis 이중화**: 중요 데이터 MySQL Database 백업
- **자동 복원**: 서비스 재시작 시 데이터 웜업
- **실시간 동기화**: 10분 간격 백업으로 최신성 보장

---

## 3. 기술 스택

### 3.1 백엔드
- **Framework**: Django 5.0+
- **API**: Django REST Framework 3.14+
- **Task Queue**: Celery 5.3+
- **Scheduler**: django-celery-beat 2.8+ (Database 스케줄러)
- **Message Broker**: Redis 5.0+
- **Web Scraping**: Playwright 1.40+

### 3.2 프론트엔드
- **CSS Framework**: Bootstrap 5.3+
- **JavaScript**: Vanilla JS (ES6+)
- **AJAX**: Fetch API

### 3.3 데이터베이스
- **Main Database**: MySQL 8.0+
- **Cache Database**: Redis 7.0+

### 3.4 외부 서비스
- **AI/ML**: OpenAI API (GPT-4)
- **Data Source**: 네이버 부동산

### 3.5 배포 및 인프라
- **Web Server**: Nginx
- **WSGI Server**: Gunicorn
- **Container**: Docker & Docker Compose
- **Monitoring**: Prometheus + Grafana

---

## 4. 데이터베이스 설계

### 4.1 MySQL 스키마

#### 4.1.1 User 모델
```python
class User(AbstractUser):
    user_id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_premium = models.BooleanField(default=False)
    search_count = models.IntegerField(default=0)
    last_search_date = models.DateTimeField(null=True)
```

#### 4.1.2 SearchHistory 모델
```python
class SearchHistory(models.Model):
    search_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query_text = models.TextField()  # 원본 자연어 쿼리
    parsed_keywords = models.JSONField()  # 파싱된 키워드
    search_date = models.DateTimeField(auto_now_add=True)
    result_count = models.IntegerField(default=0)
    redis_key = models.CharField(max_length=255)
```

#### 4.1.3 Property 모델 (크롤링 데이터)
```python
class Property(models.Model):
    property_id = models.AutoField(primary_key=True)
    address = models.CharField(max_length=500)  # 주소
    owner_type = models.CharField(max_length=50)  # 집주인
    transaction_type = models.CharField(max_length=50)  # 거래타입
    price = models.BigIntegerField()  # 가격
    building_type = models.CharField(max_length=50)  # 건물 종류
    area_pyeong = models.FloatField()  # 평수
    floor_info = models.CharField(max_length=100)  # 층정보
    direction = models.CharField(max_length=20)  # 집방향
    tags = models.JSONField(default=list)  # 태그
    updated_date = models.DateTimeField()  # 갱신일
    crawled_date = models.DateTimeField(auto_now_add=True)
    detail_url = models.URLField(max_length=500)
    image_urls = models.JSONField(default=list)
    description = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['address', 'transaction_type']),
            models.Index(fields=['price']),
            models.Index(fields=['area_pyeong']),
            models.Index(fields=['crawled_date']),
        ]
```

#### 4.1.4 UserPreference 모델
```python
class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_areas = models.JSONField(default=list)  # 선호 지역
    preferred_price_min = models.BigIntegerField(null=True)
    preferred_price_max = models.BigIntegerField(null=True)
    preferred_area_min = models.FloatField(null=True)
    preferred_area_max = models.FloatField(null=True)
    preferred_building_types = models.JSONField(default=list)
    notification_enabled = models.BooleanField(default=True)
```

#### 4.1.5 KeywordScore 모델 (Redis 백업용)
```python
class KeywordScore(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    category = models.CharField(max_length=50)  # address, transaction_type 등
    keyword = models.CharField(max_length=200)  # 키워드 값
    score = models.FloatField(default=0.0)      # Redis Sorted Set 스코어
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['user', 'category', 'keyword']]
        indexes = [
            models.Index(fields=['user', 'category']),
            models.Index(fields=['category', 'score']),
        ]
```

#### 4.1.6 RecommendationCache 모델 (추천 캐시 백업용)
```python
class RecommendationCache(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    cache_key = models.CharField(max_length=255)     # Redis 캐시 키
    properties_data = models.JSONField()             # 추천 매물 JSON 데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['user', 'cache_key']]
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['updated_at']),
        ]
```

### 4.2 Redis 데이터 구조

#### 4.2.1 캐시 키 구조
```
# 검색 결과 캐시
search:{hash(keywords)}:results -> List of property data (TTL: 5분)

# 사용자별 검색 키워드 추적 (Sorted Set)
user:{user_id}:keywords:{category} -> {keyword: score}

# 전체 사용자 검색 키워드 추적 (Sorted Set)
global:keywords:{category} -> {keyword: score}

# 추천 매물 캐시
user:{user_id}:recommendations -> List of recommended properties (No TTL)
global:recommendations -> List of global recommended properties (No TTL)

# 세션 관리
session:{session_id} -> User session data (TTL: 30분)
```

---

## 5. Django 앱 구조 설계

### 5.1 프로젝트 구조
```
real_estate_project/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   └── celery.py
├── apps/
│   ├── user/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── forms.py
│   │   ├── managers.py
│   │   └── tests.py
│   ├── home/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services/
│   │   │   ├── nlp_processor.py
│   │   │   ├── chatgpt_client.py
│   │   │   └── keyword_parser.py
│   │   └── tests.py
│   ├── board/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── pagination.py
│   │   └── tests.py
│   ├── crawler/
│   │   ├── scrapers/
│   │   │   └── naver_scraper.py
│   │   ├── tasks.py
│   │   └── utils.py
│   └── recommendation/
│       ├── engine.py
│       ├── tasks.py
│       └── utils.py
├── static/
├── media/
├── templates/
│   ├── base.html
│   ├── user/
│   ├── home/
│   └── board/
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
└── manage.py
```

### 5.2 각 앱의 역할 및 기능

#### 5.2.1 User App
**주요 기능:**
- 사용자 인증 (회원가입, 로그인, 로그아웃)
- 프로필 관리
- 비밀번호 재설정
- 사용자 선호도 설정

**핵심 View 클래스:**
```python
class UserRegistrationView(CreateAPIView):
    """사용자 회원가입"""

class UserLoginView(ObtainAuthToken):
    """사용자 로그인"""

class UserProfileView(RetrieveUpdateAPIView):
    """사용자 프로필 조회/수정"""

class UserPreferenceView(RetrieveUpdateAPIView):
    """사용자 선호도 설정"""
```

#### 5.2.2 Home App
**주요 기능:**
- 자연어 검색 인터페이스 제공
- ChatGPT API 연동
- 검색 키워드 파싱
- 크롤링 작업 트리거

**핵심 Service 클래스:**
```python
class NLPProcessor:
    """자연어 처리 서비스"""
    def process_query(self, query_text: str) -> dict:
        # ChatGPT API 호출
        # 키워드 추출 및 검증
        # JSON 형식 반환

class SearchService:
    """검색 서비스"""
    def execute_search(self, keywords: dict) -> str:
        # Redis 캐시 확인
        # 크롤링 작업 실행
        # 결과 저장 및 Redis 키 반환
```

#### 5.2.3 Board App
**주요 기능:**
- 검색 결과 표시
- 추천 매물 표시
- 페이지네이션
- 상세 정보 조회

**핵심 View 클래스:**
```python
class PropertyListView(ListView):
    """매물 목록 표시"""

class PropertyDetailView(DetailView):
    """매물 상세 정보"""

class RecommendationView(ListView):
    """추천 매물 표시"""
```

---

## 6. API 설계

### 6.1 인증 API

#### 6.1.1 회원가입
```
POST /api/v1/auth/register/
Request:
{
    "username": "string",
    "email": "string",
    "password": "string",
    "password_confirm": "string",
    "phone": "string"
}
Response:
{
    "user_id": 1,
    "username": "string",
    "email": "string",
    "token": "jwt_token"
}
```

#### 6.1.2 로그인
```
POST /api/v1/auth/login/
Request:
{
    "username": "string",
    "password": "string"
}
Response:
{
    "token": "jwt_token",
    "user": {
        "user_id": 1,
        "username": "string",
        "email": "string"
    }
}
```

### 6.2 검색 API

#### 6.2.1 자연어 검색
```
POST /api/v1/search/nlp/
Headers: Authorization: Bearer {token}
Request:
{
    "query": "서울시 강남구 30평대 아파트 매매 5억 이하"
}
Response:
{
    "status": "success",
    "redis_key": "search:abc123def456",
    "parsed_keywords": {
        "address": "서울시 강남구",
        "building_type": "아파트",
        "transaction_type": "매매",
        "area_min": 25,
        "area_max": 35,
        "price_max": 500000000
    },
    "result_count": 45
}
```

#### 6.2.2 검색 결과 조회
```
GET /api/v1/search/results/{redis_key}/?page=1&size=30
Response:
{
    "total_count": 45,
    "page": 1,
    "size": 30,
    "recommendations": {
        "user_based": [...],  # 10개
        "global_based": [...]  # 10개
    },
    "search_results": [...],  # 10개 (첫 페이지)
    "next": "/api/v1/search/results/{redis_key}/?page=2&size=30"
}
```

### 6.3 추천 API

#### 6.3.1 사용자 맞춤 추천
```
GET /api/v1/recommendations/user/
Headers: Authorization: Bearer {token}
Response:
{
    "recommendations": [
        {
            "property_id": 1,
            "address": "서울시 강남구...",
            "price": 500000000,
            "area_pyeong": 32,
            "score": 0.95
        }
    ]
}
```

---

## 7. 프론트엔드 설계

### 7.1 페이지 구조

#### 7.1.1 홈 페이지
```html
<!-- templates/home/index.html -->
<div class="container">
    <div class="search-guide">
        <!-- 검색 가이드 및 예시 -->
    </div>
    <div class="search-box">
        <input type="text" id="nlp-search" placeholder="예: 서울 강남 30평 아파트">
        <button id="search-btn">검색</button>
    </div>
    <div class="loading-spinner" style="display:none;">
        <!-- 로딩 애니메이션 -->
    </div>
</div>
```

#### 7.1.2 결과 페이지 (Board)
```html
<!-- templates/board/results.html -->
<div class="container">
    <div class="recommendations-section">
        <h3>추천 매물</h3>
        <div class="row" id="recommendations">
            <!-- 추천 카드 20개 -->
        </div>
    </div>
    <div class="search-results-section">
        <h3>검색 결과</h3>
        <div class="row" id="search-results">
            <!-- 검색 결과 카드 30개 -->
        </div>
    </div>
    <nav aria-label="Page navigation">
        <ul class="pagination">
            <!-- 페이지네이션 -->
        </ul>
    </nav>
</div>
```

### 7.2 JavaScript 모듈

#### 7.2.1 검색 모듈
```javascript
// static/js/search.js
class SearchModule {
    constructor() {
        this.searchInput = document.getElementById('nlp-search');
        this.searchBtn = document.getElementById('search-btn');
        this.init();
    }

    init() {
        this.searchBtn.addEventListener('click', this.handleSearch.bind(this));
        this.checkLoginStatus();
    }

    async handleSearch() {
        const query = this.searchInput.value;
        if (!query) return;

        try {
            const response = await fetch('/api/v1/search/nlp/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getToken()}`
                },
                body: JSON.stringify({ query })
            });

            const data = await response.json();
            if (data.status === 'success') {
                window.location.href = `/board/results/${data.redis_key}`;
            }
        } catch (error) {
            console.error('Search error:', error);
        }
    }
}
```

---

## 8. 크롤링 시스템 설계

### 8.1 Playwright 크롤러 구현

```python
# apps/crawler/scrapers/naver_scraper.py
from playwright.sync_api import sync_playwright
import json
from typing import List, Dict

class NaverRealEstateScraper:
    def __init__(self):
        self.base_url = "https://land.naver.com"

    def search_properties(self, keywords: dict) -> List[Dict]:
        """네이버 부동산 검색 및 크롤링"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # 검색 URL 생성
            search_url = self._build_search_url(keywords)
            page.goto(search_url)

            # 검색 결과 대기
            page.wait_for_selector('.item_inner', timeout=10000)

            # 데이터 추출
            properties = self._extract_properties(page)

            browser.close()
            return properties

    def _build_search_url(self, keywords: dict) -> str:
        """검색 URL 생성"""
        # 키워드를 네이버 부동산 URL 파라미터로 변환
        params = {
            'cortarNo': self._get_region_code(keywords['address']),
            'tradTpCd': self._get_trade_type_code(keywords['transaction_type']),
            'space': f"{keywords.get('area_min', 0)}:{keywords.get('area_max', 999)}",
            'price': f"0:{keywords.get('price_max', 9999999)}",
        }
        # URL 생성 로직
        return f"{self.base_url}/search?{urlencode(params)}"

    def _extract_properties(self, page) -> List[Dict]:
        """페이지에서 매물 정보 추출"""
        properties = []
        items = page.query_selector_all('.item_inner')

        for item in items[:50]:  # 최대 50개
            property_data = {
                'address': item.query_selector('.item_title').inner_text(),
                'price': self._parse_price(item.query_selector('.price').inner_text()),
                'area': item.query_selector('.spec').inner_text(),
                'floor': item.query_selector('.floor').inner_text(),
                'description': item.query_selector('.info_desc').inner_text(),
                # ... 기타 필드
            }
            properties.append(property_data)

        return properties
```

### 8.2 크롤링 작업 스케줄링

```python
# apps/crawler/tasks.py
from celery import shared_task
from .scrapers.naver_scraper import NaverRealEstateScraper
import redis
import json
import hashlib

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

@shared_task
def crawl_properties(keywords: dict, user_id: int = None):
    """비동기 크롤링 작업"""
    # Redis 키 생성
    redis_key = generate_redis_key(keywords)

    # 캐시 확인
    cached_data = redis_client.get(redis_key)
    if cached_data:
        return redis_key

    # 크롤링 실행
    scraper = NaverRealEstateScraper()
    properties = scraper.search_properties(keywords)

    # Redis 저장 (TTL: 5분)
    redis_client.setex(
        redis_key,
        300,  # 5분
        json.dumps(properties)
    )

    # 사용자 검색 기록 업데이트
    if user_id:
        update_user_search_history(user_id, keywords)

    return redis_key

def generate_redis_key(keywords: dict) -> str:
    """검색 키워드 기반 Redis 키 생성"""
    key_string = json.dumps(keywords, sort_keys=True)
    return f"search:{hashlib.md5(key_string.encode()).hexdigest()}"
```

---

## 9. 추천 시스템 설계

### 9.1 추천 엔진 구현

```python
# apps/recommendation/engine.py
import redis
from typing import List, Dict

class RecommendationEngine:
    def __init__(self):
        self.redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

    def update_keyword_score(self, user_id: int, keywords: dict):
        """사용자 검색 키워드 스코어 업데이트"""
        for category, keyword in keywords.items():
            # 사용자별 키워드 스코어 업데이트
            user_key = f"user:{user_id}:keywords:{category}"
            self.redis_client.zincrby(user_key, 1, keyword)

            # 전체 사용자 키워드 스코어 업데이트
            global_key = f"global:keywords:{category}"
            self.redis_client.zincrby(global_key, 1, keyword)

    def get_user_recommendations(self, user_id: int) -> List[Dict]:
        """사용자 맞춤 추천 매물 조회"""
        # 사용자 선호 키워드 조합
        preferred_keywords = self._get_user_preferred_keywords(user_id)

        # 키워드 기반 크롤링 또는 캐시 조회
        recommendations = self._fetch_properties_by_keywords(preferred_keywords)

        return recommendations[:10]  # 최대 10개

    def get_global_recommendations(self) -> List[Dict]:
        """전체 사용자 기반 추천 매물 조회"""
        # 전체 인기 키워드 조합
        popular_keywords = self._get_popular_keywords()

        # 키워드 기반 크롤링 또는 캐시 조회
        recommendations = self._fetch_properties_by_keywords(popular_keywords)

        return recommendations[:10]  # 최대 10개

    def _get_user_preferred_keywords(self, user_id: int) -> dict:
        """사용자 선호 키워드 추출"""
        categories = ['address', 'transaction_type', 'building_type', 'price_range']
        preferred = {}

        for category in categories:
            key = f"user:{user_id}:keywords:{category}"
            # 상위 1개 키워드 추출
            top_keywords = self.redis_client.zrevrange(key, 0, 0, withscores=False)
            if top_keywords:
                preferred[category] = top_keywords[0].decode('utf-8')

        return preferred

    def _get_popular_keywords(self) -> dict:
        """전체 인기 키워드 추출"""
        categories = ['address', 'transaction_type', 'building_type', 'price_range']
        popular = {}

        for category in categories:
            key = f"global:keywords:{category}"
            # 상위 1개 키워드 추출
            top_keywords = self.redis_client.zrevrange(key, 0, 0, withscores=False)
            if top_keywords:
                popular[category] = top_keywords[0].decode('utf-8')

        return popular
```

### 9.2 추천 작업 스케줄링

```python
# apps/recommendation/tasks.py
from celery import shared_task
from celery.schedules import crontab
from .engine import RecommendationEngine
from apps.crawler.tasks import crawl_properties

@shared_task
def update_recommendations():
    """5분마다 추천 매물 업데이트"""
    engine = RecommendationEngine()

    # 전체 사용자 추천 업데이트
    global_keywords = engine._get_popular_keywords()
    if global_keywords:
        properties = crawl_properties(global_keywords)
        engine.redis_client.set(
            'global:recommendations',
            json.dumps(properties[:10])
        )

    # 각 활성 사용자별 추천 업데이트
    active_users = get_active_users()  # 최근 활동 사용자 조회

    for user_id in active_users:
        user_keywords = engine._get_user_preferred_keywords(user_id)
        if user_keywords:
            properties = crawl_properties(user_keywords, user_id)
            engine.redis_client.set(
                f'user:{user_id}:recommendations',
                json.dumps(properties[:10])
            )

# Celery Beat 스케줄 설정
CELERY_BEAT_SCHEDULE = {
    'update-recommendations': {
        'task': 'apps.recommendation.tasks.update_recommendations',
        'schedule': crontab(minute='*/5'),  # 5분마다
    },
}
```

---

## 10. 캐싱 전략

### 10.1 Redis 캐시 구조

#### 10.1.1 캐시 정책
- **검색 결과**: TTL 5분, 최대 50개 항목
- **추천 매물**: TTL 없음 (Celery로 5분마다 갱신)
- **세션 데이터**: TTL 30분
- **API 응답**: TTL 1분 (자주 변경되지 않는 데이터)

#### 10.1.2 캐시 관리자
```python
# apps/core/cache.py
import redis
import json
from typing import Any, Optional
import hashlib

class CacheManager:
    def __init__(self):
        self.redis_client = redis.StrictRedis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )

    def get_or_set(self, key: str, func, ttl: int = 300) -> Any:
        """캐시 조회 또는 설정"""
        # 캐시 조회
        cached_value = self.redis_client.get(key)
        if cached_value:
            return json.loads(cached_value)

        # 캐시 미스 시 함수 실행
        value = func()

        # 캐시 저장
        self.redis_client.setex(
            key,
            ttl,
            json.dumps(value)
        )

        return value

    def invalidate(self, pattern: str):
        """패턴 기반 캐시 무효화"""
        keys = self.redis_client.keys(pattern)
        if keys:
            self.redis_client.delete(*keys)

    def get_search_cache_key(self, keywords: dict) -> str:
        """검색 캐시 키 생성"""
        key_string = json.dumps(keywords, sort_keys=True)
        hash_value = hashlib.md5(key_string.encode()).hexdigest()
        return f"search:{hash_value}:results"
```

---

## 11. 비동기 작업 처리

### 11.1 Celery 설정

```python
# config/celery.py
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

app = Celery('real_estate')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat 스케줄
app.conf.beat_schedule = {
    'update-recommendations': {
        'task': 'apps.recommendation.tasks.update_recommendations',
        'schedule': crontab(minute='*/5'),
    },
    'cleanup-expired-cache': {
        'task': 'apps.core.tasks.cleanup_expired_cache',
        'schedule': crontab(hour=2, minute=0),  # 매일 새벽 2시
    },
    'update-property-database': {
        'task': 'apps.crawler.tasks.update_property_database',
        'schedule': crontab(hour='*/6'),  # 6시간마다
    },
}

# Celery 설정
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Seoul',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30분
    task_soft_time_limit=25 * 60,  # 25분
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
```

### 11.2 작업 큐 관리

```python
# apps/core/tasks.py
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_search_request(self, keywords: dict, user_id: int):
    """검색 요청 비동기 처리"""
    try:
        # 크롤링 실행
        from apps.crawler.tasks import crawl_properties
        redis_key = crawl_properties(keywords, user_id)

        # 추천 시스템 업데이트
        from apps.recommendation.engine import RecommendationEngine
        engine = RecommendationEngine()
        engine.update_keyword_score(user_id, keywords)

        return {'status': 'success', 'redis_key': redis_key}

    except Exception as exc:
        logger.error(f"Search request failed: {exc}")
        raise self.retry(exc=exc, countdown=60)  # 60초 후 재시도

@shared_task
def cleanup_expired_cache():
    """만료된 캐시 정리"""
    from apps.core.cache import CacheManager
    cache_manager = CacheManager()

    # 오래된 검색 결과 정리
    cache_manager.invalidate('search:*:results')

    # 오래된 세션 정리
    cache_manager.invalidate('session:*')

    logger.info("Expired cache cleaned up")
```

---

## 12. 보안 요구사항

### 12.1 인증 및 권한

#### 12.1.1 JWT 토큰 기반 인증
```python
# config/settings/base.py
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}
```

#### 12.1.2 권한 클래스
```python
# apps/core/permissions.py
from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """소유자만 수정 가능"""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user

class IsPremiumUser(permissions.BasePermission):
    """프리미엄 사용자만 접근 가능"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_premium
```

### 12.2 보안 설정

#### 12.2.1 CORS 설정
```python
# config/settings/base.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://yourdomain.com",
]

CORS_ALLOW_CREDENTIALS = True
```

#### 12.2.2 Rate Limiting
```python
# apps/core/throttles.py
from rest_framework.throttling import UserRateThrottle

class SearchRateThrottle(UserRateThrottle):
    scope = 'search'

    THROTTLE_RATES = {
        'search': '100/hour',  # 시간당 100회 검색 제한
    }

class PremiumSearchRateThrottle(UserRateThrottle):
    scope = 'premium_search'

    THROTTLE_RATES = {
        'premium_search': '1000/hour',  # 프리미엄 사용자는 시간당 1000회
    }
```

### 12.3 데이터 보호

#### 12.3.1 개인정보 암호화
```python
# apps/user/models.py
from django.contrib.auth.hashers import make_password
from cryptography.fernet import Fernet

class EncryptedField(models.TextField):
    """암호화된 필드"""
    def __init__(self, *args, **kwargs):
        self.cipher = Fernet(settings.ENCRYPTION_KEY)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        if value:
            return self.cipher.encrypt(value.encode()).decode()
        return value

    def from_db_value(self, value, expression, connection):
        if value:
            return self.cipher.decrypt(value.encode()).decode()
        return value
```

---

## 13. 개발 일정

### 13.1 Phase 1: 기초 설정 (1주차)
- [ ] 프로젝트 초기 설정
- [ ] Django 프로젝트 구조 생성
- [ ] PostgreSQL, Redis 설치 및 설정
- [ ] Docker 환경 구성
- [ ] 기본 모델 설계 및 마이그레이션

### 13.2 Phase 2: 사용자 시스템 (2주차)
- [ ] User App 개발
- [ ] JWT 인증 구현
- [ ] 회원가입/로그인 API
- [ ] 프론트엔드 로그인 화면
- [ ] 사용자 프로필 관리

### 13.3 Phase 3: 자연어 처리 (3-4주차)
- [ ] OpenAI API 연동
- [ ] NLP 처리 서비스 구현
- [ ] 키워드 파서 개발
- [ ] 검색 인터페이스 UI
- [ ] 검색 API 엔드포인트

### 13.4 Phase 4: 크롤링 시스템 (5-6주차)
- [ ] Playwright 크롤러 구현
- [ ] 네이버 부동산 스크래퍼
- [ ] Celery 비동기 처리
- [ ] Redis 캐싱 구현
- [ ] 크롤링 데이터 저장

### 13.5 Phase 5: 추천 시스템 (7-8주차)
- [ ] 추천 엔진 개발
- [ ] 사용자 선호도 분석
- [ ] Celery Beat 스케줄러
- [ ] 추천 매물 캐싱
- [ ] 추천 API 구현

### 13.6 Phase 6: 프론트엔드 (9-10주차)
- [ ] Bootstrap 5 레이아웃
- [ ] 검색 결과 카드 UI
- [ ] 페이지네이션 구현
- [ ] 반응형 디자인
- [ ] JavaScript 모듈 개발

### 13.7 Phase 7: 테스트 및 최적화 (11-12주차)
- [ ] 단위 테스트 작성
- [ ] 통합 테스트
- [ ] 성능 최적화
- [ ] 보안 점검
- [ ] 버그 수정

---

## 14. 테스트 계획

### 14.1 단위 테스트

```python
# apps/home/tests/test_nlp_processor.py
from django.test import TestCase
from apps.home.services.nlp_processor import NLPProcessor

class NLPProcessorTestCase(TestCase):
    def setUp(self):
        self.processor = NLPProcessor()

    def test_process_valid_query(self):
        query = "서울시 강남구 30평 아파트 매매"
        result = self.processor.process_query(query)

        self.assertEqual(result['address'], '서울시 강남구')
        self.assertEqual(result['building_type'], '아파트')
        self.assertEqual(result['transaction_type'], '매매')

    def test_missing_address_error(self):
        query = "30평 아파트 매매"
        with self.assertRaises(ValueError):
            self.processor.process_query(query)
```

### 14.2 통합 테스트

```python
# apps/board/tests/test_integration.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

class SearchIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_full_search_flow(self):
        # 로그인
        self.client.login(username='testuser', password='testpass123')

        # 검색 요청
        response = self.client.post('/api/v1/search/nlp/', {
            'query': '서울시 강남구 아파트'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('redis_key', response.json())

        # 결과 조회
        redis_key = response.json()['redis_key']
        response = self.client.get(f'/api/v1/search/results/{redis_key}/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('search_results', response.json())
```

### 14.3 성능 테스트

```python
# tests/performance/test_load.py
import locust
from locust import HttpUser, task, between

class RealEstateUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # 로그인
        response = self.client.post("/api/v1/auth/login/", {
            "username": "testuser",
            "password": "testpass123"
        })
        self.token = response.json()['token']

    @task(3)
    def search_properties(self):
        headers = {'Authorization': f'Bearer {self.token}'}
        self.client.post("/api/v1/search/nlp/",
            json={"query": "서울시 강남구 아파트"},
            headers=headers
        )

    @task(1)
    def view_recommendations(self):
        headers = {'Authorization': f'Bearer {self.token}'}
        self.client.get("/api/v1/recommendations/user/",
            headers=headers
        )
```

---

## 15. 배포 계획

### 15.1 Docker 구성

```dockerfile
# docker/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements/production.txt .
RUN pip install --no-cache-dir -r production.txt

# Playwright 설치
RUN playwright install chromium
RUN playwright install-deps

# 애플리케이션 코드 복사
COPY . .

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# Gunicorn 실행
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "config.wsgi:application"]
```

### 15.2 Docker Compose

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  db:
    image: mysql:8.0
    volumes:
      - mysql_data:/var/lib/mysql
    environment:
      - MYSQL_DATABASE=ai_test_prj
      - MYSQL_USER=ai_admin
      - MYSQL_PASSWORD=test1324
      - MYSQL_ROOT_PASSWORD=rootpassword
    ports:
      - "3306:3306"
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
      - static_volume:/app/static
      - media_volume:/app/media
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=mysql://ai_admin:test1324@db:3306/ai_test_prj
      - REDIS_URL=redis://redis:6379/0

  celery:
    build: .
    command: celery -A config worker -l info
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=mysql://ai_admin:test1324@db:3306/ai_test_prj
      - REDIS_URL=redis://redis:6379/0

  celery-beat:
    build: .
    command: celery -A config beat -l info
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=mysql://ai_admin:test1324@db:3306/ai_test_prj
      - REDIS_URL=redis://redis:6379/0

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/static
      - media_volume:/media
    ports:
      - "80:80"
    depends_on:
      - web

volumes:
  mysql_data:
  redis_data:
  static_volume:
  media_volume:
```

### 15.3 CI/CD 파이프라인

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    - name: Install dependencies
      run: |
        pip install -r requirements/testing.txt
    - name: Run tests
      run: |
        python manage.py test

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Deploy to server
      uses: appleboy/ssh-action@master
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /app
          git pull origin main
          docker-compose down
          docker-compose up -d --build
          docker-compose exec web python manage.py migrate
```

### 15.4 모니터링 설정

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'django'
    static_configs:
      - targets: ['web:8000']
    metrics_path: '/metrics'

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'postgres'
    static_configs:
      - targets: ['db:5432']
```

---

## 16. 유지보수 계획

### 16.1 로깅 전략
- Django 로깅: INFO 레벨 이상
- Celery 로깅: WARNING 레벨 이상
- 크롤링 로깅: DEBUG 레벨 (개발), INFO 레벨 (운영)

### 16.2 백업 전략
- MySQL: 일일 전체 백업, 시간별 증분 백업
- Redis: 시간별 RDB 스냅샷
- 미디어 파일: 일일 S3 동기화

### 16.3 모니터링 지표
- API 응답 시간
- 크롤링 성공률
- Redis 히트율
- Celery 작업 대기열 크기
- 시스템 리소스 사용률

---

## 17. 예상 문제점 및 해결 방안

### 17.1 크롤링 차단
**문제**: 네이버 부동산 크롤링 차단
**해결**:
- User-Agent 로테이션
- IP 프록시 풀 사용
- 요청 간격 랜덤화
- Playwright stealth 모드

### 17.2 대용량 트래픽
**문제**: 동시 접속자 증가 시 성능 저하
**해결**:
- 로드 밸런서 구성
- 데이터베이스 읽기 전용 복제본
- CDN 활용
- 수평적 확장 (Kubernetes)

### 17.3 캐시 무효화
**문제**: 오래된 캐시 데이터 제공
**해결**:
- TTL 기반 자동 만료
- 이벤트 기반 캐시 무효화
- 버전 기반 캐시 키

---

## 18. 확장 계획

### 18.1 추가 기능
- 실거래가 차트 시각화
- 알림 시스템 (가격 변동, 신규 매물)
- 매물 비교 기능
- VR 매물 투어
- 챗봇 상담 시스템

### 18.2 기술적 개선
- GraphQL API 도입
- 마이크로서비스 아키텍처 전환
- 머신러닝 기반 가격 예측
- ElasticSearch 도입 (전문 검색)
- WebSocket 실시간 업데이트

---

## 19. 성공 지표 (KPI)

### 19.1 기술 지표
- API 평균 응답 시간 < 200ms
- 크롤링 성공률 > 95%
- 시스템 가용성 > 99.9%
- 캐시 히트율 > 80%

### 19.2 비즈니스 지표
- 월간 활성 사용자 (MAU)
- 평균 검색 세션 시간
- 추천 매물 클릭률
- 사용자 재방문율

---

## 20. 라이선스 및 법적 고려사항

### 20.1 오픈소스 라이선스
- Django: BSD License
- PostgreSQL: PostgreSQL License
- Redis: BSD License
- Playwright: Apache 2.0

### 20.2 법적 준수사항
- 개인정보보호법 준수
- 전자상거래법 준수
- 저작권법 준수 (크롤링 데이터)
- 서비스 이용약관 작성

---

이 명세서는 프로젝트 진행 상황에 따라 지속적으로 업데이트되어야 합니다.