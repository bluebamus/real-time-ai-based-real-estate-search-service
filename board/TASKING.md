# Board App - TASKING.md

이 문서는 AI 기반 자연어 질의형 부동산 매물 추천 서비스의 `board` 앱 개발 작업을 정의합니다.

---

## 핵심 역할

Board App은 다음 핵심 기능을 담당합니다:

1. **결과 표시 및 추천 시스템** - Bootstrap 5 카드 디자인으로 반응형 결과 표시
2. **추천 알고리즘 및 스코어링** - Redis Sorted Sets를 활용한 추천 시스템
3. **페이지네이션 및 추가 결과 로딩** - AJAX 기반 비동기 페이지 로딩
4. **자동 추천 시스템 갱신** - Celery Beat를 통한 5분마다 자동 갱신

---

## 개발 작업 목록

### 1. Utils 클래스 연동

- [x] **Redis 검색 결과 조회**: Home에서 생성된 Redis 키로 데이터 조회
  - Redis 키 형태: `search:{hash}:results`
  - TTL 5분 내 유효한 데이터 조회
  - JSON 역직렬화를 통한 매물 리스트 변환
  - 데이터 없음/만료 시 적절한 오류 처리

- [x] **추천 매물 Redis 연동**: `utils.recommendations.RecommendationEngine` 사용
  - Redis Sorted Sets에서 추천 매물 조회
  - 스코어 기반 상위 10개 추천 매물 표시
  - TTL 1시간 내 유효한 추천 데이터 조회

- [ ] **데이터 파싱**: `utils.parsers.DataParser` 클래스 구현
  ```python
  class DataParser:
      def parse_crawled_data(self, raw_data: list) -> list:
          # 크롤링 원본 데이터를 JSON 구조로 변환
          # 영문 컬럼명 적용 (COLUMN_MAPPING 사용)
          # tags 문자열을 리스트로 변환
          # price, area_size 데이터 타입 변환

      def format_property_card_data(self, property_data: dict) -> dict:
          # UI 표시용 데이터 포맷팅
          # 가격 포맷팅 (예: 390000000 → "3억 9천만원")
          # 평수 포맷팅 (예: 25.64 → "25.64평")
          # 태그 문자열 정리
  ```

### 2. 뷰 구현 및 구조 개선

#### 2.0 Views 폴더 구조 개선 (2025-09-23 완료)
- [x] **Views 폴더 구조화**: `board/views/` 폴더 생성
  - `board/views/__init__.py`: 빈 초기화 파일
  - `board/views/base_views.py`: 기본 템플릿 뷰들
  - `board/views/api_views.py`: API 뷰들
  - 기존 `board/views.py`, `board/api_views.py` 파일 삭제

#### 2.1 메인 뷰
- [x] **PropertyListView**: 매물 목록 표시 (`board/views/base_views.py`)
  - Home에서 전달받은 Redis 키로 검색 결과 조회
  - 추천 매물 상위 10개 우선 표시 ("추천" 배지)
  - 일반 검색 결과 30개 표시 (추천 매물 제외)
  - Flex 반응형 카드 레이아웃 구현
  - 페이지네이션 구현

- [ ] **PropertyDetailView**: 매물 상세 정보
  - 개별 매물 상세 정보 표시
  - 관련 매물 추천

#### 2.2 API 뷰 및 세션 인증 시스템
- [x] **AuthTestAPIView**: Board 인증 테스트 API (2025-09-23 추가)
  - 세션 기반 인증 상태 확인
  - 서버 콘솔에 상세 인증 정보 출력
  - 클라이언트에 JSON 형태 인증 상태 반환
  - Board 페이지 방문 시 자동 실행

- [x] **ResultsAPIView**: 검색 결과 API (`board/views/api_views.py`)
  - Redis 키 파라미터로 데이터 조회
  - 페이지네이션 지원 (30개씩)
  - JSON 응답 (추천 매물 제외)
  - 세션 기반 인증 적용

- [x] **RecommendationAPIView**: 추천 매물 API (`board/views/api_views.py`)
  - Redis Sorted Sets에서 상위 10개 추천 매물 조회
  - 스코어 기반 정렬된 매물 데이터 반환
  - JSON 응답 (is_recommendation: true 플래그)
  - 세션 기반 인증 적용

- [x] **PropertyDetailAPIView**: 매물 상세 정보 API (`board/views/api_views.py`)
  - 개별 매물 상세 정보 JSON 반환
  - 세션 기반 인증 적용

### 3. 추천 시스템 연동

- [ ] **추천 엔진 사용**: `utils.recommendations.RecommendationEngine` 연동
  - Redis Sorted Sets 활용
  - 사용자별 키워드 스코어 분석
  - 전체 사용자 인기 키워드 분석
  - 추천 매물 조회 로직

- [ ] **자동 갱신 시스템**: `utils.tasks.update_recommendations` 연동
  - Celery Beat로 5분마다 자동 실행
  - 최고 스코어 키워드 조합
  - 자동 크롤링 및 추천 캐시 갱신
  - 최대 10개 추천 매물 저장

### 4. 페이지네이션 시스템

- [ ] **커스텀 페이지네이션 클래스**: `pagination.py`
  - Redis 데이터 기반 페이지네이션
  - 30개씩 데이터 분할
  - 페이지 번호 기반 범위 조회

- [ ] **AJAX 페이지 로딩**: JavaScript 구현
  - 비동기 페이지 전환
  - 부드러운 사용자 경험
  - 브라우저 히스토리 관리

### 5. 템플릿 구현

- [x] **results.html**: 메인 결과 페이지
  - Bootstrap 5 Flex 반응형 카드 디자인
  - 추천 매물 섹션 (상위 10개, "추천" 배지)
  - 일반 검색 결과 섹션 (30개, 추천 매물 제외)
  - 카드 간 동일한 높이 유지 (flex-fill 활용)
  - 반응형 그리드 레이아웃 (md: 3열, sm: 2열, xs: 1열)

- [ ] **property_card.html**: 매물 카드 컴포넌트
  ```html
  <div class="card property-card">
    <div class="card-header">
      {% if is_recommendation %}
        <span class="badge bg-primary">추천</span>
      {% endif %}
      <h5 class="card-title">{{ property.owner_name }}</h5>
    </div>
    <div class="card-body">
      <p class="card-text">
        <strong>주소:</strong> {{ property.address }}<br>
        <strong>거래:</strong> {{ property.transaction_type }}<br>
        <strong>가격:</strong> {{ property.price_formatted }}<br>
        <strong>평수:</strong> {{ property.area_size }}평<br>
        <strong>층수:</strong> {{ property.floor_info }}<br>
        <strong>방향:</strong> {{ property.direction }}
      </p>
      <div class="tags">
        {% for tag in property.tags %}
          <span class="badge bg-secondary">{{ tag }}</span>
        {% endfor %}
      </div>
      <small class="text-muted">{{ property.updated_date }}</small>
    </div>
  </div>
  ```

- [ ] **pagination.html**: 페이지네이션 컴포넌트
  - Bootstrap 페이지네이션
  - 이전/다음 버튼
  - 페이지 번호 표시

### 6. JavaScript 구현 및 세션 인증 적용

- [x] **세션 기반 인증 JavaScript 적용** (2025-09-23 완료)
  - `templates/board/results.html` 내 JavaScript 수정
  - CSRF 토큰 및 `credentials: 'include'` 설정 추가
  - Board 페이지 방문 시 자동 인증 테스트 실행
  - 서버 콘솔 및 브라우저 콘솔에 인증 상태 로그 출력

- [ ] **results.js**: 결과 페이지 기능
  - 페이지네이션 클릭 처리
  - AJAX 요청 및 응답 처리
  - 카드 동적 생성 및 추가

- [ ] **utils.js**: 유틸리티 함수
  ```javascript
  // 가격 포맷팅 (390000000 → "3억 9천만원")
  function formatPrice(price) {
    const eok = Math.floor(price / 100000000);
    const man = Math.floor((price % 100000000) / 10000);
    let result = '';
    if (eok > 0) result += eok + '억 ';
    if (man > 0) result += man + '천만원';
    return result || price + '원';
  }

  // 태그 배열을 HTML로 변환
  function formatTags(tags) {
    return tags.map(tag =>
      `<span class="badge bg-secondary">${tag}</span>`
    ).join(' ');
  }

  // 매물 카드 HTML 생성
  function createPropertyCard(property, isRecommendation = false) {
    return `
      <div class="col-md-4 mb-3">
        <div class="card property-card">
          <div class="card-header">
            ${isRecommendation ? '<span class="badge bg-primary">추천</span>' : ''}
            <h5 class="card-title">${property.owner_name}</h5>
          </div>
          <div class="card-body">
            <p class="card-text">
              <strong>주소:</strong> ${property.address}<br>
              <strong>거래:</strong> ${property.transaction_type}<br>
              <strong>가격:</strong> ${formatPrice(property.price)}<br>
              <strong>평수:</strong> ${property.area_size}평<br>
              <strong>층수:</strong> ${property.floor_info}<br>
              <strong>방향:</strong> ${property.direction}
            </p>
            <div class="tags">${formatTags(property.tags)}</div>
            <small class="text-muted">${property.updated_date}</small>
          </div>
        </div>
      </div>
    `;
  }
  ```

### 7. URL 설정

- [x] **URL 구성**: `board/urls.py` (2025-09-23 업데이트)
  ```python
  urlpatterns = [
      # 메인 뷰
      path('results/<str:redis_key>/', PropertyListView.as_view(), name='property_list'),

      # API 뷰들
      path('api/auth-test/', AuthTestAPIView.as_view(), name='api_auth_test'),  # 추가됨
      path('api/results/<str:redis_key>/', ResultsAPIView.as_view(), name='api_results'),
      path('api/recommendations/', RecommendationAPIView.as_view(), name='api_recommendations'),
      path('api/results/<str:redis_key>/<int:property_index>/', PropertyDetailAPIView.as_view(), name='api_property_detail'),
  ]
  ```
  - Import 경로 업데이트: `board.views.base_views`, `board.views.api_views`
  - AuthTestAPIView 추가

### 8. Celery Beat 작업 연동

#### Celery Beat 실행 환경
```bash
# 1. Django 개발 서버 실행
uv run python manage.py runserver

# 2. Celery Worker 실행 (별도 터미널)
uv run celery -A config worker -l info

# 3. Celery Beat 실행 (별도 터미널) - 필수!
uv run celery -A config beat -l info
```

- [ ] **Celery Beat 설정 확인**: `config/settings.py`
  ```python
  CELERY_BEAT_SCHEDULE = {
      'update-recommendations': {
          'task': 'utils.tasks.update_recommendations',
          'schedule': 300.0,  # 5분마다
      },
      'backup-redis-to-database': {
          'task': 'utils.tasks.backup_redis_scores_to_database',
          'schedule': 600.0,  # 10분마다
      },
  }
  ```

- [ ] **Utils 작업 활용**: `utils.tasks.update_recommendations` 연동
  - `utils.scheduler.AutoUpdateScheduler` 사용
  - `utils.crawlers.NaverRealEstateCrawler` 사용
  - `utils.cache.RedisCache` 사용
  - 추천 매물 캐시 갱신 (TTL 없음)

#### Redis 장애 대비 백업 시스템
- [ ] **KeywordScore 모델 연동**: `utils.models.KeywordScore`
  - Redis Sorted Sets 백업용 Database 저장
  - Django 재시작 시 자동 복원

- [ ] **RecommendationCache 모델 연동**: `utils.models.RecommendationCache`
  - 추천 매물 캐시 백업용 Database 저장
  - JSON 형태 매물 데이터 관리

### 9. 테스트 구현

#### 9.1 단위 테스트
- [ ] **test_utils_integration.py**: Utils 클래스 연동 테스트
  - RedisCache 클래스 연동 테스트
  - RecommendationEngine 연동 테스트
  - DataParser 클래스 테스트

- [ ] **test_views.py**: 뷰 테스트
  - PropertyListView 테스트
  - API 뷰 테스트
  - 페이지네이션 테스트

- [ ] **test_pagination.py**: 페이지네이션 테스트
  - 커스텀 페이지네이션 클래스 테스트

#### 9.2 통합 테스트
- [ ] **test_recommendation_flow.py**: 추천 시스템 플로우 테스트
  - 스코어 업데이트 → 추천 생성 → 캐시 저장

- [ ] **test_celery_tasks.py**: Celery 작업 테스트
  - 추천 갱신 작업 테스트

### 10. 성능 최적화

- [ ] **캐시 최적화**: 효율적인 Redis 키 설계
- [ ] **쿼리 최적화**: 불필요한 데이터베이스 조회 최소화
- [ ] **이미지 최적화**: 매물 이미지 로딩 최적화

---

## 데이터 구조

### Redis 키 구조
```
# 검색 결과 (TTL: 5분) - Home에서 생성
search:{hash}:results -> List of property data (JSON 직렬화)

# 추천 매물 (TTL: 1시간) - 추천 시스템에서 생성
recommendations:top_properties -> Sorted Set (score: property_id)

# 키워드 스코어 (Sorted Sets, TTL: 1시간)
user:{user_id}:keywords:{category} -> {keyword: score}
global:keywords:{category} -> {keyword: score}

# 추천 매물 상세 데이터 (TTL: 1시간)
property:{property_id}:details -> JSON property data
```

### 매물 데이터 구조 (실제 크롤링 결과 기반)
```json
{
  "address": "서울시 강남구",          # 서버에서 별도 관리 (크롤링 키워드에서 추출)
  "owner_name": "수원한일타운",        # 건물/단지명 (집주인)
  "transaction_type": "전세",         # 거래타입 (매매/전세/월세)
  "price": 390000000,                # 가격 (정수)
  "building_type": "아파트",          # 건물타입
  "area_size": 25.64,               # 평수 (float)
  "floor_info": "8/23층",           # 층정보
  "direction": "남동향",             # 집방향
  "tags": ["25년이상", "융자금없는", "올수리"],  # 태그 (리스트)
  "updated_date": "2025-09-09"      # 갱신일
}
```

### 영문 컬럼 매핑 정보
```python
COLUMN_MAPPING = {
    '집주인': 'owner_name',        # 건물/단지명
    '거래타입': 'transaction_type', # 매매/전세/월세
    '가격': 'price',               # 가격 (정수)
    '건물 종류': 'building_type',   # 아파트/오피스텔/빌라/단독주택
    '평수': 'area_size',           # 평수 (float)
    '층정보': 'floor_info',        # 층수 정보
    '집방향': 'direction',         # 향
    'tag': 'tags',                 # 태그 (리스트)
    '갱신일': 'updated_date'       # 갱신일자
}
```

---

## 구현 우선순위

### Phase 1: Redis 연동 및 기본 결과 표시
1. Home에서 생성된 Redis 키로 검색 결과 조회
2. JSON 역직렬화 및 매물 데이터 파싱
3. 기본 뷰 및 Bootstrap 5 Flex 카드 UI 구현

### Phase 2: 추천 시스템 연동
1. Redis Sorted Sets에서 추천 매물 조회
2. 스코어 기반 상위 10개 추천 매물 표시
3. "추천" 배지 및 우선 표시 기능

### Phase 3: 페이지네이션 및 AJAX
1. 커스텀 페이지네이션 구현 (30개씩)
2. AJAX 기반 비동기 페이지 로딩
3. 브라우저 히스토리 관리

### Phase 4: 최적화 및 테스트
1. Flex 레이아웃 성능 최적화
2. Redis 조회 캐싱 최적화
3. 추천 시스템 연동 테스트

---

## 성공 기준

- Redis 데이터 조회 성공률 99% 이상
- 페이지 로딩 시간 2초 이내
- 추천 시스템 정확도 80% 이상
- Celery 작업 실행 성공률 95% 이상
- 반응형 디자인 모든 디바이스 지원
- 테스트 커버리지 80% 이상

---

## 기술 스택

- **Backend**: Django, Celery, Redis
- **Utils**: 공통 유틸리티 클래스 (캐시, 파싱, 추천, 스케줄링)
- **Frontend**: Bootstrap 5, Vanilla JavaScript, AJAX
- **Cache**: Redis (검색 결과, 추천 데이터)
- **Task Queue**: Celery Beat (자동 갱신)
- **Database**: MySQL (메타데이터)
- **Testing**: pytest

---

*이 문서는 개발 진행에 따라 지속적으로 업데이트되며, 완료된 작업은 HISTORY.md에 기록됩니다.*