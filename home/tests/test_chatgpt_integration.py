import pytest
import os
from django.conf import settings
from home.services.keyword_extraction import ChatGPTKeywordExtractor

# Mark this module to skip if OPENAI_API_KEY is not set
pytestmark = pytest.mark.skipif(
    not settings.OPENAI_API_KEY,
    reason="OPENAI_API_KEY is not set in .env, skipping ChatGPT integration test."
)

@pytest.fixture(scope="module")
def chatgpt_client():
    """Provides a ChatGPTKeywordExtractor instance for tests."""
    return ChatGPTKeywordExtractor()

@pytest.mark.external
@pytest.mark.api
@pytest.mark.chatgpt
def test_chatgpt_keyword_extraction(chatgpt_client):
    """
    Test that ChatGPTClient correctly extracts keywords from a natural language query.
    ChatGPT 응답을 바로 최종 결과로 사용하는 간소화된 플로우 테스트.
    """
    query = "서울시 강남구 30평대 아파트 매매 5억 이하 남향"
    print(f"\n--- Test Query: {query} ---")

    try:
        # ChatGPT API를 통한 키워드 추출 (최종 결과로 바로 사용)
        extracted_keywords = chatgpt_client.extract_keywords(query)
        print(f"Final Extracted Keywords from ChatGPT: {extracted_keywords}")

        # 기본 응답 형식 검증
        assert isinstance(extracted_keywords, dict), "ChatGPT should return a dictionary."

        # 필수 필드 검증
        assert "address" in extracted_keywords, "Response should contain 'address'."
        assert "transaction_type" in extracted_keywords, "Response should contain 'transaction_type'."
        assert "building_type" in extracted_keywords, "Response should contain 'building_type'."

        # ChatGPT API 새로운 응답 형식 검증
        assert isinstance(extracted_keywords["transaction_type"], list), "transaction_type should be a list."
        assert "매매" in extracted_keywords["transaction_type"], "transaction_type should contain '매매'."
        assert isinstance(extracted_keywords["building_type"], list), "building_type should be a list."
        assert "아파트" in extracted_keywords["building_type"], "building_type should contain '아파트'."

        # 주소 내용 검증
        assert "서울" in extracted_keywords["address"], "Address should contain '서울'."
        assert "강남" in extracted_keywords["address"], "Address should contain '강남'."

        # 선택 필드 타입 검증 (null이 아닌 경우)
        if "deposit" in extracted_keywords and extracted_keywords["deposit"] is not None:
            assert isinstance(extracted_keywords["deposit"], list), "deposit should be a list or null."

        if "monthly_rent" in extracted_keywords and extracted_keywords["monthly_rent"] is not None:
            assert isinstance(extracted_keywords["monthly_rent"], list), "monthly_rent should be a list or null."

        if "area_range" in extracted_keywords and extracted_keywords["area_range"] is not None:
            assert isinstance(extracted_keywords["area_range"], str), "area_range should be a string or null."

        print("--- ChatGPT keyword extraction test passed successfully. ---")

    except Exception as e:
        print(f"--- Test failed with exception: {e} ---")
        pytest.fail(f"ChatGPT keyword extraction test failed: {e}")


@pytest.mark.external
@pytest.mark.api
@pytest.mark.chatgpt
def test_chatgpt_area_range_spacing(chatgpt_client):
    """
    Test that ChatGPT returns area_range values with correct spacing.
    "~ 10평"과 "70평 ~" 형태의 공백 처리 검증.
    """
    query = "서울시 강남구 10평 이하 아파트 매매"
    print(f"\n--- Test Query for Small Area: {query} ---")

    try:
        # ChatGPT API를 통한 키워드 추출
        extracted_keywords = chatgpt_client.extract_keywords(query)
        print(f"Extracted Keywords: {extracted_keywords}")

        # area_range가 반환된 경우 공백 검증
        if "area_range" in extracted_keywords and extracted_keywords["area_range"] is not None:
            area_range = extracted_keywords["area_range"]
            print(f"Area Range Value: '{area_range}'")

            # "~ 10평" 형태인지 확인 (공백이 있어야 함)
            if area_range.startswith('~'):
                assert ' ' in area_range, f"area_range '{area_range}' should contain space: '~ 10평'"
                print(f"[OK] Correct spacing found in '{area_range}'")

            # "70평 ~" 형태인지 확인 (공백이 있어야 함)
            if area_range.endswith('~'):
                assert ' ' in area_range, f"area_range '{area_range}' should contain space: '70평 ~'"
                print(f"[OK] Correct spacing found in '{area_range}'")

        print("--- Area range spacing test passed successfully. ---")

    except Exception as e:
        print(f"--- Test failed with exception: {e} ---")
        pytest.fail(f"Area range spacing test failed: {e}")
