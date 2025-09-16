from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class KeywordScore(models.Model):
    """
    Redis Sorted Sets 데이터의 Database 백업용 모델
    Redis 장애 시 복구를 위한 키워드 스코어 저장
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="사용자 (None인 경우 전체 사용자 키워드)"
    )
    category = models.CharField(
        max_length=50,
        help_text="키워드 카테고리 (address, transaction_type, building_type 등)"
    )
    keyword = models.CharField(
        max_length=200,
        help_text="키워드 값"
    )
    score = models.FloatField(
        default=0.0,
        help_text="키워드 스코어"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['user', 'category', 'keyword']]
        indexes = [
            models.Index(fields=['user', 'category']),
            models.Index(fields=['category', 'score']),
            models.Index(fields=['updated_at']),
        ]
        verbose_name = "키워드 스코어"
        verbose_name_plural = "키워드 스코어"

    def __str__(self):
        user_info = f"User {self.user.id}" if self.user else "Global"
        return f"{user_info} - {self.category}: {self.keyword} ({self.score})"

    @classmethod
    def backup_from_redis(cls, redis_client):
        """Redis 데이터를 Database에 백업"""
        from .cache import RedisCache
        cache = RedisCache()

        # 모든 키워드 스코어 백업
        cache.backup_all_scores_to_database()

    @classmethod
    def restore_to_redis(cls, redis_client):
        """Database 데이터를 Redis로 복원"""
        from .cache import RedisCache
        cache = RedisCache()

        # 모든 키워드 스코어 복원
        cache.restore_all_scores_from_database()


class RecommendationCache(models.Model):
    """
    추천 매물 캐시의 Database 백업용 모델
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="사용자 (None인 경우 전체 사용자 추천)"
    )
    cache_key = models.CharField(
        max_length=255,
        help_text="Redis 캐시 키"
    )
    properties_data = models.JSONField(
        help_text="추천 매물 데이터 (JSON)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['user', 'cache_key']]
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['cache_key']),
            models.Index(fields=['updated_at']),
        ]
        verbose_name = "추천 캐시"
        verbose_name_plural = "추천 캐시"

    def __str__(self):
        user_info = f"User {self.user.id}" if self.user else "Global"
        return f"{user_info} - {self.cache_key}"