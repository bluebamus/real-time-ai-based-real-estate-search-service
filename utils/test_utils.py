"""
Utils 앱 테스트 코드
ChatGPT API, 크롤링, Redis 캐시, 추천 시스템 테스트
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.test import override_settings
from utils.ai import ChatGPTClient
from utils.parsers import KeywordParser
from utils.cache import RedisCache
from utils.recommendations import RecommendationEngine
from utils.models import KeywordScore, RecommendationCache

User = get_user_model()


class TestChatGPTClient(TestCase):
    """ChatGPT 클라이언트 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.client = ChatGPTClient()

    @patch('openai.ChatCompletion.create')
    def test_extract_keywords_success(self, mock_create):
        """키워드 추출 성공 테스트"""
        # Mock ChatGPT 응답
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            'address': '서울시 강남구',
            'transaction_type': '매매',
            'building_type': '아파트',
            'price_max': 500000000,
            'area_pyeong': 30
        })
        mock_create.return_value = mock_response

        # 키워드 추출
        query = "서울시 강남구 30평 아파트 매매 5억 이하"
        keywords = self.client.extract_keywords(query)

        # 검증
        self.assertEqual(keywords['address'], '서울시 강남구')
        self.assertEqual(keywords['transaction_type'], '매매')
        self.assertEqual(keywords['building_type'], '아파트')
        self.assertEqual(keywords['price_max'], 500000000)
        self.assertEqual(keywords['area_pyeong'], 30)

    def test_validate_response_missing_address(self):
        """필수 필드 누락 검증 테스트"""
        # 주소가 없는 응답
        response = {
            'transaction_type': '매매',
            'building_type': '아파트'
        }

        # 검증 시 예외 발생 확인
        with self.assertRaises(ValueError) as context:
            self.client.validate_response(response)

        self.assertIn('주소', str(context.exception))

    def test_validate_response_apply_defaults(self):
        """기본값 적용 테스트"""
        # 최소한의 응답
        response = {
            'address': '서울시 강남구'
        }

        # 검증 및 기본값 적용
        validated = self.client.validate_response(response)

        # 기본값 확인
        self.assertEqual(validated['owner_type'], '전체')
        self.assertEqual(validated['transaction_type'], '매매')
        self.assertEqual(validated['building_type'], '아파트')
        self.assertEqual(validated['floor_info'], '전체')
        self.assertEqual(validated['direction'], '전체')
        self.assertEqual(validated['tags'], [])


class TestKeywordParser(TestCase):
    """키워드 파서 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.parser = KeywordParser()

    def test_validate_required_fields_success(self):
        """필수 필드 검증 성공 테스트"""
        keywords = {
            'address': '서울시 강남구'
        }
        result = self.parser.validate_required_fields(keywords)
        self.assertTrue(result)

    def test_validate_required_fields_missing_address(self):
        """주소 누락 시 검증 실패 테스트"""
        keywords = {
            'building_type': '아파트'
        }
        result = self.parser.validate_required_fields(keywords)
        self.assertFalse(result)

    def test_parse_price_billion(self):
        """억 단위 가격 파싱 테스트"""
        price = self.parser.parse_price("5억")
        self.assertEqual(price, 500000000)

        price = self.parser.parse_price("3.5억")
        self.assertEqual(price, 350000000)

    def test_parse_price_million(self):
        """만원 단위 가격 파싱 테스트"""
        price = self.parser.parse_price("5000만원")
        self.assertEqual(price, 50000000)

    def test_parse_area_pyeong(self):
        """평수 파싱 테스트"""
        area = self.parser.parse_area("30평")
        self.assertEqual(area, 30)

        area = self.parser.parse_area("25평대")
        self.assertEqual(area, 25)

    def test_extract_tags_from_text(self):
        """텍스트에서 태그 추출 테스트"""
        text = "역세권 신축 아파트 대단지 풀옵션"
        tags = self.parser.extract_tags_from_text(text)

        self.assertIn('역세권', tags)
        self.assertIn('신축', tags)
        self.assertIn('대단지', tags)
        self.assertIn('풀옵션', tags)

    def test_normalize_building_type(self):
        """건물 타입 정규화 테스트"""
        self.assertEqual(self.parser.normalize_building_type('아파트'), '아파트')
        self.assertEqual(self.parser.normalize_building_type('apt'), '아파트')
        self.assertEqual(self.parser.normalize_building_type('다세대'), '빌라')
        self.assertEqual(self.parser.normalize_building_type('연립'), '빌라')


class TestRedisCache(TestCase):
    """Redis 캐시 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.cache = RedisCache()
        # Redis Mock
        self.cache.redis_client = MagicMock()

    def test_generate_cache_key(self):
        """캐시 키 생성 테스트"""
        keywords = {
            'address': '서울시 강남구',
            'transaction_type': '매매',
            'building_type': '아파트'
        }

        key1 = self.cache.generate_cache_key(keywords)
        key2 = self.cache.generate_cache_key(keywords)

        # 동일한 키워드는 동일한 키 생성
        self.assertEqual(key1, key2)

        # 키 형식 확인
        self.assertTrue(key1.startswith('search:'))
        self.assertTrue(key1.endswith(':results'))

    def test_set_cached_results(self):
        """캐시 저장 테스트"""
        cache_key = 'test:key'
        data = [{'property': 'test'}]
        ttl = 300

        self.cache.set_cached_results(cache_key, data, ttl)

        # Redis setex 호출 확인
        self.cache.redis_client.setex.assert_called_once()
        args = self.cache.redis_client.setex.call_args[0]
        self.assertEqual(args[0], cache_key)
        self.assertEqual(args[1], ttl)
        self.assertIn('property', args[2])

    def test_get_cached_results(self):
        """캐시 조회 테스트"""
        cache_key = 'test:key'
        cached_data = json.dumps([{'property': 'test'}])
        self.cache.redis_client.get.return_value = cached_data

        result = self.cache.get_cached_results(cache_key)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['property'], 'test')

    def test_update_keyword_score_user(self):
        """사용자 키워드 스코어 업데이트 테스트"""
        user_id = 123
        category = 'address'
        keyword = '서울시 강남구'

        self.cache.update_keyword_score(user_id, category, keyword)

        # Redis zincrby 호출 확인
        self.cache.redis_client.zincrby.assert_called_with(
            f'user:{user_id}:keywords:{category}',
            1.0,
            keyword
        )

    def test_update_keyword_score_global(self):
        """전체 키워드 스코어 업데이트 테스트"""
        category = 'transaction_type'
        keyword = '매매'

        self.cache.update_keyword_score(None, category, keyword)

        # Redis zincrby 호출 확인
        self.cache.redis_client.zincrby.assert_called_with(
            f'global:keywords:{category}',
            1.0,
            keyword
        )


class TestRecommendationEngine(TestCase):
    """추천 엔진 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.engine = RecommendationEngine()
        # Redis Mock
        self.engine.redis_client = MagicMock()
        # 테스트 사용자
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )

    def test_update_user_keyword_score(self):
        """사용자 키워드 스코어 업데이트 테스트"""
        keywords = {
            'address': '서울시 강남구',
            'transaction_type': '매매',
            'building_type': '아파트',
            'tags': ['역세권', '신축']
        }

        self.engine.update_user_keyword_score(self.user.id, keywords)

        # zincrby 호출 횟수 확인 (address, transaction_type, building_type, tags*2)
        self.assertEqual(self.engine.redis_client.zincrby.call_count, 8)

    def test_extract_top_keywords(self):
        """상위 키워드 추출 테스트"""
        # Mock Redis 응답
        self.engine.redis_client.zrevrange.side_effect = [
            ['서울시 강남구'],  # address
            ['매매'],  # transaction_type
            ['아파트'],  # building_type
            [],  # price_range
            [],  # area_range
            [],  # floor_info
            [],  # direction
            ['역세권', '신축']  # tags
        ]

        keywords = self.engine.extract_top_keywords('global')

        self.assertEqual(keywords['address'], '서울시 강남구')
        self.assertEqual(keywords['transaction_type'], '매매')
        self.assertEqual(keywords['building_type'], '아파트')
        self.assertIn('역세권', keywords['tags'])
        self.assertIn('신축', keywords['tags'])

    def test_calculate_similarity_score(self):
        """유사도 점수 계산 테스트"""
        property_data = {
            'address': '서울시 강남구',
            'transaction_type': '매매',
            'building_type': '아파트',
            'price': 450000000,
            'area': 32
        }

        user_keywords = {
            'address': '서울시 강남구',
            'transaction_type': '매매',
            'building_type': '아파트',
            'price_max': 500000000,
            'area_pyeong': 30
        }

        score = self.engine.calculate_similarity_score(property_data, user_keywords)

        # 점수는 0과 1 사이
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        # 매칭되는 항목이 많으므로 높은 점수
        self.assertGreater(score, 0.5)


class TestKeywordScoreModel(TestCase):
    """KeywordScore 모델 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )

    def test_create_keyword_score(self):
        """키워드 스코어 생성 테스트"""
        score = KeywordScore.objects.create(
            user=self.user,
            category='address',
            keyword='서울시 강남구',
            score=10.0
        )

        self.assertEqual(score.user, self.user)
        self.assertEqual(score.category, 'address')
        self.assertEqual(score.keyword, '서울시 강남구')
        self.assertEqual(score.score, 10.0)

    def test_create_global_keyword_score(self):
        """전체 키워드 스코어 생성 테스트 (user=None)"""
        score = KeywordScore.objects.create(
            user=None,
            category='transaction_type',
            keyword='매매',
            score=100.0
        )

        self.assertIsNone(score.user)
        self.assertEqual(score.category, 'transaction_type')
        self.assertEqual(score.keyword, '매매')
        self.assertEqual(score.score, 100.0)


class TestRecommendationCacheModel(TestCase):
    """RecommendationCache 모델 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )

    def test_create_recommendation_cache(self):
        """추천 캐시 생성 테스트"""
        properties_data = [
            {'property': 'test1'},
            {'property': 'test2'}
        ]

        cache = RecommendationCache.objects.create(
            user=self.user,
            cache_key='user:123:recommendations',
            properties_data=properties_data
        )

        self.assertEqual(cache.user, self.user)
        self.assertEqual(cache.cache_key, 'user:123:recommendations')
        self.assertEqual(len(cache.properties_data), 2)

    def test_create_global_recommendation_cache(self):
        """전체 추천 캐시 생성 테스트 (user=None)"""
        properties_data = [
            {'property': 'global1'},
            {'property': 'global2'}
        ]

        cache = RecommendationCache.objects.create(
            user=None,
            cache_key='global:recommendations',
            properties_data=properties_data
        )

        self.assertIsNone(cache.user)
        self.assertEqual(cache.cache_key, 'global:recommendations')
        self.assertEqual(len(cache.properties_data), 2)


@pytest.mark.django_db
class TestCeleryTasks:
    """Celery 작업 테스트"""

    @patch('utils.tasks.redis_client')
    @patch('utils.tasks.RecommendationEngine')
    @patch('utils.tasks.NaverRealEstateCrawler')
    def test_update_recommendations_task(self, mock_crawler, mock_engine, mock_redis):
        """추천 업데이트 작업 테스트"""
        from utils.tasks import update_recommendations

        # Mock 설정
        mock_engine_instance = mock_engine.return_value
        mock_engine_instance.extract_top_keywords.return_value = {
            'address': '서울시 강남구',
            'transaction_type': '매매'
        }

        mock_crawler_instance = mock_crawler.return_value
        mock_crawler_instance.crawl_properties.return_value = [
            {'property': 'test'}
        ]

        # 작업 실행
        result = update_recommendations()

        # 검증
        assert result['status'] == 'success'
        mock_engine_instance.extract_top_keywords.assert_called_with('global')
        mock_crawler_instance.crawl_properties.assert_called()

    @patch('utils.tasks.KeywordScore')
    @patch('utils.tasks.RecommendationCache')
    def test_backup_redis_scores_to_database(self, mock_cache, mock_score):
        """Redis 백업 작업 테스트"""
        from utils.tasks import backup_redis_scores_to_database

        # 작업 실행
        result = backup_redis_scores_to_database()

        # 검증
        assert result['status'] == 'success'
        assert 'timestamp' in result