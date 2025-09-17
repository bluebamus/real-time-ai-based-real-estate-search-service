"""
추천 시스템 엔진 모듈
"""
import redis
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    부동산 매물 추천 엔진
    사용자 검색 패턴을 분석하여 맞춤형 매물 추천
    """

    def __init__(self):
        """추천 엔진 초기화"""
        self.redis_client = redis.StrictRedis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
            charset='utf-8'
        )
        self.categories = [
            'address', 'transaction_type', 'building_type',
            'price_range', 'area_range', 'floor_info',
            'direction', 'tags'
        ]

    def update_user_keyword_score(self, user_id: int, keywords: Dict[str, Any]):
        """
        사용자 검색 키워드 스코어 업데이트

        Args:
            user_id: 사용자 ID
            keywords: 검색 키워드
        """
        try:
            # 각 카테고리별로 스코어 업데이트
            for category, value in keywords.items():
                if value and value != '전체':  # '전체'는 기본값이므로 제외
                    # 사용자별 스코어 업데이트
                    user_key = f"user:{user_id}:keywords:{category}"
                    self.redis_client.zincrby(user_key, 1, str(value))

                    # 전체 사용자 스코어 업데이트
                    global_key = f"global:keywords:{category}"
                    self.redis_client.zincrby(global_key, 1, str(value))

                    # 태그는 리스트일 수 있으므로 별도 처리
                    if category == 'tags' and isinstance(value, list):
                        for tag in value:
                            self.redis_client.zincrby(f"user:{user_id}:keywords:tags", 1, tag)
                            self.redis_client.zincrby("global:keywords:tags", 1, tag)

            logger.info(f"Updated keyword scores for user {user_id}")

        except Exception as e:
            logger.error(f"Error updating keyword scores: {e}")

    def get_user_recommendations(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        사용자 맞춤 추천 매물 조회

        Args:
            user_id: 사용자 ID
            limit: 추천 개수

        Returns:
            추천 매물 리스트
        """
        try:
            # Redis에서 캐시된 추천 조회
            cache_key = f"user:{user_id}:recommendations"
            cached = self.redis_client.get(cache_key)

            if cached:
                recommendations = json.loads(cached)
                logger.info(f"Retrieved {len(recommendations)} cached recommendations for user {user_id}")
                return recommendations[:limit]

            # 캐시가 없으면 빈 리스트 반환 (Celery Beat가 주기적으로 갱신)
            logger.info(f"No cached recommendations for user {user_id}")
            return []

        except Exception as e:
            logger.error(f"Error getting user recommendations: {e}")
            return []

    def get_global_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        전체 사용자 기반 인기 추천 매물 조회

        Args:
            limit: 추천 개수

        Returns:
            추천 매물 리스트
        """
        try:
            # Redis에서 캐시된 추천 조회
            cache_key = "global:recommendations"
            cached = self.redis_client.get(cache_key)

            if cached:
                recommendations = json.loads(cached)
                logger.info(f"Retrieved {len(recommendations)} cached global recommendations")
                return recommendations[:limit]

            # 캐시가 없으면 빈 리스트 반환
            logger.info("No cached global recommendations")
            return []

        except Exception as e:
            logger.error(f"Error getting global recommendations: {e}")
            return []

    def extract_top_keywords(self, prefix: str) -> Dict[str, Any]:
        """
        상위 키워드 추출 (크롤링용)

        Args:
            prefix: 키 프리픽스 ('global' 또는 'user:123')

        Returns:
            카테고리별 상위 키워드
        """
        try:
            top_keywords = {}

            for category in self.categories:
                key = f"{prefix}:keywords:{category}"
                # 각 카테고리에서 상위 1개 키워드 추출
                top_items = self.redis_client.zrevrange(key, 0, 0, withscores=False)

                if top_items:
                    value = top_items[0]
                    # 특수 처리가 필요한 카테고리
                    if category == 'price_range':
                        top_keywords['price_max'] = self._parse_price_range(value)
                    elif category == 'area_range':
                        top_keywords['area_pyeong'] = self._parse_area_range(value)
                    elif category == 'tags':
                        # 태그는 상위 3개 추출
                        top_tags = self.redis_client.zrevrange(key, 0, 2, withscores=False)
                        top_keywords['tags'] = list(top_tags)
                    else:
                        top_keywords[category] = value
                else:
                    # 기본값 설정
                    if category == 'tags':
                        top_keywords['tags'] = []
                    elif category not in ['price_range', 'area_range']:
                        top_keywords[category] = self._get_default_value(category)

            # 필수 필드 확인
            if 'address' not in top_keywords or not top_keywords['address']:
                top_keywords['address'] = '서울시 강남구'  # 기본 지역

            logger.info(f"Extracted top keywords for {prefix}: {top_keywords}")
            return top_keywords

        except Exception as e:
            logger.error(f"Error extracting top keywords: {e}")
            return {}

    def _parse_price_range(self, value: str) -> int:
        """가격 범위 파싱"""
        try:
            if '억' in value:
                billion = float(value.replace('억', '').strip())
                return int(billion * 100000000)
            elif '만' in value:
                man = int(value.replace('만', '').replace('원', '').strip())
                return man * 10000
            else:
                return int(value)
        except:
            return 500000000  # 기본값 5억

    def _parse_area_range(self, value: str) -> int:
        """면적 범위 파싱"""
        try:
            if '평' in value:
                return int(value.replace('평', '').strip())
            else:
                return int(value)
        except:
            return 30  # 기본값 30평

    def _get_default_value(self, category: str) -> str:
        """카테고리별 기본값"""
        defaults = {
            'owner_type': '전체',
            'transaction_type': '매매',
            'building_type': '아파트',
            'floor_info': '전체',
            'direction': '전체',
            'updated_date': '전체'
        }
        return defaults.get(category, '전체')

    def calculate_similarity_score(self, property_data: Dict[str, Any], user_keywords: Dict[str, Any]) -> float:
        """
        매물과 사용자 선호도 간의 유사도 점수 계산

        Args:
            property_data: 매물 데이터
            user_keywords: 사용자 선호 키워드

        Returns:
            유사도 점수 (0.0 ~ 1.0)
        """
        score = 0.0
        total_weight = 0.0

        # 카테고리별 가중치
        weights = {
            'address': 0.3,
            'transaction_type': 0.2,
            'building_type': 0.15,
            'price': 0.15,
            'area': 0.1,
            'floor_info': 0.05,
            'direction': 0.05
        }

        for category, weight in weights.items():
            total_weight += weight

            if category in property_data and category in user_keywords:
                if property_data[category] == user_keywords[category]:
                    score += weight
                elif category == 'price':
                    # 가격은 범위 내에 있으면 부분 점수
                    if property_data[category] <= user_keywords.get('price_max', float('inf')):
                        score += weight * 0.7
                elif category == 'area':
                    # 면적은 오차 범위 내면 부분 점수
                    diff = abs(property_data[category] - user_keywords.get('area_pyeong', 30))
                    if diff <= 5:
                        score += weight * (1 - diff / 10)

        return score / total_weight if total_weight > 0 else 0.0

    def get_combined_recommendations(self, user_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        사용자 맞춤 + 전체 인기 추천 조합

        Args:
            user_id: 사용자 ID

        Returns:
            {'user_based': [...], 'global_based': [...]}
        """
        try:
            user_recommendations = self.get_user_recommendations(user_id, limit=10)
            global_recommendations = self.get_global_recommendations(limit=10)

            # 중복 제거 (매물 ID 또는 주소 기준)
            seen_properties = set()
            filtered_global = []

            for prop in user_recommendations:
                prop_id = f"{prop.get('location')}_{prop.get('property_name')}"
                seen_properties.add(prop_id)

            for prop in global_recommendations:
                prop_id = f"{prop.get('location')}_{prop.get('property_name')}"
                if prop_id not in seen_properties:
                    filtered_global.append(prop)

            return {
                'user_based': user_recommendations,
                'global_based': filtered_global[:10]
            }

        except Exception as e:
            logger.error(f"Error getting combined recommendations: {e}")
            return {'user_based': [], 'global_based': []}

    def get_recommendation_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        추천 시스템 통계 조회

        Args:
            user_id: 사용자 ID (None이면 전체 통계)

        Returns:
            통계 정보
        """
        try:
            stats = {
                'timestamp': datetime.now().isoformat(),
                'categories': {}
            }

            prefix = f"user:{user_id}" if user_id else "global"

            for category in self.categories:
                key = f"{prefix}:keywords:{category}"
                top_keywords = self.redis_client.zrevrange(key, 0, 4, withscores=True)

                stats['categories'][category] = [
                    {'keyword': kw, 'score': score}
                    for kw, score in top_keywords
                ]

            # 추천 캐시 상태
            cache_key = f"{prefix}:recommendations"
            cached_recommendations = self.redis_client.get(cache_key)
            stats['has_cached_recommendations'] = cached_recommendations is not None

            if cached_recommendations:
                recommendations = json.loads(cached_recommendations)
                stats['cached_recommendation_count'] = len(recommendations)

            return stats

        except Exception as e:
            logger.error(f"Error getting recommendation stats: {e}")
            return {}