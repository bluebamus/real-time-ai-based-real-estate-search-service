from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone  # Import timezone

User = get_user_model()


class SearchHistory(models.Model):
    """
    사용자의 검색 기록을 저장하는 모델 (Development-Plan-Specification.md 기준)
    키워드 추출 결과 및 검색 상태를 추적
    """

    # 에러 유형 정의 (system_prompt 기준)
    ERROR_CHOICES = [
        ("MISSING_ADDRESS", "주소 정보 누락"),
        ("MISSING_TRANSACTION_TYPE", "거래유형 정보 누락"),
        ("MISSING_BUILDING_TYPE", "매물유형 정보 누락"),
        ("API_ERROR", "API 호출 오류"),
        ("JSON_PARSE_ERROR", "JSON 파싱 오류"),
        ("VALIDATION_ERROR", "유효성 검사 오류"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="사용자",
        help_text="사용자 정보 (Global이 True인 경우 null)",
    )
    is_global = models.BooleanField(
        default=False,
        verbose_name="전체 사용자용",
        help_text="True인 경우 전체 사용자에 대한 키워드 의미",
    )
    query_text = models.TextField(
        default="",
        verbose_name="원본 자연어 쿼리",
        help_text="사용자가 입력한 자연어 검색 쿼리",
    )

    # 추출된 키워드 필드들 (keyword_extraction.py 기준)
    address = models.JSONField(
        default=dict,
        verbose_name="주소",
        help_text="주소 정보 (JSON 형태)",
    )
    transaction_type = models.JSONField(
        default=list,
        verbose_name="거래유형",
        help_text="매매, 전세, 월세, 단기임대 (배열 형태)",
    )
    building_type = models.JSONField(
        default=list,
        verbose_name="매물유형",
        help_text="아파트, 오피스텔, 빌라 등 (배열 형태)",
    )
    sale_price = models.JSONField(
        default=None,
        null=True,
        blank=True,
        verbose_name="매매가",
        help_text="매매가 범위 [최소값] 또는 [최소값, 최대값] (원 단위)",
    )
    deposit = models.JSONField(
        default=None,
        null=True,
        blank=True,
        verbose_name="보증금",
        help_text="보증금 범위 [최소값] 또는 [최소값, 최대값] (원 단위)",
    )
    monthly_rent = models.JSONField(
        default=None,
        null=True,
        blank=True,
        verbose_name="월세",
        help_text="월세 범위 [최소값] 또는 [최소값, 최대값] (원 단위)",
    )
    area_range = models.CharField(
        max_length=20,
        default="",
        blank=True,
        verbose_name="면적대",
        help_text="~10평, 10평대, 20평대, 30평대, 40평대, 50평대, 60평대, 70평~ 중 하나",
    )

    # 기타 필드들
    error_type = models.CharField(
        max_length=50,
        choices=ERROR_CHOICES,
        null=True,
        blank=True,
        verbose_name="에러 유형",
        help_text="키워드 추출 실패 시 에러 유형",
    )
    score = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="스코어",
        help_text="Redis sorted set 스코어 (추후 사용)",
    )
    redis_key = models.CharField(
        max_length=255,
        default="",
        blank=True,
        verbose_name="Redis 키",
        help_text="Redis 캐시 키",
    )

    # 시간 필드들
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="생성 시간", help_text="검색 기록 생성 시간"
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="수정 시간", help_text="검색 기록 마지막 수정 시간"
    )
    search_date = models.DateTimeField(
        default=timezone.now,
        verbose_name="검색 수행 시간",
        help_text="실제 검색이 수행된 시간",
    )

    class Meta:
        db_table = "home_search_history"
        verbose_name = "검색 기록"
        verbose_name_plural = "검색 기록들"
        ordering = ["-search_date"]
        indexes = [
            models.Index(fields=["-search_date"]),
            models.Index(fields=["error_type"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(is_global=True, user__isnull=True)
                | models.Q(is_global=False, user__isnull=False),
                name="global_user_constraint",
            )
        ]

    def __str__(self):
        if self.is_global:
            return f"Global - {self.query_text[:50]}"
        return (
            f"{self.user.username if self.user else 'Unknown'} - {self.query_text[:50]}"
        )

    def has_error(self):
        """에러가 발생했는지 확인"""
        return self.error_type is not None

    def get_extracted_keywords(self):
        """추출된 키워드들을 딕셔너리 형태로 반환"""
        return {
            "address": self.address,
            "transaction_type": self.transaction_type,
            "building_type": self.building_type,
            "sale_price": self.sale_price,
            "deposit": self.deposit,
            "monthly_rent": self.monthly_rent,
            "area_range": self.area_range,
        }

    def is_successful_extraction(self):
        """키워드 추출이 성공했는지 확인"""
        return (
            not self.has_error()
            and self.address
            and self.transaction_type
            and self.building_type
        )


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
    updated_date = models.DateTimeField(
        default=timezone.now
    )  # Changed to default=timezone.now
    crawled_date = models.DateTimeField(auto_now_add=True)
    detail_url = models.URLField(max_length=500, blank=True, null=True)
    image_urls = models.JSONField(default=list)
    description = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["address", "transaction_type"]),
            models.Index(fields=["price"]),
            models.Index(fields=["area_pyeong"]),
            models.Index(fields=["crawled_date"]),
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
        help_text="사용자 (None인 경우 전체 사용자 키워드)",
    )
    category = models.CharField(
        max_length=50,
        help_text="키워드 카테고리 (address, transaction_type, building_type 등)",
    )
    keyword = models.CharField(max_length=200, help_text="키워드 값")
    score = models.FloatField(default=0.0, help_text="키워드 스코어")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["user", "category", "keyword"]]
        indexes = [
            models.Index(fields=["user", "category"]),
            models.Index(fields=["category", "score"]),
            models.Index(fields=["updated_at"]),
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
        help_text="사용자 (None인 경우 전체 사용자 추천)",
    )
    cache_key = models.CharField(max_length=255, help_text="Redis 캐시 키")
    properties_data = models.JSONField(help_text="추천 매물 데이터 (JSON)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["user", "cache_key"]]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["cache_key"]),
            models.Index(fields=["updated_at"]),
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

    keyword = models.CharField(max_length=200, unique=True, verbose_name="검색 키워드")
    search_count = models.PositiveIntegerField(default=1, verbose_name="검색 횟수")
    last_searched_at = models.DateTimeField(
        auto_now=True, verbose_name="마지막 검색 일시"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성 일시")

    class Meta:
        db_table = "home_popular_search"
        verbose_name = "인기 검색어"
        verbose_name_plural = "인기 검색어들"
        ordering = ["-search_count", "-last_searched_at"]
        indexes = [
            models.Index(fields=["-search_count"]),
            models.Index(fields=["-last_searched_at"]),
        ]

    def __str__(self):
        return f"{self.keyword} ({self.search_count}회)"

    @classmethod
    def increment_search_count(cls, keyword):
        """검색어의 카운트를 증가시키거나 새로 생성"""
        obj, created = cls.objects.get_or_create(
            keyword=keyword, defaults={"search_count": 1}
        )
        if not created:
            obj.search_count += 1
            obj.save(update_fields=["search_count", "last_searched_at"])
        return obj
