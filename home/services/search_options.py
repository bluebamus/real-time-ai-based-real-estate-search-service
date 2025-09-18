"""
검색 옵션 설정 모듈 (POC에서 분리)

POC의 set_search_options 메서드를 별도 모듈로 분리하여 크롤러 클래스 크기를 줄임
"""

import time
import logging
from typing import List, Optional
from playwright.sync_api import Page, Error

logger = logging.getLogger(__name__)


def set_search_options(
    page: Page,
    transaction_type: List[str],
    building_type: List[str],
    sale_price: Optional[List[int]],
    deposit: Optional[List[int]],
    monthly_rent: Optional[List[int]],
    area_range: Optional[str],
):
    """
    네이버 부동산 검색 옵션 설정 (POC 완전 복사)

    Args:
        page: Playwright 페이지 객체
        transaction_type: 거래 유형 리스트
        building_type: 건물 유형 리스트
        sale_price: 매매가 범위 [최소, 최대] 또는 [최대]
        deposit: 보증금 범위 [최소, 최대] 또는 [최대]
        monthly_rent: 월세 범위 [최소, 최대] 또는 [최대]
        area_range: 면적 범위 문자열
    """
    if not page:
        raise Exception("페이지가 초기화되지 않았습니다.")

    logger.info("[CRAWLER] 검색 옵션을 설정합니다.")

    # 기본 선택된 항목들 (매매, 전세, 아파트, 아파트분양권, 재건축)
    default_transaction_types = ["매매", "전세"]
    default_building_types = ["아파트", "아파트분양권", "재건축"]

    # 1. 거래유형 처리 (가장 먼저 수행)
    if transaction_type:
        logger.info(f"[CRAWLER] 거래유형 처리: {transaction_type}")
        # 기본값에서 제거할 항목들 (선택되어 있지만 요청에 없는 항목)
        to_deselect = [tt for tt in default_transaction_types if tt not in transaction_type]
        for tt in to_deselect:
            try:
                # 메인 필터에서만 클릭 (미니 필터 제외하고 표시되는 필터만)
                label_locator = page.locator(
                    f"div.article_box--option:not(._complexFilterBox) div._multiFilter[filtername='tradTpCd'] input[headernm='{tt}'] + label"
                )
                if label_locator.count() > 0:
                    label_locator.first.click()
                    logger.info(f"[CRAWLER] 거래유형 '{tt}' 선택 해제.")
                    time.sleep(0.5)
                else:
                    logger.debug(f"[CRAWLER] 거래유형 '{tt}' 요소를 찾을 수 없음")
            except Error as e:
                logger.warning(f"[CRAWLER] 거래유형 '{tt}' 선택 해제 실패: {e}")

        # 새로 선택할 항목들 (기본값에 없지만 요청에 있는 항목)
        to_select = [tt for tt in transaction_type if tt not in default_transaction_types]
        for tt in to_select:
            try:
                # 메인 필터에서만 클릭 (미니 필터 제외하고 표시되는 필터만)
                label_locator = page.locator(
                    f"div.article_box--option:not(._complexFilterBox) div._multiFilter[filtername='tradTpCd'] input[headernm='{tt}'] + label"
                )
                if label_locator.count() > 0:
                    label_locator.first.click()
                    logger.info(f"[CRAWLER] 거래유형 '{tt}' 선택.")
                    time.sleep(0.5)
                else:
                    logger.debug(f"[CRAWLER] 거래유형 '{tt}' 요소를 찾을 수 없음")
            except Error as e:
                logger.warning(f"[CRAWLER] 거래유형 '{tt}' 선택 실패: {e}")

    # 2. 매물유형 처리 (거래유형 다음에 수행)
    if building_type:
        logger.info(f"[CRAWLER] 매물유형 처리: {building_type}")
        # 중복 제거를 위한 처리된 아이템 추적
        processed_building_types = set()

        # 기본값에서 제거할 항목들 (선택되어 있지만 요청에 없는 항목)
        to_deselect = [bt for bt in default_building_types if bt not in building_type]
        for bt in to_deselect:
            if bt not in processed_building_types:
                try:
                    # 메인 필터에서만 클릭 (미니 필터 제외하고 표시되는 필터만)
                    label_locator = page.locator(
                        f"div.article_box--option:not(._complexFilterBox) div._multiFilter[filtername='rletTpCd'] input[headernm='{bt}'] + label"
                    )
                    if label_locator.count() > 0:
                        label_locator.first.click()
                        logger.info(f"[CRAWLER] 매물유형 '{bt}' 선택 해제.")
                        processed_building_types.add(bt)
                        time.sleep(0.5)
                    else:
                        logger.debug(f"[CRAWLER] 매물유형 '{bt}' 요소를 찾을 수 없음")
                except Error as e:
                    logger.warning(f"[CRAWLER] 매물유형 '{bt}' 선택 해제 실패: {e}")

        # 새로 선택할 항목들 (기본값에 없지만 요청에 있는 항목)
        to_select = [bt for bt in building_type if bt not in default_building_types]
        for bt in to_select:
            if bt not in processed_building_types:
                try:
                    # 메인 필터에서만 클릭 (미니 필터 제외하고 표시되는 필터만)
                    label_locator = page.locator(
                        f"div.article_box--option:not(._complexFilterBox) div._multiFilter[filtername='rletTpCd'] input[headernm='{bt}'] + label"
                    )
                    if label_locator.count() > 0:
                        label_locator.first.click()
                        logger.info(f"[CRAWLER] 매물유형 '{bt}' 선택.")
                        processed_building_types.add(bt)
                        time.sleep(0.5)
                    else:
                        logger.debug(f"[CRAWLER] 매물유형 '{bt}' 요소를 찾을 수 없음")
                except Error as e:
                    logger.warning(f"[CRAWLER] 매물유형 '{bt}' 선택 실패: {e}")

    # 3. 매매가 설정 (직접 입력)
    if sale_price:
        logger.info(f"[CRAWLER] 매매가: {sale_price} 직접 입력")
        try:
            if len(sale_price) == 1:
                page.locator("#dprcMax").fill(str(sale_price[0]))
                logger.info(f"[CRAWLER] 매매가 최대값 '{sale_price[0]}' 직접 입력 성공.")
            elif len(sale_price) == 2:
                page.locator("#dprcMin").fill(str(sale_price[0]))
                page.locator("#dprcMax").fill(str(sale_price[1]))
                logger.info(f"[CRAWLER] 매매가 범위 '{sale_price[0]} ~ {sale_price[1]}' 직접 입력 성공.")
            time.sleep(0.5)
        except Error as e:
            logger.warning(f"[CRAWLER] 매매가 설정 실패: {e}")

    # 4. 보증금 설정 (직접 입력)
    if deposit:
        logger.info(f"[CRAWLER] 보증금: {deposit} 직접 입력")
        try:
            if len(deposit) == 1:
                page.locator("#wprcMax").fill(str(deposit[0]))
                logger.info(f"[CRAWLER] 보증금 최대값 '{deposit[0]}' 직접 입력 성공.")
            elif len(deposit) == 2:
                page.locator("#wprcMin").fill(str(deposit[0]))
                page.locator("#wprcMax").fill(str(deposit[1]))
                logger.info(f"[CRAWLER] 보증금 범위 '{deposit[0]} ~ {deposit[1]}' 직접 입력 성공.")
            time.sleep(0.5)
        except Error as e:
            logger.warning(f"[CRAWLER] 보증금 설정 실패: {e}")

    # 5. 월세 설정 (직접 입력)
    if monthly_rent:
        logger.info(f"[CRAWLER] 월세: {monthly_rent} 직접 입력")
        try:
            if len(monthly_rent) == 1:
                page.locator("#rprcMax").fill(str(monthly_rent[0]))
                logger.info(f"[CRAWLER] 월세 최대값 '{monthly_rent[0]}' 직접 입력 성공.")
            elif len(monthly_rent) == 2:
                page.locator("#rprcMin").fill(str(monthly_rent[0]))
                page.locator("#rprcMax").fill(str(monthly_rent[1]))
                logger.info(f"[CRAWLER] 월세 범위 '{monthly_rent[0]} ~ {monthly_rent[1]}' 직접 입력 성공.")
            time.sleep(0.5)
        except Error as e:
            logger.warning(f"[CRAWLER] 월세 설정 실패: {e}")

    # 6. 면적 설정 (평수를 m²로 변환하여 선택)
    if area_range:
        area_option = _convert_pyeong_to_area_option(area_range)
        if area_option:
            logger.info(f"[CRAWLER] 면적대: '{area_range}' -> '{area_option}' 클릭")
            try:
                page.locator("#filterLayer #ct").get_by_role("listitem").filter(
                    has_text=area_option
                ).locator("label").click()
                logger.info(f"[CRAWLER] 면적대 '{area_option}' 클릭 성공.")
                time.sleep(0.5)
            except Error as e:
                logger.warning(f"[CRAWLER] 면적대 '{area_option}' 클릭 실패: {e}")

    # 7. 매물검색 버튼 클릭
    logger.info("[CRAWLER] 매물검색 버튼을 클릭합니다.")
    try:
        # dump.html에서 확인한 정확한 선택자 사용
        search_button = page.locator("a.btn_option.btn_option--search._filterSaveBtn")
        search_button.wait_for(state="visible", timeout=10000)
        search_button.click()
        logger.info("[CRAWLER] 매물검색 버튼 클릭 성공.")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
    except Error as e:
        logger.warning(f"[CRAWLER] 매물검색 버튼 클릭 실패: {e}")
        # 대안 선택자 시도
        try:
            logger.info("[CRAWLER] 대안 선택자로 매물검색 버튼 클릭을 재시도합니다.")
            alternative_button = page.locator("._filterSaveBtn")
            alternative_button.wait_for(state="visible", timeout=5000)
            alternative_button.click()
            logger.info("[CRAWLER] 대안 선택자로 매물검색 버튼 클릭 성공.")
            page.wait_for_load_state("networkidle")
            time.sleep(2)
        except Error as e2:
            logger.error(f"[CRAWLER] 매물검색 버튼 클릭 완전 실패: {e2}")

    page.wait_for_load_state("networkidle")
    time.sleep(2)
    logger.info("[CRAWLER] 검색 옵션 설정 완료.")


def _convert_pyeong_to_area_option(area_range: str) -> Optional[str]:
    """
    평수 범위를 네이버 부동산의 m² 면적 옵션으로 변환합니다. (POC 완전 복사)

    평수 -> m² 변환: 1평 = 3.305785 m²
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