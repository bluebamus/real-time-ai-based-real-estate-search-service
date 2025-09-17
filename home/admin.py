from django.contrib import admin
from .models import SearchHistory, PopularSearch, Property, KeywordScore, RecommendationCache


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'query_text_preview', 'result_count', 'search_date']
    list_filter = ['search_date', 'result_count']
    search_fields = ['user__username', 'query_text']
    readonly_fields = ['search_date']
    ordering = ['-search_date']

    def query_text_preview(self, obj):
        """검색어 미리보기 (50자로 제한)"""
        return obj.query_text[:50] + ('...' if len(obj.query_text) > 50 else '')
    query_text_preview.short_description = '검색어'


@admin.register(PopularSearch)
class PopularSearchAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'search_count', 'last_searched_at', 'created_at']
    list_filter = ['last_searched_at', 'created_at']
    search_fields = ['keyword']
    readonly_fields = ['created_at', 'last_searched_at']
    ordering = ['-search_count']


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('address', 'transaction_type', 'price', 'building_type', 'area_pyeong', 'crawled_date')
    list_filter = ('transaction_type', 'building_type', 'crawled_date')
    search_fields = ('address', 'description')
    readonly_fields = ('crawled_date',)


@admin.register(KeywordScore)
class KeywordScoreAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'keyword', 'score', 'updated_at')
    list_filter = ('category', 'user')
    search_fields = ('keyword',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RecommendationCache)
class RecommendationCacheAdmin(admin.ModelAdmin):
    list_display = ('user', 'cache_key', 'updated_at')
    list_filter = ('user',)
    search_fields = ('cache_key',)
    readonly_fields = ('created_at', 'updated_at')