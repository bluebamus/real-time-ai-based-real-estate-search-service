"""
Redis 사용자별 데이터 저장/조회 핸들러

사용자별 키워드와 크롤링 데이터를 Redis에 직렬화하여 저장하고
필요시 역직렬화하여 조회하는 기능을 제공합니다.

복합키 형식:
- 키워드: {user_id}:latest,keyword
- 크롤링 데이터: {user_id}:latest,crawling
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from django.conf import settings
import redis

logger = logging.getLogger(__name__)


class RedisUserDataHandler:
    """
    Redis 사용자별 데이터 핸들러

    사용자별 키워드와 크롤링 데이터를 직렬화/역직렬화하여
    Redis에 저장하고 조회하는 기능을 제공합니다.
    """

    def __init__(self):
        """Redis 핸들러 초기화"""
        logger.info("[REDIS] Redis 사용자 데이터 핸들러 초기화")

        # Redis 클라이언트 설정
        try:
            self.redis_client = redis.StrictRedis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True,  # 문자열 자동 디코딩
                socket_connect_timeout=5,
                socket_timeout=5
            )

            # Redis 연결 테스트
            self.redis_client.ping()
            logger.info("[REDIS] Redis 서버 연결 성공")

        except redis.ConnectionError as e:
            logger.error(f"[REDIS] Redis 서버 연결 실패: {e}")
            raise
        except Exception as e:
            logger.error(f"[REDIS] Redis 초기화 중 오류: {e}")
            raise

    def _generate_keyword_key(self, user_id: int) -> str:
        """
        사용자별 키워드 저장용 복합키 생성

        Args:
            user_id (int): 사용자 ID

        Returns:
            str: 복합키 ({user_id}:latest,keyword)
        """
        key = f"{user_id}:latest,keyword"
        logger.info(f"[REDIS] 키워드 복합키 생성: {key}")
        return key

    def _generate_crawling_key(self, user_id: int) -> str:
        """
        사용자별 크롤링 데이터 저장용 복합키 생성

        Args:
            user_id (int): 사용자 ID

        Returns:
            str: 복합키 ({user_id}:latest,crawling)
        """
        key = f"{user_id}:latest,crawling"
        logger.info(f"[REDIS] 크롤링 데이터 복합키 생성: {key}")
        return key

    def save_user_keywords(self, user_id: int, keywords: Dict[str, Any]) -> bool:
        """
        사용자의 검색 키워드를 Redis에 저장

        Args:
            user_id (int): 사용자 ID
            keywords (Dict[str, Any]): 저장할 키워드 딕셔너리

        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 복합키 생성
            redis_key = self._generate_keyword_key(user_id)

            # JSON 직렬화
            logger.info(f"[REDIS] 사용자 {user_id} 키워드 데이터 JSON 직렬화 시작")
            serialized_data = json.dumps(keywords, ensure_ascii=False, separators=(',', ':'))

            logger.info(f"[REDIS] JSON 직렬화 완료 (크기: {len(serialized_data)} 문자)")

            # Redis에 저장 (TTL: 24시간)
            logger.info(f"[REDIS] Redis 저장 시작 - 키: {redis_key}")
            self.redis_client.setex(redis_key, 86400, serialized_data)  # 24시간 TTL

            logger.info(f"[REDIS] 사용자 {user_id} 키워드 저장 완료")
            return True

        except (TypeError, ValueError) as e:
            logger.error(f"[REDIS] JSON 직렬화 실패: {e}")
            return False
        except redis.RedisError as e:
            logger.error(f"[REDIS] Redis 저장 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"[REDIS] 키워드 저장 중 오류 발생: {e}")
            return False

    def get_user_keywords(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        사용자의 검색 키워드를 Redis에서 조회

        Args:
            user_id (int): 사용자 ID

        Returns:
            Optional[Dict[str, Any]]: 조회된 키워드 딕셔너리 또는 None
        """
        try:
            # 복합키 생성
            redis_key = self._generate_keyword_key(user_id)

            logger.info(f"[REDIS] 사용자 {user_id} 키워드 조회 시작 - 키: {redis_key}")

            # Redis에서 데이터 조회
            serialized_data = self.redis_client.get(redis_key)

            if not serialized_data:
                logger.info(f"[REDIS] 사용자 {user_id} 키워드 데이터 없음")
                return None

            logger.info(f"[REDIS] Redis 데이터 조회 완료 (크기: {len(serialized_data)} 문자)")

            # JSON 역직렬화
            logger.info(f"[REDIS] JSON 역직렬화 시작")
            keywords = json.loads(serialized_data)

            logger.info(f"[REDIS] 사용자 {user_id} 키워드 조회 완료")
            return keywords

        except json.JSONDecodeError as e:
            logger.error(f"[REDIS] JSON 역직렬화 실패: {e}")
            return None
        except redis.RedisError as e:
            logger.error(f"[REDIS] Redis 조회 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"[REDIS] 키워드 조회 중 오류 발생: {e}")
            return None

    def save_user_crawling_data(self, user_id: int, crawling_data: List[Dict[str, Any]]) -> bool:
        """
        사용자의 크롤링 데이터를 Redis에 누적 저장

        Args:
            user_id (int): 사용자 ID
            crawling_data (List[Dict[str, Any]]): 저장할 크롤링 데이터 리스트

        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 복합키 생성
            redis_key = self._generate_crawling_key(user_id)

            logger.info(f"[REDIS] 사용자 {user_id} 크롤링 데이터 저장 시작")

            # 기존 데이터 조회
            existing_data = self._get_existing_crawling_data(user_id)

            # 새 데이터와 기존 데이터 병합 (누적 저장)
            if existing_data:
                logger.info(f"[REDIS] 기존 데이터 {len(existing_data)}개와 신규 데이터 {len(crawling_data)}개 병합")
                combined_data = existing_data + crawling_data
            else:
                logger.info(f"[REDIS] 신규 데이터 {len(crawling_data)}개 저장")
                combined_data = crawling_data

            # JSON 직렬화
            logger.info(f"[REDIS] 총 {len(combined_data)}개 매물 데이터 JSON 직렬화 시작")
            serialized_data = json.dumps(combined_data, ensure_ascii=False, separators=(',', ':'))

            logger.info(f"[REDIS] JSON 직렬화 완료 (크기: {len(serialized_data)} 문자)")

            # Redis에 저장 (TTL: 7일)
            logger.info(f"[REDIS] Redis 저장 시작 - 키: {redis_key}")
            self.redis_client.setex(redis_key, 604800, serialized_data)  # 7일 TTL

            logger.info(f"[REDIS] 사용자 {user_id} 크롤링 데이터 저장 완료")
            return True

        except (TypeError, ValueError) as e:
            logger.error(f"[REDIS] JSON 직렬화 실패: {e}")
            return False
        except redis.RedisError as e:
            logger.error(f"[REDIS] Redis 저장 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"[REDIS] 크롤링 데이터 저장 중 오류 발생: {e}")
            return False

    def get_user_crawling_data(self, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        사용자의 크롤링 데이터를 Redis에서 조회

        Args:
            user_id (int): 사용자 ID

        Returns:
            Optional[List[Dict[str, Any]]]: 조회된 크롤링 데이터 리스트 또는 None
        """
        try:
            # 복합키 생성
            redis_key = self._generate_crawling_key(user_id)

            logger.info(f"[REDIS] 사용자 {user_id} 크롤링 데이터 조회 시작 - 키: {redis_key}")

            # Redis에서 데이터 조회
            serialized_data = self.redis_client.get(redis_key)

            if not serialized_data:
                logger.info(f"[REDIS] 사용자 {user_id} 크롤링 데이터 없음")
                return None

            logger.info(f"[REDIS] Redis 데이터 조회 완료 (크기: {len(serialized_data)} 문자)")

            # JSON 역직렬화
            logger.info(f"[REDIS] JSON 역직렬화 시작")
            crawling_data = json.loads(serialized_data)

            logger.info(f"[REDIS] 사용자 {user_id} 크롤링 데이터 조회 완료 ({len(crawling_data)}개 매물)")
            return crawling_data

        except json.JSONDecodeError as e:
            logger.error(f"[REDIS] JSON 역직렬화 실패: {e}")
            return None
        except redis.RedisError as e:
            logger.error(f"[REDIS] Redis 조회 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"[REDIS] 크롤링 데이터 조회 중 오류 발생: {e}")
            return None

    def _get_existing_crawling_data(self, user_id: int) -> List[Dict[str, Any]]:
        """
        기존 크롤링 데이터 조회 (내부용)

        Args:
            user_id (int): 사용자 ID

        Returns:
            List[Dict[str, Any]]: 기존 크롤링 데이터 (없으면 빈 리스트)
        """
        existing_data = self.get_user_crawling_data(user_id)
        return existing_data if existing_data is not None else []

    def clear_user_data(self, user_id: int, data_type: str = "all") -> bool:
        """
        사용자 데이터 삭제

        Args:
            user_id (int): 사용자 ID
            data_type (str): 삭제할 데이터 타입 ("keyword", "crawling", "all")

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            deleted_keys = []

            if data_type in ["keyword", "all"]:
                keyword_key = self._generate_keyword_key(user_id)
                if self.redis_client.delete(keyword_key):
                    deleted_keys.append(keyword_key)

            if data_type in ["crawling", "all"]:
                crawling_key = self._generate_crawling_key(user_id)
                if self.redis_client.delete(crawling_key):
                    deleted_keys.append(crawling_key)

            logger.info(f"[REDIS] 사용자 {user_id} 데이터 삭제 완료: {deleted_keys}")
            return len(deleted_keys) > 0

        except redis.RedisError as e:
            logger.error(f"[REDIS] 데이터 삭제 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"[REDIS] 데이터 삭제 중 오류: {e}")
            return False

    def check_user_data_exists(self, user_id: int) -> Dict[str, bool]:
        """
        사용자 데이터 존재 여부 확인

        Args:
            user_id (int): 사용자 ID

        Returns:
            Dict[str, bool]: 각 데이터 타입별 존재 여부
        """
        try:
            keyword_key = self._generate_keyword_key(user_id)
            crawling_key = self._generate_crawling_key(user_id)

            result = {
                "keyword": bool(self.redis_client.exists(keyword_key)),
                "crawling": bool(self.redis_client.exists(crawling_key))
            }

            logger.info(f"[REDIS] 사용자 {user_id} 데이터 존재 확인: {result}")
            return result

        except redis.RedisError as e:
            logger.error(f"[REDIS] 데이터 존재 확인 실패: {e}")
            return {"keyword": False, "crawling": False}

    def get_data_info(self, user_id: int) -> Dict[str, Any]:
        """
        사용자 데이터 정보 조회 (크기, TTL 등)

        Args:
            user_id (int): 사용자 ID

        Returns:
            Dict[str, Any]: 데이터 정보
        """
        try:
            keyword_key = self._generate_keyword_key(user_id)
            crawling_key = self._generate_crawling_key(user_id)

            info = {
                "keyword": {
                    "exists": bool(self.redis_client.exists(keyword_key)),
                    "ttl": self.redis_client.ttl(keyword_key),
                    "size": 0
                },
                "crawling": {
                    "exists": bool(self.redis_client.exists(crawling_key)),
                    "ttl": self.redis_client.ttl(crawling_key),
                    "size": 0
                }
            }

            # 데이터 크기 정보 추가
            if info["keyword"]["exists"]:
                keyword_data = self.redis_client.get(keyword_key)
                info["keyword"]["size"] = len(keyword_data) if keyword_data else 0

            if info["crawling"]["exists"]:
                crawling_data = self.redis_client.get(crawling_key)
                info["crawling"]["size"] = len(crawling_data) if crawling_data else 0

            logger.info(f"[REDIS] 사용자 {user_id} 데이터 정보 조회 완료")
            return info

        except redis.RedisError as e:
            logger.error(f"[REDIS] 데이터 정보 조회 실패: {e}")
            return {"keyword": {"exists": False}, "crawling": {"exists": False}}


# 싱글톤 인스턴스
try:
    redis_handler = RedisUserDataHandler()
except Exception as e:
    logger.error(f"[REDIS] Redis 핸들러 초기화 실패: {e}")
    redis_handler = None


def get_redis_handler() -> Optional[RedisUserDataHandler]:
    """Redis 핸들러 인스턴스 반환"""
    return redis_handler


if __name__ == "__main__":
    # 테스트 실행
    if redis_handler:
        print("=== Redis 사용자 데이터 핸들러 테스트 ===")

        test_user_id = 12345
        test_keywords = {
            "address": "서울시 강남구",
            "transaction_type": "매매",
            "building_type": "아파트",
            "price_max": 800000000
        }

        test_crawling_data = [
            {
                "집주인": "테스트아파트1",
                "거래타입": "매매",
                "가격": 700000000,
                "address": "서울시 강남구"
            },
            {
                "집주인": "테스트아파트2",
                "거래타입": "매매",
                "가격": 750000000,
                "address": "서울시 강남구"
            }
        ]

        # 키워드 저장/조회 테스트
        print(f"\n1. 키워드 저장 테스트")
        success = redis_handler.save_user_keywords(test_user_id, test_keywords)
        print(f"저장 결과: {success}")

        print(f"\n2. 키워드 조회 테스트")
        retrieved_keywords = redis_handler.get_user_keywords(test_user_id)
        print(f"조회 결과: {retrieved_keywords}")

        # 크롤링 데이터 저장/조회 테스트
        print(f"\n3. 크롤링 데이터 저장 테스트")
        success = redis_handler.save_user_crawling_data(test_user_id, test_crawling_data)
        print(f"저장 결과: {success}")

        print(f"\n4. 크롤링 데이터 조회 테스트")
        retrieved_crawling = redis_handler.get_user_crawling_data(test_user_id)
        print(f"조회 결과: {len(retrieved_crawling) if retrieved_crawling else 0}개 데이터")

        # 데이터 존재 확인 테스트
        print(f"\n5. 데이터 존재 확인 테스트")
        exists = redis_handler.check_user_data_exists(test_user_id)
        print(f"존재 여부: {exists}")

        # 데이터 정보 조회 테스트
        print(f"\n6. 데이터 정보 조회 테스트")
        info = redis_handler.get_data_info(test_user_id)
        print(f"데이터 정보: {info}")

        # 정리
        print(f"\n7. 테스트 데이터 삭제")
        cleanup_success = redis_handler.clear_user_data(test_user_id)
        print(f"삭제 결과: {cleanup_success}")

    else:
        print("Redis 핸들러 초기화 실패 - Redis 서버 연결을 확인하세요")