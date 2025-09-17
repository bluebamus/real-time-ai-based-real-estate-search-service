from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone # Import timezone

User = get_user_model()

class SearchHistory(models.Model):
    """
    사용자의 검색 기록을 저장하는 모델 (Development-Plan-Specification.md 기준)
    """
    search_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query_text = models.TextField(default="")  # 원본 자연어 쿼리
    parsed_keywords = models.JSONField(default=dict)  # 파싱된 키워드
    search_date = models.DateTimeField(default=timezone.now) # Changed to default=timezone.now
    result_count = models.IntegerField(default=0)
    redis_key = models.CharField(max_length=255, default="")

    class Meta:
        db_table = 'home_search_history'
        verbose_name = '검색 기록'
        verbose_name_plural = '검색 기록들'
        ordering = ['-search_date']
        indexes = [
            models.Index(fields=['-search_date']),
            models.Index(fields=['user', '-search_date']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.query_text[:50]}"


class Property(models.Model):
    """
    크롤링된 부동산 매물 데이터를 저장하는 모델 (Development-Plan-Specification.md 기준)
    """
    property_id = models.AutoField(primary_key=True)
    address = models.CharField(max_length=500)  # 주소
    owner_type = models.CharField(max_length=50)  # 집주인
    transaction_type = models.CharField(max_length=50)  # 거래타입
    price = models.BigIntegerField()  # 가격
    building_type = models.CharField(max_length=50)  # 건물 종류
    area_pyeong = models.FloatField()  # 평수
    floor_info = models.CharField(max_length=100)  # 층정보
    direction = models.CharField(max_length=20)  # 집방향
    tags = models.JSONField(default=list)  # 태그
    updated_date = models.DateTimeField(default=timezone.now) # Changed to default=timezone.now
    crawled_date = models.DateTimeField(auto_now_add=True)
    detail_url = models.URLField(max_length=500, blank=True, null=True)
    image_urls = models.JSONField(default=list)
    description = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['address', 'transaction_type']),
            models.Index(fields=['price']),
            models.Index(fields=['area_pyeong']),
            models.Index(fields=['crawled_date']),
        ]
        verbose_name = "부동산 매물"
        verbose_name_plural = "부동산 매물"

    def __str__(self):
        return f"{self.address} - {self.transaction_type} {self.price}"


class KeywordScore(models.Model):
    """
    Redis Sorted Sets 데이터의 Database 백업용 모델 (Development-Plan-Specification.md 기준)
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


class RecommendationCache(models.Model):
    """
    추천 매물 캐시의 Database 백업용 모델 (Development-Plan-Specification.md 기준)
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


class PopularSearch(models.Model):
    """
    인기 검색어를 추적하는 모델 (기존 모델 유지)
    """
    keyword = models.CharField(max_length=200, unique=True, verbose_name='검색 키워드')
    search_count = models.PositiveIntegerField(default=1, verbose_name='검색 횟수')
    last_searched_at = models.DateTimeField(auto_now=True, verbose_name='마지막 검색 일시')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 일시')

    class Meta:
        db_table = 'home_popular_search'
        verbose_name = '인기 검색어'
        verbose_name_plural = '인기 검색어들'
        ordering = ['-search_count', '-last_searched_at']
        indexes = [
            models.Index(fields=['-search_count']),
            models.Index(fields=['-last_searched_at']),
        ]

    def __str__(self):
        return f"{self.keyword} ({self.search_count}회)"

    @classmethod
    def increment_search_count(cls, keyword):
        """검색어의 카운트를 증가시키거나 새로 생성"""
        obj, created = cls.objects.get_or_create(
            keyword=keyword,
            defaults={'search_count': 1}
        )
        if not created:
            obj.search_count += 1
            obj.save(update_fields=['search_count', 'last_searched_at'])
        return obj
