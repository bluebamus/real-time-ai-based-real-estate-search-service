import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser

from home.services.keyword_extraction import get_keyword_extractor

logger = logging.getLogger(__name__)


class AuthTestAPIView(APIView):
    """
    인증 및 세션 테스트를 위한 API View
    """
    permission_classes = [IsAuthenticated]

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
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request, *args, **kwargs):
        print("--- SearchAPIView: POST request received ---")
        query_text = request.data.get('query')
        print(f"Received query: '{query_text}'")

        # 빈 쿼리 예외 처리 (None, 빈 문자열, 공백만 있는 경우)
        if not query_text or not query_text.strip():
            print("Error: Query text is empty or contains only whitespace.")
            return Response(
                {
                    "status": "error",
                    "message": "검색어를 입력해주세요.",
                    "error": "Query text is required and cannot be empty or whitespace only",
                    "error_code": "EMPTY_QUERY",
                    "query": query_text
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ChatGPT 키워드 추출 처리
        try:
            print("--- Starting keyword extraction ---")
            extractor = get_keyword_extractor()
            keyword_result = extractor.extract_keywords(query_text)

            print("=== Keyword Extraction Result ===")
            print(f"Status: {keyword_result.get('status')}")
            print(f"Query: {query_text}")

            # keyword_extraction.py는 성공 시에만 JSON을 반환하고, 에러 시에는 ValueError를 raise함
            # 따라서 여기에 도달했다면 성공한 것
            if keyword_result.get('status') == 'success':
                data = keyword_result.get('data', {})
                print(f"Address: {data.get('address')}")
                print(f"Transaction Type: {data.get('transaction_type')}")
                print(f"Building Type: {data.get('building_type')}")
                print(f"Sale Price: {data.get('sale_price')}")
                print(f"Deposit: {data.get('deposit')}")
                print(f"Monthly Rent: {data.get('monthly_rent')}")
                print(f"Area Range: {data.get('area_range')}")
                print("=================================")

                # 성공적인 키워드 추출 결과 반환
                return Response(
                    {
                        "status": "success",
                        "message": "키워드 추출이 완료되었습니다.",
                        "query": query_text,
                        "keywords": data,
                        "redirect_url": "/board/results/extracted_keywords/"
                    },
                    status=status.HTTP_200_OK
                )
            else:
                # 이 경우는 발생하지 않을 것이지만, 안전장치로 남겨둠
                print(f"Unexpected keyword result status: {keyword_result.get('status')}")
                print("=================================")

                return Response(
                    {
                        "status": "error",
                        "message": "키워드 추출 중 예상치 못한 오류가 발생했습니다.",
                        "error": "Unexpected keyword extraction result",
                        "error_code": "UNEXPECTED_RESULT",
                        "query": query_text
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except ValueError as ve:
            # keyword_extraction.py에서 ChatGPT 에러 응답 시 ValueError를 raise함
            error_msg = str(ve)
            print(f"Keyword extraction error: {error_msg}")
            print("=================================")
            logger.error(f"Keyword extraction error for query '{query_text}': {error_msg}")

            # ChatGPT에서 온 에러 메시지 파싱
            if "ChatGPT extraction failed:" in error_msg:
                # "ChatGPT extraction failed: MISSING_ADDRESS - Address is incomplete, only 시도 is provided."
                parts = error_msg.split("ChatGPT extraction failed: ", 1)
                if len(parts) > 1:
                    error_detail = parts[1]
                    if " - " in error_detail:
                        error_code, error_message = error_detail.split(" - ", 1)
                    else:
                        error_code = error_detail
                        error_message = "Unknown error"
                else:
                    error_code = "UNKNOWN_ERROR"
                    error_message = error_msg
            else:
                error_code = "VALIDATION_ERROR"
                error_message = error_msg

            return Response(
                {
                    "status": "error",
                    "message": "키워드 추출 중 오류가 발생했습니다.",
                    "error": error_message,
                    "error_code": error_code,
                    "query": query_text
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            # 기타 예상치 못한 오류
            print(f"Unexpected error during keyword extraction: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            print("=================================")
            logger.error(f"Unexpected error in SearchAPIView for query '{query_text}': {str(e)}", exc_info=True)

            return Response(
                {
                    "status": "error",
                    "message": "서버 내부 오류가 발생했습니다.",
                    "error": "Internal server error",
                    "query": query_text
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )