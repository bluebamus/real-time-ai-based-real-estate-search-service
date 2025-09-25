import json
import os
import sys
import django
from typing import Any, Dict

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from openai import OpenAI
from openai import OpenAIError, APIError, APIConnectionError, RateLimitError, AuthenticationError
from django.conf import settings

# --- Configuration ---
# Load from Django settings
OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_MODEL = settings.OPENAI_MODEL
OPENAI_MAX_TOKENS = settings.OPENAI_MAX_TOKENS
OPENAI_TEMPERATURE = settings.OPENAI_TEMPERATURE


class ChatGPTClient:
    """
    OpenAI ChatGPT API와의 통신을 담당하는 클라이언트
    자연어 쿼리에서 부동산 검색 키워드를 추출
    """

    def __init__(self, api_key: str, model: str, max_tokens: int, temperature: float):
        """ChatGPT 클라이언트 초기화"""
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

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
        print(f"ChatGPTClient: Processing query: '{query_text}'")

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

        try:
            print(f"ChatGPTClient: Calling OpenAI API (model: {self.model})")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            result = response.choices[0].message.content.strip()
            print(f"ChatGPTClient: Raw API response: {result}")

            keywords = json.loads(result)
            print(f"ChatGPTClient: Parsed keywords: {json.dumps(keywords, ensure_ascii=False, indent=2)}")

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


def main():
    """
    ChatGPT API 연동 PoC 프로그램의 메인 함수.

    사용 방법:
    1. Django settings.py에 OpenAI API 관련 설정을 확인하세요.
       `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_MAX_TOKENS`, `OPENAI_TEMPERATURE` 값이 설정되어 있어야 합니다.
    2. 'natural_language_queries' 리스트에 테스트할 자연어 쿼리들을 추가하거나 수정하세요.
    3. 이 스크립트를 실행하여 각 쿼리에 대한 ChatGPT API의 응답을 확인합니다.
    """
    print("--- PoC Program Start ---")

    if not OPENAI_API_KEY:
        print(
            "WARNING: OpenAI API Key가 설정되지 않았습니다. Django settings를 통해 설정되었는지 확인해주세요."
        )
        print("API 키 없이 실행하면 API 호출이 실패합니다.")
        # For demonstration purposes, we might want to exit or use a mock client here.
        # For now, we'll proceed, expecting it to fail if the key is invalid.

    client = ChatGPTClient(
        api_key=OPENAI_API_KEY,
        model=OPENAI_MODEL,
        max_tokens=OPENAI_MAX_TOKENS,
        temperature=OPENAI_TEMPERATURE,
    )

    # natural_language_queries = [
    #     "서울시 강남구 30평대 아파트 매매 5억 이하",
    #     "부산 해운대구 오피스텔 전세 1억 5천만원",
    #     "경기도 수원시 영통구 원룸 월세 보증금 1000만원 월세 50만원",
    #     "강원도 속초시 토지 매매",
    #     "서울시 서초구 아파트 50평대 남향 매매 20억 이하"
    # ]

    natural_language_queries = [
        "경기도 수원시 장안구 매매, 전세, 월세, 단기임대와 아파트, 오피스텔, 상가, 빌라 중 매매는 1천만원에서 2억사이, 월세 보증금 1천만원에서 1억사이, 월세 10만원에서 200만원사이 100평",
        # Area range tests
        "서울시 강남구 아파트 매매 8평",  # Should return "~10평"
        "부산시 해운대구 오피스텔 전세 75평",  # Should return "70평~"
        "인천시 남동구 빌라 월세 20평대에서 30평대까지 고려하다가 최종 40평대",  # Should return "40평대" (last one)
    ]

    # Error test cases - each tests one required field missing
    natural_language_queries_error_case = [
        # MISSING_ADDRESS: Only 시도 without 시군구
        "경기도 매매 아파트 1억",

        # MISSING_ADDRESS: Invalid address combination
        "부산시 강남구 매매 아파트 2억",

        # MISSING_TRANSACTION_TYPE: No transaction type mentioned
        "서울시 강남구 아파트 30평대",

        # MISSING_BUILDING_TYPE: No building type mentioned
        "부산시 해운대구 매매 2억",
    ]

    # for i, query in enumerate(natural_language_queries):
    #     print(f"\n--- Processing Query {i + 1}/{len(natural_language_queries)} ---")
    #     print(f"Query: '{query}'")
    #     try:
    #         print(f"Step 1: Extracting keywords for query: '{query}'")
    #         extracted_keywords = client.extract_keywords(query)
    #         print("Step 2: Successfully extracted keywords.")
    #         print(
    #             f"Extracted Keywords (Formatted Output): {json.dumps(extracted_keywords, ensure_ascii=False, indent=2)}"
    #         )
    #     except Exception as e:
    #         print(
    #             f"Step 2: Failed to extract keywords for query: '{query}'. Error: {e}"
    #         )
    #         print("--- Moving to next query ---")
    #         continue
    #     print(f"--- Finished processing Query {i + 1} ---")

    print("\n" + "=" * 80)
    print("ERROR TEST CASES")
    print("=" * 80)

    for i, query in enumerate(natural_language_queries_error_case):
        print(f"\n--- Processing Error Test {i + 1}/{len(natural_language_queries_error_case)} ---")
        print(f"Query: '{query}'")
        try:
            print(f"Step 1: Extracting keywords for query: '{query}'")
            extracted_keywords = client.extract_keywords(query)
            print("Step 2: Keywords extracted.")
            print(
                f"Result: {json.dumps(extracted_keywords, ensure_ascii=False, indent=2)}"
            )
        except Exception as e:
            print(
                f"Step 2: Expected error occurred for query: '{query}'. Error: {e}"
            )
            print("--- Moving to next error test ---")
        print(f"--- Finished processing Error Test {i + 1} ---")

    print("\n--- PoC Program End ---")


if __name__ == "__main__":
    main()
