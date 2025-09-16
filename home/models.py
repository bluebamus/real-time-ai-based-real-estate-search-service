from django.db import models
from django.contrib.auth.models import User


class SearchHistory(models.Model):
    """
    사용자의 검색 기록을 저장하는 모델
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_histories')
    query = models.TextField(verbose_name='검색어')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='검색 일시')
    results_count = models.IntegerField(default=0, verbose_name='결과 개수')

    class Meta:
        db_table = 'home_search_history'
        verbose_name = '검색 기록'
        verbose_name_plural = '검색 기록들'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.query[:50]}"


class PopularSearch(models.Model):
    """
    인기 검색어를 추적하는 모델
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
