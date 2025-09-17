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
from utils.ai import ChatGPTClient
from utils.parsers import KeywordParser
from utils.crawlers import NaverRealEstateCrawler

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
        chatgpt_client = ChatGPTClient()
        keyword_parser = KeywordParser()
        crawler = NaverRealEstateCrawler()

        try:
            print("Step 1: Calling ChatGPTClient to extract keywords...")
            # 1. ChatGPT를 통해 키워드 추출
            raw_keywords = chatgpt_client.extract_keywords(query_text)
            print(f"Step 1 Complete: Raw keywords from ChatGPT: {raw_keywords}")
            logger.info(f"Raw keywords from ChatGPT: {raw_keywords}")

            print("Step 2: Calling KeywordParser to validate and apply defaults...")
            # 2. 키워드 파서로 검증 및 기본값 적용
            parsed_keywords = keyword_parser.parse(raw_keywords)
            print(f"Step 2 Complete: Parsed keywords: {parsed_keywords}")
            logger.info(f"Parsed keywords after validation and defaults: {parsed_keywords}")

            # 3. 추출된 키워드를 print로 확인
            print(f"Extracted Keywords for '{query_text}': {json.dumps(parsed_keywords, ensure_ascii=False, indent=2)}")

            print("Step 4: Calling NaverRealEstateCrawler to crawl properties...")
            # 4. 크롤링 실행
            crawled_properties_data = crawler.crawl_properties(parsed_keywords)
            print(f"Step 4 Complete: Crawled {len(crawled_properties_data)} properties.")
            logger.info(f"Crawled {len(crawled_properties_data)} properties.")

            print("Step 5: Saving search history...")
            # 5. 검색 기록 저장
            search_history = SearchHistory.objects.create(
                user=user,
                query_text=query_text,
                parsed_keywords=parsed_keywords,
                result_count=len(crawled_properties_data),
                redis_key="" # Redis caching is excluded for now
            )
            print(f"Step 5 Complete: Search history saved: {search_history.search_id}")
            logger.info(f"Search history saved: {search_history.search_id}")

            print("Step 6: Saving crawled properties to database...")
            # 6. 크롤링된 데이터를 Property 모델에 저장 (또는 업데이트)
            saved_properties = []
            for prop_data in crawled_properties_data:
                try:
                    property_obj = Property.objects.create(
                        address=prop_data.get('address'),
                        owner_type=prop_data.get('owner_type'),
                        transaction_type=prop_data.get('transaction_type'),
                        price=prop_data.get('price'),
                        building_type=prop_data.get('building_type'),
                        area_pyeong=prop_data.get('area_pyeong'),
                        floor_info=prop_data.get('floor_info'),
                        direction=prop_data.get('direction'),
                        tags=prop_data.get('tags'),
                        updated_date=prop_data.get('updated_date'),
                        detail_url=prop_data.get('detail_url'),
                        image_urls=prop_data.get('image_urls'),
                        description=prop_data.get('description')
                    )
                    saved_properties.append(property_obj.property_id)
                except Exception as e:
                    print(f"Error saving property: {e} - Data: {prop_data}")
                    logger.error(f"Error saving property: {e} - Data: {prop_data}")
                    continue
            print(f"Step 6 Complete: Saved {len(saved_properties)} properties.")


            print("--- SearchAPIView: POST request complete ---")
            return Response(
                {
                    "status": "success",
                    "message": "검색 및 크롤링이 완료되었습니다.",
                    "query": query_text,
                    "parsed_keywords": parsed_keywords,
                    "result_count": len(crawled_properties_data),
                    "saved_property_ids": saved_properties,
                    "redirect_url": f"/board/results/?search_history_id={search_history.search_id}" # Example redirect
                },
                status=status.HTTP_200_OK
            )

        except ValueError as e:
            print(f"Error: Keyword parsing or validation error: {e}")
            logger.error(f"Keyword parsing or validation error: {e}")
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