import datetime
from typing import Optional

# 2025~2030년 대한민국 주요 음력 명절 및 공휴일 데이터
LUNAR_HOLIDAYS = {
    # 2025
    2025: {
        (1, 28): "설날 전날", (1, 29): "설날", (1, 30): "설날 다음날",
        (5, 5): "어린이날/부처님오신날", (5, 6): "대체공휴일",
        (10, 5): "추석 전날", (10, 6): "추석", (10, 7): "추석 다음날", (10, 8): "대체공휴일"
    },
    # 2026
    2026: {
        (2, 16): "설날 전날", (2, 17): "설날", (2, 18): "설날 다음날",
        (5, 24): "부처님오신날", (5, 25): "대체공휴일",
        (9, 24): "추석 전날", (9, 25): "추석", (9, 26): "추석 다음날"
    },
    # 2027
    2027: {
        (2, 5): "설날 전날", (2, 6): "설날", (2, 7): "설날 다음날", (2, 8): "대체공휴일",
        (5, 13): "부처님오신날",
        (9, 14): "추석 전날", (9, 15): "추석", (9, 16): "추석 다음날"
    },
    # 2028
    2028: {
        (1, 26): "설날 전날", (1, 27): "설날", (1, 28): "설날 다음날",
        (5, 2): "부처님오신날",
        (10, 2): "추석 전날", (10, 3): "개천절/추석", (10, 4): "추석 다음날", (10, 5): "대체공휴일"
    },
    # 2029
    2029: {
        (2, 12): "설날 전날", (2, 13): "설날", (2, 14): "설날 다음날",
        (5, 20): "부처님오신날", (5, 21): "대체공휴일",
        (9, 21): "추석 전날", (9, 22): "추석", (9, 23): "추석 다음날", (9, 24): "대체공휴일"
    },
    # 2030
    2030: {
        (2, 2): "설날 전날", (2, 3): "설날", (2, 4): "설날 다음날", (2, 5): "대체공휴일",
        (5, 9): "부처님오신날",
        (9, 11): "추석 전날", (9, 12): "추석", (9, 13): "추석 다음날"
    }
}

# 고정 양력 공휴일
FIXED_SOLAR_HOLIDAYS = {
    (1, 1): "신정",
    (3, 1): "삼일절",
    (5, 5): "어린이날",
    (6, 6): "현충일",
    (8, 15): "광복절",
    (10, 3): "개천절",
    (10, 9): "한글날",
    (12, 25): "성탄절"
}

def get_korean_holiday(d: datetime.date) -> tuple[bool, Optional[str]]:
    """
    해당 날짜가 대한민국 법정 공휴일/대체공휴일인지 판정
    반환: (공휴일여부, 공휴일명)
    """
    year = d.year
    month = d.month
    day = d.day

    # 1. 고정 양력 공휴일 체크
    if (month, day) in FIXED_SOLAR_HOLIDAYS:
        return True, FIXED_SOLAR_HOLIDAYS[(month, day)]

    # 2. 음력 명절 및 내장 공휴일 체크
    year_lunar = LUNAR_HOLIDAYS.get(year, {})
    if (month, day) in year_lunar:
        return True, year_lunar[(month, day)]

    # 3. 대체공휴일 자동 판정 (삼일절, 광복절, 개천절, 한글날, 어린이날, 성탄절이 주말인 경우 월요일)
    # 토요일인 경우 월요일(+2일), 일요일인 경우 월요일(+1일)
    substitute_targets = [(3, 1, "삼일절"), (5, 5, "어린이날"), (8, 15, "광복절"), (10, 3, "개천절"), (10, 9, "한글날"), (12, 25, "성탄절")]
    for t_m, t_d, t_name in substitute_targets:
        try:
            target_date = datetime.date(year, t_m, t_d)
            if target_date.weekday() == 5:  # 토요일 -> 월요일(+2)
                sub_date = target_date + datetime.timedelta(days=2)
                if d == sub_date:
                    return True, f"{t_name} 대체공휴일"
            elif target_date.weekday() == 6:  # 일요일 -> 월요일(+1)
                sub_date = target_date + datetime.timedelta(days=1)
                if d == sub_date:
                    return True, f"{t_name} 대체공휴일"
        except Exception:
            pass

    return False, None
