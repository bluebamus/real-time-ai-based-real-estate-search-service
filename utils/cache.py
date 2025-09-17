"""
Redis 캐시 관리 모듈
"""
import redis
import json
import hashlib
import logging
from typing import Any, Optional, List, Dict
from datetime import datetime, timedelta
from django.conf import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis 캐시 관리 클래스
    검색 결과, 추천 데이터, 세션 정보 등을 캐싱
    """

    def __init__(self):
        """Redis 클라이언트 초기화"""
        self.redis_client = redis.StrictRedis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
            charset='utf-8'
        )
        self.default_ttl = 300  # 기본 TTL: 5분

    def get_cached_results(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """
        캐시된 검색 결과 조회

        Args:
            cache_key: Redis 캐시 키

        Returns:
            캐시된 데이터 또는 None
        """
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for key: {cache_key}")
                return json.loads(cached_data)
            else:
                logger.info(f"Cache miss for key: {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Error getting cached results: {e}")
            return None

    def set_cached_results(self, cache_key: str, data: List[Dict[str, Any]], ttl: int = None):
        """
        검색 결과 캐싱

        Args:
            cache_key: Redis 캐시 키
            data: 저장할 데이터
            ttl: Time To Live (초 단위)
        """
        try:
            ttl = ttl or self.default_ttl
            json_data = json.dumps(data, ensure_ascii=False)
            self.redis_client.setex(cache_key, ttl, json_data)
            logger.info(f"Cached data for key: {cache_key} with TTL: {ttl}s")
        except Exception as e:
            logger.error(f"Error setting cached results: {e}")

    def generate_cache_key(self, keywords: Dict[str, Any]) -> str:
        """
        키워드를 기반으로 고유한 캐시 키 생성

        Args:
            keywords: 검색 키워드 딕셔너리

        Returns:
            생성된 캐시 키
        """
        # 키워드를 정렬하여 일관된 해시 생성
        sorted_keywords = json.dumps(keywords, sort_keys=True, ensure_ascii=False)
        hash_value = hashlib.md5(sorted_keywords.encode('utf-8')).hexdigest()
        return f"search:{hash_value}:results"

    def get_or_set(self, key: str, func, ttl: int = None) -> Any:
        """
        캐시 조회 또는 설정 (캐시 미스 시 함수 실행)

        Args:
            key: 캐시 키
            func: 캐시 미스 시 실행할 함수
            ttl: Time To Live

        Returns:
            캐시된 데이터 또는 함수 실행 결과
        """
        # 캐시 조회
        cached_value = self.redis_client.get(key)
        if cached_value:
            logger.info(f"Cache hit: {key}")
            return json.loads(cached_value)

        # 캐시 미스 - 함수 실행
        logger.info(f"Cache miss: {key}, executing function...")
        result = func()

        # 결과 캐싱
        if result is not None:
            ttl = ttl or self.default_ttl
            self.redis_client.setex(key, ttl, json.dumps(result, ensure_ascii=False))

        return result

    def invalidate(self, pattern: str):
        """
        패턴에 맞는 캐시 무효화

        Args:
            pattern: 삭제할 키 패턴 (예: "search:*")
        """
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted_count = self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted_count} cache keys with pattern: {pattern}")
            else:
                logger.info(f"No keys found for pattern: {pattern}")
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")

    def set_user_session(self, session_id: str, user_data: Dict[str, Any], ttl: int = 1800):
        """
        사용자 세션 저장

        Args:
            session_id: 세션 ID
            user_data: 사용자 데이터
            ttl: 세션 유효 시간 (기본 30분)
        """
        try:
            key = f"session:{session_id}"
            self.redis_client.setex(key, ttl, json.dumps(user_data))
            logger.info(f"Session saved: {session_id}")
        except Exception as e:
            logger.error(f"Error saving session: {e}")

    def get_user_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 세션 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 데이터 또는 None
        """
        try:
            key = f"session:{session_id}"
            session_data = self.redis_client.get(key)
            if session_data:
                # 세션 조회 시 TTL 연장
                self.redis_client.expire(key, 1800)
                return json.loads(session_data)
            return None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None

    def update_keyword_score(self, user_id: Optional[int], category: str, keyword: str, increment: float = 1.0):
        """
        키워드 스코어 업데이트 (Sorted Set)

        Args:
            user_id: 사용자 ID (None이면 전체 사용자)
            category: 카테고리 (address, transaction_type 등)
            keyword: 키워드
            increment: 증가값
        """
        try:
            if user_id:
                key = f"user:{user_id}:keywords:{category}"
            else:
                key = f"global:keywords:{category}"

            self.redis_client.zincrby(key, increment, keyword)
            logger.debug(f"Updated keyword score: {key} - {keyword} (+{increment})")
        except Exception as e:
            logger.error(f"Error updating keyword score: {e}")

    def get_top_keywords(self, user_id: Optional[int], category: str, count: int = 5) -> List[tuple]:
        """
        상위 키워드 조회

        Args:
            user_id: 사용자 ID (None이면 전체 사용자)
            category: 카테고리
            count: 조회할 개수

        Returns:
            (키워드, 스코어) 튜플 리스트
        """
        try:
            if user_id:
                key = f"user:{user_id}:keywords:{category}"
            else:
                key = f"global:keywords:{category}"

            results = self.redis_client.zrevrange(key, 0, count - 1, withscores=True)
            return [(keyword, score) for keyword, score in results]
        except Exception as e:
            logger.error(f"Error getting top keywords: {e}")
            return []

    def store_recommendations(self, user_id: Optional[int], properties: List[Dict[str, Any]]):
        """
        추천 매물 저장

        Args:
            user_id: 사용자 ID (None이면 전체 추천)
            properties: 추천 매물 리스트
        """
        try:
            if user_id:
                key = f"user:{user_id}:recommendations"
            else:
                key = "global:recommendations"

            # TTL 없이 저장 (Celery Beat로 주기적 갱신)
            self.redis_client.set(key, json.dumps(properties[:10], ensure_ascii=False))
            logger.info(f"Stored {len(properties[:10])} recommendations for {key}")
        except Exception as e:
            logger.error(f"Error storing recommendations: {e}")

    def get_recommendations(self, user_id: Optional[int]) -> List[Dict[str, Any]]:
        """
        추천 매물 조회

        Args:
            user_id: 사용자 ID (None이면 전체 추천)

        Returns:
            추천 매물 리스트
        """
        try:
            if user_id:
                key = f"user:{user_id}:recommendations"
            else:
                key = "global:recommendations"

            recommendations = self.redis_client.get(key)
            if recommendations:
                return json.loads(recommendations)
            return []
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []

    def health_check(self) -> bool:
        """
        Redis 연결 상태 확인

        Returns:
            연결 성공 여부
        """
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회

        Returns:
            캐시 통계 정보
        """
        try:
            info = self.redis_client.info()
            stats = {
                'used_memory': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0),
                'total_keys': self.redis_client.dbsize(),
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': 0
            }

            # 히트율 계산
            total_requests = stats['hits'] + stats['misses']
            if total_requests > 0:
                stats['hit_rate'] = round((stats['hits'] / total_requests) * 100, 2)

            return stats
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}