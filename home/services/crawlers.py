"""
네이버 부동산 크롤링 모듈 (pre-test/gemini-naver.py 기반)

검증된 POC 코드를 Django 환경에 맞게 수정한 헤드리스 크롤링 구현
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
    네이버 부동산 크롤링 클래스 (pre-test/gemini-naver.py 기반)
    헤드리스 Firefox 브라우저를 사용하여 네이버 부동산 크롤링
    """

    def __init__(self, headless: bool = True):
        """크롤러 초기화"""
        logger.info("[CRAWLER] 네이버 부동산 크롤러 초기화")

        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.headless = headless

        # 네이버 인증 쿠키 (pre-test/gemini-naver.py에서 복사)
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
        키워드를 기반으로 네이버 부동산 매물 크롤링

        Args:
            keywords: 검색 키워드 딕셔너리

        Returns:
            크롤링된 매물 리스트 (영문 컬럼명)
        """
        search_query = keywords.get('address', '서울시 강남구')
        logger.info(f"[CRAWLER] 크롤링 시작: {search_query}")

        try:
            # 브라우저 및 페이지 초기화
            if not self.initialize_browser_and_page():
                logger.error("[CRAWLER] 브라우저 초기화 실패")
                return []

            # 검색 수행
            if not self.perform_search(search_query):
                logger.error("[CRAWLER] 검색 수행 실패")
                return []

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

    def initialize_browser_and_page(self) -> bool:
        """
        Playwright를 시작하고 브라우저와 페이지를 초기화합니다.
        (pre-test/gemini-naver.py 기반)
        """
        logger.info("[CRAWLER] Playwright 및 브라우저 초기화를 시작합니다.")
        self.playwright = sync_playwright().start()

        cookies_for_playwright = [
            {"name": name, "value": value, "domain": ".naver.com", "path": "/"}
            for name, value in self.user_cookies.items()
        ]

        MAX_RETRIES = 5
        INITIAL_RETRY_DELAY_SECONDS = 5
        target_url = "https://fin.land.naver.com/search"

        for attempt in range(MAX_RETRIES):
            try:
                if self.browser:
                    self.browser.close()
                logger.info(f"[CRAWLER] Firefox 브라우저를 시작합니다... (시도 {attempt + 1}/{MAX_RETRIES})")

                self.browser = self.playwright.firefox.launch(
                    headless=self.headless,
                    firefox_user_prefs={
                        "dom.webdriver.enabled": False,
                        "media.peerconnection.enabled": False,
                    },
                )

                self.context = self.browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
                    viewport={"width": 1920, "height": 1080},
                    locale="ko-KR",
                    extra_http_headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    },
                )

                self.context.add_cookies(cookies_for_playwright)
                self.page = self.context.new_page()
                logger.info("[CRAWLER] 브라우저 및 컨텍스트 설정이 완료되었습니다.")

                logger.info(f"[CRAWLER] 초기 URL로 접속합니다: {target_url}")
                self.page.goto(target_url, wait_until="networkidle", timeout=60000)
                logger.info("[CRAWLER] 초기 URL 접속 성공.")
                time.sleep(2)
                return True

            except Error as e:
                logger.warning(f"[CRAWLER] URL 접속 중 Playwright 오류 발생: {e}")
                if attempt >= MAX_RETRIES - 1:
                    logger.error("[CRAWLER] 최대 재시도 횟수를 초과하여 브라우저를 초기화하지 못했습니다.")
                    return False
                time.sleep(INITIAL_RETRY_DELAY_SECONDS + attempt)

        return False

    def perform_search(self, search_query: str) -> bool:
        """
        네이버 부동산에서 지역 검색 수행
        (pre-test/gemini-naver.py 기반)
        """
        if not self.page:
            logger.error("[CRAWLER] 페이지가 초기화되지 않음")
            return False

        try:
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
            return True

        except Exception as e:
            logger.error(f"[CRAWLER] 검색 중 오류 발생: {e}")
            return False

    def scrape_all_markers_and_extract_data(self) -> List[Dict[str, Any]]:
        """
        지도 위의 모든 매물 마커를 클릭하여 정보 수집
        (pre-test/gemini-naver.py 기반)
        """
        if not self.page:
            logger.error("[CRAWLER] 페이지가 초기화되지 않음")
            return []

        logger.info("[CRAWLER] 지도 위의 모든 매물 마커를 클릭하여 정보 수집을 시작합니다.")
        try:
            self.page.wait_for_selector(".marker_circle_count", state="attached", timeout=15000)
            logger.info("[CRAWLER] 지도 마커('marker_circle_count')가 로드되었습니다.")
        except Error:
            logger.error("[CRAWLER] 'marker_circle_count' 클래스를 찾지 못했습니다.")
            return []

        marker_spans = self.page.locator(".marker_circle_count").all()
        total_markers = len(marker_spans)
        logger.info(f"[CRAWLER] 총 {total_markers}개의 마커 그룹을 발견했습니다.")

        all_items_data = []
        processed_articles = set()

        for i, marker in enumerate(marker_spans):
            try:
                logger.info(f"[CRAWLER] 마커 그룹 {i + 1}/{total_markers}을(를) 클릭합니다...")
                marker.click()
                self.page.wait_for_load_state("networkidle", timeout=15000)
                time.sleep(2)  # 데이터가 로드될 시간을 줍니다.

                item_elements = self.page.locator(".item_area._Listitem").all()
                logger.info(f"[CRAWLER] 현재 마커 그룹에서 {len(item_elements)}개의 매물 항목을 찾았습니다.")

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
                        logger.debug("[CRAWLER] article_no를 가져올 수 없는 아이템을 건너뜁니다 (광고 가능성).")
                        continue

                    extracted_data = self._extract_data_from_item(item_element)
                    if extracted_data:
                        all_items_data.append(extracted_data)

            except Error as e:
                logger.warning(f"[CRAWLER] 마커 그룹 {i + 1} 처리 중 오류 발생: {e}")
                continue

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
        한글 컬럼명 데이터를 영문 컬럼명으로 변환
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
                'owner_type': item.get('집주인', ''),
                'transaction_type': item.get('거래타입', ''),
                'price': item.get('가격', 0),
                'building_type': item.get('건물 종류', ''),
                'area_pyeong': item.get('평수', 0.0),
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