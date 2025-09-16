from django.contrib import admin
from .models import KeywordScore, RecommendationCache


@admin.register(KeywordScore)
class KeywordScoreAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'keyword', 'score', 'updated_at']
    list_filter = ['category', 'updated_at', 'user']
    search_fields = ['keyword', 'category']
    ordering = ['-score', '-updated_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('키워드 정보', {
            'fields': ('user', 'category', 'keyword', 'score')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(RecommendationCache)
class RecommendationCacheAdmin(admin.ModelAdmin):
    list_display = ['user', 'cache_key', 'properties_count', 'updated_at']
    list_filter = ['updated_at', 'user']
    search_fields = ['cache_key']
    ordering = ['-updated_at']
    readonly_fields = ['created_at', 'updated_at', 'properties_count']

    fieldsets = (
        ('캐시 정보', {
            'fields': ('user', 'cache_key', 'properties_count')
        }),
        ('데이터', {
            'fields': ('properties_data',),
            'classes': ('collapse',)
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def properties_count(self, obj):
        """추천 매물 개수 표시"""
        if obj.properties_data and isinstance(obj.properties_data, list):
            return len(obj.properties_data)
        return 0
    properties_count.short_description = '매물 개수'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')