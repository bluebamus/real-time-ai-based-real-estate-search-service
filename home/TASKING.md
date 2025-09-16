# `home` App Tasking Guide

This document defines the development and testing tasks for the `home` app - the main landing page and search interface for the AI-powered real estate search service.

---

## Core Requirements

### Frontend Requirements
- **Framework**: All UI components must use **Bootstrap 5** with **responsive web design**
- **JavaScript**: Modern ES6+ JavaScript with `fetch` API for asynchronous operations
- **User Experience**: Clean, intuitive interface focused on search functionality
- **Accessibility**: WCAG 2.1 AA compliance for all interactive elements

### Backend Requirements
- **Authentication**: All views must require user login (`@login_required`)
- **View Structure**: Organized in `views/` folder with separate modules for different functionalities
- **API Design**: RESTful API endpoints using standard Django views (not DRF)
- **Database**: Efficient query optimization and proper indexing
- **Caching**: Implement caching for frequently accessed data

### Integration Requirements
- **Search Integration**: Natural language processing for real estate queries
- **External APIs**: ~~Naver Real Estate API integration~~ (현재 개발 계획 없음)
- **AI Model**: ChatGPT API integration for query processing with dummy testing
- **Environment Variables**: Secure API key management via `.env` file

---

## Detailed Task List

### 1. Environment Setup & Configuration

- [ ] **Install Dependencies**: Add required packages (`python-dotenv`, `mysqlclient`, `openai`, etc.)
- [ ] **Environment Variables**: Create `.env` file template with ChatGPT API keys
- [ ] **Settings Configuration**: Update `config/settings.py` for MySQL database and environment variables
- [ ] **Database Setup**: Configure MySQL connection (ai_admin/test1324@localhost/ai_test_prj)
- [ ] **App Registration**: Ensure `home` app is properly registered in `INSTALLED_APPS`

### 2. Models & Database

- [ ] **Search History Model**: Create model to store user search queries
  ```python
  class SearchHistory(models.Model):
      user = models.ForeignKey(User, on_delete=models.CASCADE)
      query = models.TextField()
      created_at = models.DateTimeField(auto_now_add=True)
      results_count = models.IntegerField(default=0)
  ```
- [ ] **Popular Searches Model**: Track trending searches
- [ ] **Migrations**: Create and apply database migrations
- [ ] **Admin Registration**: Register models in `admin.py` for management

### 3. View Structure Implementation

- [ ] **Create Views Directory**:
  ```
  home/views/
    ├── __init__.py
    ├── base_views.py      # Main page views
    ├── api_views.py       # API endpoints
    └── search_views.py    # Search-related views
  ```

#### 3.1 Base Views (`base_views.py`)
- [ ] **HomeView**: Main landing page with search interface
- [ ] **SearchResultsView**: Display search results
- [ ] **TrendingView**: Show trending searches and popular areas

#### 3.2 API Views (`api_views.py`)
- [ ] **SearchAPIView**: Process natural language search queries
  - Method: POST
  - CSRF exempt: `@csrf_exempt`
  - Authentication required
  - Input validation and sanitization
- [ ] **AutocompleteAPIView**: Provide search suggestions
- [ ] **SearchHistoryAPIView**: User's search history

#### 3.3 Search Views (`search_views.py`)
- [ ] **AdvancedSearchView**: Advanced search with filters
- [ ] **SaveSearchView**: Save search preferences
- [ ] **SearchAnalyticsView**: View search statistics

### 4. URL Configuration

- [ ] **Main URLs** (`home/urls.py`):
  ```python
  urlpatterns = [
      path('', HomeView.as_view(), name='home'),
      path('search/', SearchResultsView.as_view(), name='search_results'),
      path('trending/', TrendingView.as_view(), name='trending'),

      # API endpoints
      path('api/search/', SearchAPIView.as_view(), name='api_search'),
      path('api/autocomplete/', AutocompleteAPIView.as_view(), name='api_autocomplete'),
      path('api/history/', SearchHistoryAPIView.as_view(), name='api_history'),
  ]
  ```

### 5. Templates & Frontend (구현 후 마지막 단계)

#### 5.1 Templates Structure
- [ ] **home.html**: Main search page (모든 뷰와 기능 구현 후 작업)
- [ ] **search_results.html**: Results display page (모든 뷰와 기능 구현 후 작업)
- [ ] **trending.html**: Trending searches page (모든 뷰와 기능 구현 후 작업)
- [ ] **components/search_bar.html**: Reusable search component (모든 뷰와 기능 구현 후 작업)
- [ ] **components/result_card.html**: Property result card component (모든 뷰와 기능 구현 후 작업)

#### 5.2 JavaScript Implementation (모든 뷰와 기능 구현 후 작업)
- [ ] **search.js**: Main search functionality (모든 뷰와 기능 구현 후 작업)
  - Form validation
  - AJAX request handling
  - Results rendering
  - Error handling
- [ ] **autocomplete.js**: Search suggestions (모든 뷰와 기능 구현 후 작업)
- [ ] **analytics.js**: Track user interactions (모든 뷰와 기능 구현 후 작업)

#### 5.3 CSS Customization (모든 뷰와 기능 구현 후 작업)
- [ ] **custom.css**: Project-specific styles (모든 뷰와 기능 구현 후 작업)
- [ ] **Responsive breakpoints**: Mobile, tablet, desktop optimization (모든 뷰와 기능 구현 후 작업)

### 6. Search Functionality

- [ ] **Natural Language Processing**:
  - Parse user queries
  - Extract location, price, property type
  - Handle Korean language specifics

- [ ] **Search Filters**:
  - Location (시/구/동)
  - Property type (아파트, 오피스텔, 빌라, etc.)
  - Transaction type (매매, 전세, 월세)
  - Price range
  - Area size (평수)
  - Additional features (역세권, 학군, etc.)

- [ ] **Search Results**:
  - Pagination
  - Sorting options
  - Save search functionality

### 7. External Integration

- [ ] **~~Naver Real Estate API~~**: (현재 개발 계획 없음)
  - ~~API client implementation~~
  - ~~Rate limiting~~
  - ~~Error handling~~
  - ~~Data transformation~~

- [ ] **ChatGPT API Integration**:
  - Query understanding with dummy responses for testing
  - Natural language to structured query processing
  - Response generation with fallback dummy data
  - API key configuration via environment variables
  - Rate limiting handling
  - Dummy testing implementation for development

### 8. Performance Optimization

- [ ] **Database Optimization**:
  - Query optimization
  - Proper indexing
  - N+1 query prevention

- [ ] **Caching Strategy**:
  - Redis integration
  - Cache popular searches
  - Cache API responses

- [ ] **Frontend Optimization**:
  - Lazy loading
  - Image optimization
  - Minification

### 9. Testing

#### Unit Tests
- [ ] **test_models.py**:
  - `test_search_history_creation`
  - `test_popular_searches_update`

- [ ] **test_views.py**:
  - `test_home_view_authenticated_access`
  - `test_home_view_unauthenticated_redirect`
  - `test_search_api_success`
  - `test_search_api_invalid_query`
  - `test_search_api_unauthenticated`

- [ ] **test_forms.py**:
  - `test_search_form_validation`
  - `test_advanced_search_form`

#### Integration Tests
- [ ] **test_search_flow.py**:
  - Complete search workflow test
  - API integration test
  - End-to-end user journey

#### JavaScript Tests
- [ ] **search.test.js**: Frontend functionality tests (UI interactions only)

### 10. Documentation

- [ ] **API Documentation**: Document all API endpoints
- [ ] **User Guide**: Search tips and examples
- [ ] **Developer Documentation**: Setup and deployment guide

---

## Search Query Examples

The system should handle queries like:

1. **Basic Search**:
   - "강남구 아파트 매매"
   - "서초동 전세 3억 이하"

2. **Advanced Search**:
   - "강남역 도보 10분 이내 30평대 아파트 전세 5억 이하"
   - "서울 강남구 대치동 학군 좋은 곳 매매 10억 이하 신축"

3. **Natural Language**:
   - "강남에서 교통 편한 곳에 있는 깨끗한 아파트 찾아줘"
   - "아이 키우기 좋은 동네에서 전세 집 구하고 싶어"

---

## UI/UX Specifications

### Search Interface
```html
<div class="search-container">
  <h1>AI 부동산 검색 서비스</h1>
  <div class="search-box">
    <textarea placeholder="찾고 싶은 집을 자연스럽게 설명해주세요..."></textarea>
    <button type="submit">검색</button>
  </div>
  <div class="quick-filters">
    <!-- Quick filter buttons -->
  </div>
</div>
```

### Instructional Text
```html
<div class="alert alert-info">
  <h4>어떻게 질문할까요?</h4>
  <p>최상의 결과를 위해 아래 예시처럼 질문해주세요:</p>
  <ul>
    <li><strong>정확한 지역</strong>을 알려주세요 (예: 서울시 강남구)</li>
    <li>원하는 <strong>주거 타입</strong>을 선택하세요 (아파트, 오피스텔, 빌라)</li>
    <li><strong>거래 종류</strong>를 명시하세요 (매매, 전세, 월세)</li>
    <li><strong>추가 조건</strong>: 가격, 평수, 역세권, 학군 등</li>
  </ul>
  <p><strong>예시:</strong> "강남구 역삼동 30평대 아파트 전세 5억 이하 역세권"</p>
</div>
```

---

## Development Priority

1. **Phase 1 - Core Setup** (Week 1):
   - Environment setup
   - Basic models and views
   - Home page template

2. **Phase 2 - Search Implementation** (Week 2):
   - Search API
   - Natural language processing
   - Basic results display

3. **Phase 3 - Integration** (Week 3):
   - External API integration (Naver, ChatGPT)
   - Advanced filters

4. **Phase 4 - Optimization** (Week 4):
   - Performance tuning
   - Testing
   - Documentation

---

## Success Metrics

- Page load time < 2 seconds
- Search response time < 3 seconds
- 95% search query success rate
- Mobile responsive score > 95
- Test coverage > 80%

---

*This document should be updated as development progresses. All completed tasks should be checked off and documented in HISTORY.md.*