from django.contrib import admin
from .models import SearchHistory, PopularSearch


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'query_preview', 'results_count', 'created_at']
    list_filter = ['created_at', 'results_count']
    search_fields = ['user__username', 'query']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    def query_preview(self, obj):
        """검색어 미리보기 (50자로 제한)"""
        return obj.query[:50] + ('...' if len(obj.query) > 50 else '')
    query_preview.short_description = '검색어'


@admin.register(PopularSearch)
class PopularSearchAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'search_count', 'last_searched_at', 'created_at']
    list_filter = ['last_searched_at', 'created_at']
    search_fields = ['keyword']
    readonly_fields = ['created_at', 'last_searched_at']
    ordering = ['-search_count']
