# Home App - TASKING.md

이 문서는 AI 기반 자연어 질의형 부동산 매물 추천 서비스의 `home` 앱 개발 작업을 정의합니다.

---

## 핵심 역할

Home App은 다음 핵심 기능을 담당합니다:

1. **홈페이지 방문 및 검색 시작** - ChatGPT 웹 인터페이스와 유사한 중앙 배치 검색 박스
2. **로그인 인증 및 권한 확인** - JWT 토큰 기반 인증
3. **자연어 처리 및 키워드 추출** - OpenAI ChatGPT API 연동
4. **네이버 부동산 크롤링 및 캐싱** - Playwright 기반 크롤링, Redis 캐싱

---

## 개발 작업 목록

### 1. 환경 설정 및 기본 구성

- [ ] **환경 변수 설정**: `.env` 파일에 OpenAI API 키 및 토큰 절약 설정 추가
  ```env
  OPENAI_API_KEY=your_openai_api_key_here
  OPENAI_MODEL=gpt-4o-mini
  OPENAI_MAX_TOKENS=150
  OPENAI_TEMPERATURE=0.1
  ```
- [ ] **의존성 패키지 설치**: 필요 패키지 확인 및 설치 (완료)
  - `openai` (ChatGPT API)
  - `playwright` (크롤링)
  - `redis` (캐싱)
  - `mysqlclient` (MySQL 연결)
  - `django-celery-beat` (Celery Beat 스케줄러)

### 2. 모델 설계

- [ ] **SearchHistory 모델**: 사용자 검색 기록 저장
  ```python
  class SearchHistory(models.Model):
      user = models.ForeignKey(User, on_delete=models.CASCADE)
      query_text = models.TextField()  # 원본 자연어 쿼리
      parsed_keywords = models.JSONField()  # 파싱된 키워드
      search_date = models.DateTimeField(auto_now_add=True)
      result_count = models.IntegerField(default=0)
      redis_key = models.CharField(max_length=255)
  ```

- [ ] **데이터베이스 마이그레이션**: 모델 변경사항 적용

### 3. 뷰 구현

#### 3.1 메인 뷰
- [ ] **HomeView**: 메인 랜딩 페이지
  - ChatGPT 유사 검색 인터페이스
  - 상단 가이드 및 예시 텍스트
  - 로그인 상태 확인

#### 3.2 API 뷰
- [ ] **SearchAPIView**: 자연어 검색 처리 API
  - POST 메서드
  - 로그인 필수 (`@login_required`)
  - ChatGPT API 호출
  - 키워드 추출 및 검증
  - 크롤링 작업 트리거
  - Redis 키 반환

### 4. Utils 클래스 연동

- [ ] **ChatGPT API 연동**: `utils.ai.ChatGPTClient` 클래스 구현
  ```python
  class ChatGPTClient:
      def extract_keywords(self, query_text: str) -> dict:
          # 토큰 절약 프롬프트 사용 (max_tokens=150, temperature=0.1)
          # 필수 키워드 추출: address, transaction_type, building_type, price_range, area_range
          # JSON 형식으로 반환

      def validate_response(self, response: dict) -> bool:
          # 필수 키워드 존재 확인
          # 데이터 타입 검증
  ```

- [ ] **키워드 파싱**: `utils.parsers.KeywordParser` 클래스 구현
  ```python
  class KeywordParser:
      def validate_required_fields(self, keywords: dict) -> bool:
          # address 필수 검증 (시·도 + 시·군·구)
          # transaction_type, building_type 필수 검증

      def apply_defaults(self, keywords: dict) -> dict:
          # price_range 기본값: {"min": 0, "max": 999999}
          # area_range 기본값: {"min": 0, "max": 999}
          # 기타 선택 항목 기본값 적용
  ```

- [ ] **크롤링 실행**: `utils.crawlers.NaverRealEstateCrawler` 클래스 구현
  ```python
  class NaverRealEstateCrawler:
      def crawl_properties(self, keywords: dict) -> list:
          # pre-test/gemini-naver.py 코드 활용
          # 크롤링 결과를 영문 컬럼명으로 변환
          # address 정보를 키워드에서 추가

      def convert_to_english_columns(self, raw_data: list) -> list:
          # 한글 컬럼명 → 영문 컬럼명 변환
          # tags 문자열 → 리스트 변환
  ```

### 5. Redis 캐시 연동

- [ ] **캐시 관리**: `utils.cache.RedisCache` 사용
  - 검색 결과 캐시 (TTL: 5분)
  - 키워드 기반 Redis 키 생성
  - 캐시 조회 및 저장 로직

- [ ] **추천 시스템 연동**: `utils.recommendations.RecommendationEngine` 사용
  - Redis Sorted Sets 활용
  - 사용자별 키워드 스코어 업데이트
  - 전체 사용자 키워드 스코어 업데이트
  - **Redis 장애 대비**: Database 백업 시스템 연동

---

## 크롤링 결과 형식 및 데이터 구조

### 크롤링 원본 데이터 (CSV 형식)
```csv
집주인,거래타입,가격,건물 종류,평수,층정보,집방향,tag,갱신일
수원한일타운,전세,390000000,아파트,25.64,8/23층,남동향,"25년이상, 융자금없는, 올수리",2025-09-09
화서역파크푸르지오(주상복합),매매,1250000000,아파트,25.64,25/46층,남서향,"10년이내, 대단지, 방세개, 화장실두개",2025-09-16
```

### 영문 컬럼 매핑 (Database/Redis 저장용)
```python
COLUMN_MAPPING = {
    '집주인': 'owner_name',        # 건물/단지명
    '거래타입': 'transaction_type', # 매매/전세/월세
    '가격': 'price',               # 가격 (정수)
    '건물 종류': 'building_type',   # 아파트/오피스텔/빌라/단독주택
    '평수': 'area_size',           # 평수 (float)
    '층정보': 'floor_info',        # 층수 정보 (예: 8/23층)
    '집방향': 'direction',         # 향 (남향/남동향 등)
    'tag': 'tags',                 # 태그 (리스트)
    '갱신일': 'updated_date'       # 갱신일자
}
```

### 크롤링 결과 JSON 구조
```python
{
    "address": "서울시 강남구",  # 서버에서 별도 관리 (크롤링 키워드에서 추출)
    "owner_name": "수원한일타운",
    "transaction_type": "전세",
    "price": 390000000,
    "building_type": "아파트",
    "area_size": 25.64,
    "floor_info": "8/23층",
    "direction": "남동향",
    "tags": ["25년이상", "융자금없는", "올수리"],
    "updated_date": "2025-09-09"
}
```

## ChatGPT 키워드 추출 구조

### 필수 추출 항목
```python
REQUIRED_KEYWORDS = {
    "address": "주소 (시/구/동 단위)",
    "transaction_type": "거래타입 (매매/전세/월세)",
    "building_type": "건물타입 (아파트/오피스텔/빌라/단독주택)",
    "price_range": "가격 범위 (단위: 만원)",
    "area_range": "평수 범위"
}
```

### ChatGPT 출력 형식
```json
{
  "address": "서울시 강남구",
  "transaction_type": "매매",
  "building_type": "아파트",
  "price_range": {"min": 80000, "max": 120000},
  "area_range": {"min": 25, "max": 35},
  "direction": "남향",
  "floor_preference": "중층",
  "tags": ["신축", "역세권"]
}
```

### 토큰 절약 프롬프트 설계
```python
EXTRACT_PROMPT = """
부동산 검색어에서 키워드를 추출해 JSON으로 반환하세요.

필수항목: address, transaction_type, building_type, price_range, area_range
선택항목: direction, floor_preference, tags

입력: "{query}"
출력: JSON만 (설명 없이)
"""
```

### 6. URL 설정

- [ ] **URL 구성**: `home/urls.py`
  ```python
  urlpatterns = [
      path('', HomeView.as_view(), name='home'),
      path('api/search/', SearchAPIView.as_view(), name='api_search'),
  ]
  ```

### 7. 템플릿 구현

- [ ] **home.html**: 메인 페이지 템플릿
  - Bootstrap 5 기반 반응형 디자인
  - 중앙 배치 검색 박스
  - 상단 가이드 텍스트
  - 로딩 상태 표시

- [ ] **JavaScript 구현**: `static/js/home.js`
  - 검색 폼 처리
  - API 호출 및 응답 처리
  - 로그인 상태 확인
  - Board 앱으로 리다이렉트

### 8. 테스트 구현

#### 8.1 단위 테스트
- [ ] **test_models.py**: 모델 테스트
  - SearchHistory 모델 생성 테스트

- [ ] **test_utils_integration.py**: Utils 클래스 연동 테스트
  - ChatGPT API 클라이언트 테스트 (실제 API 호출)
  - 키워드 파서 테스트
  - 크롤링 서비스 테스트
  - Redis 캐시 연동 테스트

- [ ] **test_views.py**: 뷰 테스트
  - HomeView 접근 테스트
  - SearchAPIView 테스트 (실제 ChatGPT API 사용)

#### 8.2 통합 테스트
- [ ] **test_search_flow.py**: 전체 검색 플로우 테스트
  - 자연어 입력 → ChatGPTClient → KeywordParser → NaverRealEstateCrawler → RedisCache
  - Utils 클래스 간 연동 테스트

## 토큰 절약 최적화 방법

### OpenAI API 토큰 절약 설정 (완료)
```env
OPENAI_MODEL=gpt-4o-mini         # 더 저렴한 모델 사용
OPENAI_MAX_TOKENS=150            # 응답 토큰 제한
OPENAI_TEMPERATURE=0.1           # 일관된 응답을 위한 낮은 온도
```

### 프롬프트 최적화 전략
- [ ] **간결한 프롬프트**: 불필요한 설명문 제거
- [ ] **JSON Only 응답**: "JSON만 반환, 설명 없이" 명시
- [ ] **키워드 제한**: 필수 5개 + 선택 3개로 제한
- [ ] **예시 제거**: 프롬프트에서 긴 예시 문구 제거

### 실제 적용 프롬프트 예시
```python
# Bad (토큰 낭비)
PROMPT = """
당신은 부동산 전문가입니다. 사용자의 자연어 검색어를 분석하여
다음과 같은 구조화된 정보를 추출해주세요.
각 항목에 대해 자세히 설명하겠습니다...
(긴 설명이 계속됨)

예시:
- 입력: "강남에서 30평 아파트 전세 5억 이하"
- 출력: {...}

사용자 입력: "{query}"
"""

# Good (토큰 절약)
PROMPT = """
부동산 검색어에서 키워드 추출, JSON만 반환:
필수: address, transaction_type, building_type, price_range, area_range
선택: direction, floor_preference, tags

입력: "{query}"
"""
```

### API 호출 최적화
- [ ] **캐싱 활용**: 동일 쿼리 24시간 캐싱
- [ ] **배치 처리**: 가능한 경우 여러 쿼리 한번에 처리
- [ ] **에러 최소화**: 입력 검증으로 실패한 API 호출 줄이기

---

## Celery Beat 실행 및 Redis 백업 시스템

### Celery Beat 실행 방법
```bash
# 1. Django 개발 서버 실행
uv run python manage.py runserver

# 2. Celery Worker 실행 (별도 터미널)
uv run celery -A config worker -l info

# 3. Celery Beat 실행 (별도 터미널)
uv run celery -A config beat -l info
```

### Redis 장애 대비 Database 백업 시스템

#### 백업 대상 데이터
- **KeywordScore 모델**: Redis Sorted Sets의 키워드 스코어 데이터
- **RecommendationCache 모델**: 추천 매물 캐시 데이터

#### 자동 백업 작업 (Celery Beat)
```python
# 10분마다 자동 실행
CELERY_BEAT_SCHEDULE = {
    'backup-redis-to-database': {
        'task': 'utils.tasks.backup_redis_scores_to_database',
        'schedule': 600.0,  # 10분
    },
}
```

#### Django 재시작 시 자동 웜업
```python
# config/apps.py 또는 management command로 구현
class ConfigConfig(AppConfig):
    def ready(self):
        # Django 시작 시 Redis 데이터 복원
        from utils.models import KeywordScore
        KeywordScore.restore_to_redis(redis_client)
```

### Utils 클래스 확장 - 백업 시스템
- [ ] **KeywordScore 모델**: `utils.models.KeywordScore`
  - Redis Sorted Sets 데이터의 Database 백업
  - 사용자별/전체 키워드 스코어 저장
  - Django 재시작 시 Redis로 자동 복원

- [ ] **RecommendationCache 모델**: `utils.models.RecommendationCache`
  - 추천 매물 캐시의 Database 백업
  - JSON 형태로 매물 데이터 저장

- [ ] **백업 작업**: `utils.tasks.backup_redis_scores_to_database`
  - 10분마다 자동 실행
  - Redis → Database 동기화
  - 중복 데이터 방지 (upsert 로직)

---

## 구현 우선순위

### Phase 1: 핵심 기능 구현
1. 환경 설정 및 기본 모델
2. ChatGPT API 연동
3. 기본 검색 플로우

### Phase 2: 크롤링 및 캐싱
1. 네이버 부동산 크롤링 구현
2. Redis 캐싱 시스템
3. 추천 시스템 스코어링

### Phase 3: UI 및 테스트
1. 프론트엔드 구현
2. 테스트 케이스 작성
3. 통합 테스트

---

## 성공 기준

- ChatGPT API 연동 성공
- 자연어 → 키워드 추출 정확도 90% 이상
- 크롤링 성공률 95% 이상
- Redis 캐시 적중률 80% 이상
- API 응답 시간 3초 이내
- 테스트 커버리지 80% 이상

---

## 기술 스택

- **Backend**: Django, Django REST Framework
- **Utils**: 공통 유틸리티 클래스 (AI, 크롤링, 캐시, 파싱, 추천)
- **AI/ML**: OpenAI ChatGPT API
- **Crawling**: Playwright (pre-test/gemini-naver.py 활용)
- **Cache**: Redis
- **Database**: MySQL
- **Frontend**: Bootstrap 5, Vanilla JavaScript
- **Testing**: pytest

---

*이 문서는 개발 진행에 따라 지속적으로 업데이트되며, 완료된 작업은 HISTORY.md에 기록됩니다.*