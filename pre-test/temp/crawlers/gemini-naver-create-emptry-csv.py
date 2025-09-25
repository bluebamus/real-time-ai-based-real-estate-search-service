import csv
import time
import traceback
import sys

from playwright.sync_api import Error, sync_playwright


def main():
    """
    메인 실행 함수. Playwright를 사용하여 페이지를 로드하고 특정 지역을 검색합니다.
    """

    print("==================================================")
    print("[INFO] 네이버 부동산 자동 검색 프로그램을 시작합니다. (Playwright 기반)")
    print("==================================================")
    browser = None

    try:
        with sync_playwright() as p:
            page = None

            # 재시도 설정 변수
            MAX_RETRIES = 5  # 최대 반복 횟수
            INITIAL_RETRY_DELAY_SECONDS = 5  # 재시도 전 초기 대기 시간 (초)

            user_cookies = {
                "NNB": "3C7PYUFWZWUGI",
                "NAC": "ua1EBcgqOrsZ",
                "BUC": "9zuEYCy2NEsg9dTDvyNNO5m8R-5tUNI96llreZdpRNE=",
                "nid_inf": "1772764205",
                "REALESTATE": "Mon%20Sep%2015%202025%2023%3A29%3A47%20GMT%2B0900%20(Korean%20Standard%20Time)",
                "PROP_TEST_KEY": "1757946587259.af7716dc3ead8d36166392fe23451a00bb653bd8b78343cc1b143cdecf12ab21",
                "PROP_TEST_ID": "c00c7672cb7105754536969e4_0daf4231d6c34601a1d88df9e55bc09888bd866",
                "_fwb": "2986ZwfRXnJUKFFvqJhtwJ.1757946459556",
                "NACT": "1",
                "SRT30": "1757946460",
                "SRT5": "1757946460",
            }
            cookies_for_playwright = [
                {"name": name, "value": value, "domain": ".naver.com", "path": "/"}
                for name, value in user_cookies.items()
            ]

            target_url = "https://fin.land.naver.com/search"

            for attempt in range(MAX_RETRIES):
                try:
                    if browser:
                        browser.close()  # Ensure previous browser is closed before new launch
                    print(
                        f"[INFO] Playwright Firefox 브라우저를 시작합니다... (시도 {attempt + 1}/{MAX_RETRIES})"
                    )
                    browser = p.firefox.launch(
                        headless=False,
                        firefox_user_prefs={
                            "dom.webdriver.enabled": False,
                            "media.peerconnection.enabled": False,
                        },
                    )
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
                        viewport={"width": 1920, "height": 1080},
                        locale="ko-KR",
                        extra_http_headers={
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                            "Accept-Encoding": "gzip, deflate, br",
                            "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
                            "Connection": "keep-alive",
                            "Upgrade-Insecure-Requests": "1",
                        },
                    )
                    context.add_cookies(cookies_for_playwright)
                    page = context.new_page()
                    print("[SUCCESS] 브라우저 및 컨텍스트 설정이 완료되었습니다.")

                    print(f"[INFO] 초기 URL로 접속합니다: {target_url}")
                    page.goto(target_url, wait_until="networkidle", timeout=60000)

                    if page.status() == 404:
                        raise Exception(f"HTTP 404 error encountered for {target_url}")

                    print("[SUCCESS] 초기 URL 접속 성공.")
                    time.sleep(2)
                    break  # Exit retry loop on success
                except Error as e:
                    print(f"[WARNING] URL 접속 중 Playwright 오류 발생: {e}")
                    if attempt < MAX_RETRIES - 1:  # Check if more retries are available
                        current_delay = INITIAL_RETRY_DELAY_SECONDS + attempt
                        print(f"[INFO] {current_delay}초 후 재시도합니다.")
                        time.sleep(current_delay)
                    else:  # Last attempt failed
                        print(
                            "[CRITICAL] 최대 재시도 횟수를 초과했습니다. 프로그램 종료."
                        )
                        raise  # Re-raise the last exception
                except Exception as e:  # Catch the explicit 404 check
                    print(f"[WARNING] URL 접속 중 일반 오류 발생: {e}")
                    if attempt < MAX_RETRIES - 1:  # Check if more retries are available
                        current_delay = INITIAL_RETRY_DELAY_SECONDS + attempt
                        print(f"[INFO] {current_delay}초 후 재시도합니다.")
                        time.sleep(current_delay)
                    else:  # Last attempt failed
                        print(
                            "[CRITICAL] 최대 재시도 횟수를 초과했습니다. 프로그램 종료."
                        )
                        raise Exception(
                            f"Failed after multiple retries: {e}"
                        )  # Re-raise with more context

                # 검색창에 "경기도 수원시 장안구" 입력 및 엔터
                search_query = "경기도 수원시 장안구"
                search_input_locator = page.locator("#search")
                print(f"[INFO] 검색창에 '{search_query}'를 입력합니다.")
                search_input_locator.fill(search_query)
                time.sleep(2)  # 2초 대기
                print("[INFO] Enter 키를 눌러 검색을 실행합니다.")
                search_input_locator.press("Enter")
                page.wait_for_load_state(
                    "networkidle"
                )  # 검색 후 네트워크 유휴 상태 대기

                # 검색 결과 목록에서 검색어와 정확히 일치하는 링크를 클릭
                print(f"[INFO] 검색 결과 목록에서 '{search_query}' 링크를 찾습니다.")
                result_locator = page.get_by_role("link", name=search_query, exact=True)

                result_locator.first.wait_for(state="visible", timeout=10000)
                print(
                    f"[INFO] '{search_query}' 링크를 클릭하여 페이지를 이동합니다. (동일 탭)"
                )
                link_href = result_locator.first.get_attribute("href")
                if link_href:
                    page.goto(
                        link_href, wait_until="networkidle"
                    )  # 동일 탭에서 페이지 이동
                else:
                    print("[WARNING] 링크의 href 속성을 찾을 수 없습니다.")

                print(
                    "[INFO] 2초 대기 후 'marker_circle_count' 클래스가 나타날 때까지 대기합니다."
                )
                time.sleep(2)  # 2초 대기
                try:
                    # 'marker_circle_count' 클래스를 포함하는 요소를 기다립니다.
                    page.wait_for_selector(
                        ".marker_circle_count", state="attached", timeout=10000
                    )
                    print("[SUCCESS] 'marker_circle_count' 클래스가 발견되었습니다.")
                except Error:
                    print(
                        "[CRITICAL] 'marker_circle_count' 클래스를 찾지 못했습니다. 페이지 로딩에 문제가 있거나 클래스 이름이 변경되었을 수 있습니다."
                    )

                # --- 신규 크롤링 로직 시작 ---
                print("\n[INFO] 지도 위의 매물 마커를 클릭하여 정보를 수집합니다.")

                extracted_data = []
                # 모든 marker_circle_count span 요소 찾기
                marker_spans = page.locator(".marker_circle_count").all()
                print(f"[INFO] 총 {len(marker_spans)}개의 매물 마커를 찾았습니다.")

                for i, marker_span in enumerate(marker_spans):
                    print(
                        f"[INFO] {i + 1}/{len(marker_spans)}번째 매물 마커 클릭 시도..."
                    )
                    try:
                        marker_span.click()
                        # 클릭 후 페이지 내용이 업데이트될 때까지 대기 (필요시 추가적인 대기 로직)
                        page.wait_for_load_state(
                            "networkidle"
                        )  # 페이지 내용이 로드될 때까지 대기

                        # HTML에서 item--child 클래스 찾기 (각 매물 항목)
                        item_child_elements = page.locator(".item--child").all()
                        if item_child_elements:
                            print(
                                f"[INFO] 페이지 내에서 {len(item_child_elements)}개의 매물 항목을 찾았습니다."
                            )
                            for item_idx, item_element in enumerate(
                                item_child_elements
                            ):
                                # 각 항목에서 필요한 정보 추출
                                owner_place_text = (
                                    item_element.locator("em.title_place").inner_text()
                                    if item_element.locator("em.title_place").count()
                                    > 0
                                    else ""
                                )
                                transaction_type_text = (
                                    item_element.locator(
                                        ".price_area .type"
                                    ).inner_text()
                                    if item_element.locator(".price_area .type").count()
                                    > 0
                                    else ""
                                )
                                price_text = (
                                    item_element.locator("strong.price").inner_text()
                                    if item_element.locator("strong.price").count() > 0
                                    else ""
                                )

                                info_type_text = (
                                    item_element.locator(".information_area p.info strong.type").inner_text()
                                    if item_element.locator(".information_area p.info strong.type").count() > 0
                                    else ""
                                )
                                detail_info_text = (
                                    item_element.locator(".information_area p.info span.spec").inner_text()
                                    if item_element.locator(".information_area p.info span.spec").count() > 0
                                    else ""
                                )


                                tag_area_tags = ", ".join(
                                    item_element.locator(
                                        ".tag_area .tag"
                                    ).all_inner_texts()
                                )

                                confirmation_date_text = (
                                    item_element.locator(
                                        "span.icon-badge.type-confirmed"
                                    ).inner_text()
                                    if item_element.locator(
                                        "span.icon-badge.type-confirmed"
                                    ).count()
                                    > 0
                                    else ""
                                )
                                link_href = (
                                    item_element.locator("a.item_link").get_attribute(
                                        "href"
                                    )
                                    if item_element.locator("a.item_link").count() > 0
                                    else ""
                                )

                                extracted_data.append(
                                    {
                                        "marker_index": i,
                                        "집주인": owner_place_text,
                                        "타입": transaction_type_text,
                                        "가격": price_text,
                                        "정보타입": info_type_text,
                                        "상세정보": detail_info_text,
                                        "tag_area": tag_area_tags,
                                        "확인매물 날짜": confirmation_date_text,
                                        "link_href": link_href,
                                    }
                                )
                                print(
                                    f"[SUCCESS] 매물 항목 추출 완료 ({item_idx + 1}) - 가격: {price_text}, 유형: {transaction_type_text}"
                                )
                        else:
                            print(
                                "[WARNING] 페이지 내에서 매물 항목 (item--child)을 찾을 수 없습니다."
                            )
                        print("[SUCCESS] 내용 추출 완료.")

                    except Error as e:
                        print(
                            f"[ERROR] 매물 마커 클릭 또는 내용 추출 중 오류 발생: {e}"
                        )
                    time.sleep(2)  # 다음 마커 클릭 전 대기

                # 추출된 데이터를 CSV 파일로 저장
                csv_file_path = "popup_data.csv"
                if extracted_data:
                    with open(
                        csv_file_path, "w", newline="", encoding="utf-8"
                    ) as csvfile:
                        fieldnames = [
                            "marker_index",
                            "집주인",
                            "타입",
                            "가격",
                            "정보타입",
                            "상세정보",
                            "tag_area",
                            "확인매물 날짜",
                            "link_href",
                        ]
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(extracted_data)
                    print(
                        f"[SUCCESS] 추출된 데이터가 '{csv_file_path}'에 저장되었습니다."
                    )
                else:
                    print("[WARNING] 추출된 데이터가 없습니다.")

                print(
                    "\n[INFO] 모든 매물 마커 처리가 완료되었습니다. 프로그램을 종료합니다."
                )
                if browser: # Ensure browser is closed before exiting the 'with' block
                    print("[INFO] 브라우저를 종료합니다.")
                    browser.close()
                sys.exit(0) # Force program termination
    except Error as e:
        print("[CRITICAL] Playwright 작업 중 오류가 발생했습니다.")
        print(f"[ERROR] 상세 정보: {e}")
        traceback.print_exc()
    except Exception:
        print("[CRITICAL] 'main' 함수 실행 중 예상치 못한 오류가 발생했습니다.")
        traceback.print_exc()

    finally:
        # browser.close() should NOT be here anymore
        print("==================================================")
        print("[INFO] 자동 검색 프로그램을 종료합니다.")
        print("==================================================")


if __name__ == "__main__":
    main()
