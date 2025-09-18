"""
네이버 부동산 크롤링 모듈 (pre-test/crawlers-naver-with-search-opt-headless.py 기반)

POC 검증된 헤드리스 크롤링 구현 - 탐지 방지 및 검색 옵션 설정 기능 포함
"""

import json
import time
import logging
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Error

logger = logging.getLogger(__name__)


class NaverRealEstateCrawler:
    """
    네이버 부동산 크롤링 클래스 (POC 완전 동기화)
    헤드리스 Firefox 브라우저를 사용하여 네이버 부동산 크롤링
    탐지 방지 및 검색 옵션 설정 기능 포함
    """

    def __init__(self, headless: bool = True):
        """크롤러 초기화"""
        logger.info("[CRAWLER] 네이버 부동산 크롤러 초기화 (POC 동기화)")

        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.headless = headless

        # 네이버 인증 쿠키 (POC에서 검증됨)
        self.user_cookies = {
            "NNB": "3C7PYUFWZWUGI",
            "NAC": "ua1EBcgqOrsZ",
            "BUC": "9zuEYCy2NEsg9dTDvyNNO5m8R-5tUNI96llreZdpRNE=",
            "nid_inf": "1772764205",
            "REALESTATE": "Mon%20Sep%2015%202025%2023%3A29%3A47%20GMT%2B0900%20(Korean%20Standard%20Time)",
            "PROP_TEST_KEY": "1757946587259.af7716dc3ead8d36166392fe23451a00bb653bd8b78343cc1b143cdecf12ab21",
            "PROP_TEST_ID": "c00c7672cb7105754536969e4_0daf4231d6c34601a1d88df9e55bc09888bd866",
            "_fwb": "286ZwfRXnJUKFFvqJhtwJ.1757946459556",
            "NACT": "1",
            "SRT30": "1757946460",
            "SRT5": "1757946460",
        }

    def crawl_properties(self, keywords: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        키워드를 기반으로 네이버 부동산 매물 크롤링 (POC 동기화)

        Args:
            keywords: 검색 키워드 딕셔너리

        Returns:
            크롤링된 매물 리스트 (영문 컬럼명)
        """
        search_query = keywords.get('address', '서울시 강남구')
        logger.info(f"[CRAWLER] 크롤링 시작: {search_query}")

        try:
            # 브라우저 및 페이지 초기화
            self.initialize_browser_and_page()

            # 검색 수행
            self.perform_search(search_query)

            # 검색 옵션 설정 (POC 기능 추가)
            self.set_search_options(
                transaction_type=keywords.get('transaction_type', []),
                building_type=keywords.get('building_type', []),
                sale_price=keywords.get('sale_price'),
                deposit=keywords.get('deposit'),
                monthly_rent=keywords.get('monthly_rent'),
                area_range=keywords.get('area_range')
            )

            # 매물 데이터 스크래핑
            properties_data = self.scrape_all_markers_and_extract_data()

            # 각 매물에 검색 주소 추가 및 영문 컬럼명으로 변환
            converted_data = self.convert_to_english_columns(properties_data, search_query)

            logger.info(f"[CRAWLER] 크롤링 완료: {len(converted_data)}개 매물")
            return converted_data

        except Exception as e:
            logger.error(f"[CRAWLER] 크롤링 중 오류 발생: {e}")
            traceback.print_exc()
            return []
        finally:
            self.close()

    def initialize_browser_and_page(self):
        """
        Playwright를 시작하고 브라우저와 페이지를 초기화합니다.
        POC 완전 동기화 - 탐지 방지 설정 강화
        """
        logger.info("[CRAWLER] Playwright 및 브라우저 초기화를 시작합니다. (Headless 모드)")
        self.playwright = sync_playwright().start()

        cookies_for_playwright = [
            {"name": name, "value": value, "domain": ".naver.com", "path": "/"}
            for name, value in self.user_cookies.items()
        ]

        MAX_RETRIES = 5
        INITIAL_RETRY_DELAY_SECONDS = 20
        target_url = "https://fin.land.naver.com/search"

        for attempt in range(MAX_RETRIES):
            try:
                if self.browser:
                    self.browser.close()
                logger.info(f"[CRAWLER] Playwright Firefox 브라우저를 시작합니다... (시도 {attempt + 1}/{MAX_RETRIES})")

                # Headless 모드용 탐지 방지 설정 강화 (POC 완전 복사)
                self.browser = self.playwright.firefox.launch(
                    headless=self.headless,
                    firefox_user_prefs={
                        # 웹드라이버 탐지 방지
                        "dom.webdriver.enabled": False,
                        "useAutomationExtension": False,
                        "media.peerconnection.enabled": False,
                        # GPU 관련 설정
                        "webgl.disabled": True,
                        "media.webrtc.hw.h264.enabled": False,
                        # 자동화 감지 방지
                        "general.useragent.override": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
                        # 개발자 도구 비활성화
                        "devtools.console.stdout.chrome": False,
                        "devtools.debugger.remote-enabled": False,
                        # 플러그인 비활성화
                        "plugins.testmode": False,
                        # 네트워크 최적화
                        "network.http.pipelining": True,
                        "network.http.proxy.pipelining": True,
                        "network.http.pipelining.maxrequests": 8,
                        # 브라우저 fingerprinting 방지
                        "privacy.resistFingerprinting": True,
                        "privacy.trackingprotection.enabled": True,
                        # 캐시 및 히스토리 설정
                        "browser.cache.disk.enable": False,
                        "browser.cache.memory.enable": True,
                        "places.history.enabled": False,
                    },
                )

                self.context = self.browser.new_context(
                    # 실제 사용자와 유사한 User-Agent
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
                    viewport={"width": 1920, "height": 1080},
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                    # 실제 브라우저와 유사한 헤더 설정
                    extra_http_headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Cache-Control": "max-age=0",
                    },
                    # 권한 설정
                    permissions=["geolocation"],
                    geolocation={"latitude": 37.5665, "longitude": 126.9780},  # 서울 좌표
                    # JavaScript 활성화
                    java_script_enabled=True,
                )

                # 자동화 탐지 방지 스크립트 추가 (POC 완전 복사)
                self.context.add_init_script("""
                    // WebDriver 속성 숨기기
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });

                    // Chrome 객체 추가 (Firefox이지만 호환성을 위해)
                    window.chrome = {
                        runtime: {},
                        loadTimes: function() {},
                        csi: function() {},
                    };

                    // 플러그인 정보 추가
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });

                    // 언어 설정
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['ko-KR', 'ko', 'en-US', 'en'],
                    });

                    // 권한 API 모킹
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                """)

                self.context.add_cookies(cookies_for_playwright)
                self.page = self.context.new_page()

                # 페이지 설정
                self.page.set_default_navigation_timeout(60000)
                self.page.set_default_timeout(30000)

                logger.info("[CRAWLER] 브라우저 및 컨텍스트 설정이 완료되었습니다.")

                logger.info(f"[CRAWLER] 초기 URL로 접속합니다: {target_url}")
                self.page.goto(target_url, wait_until="networkidle", timeout=60000)
                logger.info("[CRAWLER] 초기 URL 접속 성공.")

                # URL이 404로 끝나는 경우 재시도
                if self.page.url.endswith("404"):
                    raise ValueError(f"URL이 404로 끝납니다: {self.page.url}")

                time.sleep(2)
                return

            except (Error, ValueError) as e:
                logger.warning(f"[CRAWLER] URL 접속 중 오류 발생: {e}")
                if attempt >= MAX_RETRIES - 1:
                    raise
                time.sleep(INITIAL_RETRY_DELAY_SECONDS + attempt)

        raise Exception("최대 재시도 횟수를 초과하여 브라우저를 초기화하지 못했습니다.")

    def perform_search(self, search_query: str):
        """
        네이버 부동산에서 지역 검색 수행 (POC 동기화)
        """
        if not self.page:
            raise Exception("페이지가 초기화되지 않았습니다. 먼저 initialize_browser_and_page를 호출하세요.")

        logger.info(f"[CRAWLER] '{search_query}'(으)로 검색을 수행합니다.")
        search_input_locator = self.page.locator("#search")
        search_input_locator.fill(search_query)
        time.sleep(2)
        search_input_locator.press("Enter")
        self.page.wait_for_load_state("networkidle")

        logger.info(f"[CRAWLER] 검색 결과 목록에서 '{search_query}' 링크를 찾습니다.")
        result_locator = self.page.get_by_role("link", name=search_query, exact=True).first
        result_locator.wait_for(state="visible", timeout=10000)

        logger.info(f"[CRAWLER] '{search_query}' 링크를 클릭하여 페이지를 현재 탭에서 이동합니다.")
        link_href = result_locator.get_attribute("href")
        if link_href:
            self.page.goto(link_href, wait_until="networkidle")
        else:
            logger.warning("[CRAWLER] 링크의 href 속성을 찾을 수 없어 기존 클릭 방식을 사용합니다.")
            result_locator.click()

        self.page.wait_for_load_state("networkidle")
        time.sleep(2)

        logger.info("[CRAWLER] 옵션 설정 페이지로 진입을 시도합니다.")

        # 현재 페이지 URL 로깅
        current_url = self.page.url
        logger.info(f"[CRAWLER] 현재 페이지 URL: {current_url}")

        # 옵션 설정 링크 클릭 시도 (강화된 로직)
        option_clicked = False

        # 시도 1: 기본 선택자
        try:
            option_link_locator = self.page.locator("a.header_option_add._optionChange").first
            option_link_locator.wait_for(state="visible", timeout=15000)
            option_link_locator.click()
            logger.info("[CRAWLER] 'header_option_add _optionChange' 링크 클릭 성공.")
            option_clicked = True
        except Error as e:
            logger.warning(f"[CRAWLER] 기본 옵션 링크 클릭 실패: {e}")

        # 시도 2: 대체 선택자들
        if not option_clicked:
            alternative_selectors = [
                "a._optionChange",
                ".header_option_add",
                "a[class*='option']",
                "a[href*='option']"
            ]

            for selector in alternative_selectors:
                try:
                    logger.info(f"[CRAWLER] 대체 선택자 시도: {selector}")
                    alt_locator = self.page.locator(selector).first
                    alt_locator.wait_for(state="visible", timeout=5000)
                    alt_locator.click()
                    logger.info(f"[CRAWLER] 대체 선택자 '{selector}' 클릭 성공.")
                    option_clicked = True
                    break
                except Error as e:
                    logger.debug(f"[CRAWLER] 대체 선택자 '{selector}' 실패: {e}")

        if option_clicked:
            self.page.wait_for_load_state("networkidle")
            time.sleep(3)  # 더 긴 대기 시간
            new_url = self.page.url
            logger.info(f"[CRAWLER] 옵션 설정 페이지 진입 성공. 새 URL: {new_url}")
        else:
            logger.error("[CRAWLER] 모든 옵션 링크 클릭 시도 실패. 페이지 구조가 변경되었을 수 있습니다.")
            # 현재 페이지의 링크들 확인
            try:
                links = self.page.locator("a").all()
                logger.info(f"[CRAWLER] 현재 페이지의 총 링크 수: {len(links)}")
                for i, link in enumerate(links[:10]):  # 처음 10개만 로깅
                    try:
                        href = link.get_attribute("href")
                        text = link.inner_text()[:30]  # 처음 30자만
                        logger.debug(f"[CRAWLER] 링크 {i+1}: href='{href}', text='{text}'")
                    except:
                        pass
            except Exception as e:
                logger.warning(f"[CRAWLER] 페이지 링크 분석 실패: {e}")

    def set_search_options(
        self,
        transaction_type: List[str],
        building_type: List[str],
        sale_price: Optional[List[int]],
        deposit: Optional[List[int]],
        monthly_rent: Optional[List[int]],
        area_range: Optional[str],
    ):
        """
        검색 옵션 설정 (POC 기능 추가)
        """
        from home.services.search_options import set_search_options

        set_search_options(
            page=self.page,
            transaction_type=transaction_type,
            building_type=building_type,
            sale_price=sale_price,
            deposit=deposit,
            monthly_rent=monthly_rent,
            area_range=area_range,
        )

    def scrape_all_markers_and_extract_data(self) -> List[Dict[str, Any]]:
        """
        지도 위의 모든 매물 마커를 클릭하여 정보 수집 (POC 강화된 로직)
        """
        if not self.page:
            raise Exception("페이지가 초기화되지 않았습니다.")

        logger.info("[CRAWLER] 지도 위의 모든 매물 마커를 클릭하여 정보 수집을 시작합니다.")

        # 현재 페이지 상태 확인
        current_url = self.page.url
        logger.info(f"[CRAWLER] 마커 찾기 시작 - 현재 URL: {current_url}")

        # 마커 요소 대기 (여러 선택자 시도)
        marker_found = False
        marker_selectors = [
            ".marker_circle_count",
            ".marker_count",
            "[class*='marker']",
            "[class*='circle_count']",
            ".map_marker",
            ".cluster_marker"
        ]

        for selector in marker_selectors:
            try:
                logger.info(f"[CRAWLER] 마커 선택자 시도: {selector}")
                self.page.wait_for_selector(selector, state="attached", timeout=10000)
                marker_count = self.page.locator(selector).count()
                if marker_count > 0:
                    logger.info(f"[CRAWLER] 마커 발견! 선택자: {selector}, 개수: {marker_count}")
                    marker_found = True
                    break
            except Error as e:
                logger.debug(f"[CRAWLER] 마커 선택자 '{selector}' 실패: {e}")

        if not marker_found:
            logger.error("[CRAWLER] 모든 마커 선택자로 마커를 찾지 못했습니다.")

            # 페이지 내용 분석
            try:
                # 페이지 제목 확인
                title = self.page.title()
                logger.info(f"[CRAWLER] 현재 페이지 제목: {title}")

                # 지도 관련 요소 확인
                map_elements = self.page.locator("[class*='map'], [id*='map'], [class*='marker']").count()
                logger.info(f"[CRAWLER] 지도 관련 요소 개수: {map_elements}")

                # 주요 클래스들 확인
                body_classes = self.page.locator("body").get_attribute("class")
                logger.info(f"[CRAWLER] body 클래스: {body_classes}")

            except Exception as e:
                logger.warning(f"[CRAWLER] 페이지 분석 실패: {e}")

            return []

        # 성공한 선택자로 마커 수집
        successful_selector = None
        for selector in marker_selectors:
            try:
                count = self.page.locator(selector).count()
                if count > 0:
                    successful_selector = selector
                    break
            except:
                continue

        if not successful_selector:
            logger.error("[CRAWLER] 성공한 마커 선택자를 찾을 수 없습니다.")
            return []

        logger.info(f"[CRAWLER] 사용할 마커 선택자: {successful_selector}")

        marker_spans = self.page.locator(successful_selector).all()
        logger.info(f"[CRAWLER] 총 {len(marker_spans)}개의 마커 그룹을 발견했습니다.")

        all_items_data = []
        processed_articles = set()

        for i, marker in enumerate(marker_spans):
            try:
                logger.info(f"[CRAWLER] 마커 그룹 {i + 1}/{len(marker_spans)}을(를) 클릭합니다...")

                # 마커가 클릭 가능한 상태인지 확인 (POC 강화 로직)
                try:
                    marker.wait_for(state="visible", timeout=5000)
                    marker.scroll_into_view_if_needed()
                    time.sleep(1)  # 안정화 대기

                    # 강제 클릭 옵션 추가
                    marker.click(force=True, timeout=10000)
                    logger.info(f"[CRAWLER] 마커 그룹 {i + 1} 클릭 성공")
                except Error as click_error:
                    logger.warning(f"[CRAWLER] 마커 그룹 {i + 1} 클릭 실패, 건너뛰기: {click_error}")
                    continue

                self.page.wait_for_load_state("networkidle", timeout=20000)
                time.sleep(2)

                item_elements = self.page.locator(".item_area._Listitem").all()
                logger.info(f"[CRAWLER] 현재 마커 그룹에서 {len(item_elements)}개의 매물 항목을 찾았습니다. 데이터 추출을 시작합니다.")

                for item_element in item_elements:
                    try:
                        article_link = item_element.locator("a.item_link").first
                        if article_link.count() > 0:
                            article_no = article_link.get_attribute("_articleno")
                            if article_no and article_no in processed_articles:
                                continue
                            if article_no:
                                processed_articles.add(article_no)
                        else:
                            continue
                    except Error:
                        continue

                    extracted_data = self._extract_data_from_item(item_element)
                    if extracted_data:
                        all_items_data.append(extracted_data)

            except Error as e:
                logger.error(f"[CRAWLER] 마커 그룹 {i + 1} 처리 중 오류 발생: {e}")
                # 페이지 상태 복구 시도
                try:
                    self.page.wait_for_load_state("networkidle", timeout=5000)
                    time.sleep(2)
                except Error:
                    pass
                continue

        if not all_items_data:
            logger.warning("[CRAWLER] 수집된 데이터가 없습니다.")
            return []

        logger.info(f"[CRAWLER] 총 {len(all_items_data)}개의 매물 정보를 수집했습니다.")
        return all_items_data

    def _extract_data_from_item(self, item_element) -> Optional[Dict[str, Any]]:
        """
        단일 매물 아이템 요소에서 데이터를 추출
        (pre-test/gemini-naver.py 기반)
        """
        inner_item = item_element.locator(".item_inner")
        if inner_item.count() == 0:
            return None

        def get_text_or_default(locator, field_name):
            try:
                if locator.count() > 0:
                    text = locator.first.inner_text(timeout=1000).strip()
                    return text
            except Error:
                pass
            return ""

        def get_all_texts_or_default(locator, field_name):
            try:
                if locator.count() > 0:
                    texts = locator.all_inner_texts()
                    joined_text = ", ".join([t.strip() for t in texts])
                    return joined_text
            except Error:
                pass
            return ""

        raw_price = get_text_or_default(inner_item.locator("div.price_area > strong.price"), "가격")
        processed_price = self._parse_price(raw_price)

        raw_date = get_text_or_default(inner_item.locator("span.icon-badge.type-confirmed"), "갱신일")
        processed_date = self._parse_date(raw_date)

        raw_spec = get_text_or_default(inner_item.locator("div.information_area p.info > span.spec"), "사양")
        processed_spec = self._parse_specification(raw_spec)

        data = {
            "집주인": get_text_or_default(inner_item.locator("em.title_place"), "집주인"),
            "거래타입": get_text_or_default(inner_item.locator("div.price_area > span.type"), "거래타입"),
            "가격": processed_price,
            "건물 종류": get_text_or_default(inner_item.locator("div.information_area p.info > strong.type"), "건물 종류"),
            "평수": processed_spec["평수"],
            "층정보": processed_spec["층정보"],
            "집방향": processed_spec["집방향"],
            "tag": get_all_texts_or_default(inner_item.locator("div.tag_area > em.tag"), "tag"),
            "갱신일": processed_date
        }

        # 유효성 검사: "집주인" 필드가 비어있으면 유효하지 않은 데이터로 간주
        if not data["집주인"]:
            return None

        return data

    def _parse_price(self, price_str: str) -> int:
        """
        '억', '천'과 같은 한글이 포함된 가격 문자열을 숫자(int)로 변환합니다.
        (pre-test/gemini-naver.py 기반)
        """
        price_str = price_str.strip()
        if not price_str:
            return 0

        if '~' in price_str:
            price_str = price_str.split('~')[0].strip()

        try:
            price_str = price_str.replace(',', '')

            parts = price_str.split('억')
            billions = 0
            millions = 0

            if len(parts) == 2:
                if parts[0].strip():
                    billions = int(parts[0].strip()) * 10000
                if parts[1].strip().replace('천',''):
                    millions = int(parts[1].strip().replace('천',''))
            elif len(parts) == 1:
                if '천' in parts[0]:
                    millions = int(parts[0].replace('천','').strip())
                else:
                    millions = int(parts[0].strip())

            return (billions + millions) * 10000

        except (ValueError, IndexError) as e:
            logger.debug(f"[CRAWLER] 가격 변환 오류: '{price_str}'. 오류: {e}")
            return 0

    def _parse_date(self, date_str: str) -> str:
        """
        '확인매물 YY.MM.DD.' 형식의 날짜 문자열을 'YYYY-MM-DD' 형식으로 변환합니다.
        (pre-test/gemini-naver.py 기반)
        """
        try:
            date_str = date_str.strip()
            if not date_str:
                return ""

            clean_str = date_str.replace('확인매물', '').replace('.', '').strip()
            dt_obj = datetime.strptime(f"20{clean_str}", "%Y%m%d")
            return dt_obj.strftime("%Y-%m-%d")
        except (ValueError, IndexError) as e:
            logger.debug(f"[CRAWLER] 날짜 변환 오류: '{date_str}'. 오류: {e}")
            return ""

    def _parse_specification(self, spec_str: str) -> dict:
        """
        '사양' 문자열을 '평수', '층정보', '집방향'으로 파싱합니다.
        (pre-test/gemini-naver.py 기반)
        """
        pyeong = 0.0
        floor_info = ""
        direction = ""

        if not spec_str:
            return {"평수": pyeong, "층정보": floor_info, "집방향": direction}

        parts = [p.strip() for p in spec_str.split(',')]

        # 1. 평수 계산
        if len(parts) > 0:
            area_part = parts[0]
            if '/' in area_part and '㎡' in area_part:
                try:
                    # 예: '109/84.77㎡' -> '84.77'
                    sq_meter_str = area_part.split('/')[1].replace('㎡', '').strip()
                    sq_meter = float(sq_meter_str)
                    # 1평 = 3.305785㎡
                    pyeong = round(sq_meter / 3.305785, 2)
                except (ValueError, IndexError) as e:
                    logger.debug(f"[CRAWLER] 평수 변환 오류: '{area_part}'. 오류: {e}")
                    pyeong = 0.0

        # 2. 층정보
        if len(parts) > 1:
            floor_info = parts[1]

        # 3. 집방향
        if len(parts) > 2:
            direction = parts[2]

        return {"평수": pyeong, "층정보": floor_info, "집방향": direction}

    def convert_to_english_columns(self, raw_data: List[Dict[str, Any]], address_keyword: str) -> List[Dict[str, Any]]:
        """
        한글 컬럼명 데이터를 영문 컬럼명으로 변환 (Redis 저장용)
        """
        converted_data = []
        for item in raw_data:
            # tags 처리
            tags = item.get('tag', '')
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(',') if t.strip()]
            elif not isinstance(tags, list):
                tags = []

            converted_item = {
                'address': address_keyword,  # 검색 키워드의 주소 사용
                'owner_name': item.get('집주인', ''),  # Redis 저장에 맞춘 필드명
                'transaction_type': item.get('거래타입', ''),
                'price': item.get('가격', 0),
                'building_type': item.get('건물 종류', ''),
                'area_size': item.get('평수', 0.0),  # Redis 저장에 맞춘 필드명
                'floor_info': item.get('층정보', ''),
                'direction': item.get('집방향', ''),
                'tags': tags,
                'updated_date': item.get('갱신일', ''),
                'detail_url': '',  # 상세 링크는 필요시 추가 구현
                'image_urls': [],  # 이미지 URL은 필요시 추가 구현
                'description': ''  # 설명은 필요시 추가 구현
            }
            converted_data.append(converted_item)

        return converted_data

    def close(self):
        """브라우저 리소스 정리"""
        try:
            if self.browser:
                logger.info("[CRAWLER] 브라우저를 종료합니다.")
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.warning(f"[CRAWLER] 브라우저 종료 중 오류: {e}")


# 외부에서 사용할 수 있는 간단한 함수
def crawl_naver_real_estate(keywords: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    네이버 부동산 크롤링 실행 함수

    Args:
        keywords: 검색 키워드 딕셔너리

    Returns:
        크롤링된 매물 데이터 리스트 (영문 컬럼명)
    """
    crawler = NaverRealEstateCrawler(headless=True)
    return crawler.crawl_properties(keywords)


if __name__ == "__main__":
    # 테스트 실행
    test_keywords = {
        "address": "경기도 수원시 장안구",
        "transaction_type": "매매",
        "building_type": "아파트"
    }

    print("=== 네이버 부동산 크롤링 테스트 ===")
    result = crawl_naver_real_estate(test_keywords)
    print(f"크롤링 결과: {len(result)}개 매물")

    if result:
        print("첫 번째 매물 예시:")
        print(json.dumps(result[0], ensure_ascii=False, indent=2))