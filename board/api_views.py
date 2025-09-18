"""
Board App - API 뷰

이 모듈은 검색 결과와 추천 매물을 JSON 형태로 제공하는 API 뷰들을 정의합니다.
"""

import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from board.services.redis_data_service import redis_data_service
from utils.recommendations import recommendation_engine

logger = logging.getLogger(__name__)


class ResultsAPIView(APIView):
    """
    검색 결과를 JSON 형태로 제공하는 API 뷰

    주요 기능:
    - Redis 키로 검색 결과 조회
    - 페이지네이션 지원 (30개씩)
    - 추천 매물 제외한 일반 검색 결과만 반환
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, redis_key, *args, **kwargs):
        """
        검색 결과 API - GET 요청 처리

        Args:
            redis_key: Redis 키 (URL 파라미터)

        Query Parameters:
            page: 페이지 번호 (기본값: 1)

        Returns:
            JSON: 페이지네이션된 검색 결과
        """
        try:
            # Redis 키 유효성 확인
            if not redis_data_service.check_redis_key_valid(redis_key):
                logger.warning(f"Invalid or expired Redis key: {redis_key}")
                return Response(
                    {"error": "검색 결과가 만료되었거나 존재하지 않습니다."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 검색 결과 조회 (추천 매물 제외)
            search_properties = redis_data_service.get_properties_from_search_results(redis_key)

            if not search_properties:
                logger.info(f"No search results found for key: {redis_key}")
                return Response(
                    {
                        "results": [],
                        "total_count": 0,
                        "current_page": 1,
                        "total_pages": 0,
                        "has_next": False,
                        "has_previous": False
                    },
                    status=status.HTTP_200_OK
                )

            # 페이지네이션 처리
            page_number = request.GET.get('page', 1)
            paginator = Paginator(search_properties, 30)  # 30개씩 페이지네이션

            try:
                page_obj = paginator.page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            # 검색 결과에 is_recommendation 플래그 추가
            results = []
            for prop in page_obj.object_list:
                prop_data = dict(prop)
                prop_data['is_recommendation'] = False
                results.append(prop_data)

            response_data = {
                "results": results,
                "total_count": paginator.count,
                "current_page": page_obj.number,
                "total_pages": paginator.num_pages,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
                "redis_key": redis_key
            }

            logger.info(f"검색 결과 API 응답 - 페이지: {page_obj.number}, 결과: {len(results)}개")

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"검색 결과 API 오류: {e}")
            return Response(
                {"error": "검색 결과 조회 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RecommendationAPIView(APIView):
    """
    추천 매물을 JSON 형태로 제공하는 API 뷰

    주요 기능:
    - Redis Sorted Sets에서 추천 매물 조회
    - 스코어 기반 상위 10개 추천 매물 반환
    - is_recommendation: true 플래그 포함
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        추천 매물 API - GET 요청 처리

        Query Parameters:
            limit: 추천 매물 개수 (기본값: 10, 최대: 20)
            type: 추천 타입 ('user' 또는 'global', 기본값: 'user')

        Returns:
            JSON: 추천 매물 리스트
        """
        try:
            # 파라미터 추출
            limit = min(int(request.GET.get('limit', 10)), 20)  # 최대 20개 제한
            recommendation_type = request.GET.get('type', 'user')

            # 사용자별 또는 전체 추천 매물 조회
            if recommendation_type == 'global':
                recommendations = redis_data_service.get_recommendation_properties(
                    user_id=None, limit=limit
                )
            else:
                recommendations = redis_data_service.get_recommendation_properties(
                    user_id=request.user.id, limit=limit
                )

            # 추천 매물에 is_recommendation 플래그 추가 (이미 서비스에서 추가됨)
            response_data = {
                "recommendations": recommendations,
                "total_count": len(recommendations),
                "recommendation_type": recommendation_type,
                "user_id": request.user.id if recommendation_type == 'user' else None
            }

            logger.info(f"추천 매물 API 응답 - 타입: {recommendation_type}, 결과: {len(recommendations)}개")

            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.error(f"추천 매물 API 파라미터 오류: {e}")
            return Response(
                {"error": "잘못된 파라미터입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"추천 매물 API 오류: {e}")
            return Response(
                {"error": "추천 매물 조회 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PropertyDetailAPIView(APIView):
    """
    개별 매물 상세 정보를 JSON 형태로 제공하는 API 뷰
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, redis_key, property_index, *args, **kwargs):
        """
        매물 상세 정보 API - GET 요청 처리

        Args:
            redis_key: Redis 키
            property_index: 매물 인덱스 (0부터 시작)

        Returns:
            JSON: 매물 상세 정보
        """
        try:
            # Redis 키 유효성 확인
            if not redis_data_service.check_redis_key_valid(redis_key):
                return Response(
                    {"error": "검색 결과가 만료되었거나 존재하지 않습니다."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 검색 결과 조회
            search_properties = redis_data_service.get_properties_from_search_results(redis_key)

            # 매물 인덱스 유효성 확인
            try:
                property_index = int(property_index)
                if property_index < 0 or property_index >= len(search_properties):
                    return Response(
                        {"error": "존재하지 않는 매물입니다."},
                        status=status.HTTP_404_NOT_FOUND
                    )
            except ValueError:
                return Response(
                    {"error": "잘못된 매물 인덱스입니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 매물 상세 정보 반환
            property_detail = search_properties[property_index]
            property_detail['is_recommendation'] = False

            logger.info(f"매물 상세 정보 API 응답 - 인덱스: {property_index}")

            return Response(property_detail, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"매물 상세 정보 API 오류: {e}")
            return Response(
                {"error": "매물 정보 조회 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )