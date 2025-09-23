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
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from board.services.redis_data_service import redis_data_service
from utils.recommendations import recommendation_engine

logger = logging.getLogger(__name__)


class AuthTestAPIView(APIView):
    """
    Board 인증 및 세션 테스트를 위한 API View
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id='board_auth_test',
        summary='Board 페이지 인증 테스트',
        description='''
        Board 페이지에서 세션 기반 인증 상태를 테스트합니다.

        ## 기능
        - 현재 사용자의 인증 상태 확인
        - 세션 정보 서버 콘솔 출력
        - CSRF 토큰 및 세션 키 검증
        - 현재 페이지 경로 정보 포함

        ## 자동 실행
        - Board 페이지 방문 시 JavaScript에서 자동 호출
        - Home과 달리 인증 실패 시 리다이렉트하지 않음
        ''',
        tags=['Authentication', 'Board API'],
        responses={
            200: {
                'description': '인증 테스트 성공',
                'examples': [
                    OpenApiExample(
                        'Success Response',
                        summary='Board 인증된 사용자',
                        description='Board 페이지에서 로그인된 사용자의 응답',
                        value={
                            "status": "success",
                            "is_authenticated": True,
                            "username": "testuser",
                            "user_id": 1,
                            "session_exists": True,
                            "current_path": "/board/api/auth-test/",
                            "message": "Board 인증 테스트 완료"
                        }
                    )
                ]
            },
            401: {
                'description': '인증 실패',
                'examples': [
                    OpenApiExample(
                        'Authentication Failed',
                        summary='미인증 사용자',
                        description='로그인하지 않은 사용자의 응답',
                        value={
                            "detail": "Authentication credentials were not provided."
                        }
                    )
                ]
            }
        }
    )
    def get(self, request):
        # 인증 및 세션 관련 정보 출력 (서버 로그에 기록됨)
        print("=== Board Auth Test Info ===")
        print("is_authenticated:", request.user.is_authenticated)
        print("username:", request.user.username if request.user.is_authenticated else None)
        print("user_id:", request.user.id if request.user.is_authenticated else None)
        print("session_key:", request.session.session_key)
        print("csrf_cookie:", request.META.get("CSRF_COOKIE"))
        print("csrf_token_from_meta:", request.META.get("HTTP_X_CSRFTOKEN"))
        print("user_agent:", request.META.get("HTTP_USER_AGENT"))
        print("session_data:", dict(request.session))
        print("current_path:", request.path)
        print("============================")

        # 클라이언트에는 성공 코드와 기본 정보 반환
        return Response({
            "status": "success",
            "is_authenticated": request.user.is_authenticated,
            "username": request.user.username if request.user.is_authenticated else None,
            "user_id": request.user.id if request.user.is_authenticated else None,
            "session_exists": bool(request.session.session_key),
            "current_path": request.path,
            "message": "Board 인증 테스트 완료"
        }, status=status.HTTP_200_OK)


class ResultsAPIView(APIView):
    """
    검색 결과를 JSON 형태로 제공하는 API 뷰

    주요 기능:
    - Redis 키로 검색 결과 조회
    - 페이지네이션 지원 (30개씩)
    - 추천 매물 제외한 일반 검색 결과만 반환
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id='board_search_results',
        summary='검색 결과 조회',
        description='''
        Redis에 저장된 검색 결과를 페이지네이션하여 조회합니다.

        ## 기능
        - Home에서 생성된 Redis 키로 검색 결과 조회
        - 30개씩 페이지네이션 지원
        - 추천 매물 제외한 일반 검색 결과만 반환
        - Redis 키 유효성 검증 (TTL 5분)

        ## 사용 플로우
        1. Home에서 검색 수행 → Redis 키 생성
        2. Board 페이지로 리다이렉트
        3. 이 API로 페이지네이션된 결과 조회
        ''',
        tags=['Board API'],
        parameters=[
            OpenApiParameter(
                name='redis_key',
                description='Home에서 생성된 Redis 키 (search:hash:results 형태)',
                required=True,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                examples=[
                    OpenApiExample(
                        'Valid Redis Key',
                        summary='유효한 Redis 키',
                        description='Home 검색에서 생성된 키',
                        value='search:abc123def456:results'
                    )
                ]
            ),
            OpenApiParameter(
                name='page',
                description='페이지 번호 (기본값: 1)',
                required=False,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                examples=[
                    OpenApiExample('First Page', summary='첫 번째 페이지', value=1),
                    OpenApiExample('Second Page', summary='두 번째 페이지', value=2)
                ]
            )
        ],
        responses={
            200: {
                'description': '검색 결과 조회 성공',
                'examples': [
                    OpenApiExample(
                        'Results Found',
                        summary='검색 결과 있음',
                        description='페이지네이션된 검색 결과',
                        value={
                            "results": [
                                {
                                    "owner_name": "강남 아파트",
                                    "address": "서울시 강남구",
                                    "transaction_type": "매매",
                                    "price": 800000000,
                                    "building_type": "아파트",
                                    "area_size": 30.5,
                                    "floor_info": "10/25층",
                                    "direction": "남향",
                                    "tags": ["신축", "역세권"],
                                    "updated_date": "2025-09-23",
                                    "is_recommendation": False
                                }
                            ],
                            "total_count": 45,
                            "current_page": 1,
                            "total_pages": 2,
                            "has_next": True,
                            "has_previous": False,
                            "redis_key": "search:abc123def456:results"
                        }
                    ),
                    OpenApiExample(
                        'No Results',
                        summary='검색 결과 없음',
                        description='유효한 키지만 결과 없음',
                        value={
                            "results": [],
                            "total_count": 0,
                            "current_page": 1,
                            "total_pages": 0,
                            "has_next": False,
                            "has_previous": False
                        }
                    )
                ]
            },
            404: {
                'description': 'Redis 키 만료 또는 존재하지 않음',
                'examples': [
                    OpenApiExample(
                        'Expired Key',
                        summary='만료된 키',
                        description='5분 TTL 만료 또는 잘못된 키',
                        value={"error": "검색 결과가 만료되었거나 존재하지 않습니다."}
                    )
                ]
            },
            401: {
                'description': '인증 필요',
                'examples': [
                    OpenApiExample(
                        'Authentication Required',
                        summary='로그인 필요',
                        description='세션 인증 실패',
                        value={"detail": "Authentication credentials were not provided."}
                    )
                ]
            },
            500: {
                'description': '서버 오류',
                'examples': [
                    OpenApiExample(
                        'Server Error',
                        summary='서버 내부 오류',
                        description='Redis 연결 오류 등',
                        value={"error": "검색 결과 조회 중 오류가 발생했습니다."}
                    )
                ]
            }
        }
    )
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