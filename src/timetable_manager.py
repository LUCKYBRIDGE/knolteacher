import os
import sys
import json
import datetime
from typing import Optional, Any
from src.holidays_kr import get_korean_holiday
from src.config_utils import get_config_dir

DAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]
DAY_KEYS = ["mon", "tue", "wed", "thu", "fri"]

class TimetableManager:
    """
    선생님 맞춤형 시간표 및 일과표 종합 관리자
    - 표준 일과표 (9:10 시작, 4교시 후 점심 12:20~13:20, 6교시 14:50 종료)
    - 점심시간 위치 자유 이동 (3/4/5교시 후)
    - 일괄 시차 조정 (N분 당기기 / 미루기)
    - 주간 시간표 (목 5교시, 7교시 확장, 전담/외강 태그)
    - 대한민국 공휴일 자동 인식
    """
    def __init__(self):
        self.timetable_file = os.path.join(get_config_dir(), "custom_timetable.json")
        self.periods_file = os.path.join(get_config_dir(), "schedule_periods.json")
        self.settings_file = os.path.join(get_config_dir(), "timetable_settings.json")

        self.max_periods: int = 6  # 기본 6교시 (7교시 추가 지원)
        self.weekly_timetable = self._get_default_weekly_timetable()
        self.periods = self._get_default_periods()
        self._listeners: list[Any] = []
        self.settings = {
            "alarm_lead_minutes": 5,
            "alarm_sound_id": "chime",
            "theme_mode": "Beige",
            "window_alpha": 1.0,
            "lunch_after_period": 4,  # 점심시간 위치 (4교시 후)
            "enable_period_7": False,
            "google_sheet_url": ""
        }

        self.load_all()

    def add_listener(self, callback):
        """시간표/일과 변경 시 실시간 통보받을 리스너 등록"""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback):
        """리스너 해제"""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def notify_listeners(self):
        """등록된 모든 UI(놀티쳐 보드, 위젯, 메인 창)에 실시간 변경 알림"""
        dead = []
        for cb in self._listeners:
            try:
                cb()
            except Exception:
                dead.append(cb)
        for d in dead:
            if d in self._listeners:
                self._listeners.remove(d)

    def _get_default_periods(self) -> list[dict[str, Any]]:
        """사용자 요청 표준 일과표 기본값 (9:10 시작, 점심 12:20~13:20)"""
        return [
            {"name": "1교시", "start": "09:10", "end": "09:50", "is_lunch": False},
            {"name": "2교시", "start": "10:00", "end": "10:40", "is_lunch": False},
            {"name": "3교시", "start": "10:50", "end": "11:30", "is_lunch": False},
            {"name": "4교시", "start": "11:40", "end": "12:20", "is_lunch": False},
            {"name": "점심시간", "start": "12:20", "end": "13:20", "is_lunch": True},
            {"name": "5교시", "start": "13:20", "end": "14:00", "is_lunch": False},
            {"name": "6교시", "start": "14:10", "end": "14:50", "is_lunch": False},
            {"name": "7교시", "start": "15:00", "end": "15:40", "is_lunch": False}
        ]

    def _get_default_weekly_timetable(self) -> dict[str, list[dict[str, str]]]:
        """기본 주간 시간표 (수요일만 5교시, 전담/외강 태그 포함)"""
        return {
            "mon": [
                {"subject": "국어", "tag": "담임"}, {"subject": "수학", "tag": "담임"},
                {"subject": "사회", "tag": "담임"}, {"subject": "과학", "tag": "전담"},
                {"subject": "음악", "tag": "전담"}, {"subject": "체육", "tag": "외강"},
                {"subject": "", "tag": "담임"}
            ],
            "tue": [
                {"subject": "수학", "tag": "담임"}, {"subject": "국어", "tag": "담임"},
                {"subject": "체육", "tag": "외강"}, {"subject": "도덕", "tag": "담임"},
                {"subject": "영어", "tag": "전담"}, {"subject": "미술", "tag": "전담"},
                {"subject": "", "tag": "담임"}
            ],
            "wed": [
                {"subject": "국어", "tag": "담임"}, {"subject": "사회", "tag": "담임"},
                {"subject": "수학", "tag": "담임"}, {"subject": "과학", "tag": "전담"},
                {"subject": "창체", "tag": "담임"}, {"subject": "", "tag": "담임"},  # 수 6교시 빈칸 (5교시 기본)
                {"subject": "", "tag": "담임"}
            ],
            "thu": [
                {"subject": "영어", "tag": "전담"}, {"subject": "수학", "tag": "담임"},
                {"subject": "국어", "tag": "담임"}, {"subject": "음악", "tag": "전담"},
                {"subject": "실과", "tag": "담임"}, {"subject": "체육", "tag": "외강"},
                {"subject": "", "tag": "담임"}
            ],
            "fri": [
                {"subject": "사회", "tag": "담임"}, {"subject": "국어", "tag": "담임"},
                {"subject": "수학", "tag": "담임"}, {"subject": "미술", "tag": "전담"},
                {"subject": "창체", "tag": "담임"}, {"subject": "동아리", "tag": "외강"},
                {"subject": "", "tag": "담임"}
            ]
        }

    def load_all(self):
        if os.path.exists(self.timetable_file):
            try:
                with open(self.timetable_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 하위 호환성 (str 리스트 -> dict 리스트)
                    for k, v in data.items():
                        new_list = []
                        for item in v:
                            if isinstance(item, str):
                                new_list.append({"subject": item, "tag": "담임"})
                            elif isinstance(item, dict):
                                new_list.append(item)
                        data[k] = new_list
                    self.weekly_timetable.update(data)
            except Exception as e:
                print(f"Error loading custom timetable: {e}")

        if os.path.exists(self.periods_file):
            try:
                with open(self.periods_file, "r", encoding="utf-8") as f:
                    self.periods = json.load(f)
            except Exception as e:
                print(f"Error loading periods: {e}")

        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    self.settings.update(json.load(f))
                    self.max_periods = 7 if self.settings.get("enable_period_7", False) else 6
            except Exception as e:
                print(f"Error loading timetable settings: {e}")

    def save_weekly_timetable(self, data: dict[str, list[dict[str, str]]]) -> bool:
        self.weekly_timetable = data
        try:
            with open(self.timetable_file, "w", encoding="utf-8") as f:
                json.dump(self.weekly_timetable, f, ensure_ascii=False, indent=2)
            self.notify_listeners()
            return True
        except Exception as e:
            print(f"Error saving weekly timetable: {e}")
            return False

    def save_periods(self, periods: list[dict[str, Any]]) -> bool:
        self.periods = periods
        try:
            with open(self.periods_file, "w", encoding="utf-8") as f:
                json.dump(self.periods, f, ensure_ascii=False, indent=2)
            self.notify_listeners()
            return True
        except Exception as e:
            print(f"Error saving periods: {e}")
            return False

    def save_settings(self, settings: Optional[dict[str, Any]] = None) -> bool:
        if settings:
            self.settings.update(settings)
        if "enable_period_7" in self.settings:
            self.max_periods = 7 if self.settings["enable_period_7"] else 6
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            self.notify_listeners()
            return True
        except Exception as e:
            print(f"Error saving timetable settings: {e}")
            return False

    def update_period_subject(self, day_key: str, lesson_idx: int, new_subject: str, new_tag: str = "담임") -> bool:
        """특정 요일의 교시 과목 즉시 변경 및 전체 연동"""
        if day_key not in self.weekly_timetable:
            self.weekly_timetable[day_key] = [{"subject": "", "tag": "담임"} for _ in range(7)]
        
        while len(self.weekly_timetable[day_key]) <= lesson_idx:
            self.weekly_timetable[day_key].append({"subject": "", "tag": "담임"})

        self.weekly_timetable[day_key][lesson_idx] = {
            "subject": new_subject.strip(),
            "tag": new_tag
        }
        return self.save_weekly_timetable(self.weekly_timetable)

    def update_today_period(self, lesson_idx: int, new_subject: str, new_tag: str = "담임") -> bool:
        """오늘 요일의 교시 과목 즉시 변경 및 전체 연동"""
        d = datetime.date.today()
        w = d.weekday()
        if 0 <= w < len(DAY_KEYS):
            day_key = DAY_KEYS[w]
            return self.update_period_subject(day_key, lesson_idx, new_subject, new_tag)
        return False

    def reset_to_defaults(self):
        """기본값으로 전면 초기화"""
        self.weekly_timetable = self._get_default_weekly_timetable()
        self.periods = self._get_default_periods()
        self.settings["enable_period_7"] = False
        self.settings["lunch_after_period"] = 4
        self.max_periods = 6
        self.save_weekly_timetable(self.weekly_timetable)
        self.save_periods(self.periods)
        self.save_settings(self.settings)

    def shift_all_periods(self, minutes_delta: int) -> list[dict[str, Any]]:
        """모든 교시 및 점심시간을 일괄 N분 당기기(-) 또는 미루기(+)"""
        def shift_time_str(t_str: str, delta: int) -> str:
            try:
                h, m = map(int, t_str.split(":"))
                dt = datetime.datetime(2026, 1, 1, h, m) + datetime.timedelta(minutes=delta)
                return dt.strftime("%H:%M")
            except Exception:
                return t_str

        for p in self.periods:
            p["start"] = shift_time_str(p.get("start", ""), minutes_delta)
            p["end"] = shift_time_str(p.get("end", ""), minutes_delta)

        self.save_periods(self.periods)
        return self.periods

    def move_lunch_after(self, target_period_num: int) -> list[dict[str, Any]]:
        """
        점심시간의 위치를 N교시 후로 이동 (예: 3교시 후, 4교시 후, 5교시 후)
        """
        lunch_item = None
        other_periods = []

        for p in self.periods:
            if p.get("is_lunch", False):
                lunch_item = p
            else:
                other_periods.append(p)

        if not lunch_item:
            lunch_item = {"name": "점심시간", "start": "12:20", "end": "13:20", "is_lunch": True}

        # 새 순서 조립
        new_periods = []
        target_period_num = max(1, min(target_period_num, len(other_periods)))

        for idx, p in enumerate(other_periods, 1):
            new_periods.append(p)
            if idx == target_period_num:
                new_periods.append(lunch_item)

        self.periods = new_periods
        self.settings["lunch_after_period"] = target_period_num
        self.save_periods(self.periods)
        self.save_settings(self.settings)
        return self.periods

    def get_today_schedule_items(self, target_date: Optional[datetime.date] = None) -> tuple[bool, str, list[dict[str, Any]]]:
        """
        오늘의 일과표와 시간표 과목을 매핑하여 반환
        반환: (공휴일여부, 공휴일명, [항목리스트])
        """
        d = target_date or datetime.date.today()
        is_holiday, holiday_name = get_korean_holiday(d)

        weekday_idx = d.weekday() # 0: 월, 4: 금
        day_key = DAY_KEYS[weekday_idx] if 0 <= weekday_idx < len(DAY_KEYS) else ""
        subjects_data = self.weekly_timetable.get(day_key, [])

        items = []
        lesson_counter = 0

        for p in self.periods:
            is_lunch = p.get("is_lunch", False)
            name = p.get("name", "")
            start_str = p.get("start", "")
            end_str = p.get("end", "")

            # 7교시 활성화 여부 체크
            if "7교시" in name and not self.settings.get("enable_period_7", False):
                continue

            if is_lunch:
                subj = "🍱 점심식사 및 휴식"
                tag = "점심"
            else:
                if lesson_counter < len(subjects_data):
                    subj_obj = subjects_data[lesson_counter]
                    subj = subj_obj.get("subject", "") if isinstance(subj_obj, dict) else str(subj_obj)
                    tag = subj_obj.get("tag", "담임") if isinstance(subj_obj, dict) else "담임"
                else:
                    subj = ""
                    tag = "담임"

                lesson_counter += 1
                if not subj.strip():
                    subj = "자율/수업" if not is_holiday else "수업 없음"

            items.append({
                "name": name,
                "start": start_str,
                "end": end_str,
                "subject": subj,
                "tag": tag,
                "is_lunch": is_lunch,
                "is_holiday": is_holiday
            })

        return is_holiday, holiday_name or "", items

    def get_next_alarm_time(self, item: dict[str, Any], lead_minutes: int, target_date: Optional[datetime.date] = None) -> Optional[datetime.datetime]:
        d = target_date or datetime.date.today()
        start_str = item.get("start", "")
        if not start_str or ":" not in start_str:
            return None

        try:
            h, m = map(int, start_str.split(":"))
            start_dt = datetime.datetime(d.year, d.month, d.day, h, m, 0)
            alarm_dt = start_dt - datetime.timedelta(minutes=lead_minutes)
            return alarm_dt
        except Exception:
            return None

timetable_manager = TimetableManager()
