"""
ChatGPT 키워드 추출기 통합 테스트

home/services/backup/keyword_extraction.py의 싱글톤 인스턴스를 사용한 통합 테스트
성공 케이스와 실패 케이스에 대한 검증을 포함
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# 프로젝트 루트를 Python path에 추가
# home/tests/ -> home/ -> project_root/
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from home.services.backup.keyword_extraction import get_keyword_extractor


class TestChatGPTKeywordExtractor:
    """ChatGPT 키워드 추출기 통합 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 셋업"""
        self.extractor = get_keyword_extractor()

    def _create_mock_response(self, content):
        """Mock 응답 객체 생성 헬퍼"""
        mock_choice = Mock()
        mock_choice.message.content = content

        mock_response = Mock()
        mock_response.choices = [mock_choice]

        return mock_response

    def test_singleton_instance(self):
        """싱글톤 인스턴스 테스트"""
        extractor1 = get_keyword_extractor()
        extractor2 = get_keyword_extractor()
        assert extractor1 is extractor2, "싱글톤 인스턴스가 동일해야 합니다"

    def test_success_case_comprehensive_query(self):
        """성공 케이스 테스트 - 종합 쿼리"""
        response_data = {
            "status": "success",
            "data": {
                "address": "경기도 수원시 장안구",
                "transaction_type": ["매매", "전세", "월세", "단기임대"],
                "building_type": ["아파트", "오피스텔", "상가", "빌라"],
                "sale_price": [10000000, 200000000],
                "deposit": [10000000, 100000000],
                "monthly_rent": [100000, 2000000],
                "area_range": "70평~"
            },
            "error": None
        }

        mock_response = self._create_mock_response(json.dumps(response_data, ensure_ascii=False))

        with patch.object(self.extractor.client.chat.completions, 'create', return_value=mock_response):
            query = "경기도 수원시 장안구 매매, 전세, 월세, 단기임대와 아파트, 오피스텔, 상가, 빌라 중 매매는 1천만원에서 2억사이, 월세 보증금 1천만원에서 1억사이, 월세 10만원에서 200만원사이 100평"
            result = self.extractor.extract_keywords(query)

            assert result["status"] == "success"
            assert result["data"]["address"] == "경기도 수원시 장안구"
            assert "매매" in result["data"]["transaction_type"]
            assert "아파트" in result["data"]["building_type"]
            assert result["data"]["sale_price"] == [10000000, 200000000]

    def test_success_case_area_range_small(self):
        """성공 케이스 테스트 - 8평 -> ~10평"""
        response_data = {
            "status": "success",
            "data": {
                "address": "서울시 강남구",
                "transaction_type": ["매매"],
                "building_type": ["아파트"],
                "sale_price": None,
                "deposit": None,
                "monthly_rent": None,
                "area_range": "~10평"
            },
            "error": None
        }

        mock_response = self._create_mock_response(json.dumps(response_data, ensure_ascii=False))

        with patch.object(self.extractor.client.chat.completions, 'create', return_value=mock_response):
            query = "서울시 강남구 아파트 매매 8평"
            result = self.extractor.extract_keywords(query)

            assert result["status"] == "success"
            assert result["data"]["area_range"] == "~10평"

    def test_success_case_area_range_large(self):
        """성공 케이스 테스트 - 75평 -> 70평~"""
        response_data = {
            "status": "success",
            "data": {
                "address": "부산시 해운대구",
                "transaction_type": ["전세"],
                "building_type": ["오피스텔"],
                "sale_price": None,
                "deposit": None,
                "monthly_rent": None,
                "area_range": "70평~"
            },
            "error": None
        }

        mock_response = self._create_mock_response(json.dumps(response_data, ensure_ascii=False))

        with patch.object(self.extractor.client.chat.completions, 'create', return_value=mock_response):
            query = "부산시 해운대구 오피스텔 전세 75평"
            result = self.extractor.extract_keywords(query)

            assert result["status"] == "success"
            assert result["data"]["area_range"] == "70평~"

    def test_success_case_area_range_last_mentioned(self):
        """성공 케이스 테스트 - 마지막 언급된 면적 범위"""
        response_data = {
            "status": "success",
            "data": {
                "address": "인천시 남동구",
                "transaction_type": ["월세"],
                "building_type": ["빌라"],
                "sale_price": None,
                "deposit": None,
                "monthly_rent": None,
                "area_range": "40평대"
            },
            "error": None
        }

        mock_response = self._create_mock_response(json.dumps(response_data, ensure_ascii=False))

        with patch.object(self.extractor.client.chat.completions, 'create', return_value=mock_response):
            query = "인천시 남동구 빌라 월세 20평대에서 30평대까지 고려하다가 최종 40평대"
            result = self.extractor.extract_keywords(query)

            assert result["status"] == "success"
            assert result["data"]["area_range"] == "40평대"

    def test_error_case_missing_address(self):
        """에러 케이스 테스트 - MISSING_ADDRESS"""
        response_data = {
            "status": "error",
            "data": None,
            "error": {
                "code": "MISSING_ADDRESS",
                "message": "Address missing or insufficient (only 시도 without 시군구)"
            }
        }

        mock_response = self._create_mock_response(json.dumps(response_data, ensure_ascii=False))

        with patch.object(self.extractor.client.chat.completions, 'create', return_value=mock_response):
            query = "경기도 매매 아파트 1억"

            with pytest.raises(ValueError) as exc_info:
                self.extractor.extract_keywords(query)

            assert "MISSING_ADDRESS" in str(exc_info.value)

    def test_error_case_invalid_address_combination(self):
        """에러 케이스 테스트 - 잘못된 주소 조합"""
        response_data = {
            "status": "error",
            "data": None,
            "error": {
                "code": "MISSING_ADDRESS",
                "message": "Address missing, insufficient (only 시도 without 시군구), or invalid combination"
            }
        }

        mock_response = self._create_mock_response(json.dumps(response_data, ensure_ascii=False))

        with patch.object(self.extractor.client.chat.completions, 'create', return_value=mock_response):
            query = "부산시 강남구 매매 아파트 2억"

            with pytest.raises(ValueError) as exc_info:
                self.extractor.extract_keywords(query)

            assert "MISSING_ADDRESS" in str(exc_info.value)

    def test_error_case_missing_transaction_type(self):
        """에러 케이스 테스트 - MISSING_TRANSACTION_TYPE"""
        response_data = {
            "status": "error",
            "data": None,
            "error": {
                "code": "MISSING_TRANSACTION_TYPE",
                "message": "Transaction type required"
            }
        }

        mock_response = self._create_mock_response(json.dumps(response_data, ensure_ascii=False))

        with patch.object(self.extractor.client.chat.completions, 'create', return_value=mock_response):
            query = "서울시 강남구 아파트 30평대"

            with pytest.raises(ValueError) as exc_info:
                self.extractor.extract_keywords(query)

            assert "MISSING_TRANSACTION_TYPE" in str(exc_info.value)

    def test_error_case_missing_building_type(self):
        """에러 케이스 테스트 - MISSING_BUILDING_TYPE"""
        response_data = {
            "status": "error",
            "data": None,
            "error": {
                "code": "MISSING_BUILDING_TYPE",
                "message": "Building type required"
            }
        }

        mock_response = self._create_mock_response(json.dumps(response_data, ensure_ascii=False))

        with patch.object(self.extractor.client.chat.completions, 'create', return_value=mock_response):
            query = "부산시 해운대구 매매 2억"

            with pytest.raises(ValueError) as exc_info:
                self.extractor.extract_keywords(query)

            assert "MISSING_BUILDING_TYPE" in str(exc_info.value)

    def test_json_decode_error(self):
        """JSON 파싱 에러 테스트"""
        mock_response = self._create_mock_response("Invalid JSON response")

        with patch.object(self.extractor.client.chat.completions, 'create', return_value=mock_response):
            with pytest.raises(ValueError) as exc_info:
                self.extractor.extract_keywords("test query")

            assert "ChatGPT API returned invalid JSON format" in str(exc_info.value)

    def test_validate_response_success(self):
        """응답 검증 성공 테스트"""
        valid_response = {
            "address": "서울시 강남구",
            "transaction_type": ["매매"],
            "building_type": ["아파트"],
            "sale_price": [100000000, 200000000],
            "deposit": None,
            "monthly_rent": None,
            "area_range": "30평대"
        }

        result = self.extractor.validate_response(valid_response)
        assert result == valid_response

    def test_validate_response_missing_address(self):
        """응답 검증 실패 테스트 - 주소 누락"""
        invalid_response = {
            "transaction_type": ["매매"],
            "building_type": ["아파트"]
        }

        with pytest.raises(ValueError) as exc_info:
            self.extractor.validate_response(invalid_response)

        assert "필수 필드 'address'가 누락되었습니다" in str(exc_info.value)

    def test_validate_response_invalid_transaction_type(self):
        """응답 검증 실패 테스트 - 잘못된 거래유형"""
        invalid_response = {
            "address": "서울시 강남구",
            "transaction_type": ["잘못된유형"],
            "building_type": ["아파트"]
        }

        with pytest.raises(ValueError) as exc_info:
            self.extractor.validate_response(invalid_response)

        assert "유효하지 않은 거래 유형" in str(exc_info.value)

    def test_validate_response_invalid_building_type(self):
        """응답 검증 실패 테스트 - 잘못된 건물유형"""
        invalid_response = {
            "address": "서울시 강남구",
            "transaction_type": ["매매"],
            "building_type": ["잘못된건물유형"]
        }

        with pytest.raises(ValueError) as exc_info:
            self.extractor.validate_response(invalid_response)

        assert "유효하지 않은 건물 유형" in str(exc_info.value)

    def test_validate_response_invalid_area_range(self):
        """응답 검증 실패 테스트 - 잘못된 면적 범위"""
        invalid_response = {
            "address": "서울시 강남구",
            "transaction_type": ["매매"],
            "building_type": ["아파트"],
            "area_range": "잘못된면적"
        }

        with pytest.raises(ValueError) as exc_info:
            self.extractor.validate_response(invalid_response)

        assert "유효하지 않은 면적 범위" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])