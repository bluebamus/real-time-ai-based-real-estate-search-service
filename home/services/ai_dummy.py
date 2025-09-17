"""
ChatGPT API 더미 클래스

실제 API 호출 없이 하드코딩된 반환값을 제공하는 더미 구현
개발 및 테스트 환경에서 API 비용 절약 및 일관된 테스트를 위해 사용
"""

import json
import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class DummyChatGPTClient:
    """
    ChatGPT API의 더미 구현 클래스

    실제 OpenAI API 호출 없이 사전 정의된 키워드 패턴에 따라
    하드코딩된 응답을 반환합니다.
    """

    def __init__(self):
        """더미 클라이언트 초기화"""
        logger.info("[DUMMY ChatGPT] 더미 ChatGPT 클라이언트 초기화")
        self.dummy_mode = True

        # 더미 응답 패턴 정의
        self.response_patterns = self._initialize_response_patterns()

    def _initialize_response_patterns(self) -> List[Dict[str, Any]]:
        """더미 응답 패턴 초기화"""
        patterns = [
            # 서울 강남구 패턴
            {
                "keywords": ["서울", "강남", "강남구"],
                "response": {
                    "address": "서울시 강남구",
                    "transaction_type": "매매",
                    "building_type": "아파트",
                    "price_max": 800000000,  # 8억
                    "area_pyeong": 30,
                    "floor_info": "중층",
                    "direction": "남향",
                    "tags": ["신축", "역세권"],
                    "updated_date": "최근"
                }
            },
            # 서울 서초구 패턴
            {
                "keywords": ["서울", "서초", "서초구"],
                "response": {
                    "address": "서울시 서초구",
                    "transaction_type": "매매",
                    "building_type": "아파트",
                    "price_max": 700000000,  # 7억
                    "area_pyeong": 28,
                    "floor_info": "고층",
                    "direction": "남동향",
                    "tags": ["학군", "대단지"],
                    "updated_date": "최근"
                }
            },
            # 경기도 수원시 패턴
            {
                "keywords": ["경기", "수원", "수원시", "장안구"],
                "response": {
                    "address": "경기도 수원시 장안구",
                    "transaction_type": "전세",
                    "building_type": "아파트",
                    "price_max": 400000000,  # 4억
                    "area_pyeong": 25,
                    "floor_info": "중층",
                    "direction": "남서향",
                    "tags": ["교통편리", "주차공간"],
                    "updated_date": "최근"
                }
            },
            # 부산 해운대 패턴
            {
                "keywords": ["부산", "해운대"],
                "response": {
                    "address": "부산시 해운대구",
                    "transaction_type": "매매",
                    "building_type": "아파트",
                    "price_max": 600000000,  # 6억
                    "area_pyeong": 32,
                    "floor_info": "고층",
                    "direction": "남향",
                    "tags": ["바다전망", "리조트"],
                    "updated_date": "최근"
                }
            },
            # 전세 패턴
            {
                "keywords": ["전세"],
                "response": {
                    "address": "서울시 마포구",
                    "transaction_type": "전세",
                    "building_type": "아파트",
                    "price_max": 500000000,  # 5억
                    "area_pyeong": 27,
                    "floor_info": "중층",
                    "direction": "남향",
                    "tags": ["역세권"],
                    "updated_date": "최근"
                }
            },
            # 월세 패턴
            {
                "keywords": ["월세"],
                "response": {
                    "address": "서울시 성동구",
                    "transaction_type": "월세",
                    "building_type": "오피스텔",
                    "price_max": 150000000,  # 보증금 1.5억
                    "area_pyeong": 15,
                    "floor_info": "고층",
                    "direction": "동향",
                    "tags": ["원룸", "신축"],
                    "updated_date": "최근"
                }
            },
            # 오피스텔 패턴
            {
                "keywords": ["오피스텔"],
                "response": {
                    "address": "서울시 영등포구",
                    "transaction_type": "매매",
                    "building_type": "오피스텔",
                    "price_max": 400000000,  # 4억
                    "area_pyeong": 20,
                    "floor_info": "고층",
                    "direction": "서향",
                    "tags": ["투자", "임대"],
                    "updated_date": "최근"
                }
            },
            # 빌라 패턴
            {
                "keywords": ["빌라", "다세대"],
                "response": {
                    "address": "서울시 은평구",
                    "transaction_type": "매매",
                    "building_type": "빌라",
                    "price_max": 300000000,  # 3억
                    "area_pyeong": 22,
                    "floor_info": "저층",
                    "direction": "남향",
                    "tags": ["주택", "조용"],
                    "updated_date": "최근"
                }
            },
            # 기본 패턴 (매칭되지 않는 경우)
            {
                "keywords": ["default"],
                "response": {
                    "address": "서울시 강남구",
                    "transaction_type": "매매",
                    "building_type": "아파트",
                    "price_max": 500000000,  # 5억
                    "area_pyeong": 30,
                    "floor_info": "중층",
                    "direction": "남향",
                    "tags": ["일반"],
                    "updated_date": "최근"
                }
            }
        ]

        logger.info(f"[DUMMY ChatGPT] {len(patterns)}개의 응답 패턴 초기화 완료")
        return patterns

    def extract_keywords(self, query_text: str) -> Dict[str, Any]:
        """
        자연어 쿼리에서 키워드 추출 (더미 구현)

        Args:
            query_text (str): 사용자의 자연어 검색 쿼리

        Returns:
            Dict[str, Any]: 추출된 키워드 딕셔너리
        """
        logger.info(f"[DUMMY ChatGPT] 키워드 추출 요청: '{query_text}'")

        # 입력값 검증
        if not query_text or not isinstance(query_text, str):
            logger.warning("[DUMMY ChatGPT] 유효하지 않은 쿼리 텍스트 - 기본 패턴 사용")
            query_text = "기본 검색"

        # 쿼리 텍스트를 소문자로 변환하여 패턴 매칭
        query_lower = query_text.lower()

        # 패턴 매칭하여 적절한 응답 선택
        selected_response = None
        matched_pattern = None

        for pattern in self.response_patterns[:-1]:  # 기본 패턴 제외하고 순회
            for keyword in pattern["keywords"]:
                if keyword.lower() in query_lower:
                    selected_response = pattern["response"].copy()
                    matched_pattern = pattern["keywords"]
                    logger.info(f"[DUMMY ChatGPT] 패턴 매칭 성공: {matched_pattern}")
                    break
            if selected_response:
                break

        # 매칭되는 패턴이 없으면 기본 패턴 사용
        if not selected_response:
            selected_response = self.response_patterns[-1]["response"].copy()
            matched_pattern = ["default"]
            logger.info("[DUMMY ChatGPT] 기본 패턴 사용")

        # 쿼리에서 추가 정보 추출하여 응답 수정
        self._enhance_response_from_query(query_text, selected_response)

        # 검증 및 기본값 적용
        validated_response = self.validate_response(selected_response)

        logger.info(f"[DUMMY ChatGPT] 키워드 추출 완료 - 매칭 패턴: {matched_pattern}")
        return validated_response

    def _enhance_response_from_query(self, query: str, response: Dict[str, Any]) -> None:
        """쿼리에서 추가 정보를 추출하여 응답 보강"""
        query_lower = query.lower()

        # 거래 타입 감지
        if "전세" in query_lower:
            response["transaction_type"] = "전세"
        elif "월세" in query_lower:
            response["transaction_type"] = "월세"
        elif "매매" in query_lower:
            response["transaction_type"] = "매매"

        # 건물 타입 감지
        if "오피스텔" in query_lower:
            response["building_type"] = "오피스텔"
        elif "빌라" in query_lower or "다세대" in query_lower:
            response["building_type"] = "빌라"
        elif "원룸" in query_lower:
            response["building_type"] = "원룸"
        elif "투룸" in query_lower:
            response["building_type"] = "투룸"

        # 가격 정보 감지
        price_patterns = [
            (r"(\d+)억", lambda x: int(x) * 100000000),
            (r"(\d+)만원", lambda x: int(x) * 10000),
            (r"(\d+)천만", lambda x: int(x) * 10000000)
        ]

        for pattern, converter in price_patterns:
            match = re.search(pattern, query)
            if match:
                response["price_max"] = converter(match.group(1))
                break

        # 평수 정보 감지
        pyeong_match = re.search(r"(\d+)평", query)
        if pyeong_match:
            response["area_pyeong"] = int(pyeong_match.group(1))

        # 방향 정보 감지
        directions = ["남향", "동향", "서향", "북향", "남동향", "남서향", "북동향", "북서향"]
        for direction in directions:
            if direction in query:
                response["direction"] = direction
                break

    def validate_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        응답 검증 및 기본값 적용

        Args:
            response (Dict[str, Any]): 검증할 응답 딕셔너리

        Returns:
            Dict[str, Any]: 검증된 응답 딕셔너리

        Raises:
            ValueError: 필수 키워드가 누락된 경우
        """
        logger.info("[DUMMY ChatGPT] 응답 검증 시작")

        # 필수 필드 검증
        if not response.get('address'):
            raise ValueError("주소 정보(시·도 + 시·군·구)는 필수입니다.")

        # 기본값 적용
        defaults = {
            'owner_type': '개인',
            'transaction_type': '매매',
            'building_type': '아파트',
            'floor_info': '중층',
            'direction': '남향',
            'tags': [],
            'updated_date': '최근'
        }

        for key, default_value in defaults.items():
            if key not in response or response[key] is None:
                response[key] = default_value

        # 데이터 타입 검증 및 변환
        if 'price_max' in response and response['price_max']:
            try:
                response['price_max'] = int(response['price_max'])
            except (ValueError, TypeError):
                response['price_max'] = None

        if 'area_pyeong' in response and response['area_pyeong']:
            try:
                response['area_pyeong'] = float(response['area_pyeong'])
            except (ValueError, TypeError):
                response['area_pyeong'] = None

        logger.info("[DUMMY ChatGPT] 응답 검증 완료")
        return response

    def get_available_patterns(self) -> List[str]:
        """사용 가능한 패턴 목록 반환"""
        patterns = []
        for pattern in self.response_patterns[:-1]:  # 기본 패턴 제외
            patterns.append(", ".join(pattern["keywords"]))
        return patterns

    def test_all_patterns(self) -> Dict[str, Any]:
        """모든 패턴에 대한 테스트 수행"""
        logger.info("[DUMMY ChatGPT] 모든 패턴 테스트 시작")

        test_results = {}

        for i, pattern in enumerate(self.response_patterns[:-1]):  # 기본 패턴 제외
            test_query = pattern["keywords"][0] + " 아파트"
            try:
                result = self.extract_keywords(test_query)
                test_results[f"pattern_{i}_{pattern['keywords'][0]}"] = {
                    "query": test_query,
                    "success": True,
                    "result": result
                }
            except Exception as e:
                test_results[f"pattern_{i}_{pattern['keywords'][0]}"] = {
                    "query": test_query,
                    "success": False,
                    "error": str(e)
                }

        logger.info(f"[DUMMY ChatGPT] 패턴 테스트 완료: {len(test_results)}개 패턴")
        return test_results


# 싱글톤 인스턴스
dummy_chatgpt_client = DummyChatGPTClient()


def get_dummy_client() -> DummyChatGPTClient:
    """더미 클라이언트 인스턴스 반환"""
    return dummy_chatgpt_client


if __name__ == "__main__":
    # 테스트 실행
    client = DummyChatGPTClient()

    test_queries = [
        "서울 강남구 아파트 매매 5억 이하",
        "경기도 수원시 전세 3억",
        "부산 해운대 오피스텔 월세",
        "서울 서초구 30평 아파트",
        "빌라 매매 3억 이하"
    ]

    print("=== 더미 ChatGPT 클라이언트 테스트 ===")
    for query in test_queries:
        print(f"\n쿼리: {query}")
        try:
            result = client.extract_keywords(query)
            print(f"결과: {json.dumps(result, ensure_ascii=False, indent=2)}")
        except Exception as e:
            print(f"오류: {e}")

    # 모든 패턴 테스트
    print("\n=== 모든 패턴 테스트 ===")
    test_results = client.test_all_patterns()
    for pattern_name, result in test_results.items():
        status = "성공" if result["success"] else "실패"
        print(f"{pattern_name}: {status}")
        if not result["success"]:
            print(f"  오류: {result['error']}")