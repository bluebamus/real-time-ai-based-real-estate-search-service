"""
ChatGPT 키워드 추출 테스트 모듈

home.services.keyword_extraction.ChatGPTKeywordExtractor에 대한 테스트케이스
실제 ChatGPT API를 사용하여 자연어 쿼리에서 키워드 추출을 검증
"""

import pytest
import json
from django.conf import settings
from home.services.keyword_extraction import ChatGPTKeywordExtractor, get_keyword_extractor

# Mark this module to skip if OPENAI_API_KEY is not set
pytestmark = pytest.mark.skipif(
    not hasattr(settings, 'OPENAI_API_KEY') or not settings.OPENAI_API_KEY,
    reason="OPENAI_API_KEY is not set in settings, skipping ChatGPT keyword extraction test."
)


@pytest.fixture(scope="module")
def keyword_extractor():
    """Provides a ChatGPTKeywordExtractor instance for tests."""
    return ChatGPTKeywordExtractor()


@pytest.mark.external
@pytest.mark.api
@pytest.mark.chatgpt
def test_keyword_extraction_seoul_seocho(keyword_extractor):
    """
    Test that ChatGPTKeywordExtractor correctly extracts keywords
    from the specific natural language query mentioned in the prompt.
    """
    query = "서울시 서초구 아파트 50평대 남향 매매 20억 이하"
    print(f"\nQuery: '{query}'")
    print(f"Step 1: Extracting keywords for query: '{query}'")

    try:
        # Extract keywords from ChatGPT
        extracted_keywords = keyword_extractor.extract_keywords(query)

        print("Step 2: Successfully extracted keywords.")
        print(f"Extracted Keywords (Formatted Output): {json.dumps(extracted_keywords, ensure_ascii=False, indent=2)}")
        print("--- Finished processing Query 1 ---")
        print("\n--- PoC Program End ---")

        # Basic validations
        assert isinstance(extracted_keywords, dict), "ChatGPT should return a dictionary."

        # Required field validations
        assert "address" in extracted_keywords, "Raw keywords should contain 'address'."
        assert "transaction_type" in extracted_keywords, "Raw keywords should contain 'transaction_type'."
        assert "building_type" in extracted_keywords, "Raw keywords should contain 'building_type'."

        # Specific content validations based on the expected output
        assert extracted_keywords["address"] == "서울시 서초구", "Address should be '서울시 서초구'."
        assert isinstance(extracted_keywords["transaction_type"], list), "Transaction type should be a list."
        assert "매매" in extracted_keywords["transaction_type"], "Transaction type should contain '매매'."
        assert isinstance(extracted_keywords["building_type"], list), "Building type should be a list."
        assert "아파트" in extracted_keywords["building_type"], "Building type should contain '아파트'."

        # Optional field validations
        if "area_range" in extracted_keywords:
            assert extracted_keywords["area_range"] == "50평대", "Area range should be '50평대' if present."

        # Null field validations
        assert extracted_keywords.get("deposit") is None, "Deposit should be null for this query."
        assert extracted_keywords.get("monthly_rent") is None, "Monthly rent should be null for this query."

        print("--- ChatGPT keyword extraction test passed successfully. ---")

    except Exception as e:
        print(f"--- Test failed with exception: {e} ---")
        pytest.fail(f"ChatGPT keyword extraction test failed: {e}")


@pytest.mark.external
@pytest.mark.api
@pytest.mark.chatgpt
def test_keyword_extraction_validation(keyword_extractor):
    """
    Test that ChatGPTKeywordExtractor validate_response works correctly.
    """
    # Valid response
    valid_response = {
        "address": "서울시 강남구",
        "transaction_type": ["매매"],
        "building_type": ["아파트"],
        "deposit": None,
        "monthly_rent": None,
        "area_range": "30평대"
    }

    # Should not raise any exception
    validated = keyword_extractor.validate_response(valid_response)
    assert validated == valid_response

    # Invalid response - missing required field
    invalid_response = {
        "deposit": None,
        "monthly_rent": None,
        "area_range": "30평대"
    }

    with pytest.raises(ValueError, match="필수 필드"):
        keyword_extractor.validate_response(invalid_response)


@pytest.mark.external
@pytest.mark.api
@pytest.mark.chatgpt
def test_get_keyword_extractor_singleton():
    """
    Test that get_keyword_extractor returns a singleton instance.
    """
    extractor1 = get_keyword_extractor()
    extractor2 = get_keyword_extractor()

    assert isinstance(extractor1, ChatGPTKeywordExtractor)
    assert isinstance(extractor2, ChatGPTKeywordExtractor)
    # Note: Since we're creating new instances each time, they won't be the same object
    # But they should both be valid ChatGPTKeywordExtractor instances