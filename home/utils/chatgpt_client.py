import json
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
import openai

logger = logging.getLogger(__name__)


class ChatGPTClient:
    """
    ChatGPT API 클라이언트
    실제 OpenAI API를 사용하여 자연어 쿼리를 처리
    """

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

        # OpenAI 클라이언트 초기화
        openai.api_key = self.api_key

    def process_real_estate_query(self, query: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        부동산 검색 쿼리를 ChatGPT API로 처리

        Args:
            query: 사용자의 자연어 검색 쿼리
            user_context: 사용자 컨텍스트 (이전 검색 기록 등)

        Returns:
            처리된 검색 결과 딕셔너리
        """
        try:
            # 시스템 프롬프트 구성
            system_prompt = self._get_real_estate_system_prompt()

            # 사용자 프롬프트 구성
            user_prompt = self._construct_user_prompt(query, user_context)

            # ChatGPT API 호출
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
                temperature=0.3,
            )

            # 응답 파싱
            result = self._parse_chatgpt_response(response.choices[0].message.content)
            result['original_query'] = query

            logger.info(f"ChatGPT API 호출 성공: {query[:50]}...")
            return result

        except Exception as e:
            logger.error(f"ChatGPT API 오류: {str(e)}")
            # API 오류 시 더미 응답으로 폴백
            return self._get_fallback_response(query)

    def _get_real_estate_system_prompt(self) -> str:
        """부동산 검색 전용 시스템 프롬프트"""
        return """
        당신은 한국 부동산 검색 전문 AI 어시스턴트입니다.
        사용자의 자연어 검색 쿼리를 분석하여 다음 정보를 추출해주세요:

        1. 지역 정보 (시/구/동 단위)
        2. 부동산 타입 (아파트, 오피스텔, 빌라, 단독주택 등)
        3. 거래 유형 (매매, 전세, 월세)
        4. 가격 범위
        5. 면적/평수
        6. 추가 조건 (역세권, 학군, 신축 등)

        응답은 반드시 다음 JSON 형식으로 해주세요:
        {
            "location": {"city": "", "district": "", "dong": ""},
            "property_type": "",
            "transaction_type": "",
            "price_range": {"min": 0, "max": 0, "unit": ""},
            "size_range": {"min": 0, "max": 0, "unit": "평"},
            "additional_conditions": [],
            "processed_query": "",
            "suggestions": []
        }
        """

    def _construct_user_prompt(self, query: str, user_context: Optional[Dict] = None) -> str:
        """사용자 프롬프트 구성"""
        prompt = f"다음 부동산 검색 쿼리를 분석해주세요: '{query}'"

        if user_context and 'recent_searches' in user_context:
            recent = user_context['recent_searches'][:3]  # 최근 3개 검색만
            prompt += f"\n\n사용자의 최근 검색 기록: {recent}"

        return prompt

    def _parse_chatgpt_response(self, response_text: str) -> Dict[str, Any]:
        """ChatGPT 응답을 파싱하여 구조화된 데이터로 변환"""
        try:
            # JSON 응답 파싱 시도
            return json.loads(response_text)
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 텍스트에서 정보 추출
            logger.warning("ChatGPT 응답 JSON 파싱 실패, 텍스트 파싱 시도")
            return self._extract_from_text(response_text)

    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """텍스트 응답에서 부동산 정보 추출"""
        # 간단한 키워드 추출 로직
        return {
            "location": {"city": "", "district": "", "dong": ""},
            "property_type": "",
            "transaction_type": "",
            "price_range": {"min": 0, "max": 0, "unit": ""},
            "size_range": {"min": 0, "max": 0, "unit": "평"},
            "additional_conditions": [],
            "processed_query": text[:200],
            "suggestions": []
        }

    def _get_fallback_response(self, query: str) -> Dict[str, Any]:
        """API 오류 시 폴백 응답"""
        return {
            "original_query": query,
            "location": {"city": "", "district": "", "dong": ""},
            "property_type": "",
            "transaction_type": "",
            "price_range": {"min": 0, "max": 0, "unit": ""},
            "size_range": {"min": 0, "max": 0, "unit": "평"},
            "additional_conditions": [],
            "processed_query": f"{query} (API 오류로 인한 기본 처리)",
            "suggestions": [f"{query} 아파트", f"{query} 전세"],
            "error": "ChatGPT API 연결 오류"
        }


class DummyChatGPTClient:
    """
    더미 ChatGPT 클라이언트
    실제 API 호출 없이 테스트용 응답을 반환
    """

    def __init__(self):
        logger.info("DummyChatGPTClient 초기화됨 (테스트 모드)")

    def process_real_estate_query(self, query: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        더미 부동산 검색 쿼리 처리
        """
        logger.info(f"더미 쿼리 처리: {query}")

        # 간단한 키워드 분석
        location_info = self._extract_location(query)
        property_type = self._extract_property_type(query)
        transaction_type = self._extract_transaction_type(query)

        return {
            "original_query": query,
            "location": location_info,
            "property_type": property_type,
            "transaction_type": transaction_type,
            "price_range": self._extract_price_range(query),
            "size_range": self._extract_size_range(query),
            "additional_conditions": self._extract_conditions(query),
            "processed_query": f"{query} → 더미 처리 완료",
            "suggestions": [
                f"{query} 매매",
                f"{query} 전세",
                f"{query} 월세",
                f"{query} 신축"
            ][:3],
            "dummy": True
        }

    def _extract_location(self, query: str) -> Dict[str, str]:
        """쿼리에서 지역 정보 추출"""
        locations = {
            "강남": {"city": "서울시", "district": "강남구", "dong": ""},
            "서초": {"city": "서울시", "district": "서초구", "dong": ""},
            "송파": {"city": "서울시", "district": "송파구", "dong": ""},
            "마포": {"city": "서울시", "district": "마포구", "dong": ""},
        }

        for key, location in locations.items():
            if key in query:
                return location

        return {"city": "서울시", "district": "", "dong": ""}

    def _extract_property_type(self, query: str) -> str:
        """쿼리에서 부동산 타입 추출"""
        property_types = {
            "아파트": "아파트",
            "오피스텔": "오피스텔",
            "빌라": "빌라",
            "주택": "단독주택"
        }

        for keyword, prop_type in property_types.items():
            if keyword in query:
                return prop_type

        return "아파트"  # 기본값

    def _extract_transaction_type(self, query: str) -> str:
        """쿼리에서 거래 유형 추출"""
        if "매매" in query:
            return "매매"
        elif "전세" in query:
            return "전세"
        elif "월세" in query:
            return "월세"

        return "매매"  # 기본값

    def _extract_price_range(self, query: str) -> Dict[str, Any]:
        """쿼리에서 가격 범위 추출"""
        return {"min": 0, "max": 100000, "unit": "만원"}

    def _extract_size_range(self, query: str) -> Dict[str, Any]:
        """쿼리에서 면적 범위 추출"""
        return {"min": 20, "max": 50, "unit": "평"}

    def _extract_conditions(self, query: str) -> List[str]:
        """쿼리에서 추가 조건 추출"""
        conditions = []

        condition_keywords = {
            "역세권": "역세권",
            "학군": "좋은 학군",
            "신축": "신축",
            "리모델링": "리모델링",
            "남향": "남향",
        }

        for keyword, condition in condition_keywords.items():
            if keyword in query:
                conditions.append(condition)

        return conditions


def get_chatgpt_client() -> ChatGPTClient:
    """
    ChatGPT 클라이언트 팩토리 함수
    설정에 따라 실제 클라이언트 또는 더미 클라이언트 반환
    """
    if settings.DEBUG or not settings.OPENAI_API_KEY:
        logger.info("더미 ChatGPT 클라이언트 사용")
        return DummyChatGPTClient()
    else:
        logger.info("실제 ChatGPT API 클라이언트 사용")
        return ChatGPTClient()