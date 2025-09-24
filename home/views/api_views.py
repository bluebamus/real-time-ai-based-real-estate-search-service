import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

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

    def post(self, request, *args, **kwargs):
        print("--- SearchAPIView: POST request received ---")
        query_text = request.data.get('query')
        print(f"Received query: '{query_text}'")

        if not query_text:
            print("Error: Query text is empty.")
            return Response(
                {"error": "검색어를 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 간단한 응답 반환 (실제 구현은 나중에)
        return Response(
            {
                "status": "success",
                "message": "검색 요청이 처리되었습니다.",
                "query": query_text,
                "result_count": 0,
                "redirect_url": "/board/results/test_key/"
            },
            status=status.HTTP_200_OK
        )