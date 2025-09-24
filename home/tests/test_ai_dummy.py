"""
Home App - ChatGPT 더미 API 테스트

이 모듈은 다음과 같은 테스트들을 포함합니다:
1. test_client_initialization: 클라이언트 초기화 테스트
2. test_extract_keywords_seoul_gangnam: 서울 강남구 패턴 키워드 추출 테스트
3. test_extract_keywords_gyeonggi_suwon: 경기도 수원시 패턴 키워드 추출 테스트
4. test_extract_keywords_default_pattern: 기본 패턴 적용 테스트
5. test_validate_response_success: 응답 검증 성공 테스트
6. test_validate_response_missing_address_failure: 주소 누락 시 검증 실패 테스트
7. test_enhance_response_from_query_transaction_type: 쿼리에서 거래타입 추출 테스트
8. test_enhance_response_from_query_building_type: 쿼리에서 건물타입 추출 테스트
9. test_enhance_response_from_query_price: 쿼리에서 가격 추출 테스트
10. test_enhance_response_from_query_area: 쿼리에서 평수 추출 테스트
11. test_get_available_patterns: 사용 가능한 패턴 목록 반환 테스트
12. test_test_all_patterns: 모든 패턴 테스트 기능 검증
13. test_singleton_instance: 싱글톤 인스턴스 테스트
14. test_various_query_patterns: 다양한 쿼리 패턴에 대한 파라미터화 테스트
15. test_client_error_handling: 클라이언트 에러 처리 테스트
16. test_data_type_conversion: 데이터 타입 변환 테스트
"""

import pytest
from unittest.mock import patch
from home.services.ai_dummy import DummyChatGPTClient, get_dummy_client


class TestDummyChatGPTClient:
    """ChatGPT 더미 클라이언트 테스트"""

    def setup_method(self):
        """각 테스트 메서드 실행 전 설정"""
        self.client = DummyChatGPTClient()

    def test_client_initialization(self):
        """클라이언트 초기화 테스트"""
        assert self.client.dummy_mode is True
        assert len(self.client.response_patterns) > 0
        assert 'keywords' in self.client.response_patterns[0]
        assert 'response' in self.client.response_patterns[0]

    def test_extract_keywords_seoul_gangnam(self):
        """서울 강남구 패턴 키워드 추출 테스트"""
        query = "서울 강남구 아파트 매매 5억 이하"
        result = self.client.extract_keywords(query)

        # 필수 필드 검증
        assert 'address' in result
        assert 'transaction_type' in result
        assert 'building_type' in result

        # 값 검증
        assert "강남" in result['address']
        assert result['transaction_type'] in ['매매', '전세', '월세']
        assert result['building_type'] in ['아파트', '오피스텔', '빌라', '원룸', '투룸']

    def test_extract_keywords_gyeonggi_suwon(self):
        """경기도 수원시 패턴 키워드 추출 테스트"""
        query = "경기도 수원시 장안구 전세"
        result = self.client.extract_keywords(query)

        # 주소 패턴 매칭 확인
        assert "수원" in result['address'] or "경기" in result['address']
        # 거래타입이 쿼리에 따라 변경되는지 확인
        assert result['transaction_type'] == '전세'

    def test_extract_keywords_default_pattern(self):
        """기본 패턴 적용 테스트 (매칭되지 않는 쿼리)"""
        query = "알 수 없는 지역 매물 검색"
        result = self.client.extract_keywords(query)

        # 기본값이 적용되었는지 확인
        assert result['address'] is not None
        assert result['transaction_type'] is not None
        assert result['building_type'] is not None

    def test_validate_response_success(self):
        """응답 검증 성공 테스트"""
        test_response = {
            'address': '서울시 강남구',
            'transaction_type': '매매',
            'building_type': '아파트'
        }

        validated = self.client.validate_response(test_response)

        # 필수 필드 존재 확인
        assert validated['address'] == '서울시 강남구'
        assert validated['transaction_type'] == '매매'
        assert validated['building_type'] == '아파트'

        # 기본값이 적용되었는지 확인
        assert 'owner_type' in validated
        assert 'direction' in validated
        assert 'tags' in validated

    def test_validate_response_missing_address_failure(self):
        """주소 누락 시 검증 실패 테스트"""
        test_response = {
            'transaction_type': '매매',
            'building_type': '아파트'
        }

        with pytest.raises(ValueError, match="주소.*필수"):
            self.client.validate_response(test_response)

    def test_enhance_response_from_query_transaction_type(self):
        """쿼리에서 거래타입 추출 테스트"""
        response = {'address': '서울시 강남구'}

        # 전세 테스트
        self.client._enhance_response_from_query("서울 강남 전세", response)
        assert response['transaction_type'] == '전세'

        # 월세 테스트
        response = {'address': '서울시 강남구'}
        self.client._enhance_response_from_query("서울 강남 월세", response)
        assert response['transaction_type'] == '월세'

    def test_enhance_response_from_query_building_type(self):
        """쿼리에서 건물타입 추출 테스트"""
        response = {'address': '서울시 강남구'}

        # 오피스텔 테스트
        self.client._enhance_response_from_query("서울 강남 오피스텔", response)
        assert response['building_type'] == '오피스텔'

        # 빌라 테스트
        response = {'address': '서울시 강남구'}
        self.client._enhance_response_from_query("서울 강남 빌라", response)
        assert response['building_type'] == '빌라'

    def test_enhance_response_from_query_price(self):
        """쿼리에서 가격 추출 테스트"""
        response = {'address': '서울시 강남구'}

        # 억 단위 가격 테스트
        self.client._enhance_response_from_query("서울 강남 5억 이하", response)
        assert response['price_max'] == 500000000

        # 천만원 단위 테스트
        response = {'address': '서울시 강남구'}
        self.client._enhance_response_from_query("서울 강남 5천만", response)
        assert response['price_max'] == 50000000

    def test_enhance_response_from_query_area(self):
        """쿼리에서 평수 추출 테스트"""
        response = {'address': '서울시 강남구'}

        self.client._enhance_response_from_query("서울 강남 30평", response)
        assert response['area_pyeong'] == 30

    def test_get_available_patterns(self):
        """사용 가능한 패턴 목록 반환 테스트"""
        patterns = self.client.get_available_patterns()

        assert isinstance(patterns, list)
        assert len(patterns) > 0
        # 기본 패턴은 제외되어야 함
        assert not any('default' in pattern for pattern in patterns)

    def test_test_all_patterns(self):
        """모든 패턴 테스트 기능 검증"""
        results = self.client.test_all_patterns()

        assert isinstance(results, dict)
        assert len(results) > 0

        # 각 결과에 필수 정보가 있는지 확인
        for pattern_name, result in results.items():
            assert 'query' in result
            assert 'success' in result
            if result['success']:
                assert 'result' in result
                assert isinstance(result['result'], dict)
            else:
                assert 'error' in result

    def test_singleton_instance(self):
        """싱글톤 인스턴스 테스트"""
        client1 = get_dummy_client()
        client2 = get_dummy_client()

        # 같은 인스턴스인지 확인
        assert client1 is client2
        assert client1.dummy_mode is True

    @pytest.mark.parametrize("query,expected_address_keyword", [
        ("서울 강남구 아파트", "강남"),
        ("부산 해운대 오피스텔", "해운대"),
        ("경기 수원시 빌라", "수원"),
        ("전세 매물 찾아줘", None)  # 기본 패턴
    ])
    def test_various_query_patterns(self, query, expected_address_keyword):
        """다양한 쿼리 패턴에 대한 파라미터화 테스트"""
        result = self.client.extract_keywords(query)

        # 기본 필드 존재 확인
        assert 'address' in result
        assert 'transaction_type' in result
        assert 'building_type' in result

        # 주소 키워드 확인 (기본 패턴이 아닌 경우)
        if expected_address_keyword:
            assert expected_address_keyword in result['address']

    def test_client_error_handling(self):
        """클라이언트 에러 처리 테스트"""
        # 빈 쿼리
        result = self.client.extract_keywords("")
        assert result is not None
        assert 'address' in result

        # None 쿼리
        result = self.client.extract_keywords(None)
        assert result is not None

    def test_data_type_conversion(self):
        """데이터 타입 변환 테스트"""
        test_response = {
            'address': '서울시 강남구',
            'price_max': '500000000',  # 문자열
            'area_pyeong': '30.5',     # 문자열
            'tags': 'test,value'       # 문자열이지만 리스트여야 함
        }

        validated = self.client.validate_response(test_response)

        # price_max가 정수로 변환되었는지 확인
        assert isinstance(validated['price_max'], int)
        assert validated['price_max'] == 500000000

        # area_pyeong이 실수로 변환되었는지 확인
        assert isinstance(validated['area_pyeong'], float)
        assert validated['area_pyeong'] == 30.5