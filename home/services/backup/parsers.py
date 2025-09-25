import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class KeywordParser:
    """
    자연어 쿼리 파싱 및 키워드 검증 클래스
    """

    # 유효한 시·도 목록
    VALID_PROVINCES = [
        '서울', '서울시', '서울특별시',
        '부산', '부산시', '부산광역시',
        '대구', '대구시', '대구광역시',
        '인천', '인천시', '인천광역시',
        '광주', '광주시', '광주광역시',
        '대전', '대전시', '대전광역시',
        '울산', '울산시', '울산광역시',
        '세종', '세종시', '세종특별자치시',
        '경기', '경기도',
        '강원', '강원도',
        '충북', '충청북도',
        '충남', '충청남도',
        '전북', '전라북도',
        '전남', '전라남도',
        '경북', '경상북도',
        '경남', '경상남도',
        '제주', '제주도', '제주특별자치도'
    ]

    def __init__(self):
        """파서 초기화"""
        self.price_patterns = self._compile_price_patterns()
        self.area_patterns = self._compile_area_patterns()

    def _compile_price_patterns(self) -> Dict[str, re.Pattern]:
        """가격 관련 정규표현식 컴파일"""
        return {
            'billion': re.compile(r'(\d+(?:\.\d+)?)\s*억'),
            'million': re.compile(r'(\d+)\s*만\s*원?'),
            'thousand': re.compile(r'(\d+)\s*천\s*만?\s*원?'),
            'range': re.compile(r'(\d+(?:\.\d+)?)\s*억?\s*~\s*(\d+(?:\.\d+)?)\s*억?')
        }

    def _compile_area_patterns(self) -> Dict[str, re.Pattern]:
        """면적 관련 정규표현식 컴파일"""
        return {
            'pyeong': re.compile(r'(\d+)\s*평'),
            'pyeong_range': re.compile(r'(\d+)\s*평\s*대'),
            'sqm': re.compile(r'(\d+)\s*m2|(\d+)\s*㎡'),
            'range': re.compile(r'(\d+)\s*~\s*(\d+)\s*평')
        }

    def parse(self, raw_keywords: Dict[str, Any]) -> Dict[str, Any]:
        """
        ChatGPT에서 추출된 키워드를 검증하고 기본값을 적용하여 최종 파싱된 키워드를 반환
        새로운 ChatGPT API 응답 형식 (배열 형태)을 처리

        Args:
            raw_keywords: ChatGPT에서 추출된 원본 키워드 딕셔너리

        Returns:
            검증 및 기본값 적용이 완료된 키워드 딕셔너리
        """
        # 1. 새로운 형식을 기존 형식으로 변환
        converted_keywords = self._convert_new_format_to_legacy(raw_keywords)

        # 2. 데이터 타입 변환 및 정제
        processed_keywords = self._process_data_types(converted_keywords)

        # 3. 기본값 적용
        keywords_with_defaults = self.apply_defaults(processed_keywords)

        # 4. 필수 필드 검증
        if not self.validate_required_fields(keywords_with_defaults):
            raise ValueError("필수 검색 키워드(주소)가 유효하지 않습니다.")

        return keywords_with_defaults

    def _convert_new_format_to_legacy(self, new_keywords: Dict[str, Any]) -> Dict[str, Any]:
        """
        새로운 ChatGPT API 응답 형식을 기존 파서가 처리할 수 있는 형식으로 변환

        새로운 형식:
        - transaction_type: ["매매", "전세"] (배열)
        - building_type: ["아파트", "오피스텔"] (배열)
        - deposit: [500000000] 또는 [100000000, 500000000] (배열)
        - monthly_rent: [500000] 또는 [300000, 800000] (배열)
        - area_range: "30평대" (문자열)

        기존 형식:
        - transaction_type: "매매" (문자열, 첫 번째 값 사용)
        - building_type: "아파트" (문자열, 첫 번째 값 사용)
        - price_max: 500000000 (정수, deposit의 최대값 또는 단일값)
        - area_pyeong: 30 (정수, area_range에서 추출)

        Args:
            new_keywords: 새로운 형식의 키워드 딕셔너리

        Returns:
            기존 형식으로 변환된 키워드 딕셔너리
        """
        converted = {}

        # address는 그대로 유지
        if 'address' in new_keywords:
            converted['address'] = new_keywords['address']

        # transaction_type: 배열의 첫 번째 값 사용
        if 'transaction_type' in new_keywords and new_keywords['transaction_type']:
            if isinstance(new_keywords['transaction_type'], list):
                converted['transaction_type'] = new_keywords['transaction_type'][0]
            else:
                converted['transaction_type'] = new_keywords['transaction_type']

        # building_type: 배열의 첫 번째 값 사용
        if 'building_type' in new_keywords and new_keywords['building_type']:
            if isinstance(new_keywords['building_type'], list):
                converted['building_type'] = new_keywords['building_type'][0]
            else:
                converted['building_type'] = new_keywords['building_type']

        # deposit을 price_max로 변환 (최대값 또는 단일값 사용)
        if 'deposit' in new_keywords and new_keywords['deposit'] is not None:
            if isinstance(new_keywords['deposit'], list) and len(new_keywords['deposit']) > 0:
                # 배열의 마지막 값이 최대값
                converted['price_max'] = new_keywords['deposit'][-1]

        # monthly_rent는 현재 기존 시스템에서 사용하지 않으므로 무시

        # area_range를 area_pyeong으로 변환
        if 'area_range' in new_keywords and new_keywords['area_range'] is not None:
            converted['area_pyeong'] = self._extract_pyeong_from_range(new_keywords['area_range'])

        # 기존 필드들 중 누락된 것들은 null로 설정
        default_fields = {
            'owner_type': None,
            'floor_info': None,
            'direction': None,
            'updated_date': None,
            'tags': []
        }

        for field, default_value in default_fields.items():
            if field not in converted:
                converted[field] = default_value

        return converted

    def _extract_pyeong_from_range(self, area_range: str) -> Optional[int]:
        """
        area_range 문자열에서 평수 추출

        Args:
            area_range: "30평대", "~ 10평", "70평 ~" 등의 문자열

        Returns:
            추출된 평수 (정수)
        """
        if not area_range:
            return None

        # "30평대" -> 30
        if '평대' in area_range:
            match = re.search(r'(\d+)평대', area_range)
            if match:
                return int(match.group(1))

        # "~ 10평" -> 10
        if area_range.startswith('~') and '평' in area_range:
            match = re.search(r'~\s*(\d+)평', area_range)
            if match:
                return int(match.group(1))

        # "70평 ~" -> 70
        if area_range.endswith('~'):
            match = re.search(r'(\d+)평?\s*~', area_range)
            if match:
                return int(match.group(1))

        return None

    def _process_data_types(self, keywords: Dict[str, Any]) -> Dict[str, Any]:
        """
        키워드 딕셔너리 내의 값들을 적절한 데이터 타입으로 변환 (예: 가격, 평수)
        """
        processed = keywords.copy()

        # 가격 필드 정수 변환
        if 'price_max' in processed and processed['price_max'] is not None:
            try:
                # ChatGPT가 문자열로 반환할 수 있으므로 parse_price를 활용
                if isinstance(processed['price_max'], (int, float)):
                    processed['price_max'] = int(processed['price_max'])
                elif isinstance(processed['price_max'], str):
                    parsed_price = self.parse_price(processed['price_max'])
                    if parsed_price is not None:
                        processed['price_max'] = parsed_price
                    else:
                        processed['price_max'] = None
                else:
                    processed['price_max'] = None
            except (ValueError, TypeError):
                processed['price_max'] = None

        # 평수 필드 정수 변환
        if 'area_pyeong' in processed and processed['area_pyeong'] is not None:
            try:
                if isinstance(processed['area_pyeong'], (int, float)):
                    processed['area_pyeong'] = int(processed['area_pyeong'])
                elif isinstance(processed['area_pyeong'], str):
                    parsed_area = self.parse_area(processed['area_pyeong'])
                    if parsed_area is not None:
                        processed['area_pyeong'] = parsed_area
                    else:
                        processed['area_pyeong'] = None
                else:
                    processed['area_pyeong'] = None
            except (ValueError, TypeError):
                processed['area_pyeong'] = None
        
        # tags가 문자열로 올 경우 리스트로 변환
        if 'tags' in processed and isinstance(processed['tags'], str):
            processed['tags'] = [tag.strip() for tag in processed['tags'].split(',') if tag.strip()]
        elif 'tags' not in processed or processed['tags'] is None:
            processed['tags'] = []


        return processed

    def validate_required_fields(self, keywords: Dict[str, Any]) -> bool:
        """
        필수 필드 검증

        Args:
            keywords: 검증할 키워드 딕셔너리

        Returns:
            검증 성공 여부
        """
        # 필수 필드: address (시·도 + 시·군·구)
        if 'address' not in keywords or not keywords['address']:
            logger.warning("Missing required field: address")
            return False

        # 주소 검증
        address = keywords['address']
        if not self._validate_address(address):
            logger.warning(f"Invalid address format: {address}")
            return False

        return True

    def _validate_address(self, address: str) -> bool:
        """
        주소 형식 검증

        Args:
            address: 검증할 주소 문자열

        Returns:
            유효한 주소 여부
        """
        if not address:
            return False

        # 시·도가 포함되어 있는지 확인
        has_province = any(province in address for province in self.VALID_PROVINCES)

        # 최소 2개 이상의 지역명이 포함되어야 함 (시·도 + 시·군·구)
        # 예: "서울 강남" -> 2개, "서울시 강남구" -> 2개 (split() 결과)
        parts = address.split()
        has_district = len(parts) >= 2

        return has_province and has_district

    def apply_defaults(self, keywords: Dict[str, Any]) -> Dict[str, Any]:
        """
        누락된 필드에 기본값 적용

        Args:
            keywords: 기본값을 적용할 키워드 딕셔너리

        Returns:
            기본값이 적용된 키워드 딕셔너리
        """
        defaults = {
            'owner_type': '전체',
            'transaction_type': '매매',
            'building_type': '아파트',
            'floor_info': '전체',
            'direction': '전체',
            'updated_date': '전체',
            'tags': []
        }

        # 기본값 적용
        for key, value in defaults.items():
            if key not in keywords or keywords[key] is None or (isinstance(keywords[key], (str, list)) and not keywords[key]):
                keywords[key] = value
            # Ensure tags is always a list
            if key == 'tags' and not isinstance(keywords[key], list):
                keywords[key] = [keywords[key]] if keywords[key] else []


        # 유효한 값 검증 (ChatGPT가 잘못된 값을 반환할 경우 기본값으로 대체)
        valid_values = {
            'owner_type': ['개인', '사업자', '전체'],
            'transaction_type': ['매매', '전세', '월세'],
            'building_type': ['아파트', '빌라', '오피스텔', '원룸', '투룸', '상가', '사무실', '공장', '토지'],
            'floor_info': ['저층', '중층', '고층', '전체'],
            'direction': ['남향', '동향', '서향', '북향', '남동향', '남서향', '북동향', '북서향', '전체'],
            'updated_date': ['오늘', '3일이내', '일주일이내', '한달이내', '전체']
        }

        for field, valid_list in valid_values.items():
            if field in keywords and keywords[field] not in valid_list:
                keywords[field] = defaults[field]

        return keywords

    def parse_price(self, text: str) -> Optional[int]:
        """
        텍스트에서 가격 정보 추출

        Args:
            text: 가격 정보가 포함된 텍스트

        Returns:
            추출된 가격 (원 단위)
        """
        try:
            # 억 단위 처리
            billion_match = self.price_patterns['billion'].search(text)
            if billion_match:
                value = float(billion_match.group(1))
                return int(value * 100000000)

            # 천만원 단위 처리
            thousand_match = self.price_patterns['thousand'].search(text)
            if thousand_match:
                value = int(thousand_match.group(1))
                return value * 10000000

            # 만원 단위 처리
            million_match = self.price_patterns['million'].search(text)
            if million_match:
                value = int(million_match.group(1))
                return value * 10000

            # 숫자만 있는 경우 (원 단위로 가정)
            number_match = re.search(r'\d+', text)
            if number_match:
                return int(number_match.group())

        except Exception as e:
            logger.error(f"Error parsing price from text: {text}, error: {e}")

        return None

    def parse_area(self, text: str) -> Optional[int]:
        """
        텍스트에서 면적 정보 추출

        Args:
            text: 면적 정보가 포함된 텍스트

        Returns:
            추출된 면적 (평 단위)
        """
        try:
            # 평 단위 직접 표현
            pyeong_match = self.area_patterns['pyeong'].search(text)
            if pyeong_match:
                return int(pyeong_match.group(1))

            # 평대 표현 (예: 30평대 -> 30)
            pyeong_range_match = self.area_patterns['pyeong_range'].search(text)
            if pyeong_range_match:
                return int(pyeong_range_match.group(1))

            # 제곱미터 -> 평 변환
            sqm_match = self.area_patterns['sqm'].search(text)
            if sqm_match:
                sqm_value = int(sqm_match.group(1) or sqm_match.group(2))
                return int(sqm_value / 3.3)  # 1평 = 약 3.3㎡

        except Exception as e:
            logger.error(f"Error parsing area from text: {text}, error: {e}")

        return None

    def extract_tags_from_text(self, text: str) -> List[str]:
        """
        텍스트에서 태그 추출

        Args:
            text: 태그를 추출할 텍스트

        Returns:
            추출된 태그 리스트
        """
        tags = []
        tag_keywords = {
            '신축': ['신축', '새집', '새아파트', '신규'],
            '역세권': ['역세권', '지하철', '역근처', '역앞'],
            '학군': ['학군', '학교', '초등학교', '중학교', '고등학교'],
            '공원': ['공원', '녹지', '산책로'],
            '리모델링': ['리모델링', '재건축', '재개발'],
            '브랜드': ['브랜드', '대기업', '현대', '삼성', 'GS', 'SK', '대림'],
            '주차': ['주차', '주차장', '지하주차장'],
            '보안': ['보안', 'CCTV', '경비'],
            '편의시설': ['편의시설', '헬스장', '수영장', '사우나', '골프장'],
            '대단지': ['대단지', '대규모'],
            '저층': ['저층', '낮은층'],
            '고층': ['고층', '높은층', '뷰'],
            '투자': ['투자', '수익', '전세가'],
            '급매': ['급매', '급처', '급급매'],
            '풀옵션': ['풀옵션', '가전', '가구완비']
        }

        text_lower = text.lower()
        for tag, keywords in tag_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                tags.append(tag)

        return tags

    def normalize_building_type(self, text: str) -> str:
        """
        건물 타입 정규화

        Args:
            text: 정규화할 건물 타입 텍스트

        Returns:
            정규화된 건물 타입
        """
        type_mapping = {
            '아파트': ['아파트', 'apt', '아팟'],
            '빌라': ['빌라', '다세대', '연립'],
            '오피스텔': ['오피스텔', '오피'],
            '원룸': ['원룸', '1룸', '원룸'],
            '투룸': ['투룸', '2룸', '투룸'],
            '상가': ['상가', '점포', '매장'],
            '사무실': ['사무실', '사무소', '오피스'],
            '공장': ['공장', '창고', '물류'],
            '토지': ['토지', '땅', '대지', '임야']
        }

        text_lower = text.lower()
        for normalized, variants in type_mapping.items():
            if any(variant in text_lower for variant in variants):
                return normalized

        return '아파트'  # 기본값

    def parse_date_range(self, text: str) -> datetime:
        """
        날짜 범위 텍스트를 datetime 객체로 변환

        Args:
            text: 날짜 범위 텍스트

        Returns:
            계산된 날짜
        """
        today = datetime.now()

        if '오늘' in text:
            return today
        elif '3일' in text:
            return today - timedelta(days=3)
        elif '일주일' in text or '7일' in text:
            return today - timedelta(days=7)
        elif '한달' in text or '30일' in text:
            return today - timedelta(days=30)
        else:
            return today - timedelta(days=365)  # 전체 (1년)
