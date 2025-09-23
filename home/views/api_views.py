import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from home.models import SearchHistory, Property
from home.services.keyword_extraction import ChatGPTKeywordExtractor
from home.services.crawlers import NaverRealEstateCrawler
from home.services.redis_storage import redis_storage
from utils.recommendations import recommendation_engine

logger = logging.getLogger(__name__)


class AuthTestAPIView(APIView):
    """
    인증 및 세션 테스트를 위한 API View
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id='home_auth_test',
        summary='Home 페이지 인증 테스트',
        description='''
        Home 페이지에서 세션 기반 인증 상태를 테스트합니다.

        ## 기능
        - 현재 사용자의 인증 상태 확인
        - 세션 정보 서버 콘솔 출력
        - CSRF 토큰 및 세션 키 검증

        ## 자동 실행
        - Home 페이지 방문 시 JavaScript에서 자동 호출
        - 인증 실패 시 로그인 페이지로 리다이렉트
        ''',
        tags=['Authentication', 'Home API'],
        responses={
            200: {
                'description': '인증 테스트 성공',
                'examples': [
                    OpenApiExample(
                        'Success Response',
                        summary='인증된 사용자',
                        description='로그인된 사용자의 성공 응답',
                        value={
                            "status": "success",
                            "is_authenticated": True,
                            "username": "testuser",
                            "user_id": 1,
                            "session_exists": True,
                            "message": "인증 테스트 완료"
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
        print("=== Auth Test Info ===")
        print("is_authenticated:", request.user.is_authenticated)
        print("username:", request.user.username if request.user.is_authenticated else None)
        print("user_id:", request.user.id if request.user.is_authenticated else None)
        print("session_key:", request.session.session_key)
        print("csrf_cookie:", request.META.get("CSRF_COOKIE"))
        print("csrf_token_from_meta:", request.META.get("HTTP_X_CSRFTOKEN"))
        print("user_agent:", request.META.get("HTTP_USER_AGENT"))
        print("session_data:", dict(request.session))
        print("======================")

        # 클라이언트에는 성공 코드와 기본 정보 반환
        return Response({
            "status": "success",
            "is_authenticated": request.user.is_authenticated,
            "username": request.user.username if request.user.is_authenticated else None,
            "user_id": request.user.id if request.user.is_authenticated else None,
            "session_exists": bool(request.session.session_key),
            "message": "인증 테스트 완료"
        }, status=status.HTTP_200_OK)


class SearchAPIView(APIView):
    """
    자연어 기반 부동산 검색 API View
    ChatGPT를 통한 키워드 추출, 네이버 크롤링 수행
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id='home_search',
        summary='자연어 부동산 검색',
        description='''
        자연어 질의를 통한 부동산 매물 검색 API

        ## 처리 과정
        1. ChatGPT API를 통한 키워드 추출
        2. 네이버 부동산 크롤링 수행
        3. Redis에 검색 결과 저장 (TTL: 5분)
        4. 추천 시스템 키워드 스코어 업데이트
        5. 검색 히스토리 DB 저장

        ## 자연어 검색 예시
        - "서울시 강남구 30평대 아파트 매매 5억 이하"
        - "경기도 수원시에서 전세 또는 월세로 오피스텔 20평대"
        - "부산시 해운대구에서 단기임대 원룸 50만원 이하"

        ## 필수 조건
        - 주소: 시·도와 시·군·구 필수 (예: "서울시 강남구")
        - 거래유형: 매매, 전세, 월세, 단기임대 중 하나 이상
        - 건물유형: 아파트, 오피스텔, 빌라 등 18가지 유형 중 하나 이상
        ''',
        tags=['Home API'],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': '자연어 검색 질의',
                        'example': '서울시 강남구 30평대 아파트 매매 5억 이하'
                    }
                },
                'required': ['query']
            }
        },
        examples=[
            OpenApiExample(
                'Basic Search',
                summary='기본 검색 예시',
                description='서울 강남구 아파트 검색',
                value={'query': '서울시 강남구 30평대 아파트 매매 5억 이하'},
                request_only=True
            ),
            OpenApiExample(
                'Rental Search',
                summary='전세/월세 검색 예시',
                description='수원시 오피스텔 전세 검색',
                value={'query': '경기도 수원시에서 전세 또는 월세로 오피스텔 20평대'},
                request_only=True
            )
        ],
        responses={
            200: {
                'description': '검색 성공',
                'examples': [
                    OpenApiExample(
                        'Search Success',
                        summary='검색 성공 응답',
                        description='크롤링 완료 후 결과 페이지로 리다이렉트',
                        value={
                            "status": "success",
                            "message": "검색 및 크롤링이 완료되었습니다.",
                            "query": "서울시 강남구 30평대 아파트 매매 5억 이하",
                            "extracted_keywords": {
                                "address": {"sido": "서울시", "sigungu": "강남구"},
                                "transaction_type": ["매매"],
                                "building_type": ["아파트"],
                                "price_range": {"max": 500000000},
                                "area_range": "30평대"
                            },
                            "result_count": 25,
                            "redis_key": "search:abc123:results",
                            "redirect_url": "/board/results/search:abc123:results/"
                        }
                    )
                ]
            },
            400: {
                'description': '검색 실패 - 잘못된 요청',
                'examples': [
                    OpenApiExample(
                        'Empty Query',
                        summary='빈 검색어',
                        description='검색어가 제공되지 않은 경우',
                        value={"error": "검색어를 입력해주세요."}
                    ),
                    OpenApiExample(
                        'Invalid Keywords',
                        summary='키워드 추출 실패',
                        description='ChatGPT 키워드 추출 중 오류',
                        value={"error": "필수 조건이 부족합니다. 주소(시·도, 시·군·구), 거래유형, 건물유형을 모두 포함해주세요."}
                    )
                ]
            },
            500: {
                'description': '서버 오류',
                'examples': [
                    OpenApiExample(
                        'Server Error',
                        summary='서버 내부 오류',
                        description='크롤링 또는 시스템 오류',
                        value={"error": "검색 처리 중 오류가 발생했습니다. 다시 시도해주세요."}
                    )
                ]
            }
        }
    )
    def post(self, request, *args, **kwargs):
        print("--- SearchAPIView: POST request received ---")
        query_text = request.data.get('query')
        print(f"Received query: '{query_text}'")

        if not query_text:
            print("Error: Query text is empty.")
            return Response(
                {"error": "�ɴ| �%t�8�."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        chatgpt_client = ChatGPTKeywordExtractor()
        crawler = NaverRealEstateCrawler()

        try:
            print("Step 1: Calling ChatGPTClient to extract keywords...")
            # 1. ChatGPT| �t ��� �� (\� ��\ \ ��)
            extracted_keywords = chatgpt_client.extract_keywords(query_text)
            print(f"Step 1 Complete: Final keywords from ChatGPT: {extracted_keywords}")
            logger.info(f"Final keywords from ChatGPT: {extracted_keywords}")

            # 2. �� ���| print\ Ux
            print(f"Extracted Keywords for '{query_text}': {json.dumps(extracted_keywords, ensure_ascii=False, indent=2)}")

            print("Step 3: Calling NaverRealEstateCrawler to crawl properties...")
            # 3. ld� � (ChatGPT Q� � ��)
            crawled_properties_data = crawler.crawl_properties(extracted_keywords)
            print(f"Step 3 Complete: Crawled {len(crawled_properties_data)} properties.")
            logger.info(f"Crawled {len(crawled_properties_data)} properties.")

            print("Step 4: Storing crawling results in Redis...")
            # 4. ld� ��| Redis�  � (TTL: 5�)
            redis_key = redis_storage.store_crawling_results(extracted_keywords, crawled_properties_data)
            print(f"Step 4 Complete: Crawling results stored in Redis: {redis_key}")
            logger.info(f"Crawling results stored in Redis: {redis_key}")

            print("Step 5: Updating recommendation system keyword scores...")
            # 5. �� ܤ\ ��� �T� �pt�
            if recommendation_engine:
                # ���� ��� �T� �pt�
                recommendation_engine.update_user_keyword_scores(user.id, extracted_keywords)
                # � ��� ��� �T� �pt�
                recommendation_engine.update_global_keyword_scores(extracted_keywords)
                print("Step 5 Complete: Recommendation system keyword scores updated.")
                logger.info("Recommendation system keyword scores updated.")

            print("Step 6: Saving search history...")
            # 6. �� 0]  � (Redis � �h)
            search_history = SearchHistory.objects.create(
                user=user,
                query_text=query_text,
                parsed_keywords=extracted_keywords,  # ChatGPT Q� �  �
                result_count=len(crawled_properties_data),
                redis_key=redis_key  # Redis �  �
            )
            print(f"Step 6 Complete: Search history saved: {search_history.search_id}")
            logger.info(f"Search history saved: {search_history.search_id}")


            print("--- SearchAPIView: POST request complete ---")
            return Response(
                {
                    "status": "success",
                    "message": "��  ld�t D�ȵ��.",
                    "query": query_text,
                    "extracted_keywords": extracted_keywords,  # ChatGPT Q� � X
                    "result_count": len(crawled_properties_data),
                    "redis_key": redis_key,  # Board q� ��` Redis �
                    "redirect_url": f"/board/results/{redis_key}/" # Redis �| URL� �h
                },
                status=status.HTTP_200_OK
            )

        except ValueError as e:
            print(f"Error: Keyword extraction error: {e}")
            logger.error(f"Keyword extraction error: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            logger.exception("An unexpected error occurred during search API call.")
            return Response(
                {"error": "��  $X  ݈���. �� � �� ��t�8�."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )