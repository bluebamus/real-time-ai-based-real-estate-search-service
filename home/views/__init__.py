import json
import logging
from django.shortcuts import render
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.mixins import LoginRequiredMixin

from home.models import SearchHistory, Property # Changed relative import to absolute
from home.services.keyword_extraction import ChatGPTKeywordExtractor
from home.services.crawlers import NaverRealEstateCrawler
from home.services.redis_storage import redis_storage
from utils.recommendations import recommendation_engine

logger = logging.getLogger(__name__)

class HomeView(LoginRequiredMixin, TemplateView):
    """
    메인 랜딩 페이지 뷰
    ChatGPT 유사 검색 인터페이스 제공
    """
    template_name = 'home/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


class SearchAPIView(APIView):
    """
    자연어 검색 요청을 처리하는 API 뷰
    ChatGPT를 통해 키워드를 추출하고, 크롤링을 트리거
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

        user = request.user
        chatgpt_client = ChatGPTKeywordExtractor()
        crawler = NaverRealEstateCrawler()

        try:
            print("Step 1: Calling ChatGPTClient to extract keywords...")
            # 1. ChatGPT를 통해 키워드 추출 (최종 결과로 바로 사용)
            extracted_keywords = chatgpt_client.extract_keywords(query_text)
            print(f"Step 1 Complete: Final keywords from ChatGPT: {extracted_keywords}")
            logger.info(f"Final keywords from ChatGPT: {extracted_keywords}")

            # 2. 추출된 키워드를 print로 확인
            print(f"Extracted Keywords for '{query_text}': {json.dumps(extracted_keywords, ensure_ascii=False, indent=2)}")

            print("Step 3: Calling NaverRealEstateCrawler to crawl properties...")
            # 3. 크롤링 실행 (ChatGPT 응답 직접 사용)
            crawled_properties_data = crawler.crawl_properties(extracted_keywords)
            print(f"Step 3 Complete: Crawled {len(crawled_properties_data)} properties.")
            logger.info(f"Crawled {len(crawled_properties_data)} properties.")

            print("Step 4: Storing crawling results in Redis...")
            # 4. 크롤링 결과를 Redis에 저장 (TTL: 5분)
            redis_key = redis_storage.store_crawling_results(extracted_keywords, crawled_properties_data)
            print(f"Step 4 Complete: Crawling results stored in Redis: {redis_key}")
            logger.info(f"Crawling results stored in Redis: {redis_key}")

            print("Step 5: Updating recommendation system keyword scores...")
            # 5. 추천 시스템 키워드 스코어 업데이트
            if recommendation_engine:
                # 사용자별 키워드 스코어 업데이트
                recommendation_engine.update_user_keyword_scores(user.id, extracted_keywords)
                # 전체 사용자 키워드 스코어 업데이트
                recommendation_engine.update_global_keyword_scores(extracted_keywords)
                print("Step 5 Complete: Recommendation system keyword scores updated.")
                logger.info("Recommendation system keyword scores updated.")

            print("Step 6: Saving search history...")
            # 6. 검색 기록 저장 (Redis 키 포함)
            search_history = SearchHistory.objects.create(
                user=user,
                query_text=query_text,
                parsed_keywords=extracted_keywords,  # ChatGPT 응답 직접 저장
                result_count=len(crawled_properties_data),
                redis_key=redis_key  # Redis 키 저장
            )
            print(f"Step 6 Complete: Search history saved: {search_history.search_id}")
            logger.info(f"Search history saved: {search_history.search_id}")


            print("--- SearchAPIView: POST request complete ---")
            return Response(
                {
                    "status": "success",
                    "message": "검색 및 크롤링이 완료되었습니다.",
                    "query": query_text,
                    "extracted_keywords": extracted_keywords,  # ChatGPT 응답 직접 반환
                    "result_count": len(crawled_properties_data),
                    "redis_key": redis_key,  # Board 앱에서 사용할 Redis 키
                    "redirect_url": f"/board/results/{redis_key}/" # Redis 키를 URL에 포함
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
                {"error": "검색 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )