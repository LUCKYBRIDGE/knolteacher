import os
import sys
import json
import urllib.request
import urllib.parse
import datetime
from typing import Optional, Any

OFFICE_CODES = {
    "전체 (전국)": "",
    "서울특별시교육청": "B10",
    "부산광역시교육청": "C10",
    "대구광역시교육청": "D10",
    "인천광역시교육청": "E10",
    "광주광역시교육청": "F10",
    "대전광역시교육청": "G10",
    "울산광역시교육청": "H10",
    "세종특별자치시교육청": "I10",
    "경기도교육청": "J10",
    "강원특별자치도교육청": "K10",
    "충청북도교육청": "M10",
    "충청남도교육청": "N10",
    "전북특별자치도교육청": "P10",
    "전라남도교육청": "Q10",
    "경상북도교육청": "R10",
    "경상남도교육청": "S10",
    "제주특별자치도교육청": "T10",
}

from src.config_utils import get_config_dir

class NeisApiClient:
    """
    공식 교육부 NEIS Open API 전국 학교 & 시간표 종합 클라이언트
    - 전국 17개 시도 교육청 전역 학교 검색 (다중 페이지네이션 및 스마트 키워드 처리)
    - 초/중/고/특수학교 반별 실시간 시간표 조회 및 캐시 관리
    """
    BASE_URL = "https://open.neis.go.kr/hub"

    def __init__(self):
        self.config_file = os.path.join(get_config_dir(), "neis_config.json")
        self.cache_file = os.path.join(get_config_dir(), "neis_timetable_cache.json")
        self.config = {
            "api_key": "",
            "office_code": "",
            "office_name": "",
            "school_code": "",
            "school_name": "",
            "school_type": "초등학교",
            "grade": "5",
            "class_nm": "1",
            "ay": str(datetime.date.today().year),
            "sem": "1" if datetime.date.today().month < 8 else "2"
        }
        self.cache = {}
        self.load_config()
        self.load_cache()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.config.update(json.load(f))
            except Exception as e:
                print(f"Error loading neis config: {e}")

    def save_config(self, new_cfg: dict) -> bool:
        self.config.update(new_cfg)
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving neis config: {e}")
            return False

    def load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception as e:
                print(f"Error loading neis cache: {e}")

    def save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving neis cache: {e}")

    def _fetch_json(self, endpoint: str, params: dict) -> dict:
        api_key = self.config.get("api_key", "").strip()
        if api_key:
            params["KEY"] = api_key
        params["Type"] = "json"
        if "pIndex" not in params:
            params["pIndex"] = "1"
        if "pSize" not in params:
            params["pSize"] = "100"

        query_str = urllib.parse.urlencode(params)
        url = f"{self.BASE_URL}/{endpoint}?{query_str}"

        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TeacherUtility/2.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = response.read().decode("utf-8")
            return json.loads(data)

    def search_school(self, school_name: str, office_code: Optional[str] = None, school_type_filter: Optional[str] = None) -> list[dict[str, str]]:
        """
        전국 17개 시도 교육청의 모든 학교를 완벽하게 검색 (다중 페이지 자동 순회)
        """
        raw_query = school_name.strip()
        if not raw_query:
            return []

        # 공백 제거 및 원본 쿼리 준비
        clean_query = raw_query.replace(" ", "")

        all_results: list[dict[str, str]] = []
        seen_keys = set()

        # 최대 15페이지(샘플키 기준 최대 75~1500건) 자동 병합
        for page in range(1, 16):
            params = {
                "pIndex": str(page),
                "pSize": "100",
                "SCHUL_NM": clean_query
            }
            if office_code and office_code.strip():
                params["ATPT_OFCDC_SC_CODE"] = office_code.strip()

            try:
                res = self._fetch_json("schoolInfo", params)
                if "schoolInfo" not in res:
                    break

                head_info = res["schoolInfo"][0].get("head", [])
                total_count = 0
                if head_info and len(head_info) > 0 and "list_total_count" in head_info[0]:
                    total_count = int(head_info[0]["list_total_count"])

                row_data = res["schoolInfo"][1].get("row", [])
                if not row_data:
                    break

                for item in row_data:
                    s_code = item.get("SD_SCHUL_CODE", "")
                    o_code = item.get("ATPT_OFCDC_SC_CODE", "")
                    s_type = item.get("SCHUL_KND_SC_NM", "")
                    unique_k = f"{o_code}_{s_code}"

                    if unique_k in seen_keys:
                        continue

                    # 학교급 필터 (초/중/고/특수)
                    if school_type_filter and school_type_filter != "전체" and school_type_filter != "":
                        if school_type_filter not in s_type:
                            continue

                    seen_keys.add(unique_k)
                    all_results.append({
                        "office_code": o_code,
                        "office_name": item.get("ATPT_OFCDC_SC_NM", ""),
                        "school_code": s_code,
                        "school_name": item.get("SCHUL_NM", ""),
                        "school_type": s_type,
                        "address": item.get("ORG_RDNMA", item.get("JU_ADRES", ""))
                    })

                if total_count > 0 and len(seen_keys) >= total_count:
                    break
            except Exception as e:
                print(f"Error fetching page {page} of schoolInfo: {e}")
                break

        return all_results

    def get_timetable_for_date(self, target_date: datetime.date) -> tuple[bool, list[dict[str, Any]], str]:
        """
        특정 날짜의 시간표 조회 (초/중/고/특수학교 자동 판별 및 캐싱)
        """
        office_code = self.config.get("office_code", "")
        school_code = self.config.get("school_code", "")
        school_type = self.config.get("school_type", "초등학교")
        grade = str(self.config.get("grade", "1")).strip()
        class_nm = str(self.config.get("class_nm", "1")).strip()
        ay = str(self.config.get("ay", str(target_date.year))).strip()
        sem = str(self.config.get("sem", "1")).strip()

        if not office_code or not school_code:
            return False, [], "학교 설정이 필요합니다. [나이스 설정]에서 학교를 검색하여 저장해주세요."

        # 학교급별 엔드포인트 자동 선택
        if "중학교" in school_type:
            endpoint = "misTimetable"
        elif "고등학교" in school_type:
            endpoint = "hisTimetable"
        elif "특수" in school_type:
            endpoint = "spsTimetable"
        else:
            endpoint = "elsTimetable"

        ymd = target_date.strftime("%Y%m%d")
        cache_key = f"{school_code}_{grade}_{class_nm}_{ymd}"

        params = {
            "ATPT_OFCDC_SC_CODE": office_code,
            "SD_SCHUL_CODE": school_code,
            "AY": ay,
            "SEM": sem,
            "ALL_TI_YMD": ymd,
            "GRADE": grade,
            "CLASS_NM": class_nm
        }

        try:
            res = self._fetch_json(endpoint, params)
            if endpoint not in res:
                head = res.get("RESULT", {}).get("MESSAGE", "해당 날짜에 등록된 나이스 시간표가 없습니다.")
                return False, [], head

            row_data = res[endpoint][1]["row"]
            row_data.sort(key=lambda x: int(x.get("PERIO", 0)))

            timetable = []
            for item in row_data:
                perio = item.get("PERIO", "")
                subject = item.get("ITRT_CNTNT", "").strip()
                timetable.append({
                    "period": perio,
                    "subject": subject
                })

            # 캐시 저장
            self.cache[cache_key] = {
                "saved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data": timetable
            }
            self.save_cache()

            return True, timetable, "나이스 시간표 조회 성공"
        except Exception as e:
            if cache_key in self.cache:
                cached_obj = self.cache[cache_key]
                return True, cached_obj.get("data", []), f"네트워크 오류로 마지막 저장된 캐시를 표시합니다. (조회시각: {cached_obj.get('saved_at', '')})"
            return False, [], f"시간표 조회 실패: {str(e)}"

    def get_meal_for_date(self, target_date: datetime.date) -> tuple[bool, dict[str, Any], str]:
        """
        특정 날짜의 급식(중식) 식단표 및 영양/칼로리 정보 조회 (캐싱 지원)
        반환: (성공여부, 급식딕셔너리, 상태메시지)
        """
        office_code = self.config.get("office_code", "")
        school_code = self.config.get("school_code", "")

        if not office_code or not school_code:
            return False, {}, "학교 설정이 필요합니다. [학교 검색]에서 학교를 먼저 설정해주세요."

        ymd = target_date.strftime("%Y%m%d")
        cache_key = f"meal_{school_code}_{ymd}"

        params = {
            "ATPT_OFCDC_SC_CODE": office_code,
            "SD_SCHUL_CODE": school_code,
            "MLSV_YMD": ymd,
            "MMEAL_SC_CODE": "2" # 2: 중식
        }

        try:
            res = self._fetch_json("mealServiceDietInfo", params)
            if "mealServiceDietInfo" not in res:
                head = res.get("RESULT", {}).get("MESSAGE", "오늘 등록된 급식 식단표가 없습니다. (방학 또는 공휴일)")
                return False, {}, head

            row_data = res["mealServiceDietInfo"][1]["row"][0]
            raw_dishes = row_data.get("DDISH_NM", "")
            calorie = row_data.get("CAL_INFO", "")
            origin_info = row_data.get("ORPLC_INFO", "")

            # <br/> 태그 분리 및 정리
            dish_lines = [d.strip() for d in raw_dishes.replace("<br/>", "\n").replace("<br>", "\n").split("\n") if d.strip()]

            meal_info = {
                "date_str": target_date.strftime("%Y-%m-%d"),
                "dishes": dish_lines,
                "calorie": calorie,
                "origin": origin_info,
                "menu_text": " • " + "\n • ".join(dish_lines) if dish_lines else "급식 메뉴 없음"
            }

            # 캐시 저장
            self.cache[cache_key] = {
                "saved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data": meal_info
            }
            self.save_cache()

            return True, meal_info, "급식 정보 조회 성공"
        except Exception as e:
            if cache_key in self.cache:
                cached_obj = self.cache[cache_key]
                return True, cached_obj.get("data", {}), f"네트워크 오류로 저장된 최근 급식을 표시합니다."
            return False, {}, f"급식 조회 실패: {str(e)}"

    def get_weekly_meals(self, monday_date: datetime.date) -> dict[str, dict[str, Any]]:
        """월~금 주간 급식 일괄 조회"""
        weekly_meals = {}
        day_keys = ["mon", "tue", "wed", "thu", "fri"]

        for idx, d_key in enumerate(day_keys):
            cur_date = monday_date + datetime.timedelta(days=idx)
            ok, meal, _ = self.get_meal_for_date(cur_date)
            weekly_meals[d_key] = meal if ok else {}

        return weekly_meals

neis_client = NeisApiClient()
