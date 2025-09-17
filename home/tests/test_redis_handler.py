"""
Redis 핸들러 테스트 모듈

utils.redis_handler.RedisUserDataHandler에 대한 테스트케이스
직렬화/역직렬화, 데이터 저장/조회, 복합키 생성 등을 검증
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from utils.redis_handler import RedisUserDataHandler, get_redis_handler


class TestRedisUserDataHandler:
    """Redis 사용자 데이터 핸들러 테스트"""

    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        # Mock Redis 클라이언트 생성
        self.mock_redis = MagicMock()

        # RedisUserDataHandler 인스턴스 생성 (Redis 초기화를 Mock으로 우회)
        with patch('utils.redis_handler.redis.StrictRedis', return_value=self.mock_redis):
            self.handler = RedisUserDataHandler()

    def test_handler_initialization(self):
        """핸들러 초기화 테스트"""
        assert self.handler.redis_client is not None
        # ping() 메서드가 호출되었는지 확인
        self.mock_redis.ping.assert_called_once()

    def test_generate_keyword_key(self):
        """키워드 복합키 생성 테스트"""
        user_id = 12345
        expected_key = "12345:latest,keyword"

        key = self.handler._generate_keyword_key(user_id)

        assert key == expected_key

    def test_generate_crawling_key(self):
        """크롤링 데이터 복합키 생성 테스트"""
        user_id = 12345
        expected_key = "12345:latest,crawling"

        key = self.handler._generate_crawling_key(user_id)

        assert key == expected_key

    def test_save_user_keywords_success(self):
        """사용자 키워드 저장 성공 테스트"""
        user_id = 12345
        test_keywords = {
            "address": "서울시 강남구",
            "transaction_type": "매매",
            "building_type": "아파트",
            "price_max": 800000000
        }

        # Redis setex 메서드가 성공적으로 실행되도록 Mock 설정
        self.mock_redis.setex.return_value = True

        result = self.handler.save_user_keywords(user_id, test_keywords)

        # 저장 성공 확인
        assert result is True

        # setex 메서드가 올바른 인자로 호출되었는지 확인
        self.mock_redis.setex.assert_called_once()
        call_args = self.mock_redis.setex.call_args

        # 복합키 확인
        expected_key = "12345:latest,keyword"
        assert call_args[0][0] == expected_key

        # TTL 확인 (24시간 = 86400초)
        assert call_args[0][1] == 86400

        # JSON 직렬화된 데이터 확인
        serialized_data = call_args[0][2]
        deserialized_data = json.loads(serialized_data)
        assert deserialized_data == test_keywords

    def test_get_user_keywords_success(self):
        """사용자 키워드 조회 성공 테스트"""
        user_id = 12345
        test_keywords = {
            "address": "서울시 강남구",
            "transaction_type": "매매",
            "building_type": "아파트"
        }

        # Redis get 메서드가 직렬화된 데이터를 반환하도록 Mock 설정
        serialized_data = json.dumps(test_keywords, ensure_ascii=False, separators=(',', ':'))
        self.mock_redis.get.return_value = serialized_data

        result = self.handler.get_user_keywords(user_id)

        # 조회 성공 및 데이터 일치 확인
        assert result is not None
        assert result == test_keywords

        # get 메서드가 올바른 복합키로 호출되었는지 확인
        expected_key = "12345:latest,keyword"
        self.mock_redis.get.assert_called_once_with(expected_key)

    def test_get_user_keywords_not_found(self):
        """사용자 키워드 조회 실패 테스트 (데이터 없음)"""
        user_id = 12345

        # Redis get 메서드가 None을 반환하도록 Mock 설정
        self.mock_redis.get.return_value = None

        result = self.handler.get_user_keywords(user_id)

        # 데이터가 없을 때 None 반환 확인
        assert result is None

    def test_save_user_crawling_data_new_data(self):
        """사용자 크롤링 데이터 저장 테스트 (신규 데이터)"""
        user_id = 12345
        test_crawling_data = [
            {
                "집주인": "테스트아파트1",
                "거래타입": "매매",
                "가격": 700000000,
                "address": "서울시 강남구"
            },
            {
                "집주인": "테스트아파트2",
                "거래타입": "전세",
                "가격": 400000000,
                "address": "서울시 강남구"
            }
        ]

        # 기존 데이터가 없다고 Mock 설정
        self.mock_redis.get.return_value = None
        self.mock_redis.setex.return_value = True

        result = self.handler.save_user_crawling_data(user_id, test_crawling_data)

        # 저장 성공 확인
        assert result is True

        # setex 메서드 호출 확인
        self.mock_redis.setex.assert_called_once()
        call_args = self.mock_redis.setex.call_args

        # 복합키 확인
        expected_key = "12345:latest,crawling"
        assert call_args[0][0] == expected_key

        # TTL 확인 (7일 = 604800초)
        assert call_args[0][1] == 604800

        # 직렬화된 데이터가 원본과 일치하는지 확인
        serialized_data = call_args[0][2]
        deserialized_data = json.loads(serialized_data)
        assert deserialized_data == test_crawling_data

    def test_save_user_crawling_data_accumulate(self):
        """사용자 크롤링 데이터 누적 저장 테스트"""
        user_id = 12345
        existing_data = [
            {"집주인": "기존아파트1", "가격": 600000000}
        ]
        new_data = [
            {"집주인": "신규아파트1", "가격": 700000000}
        ]

        # 기존 데이터가 있다고 Mock 설정
        existing_serialized = json.dumps(existing_data, ensure_ascii=False, separators=(',', ':'))
        self.mock_redis.get.return_value = existing_serialized
        self.mock_redis.setex.return_value = True

        result = self.handler.save_user_crawling_data(user_id, new_data)

        # 저장 성공 확인
        assert result is True

        # setex 메서드 호출 확인
        call_args = self.mock_redis.setex.call_args
        serialized_data = call_args[0][2]
        deserialized_data = json.loads(serialized_data)

        # 기존 데이터와 신규 데이터가 합쳐졌는지 확인
        assert len(deserialized_data) == 2
        assert deserialized_data[0] == existing_data[0]
        assert deserialized_data[1] == new_data[0]

    def test_get_user_crawling_data_success(self):
        """사용자 크롤링 데이터 조회 성공 테스트"""
        user_id = 12345
        test_crawling_data = [
            {
                "집주인": "테스트아파트",
                "거래타입": "매매",
                "가격": 700000000
            }
        ]

        # Redis get 메서드가 직렬화된 데이터를 반환하도록 Mock 설정
        serialized_data = json.dumps(test_crawling_data, ensure_ascii=False, separators=(',', ':'))
        self.mock_redis.get.return_value = serialized_data

        result = self.handler.get_user_crawling_data(user_id)

        # 조회 성공 및 데이터 일치 확인
        assert result is not None
        assert result == test_crawling_data

        # 복합키로 조회되었는지 확인
        expected_key = "12345:latest,crawling"
        self.mock_redis.get.assert_called_once_with(expected_key)

    def test_serialization_deserialization_consistency(self):
        """직렬화/역직렬화 일관성 테스트"""
        user_id = 12345

        # 복잡한 테스트 데이터 (한글, 특수문자, 다양한 데이터 타입 포함)
        test_keywords = {
            "address": "서울시 강남구 테헤란로 123번길",
            "transaction_type": "매매",
            "building_type": "아파트",
            "price_max": 1000000000,
            "area_pyeong": 35.5,
            "tags": ["신축", "역세권", "학군우수", "남향"],
            "special_chars": "!@#$%^&*()",
            "korean_text": "가나다라마바사아자차카타파하"
        }

        self.mock_redis.setex.return_value = True

        # 저장
        save_result = self.handler.save_user_keywords(user_id, test_keywords)
        assert save_result is True

        # 저장 시 사용된 직렬화 데이터 추출
        call_args = self.mock_redis.setex.call_args
        serialized_data = call_args[0][2]

        # 직렬화 데이터를 다시 역직렬화하여 원본과 비교
        deserialized_data = json.loads(serialized_data)
        assert deserialized_data == test_keywords

        # 타입 검증
        assert isinstance(deserialized_data["price_max"], int)
        assert isinstance(deserialized_data["area_pyeong"], float)
        assert isinstance(deserialized_data["tags"], list)

    def test_check_user_data_exists(self):
        """사용자 데이터 존재 여부 확인 테스트"""
        user_id = 12345

        # Redis exists 메서드 Mock 설정
        def mock_exists(key):
            if "keyword" in key:
                return 1  # 키워드 데이터 존재
            elif "crawling" in key:
                return 0  # 크롤링 데이터 없음
            return 0

        self.mock_redis.exists.side_effect = mock_exists

        result = self.handler.check_user_data_exists(user_id)

        # 결과 검증
        assert result["keyword"] is True
        assert result["crawling"] is False

        # exists 메서드가 올바른 키로 호출되었는지 확인
        assert self.mock_redis.exists.call_count == 2

    def test_clear_user_data_all(self):
        """사용자 데이터 전체 삭제 테스트"""
        user_id = 12345

        # Redis delete 메서드가 성공적으로 실행되도록 Mock 설정
        self.mock_redis.delete.return_value = 1

        result = self.handler.clear_user_data(user_id, "all")

        # 삭제 성공 확인
        assert result is True

        # delete 메서드가 두 번 호출되었는지 확인 (키워드 + 크롤링)
        assert self.mock_redis.delete.call_count == 2

    def test_clear_user_data_keyword_only(self):
        """사용자 키워드 데이터만 삭제 테스트"""
        user_id = 12345

        self.mock_redis.delete.return_value = 1

        result = self.handler.clear_user_data(user_id, "keyword")

        # 삭제 성공 확인
        assert result is True

        # delete 메서드가 한 번만 호출되었는지 확인
        assert self.mock_redis.delete.call_count == 1

        # 키워드 키로 호출되었는지 확인
        call_args = self.mock_redis.delete.call_args
        called_key = call_args[0][0]
        assert "keyword" in called_key

    def test_get_data_info(self):
        """사용자 데이터 정보 조회 테스트"""
        user_id = 12345

        # Mock 설정
        def mock_exists(key):
            return 1 if "keyword" in key else 0

        def mock_ttl(key):
            return 86400 if "keyword" in key else -2

        def mock_get(key):
            if "keyword" in key:
                return '{"test": "data"}'
            return None

        self.mock_redis.exists.side_effect = mock_exists
        self.mock_redis.ttl.side_effect = mock_ttl
        self.mock_redis.get.side_effect = mock_get

        result = self.handler.get_data_info(user_id)

        # 결과 검증
        assert "keyword" in result
        assert "crawling" in result

        # 키워드 데이터 정보 확인
        keyword_info = result["keyword"]
        assert keyword_info["exists"] is True
        assert keyword_info["ttl"] == 86400
        assert keyword_info["size"] > 0

        # 크롤링 데이터 정보 확인
        crawling_info = result["crawling"]
        assert crawling_info["exists"] is False

    def test_json_serialization_error_handling(self):
        """JSON 직렬화 오류 처리 테스트"""
        user_id = 12345

        # 직렬화 불가능한 데이터 (함수 객체 등)
        invalid_data = {
            "address": "서울시 강남구",
            "invalid_func": lambda x: x  # 직렬화 불가능
        }

        result = self.handler.save_user_keywords(user_id, invalid_data)

        # 저장 실패 확인
        assert result is False

    def test_json_deserialization_error_handling(self):
        """JSON 역직렬화 오류 처리 테스트"""
        user_id = 12345

        # 잘못된 JSON 데이터 Mock 설정
        self.mock_redis.get.return_value = "invalid json data"

        result = self.handler.get_user_keywords(user_id)

        # 조회 실패 시 None 반환 확인
        assert result is None

    def test_redis_connection_error_handling(self):
        """Redis 연결 오류 처리 테스트"""
        user_id = 12345
        test_data = {"address": "서울시 강남구"}

        # Redis 오류 Mock 설정
        import redis
        self.mock_redis.setex.side_effect = redis.RedisError("Connection failed")

        result = self.handler.save_user_keywords(user_id, test_data)

        # 저장 실패 확인
        assert result is False

    def test_get_redis_handler_singleton(self):
        """Redis 핸들러 싱글톤 테스트"""
        with patch('utils.redis_handler.redis_handler') as mock_handler:
            mock_instance = MagicMock()
            mock_handler.return_value = mock_instance

            handler1 = get_redis_handler()
            handler2 = get_redis_handler()

            # 같은 인스턴스 반환 확인
            assert handler1 is handler2


# Integration tests for Redis functionality
@pytest.mark.integration
class TestRedisIntegration:
    """Redis 통합 테스트 (실제 Redis 서버 필요)"""

    def test_redis_real_connection(self):
        """실제 Redis 연결 테스트"""
        try:
            handler = RedisUserDataHandler()

            # 간단한 테스트 데이터
            test_user_id = 99999  # 테스트용 사용자 ID
            test_keywords = {"test": "integration_test"}

            # 저장/조회/삭제 테스트
            save_result = handler.save_user_keywords(test_user_id, test_keywords)
            assert save_result is True

            retrieved_data = handler.get_user_keywords(test_user_id)
            assert retrieved_data == test_keywords

            # 정리
            handler.clear_user_data(test_user_id, "all")

        except Exception:
            # Redis 서버가 없거나 연결할 수 없는 경우 테스트 스킵
            pytest.skip("Redis server not available")

    @pytest.mark.parametrize("user_id,data_type", [
        (1001, "keyword"),
        (1002, "crawling"),
        (1003, "all")
    ])
    def test_multiple_users_data_isolation(self, user_id, data_type):
        """다중 사용자 데이터 격리 테스트"""
        try:
            handler = RedisUserDataHandler()

            test_data = {f"test_user_{user_id}": f"data_{data_type}"}

            if data_type == "keyword":
                save_result = handler.save_user_keywords(user_id, test_data)
                retrieved = handler.get_user_keywords(user_id)
            else:  # crawling or all
                save_result = handler.save_user_crawling_data(user_id, [test_data])
                retrieved = handler.get_user_crawling_data(user_id)

            assert save_result is True
            assert retrieved is not None

            # 정리
            handler.clear_user_data(user_id, "all")

        except Exception:
            pytest.skip("Redis server not available")