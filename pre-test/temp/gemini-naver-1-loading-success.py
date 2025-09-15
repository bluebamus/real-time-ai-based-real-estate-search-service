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
            target_url = "https://new.land.naver.com/"

            print(f"[INFO] 초기 URL로 접속합니다: {target_url}")
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            print("[SUCCESS] 페이지 접속 및 초기 로딩 완료.")

            # 검색창에 "경기도 수원시 장안구" 입력 및 엔터
            search_query = "경기도 수원시 장안구"
            search_input_locator = page.locator('//*[@id="land_search"]')
            print(f"[INFO] 검색창에 '{search_query}'를 입력합니다.")
            search_input_locator.fill(search_query)
            print("[INFO] Enter 키를 눌러 검색을 실행합니다.")
            search_input_locator.press("Enter")

            # 검색 결과 팝업에서 정확히 일치하는 항목을 클릭
            print(f"[INFO] 검색 결과 팝업에서 '{search_query}' 항목을 찾습니다.")
            # get_by_text를 사용하여 텍스트가 정확히 일치하는 요소를 찾습니다.
            result_locator = page.get_by_text(search_query, exact=True)

            # 여러 요소가 있을 수 있으므로 첫 번째 보이는 요소를 클릭합니다.
            result_locator.first.wait_for(state="visible", timeout=10000)
            print(f"[INFO] '{search_query}' 항목을 클릭합니다.")
            result_locator.first.click()

            # 화면 전환 대기
            print("[INFO] 화면 전환을 기다립니다...")
            page.wait_for_load_state("networkidle", timeout=30000)
            print("[SUCCESS] 화면 전환이 완료되었습니다.")

            # 5초 대기 후 종료
            print("[INFO] 5초 후 프로그램을 종료합니다.")
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
