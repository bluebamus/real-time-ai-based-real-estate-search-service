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
from openai import OpenAIError, APIError, APIConnectionError, RateLimitError, AuthenticationError

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
        self.max_tokens = getattr(settings, 'OPENAI_MAX_TOKENS', 150)
        self.temperature = getattr(settings, 'OPENAI_TEMPERATURE', 0.1)

        # OpenAI 클라이언트 설정
        self.client = OpenAI(api_key=self.api_key)
        
    # --- 키워드 추출 규칙 및 반환 값 조건 (개발자 참고용) ---
    # 1. address (주소):
    #    - 형식: 시·도 + 시·군·구 + (선택: 읍·면 + 도로명 + 건물번호 + 상세주소)
    #    - 필수: 최소 '시·도 + 시·군·구' 형태의 주소 정보가 있어야 함.
    #    - 예외처리: 주소 정보가 없거나 시·군·구에 대한 정보 없이 시·도 정보만 제공될 경우 에러 출력.
    # 2. transaction_type (거래유형):
    #    - 값: 매매, 전세, 월세, 단기임대 (배열 형태)
    #    - 필수: 최소 한 개 이상의 거래유형이 추출되어야 함.
    #    - 예외처리: 자연어에서 추출된 정보가 없으면 에러 출력.
    # 3. building_type (매물유형):
    #    - 값: 아파트, 오피스텔, 빌라, 아파트분양권, 오피스텔분양권, 재건축, 전원주택, 단독/다가구, 상가주택, 한옥주택, 재개발, 원룸, 상가, 사무실, 공장/창고, 건물, 토지, 지식산업센터 (배열 형태)
    #    - 필수: 최소 한 개 이상의 매물유형이 추출되어야 함.
    #    - 예외처리: 자연어에서 추출된 정보가 없으면 에러 출력.
    # 4. sale_price (매매가):
    #    - 값: 정수형 숫자(원). 예: [1000] 또는 [1000, 5000] (최소, 최대).
    #    - 필수 아님: 정보가 없으면 null.
    # 5. deposit (보증금):
    #    - 값: 정수형 숫자(원). 예: [1000] 또는 [1000, 5000] (최소, 최대). 정보가 없으면 null.
    # 6. monthly_rent (월세):
    #    - 값: 정수형 숫자(원). 예: [100] 또는 [100, 500] (최소, 최대). 정보가 없으면 null.
    # 7. area_range (면적대):
    #    - 값: ~10평, 10평대, 20평대, 30평대, 40평대, 50평대, 60평대, 70~ 중 하나.
    #    - 필수 아님: 정보가 없으면 null.
    #
    # 일반 규칙:
    # - 모든 키워드는 설정된 범위 내의 정의된 값 혹은 숫자로만 반환되어야 합니다.
    # - 추출된 키워드는 JSON 형태로 반환되며, 각 항목별 조건은 null, 하나의 키워드, 또는 여러 개의 키워드(배열)가 될 수 있습니다.
    # - 주소 정보가 없거나 시·군·구에 대한 정보 없이 시·도 정보만 제공되면 에러를 반환해야 합니다.
    # - 거래유형과 매물유형은 반드시 하나 이상 추출되어야 합니다. 추출된 정보가 없으면 에러를 반환해야 합니다.
    # - 값이 없는 필드는 반드시 JSON 'null'로 반환해야 합니다. Python의 'None'이 아닙니다.
    # - 위에 정의된 JSON 스키마에 있는 항목들만 반환해야 합니다. 다른 항목은 포함하지 마십시오.
    # --------------------------------------------------------------------

    def extract_keywords(self, query_text: str) -> Dict[str, Any]:
        """
        자연어 쿼리에서 부동산 검색 키워드 추출

        Args:
            query_text: 사용자가 입력한 자연어 검색 쿼리

        Returns:
            추출된 키워드 딕셔너리 (ChatGPT의 원시 JSON)

        Raises:
            ValueError: ChatGPT 응답을 JSON으로 파싱할 수 없을 때
            Exception: OpenAI API 호출이 실패했을 때
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

            system_prompt = """Extract Korean real estate search keywords from the query and return JSON.

REQUIRED FIELDS - Return error only if truly missing:
1. address: Extract Korean address with 시도+시군구 minimum
   - VALID: "서울시 강남구", "경기도 수원시", "부산시 해운대구", "인천시 남동구"
   - ERROR only if: incomplete like "경기도" alone, or impossible like "부산시 강남구"

2. transaction_type: Extract transaction types from query
   - OPTIONS: ["매매","전세","월세","단기임대"]
   - EXTRACT ALL mentioned types as array
   - ERROR only if NO transaction type found in query

3. building_type: Extract property types from query
   - OPTIONS: ["아파트","오피스텔","빌라","아파트분양권","오피스텔분양권","재건축","전원주택","단독/다가구","상가주택","한옥주택","재개발","원룸","상가","사무실","공장/창고","건물","토지","지식산업센터"]
   - EXTRACT ALL mentioned types as array
   - ERROR only if NO building type found in query

OPTIONAL FIELDS - null if not mentioned:
- sale_price: [single_price] or [min_price, max_price] or null
- deposit: [single_amount] or [min_amount, max_amount] or null
- monthly_rent: [single_amount] or [min_amount, max_amount] or null
- area_range: Use EXACT options: "~10평"|"10평대"|"20평대"|"30평대"|"40평대"|"50평대"|"60평대"|"70평~"
  For 8평→"~10평", for 75평→"70평~", for multiple ranges use LAST mentioned

RESPONSE FORMAT:
{"status":"success|error","data":{address,transaction_type,building_type,sale_price,deposit,monthly_rent,area_range}|null,"error":{"code":"MISSING_ADDRESS|MISSING_TRANSACTION_TYPE|MISSING_BUILDING_TYPE","message":"description"}|null}

VALIDATION RULES:
- If building_type is null/empty/missing → MUST return MISSING_BUILDING_TYPE error
- If transaction_type is null/empty/missing → MUST return MISSING_TRANSACTION_TYPE error
- If address is incomplete → MUST return MISSING_ADDRESS error

EXAMPLES:
"서울시 강남구 아파트 매매 8평" → SUCCESS (has address+transaction+building, area_range="~10평")
"경기도 매매 아파트" → ERROR MISSING_ADDRESS (only 시도)
"서울시 강남구 아파트" → ERROR MISSING_TRANSACTION_TYPE (no 매매/전세/월세/단기임대)
"부산시 해운대구 매매 2억" → ERROR MISSING_BUILDING_TYPE (no 아파트/오피스텔/빌라 etc)

CRITICAL: ALL 3 required fields (address, transaction_type, building_type) MUST have values. Return error if ANY is missing."""

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
            print(f"\n\nChatGPTClient: Parsed keywords: {json.dumps(keywords, ensure_ascii=False, indent=2)}\n\n")

            # Check if ChatGPT returned error status
            if isinstance(keywords, dict) and keywords.get("status") == "error":
                error_info = keywords.get("error", {})
                error_code = error_info.get("code", "UNKNOWN_ERROR")
                error_message = error_info.get("message", "Unknown error from ChatGPT")
                print(f"ChatGPTClient: ChatGPT returned error - Code: {error_code}, Message: {error_message}")
                raise ValueError(f"ChatGPT extraction failed: {error_code} - {error_message}")

            return keywords

        except AuthenticationError as e:
            error_msg = f"ChatGPTClient Error: Authentication failed - Invalid API key. Error: {str(e)}"
            print(error_msg)
            raise Exception("OpenAI API authentication failed. Check your API key.")

        except RateLimitError as e:
            error_msg = f"ChatGPTClient Error: Rate limit exceeded. Error: {str(e)}"
            print(error_msg)
            raise Exception("OpenAI API rate limit exceeded. Please retry later.")

        except APIConnectionError as e:
            error_msg = f"ChatGPTClient Error: Connection failed. Error: {str(e)}"
            print(error_msg)
            raise Exception("Failed to connect to OpenAI API. Check your network connection.")

        except APIError as e:
            error_msg = f"ChatGPTClient Error: API error. Error: {str(e)}"
            print(error_msg)
            raise Exception(f"OpenAI API error: {str(e)}")

        except json.JSONDecodeError as e:
            error_msg = f"ChatGPTClient Error: Invalid JSON response from API. Error: {e}. Raw response: {result if 'result' in locals() else 'No response'}"
            print(error_msg)
            raise ValueError("ChatGPT API returned invalid JSON format")

        except OpenAIError as e:
            error_msg = f"ChatGPTClient Error: General OpenAI error. Error: {str(e)}"
            print(error_msg)
            raise Exception(f"OpenAI API error: {str(e)}")

        except Exception as e:
            error_msg = f"ChatGPTClient Error: Unexpected error. Error: {str(e)}"
            print(error_msg)
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