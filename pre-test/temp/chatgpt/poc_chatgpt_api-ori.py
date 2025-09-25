import json
import os
from typing import Any, Dict

from openai import OpenAI


# --- .env file loading ---
def load_env_vars(env_path: str) -> Dict[str, str]:
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()
    return env_vars


# Project root directory (assuming this script is in pre-test/ and .env is in the parent directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE_PATH = os.path.join(PROJECT_ROOT, ".env")
env_config = load_env_vars(ENV_FILE_PATH)

# --- Configuration ---
# Load from .env file, then environment variables, then provide a default placeholder
OPENAI_API_KEY = env_config.get("OPENAI_API_KEY") or os.getenv(
    "OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE"
)
OPENAI_MODEL = env_config.get(
    "OPENAI_MODEL", "gpt-4o"
)  # Default to gpt-4o if not in .env or env vars
OPENAI_MAX_TOKENS = int(env_config.get("OPENAI_MAX_TOKENS", 500))
OPENAI_TEMPERATURE = float(env_config.get("OPENAI_TEMPERATURE", 0.7))


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
            추출된 키워드 딕셔너리 (raw JSON from ChatGPT)
        """
        print(
            f"--- ChatGPTClient: Entering extract_keywords for query: '{query_text}' ---"
        )
        try:
            system_prompt = """부동산 검색어에서 키워드 추출. JSON 형식만 반환:
{
  "address": "시·도 + 시·군·구 + (선택: 읍·면 + 도로명 + 건물번호 + 상세주소). 최소 '시·도 + 시·군·구' 형태 필수. 주소 정보가 없거나 시·군·구 없이 시·도만 있으면 에러 반환.",
  "transaction_type": "배열. 매매|전세|월세|단기임대 중 최소 1개 이상. 필수 정보. 추출된 정보가 없으면 에러 반환.",
  "building_type": "배열. 아파트|오피스텔|빌라|아파트분양권|오피스텔분양권|재건축|전원주택|단독/다가구|상가주택|한옥주택|재개발|원룸|상가|사무실|공장/창고|건물|토지|지식산업센터 중 최소 1개 이상. 필수 정보. 추출된 정보가 없으면 에러 반환.",
  "sale_price": "배열. 정수형 숫자(원). 예: [1000] 또는 [1000, 5000] (최소, 최대). 정보가 없으면 null.",
  "deposit": "배열. 정수형 숫자(원). 예: [1000] 또는 [1000, 5000] (최소, 최대). 정보가 없으면 null.",
  "monthly_rent": "배열. 정수형 숫자(원). 예: [100] 또는 [100, 500] (최소, 최대). 정보가 없으면 null.",
  "area_range": "~10평|10평대|20평대|30평대|40평대|50평대|60평대|70~ 중 하나. 정보가 없으면 null."
}

기본값:
- sale_price: null
- deposit: null
- monthly_rent: null
- area_range: null

참고:
- 모든 키워드는 설정된 범위 내의 정의된 값 혹은 숫자로만 반환되어야 합니다.
- 추출된 키워드는 JSON 형태로 반환되며, 각 항목별 조건은 null, 하나의 키워드, 또는 여러 개의 키워드(배열)가 될 수 있습니다.
- 주소 정보가 없거나 시·군·구에 대한 정보 없이 시·도 정보만 제공되면 에러를 반환해야 합니다.
- 거래유형과 매물유형은 반드시 하나 이상 추출되어야 합니다. 추출된 정보가 없으면 에러를 반환해야 합니다.
- 값이 없는 필드는 반드시 JSON 'null'로 반환해야 합니다. Python의 'None'이 아닙니다.
- 위에 정의된 JSON 스키마에 있는 항목들만 반환해야 합니다. 다른 항목은 포함하지 마십시오."""

            user_prompt = f"쿼리: {query_text}"

            print(
                f"--- ChatGPTClient: Sending request to OpenAI API (model: {self.model}) ---"
            )
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            print("--- ChatGPTClient: Received response from OpenAI API ---")

            result = response.choices[0].message.content.strip()
            print(
                f"\n\n--- ChatGPTClient: Raw response content: {result}\n\n"
            )  # Print full raw response
            keywords = json.loads(result)
            print(
                f"\n\n--- ChatGPTClient: Parsed keywords from API: {json.dumps(keywords, ensure_ascii=False, indent=2)}\n\n"
            )

            if not isinstance(keywords, dict):
                raise ValueError("ChatGPT response is not a valid JSON dictionary.")

            print(
                "--- ChatGPTClient: Successfully extracted keywords. Exiting extract_keywords. ---"
            )
            return keywords

        except json.JSONDecodeError as e:
            print(
                f"\n\n--- ChatGPTClient Error: Failed to parse ChatGPT response: {e}. Full raw response: {result}\n\n"
            )
            raise ValueError(
                "ChatGPT 응답을 파싱할 수 없습니다. 응답이 유효한 JSON 형식이 아닙니다."
            )
        except Exception as e:
            print(f"--- ChatGPTClient Error: General API error: {e}")
            raise


def main():
    """
    ChatGPT API 연동 PoC 프로그램의 메인 함수.

    사용 방법:
    1. 프로젝트 루트 디렉토리 (F:\project\django\github\projects\real-time-ai-based-real-estate-search-service)에 `.env` 파일을 생성하고,
       `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_MAX_TOKENS`, `OPENAI_TEMPERATURE` 값을 설정하세요.
       예시:
       OPENAI_API_KEY="sk-your-api-key"
       OPENAI_MODEL="gpt-4o"
       OPENAI_MAX_TOKENS=500
       OPENAI_TEMPERATURE=0.7
    2. 'natural_language_queries' 리스트에 테스트할 자연어 쿼리들을 추가하거나 수정하세요.
    3. 이 스크립트를 실행하여 각 쿼리에 대한 ChatGPT API의 응답을 확인합니다.
    """
    print("--- PoC Program Start ---")

    if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY_HERE" or not OPENAI_API_KEY:
        print(
            "WARNING: OpenAI API Key가 설정되지 않았습니다. 프로젝트 루트의 .env 파일 또는 환경 변수를 확인해주세요."
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
        "경기도 수원시 장안구 매매, 전세, 월세, 단기임대와 아파트, 오피스텔, 상가, 빌라 중 매매는 1천만원에서 2억사이, 월세 보증금 1천만원에서 1억사이, 월세 10만원에서 200만원사이 34평",
    ]

    for i, query in enumerate(natural_language_queries):
        print(f"\n--- Processing Query {i + 1}/{len(natural_language_queries)} ---")
        print(f"Query: '{query}'")
        try:
            print(f"Step 1: Extracting keywords for query: '{query}'")
            extracted_keywords = client.extract_keywords(query)
            print("Step 2: Successfully extracted keywords.")
            print(
                f"Extracted Keywords (Formatted Output): {json.dumps(extracted_keywords, ensure_ascii=False, indent=2)}"
            )
        except Exception as e:
            print(
                f"Step 2: Failed to extract keywords for query: '{query}'. Error: {e}"
            )
            print("--- Moving to next query ---")
            continue
        print(f"--- Finished processing Query {i + 1} ---")

    print("\n--- PoC Program End ---")


if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()
