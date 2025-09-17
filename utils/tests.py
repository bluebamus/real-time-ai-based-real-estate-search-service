"""
Utils 앱 테스트 모듈

이 모듈은 다음 기능들에 대한 테스트를 제공합니다:
- KeywordScore 모델 테스트
- RecommendationCache 모델 테스트
- Celery 작업 테스트
- AI/파서/크롤러 클래스 테스트
"""

import json
import pytest
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from .models import KeywordScore, RecommendationCache
from .tasks import (
    update_recommendations,
    backup_redis_scores_to_database,
    restore_redis_from_database,
    update_user_keyword_score
)
from .ai import ChatGPTClient
from .parsers import KeywordParser
from .crawlers import NaverRealEstateCrawler

User = get_user_model()


class KeywordScoreModelTest(TestCase):
    """KeywordScore 모델 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_keyword_score(self):
        """키워드 스코어 생성 테스트"""
        score = KeywordScore.objects.create(
            user=self.user,
            category='address',
            keyword='서울시 강남구',
            score=10.5
        )

        self.assertEqual(score.user, self.user)
        self.assertEqual(score.category, 'address')
        self.assertEqual(score.keyword, '서울시 강남구')
        self.assertEqual(score.score, 10.5)

    def test_global_keyword_score(self):
        """전체 사용자 키워드 스코어 테스트"""
        score = KeywordScore.objects.create(
            user=None,  # 전체 사용자
            category='transaction_type',
            keyword='매매',
            score=100.0
        )

        self.assertIsNone(score.user)
        self.assertEqual(score.category, 'transaction_type')
        self.assertEqual(score.keyword, '매매')

    def test_unique_constraint(self):
        """유니크 제약 조건 테스트"""
        KeywordScore.objects.create(
            user=self.user,
            category='address',
            keyword='서울시 강남구',
            score=10.0
        )

        # 같은 사용자, 카테고리, 키워드로 중복 생성 시 오류 발생
        with self.assertRaises(Exception):
            KeywordScore.objects.create(
                user=self.user,
                category='address',
                keyword='서울시 강남구',
                score=20.0
            )

    def test_backup_from_redis(self):
        """Redis에서 백업 메서드 테스트"""
        with patch('redis.StrictRedis') as mock_redis:
            # Mock Redis 데이터
            mock_client = MagicMock()
            mock_redis.return_value = mock_client
            mock_client.zrevrange.return_value = [
                ('서울시 강남구', 10.0),
                ('서울시 서초구', 8.0)
            ]

            # 백업 실행
            KeywordScore.backup_from_redis(mock_client)

            # 데이터 검증
            scores = KeywordScore.objects.filter(category='address')
            self.assertEqual(scores.count(), 2)


class RecommendationCacheModelTest(TestCase):
    """RecommendationCache 모델 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.sample_properties = [
            {
                'property_id': 'test_1',
                'address': '서울시 강남구',
                'price': 500000000,
                'building_type': '아파트'
            },
            {
                'property_id': 'test_2',
                'address': '서울시 서초구',
                'price': 600000000,
                'building_type': '빌라'
            }
        ]

    def test_create_recommendation_cache(self):
        """추천 캐시 생성 테스트"""
        cache_obj = RecommendationCache.objects.create(
            user=self.user,
            cache_key='user:1:recommendations',
            properties_data=self.sample_properties
        )

        self.assertEqual(cache_obj.user, self.user)
        self.assertEqual(cache_obj.cache_key, 'user:1:recommendations')
        self.assertEqual(len(cache_obj.properties_data), 2)
        self.assertEqual(cache_obj.properties_data[0]['property_id'], 'test_1')

    def test_global_recommendation_cache(self):
        """전체 추천 캐시 테스트"""
        cache_obj = RecommendationCache.objects.create(
            user=None,  # 전체 사용자
            cache_key='global:recommendations',
            properties_data=self.sample_properties
        )

        self.assertIsNone(cache_obj.user)
        self.assertEqual(cache_obj.cache_key, 'global:recommendations')


class ChatGPTClientTest(TestCase):
    """ChatGPT 클라이언트 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        self.client = ChatGPTClient()

    @patch('utils.ai.openai.chat.completions.create')
    def test_extract_keywords_success(self, mock_openai):
        """키워드 추출 성공 테스트"""
        # Mock OpenAI 응답
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            'address': '서울시 강남구',
            'transaction_type': '매매',
            'building_type': '아파트',
            'price_max': 500000000
        })
        mock_openai.return_value = mock_response

        # 테스트 실행
        query = "서울시 강남구 아파트 매매 5억 이하"
        result = self.client.extract_keywords(query)

        # 결과 검증
        self.assertEqual(result['address'], '서울시 강남구')
        self.assertEqual(result['transaction_type'], '매매')
        self.assertEqual(result['building_type'], '아파트')
        self.assertEqual(result['price_max'], 500000000)

    def test_dummy_mode(self):
        """더미 모드 테스트"""
        # API 키 없이 더미 모드 실행
        client = ChatGPTClient()
        client.dummy_mode = True

        query = "서울시 강남구 아파트"
        result = client.extract_keywords(query)

        # 더미 데이터 검증
        self.assertIn('address', result)
        self.assertIn('transaction_type', result)
        self.assertIn('building_type', result)

    def test_validate_response_missing_address(self):
        """주소 누락 시 검증 실패 테스트"""
        keywords = {
            'transaction_type': '매매',
            'building_type': '아파트'
            # address 누락
        }

        with self.assertRaises(ValueError):
            self.client.validate_response(keywords)

    def test_parse_price(self):
        """가격 파싱 테스트"""
        # 억 단위
        price = self.client._parse_price("5억")
        self.assertEqual(price, 500000000)

        # 만원 단위
        price = self.client._parse_price("5000만원")
        self.assertEqual(price, 50000000)

        # 숫자만
        price = self.client._parse_price("50000000")
        self.assertEqual(price, 50000000)

    def test_parse_area(self):
        """면적 파싱 테스트"""
        # 평 단위
        area = self.client._parse_area("30평")
        self.assertEqual(area, 30.0)

        # 제곱미터
        area = self.client._parse_area("100㎡")
        self.assertEqual(area, 100.0)

        # 숫자만
        area = self.client._parse_area("25")
        self.assertEqual(area, 25.0)


class KeywordParserTest(TestCase):
    """키워드 파서 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        self.parser = KeywordParser()

    def test_validate_required_fields_success(self):
        """필수 필드 검증 성공 테스트"""
        keywords = {
            'address': '서울시 강남구',
            'transaction_type': '매매'
        }

        result = self.parser.validate_required_fields(keywords)
        self.assertTrue(result)

    def test_validate_required_fields_missing_address(self):
        """주소 누락 시 검증 실패 테스트"""
        keywords = {
            'transaction_type': '매매'
            # address 누락
        }

        with self.assertRaises(ValueError):
            self.parser.validate_required_fields(keywords)

    def test_apply_defaults(self):
        """기본값 적용 테스트"""
        keywords = {
            'address': '서울시 강남구'
            # 다른 필드들은 누락
        }

        result = self.parser.apply_defaults(keywords)

        # 기본값 확인
        self.assertEqual(result['owner_type'], '개인')
        self.assertEqual(result['transaction_type'], '매매')
        self.assertEqual(result['building_type'], '아파트')
        self.assertEqual(result['direction'], '전체')

    def test_normalize_price(self):
        """가격 정규화 테스트"""
        # 억 단위
        price = self.parser._normalize_price("5억")
        self.assertEqual(price, 500000000)

        # 만원 단위
        price = self.parser._normalize_price("5000만")
        self.assertEqual(price, 50000000)

        # 숫자 타입
        price = self.parser._normalize_price(50000000)
        self.assertEqual(price, 50000000)

    def test_normalize_area(self):
        """면적 정규화 테스트"""
        # 평 단위
        area = self.parser._normalize_area("30평")
        self.assertEqual(area, 30.0)

        # 숫자 타입
        area = self.parser._normalize_area(25.5)
        self.assertEqual(area, 25.5)

    def test_normalize_tags(self):
        """태그 정규화 테스트"""
        # 리스트 타입
        tags = self.parser._normalize_tags(['신축', '역세권'])
        self.assertEqual(tags, ['신축', '역세권'])

        # 문자열 타입
        tags = self.parser._normalize_tags("신축, 역세권")
        self.assertEqual(tags, ['신축', '역세권'])


class NaverRealEstateCrawlerTest(TestCase):
    """네이버 부동산 크롤러 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        self.crawler = NaverRealEstateCrawler()
        self.test_keywords = {
            'address': '서울시 강남구',
            'transaction_type': '매매',
            'building_type': '아파트',
            'price_max': 500000000
        }

    def test_build_search_url(self):
        """검색 URL 생성 테스트"""
        url = self.crawler._build_search_url(self.test_keywords)

        self.assertIn('land.naver.com', url)
        self.assertIn('서울시 강남구', url)

    def test_parse_price(self):
        """가격 파싱 테스트"""
        # 억 단위
        price = self.crawler._parse_price("5억")
        self.assertEqual(price, 500000000)

        # 만원 단위
        price = self.crawler._parse_price("5000만원")
        self.assertEqual(price, 50000000)

    def test_generate_dummy_properties(self):
        """더미 데이터 생성 테스트"""
        properties = self.crawler._generate_dummy_properties(self.test_keywords)

        self.assertEqual(len(properties), 15)
        self.assertIn('property_id', properties[0])
        self.assertIn('address', properties[0])
        self.assertIn('price', properties[0])

    @patch('utils.crawlers.sync_playwright')
    def test_crawl_properties_fallback(self, mock_playwright):
        """크롤링 폴백 테스트"""
        # Playwright 에러 시뮬레이션
        mock_playwright.side_effect = Exception("Browser error")

        properties = self.crawler.crawl_properties_sync(self.test_keywords)

        # 더미 데이터 반환 확인
        self.assertGreater(len(properties), 0)
        self.assertIn('property_id', properties[0])


class CeleryTasksTest(TransactionTestCase):
    """Celery 작업 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @patch('utils.tasks.redis_client')
    def test_update_recommendations_task(self, mock_redis):
        """추천 시스템 갱신 작업 테스트"""
        # Mock Redis 데이터
        mock_redis.zrevrange.return_value = ['서울시 강남구']
        mock_redis.set.return_value = True

        # 작업 실행
        result = update_recommendations()

        # 결과 검증
        self.assertEqual(result['status'], 'success')

    @patch('utils.tasks.redis_client')
    def test_backup_redis_scores_task(self, mock_redis):
        """Redis 백업 작업 테스트"""
        # Mock Redis 데이터
        mock_redis.zrevrange.return_value = [
            ('서울시 강남구', 10.0),
            ('서울시 서초구', 8.0)
        ]
        mock_redis.get.return_value = json.dumps([
            {'property_id': 'test_1', 'address': '서울시 강남구'}
        ])

        # 작업 실행
        result = backup_redis_scores_to_database()

        # 결과 검증
        self.assertEqual(result['status'], 'success')

        # 데이터베이스에 백업 확인
        scores = KeywordScore.objects.all()
        self.assertGreater(scores.count(), 0)

    def test_update_user_keyword_score_task(self):
        """사용자 키워드 스코어 업데이트 작업 테스트"""
        keywords = {
            'address': '서울시 강남구',
            'transaction_type': '매매'
        }

        with patch('utils.tasks.RecommendationEngine') as mock_engine:
            mock_instance = MagicMock()
            mock_engine.return_value = mock_instance

            # 작업 실행
            result = update_user_keyword_score(self.user.id, keywords)

            # 결과 검증
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['user_id'], self.user.id)

            # 엔진 메서드 호출 확인
            mock_instance.update_user_keyword_score.assert_called_once()


class IntegrationTest(TransactionTestCase):
    """통합 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @patch('utils.ai.openai.chat.completions.create')
    @patch('utils.tasks.redis_client')
    def test_full_search_flow(self, mock_redis, mock_openai):
        """전체 검색 플로우 테스트"""
        # ChatGPT Mock 응답
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            'address': '서울시 강남구',
            'transaction_type': '매매',
            'building_type': '아파트',
            'price_max': 500000000
        })
        mock_openai.return_value = mock_response

        # Redis Mock 설정
        mock_redis.get.return_value = None  # 캐시 미스
        mock_redis.setex.return_value = True
        mock_redis.zincrby.return_value = 1

        # 1. 자연어 쿼리 처리
        client = ChatGPTClient()
        query = "서울시 강남구 아파트 매매 5억 이하"
        keywords = client.extract_keywords(query)

        # 2. 키워드 검증 및 정제
        parser = KeywordParser()
        validated_keywords = parser.apply_defaults(keywords)

        # 3. 크롤링 (더미)
        crawler = NaverRealEstateCrawler()
        properties = crawler._generate_dummy_properties(validated_keywords)

        # 4. 사용자 키워드 스코어 업데이트
        result = update_user_keyword_score(self.user.id, validated_keywords)

        # 결과 검증
        self.assertEqual(result['status'], 'success')
        self.assertGreater(len(properties), 0)
        self.assertEqual(validated_keywords['address'], '서울시 강남구')


# Pytest 마크 정의
pytestmark = [
    pytest.mark.django_db,
    pytest.mark.utils
]


class TestUtilsAPI(TestCase):
    """Utils API 테스트"""

    def test_health_check(self):
        """헬스 체크 테스트"""
        from config.celery import health_check_task

        # 헬스 체크 실행
        result = health_check_task()

        # 결과 검증
        self.assertIn('celery', result)
        self.assertIn('redis', result)
        self.assertIn('database', result)
        self.assertTrue(result['celery'])


# 성능 테스트용 마크
@pytest.mark.performance
class PerformanceTest(TestCase):
    """성능 테스트"""

    def test_keyword_extraction_performance(self):
        """키워드 추출 성능 테스트"""
        import time

        client = ChatGPTClient()
        client.dummy_mode = True  # 더미 모드로 테스트

        start_time = time.time()

        # 100회 반복 테스트
        for i in range(100):
            query = f"서울시 강남구 아파트 매매 {i}억"
            result = client.extract_keywords(query)
            self.assertIn('address', result)

        end_time = time.time()
        execution_time = end_time - start_time

        # 100회 실행이 5초 이내 완료되어야 함
        self.assertLess(execution_time, 5.0)

    def test_crawling_performance(self):
        """크롤링 성능 테스트"""
        import time

        crawler = NaverRealEstateCrawler()
        keywords = {
            'address': '서울시 강남구',
            'transaction_type': '매매',
            'building_type': '아파트'
        }

        start_time = time.time()

        # 더미 크롤링 10회
        for i in range(10):
            properties = crawler._generate_dummy_properties(keywords)
            self.assertEqual(len(properties), 15)

        end_time = time.time()
        execution_time = end_time - start_time

        # 10회 실행이 1초 이내 완료되어야 함
        self.assertLess(execution_time, 1.0)