"""
Board App - Redis 데이터 조회 서비스

이 모듈은 Home에서 생성된 Redis 키로 검색 결과를 조회하고,
추천 시스템에서 추천 매물을 조회하는 기능을 제공합니다.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from django.conf import settings
import redis

logger = logging.getLogger(__name__)


class RedisDataService:
    """
    Redis에서 검색 결과 및 추천 매물을 조회하는 서비스

    주요 기능:
    - Home에서 생성된 Redis 키로 검색 결과 조회
    - 추천 시스템에서 추천 매물 조회
    - JSON 역직렬화 및 데이터 변환
    - TTL 확인 및 만료 처리
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
            logger.info("Board Redis 데이터 서비스 초기화 완료")
        except Exception as e:
            logger.error(f"Board Redis 연결 실패: {e}")
            raise

    def get_search_results(self, redis_key: str) -> Optional[Dict[str, Any]]:
        """
        Redis에서 검색 결과 조회

        Args:
            redis_key: Home에서 생성된 Redis 키 (search:{hash}:results)

        Returns:
            Dict 또는 None: 검색 결과 데이터 또는 None (만료/미존재 시)
        """
        try:
            # Redis에서 데이터 조회
            serialized_data = self.redis_client.get(redis_key)

            if serialized_data is None:
                logger.warning(f"검색 결과 만료 또는 미존재: {redis_key}")
                return None

            # JSON 역직렬화
            search_data = json.loads(serialized_data)

            logger.info(f"검색 결과 조회 성공: {redis_key} - 매물 {search_data.get('property_count', 0)}개")

            return search_data

        except json.JSONDecodeError as e:
            logger.error(f"검색 결과 JSON 파싱 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"검색 결과 조회 실패: {e}")
            return None

    def get_properties_from_search_results(self, redis_key: str) -> List[Dict[str, Any]]:
        """
        검색 결과에서 매물 리스트만 추출

        Args:
            redis_key: Redis 키

        Returns:
            List[Dict]: 매물 리스트
        """
        try:
            search_data = self.get_search_results(redis_key)

            if search_data is None:
                return []

            properties = search_data.get('properties', [])

            logger.info(f"매물 리스트 추출 완료: {len(properties)}개")

            return properties

        except Exception as e:
            logger.error(f"매물 리스트 추출 실패: {e}")
            return []

    def get_recommendation_properties(self, user_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        추천 매물 조회

        Args:
            user_id: 사용자 ID (None인 경우 전체 사용자 추천)
            limit: 조회 개수

        Returns:
            List[Dict]: 추천 매물 리스트
        """
        try:
            if user_id:
                # 사용자별 추천 매물
                recommendation_key = f"user:{user_id}:recommendations"
            else:
                # 전체 사용자 추천 매물
                recommendation_key = "global:recommendations"

            # Redis에서 추천 매물 조회
            serialized_data = self.redis_client.get(recommendation_key)

            if serialized_data is None:
                logger.info(f"추천 매물 없음: {recommendation_key}")
                return []

            # JSON 역직렬화
            recommendations = json.loads(serialized_data)

            # 제한 개수만큼 반환
            limited_recommendations = recommendations[:limit]

            # 추천 매물에 is_recommendation 플래그 추가
            for prop in limited_recommendations:
                prop['is_recommendation'] = True

            logger.info(f"추천 매물 조회 완료: {len(limited_recommendations)}개")

            return limited_recommendations

        except json.JSONDecodeError as e:
            logger.error(f"추천 매물 JSON 파싱 실패: {e}")
            return []
        except Exception as e:
            logger.error(f"추천 매물 조회 실패: {e}")
            return []

    def get_combined_results(self, redis_key: str, user_id: Optional[int] = None,
                           recommendation_limit: int = 10, search_limit: int = 30) -> Dict[str, Any]:
        """
        추천 매물과 검색 결과를 결합하여 반환

        Args:
            redis_key: 검색 결과 Redis 키
            user_id: 사용자 ID
            recommendation_limit: 추천 매물 개수
            search_limit: 검색 결과 개수

        Returns:
            Dict: 결합된 결과 데이터
        """
        try:
            # 추천 매물 조회
            recommendations = self.get_recommendation_properties(user_id, recommendation_limit)

            # 검색 결과 조회
            search_properties = self.get_properties_from_search_results(redis_key)

            # 추천 매물에 포함되지 않은 검색 결과만 필터링
            # (실제 구현에서는 더 정교한 중복 제거 로직 필요)
            filtered_search_properties = search_properties[:search_limit]

            # 검색 결과에 is_recommendation 플래그 추가
            for prop in filtered_search_properties:
                prop['is_recommendation'] = False

            result = {
                'recommendations': recommendations,
                'search_results': filtered_search_properties,
                'total_recommendations': len(recommendations),
                'total_search_results': len(filtered_search_properties),
                'redis_key': redis_key
            }

            logger.info(f"결합 결과 생성 완료 - 추천: {len(recommendations)}개, 검색: {len(filtered_search_properties)}개")

            return result

        except Exception as e:
            logger.error(f"결합 결과 생성 실패: {e}")
            return {
                'recommendations': [],
                'search_results': [],
                'total_recommendations': 0,
                'total_search_results': 0,
                'redis_key': redis_key
            }

    def check_redis_key_valid(self, redis_key: str) -> bool:
        """
        Redis 키 유효성 확인

        Args:
            redis_key: 확인할 Redis 키

        Returns:
            bool: 키 유효 여부
        """
        try:
            # 키 존재 확인
            exists = self.redis_client.exists(redis_key)

            if not exists:
                return False

            # TTL 확인
            ttl = self.redis_client.ttl(redis_key)

            # TTL이 0 이하면 만료된 키
            if ttl <= 0:
                return False

            return True

        except Exception as e:
            logger.error(f"Redis 키 유효성 확인 실패: {e}")
            return False

    def get_redis_key_info(self, redis_key: str) -> Dict[str, Any]:
        """
        Redis 키 정보 조회

        Args:
            redis_key: Redis 키

        Returns:
            Dict: 키 정보
        """
        try:
            info = {
                'key': redis_key,
                'exists': self.redis_client.exists(redis_key),
                'ttl': self.redis_client.ttl(redis_key),
                'type': self.redis_client.type(redis_key),
                'size': None
            }

            if info['exists']:
                try:
                    data = self.redis_client.get(redis_key)
                    if data:
                        info['size'] = len(data)
                except:
                    pass

            return info

        except Exception as e:
            logger.error(f"Redis 키 정보 조회 실패: {e}")
            return {
                'key': redis_key,
                'exists': False,
                'ttl': -1,
                'type': 'none',
                'size': None
            }


# 싱글톤 인스턴스 생성
try:
    redis_data_service = RedisDataService()
except Exception as e:
    logger.error(f"Board Redis 데이터 서비스 초기화 실패: {e}")
    redis_data_service = None