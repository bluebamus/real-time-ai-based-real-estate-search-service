import os
import json
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


class ChatGPTClient:
    """
    OpenAI ChatGPT API와의 통신을 담당하는 클라이언트
    자연어 쿼리에서 부동산 검색 키워드를 추출
    """

    def __init__(self):
        """ChatGPT 클라이언트 초기화"""
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE

        # OpenAI 클라이언트 설정 (New way)
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
            # 토큰 최적화된 프롬프트
            system_prompt = """부동산 검색어에서 키워드 추출. JSON 형식만 반환:
{
  "address": "시·도 + 시·군·구",
  "owner_type": "개인|사업자|전체",
  "transaction_type": "매매|전세|월세",
  "price_max": 숫자(원),
  "building_type": "아파트|빌라|오피스텔|원룸|투룸|상가|사무실|공장|토지",
  "area_pyeong": 숫자,
  "floor_info": "저층|중층|고층|전체",
  "direction": "남향|동향|서향|북향|남동향|남서향|북동향|북서향|전체",
  "tags": ["태그1", "태그2"],
  "updated_date": "오늘|3일이내|일주일이내|한달이내|전체"
}

기본값:\n- owner_type: \"전체\"\n- transaction_type: \"매매\"\n- building_type: \"아파트\"\n- floor_info: \"전체\"\n- direction: \"전체\"\n- updated_date: \"전체\"\n- tags: []"""

            user_prompt = f"쿼리: {query_text}"

            print(f"--- ChatGPTClient: Sending request to OpenAI API (model: {self.model}) ---")
            # ChatGPT API 호출 (New way)
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

            # 응답 파싱 (New way: response.choices is a list of ChatCompletionChoice objects)
            # Access message content via .message.content
            result = response.choices[0].message.content.strip()
            print(f"--- ChatGPTClient: Raw response content: {result[:100]}... ---") # Print first 100 chars
            keywords = json.loads(result)

            # Basic validation: ensure it's a dictionary
            if not isinstance(keywords, dict):
                raise ValueError("ChatGPT response is not a valid JSON dictionary.")

            print(f"--- ChatGPTClient: Successfully extracted keywords. Exiting extract_keywords. ---")
            logger.info(f"Successfully extracted raw keywords from query: {query_text[:50]}...")
            return keywords

        except json.JSONDecodeError as e:
            print(f"--- ChatGPTClient Error: Failed to parse ChatGPT response: {e}. Raw response: {result} ---")
            logger.error(f"Failed to parse ChatGPT response: {e}. Raw response: {result}")
            raise ValueError("ChatGPT 응답을 파싱할 수 없습니다. 응답이 유효한 JSON 형식이 아닙니다.")
        except Exception as e:
            print(f"--- ChatGPTClient Error: General API error: {e} ---")
            logger.error(f"ChatGPT API error: {e}")
            raise

    def validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        ChatGPT 응답의 기본 유효성 검사 (JSON 형식 및 딕셔너리 여부 확인)
        상세 검증 및 기본값 적용은 KeywordParser에서 수행.

        Args:
            response: ChatGPT API 응답 (딕셔너리 형태)

        Returns:
            검증된 키워드 딕셔너리 (변형 없음)
        """
        if not isinstance(response, dict):
            raise ValueError("Invalid response format: expected a dictionary.")
        return response

    def generate_search_summary(self, keywords: Dict[str, Any]) -> str:
        """
        검색 키워드를 자연어 요약문으로 변환

        Args:
            keywords: 검색 키워드 딕셔너리

        Returns:
            자연어 요약문
        """
        summary_parts = []

        # 주소
        if keywords.get('address'):
            summary_parts.append(keywords['address'])

        # 건물 종류
        if keywords.get('building_type') and keywords['building_type'] != '전체':
            summary_parts.append(keywords['building_type'])

        # 거래 타입
        if keywords.get('transaction_type'):
            summary_parts.append(keywords['transaction_type'])

        # 가격
        if keywords.get('price_max'):
            price_str = f"{keywords['price_max'] // 100000000}억" if keywords['price_max'] >= 100000000 else f"{keywords['price_max'] // 10000}만원"
            summary_parts.append(f"{price_str} 이하")

        # 평수
        if keywords.get('area_pyeong'):
            summary_parts.append(f"{keywords['area_pyeong']}평")

        # 층수
        if keywords.get('floor_info') and keywords['floor_info'] != '전체':
            summary_parts.append(keywords['floor_info'])

        # 방향
        if keywords.get('direction') and keywords['direction'] != '전체':
            summary_parts.append(keywords['direction'])

        return " ".join(summary_parts)
