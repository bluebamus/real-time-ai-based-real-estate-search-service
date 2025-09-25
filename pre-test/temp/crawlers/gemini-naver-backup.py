import csv
import time
import traceback

from playwright.sync_api import Error, sync_playwright


def main():
    """
    메인 실행 함수. Playwright를 사용하여 페이지를 로드하고 특정 지역을 검색합니다.
    """
    print("==================================================")
    print("[INFO] 네이버 부동산 자동 검색 프로그램을 시작합니다. (Playwright 기반)")
    print("==================================================")

    with sync_playwright() as p:
        browser = None
        try:
            print("[INFO] Playwright Firefox 브라우저를 시작합니다...")
            # Firefox 브라우저를 실행하고, 자동화 탐지를 우회하기 위한 설정을 추가합니다.
            browser = p.firefox.launch(
                headless=False,
                firefox_user_prefs={
                    "dom.webdriver.enabled": False,  # WebDriver 플래그 비활성화
                    "media.peerconnection.enabled": False,  # WebRTC를 통한 IP 유출 방지
                },
            )

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

            # 실제 사용자와 유사한 환경을 위해 컨텍스트를 설정합니다.
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
                viewport={"width": 1920, "height": 1080},  # 일반적인 데스크톱 해상도
                locale="ko-KR",  # 한국어 설정
            )
            context.add_cookies(cookies_for_playwright)
            page = context.new_page()
            print("[SUCCESS] 브라우저 및 컨텍스트 설정이 완료되었습니다.")

            # 타겟 URL
            target_url = "https://fin.land.naver.com/search"

            print(f"[INFO] 초기 URL로 접속합니다: {target_url}")
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            print("[SUCCESS] 페이지 접속 및 초기 로딩 완료.")

            # 검색창에 "경기도 수원시 장안구" 입력 및 엔터
            search_query = "경기도 수원시 장안구"
            search_input_locator = page.locator("#search")
            print(f"[INFO] 검색창에 '{search_query}'를 입력합니다.")
            search_input_locator.fill(search_query)
            print("[INFO] Enter 키를 눌러 검색을 실행합니다.")
            search_input_locator.press("Enter")

            # 검색 결과 목록에서 검색어와 정확히 일치하는 링크를 클릭
            print(f"[INFO] 검색 결과 목록에서 '{search_query}' 링크를 찾습니다.")
            result_locator = page.get_by_role("link", name=search_query, exact=True)

            result_locator.first.wait_for(state="visible", timeout=10000)
            print(f"[INFO] '{search_query}' 링크를 클릭하여 페이지를 이동합니다.")
            result_locator.first.click()

            # 화면 전환 대기
            print("[INFO] 화면 전환을 기다립니다...")
            page.wait_for_load_state("networkidle", timeout=30000)
            print("[SUCCESS] 화면 전환이 완료되었습니다.")

            # --- 신규 크롤링 로직 시작 ---
            print("\n[INFO] 지도 위의 매물 마커를 클릭하여 정보를 수집합니다.")
            all_properties_data = []

            try:
                # 타겟 마커와 팝업의 CSS 선택자
                marker_selector = "div.marker_circle > span:nth-child(1)"
                popup_selector = ".popup_info_box"

                # 마커가 IFrame 내에 있는지 확인하고, 있다면 해당 프레임을 타겟으로 설정
                target_frame = page
                try:
                    print("[INFO] 메인 페이지에서 마커를 찾는 중...")
                    page.wait_for_selector(
                        marker_selector, state="visible", timeout=5000
                    )
                    print("[SUCCESS] 메인 페이지에서 마커를 찾았습니다.")
                except Error:
                    print(
                        "[WARNING] 메인 페이지에서 마커를 찾지 못했습니다. IFrame을 탐색합니다..."
                    )
                    iframes = page.locator("iframe").all()
                    found_in_frame = False
                    for i, iframe_locator in enumerate(iframes):
                        try:
                            frame_content = iframe_locator.content_frame()
                            frame_content.wait_for_selector(
                                marker_selector, state="visible", timeout=3000
                            )
                            print(
                                f"[SUCCESS] IFrame #{i + 1}에서 마커를 찾았습니다. 이 프레임을 타겟으로 설정합니다."
                            )
                            target_frame = frame_content
                            found_in_frame = True
                            break
                        except Error:
                            continue
                    if not found_in_frame:
                        raise Error(
                            "페이지와 모든 IFrame을 탐색했지만 마커를 찾을 수 없었습니다."
                        )

                marker_count = target_frame.locator(marker_selector).count()

                if marker_count == 0:
                    print("[WARNING] 지도에서 매물 마커를 찾을 수 없습니다.")
                else:
                    print(
                        f"[INFO] 총 {marker_count}개의 매물 마커를 찾았습니다. 순차적으로 정보를 수집합니다."
                    )

                    for i in range(marker_count):
                        print(f"\n--- 마커 {i + 1}/{marker_count} 처리 중 ---")
                        try:
                            marker = target_frame.locator(marker_selector).nth(i)

                            marker.scroll_into_view_if_needed()
                            marker.click(timeout=5000)

                            target_frame.wait_for_selector(
                                popup_selector, state="visible", timeout=5000
                            )
                            print("[SUCCESS] 정보 팝업이 나타났습니다.")

                            popup_locator = target_frame.locator(popup_selector)

                            title = popup_locator.locator(
                                ".item_title .text"
                            ).text_content(timeout=2000)
                            price_type = popup_locator.locator(
                                ".price_line .type"
                            ).text_content(timeout=2000)
                            price_value = popup_locator.locator(
                                ".price_line .price"
                            ).text_content(timeout=2000)
                            price = f"{price_type} {price_value}"
                            spec = popup_locator.locator(
                                ".info_area p.line .spec"
                            ).text_content(timeout=2000)

                            tags_elements = popup_locator.locator(
                                ".tag_area span"
                            ).all()
                            tags = " ".join(
                                [tag.text_content() for tag in tags_elements]
                            )

                            date_element = popup_locator.locator(
                                "*:has-text('확인매물')"
                            ).last
                            confirm_date = (
                                date_element.text_content() if date_element else "N/A"
                            )

                            combined_info = (
                                f"제목: {title.strip()} | "
                                f"가격: {price.strip()} | "
                                f"스펙: {spec.strip()} | "
                                f"태그: {tags.strip()} | "
                                f"확인일: {confirm_date.strip()}"
                            )

                            print(f"[DATA] 수집된 정보: {combined_info}")
                            all_properties_data.append([combined_info])

                            marker.scroll_into_view_if_needed()
                            marker.click(timeout=5000)
                            target_frame.wait_for_selector(
                                popup_selector, state="hidden", timeout=5000
                            )
                            print("[SUCCESS] 팝업을 닫았습니다.")

                            time.sleep(0.5)

                        except Error as e:
                            print(
                                f"[ERROR] 마커 {i + 1} 처리 중 오류 발생: {e}. 다음으로 넘어갑니다."
                            )
                            if target_frame.locator(popup_selector).is_visible():
                                try:
                                    target_frame.locator(marker_selector).nth(i).click(
                                        timeout=2000
                                    )
                                except:
                                    pass
                            continue

                if all_properties_data:
                    filename = "result.csv"
                    print(
                        f"\n[INFO] 수집된 {len(all_properties_data)}개의 매물 정보를 '{filename}' 파일로 저장합니다."
                    )
                    with open(
                        filename, "w", newline="", encoding="utf-8-sig"
                    ) as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(["매물 정보"])
                        writer.writerows(all_properties_data)
                    print(f"[SUCCESS] '{filename}' 파일 저장이 완료되었습니다.")
                else:
                    print(
                        "\n[INFO] 수집된 매물 정보가 없어 CSV 파일을 생성하지 않았습니다."
                    )

            except Error as e:
                print(f"[CRITICAL] 매물 정보 수집 과정에서 오류 발생: {e}")
                traceback.print_exc()

            # 5초 대기 후 종료
            print("\n[INFO] 5초 후 프로그램을 종료합니다.")
            time.sleep(5)

        except Error as e:
            print("[CRITICAL] Playwright 작업 중 오류가 발생했습니다.")
            print(f"[ERROR] 상세 정보: {e}")
            traceback.print_exc()
        except Exception:
            print("[CRITICAL] 'main' 함수 실행 중 예상치 못한 오류가 발생했습니다.")
            traceback.print_exc()

        finally:
            if browser:
                print("[INFO] 브라우저를 종료합니다.")
                browser.close()
            print("==================================================")
            print("[INFO] 자동 검색 프로그램을 종료합니다.")
            print("==================================================")


if __name__ == "__main__":
    main()
