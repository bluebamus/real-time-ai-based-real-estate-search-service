"""
SearchAPIView 통합 테스트

home/views/api_views.py의 SearchAPIView를 테스트합니다.
키워드 추출 기능과 에러 처리에 대한 검증을 포함합니다.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
from rest_framework import status

# 프로젝트 루트를 Python path에 추가
# home/tests/ -> home/ -> project_root/
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from home.views.api_views import SearchAPIView
from home.services.keyword_extraction import get_keyword_extractor


@pytest.mark.django_db
class TestSearchAPIView:
    """SearchAPIView 통합 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 셋업"""
        self.factory = APIRequestFactory()
        self.view = SearchAPIView()
        self.extractor = get_keyword_extractor()

        # 테스트 유저 생성
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123'
        )

    def _create_mock_response(self, content):
        """Mock 응답 객체 생성 헬퍼"""
        mock_choice = Mock()
        mock_choice.message.content = content

        mock_response = Mock()
        mock_response.choices = [mock_choice]

        return mock_response

    def _create_request(self, data):
        """POST 요청 객체 생성 헬퍼 - JSON 데이터 직접 전달"""
        import io
        from django.http import HttpRequest

        request = self.factory.post(
            '/test/',
            data=json.dumps(data),
            content_type='application/json'
        )
        request.user = self.user
        return request

    def test_search_api_empty_query(self):
        """빈 쿼리에 대한 에러 처리 테스트"""
        request = self._create_request({})
        response = self.view.post(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['status'] == 'error'
        assert response.data['message'] == '검색어를 입력해주세요.'
        assert response.data['error_code'] == 'EMPTY_QUERY'
        assert 'Query text is required' in response.data['error']

    def test_search_api_whitespace_only_query(self):
        """공백만 있는 쿼리에 대한 에러 처리 테스트"""
        request = self._create_request({'query': '   '})
        response = self.view.post(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['status'] == 'error'
        assert response.data['message'] == '검색어를 입력해주세요.'
        assert response.data['error_code'] == 'EMPTY_QUERY'

    def test_search_api_none_query(self):
        """None 쿼리에 대한 에러 처리 테스트"""
        request = self._create_request({'query': None})
        response = self.view.post(request)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['status'] == 'error'
        assert response.data['error_code'] == 'EMPTY_QUERY'

    def test_search_api_successful_keyword_extraction(self):
        """성공적인 키워드 추출 테스트"""
        response_data = {
            "status": "success",
            "data": {
                "address": "서울시 강남구",
                "transaction_type": ["매매"],
                "building_type": ["아파트"],
                "sale_price": [100000000, 200000000],
                "deposit": None,
                "monthly_rent": None,
                "area_range": "30평대"
            },
            "error": None
        }

        mock_response = self._create_mock_response(json.dumps(response_data, ensure_ascii=False))

        with patch.object(self.extractor.client.chat.completions, 'create', return_value=mock_response):
            request = self._create_request({'query': '서울시 강남구 아파트 매매 30평대 1억에서 2억'})
            response = self.view.post(request)

            assert response.status_code == status.HTTP_200_OK
            assert response.data['status'] == 'success'
            assert response.data['message'] == '키워드 추출이 완료되었습니다.'
            assert response.data['query'] == '서울시 강남구 아파트 매매 30평대 1억에서 2억'
            assert 'keywords' in response.data
            assert response.data['keywords']['address'] == '서울시 강남구'
            assert '매매' in response.data['keywords']['transaction_type']
            assert '아파트' in response.data['keywords']['building_type']

    def test_search_api_keyword_extraction_error_missing_address(self):
        """키워드 추출 오류 테스트 - MISSING_ADDRESS (ValueError로 처리됨)"""
        # keyword_extraction.py는 에러 응답을 받으면 ValueError를 raise함
        with patch.object(self.extractor, 'extract_keywords',
                         side_effect=ValueError("ChatGPT extraction failed: MISSING_ADDRESS - Address is incomplete, only 시도 is provided.")):
            request = self._create_request({'query': '경기도 매매 아파트 1억'})
            response = self.view.post(request)

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.data['status'] == 'error'
            assert response.data['message'] == '키워드 추출 중 오류가 발생했습니다.'
            assert response.data['error_code'] == 'MISSING_ADDRESS'
            assert 'Address is incomplete' in response.data['error']

    def test_search_api_keyword_extraction_error_missing_transaction_type(self):
        """키워드 추출 오류 테스트 - MISSING_TRANSACTION_TYPE"""
        with patch.object(self.extractor, 'extract_keywords',
                         side_effect=ValueError("ChatGPT extraction failed: MISSING_TRANSACTION_TYPE - Transaction type is missing.")):
            request = self._create_request({'query': '서울시 강남구 아파트 30평대'})
            response = self.view.post(request)

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.data['status'] == 'error'
            assert response.data['error_code'] == 'MISSING_TRANSACTION_TYPE'

    def test_search_api_keyword_extraction_error_missing_building_type(self):
        """키워드 추출 오류 테스트 - MISSING_BUILDING_TYPE"""
        with patch.object(self.extractor, 'extract_keywords',
                         side_effect=ValueError("ChatGPT extraction failed: MISSING_BUILDING_TYPE - Building type is missing.")):
            request = self._create_request({'query': '부산시 해운대구 매매 2억'})
            response = self.view.post(request)

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.data['status'] == 'error'
            assert response.data['error_code'] == 'MISSING_BUILDING_TYPE'

    def test_search_api_validation_error_exception(self):
        """검증 오류 예외 처리 테스트"""
        with patch.object(self.extractor, 'extract_keywords', side_effect=ValueError("Invalid query format")):
            request = self._create_request({'query': 'invalid query'})
            response = self.view.post(request)

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.data['status'] == 'error'
            assert response.data['message'] == '키워드 추출 중 오류가 발생했습니다.'
            assert response.data['error_code'] == 'VALIDATION_ERROR'  # ChatGPT extraction failed가 없는 경우
            assert 'Invalid query format' in response.data['error']

    def test_search_api_unexpected_exception(self):
        """예상치 못한 예외 처리 테스트"""
        with patch.object(self.extractor, 'extract_keywords', side_effect=Exception("Unexpected error")):
            request = self._create_request({'query': 'test query'})
            response = self.view.post(request)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert response.data['status'] == 'error'
            assert response.data['message'] == '서버 내부 오류가 발생했습니다.'
            assert response.data['error'] == 'Internal server error'

    def test_search_api_json_decode_error(self):
        """JSON 파싱 오류 테스트 (keyword_extraction.py에서 ValueError로 처리됨)"""
        with patch.object(self.extractor, 'extract_keywords',
                         side_effect=ValueError("ChatGPT API returned invalid JSON format")):
            request = self._create_request({'query': 'test query'})
            response = self.view.post(request)

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.data['status'] == 'error'
            assert response.data['error_code'] == 'VALIDATION_ERROR'
            assert 'ChatGPT API returned invalid JSON format' in response.data['error']

    def test_search_api_comprehensive_query_success(self):
        """종합 쿼리 성공 테스트"""
        response_data = {
            "status": "success",
            "data": {
                "address": "경기도 수원시 장안구",
                "transaction_type": ["매매", "전세"],
                "building_type": ["아파트", "오피스텔"],
                "sale_price": [50000000, 100000000],
                "deposit": [20000000, 50000000],
                "monthly_rent": None,
                "area_range": "40평대"
            },
            "error": None
        }

        mock_response = self._create_mock_response(json.dumps(response_data, ensure_ascii=False))

        with patch.object(self.extractor.client.chat.completions, 'create', return_value=mock_response):
            query = "경기도 수원시 장안구 아파트나 오피스텔 매매 전세 5천만원에서 1억사이 40평대"
            request = self._create_request({'query': query})
            response = self.view.post(request)

            assert response.status_code == status.HTTP_200_OK
            assert response.data['status'] == 'success'
            assert response.data['keywords']['address'] == '경기도 수원시 장안구'
            assert len(response.data['keywords']['transaction_type']) == 2
            assert len(response.data['keywords']['building_type']) == 2
            assert response.data['keywords']['area_range'] == '40평대'

    def test_search_api_area_range_mapping(self):
        """면적 범위 매핑 테스트"""
        response_data = {
            "status": "success",
            "data": {
                "address": "인천시 남동구",
                "transaction_type": ["월세"],
                "building_type": ["빌라"],
                "sale_price": None,
                "deposit": None,
                "monthly_rent": [500000, 800000],
                "area_range": "~10평"
            },
            "error": None
        }

        mock_response = self._create_mock_response(json.dumps(response_data, ensure_ascii=False))

        with patch.object(self.extractor.client.chat.completions, 'create', return_value=mock_response):
            request = self._create_request({'query': '인천시 남동구 빌라 월세 8평'})
            response = self.view.post(request)

            assert response.status_code == status.HTTP_200_OK
            assert response.data['keywords']['area_range'] == '~10평'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])