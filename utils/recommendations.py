"""
Utils - 추천 시스템 엔진

이 모듈은 Redis Sorted Sets를 활용한 부동산 매물 추천 시스템을 구현합니다.
사용자별 키워드 스코어와 전체 사용자 키워드 스코어를 관리하여 개인화된 추천을 제공합니다.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from django.conf import settings
import redis

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Redis Sorted Sets를 활용한 추천 엔진

    주요 기능:
    - 사용자별 키워드 스코어 관리 (TTL: 1시간)
    - 전체 사용자 키워드 스코어 관리 (TTL: 1시간)
    - 스코어 기반 추천 매물 조회
    - 키워드 스코어 업데이트 및 누적
    """

    def __init__(self):
        """Redis 클라이언트 초기화"""
        try:
            self.redis_client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True
            )
            # Redis 연결 테스트
            self.redis_client.ping()
            logger.info("추천 엔진 Redis 연결 완료")

            # TTL 설정 (1시간 = 3600초)
            self.ttl_seconds = 3600

        except Exception as e:
            logger.error(f"추천 엔진 Redis 연결 실패: {e}")
            raise

    def update_user_keyword_scores(self, user_id: int, keywords: Dict[str, Any]) -> None:
        """
        사용자별 키워드 스코어 업데이트

        Args:
            user_id: 사용자 ID
            keywords: ChatGPT에서 추출된 키워드 딕셔너리
        """
        try:
            # 키워드별 카테고리 분류 및 스코어 업데이트
            self._update_keyword_category_scores(user_id, keywords, is_global=False)

            logger.info(f"사용자 {user_id} 키워드 스코어 업데이트 완료")

        except Exception as e:
            logger.error(f"사용자 키워드 스코어 업데이트 실패 (user_id: {user_id}): {e}")

    def update_global_keyword_scores(self, keywords: Dict[str, Any]) -> None:
        """
        전체 사용자 키워드 스코어 업데이트

        Args:
            keywords: ChatGPT에서 추출된 키워드 딕셔너리
        """
        try:
            # 전체 사용자 키워드 스코어 업데이트
            self._update_keyword_category_scores(None, keywords, is_global=True)

            logger.info("전체 사용자 키워드 스코어 업데이트 완료")

        except Exception as e:
            logger.error(f"전체 사용자 키워드 스코어 업데이트 실패: {e}")

    def _update_keyword_category_scores(self, user_id: Optional[int], keywords: Dict[str, Any], is_global: bool) -> None:
        """
        키워드 카테고리별 스코어 업데이트

        Args:
            user_id: 사용자 ID (전체 사용자인 경우 None)
            keywords: 키워드 딕셔너리
            is_global: 전체 사용자 스코어 여부
        """
        try:
            # 카테고리별 키워드 매핑
            category_mappings = {
                'address': ['address'],
                'transaction_type': ['transaction_type'],
                'building_type': ['building_type'],
                'price': ['deposit', 'monthly_rent', 'sale_price'],
                'area': ['area_range']
            }

            for category, keyword_keys in category_mappings.items():
                for keyword_key in keyword_keys:
                    if keyword_key in keywords and keywords[keyword_key] is not None:
                        keyword_value = keywords[keyword_key]

                        # 키워드 값 처리 및 스코어 업데이트
                        self._process_keyword_value(user_id, category, keyword_key, keyword_value, is_global)

        except Exception as e:
            logger.error(f"키워드 카테고리별 스코어 업데이트 실패: {e}")

    def _process_keyword_value(self, user_id: Optional[int], category: str, keyword_key: str,
                             keyword_value: Any, is_global: bool) -> None:
        """
        개별 키워드 값 처리 및 스코어 업데이트

        Args:
            user_id: 사용자 ID
            category: 키워드 카테고리
            keyword_key: 키워드 키
            keyword_value: 키워드 값
            is_global: 전체 사용자 스코어 여부
        """
        try:
            # 키워드 값을 문자열 리스트로 변환
            keyword_strings = self._extract_keyword_strings(keyword_value)

            for keyword_str in keyword_strings:
                # Redis 키 생성
                redis_key = self._generate_redis_key(user_id, category, is_global)

                # 스코어 업데이트 (기존 스코어에 1점 추가)
                self.redis_client.zincrby(redis_key, 1, keyword_str)

                # TTL 설정
                self.redis_client.expire(redis_key, self.ttl_seconds)

                logger.debug(f"키워드 스코어 업데이트: {redis_key} -> {keyword_str} (+1)")

        except Exception as e:
            logger.error(f"키워드 값 처리 실패: {e}")

    def _extract_keyword_strings(self, keyword_value: Any) -> List[str]:
        """
        키워드 값에서 문자열 리스트 추출

        Args:
            keyword_value: 키워드 값 (문자열, 리스트, 딕셔너리 등)

        Returns:
            List[str]: 키워드 문자열 리스트
        """
        try:
            if isinstance(keyword_value, str):
                return [keyword_value]
            elif isinstance(keyword_value, list):
                return [str(item) for item in keyword_value if item is not None]
            elif isinstance(keyword_value, dict):
                # min, max 값들을 문자열로 변환
                return [f"{k}:{v}" for k, v in keyword_value.items() if v is not None]
            else:
                return [str(keyword_value)]

        except Exception as e:
            logger.error(f"키워드 문자열 추출 실패: {e}")
            return []

    def _generate_redis_key(self, user_id: Optional[int], category: str, is_global: bool) -> str:
        """
        Redis 키 생성

        Args:
            user_id: 사용자 ID
            category: 키워드 카테고리
            is_global: 전체 사용자 스코어 여부

        Returns:
            str: Redis 키
        """
        if is_global:
            return f"global:keywords:{category}"
        else:
            return f"user:{user_id}:keywords:{category}"

    def get_user_top_keywords(self, user_id: int, category: str, limit: int = 10) -> List[Tuple[str, float]]:
        """
        사용자별 상위 키워드 조회

        Args:
            user_id: 사용자 ID
            category: 키워드 카테고리
            limit: 조회 개수

        Returns:
            List[Tuple[str, float]]: (키워드, 스코어) 튜플 리스트
        """
        try:
            redis_key = self._generate_redis_key(user_id, category, is_global=False)

            # 상위 키워드 조회 (스코어 내림차순)
            top_keywords = self.redis_client.zrevrange(redis_key, 0, limit - 1, withscores=True)

            logger.debug(f"사용자 {user_id} 상위 키워드 조회: {category} - {len(top_keywords)}개")

            return top_keywords

        except Exception as e:
            logger.error(f"사용자 상위 키워드 조회 실패: {e}")
            return []

    def get_global_top_keywords(self, category: str, limit: int = 10) -> List[Tuple[str, float]]:
        """
        전체 사용자 상위 키워드 조회

        Args:
            category: 키워드 카테고리
            limit: 조회 개수

        Returns:
            List[Tuple[str, float]]: (키워드, 스코어) 튜플 리스트
        """
        try:
            redis_key = self._generate_redis_key(None, category, is_global=True)

            # 상위 키워드 조회 (스코어 내림차순)
            top_keywords = self.redis_client.zrevrange(redis_key, 0, limit - 1, withscores=True)

            logger.debug(f"전체 사용자 상위 키워드 조회: {category} - {len(top_keywords)}개")

            return top_keywords

        except Exception as e:
            logger.error(f"전체 사용자 상위 키워드 조회 실패: {e}")
            return []

    def get_recommendation_properties(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        사용자별 추천 매물 조회

        Args:
            user_id: 사용자 ID
            limit: 추천 매물 개수

        Returns:
            List[Dict]: 추천 매물 리스트
        """
        try:
            # 사용자별 상위 키워드들을 조합하여 추천 매물 생성
            # 실제 구현에서는 더 복잡한 추천 알고리즘 적용 가능

            recommendation_key = f"user:{user_id}:recommendations"

            # 추천 매물이 Redis에 저장되어 있는 경우 조회
            stored_recommendations = self.redis_client.get(recommendation_key)

            if stored_recommendations:
                recommendations = json.loads(stored_recommendations)
                logger.info(f"사용자 {user_id} 저장된 추천 매물 조회: {len(recommendations)}개")
                return recommendations[:limit]
            else:
                logger.info(f"사용자 {user_id} 저장된 추천 매물 없음")
                return []

        except Exception as e:
            logger.error(f"추천 매물 조회 실패: {e}")
            return []

    def store_recommendation_properties(self, user_id: int, properties: List[Dict[str, Any]]) -> None:
        """
        추천 매물 저장

        Args:
            user_id: 사용자 ID
            properties: 추천 매물 리스트
        """
        try:
            recommendation_key = f"user:{user_id}:recommendations"

            # JSON 직렬화하여 저장
            serialized_properties = json.dumps(properties, ensure_ascii=False)

            # TTL과 함께 저장
            self.redis_client.setex(recommendation_key, self.ttl_seconds, serialized_properties)

            logger.info(f"사용자 {user_id} 추천 매물 저장 완료: {len(properties)}개")

        except Exception as e:
            logger.error(f"추천 매물 저장 실패: {e}")

    def get_global_recommendation_properties(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        전체 사용자 기반 인기 추천 매물 조회

        Args:
            limit: 추천 매물 개수

        Returns:
            List[Dict]: 추천 매물 리스트
        """
        try:
            recommendation_key = "global:recommendations"

            # 전체 추천 매물 조회
            stored_recommendations = self.redis_client.get(recommendation_key)

            if stored_recommendations:
                recommendations = json.loads(stored_recommendations)
                logger.info(f"전체 사용자 추천 매물 조회: {len(recommendations)}개")
                return recommendations[:limit]
            else:
                logger.info("전체 사용자 추천 매물 없음")
                return []

        except Exception as e:
            logger.error(f"전체 추천 매물 조회 실패: {e}")
            return []

    def store_global_recommendation_properties(self, properties: List[Dict[str, Any]]) -> None:
        """
        전체 사용자 기반 추천 매물 저장

        Args:
            properties: 추천 매물 리스트
        """
        try:
            recommendation_key = "global:recommendations"

            # JSON 직렬화하여 저장
            serialized_properties = json.dumps(properties, ensure_ascii=False)

            # TTL과 함께 저장
            self.redis_client.setex(recommendation_key, self.ttl_seconds, serialized_properties)

            logger.info(f"전체 사용자 추천 매물 저장 완료: {len(properties)}개")

        except Exception as e:
            logger.error(f"전체 추천 매물 저장 실패: {e}")


# 싱글톤 인스턴스 생성
try:
    recommendation_engine = RecommendationEngine()
except Exception as e:
    logger.error(f"추천 엔진 초기화 실패: {e}")
    recommendation_engine = None