"""
Home App - Redis 크롤링 결과 저장 서비스

이 모듈은 크롤링 완료 후 결과를 Redis에 직렬화하여 저장하고,
Board 앱에서 조회 가능한 Redis 키를 생성하는 기능을 제공합니다.
"""

import json
import hashlib
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
import redis

logger = logging.getLogger(__name__)


class RedisCrawlingResultStorage:
    """
    크롤링 결과를 Redis에 저장하고 관리하는 클래스

    주요 기능:
    - 크롤링 결과를 JSON 직렬화하여 Redis 저장 (TTL: 5분)
    - Redis 키 생성: search:{hash}:results 형태
    - Board 앱에서 조회 가능한 키 반환
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
            logger.info("Redis 크롤링 결과 저장 서비스 초기화 완료")
        except Exception as e:
            logger.error(f"Redis 연결 실패: {e}")
            raise

    def generate_search_key(self, keywords: Dict[str, Any]) -> str:
        """
        키워드를 기반으로 고유한 검색 키 생성

        Args:
            keywords: ChatGPT에서 추출된 키워드 딕셔너리

        Returns:
            str: search:{hash}:results 형태의 Redis 키
        """
        try:
            # 키워드를 정렬된 JSON 문자열로 변환
            keywords_str = json.dumps(keywords, sort_keys=True, ensure_ascii=False)

            # SHA256 해시 생성 (처음 16자리만 사용)
            hash_value = hashlib.sha256(keywords_str.encode('utf-8')).hexdigest()[:16]

            redis_key = f"search:{hash_value}:results"
            logger.info(f"검색 키 생성 완료: {redis_key}")

            return redis_key
        except Exception as e:
            logger.error(f"검색 키 생성 실패: {e}")
            raise

    def store_crawling_results(self, keywords: Dict[str, Any], properties: List[Dict[str, Any]]) -> str:
        """
        크롤링 결과를 Redis에 저장

        Args:
            keywords: ChatGPT에서 추출된 키워드
            properties: 크롤링된 매물 리스트 (영문 컬럼명 적용)

        Returns:
            str: 생성된 Redis 키
        """
        try:
            # Redis 키 생성
            redis_key = self.generate_search_key(keywords)

            # 저장할 데이터 구조 생성
            storage_data = {
                'keywords': keywords,
                'properties': properties,
                'property_count': len(properties),
                'timestamp': str(self._get_current_timestamp())
            }

            # JSON 직렬화
            serialized_data = json.dumps(storage_data, ensure_ascii=False, indent=2)

            # Redis에 저장 (TTL: 5분 = 300초)
            self.redis_client.setex(redis_key, 300, serialized_data)

            logger.info(f"크롤링 결과 저장 완료 - 키: {redis_key}, 매물 수: {len(properties)}")

            return redis_key
        except Exception as e:
            logger.error(f"크롤링 결과 저장 실패: {e}")
            raise

    def get_stored_results(self, redis_key: str) -> Optional[Dict[str, Any]]:
        """
        Redis에서 저장된 검색 결과 조회

        Args:
            redis_key: Redis 키

        Returns:
            Dict 또는 None: 저장된 데이터 또는 None (만료/미존재 시)
        """
        try:
            serialized_data = self.redis_client.get(redis_key)

            if serialized_data is None:
                logger.warning(f"Redis 키 만료 또는 미존재: {redis_key}")
                return None

            # JSON 역직렬화
            data = json.loads(serialized_data)

            logger.info(f"저장된 결과 조회 완료 - 키: {redis_key}, 매물 수: {data.get('property_count', 0)}")

            return data
        except Exception as e:
            logger.error(f"저장된 결과 조회 실패: {e}")
            return None

    def check_key_exists(self, redis_key: str) -> bool:
        """
        Redis 키 존재 여부 확인

        Args:
            redis_key: 확인할 Redis 키

        Returns:
            bool: 키 존재 여부
        """
        try:
            exists = self.redis_client.exists(redis_key)
            return bool(exists)
        except Exception as e:
            logger.error(f"키 존재 확인 실패: {e}")
            return False

    def get_key_ttl(self, redis_key: str) -> int:
        """
        Redis 키의 남은 TTL 확인

        Args:
            redis_key: 확인할 Redis 키

        Returns:
            int: 남은 시간(초), -1(키 미존재), -2(TTL 없음)
        """
        try:
            ttl = self.redis_client.ttl(redis_key)
            return ttl
        except Exception as e:
            logger.error(f"TTL 확인 실패: {e}")
            return -1

    def _get_current_timestamp(self):
        """현재 타임스탬프 반환"""
        from datetime import datetime
        return datetime.now()

    def clear_expired_keys(self) -> int:
        """
        만료된 검색 결과 키들을 수동으로 정리
        (Redis는 자동으로 만료되지만, 필요시 수동 정리 가능)

        Returns:
            int: 정리된 키 개수
        """
        try:
            pattern = "search:*:results"
            keys = self.redis_client.keys(pattern)

            expired_count = 0
            for key in keys:
                ttl = self.redis_client.ttl(key)
                if ttl <= 0:  # 만료되었거나 TTL이 없는 키
                    self.redis_client.delete(key)
                    expired_count += 1

            if expired_count > 0:
                logger.info(f"만료된 검색 결과 키 {expired_count}개 정리 완료")

            return expired_count
        except Exception as e:
            logger.error(f"만료된 키 정리 실패: {e}")
            return 0


# 싱글톤 인스턴스 생성
try:
    redis_storage = RedisCrawlingResultStorage()
except Exception as e:
    logger.error(f"Redis 크롤링 결과 저장 서비스 초기화 실패: {e}")
    redis_storage = None