"""
반복 알람 및 정기 스케줄 매니저 (RecurringScheduleManager)
- 매일 반복, 평일(월~금) 반복, 지정 요일 반복 스케줄 완벽 지원
- 알람(차임벨/사전 타이머) 및 PC 전원(종료/절전/재시작) 반복 자동화
- 공휴일 자동 건너뛰기 지원
- recurring_schedules.json 영구 저장
"""
import os
import sys
import json
import uuid
import datetime
import threading
import time
from typing import List, Dict, Any, Tuple

from src.config_utils import get_config_dir
from src.holidays_kr import get_korean_holiday
from src.sound_manager import sound_manager

DAYS_NAME = ["월", "화", "수", "목", "금", "토", "일"]

DEFAULT_RECURRING = [
    {
        "id": "rec_def_leave",
        "title": "퇴근 시간 자동 종료",
        "action_type": "shutdown",
        "time_str": "16:40",
        "ampm": "오후",
        "hour12": 4,
        "minute": 40,
        "repeat_mode": "weekdays",
        "repeat_days": [0, 1, 2, 3, 4],
        "skip_holidays": True,
        "enabled": False,
        "memo": "선생님 퇴근 시간(16:40) PC 자동 전원 차단"
    },
    {
        "id": "rec_def_clean",
        "title": "청소 및 하교 지도 알람",
        "action_type": "alarm",
        "time_str": "14:30",
        "ampm": "오후",
        "hour12": 2,
        "minute": 30,
        "repeat_mode": "weekdays",
        "repeat_days": [0, 1, 2, 3, 4],
        "skip_holidays": True,
        "enabled": False,
        "memo": "교실 청소 및 학생 하교 지도 알람"
    }
]


class RecurringScheduleManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.file_path = os.path.join(get_config_dir(), "recurring_schedules.json")
        self.schedules: List[Dict[str, Any]] = []
        self.app = None
        self._last_triggered_minute = ""
        self._lock = threading.Lock()

        self.load_schedules()

        # 백그라운드 반복 체크 루프 시작
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()

    def load_schedules(self):
        with self._lock:
            if os.path.exists(self.file_path):
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.schedules = data.get("schedules", [])
                        return
                except Exception as e:
                    print(f"[Recurring Schedule Load Error] {e}")
            self.schedules = [dict(d) for d in DEFAULT_RECURRING]

    def save_schedules(self):
        with self._lock:
            try:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump({"schedules": self.schedules}, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[Recurring Schedule Save Error] {e}")

    def add_schedule(self, item: Dict[str, Any]) -> str:
        if "id" not in item:
            item["id"] = f"rec_{uuid.uuid4().hex[:8]}"
        with self._lock:
            self.schedules.append(item)
        self.save_schedules()
        return item["id"]

    def update_schedule(self, item_id: str, updates: Dict[str, Any]):
        with self._lock:
            for itm in self.schedules:
                if itm["id"] == item_id:
                    itm.update(updates)
                    break
        self.save_schedules()

    def delete_schedule(self, item_id: str):
        with self._lock:
            self.schedules = [s for s in self.schedules if s["id"] != item_id]
        self.save_schedules()

    def toggle_enable(self, item_id: str) -> bool:
        new_state = False
        with self._lock:
            for itm in self.schedules:
                if itm["id"] == item_id:
                    itm["enabled"] = not itm.get("enabled", True)
                    new_state = itm["enabled"]
                    break
        self.save_schedules()
        return new_state

    def _check_loop(self):
        while True:
            try:
                now = datetime.datetime.now()
                cur_min_str = now.strftime("%Y-%m-%d %H:%M")
                if cur_min_str != self._last_triggered_minute:
                    self._last_triggered_minute = cur_min_str
                    self._check_triggers(now)
            except Exception as e:
                print(f"[Recurring Loop Error] {e}")
            time.sleep(10)

    def _check_triggers(self, now: datetime.datetime):
        cur_hm = now.strftime("%H:%M")
        cur_weekday = now.weekday()  # 0:월 ~ 6:일

        with self._lock:
            active_list = [dict(s) for s in self.schedules if s.get("enabled", True)]

        for item in active_list:
            t_str = item.get("time_str", "")
            if t_str != cur_hm:
                continue

            # 공휴일 검사
            if item.get("skip_holidays", True):
                is_hol, hol_name = get_korean_holiday(now.date())
                if is_hol:
                    continue

            # 요일 검사
            rep_mode = item.get("repeat_mode", "weekdays")
            rep_days = item.get("repeat_days", [0, 1, 2, 3, 4])
            if rep_mode == "weekdays" and cur_weekday >= 5:
                continue  # 토/일 제외
            elif rep_mode == "custom" and cur_weekday not in rep_days:
                continue

            # 트리거 발동!
            self._trigger_item(item)

    def _trigger_item(self, item: Dict[str, Any]):
        act = item.get("action_type", "alarm")
        title = item.get("title", "반복 알람")
        memo = item.get("memo", "")

        print(f"[Recurring Trigger] {title} ({act}) triggered at {datetime.datetime.now()}")

        if act == "alarm":
            sound_manager.play("chime")
            if self.app and hasattr(self.app, "after"):
                self.app.after(0, lambda: self._show_alarm_popup(title, memo))
        elif act in ("shutdown", "restart", "sleep"):
            if self.app and hasattr(self.app, "manager"):
                self.app.manager.schedule_action(act, 60, memo=f"[정기 반복] {title}: {memo}", force=True)

    def _show_alarm_popup(self, title: str, memo: str):
        from src.class_countdown_popup import ClassCountdownPopup
        ClassCountdownPopup.show(title, memo, 0, total_seconds=60, parent=self.app)

recurring_manager = RecurringScheduleManager.get_instance()
