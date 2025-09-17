import json
import hashlib
import logging
import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Error
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class NaverRealEstateCrawler:
    """
    네이버 부동산 크롤링 클래스
    Playwright를 사용하여 동적 웹 페이지 크롤링
    """

    def __init__(self):
        """크롤러 초기화"""
        self.base_url = "https://land.naver.com"
        self.max_items = 50  # 최대 크롤링 아이템 수

    def crawl_properties(self, keywords: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        키워드를 기반으로 네이버 부동산 매물 크롤링

        Args:
            keywords: 검색 키워드 딕셔너리

        Returns:
            크롤링된 매물 리스트
        """
        properties = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                page = browser.new_page()

                # User-Agent 설정 (크롤링 차단 방지)
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })

                # 검색 URL 생성
                search_url = self.build_search_url(keywords)
                logger.info(f"Crawling URL: {search_url}")

                # 페이지 로드
                page.goto(search_url, wait_until='networkidle', timeout=30000)

                # 검색 결과 대기
                page.wait_for_selector('.item_inner', timeout=10000)

                # 매물 데이터 추출
                properties = self.extract_property_data(page)

                browser.close()

                logger.info(f"Successfully crawled {len(properties)} properties")
                return self.convert_to_english_columns(properties, keywords.get('address', ''))

        except Error as e:
            logger.error(f"Playwright error during crawling: {e}")
            return []
        except Exception as e:
            logger.error(f"General crawling error: {e}")
            return []

    def build_search_url(self, keywords: Dict[str, Any]) -> str:
        """
        키워드를 기반으로 네이버 부동산 검색 URL 생성

        Args:
            keywords: 검색 키워드

        Returns:
            생성된 검색 URL
        """
        # 기본 검색 페이지
        base_search = f"{self.base_url}/search"

        # URL 파라미터 구성
        params = {}

        # 지역 검색어
        if keywords.get('address'):
            params['query'] = keywords['address']

        # 거래 타입 (매매, 전세, 월세)
        if keywords.get('transaction_type'):
            trade_map = {
                '매매': 'A1',
                '전세': 'B1',
                '월세': 'B2'
            }
            params['tradTpCd'] = trade_map.get(keywords['transaction_type'], 'A1')

        # 건물 타입
        if keywords.get('building_type'):
            building_map = {
                '아파트': 'APT',
                '빌라': 'VL',
                '오피스텔': 'OPST',
                '원룸': 'ONE',
                '투룸': 'TWO',
                '상가': 'SG',
                '사무실': 'SMS',
                '공장': 'GJ',
                '토지': 'LND'
            }
            params['rletTpCd'] = building_map.get(keywords['building_type'], 'APT')

        # 가격 범위
        if keywords.get('price_max'):
            price_in_man = keywords['price_max'] // 10000  # 원 -> 만원
            params['dprcMax'] = str(price_in_man)

        # 면적 범위 (평 -> ㎡)
        if keywords.get('area_pyeong'):
            area_m2 = int(keywords['area_pyeong'] * 3.305785) # 1평 = 3.305785㎡
            # 네이버 부동산은 면적 검색 시 최소/최대 범위로 검색하는 경우가 많음
            # 여기서는 대략적인 범위로 설정
            params['spcMin'] = str(max(0, area_m2 - 10))
            params['spcMax'] = str(area_m2 + 10)

        return f"{base_search}?{urlencode(params)}"

    def extract_property_data(self, page: Page) -> List[Dict[str, Any]]:
        """
        페이지에서 매물 데이터 추출

        Args:
            page: Playwright 페이지 객체

        Returns:
            추출된 매물 데이터 리스트 (한글 컬럼명)
        """
        properties = []
        try:
            # 매물 아이템 선택
            items = page.query_selector_all('.item_inner')[:self.max_items]

            for idx, item in enumerate(items):
                try:
                    property_data = self._extract_single_property(item, idx + 1)
                    if property_data:
                        properties.append(property_data)
                except Exception as e:
                    logger.warning(f"Failed to extract property {idx + 1}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error extracting properties: {e}")

        return properties

    def _extract_single_property(self, item, index: int) -> Optional[Dict[str, Any]]:
        """
        단일 매물 데이터 추출 (pre-test/gemini-naver.py의 _extract_data_from_item 참조)

        Args:
            item: 매물 HTML 요소
            index: 매물 인덱스

        Returns:
            추출된 매물 데이터 (한글 컬럼명)
        """
        try:
            # Selectors based on pre-test/gemini-naver.py and common Naver Real Estate structure
            owner_type = self._safe_extract(item, 'em.title_place', '')
            transaction_type = self._safe_extract(item, 'div.price_area > span.type', '')
            raw_price = self._safe_extract(item, 'div.price_area > strong.price', '0')
            building_type = self._safe_extract(item, 'div.information_area p.info > strong.type', '')
            raw_spec = self._safe_extract(item, 'div.information_area p.info > span.spec', '')
            description = self._safe_extract(item, 'div.information_area p.info_desc', '')
            tags_text = self._safe_extract(item, 'div.tag_area', '') # Tags are often in a div, need to parse
            detail_link = self._safe_extract_attr(item, 'a.item_link', 'href', '')
            image_url = self._safe_extract_attr(item, 'img', 'src', '') # Assuming there's an img tag

            # Parse spec string
            parsed_spec = self._parse_specification(raw_spec)

            # Parse price
            price = self._parse_price(raw_price)

            # Parse tags (simple split for now, can be enhanced)
            tags = [t.strip() for t in tags_text.split(',') if t.strip()] if tags_text else []

            # Updated date - Naver often shows "확인매물 YY.MM.DD."
            # For simplicity, we'll use current date if not found or parse if possible
            updated_date_str = self._safe_extract(item, 'span.icon-badge.type-confirmed', '')
            updated_date = self._parse_date(updated_date_str) if updated_date_str else datetime.now().strftime('%Y-%m-%d %H:%M:%S')


            property_data = {
                '집주인': owner_type,
                '거래타입': transaction_type,
                '가격': price,
                '건물 종류': building_type,
                '평수': parsed_spec['평수'],
                '층정보': parsed_spec['층정보'],
                '집방향': parsed_spec['집방향'],
                'tag': tags, # List of tags
                '갱신일': updated_date,
                '상세링크': self.base_url + detail_link if detail_link else '',
                '이미지URL': image_url
            }

            return property_data

        except Exception as e:
            logger.error(f"Error extracting single property: {e}")
            return None

    def _safe_extract(self, element, selector: str, default: str = '') -> str:
        """안전한 텍스트 추출"""
        try:
            el = element.query_selector(selector)
            if el:
                return el.inner_text().strip()
        except:
            pass
        return default

    def _safe_extract_attr(self, element, selector: str, attr: str, default: str = '') -> str:
        """안전한 속성 추출"""
        try:
            el = element.query_selector(selector)
            if el:
                return el.get_attribute(attr) or default
        except:
            pass
        return default

    def _parse_price(self, price_text: str) -> int:
        """가격 텍스트 파싱 (pre-test/gemini-naver.py 참조)"""
        price_text = price_text.strip()
        if not price_text:
            return 0

        if '~' in price_text:
            price_text = price_text.split('~')[0].strip()

        try:
            price_text = price_text.replace(',', '')

            parts = price_text.split('억')
            billions = 0
            millions = 0

            if len(parts) == 2:
                if parts[0].strip():
                    billions = int(parts[0].strip()) * 10000
                if parts[1].strip().replace('천', ''):
                    millions = int(parts[1].strip().replace('천', ''))
            elif len(parts) == 1:
                if '천' in parts[0]:
                    millions = int(parts[0].replace('천', '').strip())
                else:
                    millions = int(parts[0].strip())

            return (billions + millions) * 10000

        except (ValueError, IndexError) as e:
            logger.debug(f"가격 변환 오류: '{price_text}'. 오류: {e}")
            return 0

    def _parse_area(self, area_text: str) -> float:
        """면적 텍스트 파싱 (㎡)"""
        try:
            area_text = area_text.replace('㎡', '').replace('m2', '').strip()
            return float(area_text)
        except:
            return 0.0

    def _parse_area_pyeong(self, area_text: str) -> float:
        """면적 텍스트 파싱 (평)"""
        try:
            if '평' in area_text:
                return float(area_text.replace('평', '').strip())
            elif '㎡' in area_text or 'm2' in area_text:
                sqm = self._parse_area(area_text)
                return round(sqm / 3.305785, 1) # 1평 = 3.305785㎡
        except:
            return 0.0

    def _parse_specification(self, spec_str: str) -> Dict[str, Any]:
        """
        '사양' 문자열을 '평수', '층정보', '집방향'으로 파싱합니다.
        (pre-test/gemini-naver.py 참조)
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
                    sq_meter_str = area_part.split('/')[1].replace('㎡', '').strip()
                    sq_meter = float(sq_meter_str)
                    pyeong = round(sq_meter / 3.305785, 2)
                except (ValueError, IndexError) as e:
                    logger.debug(f"평수 변환 오류: '{area_part}'. 오류: {e}")
                    pyeong = 0.0

        # 2. 층정보
        if len(parts) > 1:
            floor_info = parts[1]

        # 3. 집방향
        if len(parts) > 2:
            direction = parts[2]

        return {"평수": pyeong, "층정보": floor_info, "집방향": direction}

    def _parse_date(self, date_str: str) -> str:
        """
        '확인매물 YY.MM.DD.' 형식의 날짜 문자열을 'YYYY-MM-DD' 형식으로 변환합니다.
        (pre-test/gemini-naver.py 참조)
        """
        try:
            date_str = date_str.strip()
            if not date_str:
                return ""

            clean_str = date_str.replace('확인매물', '').replace('.', '').strip()
            dt_obj = datetime.strptime(f"20{clean_str}", "%Y%m%d")
            return dt_obj.strftime("%Y-%m-%d %H:%M:%S") # Include time for DateTimeField
        except (ValueError, IndexError) as e:
            logger.debug(f"날짜 변환 오류: '{date_str}'. 오류: {e}")
            return ""

    def convert_to_english_columns(self, raw_data: List[Dict[str, Any]], address_keyword: str) -> List[Dict[str, Any]]:
        """
        한글 컬럼명 데이터를 영문 컬럼명으로 변환하고 Property 모델에 맞게 정제

        Args:
            raw_data: 크롤링된 한글 컬럼명 데이터 리스트
            address_keyword: 검색 키워드에서 추출된 주소 (Property 모델의 address 필드에 사용)

        Returns:
            영문 컬럼명으로 변환된 데이터 리스트
        """
        converted_data = []
        for item in raw_data:
            # 'tag' 필드가 리스트가 아닌 경우 문자열로 변환 후 다시 리스트로 파싱
            tags = item.get('tag', [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(',') if t.strip()]

            # '갱신일' 필드가 datetime 객체가 아닌 경우 문자열로 변환
            updated_date = item.get('갱신일')
            if isinstance(updated_date, datetime):
                updated_date = updated_date.strftime('%Y-%m-%d %H:%M:%S')
            elif not isinstance(updated_date, str):
                updated_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # Fallback

            converted_item = {
                'address': address_keyword, # Use the address from the search keyword
                'owner_type': item.get('집주인', ''),
                'transaction_type': item.get('거래타입', ''),
                'price': item.get('가격', 0),
                'building_type': item.get('건물 종류', ''),
                'area_pyeong': item.get('평수', 0.0),
                'floor_info': item.get('층정보', ''),
                'direction': item.get('집방향', ''),
                'tags': tags,
                'updated_date': updated_date,
                'detail_url': item.get('상세링크', ''),
                'image_urls': [item.get('이미지URL', '')] if item.get('이미지URL') else [],
                'description': item.get('설명', '')
            }
            converted_data.append(converted_item)
        return converted_data
