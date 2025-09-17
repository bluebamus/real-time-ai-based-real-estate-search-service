"""
Celery tasks for utils app
Redis backup and recommendation system update tasks
"""
from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
import redis
import json
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

# Redis client 초기화
redis_client = redis.StrictRedis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)


@shared_task
def update_recommendations():
    """
    5분마다 실행되는 추천 시스템 갱신 작업
    전체 사용자 및 개별 사용자의 추천 매물을 업데이트
    """
    from utils.recommendations import RecommendationEngine
    from utils.crawlers import NaverRealEstateCrawler

    logger.info("Starting recommendation update task...")

    try:
        engine = RecommendationEngine()
        crawler = NaverRealEstateCrawler()

        # 1. 전체 사용자 추천 업데이트
        global_keywords = engine.extract_top_keywords('global')
        if global_keywords:
            logger.info(f"Crawling for global recommendations with keywords: {global_keywords}")
            properties = crawler.crawl_properties(global_keywords)

            # Redis에 저장 (TTL 없음 - 다음 갱신까지 유지)
            redis_client.set(
                'global:recommendations',
                json.dumps(properties[:10])  # 최대 10개
            )
            logger.info(f"Updated global recommendations with {len(properties[:10])} properties")

        # 2. 활성 사용자별 추천 업데이트
        # 최근 24시간 내 활동한 사용자 조회
        active_users = User.objects.filter(
            last_login__gte=datetime.now() - timedelta(hours=24)
        ).values_list('id', flat=True)

        updated_users = 0
        for user_id in active_users:
            user_keywords = engine.extract_top_keywords(f'user:{user_id}')
            if user_keywords:
                logger.info(f"Crawling for user {user_id} with keywords: {user_keywords}")
                properties = crawler.crawl_properties(user_keywords)

                # Redis에 저장
                redis_client.set(
                    f'user:{user_id}:recommendations',
                    json.dumps(properties[:10])  # 최대 10개
                )
                updated_users += 1

        logger.info(f"Recommendation update completed. Updated {updated_users} users.")
        return {'status': 'success', 'updated_users': updated_users}

    except Exception as e:
        logger.error(f"Error updating recommendations: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def backup_redis_scores_to_database():
    """
    10분마다 실행되는 Redis 백업 작업
    Redis Sorted Sets와 추천 캐시를 Database에 백업
    """
    from utils.models import KeywordScore, RecommendationCache

    logger.info("Starting Redis backup to database...")

    try:
        with transaction.atomic():
            # 1. Keyword Scores 백업
            backup_keyword_scores()

            # 2. Recommendation Cache 백업
            backup_recommendation_cache()

        logger.info("Redis backup completed successfully")
        return {'status': 'success', 'timestamp': datetime.now().isoformat()}

    except Exception as e:
        logger.error(f"Error backing up Redis data: {e}")
        return {'status': 'error', 'message': str(e)}


def backup_keyword_scores():
    """키워드 스코어 백업"""
    from utils.models import KeywordScore

    categories = ['address', 'transaction_type', 'building_type', 'price_range',
                  'area_range', 'floor_info', 'direction', 'tags']

    # 전체 사용자 키워드 백업
    for category in categories:
        key = f"global:keywords:{category}"
        keywords_with_scores = redis_client.zrevrange(key, 0, -1, withscores=True)

        for keyword, score in keywords_with_scores:
            KeywordScore.objects.update_or_create(
                user=None,  # 전체 사용자는 user=None
                category=category,
                keyword=keyword,
                defaults={'score': score}
            )

    # 개별 사용자 키워드 백업
    active_users = User.objects.filter(
        last_login__gte=datetime.now() - timedelta(days=7)  # 최근 7일 활동 사용자
    )

    for user in active_users:
        for category in categories:
            key = f"user:{user.id}:keywords:{category}"
            keywords_with_scores = redis_client.zrevrange(key, 0, -1, withscores=True)

            for keyword, score in keywords_with_scores:
                KeywordScore.objects.update_or_create(
                    user=user,
                    category=category,
                    keyword=keyword,
                    defaults={'score': score}
                )

    logger.info(f"Backed up keyword scores for {active_users.count()} users")


def backup_recommendation_cache():
    """추천 캐시 백업"""
    from utils.models import RecommendationCache

    # 전체 추천 백업
    global_recommendations = redis_client.get('global:recommendations')
    if global_recommendations:
        RecommendationCache.objects.update_or_create(
            user=None,
            cache_key='global:recommendations',
            defaults={'properties_data': json.loads(global_recommendations)}
        )

    # 사용자별 추천 백업
    active_users = User.objects.filter(
        last_login__gte=datetime.now() - timedelta(days=7)
    )

    for user in active_users:
        cache_key = f'user:{user.id}:recommendations'
        user_recommendations = redis_client.get(cache_key)

        if user_recommendations:
            RecommendationCache.objects.update_or_create(
                user=user,
                cache_key=cache_key,
                defaults={'properties_data': json.loads(user_recommendations)}
            )

    logger.info(f"Backed up recommendation cache for {active_users.count()} users")


@shared_task
def restore_redis_from_database():
    """
    Django 재시작 시 Database에서 Redis로 데이터 복원
    """
    from utils.models import KeywordScore, RecommendationCache

    logger.info("Starting Redis restoration from database...")

    try:
        # 1. Keyword Scores 복원
        keyword_scores = KeywordScore.objects.all()
        restored_scores = 0

        for score in keyword_scores:
            if score.user:
                key = f"user:{score.user.id}:keywords:{score.category}"
            else:
                key = f"global:keywords:{score.category}"

            redis_client.zadd(key, {score.keyword: score.score})
            restored_scores += 1

        # 2. Recommendation Cache 복원
        recommendation_caches = RecommendationCache.objects.all()
        restored_caches = 0

        for cache in recommendation_caches:
            redis_client.set(
                cache.cache_key,
                json.dumps(cache.properties_data)
            )
            restored_caches += 1

        logger.info(f"Redis restoration completed. Restored {restored_scores} scores and {restored_caches} caches")
        return {
            'status': 'success',
            'restored_scores': restored_scores,
            'restored_caches': restored_caches
        }

    except Exception as e:
        logger.error(f"Error restoring Redis data: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def cleanup_old_search_history():
    """
    오래된 검색 기록 정리 (30일 이상)
    """
    from home.models import SearchHistory

    cutoff_date = datetime.now() - timedelta(days=30)
    deleted_count = SearchHistory.objects.filter(
        search_date__lt=cutoff_date
    ).delete()[0]

    logger.info(f"Cleaned up {deleted_count} old search records")
    return {'deleted_count': deleted_count}


@shared_task
def update_user_keyword_score(user_id: int, keywords: dict):
    """
    사용자의 검색 키워드 스코어 업데이트
    """
    from utils.recommendations import RecommendationEngine

    try:
        engine = RecommendationEngine()
        engine.update_user_keyword_score(user_id, keywords)

        logger.info(f"Updated keyword scores for user {user_id}")
        return {'status': 'success', 'user_id': user_id}

    except Exception as e:
        logger.error(f"Error updating keyword score for user {user_id}: {e}")
        return {'status': 'error', 'message': str(e)}