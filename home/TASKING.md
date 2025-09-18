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

- [x] **환경 변수 설정**: `.env` 파일에 OpenAI API 키 및 토큰 절약 설정 추가
  ```env
  OPENAI_API_KEY=your_openai_api_key_here
  OPENAI_MODEL=gpt-4o-mini
  OPENAI_MAX_TOKENS=150
  OPENAI_TEMPERATURE=0.1
  ```
- [x] **의존성 패키지 설치**: 필요 패키지 확인 및 설치 (완료)
  - `openai` (ChatGPT API)
  - `playwright` (크롤링)
  - `redis` (캐싱)
  - `mysqlclient` (MySQL 연결)
  - `django-celery-beat` (Celery Beat 스케줄러)

### 2. 모델 설계

- [x] **SearchHistory 모델**: 사용자 검색 기록 저장
  ```python
  class SearchHistory(models.Model):
      user = models.ForeignKey(User, on_delete=models.CASCADE)
      query_text = models.TextField()  # 원본 자연어 쿼리
      parsed_keywords = models.JSONField()  # 파싱된 키워드
      search_date = models.DateTimeField(auto_now_add=True)
      result_count = models.IntegerField(default=0)
      redis_key = models.CharField(max_length=255)
  ```

- [x] **데이터베이스 마이그레이션**: 모델 변경사항 적용

### 3. 뷰 구현

#### 3.1 메인 뷰
- [x] **HomeView**: 메인 랜딩 페이지
  - ChatGPT 유사 검색 인터페이스
  - 상단 가이드 및 예시 텍스트
  - 로그인 상태 확인

#### 3.2 API 뷰
- [x] **SearchAPIView**: 자연어 검색 처리 API
  - POST 메서드
  - 로그인 필수 (`@login_required`)
  - ChatGPT API 호출
  - 키워드 추출 및 검증
  - 크롤링 작업 트리거
  - 크롤링 결과를 Redis에 직렬화 저장 (TTL: 5분)
  - Redis 키 (`search:{hash}:results`) JSON 응답으로 반환
  - 추천 시스템 키워드 스코어 업데이트

### 4. Utils 클래스 연동

- [x] **ChatGPT API 연동**: `home.services.keyword_extraction.ChatGPTKeywordExtractor` 실제 API 클래스 구현 완료
  ```python
  class ChatGPTKeywordExtractor:
      def extract_keywords(self, query_text: str) -> dict:
          # POC 코드 기반 실제 ChatGPT API 호출
          # 필수 키워드 추출: address, transaction_type, building_type
          # 선택 키워드: deposit, monthly_rent, area_range
          # JSON 형식으로 반환

      def validate_response(self, response: dict) -> dict:
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

- [x] **크롤링 실행**: `home.services.crawler.NaverRealEstateHeadlessCrawler` 헤드리스 크롤링 클래스 구현 완료
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

- [x] **캐시 관리**: `home.services.redis_handler.RedisUserDataHandler` 사용자별 복합키 Redis 저장 구현 완료
  - 검색 결과 캐시 (TTL: 5분)
  - 키워드 기반 Redis 키 생성
  - 캐시 조회 및 저장 로직

- [x] **크롤링 결과 Redis 저장 시스템**: 새로운 Redis 저장 구조 구현
  - 크롤링 완료 후 JSON 직렬화하여 Redis 저장 (TTL: 5분)
  - Redis 키 생성: `search:{hash}:results` 형태
  - 저장 데이터: 크롤링된 매물 리스트 (영문 컬럼명 적용)
  - API 응답: JSON 형태로 Redis 키 반환

- [x] **추천 시스템 연동**: `utils.recommendations.RecommendationEngine` 사용
  - Redis Sorted Sets 활용 (TTL: 1시간)
  - 사용자별 키워드 스코어 업데이트
  - 전체 사용자 키워드 스코어 업데이트
  - 키워드 스코어 기반 추천 매물 조회
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

- [x] **test_ai_dummy.py, test_redis_handler.py**: Utils 클래스 연동 테스트 완료
  - ChatGPT 더미 클라이언트 테스트 (42개 테스트 케이스 통과)
  - Redis 사용자 데이터 핸들러 테스트 (직렬화/역직렬화 일관성 검증)
  - 복합키 생성 및 데이터 격리 테스트
  - 모든 테스트 케이스 성공적으로 통과

- [ ] **test_views.py**: 뷰 테스트
  - HomeView 접근 테스트
  - SearchAPIView 테스트 (실제 ChatGPT API 사용)

- [ ] **test_redis_storage.py**: Redis 저장 시스템 테스트
  - 크롤링 결과 Redis 직렬화/역직렬화 테스트
  - TTL 5분 설정 확인
  - 키 생성 로직 검증 (`search:{hash}:results`)

#### 8.2 통합 테스트
- [ ] **test_search_flow.py**: 전체 검색 플로우 테스트
  - 자연어 입력 → ChatGPTClient → NaverRealEstateCrawler → Redis 저장 → Board 연동
  - 추천 시스템 스코어 업데이트 플로우 테스트

- [ ] **test_recommendation_system.py**: 추천 시스템 테스트
  - Redis Sorted Sets 키워드 스코어 저장/조회
  - TTL 1시간 설정 확인
  - 사용자별/전체 추천 매물 조회

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

---

## 최근 완료된 작업 (2025-09-17)

### 구현 완료 항목
1. **ChatGPT API 실제 구현** (`home/services/keyword_extraction.py`)
   - `pre-test/poc_chatgpt_api.py` 기반 실제 ChatGPT API 연동
   - POC 검증된 프롬프트 및 응답 구조 적용
   - 필수 키워드 추출: address, transaction_type, building_type
   - 선택 키워드: deposit, monthly_rent, area_range

2. **헤드리스 크롤링 구현** (`home/services/crawler.py`)
   - `pre-test/gemini-naver.py` 기반 Playwright 헤드리스 크롤링
   - 실제 사용자와 동일한 설정 (cookies, user-agent)
   - 매물 데이터 파싱 및 JSON 변환 로직

3. **Redis 사용자 데이터 핸들러** (`home/services/redis_handler.py`)
   - 복합키 패턴: `{user_id}:latest,keyword`, `{user_id}:latest,crawling`
   - JSON 직렬화/역직렬화 with 일관성 검증
   - 크롤링 데이터 누적 저장 기능

4. **포괄적 테스트 케이스** (`home/tests/`)
   - `test_ai_dummy.py`: 더미 클라이언트 패턴 매칭 테스트 (19개 통과)
   - `test_keyword_extraction.py`: 실제 ChatGPT API 키워드 추출 테스트 (1개 통과)
   - `test_redis_handler.py`: Redis 직렬화/역직렬화 일관성 테스트 (22개 통과)
   - **총 42개 테스트 케이스 모두 성공적으로 통과**

### 주요 기술적 특징
- **로깅 전략**: 복합키 정보는 로그 출력, 실제 데이터는 보안상 비출력
- **에러 핸들링**: JSON 직렬화 오류 수정 (`TypeError` vs `JSONDecodeError`)
- **데이터 일관성**: 직렬화 전후 데이터 동일성 검증
- **헤드리스 최적화**: 실제 브라우저 환경과 동일한 설정으로 감지 회피

---

## 최신 업데이트 (2025-09-17)

### ChatGPT API 상세 조건 구현 완료

**변경된 파일들:**
1. `home/services/keyword_extraction.py` - ChatGPT API 프롬프트 및 검증 로직 업데이트
2. `home/services/parsers.py` - 새로운 응답 형식 처리를 위한 변환 로직 추가
3. `home/tests/test_chatgpt_integration.py` - 새로운 형식에 맞춘 테스트 케이스 업데이트

**구현된 6가지 상세 조건:**

1. **address (필수)**: 최소한 "시·도 + 시·군·구" 형태 구성
   - 예: "서울시 강남구", "경기도 수원시", "부산시 해운대구"
   - 시·도만 있고 시·군·구가 없으면 에러 반환

2. **transaction_type (필수)**: 배열 형태로 반환
   - 4가지 거래 유형: ["매매"], ["전세"], ["월세"], ["단기임대"]
   - 최소 1개 이상 추출 필수

3. **building_type (필수)**: 배열 형태로 반환
   - 18가지 건물 유형: 아파트, 오피스텔, 빌라, 아파트분양권, 오피스텔분양권, 재건축, 전원주택, 단독/다가구, 상가주택, 한옥주택, 재개발, 원룸, 상가, 사무실, 공장/창고, 건물, 토지, 지식산업센터
   - 최소 1개 이상 추출 필수

4. **deposit (선택)**: 정수 배열 또는 null
   - 형태: [최대값] 또는 [최소값, 최대값]
   - 예: [50000000], [10000000, 50000000]

5. **monthly_rent (선택)**: 정수 배열 또는 null
   - 형태: [최대값] 또는 [최소값, 최대값]
   - 예: [500000], [300000, 800000]

6. **area_range (선택)**: 문자열 또는 null
   - 8가지 면적 범위: "~10평", "10평대", "20평대", "30평대", "40평대", "50평대", "60평대", "70~"

**주요 개선사항:**
- **상세 유효성 검증**: 6가지 조건에 맞춘 엄격한 검증 로직 구현
- **형식 변환 로직**: 새로운 배열 형식을 기존 레거시 형식으로 변환하는 호환성 레이어 추가
- **포괄적 문서화**: 모든 조건과 JSON 예시를 주석으로 개발자 참고용 제공
- **테스트 검증 완료**: 업데이트된 테스트 케이스로 실제 ChatGPT API 호출 검증 (PASSED)

**테스트 결과:**
- ChatGPT API 응답이 정확한 배열 형식으로 반환됨 확인
- 파서가 새로운 형식을 기존 시스템과 호환되도록 변환함 확인
- 로그 출력 형식이 POC와 일치함 확인

---

## 최신 업데이트 (2025-09-17) - 간소화된 키워드 추출 플로우

### ChatGPT API 직접 사용으로 플로우 간소화 완료

**변경된 파일들:**
1. `home/services/keyword_extraction.py` - 불필요한 변환 로직 제거, ChatGPT 응답 직접 반환
2. `home/views/__init__.py` - KeywordParser 사용 제거, ChatGPT 응답 직접 활용
3. `home/tests/test_chatgpt_integration.py` - 간소화된 플로우에 맞춘 테스트 케이스 업데이트

**주요 변경사항:**

**1. 기존 플로우 (제거됨):**
```
자연어 쿼리 → ChatGPT API → raw_keywords → KeywordParser.parse() → parsed_keywords
```

**2. 새로운 간소화된 플로우:**
```
자연어 쿼리 → ChatGPT API → extracted_keywords (최종 결과)
```

**3. 구체적 개선점:**
- **불필요한 변환 제거**: KeywordParser의 legacy 변환 로직 제거
- **직접적인 API 활용**: ChatGPT 응답을 바로 최종 결과로 사용
- **단순화된 워크플로우**: SearchAPIView에서 Step 2 (파싱) 단계 제거
- **일관된 데이터 형식**: ChatGPT가 반환하는 배열 형식을 그대로 활용

**4. 테스트 결과:**
- 간소화된 테스트 케이스 실행 성공 (PASSED)
- ChatGPT API 응답 형식 검증 완료
- 로그 출력에서 불필요한 변환 과정 제거 확인

**5. 성능 향상:**
- 키워드 추출 과정에서 중간 변환 단계 제거로 처리 속도 향상
- 메모리 사용량 감소 (중간 변환 객체 불필요)
- 코드 복잡성 감소로 유지보수성 향상

이제 ChatGPT API로부터 반환받은 JSON이 바로 최종 추출 결과로 사용되며, 이후 추가적인 파싱이나 변환 작업은 수행되지 않습니다.

---

## 최신 업데이트 (2025-09-17) - 보증금/월세 최소/최대값 제한

### ChatGPT API 보증금/월세 배열 최적화 완료

**변경된 파일:**
- `home/services/keyword_extraction.py` - 보증금/월세 최소/최대값 제한 및 검증 로직 추가

**주요 개선사항:**

**1. 보증금(deposit) 배열 제한:**
- 여러 개의 값이 추출된 경우, 반드시 최소값과 최대값만 반환
- 형태: `[최대값]` 또는 `[최소값, 최대값]`
- 예: `[50000000]` (5천만원 이하), `[10000000, 50000000]` (1천만원~5천만원)

**2. 월세(monthly_rent) 배열 제한:**
- 여러 개의 값이 추출된 경우, 반드시 최소값과 최대값만 반환
- 형태: `[최대값]` 또는 `[최소값, 최대값]`
- 예: `[500000]` (50만원 이하), `[300000, 800000]` (30만원~80만원)

**3. 검증 로직 강화:**
- 배열 요소 개수 제한: 최대 2개 (1개 또는 2개만 허용)
- 2개 요소인 경우 순서 검증: 첫 번째 값(최소값) ≤ 두 번째 값(최대값)
- 모든 값은 0 이상의 정수여야 함

**4. ChatGPT 프롬프트 업데이트:**
```
중요: deposit과 monthly_rent는 배열에 최대 2개 요소만 허용됩니다.
- 단일 값: [최대값] 형태로 반환
- 범위 값: [최소값, 최대값] 형태로 반환
- 여러 개의 값이 추출된 경우, 반드시 최소값과 최대값만 선별하여 반환하세요.
```

**5. 테스트 결과:**
- 업데이트된 검증 로직으로 테스트 통과 (PASSED)
- ChatGPT API가 새로운 제한사항을 준수하여 응답 반환 확인

이 업데이트로 ChatGPT API는 보증금과 월세 항목에서 불필요한 중간값들을 제거하고, 핵심적인 최소값과 최대값만 반환하게 됩니다.

---

## 최신 업데이트 (2025-09-17) - 면적 범위 공백 처리 버그 수정

### area_range 값 공백 처리 표준화 완료

**변경된 파일들:**
1. `home/services/keyword_extraction.py` - ChatGPT 프롬프트 및 검증 로직의 area_range 값 수정
2. `home/services/parsers.py` - area_range 파싱 정규식 공백 처리 개선
3. `home/tests/test_chatgpt_integration.py` - area_range 공백 검증 테스트 추가

**주요 변경사항:**

**1. 공백 표준화:**
- **기존:** `"~10평"`, `"70~"` (공백 없음)
- **수정됨:** `"~ 10평"`, `"70평 ~"` (물결표 앞뒤 공백 추가)

**2. ChatGPT 프롬프트 업데이트:**
```
"area_range": "~ 10평|10평대|20평대|30평대|40평대|50평대|60평대|70평 ~" 중 하나 또는 null
```

**3. 검증 로직 개선:**
- 유효한 area_range 값: `['~ 10평', '10평대', '20평대', '30평대', '40평대', '50평대', '60평대', '70평 ~']`
- 공백을 포함한 올바른 형식만 허용

**4. 파싱 정규식 개선:**
```python
# "~ 10평" -> 10
match = re.search(r'~\s*(\d+)평', area_range)

# "70평 ~" -> 70
match = re.search(r'(\d+)평?\s*~', area_range)
```

**5. 테스트 검증:**
- `test_chatgpt_area_range_spacing` 테스트 추가
- ChatGPT API가 "~ 10평 ~" 형태로 올바른 공백 포함하여 응답 반환 확인 (PASSED)

**결과:**
이제 ChatGPT API는 면적 범위를 나타낼 때 일관되게 공백을 포함한 표준화된 형식으로 반환합니다:
- 10평 이하: `"~ 10평"`
- 70평 이상: `"70평 ~"`
- 특정 평수대: `"30평대"` (기존과 동일)