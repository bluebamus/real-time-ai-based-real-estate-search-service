"""
ChatGPT API 키워드 추출 모듈

pre-test/poc_chatgpt_api.py를 기반으로 한 자연어 부동산 검색 키워드 추출
Django home 앱에서 사용하기 위해 최적화된 버전
"""

import json
import logging
from typing import Dict, Any
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


class ChatGPTKeywordExtractor:
    """
    OpenAI ChatGPT API와의 통신을 담당하는 클라이언트
    자연어 쿼리에서 부동산 검색 키워드를 추출
    """

    def __init__(self):
        """ChatGPT 클라이언트 초기화"""
        self.api_key = settings.OPENAI_API_KEY
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
        self.max_tokens = getattr(settings, 'OPENAI_MAX_TOKENS', 500)
        self.temperature = getattr(settings, 'OPENAI_TEMPERATURE', 0.7)

        # OpenAI 클라이언트 설정
        self.client = OpenAI(api_key=self.api_key)

    def extract_keywords(self, query_text: str) -> Dict[str, Any]:
        """
        자연어 쿼리에서 부동산 검색 키워드 추출

        Args:
            query_text: 사용자가 입력한 자연어 검색 쿼리

        Returns:
            추출된 키워드 딕셔너리 (raw JSON from ChatGPT)
        """
        print(f"--- ChatGPTClient: Entering extract_keywords for query: '{query_text}' ---")
        try:
            # ChatGPT API 요청 시 전달되는 상세 조건들
            # 다음 6가지 조건을 기반으로 ChatGPT API에게 자연어를 전달하여
            # 명시된 조건에 맞춰 형식, 데이터 타입, 범위가 반환되어야 함

            # 조건 1: address (필수)
            # - 최소한 "시·도 + 시·군·구" 형태로 구성되어야 함
            # - 예: "서울시 강남구", "경기도 수원시", "부산시 해운대구"
            # - 시·도만 있고 시·군·구가 없으면 에러 반환
            # - 주소 정보가 전혀 없으면 에러 반환

            # 조건 2: transaction_type (필수)
            # - 배열 형태로 반환: ["매매"], ["전세"], ["월세"], ["단기임대"] 또는 여러 개 조합
            # - 4가지 거래 유형: 매매, 전세, 월세, 단기임대
            # - 최소 1개 이상 추출되어야 함, 추출된 정보가 없으면 에러 반환

            # 조건 3: building_type (필수)
            # - 배열 형태로 반환: ["아파트"], ["오피스텔"] 등
            # - 18가지 건물 유형: 아파트, 오피스텔, 빌라, 아파트분양권, 오피스텔분양권,
            #   재건축, 전원주택, 단독/다가구, 상가주택, 한옥주택, 재개발, 원룸, 상가,
            #   사무실, 공장/창고, 건물, 토지, 지식산업센터
            # - 최소 1개 이상 추출되어야 함, 추출된 정보가 없으면 에러 반환

            # 조건 4: sale_price (선택)
            # - 배열 형태: [최대값] 또는 [최소값, 최대값] 또는 null
            # - 정수형 숫자(원 단위)
            # - 매매가 범위를 나타냄
            # - 여러 개의 값이 있는 경우 반드시 최소값과 최대값만 반환
            # - 예: [1000000000] (10억원 이하), [500000000, 1000000000] (5억원~10억원)
            # - 정보가 없으면 null

            # 조건 5: deposit (선택)
            # - 배열 형태: [최대값] 또는 [최소값, 최대값] 또는 null
            # - 정수형 숫자(원 단위)
            # - 여러 개의 값이 있는 경우 반드시 최소값과 최대값만 반환
            # - 예: [50000000] (5천만원 이하), [10000000, 50000000] (1천만원~5천만원)
            # - 정보가 없으면 null

            # 조건 6: monthly_rent (선택)
            # - 배열 형태: [최대값] 또는 [최소값, 최대값] 또는 null
            # - 정수형 숫자(원 단위)
            # - 여러 개의 값이 있는 경우 반드시 최소값과 최대값만 반환
            # - 예: [500000] (50만원 이하), [300000, 800000] (30만원~80만원)
            # - 정보가 없으면 null

            # 조건 7: area_range (선택)
            # - 문자열 또는 null
            # - 8가지 면적 범위: "~ 10평", "10평대", "20평대", "30평대", "40평대", "50평대", "60평대", "70평 ~"
            # - 정보가 없으면 null

            system_prompt = """부동산 검색어에서 키워드 추출. 아래 조건에 맞춰 JSON 형식만 반환:

{
  "address": "시·도 + 시·군·구 최소 형태 필수",
  "transaction_type": ["매매", "전세", "월세", "단기임대"] 중 1개 이상,
  "building_type": ["아파트", "오피스텔", "빌라", "아파트분양권", "오피스텔분양권", "재건축", "전원주택", "단독/다가구", "상가주택", "한옥주택", "재개발", "원룸", "상가", "사무실", "공장/창고", "건물", "토지", "지식산업센터"] 중 1개 이상,
  "sale_price": [최대값] 또는 [최소값, 최대값] 정수 배열 또는 null,
  "deposit": [최대값] 또는 [최소값, 최대값] 정수 배열 또는 null,
  "monthly_rent": [최대값] 또는 [최소값, 최대값] 정수 배열 또는 null,
  "area_range": "~ 10평|10평대|20평대|30평대|40평대|50평대|60평대|70평 ~" 중 하나 또는 null
}

필수 검증 규칙:
1. address: 시·도만 있고 시·군·구가 없으면 에러 반환
2. transaction_type: 배열 형태, 최소 1개 필수, 없으면 에러 반환
3. building_type: 배열 형태, 최소 1개 필수, 없으면 에러 반환
4. sale_price: 선택, 정수 배열 [최대값] 또는 [최소값, 최대값] 또는 null (여러 값이 있는 경우 최소/최대값만 반환)
5. deposit: 선택, 정수 배열 [최대값] 또는 [최소값, 최대값] 또는 null (여러 값이 있는 경우 최소/최대값만 반환)
6. monthly_rent: 선택, 정수 배열 [최대값] 또는 [최소값, 최대값] 또는 null (여러 값이 있는 경우 최소/최대값만 반환)
7. area_range: 선택, "~ 10평|10평대|20평대|30평대|40평대|50평대|60평대|70평 ~" 중 하나 또는 null

모든 가격은 원(₩) 단위 정수로 변환하여 반환.
값이 없는 선택 필드는 반드시 JSON null로 반환.
위 스키마 외 다른 필드는 포함하지 말 것.

중요: deposit과 monthly_rent는 배열에 최대 2개 요소만 허용됩니다.
- 단일 값: [최대값] 형태로 반환
- 범위 값: [최소값, 최대값] 형태로 반환
- 여러 개의 값이 추출된 경우, 반드시 최소값과 최대값만 선별하여 반환하세요."""

            user_prompt = f"쿼리: {query_text}"

            print(f"--- ChatGPTClient: Sending request to OpenAI API (model: {self.model}) ---")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            print("--- ChatGPTClient: Received response from OpenAI API ---")

            result = response.choices[0].message.content.strip()
            print(f"\n\n--- ChatGPTClient: Raw response content: {result}\n\n\n")

            keywords = json.loads(result)

            # Basic validation: ensure it's a dictionary
            if not isinstance(keywords, dict):
                raise ValueError("ChatGPT response is not a valid JSON dictionary.")

            print(f"--- ChatGPTClient: Parsed keywords from API: {json.dumps(keywords, ensure_ascii=False, indent=2)}\n\n")
            print("--- ChatGPTClient: Successfully extracted keywords. Exiting extract_keywords. ---")

            # ChatGPT API 응답을 바로 최종 결과로 반환 (추가 변환 작업 없음)
            return keywords

        except json.JSONDecodeError as e:
            logger.error(f"[KEYWORD EXTRACTOR] JSON 파싱 실패: {e}. Raw response: {result}")
            raise ValueError("ChatGPT 응답을 파싱할 수 없습니다. 응답이 유효한 JSON 형식이 아닙니다.")
        except Exception as e:
            logger.error(f"[KEYWORD EXTRACTOR] API 호출 오류: {e}")
            raise

    def validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        ChatGPT 응답의 상세 유효성 검사
        6가지 조건에 맞춰 검증 수행

        Args:
            response: ChatGPT API 응답 (딕셔너리 형태)

        Returns:
            검증된 키워드 딕셔너리
        """
        if not isinstance(response, dict):
            raise ValueError("Invalid response format: expected a dictionary.")

        # 조건 1: address (필수) - 시·도 + 시·군·구 최소 형태 검증
        if 'address' not in response or not response['address']:
            raise ValueError("필수 필드 'address'가 누락되었습니다.")

        address_parts = response['address'].split()
        if len(address_parts) < 2:
            raise ValueError("주소는 최소 '시·도 + 시·군·구' 형태여야 합니다.")

        # 조건 2: transaction_type (필수) - 배열 형태, 최소 1개
        if 'transaction_type' not in response or not response['transaction_type']:
            raise ValueError("필수 필드 'transaction_type'가 누락되었습니다.")

        if not isinstance(response['transaction_type'], list) or len(response['transaction_type']) == 0:
            raise ValueError("transaction_type은 최소 1개 이상의 배열이어야 합니다.")

        valid_transaction_types = ['매매', '전세', '월세', '단기임대']
        for t_type in response['transaction_type']:
            if t_type not in valid_transaction_types:
                raise ValueError(f"유효하지 않은 거래 유형: {t_type}")

        # 조건 3: building_type (필수) - 배열 형태, 최소 1개
        if 'building_type' not in response or not response['building_type']:
            raise ValueError("필수 필드 'building_type'가 누락되었습니다.")

        if not isinstance(response['building_type'], list) or len(response['building_type']) == 0:
            raise ValueError("building_type은 최소 1개 이상의 배열이어야 합니다.")

        valid_building_types = [
            '아파트', '오피스텔', '빌라', '아파트분양권', '오피스텔분양권', '재건축',
            '전원주택', '단독/다가구', '상가주택', '한옥주택', '재개발', '원룸',
            '상가', '사무실', '공장/창고', '건물', '토지', '지식산업센터'
        ]
        for b_type in response['building_type']:
            if b_type not in valid_building_types:
                raise ValueError(f"유효하지 않은 건물 유형: {b_type}")

        # 조건 4: sale_price (선택) - 정수 배열 또는 null (최소/최대값만)
        if 'sale_price' in response and response['sale_price'] is not None:
            if not isinstance(response['sale_price'], list):
                raise ValueError("sale_price는 배열 형태여야 합니다.")
            if len(response['sale_price']) == 0 or len(response['sale_price']) > 2:
                raise ValueError("sale_price 배열은 1개 또는 2개 요소만 허용됩니다.")
            for val in response['sale_price']:
                if not isinstance(val, int) or val < 0:
                    raise ValueError("sale_price 값은 0 이상의 정수여야 합니다.")
            # 2개 요소인 경우 최소값 ≤ 최대값 검증
            if len(response['sale_price']) == 2 and response['sale_price'][0] > response['sale_price'][1]:
                raise ValueError("sale_price 배열에서 첫 번째 값(최소값)은 두 번째 값(최대값)보다 작거나 같아야 합니다.")

        # 조건 5: deposit (선택) - 정수 배열 또는 null (최소/최대값만)
        if 'deposit' in response and response['deposit'] is not None:
            if not isinstance(response['deposit'], list):
                raise ValueError("deposit은 배열 형태여야 합니다.")
            if len(response['deposit']) == 0 or len(response['deposit']) > 2:
                raise ValueError("deposit 배열은 1개 또는 2개 요소만 허용됩니다.")
            for val in response['deposit']:
                if not isinstance(val, int) or val < 0:
                    raise ValueError("deposit 값은 0 이상의 정수여야 합니다.")
            # 2개 요소인 경우 최소값 ≤ 최대값 검증
            if len(response['deposit']) == 2 and response['deposit'][0] > response['deposit'][1]:
                raise ValueError("deposit 배열에서 첫 번째 값(최소값)은 두 번째 값(최대값)보다 작거나 같아야 합니다.")

        # 조건 6: monthly_rent (선택) - 정수 배열 또는 null (최소/최대값만)
        if 'monthly_rent' in response and response['monthly_rent'] is not None:
            if not isinstance(response['monthly_rent'], list):
                raise ValueError("monthly_rent는 배열 형태여야 합니다.")
            if len(response['monthly_rent']) == 0 or len(response['monthly_rent']) > 2:
                raise ValueError("monthly_rent 배열은 1개 또는 2개 요소만 허용됩니다.")
            for val in response['monthly_rent']:
                if not isinstance(val, int) or val < 0:
                    raise ValueError("monthly_rent 값은 0 이상의 정수여야 합니다.")
            # 2개 요소인 경우 최소값 ≤ 최대값 검증
            if len(response['monthly_rent']) == 2 and response['monthly_rent'][0] > response['monthly_rent'][1]:
                raise ValueError("monthly_rent 배열에서 첫 번째 값(최소값)은 두 번째 값(최대값)보다 작거나 같아야 합니다.")

        # 조건 7: area_range (선택) - 지정된 8개 값 중 하나 또는 null
        if 'area_range' in response and response['area_range'] is not None:
            valid_area_ranges = ['~ 10평', '10평대', '20평대', '30평대', '40평대', '50평대', '60평대', '70평 ~']
            if response['area_range'] not in valid_area_ranges:
                raise ValueError(f"유효하지 않은 면적 범위: {response['area_range']}")

        return response


# 싱글톤 인스턴스
try:
    keyword_extractor = ChatGPTKeywordExtractor()
except Exception as e:
    logger.error(f"[KEYWORD EXTRACTOR] 초기화 실패: {e}")
    keyword_extractor = None


def get_keyword_extractor() -> ChatGPTKeywordExtractor:
    """키워드 추출기 인스턴스 반환"""
    if keyword_extractor is None:
        raise RuntimeError("Keyword extractor가 초기화되지 않았습니다.")
    return keyword_extractor