import csv
import time
import traceback
from datetime import datetime

from playwright.sync_api import Browser, BrowserContext, Error, Page, sync_playwright


class NaverRealEstateScraper:
    """
    네이버 부동산 웹사이트에서 부동산 매물 정보를 스크래핑하는 클래스.
    """

    def __init__(self, headless: bool = False):
        """
        스크래퍼 초기화.

        :param headless: 브라우저를 headless 모드로 실행할지 여부.
        """
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.headless = headless

    def initialize_browser_and_page(self):
        """
        Playwright를 시작하고 브라우저와 페이지를 초기화합니다.
        쿠키 및 브라우저 설정을 포함합니다.
        """
        print("[INFO] Playwright 및 브라우저 초기화를 시작합니다.", flush=True)
        self.playwright = sync_playwright().start()

        user_cookies = {
            "NNB": "3C7PYUFWZWUGI",
            "NAC": "ua1EBcgqOrsZ",
            "BUC": "9zuEYCy2NEsg9dTDvyNNO5m8R-5tUNI96llreZdpRNE=",
            "nid_inf": "1772764205",
            "REALESTATE": "Mon%20Sep%2015%202025%2023%3A29%3A47%20GMT%2B0900%20(Korean%20Standard%20Time)",
            "PROP_TEST_KEY": "1757946587259.af7716dc3ead8d36166392fe23451a00bb653bd8b78343cc1b143cdecf12ab21",
            "PROP_TEST_ID": "c00c7672cb7105754536969e4_0daf4231d6c34601a1d88df9e55bc09888bd866",
            "_fwb": "286ZwfRXnJUKFFvqJhtwJ.1757946459556",
            "NACT": "1",
            "SRT30": "1757946460",
            "SRT5": "1757946460",
        }
        cookies_for_playwright = [
            {"name": name, "value": value, "domain": ".naver.com", "path": "/"}
            for name, value in user_cookies.items()
        ]

        MAX_RETRIES = 5
        INITIAL_RETRY_DELAY_SECONDS = 20
        target_url = "https://fin.land.naver.com/search"

        for attempt in range(MAX_RETRIES):
            try:
                if self.browser:
                    self.browser.close()
                print(
                    f"[INFO] Playwright Firefox 브라우저를 시작합니다... (시도 {attempt + 1}/{MAX_RETRIES})",
                    flush=True,
                )
                self.browser = self.playwright.firefox.launch(
                    headless=self.headless,
                    firefox_user_prefs={
                        "dom.webdriver.enabled": False,
                        "media.peerconnection.enabled": False,
                    },
                )
                self.context = self.browser.new_context(
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
                self.context.add_cookies(cookies_for_playwright)
                self.page = self.context.new_page()
                print(
                    "[SUCCESS] 브라우저 및 컨텍스트 설정이 완료되었습니다.", flush=True
                )

                print(f"[INFO] 초기 URL로 접속합니다: {target_url}", flush=True)
                self.page.goto(target_url, wait_until="networkidle", timeout=60000)
                print("[SUCCESS] 초기 URL 접속 성공.", flush=True)

                # URL이 404로 끝나는 경우 재시도
                if self.page.url.endswith("404"):
                    raise ValueError(f"URL이 404로 끝납니다: {self.page.url}")

                time.sleep(2)
                return

            except (Error, ValueError) as e:
                print(f"[WARNING] URL 접속 중 오류 발생: {e}", flush=True)
                if attempt >= MAX_RETRIES - 1:
                    raise
                time.sleep(INITIAL_RETRY_DELAY_SECONDS + attempt)

        raise Exception("최대 재시도 횟수를 초과하여 브라우저를 초기화하지 못했습니다.")

    def perform_search(self, search_query: str):
        if not self.page:
            raise Exception(
                "페이지가 초기화되지 않았습니다. 먼저 initialize_browser_and_page를 호출하세요."
            )

        print(f"\n[INFO] '{search_query}'(으)로 검색을 수행합니다.", flush=True)
        search_input_locator = self.page.locator("#search")
        search_input_locator.fill(search_query)
        time.sleep(2)
        search_input_locator.press("Enter")
        self.page.wait_for_load_state("networkidle")

        print(
            f"[INFO] 검색 결과 목록에서 '{search_query}' 링크를 찾습니다.", flush=True
        )
        result_locator = self.page.get_by_role(
            "link", name=search_query, exact=True
        ).first
        result_locator.wait_for(state="visible", timeout=10000)

        print(
            f"[INFO] '{search_query}' 링크를 클릭하여 페이지를 현재 탭에서 이동합니다.",
            flush=True,
        )
        link_href = result_locator.get_attribute("href")
        if link_href:
            self.page.goto(link_href, wait_until="networkidle")
        else:
            print(
                "[WARNING] 링크의 href 속성을 찾을 수 없어 기존 클릭 방식을 사용합니다.",
                flush=True,
            )
            result_locator.click()

        self.page.wait_for_load_state("networkidle")
        time.sleep(2)

        print(
            "[INFO] 'header_option_add _optionChange' 클래스를 가진 링크를 클릭합니다.",
            flush=True,
        )
        try:
            option_link_locator = self.page.locator(
                "a.header_option_add._optionChange"
            ).first
            option_link_locator.wait_for(state="visible", timeout=10000)
            option_link_locator.click()
            print(
                "[SUCCESS] 'header_option_add _optionChange' 링크 클릭 성공.",
                flush=True,
            )
            self.page.wait_for_load_state("networkidle")
            time.sleep(2)
        except Error as e:
            print(
                f"[WARNING] 'header_option_add _optionChange' 링크를 찾거나 클릭하는 데 실패했습니다: {e}",
                flush=True,
            )
            print("[WARNING] 이 단계는 건너뛰고 다음 작업으로 진행합니다.", flush=True)

    def set_search_options(
        self,
        transaction_type: list[str],
        building_type: list[str],
        sale_price: list[int] | None,
        deposit: list[int] | None,
        monthly_rent: list[int] | None,
        area_range: str | None,
    ):
        if not self.page:
            raise Exception(
                "페이지가 초기화되지 않았습니다. 먼저 initialize_browser_and_page를 호출하세요."
            )

        # 현재 페이지의 HTML을 dump.html로 저장
        try:
            html_content = self.page.content()
            with open("dump.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("[INFO] 현재 페이지 HTML을 dump.html로 저장했습니다.", flush=True)
        except Exception as e:
            print(f"[WARNING] dump.html 저장 실패: {e}", flush=True)

        print("\n[INFO] 검색 옵션을 설정합니다.", flush=True)

        # 기본 선택된 항목들 (매매, 전세, 아파트, 아파트분양권, 재건축)
        default_transaction_types = ["매매", "전세"]
        default_building_types = ["아파트", "아파트분양권", "재건축"]

        # 1. 거래유형 처리 (가장 먼저 수행)
        if transaction_type:
            print(f"[INFO] 거래유형 처리: {transaction_type}", flush=True)
            # 기본값에서 제거할 항목들 (선택되어 있지만 요청에 없는 항목)
            to_deselect = [
                tt for tt in default_transaction_types if tt not in transaction_type
            ]
            for tt in to_deselect:
                try:
                    # 메인 필터에서만 클릭 (미니 필터 제외하고 표시되는 필터만)
                    label_locator = self.page.locator(
                        f"div.article_box--option:not(._complexFilterBox) div._multiFilter[filtername='tradTpCd'] input[headernm='{tt}'] + label"
                    )
                    if label_locator.count() > 0:
                        label_locator.first.click()
                        print(f"[SUCCESS] 거래유형 '{tt}' 선택 해제.", flush=True)
                        time.sleep(0.5)
                    else:
                        print(
                            f"[DEBUG] 거래유형 '{tt}' 요소를 찾을 수 없음", flush=True
                        )
                except Error as e:
                    print(f"[WARNING] 거래유형 '{tt}' 선택 해제 실패: {e}", flush=True)

            # 새로 선택할 항목들 (기본값에 없지만 요청에 있는 항목)
            to_select = [
                tt for tt in transaction_type if tt not in default_transaction_types
            ]
            for tt in to_select:
                try:
                    # 메인 필터에서만 클릭 (미니 필터 제외하고 표시되는 필터만)
                    label_locator = self.page.locator(
                        f"div.article_box--option:not(._complexFilterBox) div._multiFilter[filtername='tradTpCd'] input[headernm='{tt}'] + label"
                    )
                    if label_locator.count() > 0:
                        label_locator.first.click()
                        print(f"[SUCCESS] 거래유형 '{tt}' 선택.", flush=True)
                        time.sleep(0.5)
                    else:
                        print(
                            f"[DEBUG] 거래유형 '{tt}' 요소를 찾을 수 없음", flush=True
                        )
                except Error as e:
                    print(f"[WARNING] 거래유형 '{tt}' 선택 실패: {e}", flush=True)

        # 2. 매물유형 처리 (거래유형 다음에 수행)
        if building_type:
            print(f"[INFO] 매물유형 처리: {building_type}", flush=True)
            # 중복 제거를 위한 처리된 아이템 추적
            processed_building_types = set()

            # 기본값에서 제거할 항목들 (선택되어 있지만 요청에 없는 항목)
            to_deselect = [
                bt for bt in default_building_types if bt not in building_type
            ]
            for bt in to_deselect:
                if bt not in processed_building_types:
                    try:
                        # 메인 필터에서만 클릭 (미니 필터 제외하고 표시되는 필터만)
                        label_locator = self.page.locator(
                            f"div.article_box--option:not(._complexFilterBox) div._multiFilter[filtername='rletTpCd'] input[headernm='{bt}'] + label"
                        )
                        if label_locator.count() > 0:
                            label_locator.first.click()
                            print(f"[SUCCESS] 매물유형 '{bt}' 선택 해제.", flush=True)
                            processed_building_types.add(bt)
                            time.sleep(0.5)
                        else:
                            print(
                                f"[DEBUG] 매물유형 '{bt}' 요소를 찾을 수 없음",
                                flush=True,
                            )
                    except Error as e:
                        print(
                            f"[WARNING] 매물유형 '{bt}' 선택 해제 실패: {e}", flush=True
                        )

            # 새로 선택할 항목들 (기본값에 없지만 요청에 있는 항목)
            to_select = [bt for bt in building_type if bt not in default_building_types]
            for bt in to_select:
                if bt not in processed_building_types:
                    try:
                        # 메인 필터에서만 클릭 (미니 필터 제외하고 표시되는 필터만)
                        label_locator = self.page.locator(
                            f"div.article_box--option:not(._complexFilterBox) div._multiFilter[filtername='rletTpCd'] input[headernm='{bt}'] + label"
                        )
                        if label_locator.count() > 0:
                            label_locator.first.click()
                            print(f"[SUCCESS] 매물유형 '{bt}' 선택.", flush=True)
                            processed_building_types.add(bt)
                            time.sleep(0.5)
                        else:
                            print(
                                f"[DEBUG] 매물유형 '{bt}' 요소를 찾을 수 없음",
                                flush=True,
                            )
                    except Error as e:
                        print(f"[WARNING] 매물유형 '{bt}' 선택 실패: {e}", flush=True)

        # 3. 매매가 설정 (직접 입력)
        if sale_price:
            print(f"[INFO] 매매가: {sale_price} 직접 입력", flush=True)
            try:
                if len(sale_price) == 1:
                    self.page.locator("#dprcMax").fill(str(sale_price[0]))
                    print(
                        f"[SUCCESS] 매매가 최대값 '{sale_price[0]}' 직접 입력 성공.",
                        flush=True,
                    )
                elif len(sale_price) == 2:
                    self.page.locator("#dprcMin").fill(str(sale_price[0]))
                    self.page.locator("#dprcMax").fill(str(sale_price[1]))
                    print(
                        f"[SUCCESS] 매매가 범위 '{sale_price[0]} ~ {sale_price[1]}' 직접 입력 성공.",
                        flush=True,
                    )
                time.sleep(0.5)
            except Error as e:
                print(f"[WARNING] 매매가 설정 실패: {e}", flush=True)

        # 4. 보증금 설정 (직접 입력)
        if deposit:
            print(f"[INFO] 보증금: {deposit} 직접 입력", flush=True)
            try:
                if len(deposit) == 1:
                    self.page.locator("#wprcMax").fill(str(deposit[0]))
                    print(
                        f"[SUCCESS] 보증금 최대값 '{deposit[0]}' 직접 입력 성공.",
                        flush=True,
                    )
                elif len(deposit) == 2:
                    self.page.locator("#wprcMin").fill(str(deposit[0]))
                    self.page.locator("#wprcMax").fill(str(deposit[1]))
                    print(
                        f"[SUCCESS] 보증금 범위 '{deposit[0]} ~ {deposit[1]}' 직접 입력 성공.",
                        flush=True,
                    )
                time.sleep(0.5)
            except Error as e:
                print(f"[WARNING] 보증금 설정 실패: {e}", flush=True)

        # 5. 월세 설정 (직접 입력)
        if monthly_rent:
            print(f"[INFO] 월세: {monthly_rent} 직접 입력", flush=True)
            try:
                if len(monthly_rent) == 1:
                    self.page.locator("#rprcMax").fill(str(monthly_rent[0]))
                    print(
                        f"[SUCCESS] 월세 최대값 '{monthly_rent[0]}' 직접 입력 성공.",
                        flush=True,
                    )
                elif len(monthly_rent) == 2:
                    self.page.locator("#rprcMin").fill(str(monthly_rent[0]))
                    self.page.locator("#rprcMax").fill(str(monthly_rent[1]))
                    print(
                        f"[SUCCESS] 월세 범위 '{monthly_rent[0]} ~ {monthly_rent[1]}' 직접 입력 성공.",
                        flush=True,
                    )
                time.sleep(0.5)
            except Error as e:
                print(f"[WARNING] 월세 설정 실패: {e}", flush=True)

        # 6. 면적 설정 (평수를 m²로 변환하여 선택)
        if area_range:
            area_option = self._convert_pyeong_to_area_option(area_range)
            if area_option:
                print(
                    f"[INFO] 면적대: '{area_range}' -> '{area_option}' 클릭", flush=True
                )
                try:
                    self.page.locator("#filterLayer #ct").get_by_role(
                        "listitem"
                    ).filter(has_text=area_option).locator("label").click()
                    print(f"[SUCCESS] 면적대 '{area_option}' 클릭 성공.", flush=True)
                    time.sleep(0.5)
                except Error as e:
                    print(
                        f"[WARNING] 면적대 '{area_option}' 클릭 실패: {e}", flush=True
                    )

        # 7. 매물검색 버튼 클릭
        print("[INFO] 매물검색 버튼을 클릭합니다.", flush=True)
        try:
            # dump.html에서 확인한 정확한 선택자 사용
            search_button = self.page.locator(
                "a.btn_option.btn_option--search._filterSaveBtn"
            )
            search_button.wait_for(state="visible", timeout=10000)
            search_button.click()
            print("[SUCCESS] 매물검색 버튼 클릭 성공.", flush=True)
            self.page.wait_for_load_state("networkidle")
            time.sleep(2)
        except Error as e:
            print(f"[WARNING] 매물검색 버튼 클릭 실패: {e}", flush=True)
            # 대안 선택자 시도
            try:
                print(
                    "[INFO] 대안 선택자로 매물검색 버튼 클릭을 재시도합니다.",
                    flush=True,
                )
                alternative_button = self.page.locator("._filterSaveBtn")
                alternative_button.wait_for(state="visible", timeout=5000)
                alternative_button.click()
                print("[SUCCESS] 대안 선택자로 매물검색 버튼 클릭 성공.", flush=True)
                self.page.wait_for_load_state("networkidle")
                time.sleep(2)
            except Error as e2:
                print(f"[ERROR] 매물검색 버튼 클릭 완전 실패: {e2}", flush=True)

        self.page.wait_for_load_state("networkidle")
        time.sleep(2)
        print("[SUCCESS] 검색 옵션 설정 완료.", flush=True)

    def _convert_pyeong_to_area_option(self, area_range: str) -> str | None:
        """
        평수 범위를 네이버 부동산의 m² 면적 옵션으로 변환합니다.

        평수 -> m² 변환: 1평 = 3.305785 m²

        평수 범위:
        ~ 10평 -> ~ 33㎡
        10평대 -> 33~66㎡
        20평대 -> 66~99㎡
        30평대 -> 99~132㎡
        40평대 -> 132~165㎡
        50평대 -> 165~198㎡
        60평대 -> 198~231㎡
        70평 ~ -> 231㎡ ~
        """
        if not area_range:
            return None

        area_range = area_range.strip()

        # 평수 범위별 매핑
        pyeong_to_sqm_mapping = {
            "~ 10평": "~ 33㎡",
            "10평대": "33~66㎡",
            "20평대": "66~99㎡",
            "30평대": "99~132㎡",
            "40평대": "132~165㎡",
            "50평대": "165~198㎡",
            "60평대": "198~231㎡",
            "70평 ~": "231㎡ ~",
        }

        return pyeong_to_sqm_mapping.get(area_range)

    def _parse_price(self, price_str: str) -> int:
        """
        '억', '천'과 같은 한글이 포함된 가격 문자열을 숫자(int)로 변환합니다.
        '~'가 포함된 범위 가격의 경우 앞의 값만 사용합니다.
        """
        price_str = price_str.strip()
        if not price_str:
            return 0

        if "~" in price_str:
            price_str = price_str.split("~")[0].strip()

        try:
            price_str = price_str.replace(",", "")

            parts = price_str.split("억")
            billions = 0
            millions = 0

            if len(parts) == 2:
                if parts[0].strip():
                    billions = int(parts[0].strip()) * 10000
                if parts[1].strip().replace("천", ""):
                    millions = int(parts[1].strip().replace("천", ""))
            elif len(parts) == 1:
                if "천" in parts[0]:
                    millions = int(parts[0].replace("천", "").strip())
                else:
                    millions = int(parts[0].strip())

            return (billions + millions) * 10000

        except (ValueError, IndexError) as e:
            print(f"[DEBUG]  - 가격 변환 오류: '{price_str}'. 오류: {e}")
            return 0

    def _parse_date(self, date_str: str) -> str:
        """
        '확인매물 YY.MM.DD.' 형식의 날짜 문자열을 'YYYY-MM-DD' 형식으로 변환합니다.
        """
        try:
            date_str = date_str.strip()
            if not date_str:
                return ""

            clean_str = date_str.replace("확인매물", "").replace(".", "").strip()
            dt_obj = datetime.strptime(f"20{clean_str}", "%Y%m%d")
            return dt_obj.strftime("%Y-%m-%d")
        except (ValueError, IndexError) as e:
            print(f"[DEBUG]  - 날짜 변환 오류: '{date_str}'. 오류: {e}")
            return ""

    def _parse_specification(self, spec_str: str) -> dict:
        """
        '사양' 문자열을 '평수', '층정보', '집방향'으로 파싱합니다.
        """
        pyeong = 0.0
        floor_info = ""
        direction = ""

        if not spec_str:
            return {"평수": pyeong, "층정보": floor_info, "집방향": direction}

        parts = [p.strip() for p in spec_str.split(",")]

        # 1. 평수 계산
        if len(parts) > 0:
            area_part = parts[0]
            if "/" in area_part and "㎡" in area_part:
                try:
                    sq_meter_str = area_part.split("/")[1].replace("㎡", "").strip()
                    sq_meter = float(sq_meter_str)
                    pyeong = round(sq_meter / 3.305785, 2)
                except (ValueError, IndexError) as e:
                    print(f"[DEBUG]  - 평수 변환 오류: '{area_part}'. 오류: {e}")
                    pyeong = 0.0

        # 2. 층정보
        if len(parts) > 1:
            floor_info = parts[1]

        # 3. 집방향
        if len(parts) > 2:
            direction = parts[2]

        return {"평수": pyeong, "층정보": floor_info, "집방향": direction}

    def _extract_data_from_item(self, item_element) -> dict:
        """
        단일 매물 아이템 요소에서 데이터를 추출합니다.
        """
        inner_item = item_element.locator(".item_inner")
        if inner_item.count() == 0:
            print("[DEBUG] '.item_inner'를 찾을 수 없어 이 항목을 건너뜁니다.")
            return {}

        def get_text_or_default(locator, field_name):
            try:
                if locator.count() > 0:
                    return locator.first.inner_text(timeout=1000).strip()
            except Error:
                pass
            return ""

        def get_all_texts_or_default(locator, field_name):
            try:
                if locator.count() > 0:
                    texts = locator.all_inner_texts()
                    return ", ".join([t.strip() for t in texts])
            except Error:
                pass
            return ""

        raw_price = get_text_or_default(
            inner_item.locator("div.price_area > strong.price"), "가격"
        )
        processed_price = self._parse_price(raw_price)

        raw_date = get_text_or_default(
            inner_item.locator("span.icon-badge.type-confirmed"), "갱신일"
        )
        processed_date = self._parse_date(raw_date)

        raw_spec = get_text_or_default(
            inner_item.locator("div.information_area p.info > span.spec"), "사양"
        )
        processed_spec = self._parse_specification(raw_spec)

        data = {
            "집주인": get_text_or_default(
                inner_item.locator("em.title_place"), "집주인"
            ),
            "거래타입": get_text_or_default(
                inner_item.locator("div.price_area > span.type"), "거래타입"
            ),
            "가격": processed_price,
            "건물 종류": get_text_or_default(
                inner_item.locator("div.information_area p.info > strong.type"),
                "건물 종류",
            ),
            "평수": processed_spec["평수"],
            "층정보": processed_spec["층정보"],
            "집방향": processed_spec["집방향"],
            "tag": get_all_texts_or_default(
                inner_item.locator("div.tag_area > em.tag"), "tag"
            ),
            "갱신일": processed_date,
        }

        # 유효성 검사: "집주인" 필드가 비어있으면 유효하지 않은 데이터로 간주
        if not data["집주인"]:
            return {}

        return data

    def scrape_all_markers_and_save_csv(self, filename: str):
        if not self.page:
            raise Exception(
                "페이지가 초기화되지 않았습니다. 먼저 initialize_browser_and_page를 호출하세요."
            )

        print(
            "\n[INFO] 지도 위의 모든 매물 마커를 클릭하여 정보 수집을 시작합니다.",
            flush=True,
        )
        try:
            self.page.wait_for_selector(
                ".marker_circle_count", state="attached", timeout=15000
            )
            print(
                "[SUCCESS] 지도 마커('marker_circle_count')가 로드되었습니다.",
                flush=True,
            )
        except Error:
            print(
                "[CRITICAL] 'marker_circle_count' 클래스를 찾지 못했습니다.", flush=True
            )
            return

        marker_spans = self.page.locator(".marker_circle_count").all()
        print(
            f"[INFO] 총 {len(marker_spans)}개의 마커 그룹을 발견했습니다.", flush=True
        )

        all_items_data = []
        processed_articles = set()

        for i, marker in enumerate(marker_spans):
            try:
                print(
                    f"\n[INFO] 마커 그룹 {i + 1}/{len(marker_spans)}을(를) 클릭합니다...",
                    flush=True,
                )

                # 마커가 클릭 가능한 상태인지 확인
                try:
                    marker.wait_for(state="visible", timeout=5000)
                    marker.scroll_into_view_if_needed()
                    time.sleep(1)  # 안정화 대기

                    # 강제 클릭 옵션 추가
                    marker.click(force=True, timeout=10000)
                    print(f"[SUCCESS] 마커 그룹 {i + 1} 클릭 성공", flush=True)
                except Error as click_error:
                    print(
                        f"[WARNING] 마커 그룹 {i + 1} 클릭 실패, 건너뛰기: {click_error}",
                        flush=True,
                    )
                    continue

                self.page.wait_for_load_state("networkidle", timeout=20000)

                time.sleep(2)

                item_elements = self.page.locator(".item_area._Listitem").all()
                print(
                    f"[INFO] 현재 마커 그룹에서 {len(item_elements)}개의 매물 항목을 찾았습니다. 데이터 추출을 시작합니다.",
                    flush=True,
                )

                for item_element in item_elements:
                    try:
                        article_link = item_element.locator("a.item_link").first
                        if article_link.count() > 0:
                            article_no = article_link.get_attribute("_articleno")
                            if article_no and article_no in processed_articles:
                                continue
                            if article_no:
                                processed_articles.add(article_no)
                        else:
                            continue
                    except Error:
                        continue

                    extracted_data = self._extract_data_from_item(item_element)
                    if extracted_data:
                        all_items_data.append(extracted_data)

            except Error as e:
                print(f"[ERROR] 마커 그룹 {i + 1} 처리 중 오류 발생: {e}", flush=True)
                # 페이지 상태 복구 시도
                try:
                    self.page.wait_for_load_state("networkidle", timeout=5000)
                    time.sleep(2)
                except Error:
                    pass
                continue

        if not all_items_data:
            print(
                "[WARNING] 수집된 데이터가 없습니다. CSV 파일을 생성하지 않습니다.",
                flush=True,
            )
            return

        print(
            f"\n[INFO] 총 {len(all_items_data)}개의 매물 정보를 수집했습니다. '{filename}' 파일로 저장합니다.",
            flush=True,
        )

        headers = all_items_data[0].keys()
        with open(filename, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(all_items_data)

        print(
            f"[SUCCESS] 데이터가 '{filename}'에 성공적으로 저장되었습니다.", flush=True
        )

    def close(self):
        if self.browser:
            print("[INFO] 브라우저를 종료합니다.", flush=True)
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


if __name__ == "__main__":
    print("==================================================", flush=True)
    print(
        "[INFO] 네이버 부동산 자동 검색 프로그램을 시작합니다. (리팩토링 버전)",
        flush=True,
    )
    print("==================================================", flush=True)

    scraper = NaverRealEstateScraper(headless=False)

    keywords1 = {
        "address": "경기도 수원시 장안구",
        "transaction_type": ["매매", "전세", "월세", "단기임대"],
        "building_type": [
            "아파트",
            "오피스텔",
            "상가",
            "빌라",
            "아파트분양권",
            "오피스텔분양권",
            "재건축",
            "전원주택",
            "단독/다가구",
            "상가주택",
            "한옥주택",
            "재개발",
            "원룸",
            "사무실",
            "공장/창고",
            "건물",
            "토지",
            "지식산업센터",
        ],
        "sale_price": [10000000, 200000000],
        "deposit": [1000000, 100000000],
        "monthly_rent": [100000, 200000],
        "area_range": "30평대",
    }

    keywords = {
        "address": "경기도 수원시 장안구",
        "transaction_type": ["매매", "전세"],
        "building_type": ["아파트", "아파트분양권", "재건축"],
        "sale_price": None,
        "deposit": None,
        "monthly_rent": None,
        "area_range": None,
    }

    try:
        scraper.initialize_browser_and_page()
        scraper.perform_search(keywords["address"])
        scraper.set_search_options(
            transaction_type=keywords["transaction_type"],
            building_type=keywords["building_type"],
            sale_price=keywords["sale_price"],
            deposit=keywords["deposit"],
            monthly_rent=keywords["monthly_rent"],
            area_range=keywords["area_range"],
        )
        scraper.scrape_all_markers_and_save_csv("popup_data.csv")
        time.sleep(2)
    except Exception as e:
        print(
            f"[CRITICAL] 스크래핑 작업 중 심각한 오류가 발생했습니다: {e}", flush=True
        )
        traceback.print_exc()
    finally:
        scraper.close()
        print("\n==================================================", flush=True)
        print("[INFO] 자동 검색 프로그램을 종료합니다.", flush=True)
        print("==================================================", flush=True)
