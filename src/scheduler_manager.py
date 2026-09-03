import os
import sys
import time
import ctypes
import datetime
import threading
import subprocess
import json
from typing import Callable, Optional
from src.holidays_kr import get_korean_holiday
from src.config_utils import get_config_dir

class SchedulerManager:
    """
    종합 스케줄러 관리자:
    - 1회성 종료/재부팅/절전/알람 예약
    - 월~금 주간 반복 자동 꺼짐 (공휴일 자동 제외)
    - 월~금 주간 자동 켜짐(절전 깨우기) 설정 지원
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._timer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        self.is_scheduled: bool = False
        self.action_type: Optional[str] = None
        self.target_time: Optional[datetime.datetime] = None
        self.total_seconds: int = 0
        self.remaining_seconds: int = 0
        self.memo: str = ""
        self.sound_id: str = "chime"

        # 주간 자동 전원 스케줄 설정 파일
        self.auto_schedule_file = os.path.join(get_config_dir(), "auto_power_schedule.json")
        self.auto_power_config = {
            "auto_shutdown_enabled": False,
            "auto_shutdown_time": "16:40",  # 퇴근 시간
            "skip_holidays": True,
            "auto_wake_enabled": False,
            "auto_wake_time": "08:30"
        }
        self.load_auto_power_config()

        # 백그라운드 주간 스케줄 워커
        self._auto_worker_thread = threading.Thread(target=self._auto_power_loop, daemon=True)
        self._auto_worker_thread.start()

        # 콜백
        self.on_tick: Optional[Callable[[int, str], None]] = None
        self.on_state_change: Optional[Callable[[bool, Optional[str], str], None]] = None
        self.on_alarm_triggered: Optional[Callable[[str, str], None]] = None

    def load_auto_power_config(self):
        if os.path.exists(self.auto_schedule_file):
            try:
                with open(self.auto_schedule_file, "r", encoding="utf-8") as f:
                    self.auto_power_config.update(json.load(f))
            except Exception as e:
                print(f"Error loading auto power config: {e}")

    def save_auto_power_config(self, cfg: dict) -> bool:
        self.auto_power_config.update(cfg)
        try:
            with open(self.auto_schedule_file, "w", encoding="utf-8") as f:
                json.dump(self.auto_power_config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving auto power config: {e}")
            return False

    def cancel_schedule(self, notify: bool = True) -> tuple[bool, str]:
        with self._lock:
            self._stop_event.set()
            self._run_windows_cancel()
            
            was_scheduled = self.is_scheduled
            self.is_scheduled = False
            self.action_type = None
            self.target_time = None
            self.remaining_seconds = 0
            self.total_seconds = 0
            self.memo = ""

            msg = "예약이 취소되었습니다." if was_scheduled else "진행 중인 예약이 없습니다."
            if notify and self.on_state_change:
                self.on_state_change(False, None, msg)
            return True, msg

    def schedule_action(self, action_type: str, seconds: int, memo: str = "", sound_id: str = "chime") -> tuple[bool, str]:
        if seconds <= 0:
            return False, "예약 시간은 1초 이상이어야 합니다."
        
        # 최대 2개월 (60일) 예약 제한 규칙
        MAX_SCHEDULE_SECONDS = 60 * 86400
        if seconds > MAX_SCHEDULE_SECONDS:
            return False, "⚠️ 컴퓨터 전원 및 알람 예약은 시스템 안정성을 위해 최대 2개월(60일)까지만 지원됩니다."

        self.cancel_schedule(notify=False)
        
        with self._lock:
            self._stop_event.clear()
            self.action_type = action_type
            self.total_seconds = seconds
            self.remaining_seconds = seconds
            self.memo = memo.strip()
            self.sound_id = sound_id
            now = datetime.datetime.now()
            self.target_time = now + datetime.timedelta(seconds=seconds)
            self.is_scheduled = True
            
            if action_type in ('shutdown', 'restart'):
                sec_param = min(seconds, 315360000)
                flag = '/s' if action_type == 'shutdown' else '/r'
                try:
                    subprocess.run(
                        ['shutdown', flag, '/t', str(sec_param), '/c', f'컴퓨터예약 앱에 의해 {self.target_time.strftime("%H:%M:%S")}에 실행됩니다.'],
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                except Exception:
                    pass

            self._timer_thread = threading.Thread(target=self._countdown_loop, daemon=True)
            self._timer_thread.start()

            action_name = self._get_action_name(action_type)
            msg = f"{self.target_time.strftime('%Y-%m-%d %H:%M:%S')}에 [{action_name}] 예약이 완료되었습니다."
            
            if self.on_state_change:
                self.on_state_change(True, action_type, msg)
                
            return True, msg

    def snooze_alarm(self, minutes: int = 5):
        return self.schedule_action(
            action_type="alarm",
            seconds=minutes * 60,
            memo=self.memo,
            sound_id=self.sound_id
        )

    def execute_immediate(self, action_type: str) -> tuple[bool, str]:
        self.cancel_schedule(notify=False)
        action_name = self._get_action_name(action_type)
        try:
            if action_type == 'shutdown':
                subprocess.run(['shutdown', '/s', '/f', '/t', '0'], 
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                               check=False)
            elif action_type == 'restart':
                subprocess.run(['shutdown', '/r', '/f', '/t', '0'], 
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                               check=False)
            elif action_type == 'sleep':
                self._trigger_sleep()
            else:
                return False, "알 수 없는 동작입니다."
            return True, f"컴퓨터 {action_name}을(를) 즉시 실행합니다."
        except Exception as e:
            return False, f"{action_name} 실행 실패: {str(e)}"

    def _countdown_loop(self):
        while not self._stop_event.is_set():
            if self.remaining_seconds <= 0:
                self._execute_due_action()
                break
            
            if self.on_tick:
                target_str = self.target_time.strftime('%Y-%m-%d %H:%M:%S') if self.target_time else ""
                self.on_tick(self.remaining_seconds, target_str)
            
            if self._stop_event.wait(timeout=1.0):
                break
            
            self.remaining_seconds -= 1

    def _execute_due_action(self):
        with self._lock:
            act = self.action_type
            memo_to_show = self.memo
            sound_to_play = self.sound_id
            self.is_scheduled = False
            
        if self.on_state_change:
            self.on_state_change(False, None, "예약 시간이 도달했습니다.")

        if act == 'alarm':
            if self.on_alarm_triggered:
                self.on_alarm_triggered(memo_to_show, sound_to_play)
        elif act == 'sleep':
            self._trigger_sleep()
        elif act in ('shutdown', 'restart'):
            flag = '/s' if act == 'shutdown' else '/r'
            try:
                subprocess.run(['shutdown', flag, '/f', '/t', '0'],
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                               check=False)
            except Exception:
                pass

    def _auto_power_loop(self):
        """월~금 퇴근 자동 종료 감시 루프 (공휴일 자동 제외)"""
        last_triggered_date = None

        while True:
            time.sleep(30)
            if not self.auto_power_config.get("auto_shutdown_enabled", False):
                continue

            now = datetime.datetime.now()
            today_date = now.date()

            # 주말(토, 일) 제외 (0:월, 4:금, 5:토, 6:일)
            if now.weekday() >= 5:
                continue

            # 공휴일 제외 옵션
            if self.auto_power_config.get("skip_holidays", True):
                is_hol, _ = get_korean_holiday(today_date)
                if is_hol:
                    continue

            # 지정 시각 도달 체크
            t_str = self.auto_power_config.get("auto_shutdown_time", "16:40")
            try:
                target_h, target_m = map(int, t_str.split(":"))
                if now.hour == target_h and now.minute == target_m and last_triggered_date != today_date:
                    last_triggered_date = today_date
                    # 자동 종료 트리거
                    print(f"Auto shutdown triggered at {now.strftime('%H:%M')}")
                    self.execute_immediate("shutdown")
            except Exception as e:
                print(f"Auto power loop error: {e}")

    def _trigger_sleep(self):
        try:
            ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
        except Exception:
            subprocess.run(
                ['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0'],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                check=False
            )

    def _run_windows_cancel(self):
        try:
            subprocess.run(
                ['shutdown', '/a'],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                capture_output=True,
                text=True,
                check=False
            )
        except Exception:
            pass

    @staticmethod
    def _get_action_name(action_type: str) -> str:
        names = {
            'shutdown': '컴퓨터 종료',
            'restart': '다시 시작',
            'sleep': '절전 모드',
            'alarm': '알람 / 리마인더'
        }
        return names.get(action_type, '동작')

    def get_active_schedules(self) -> list[dict]:
        """현재 가동 중인 1회성 예약 및 주간 반복 자동 전원 일정을 일목요연하게 반환"""
        items = []
        with self._lock:
            if self.is_scheduled and self.target_time:
                action_kr = self._get_action_name(self.action_type)
                items.append({
                    "id": "active_timer",
                    "type_name": action_kr,
                    "action_type": self.action_type,
                    "target_time_str": self.target_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "repeat_type": "오늘 1회성",
                    "remaining_sec": self.remaining_seconds,
                    "memo": self.memo or f"컴퓨터 {action_kr} 예약",
                    "can_cancel": True
                })

        # 주간 퇴근 자동 종료 설정
        if self.auto_power_config.get("auto_shutdown_enabled"):
            t_str = self.auto_power_config.get("auto_shutdown_time", "16:40")
            items.append({
                "id": "weekly_shutdown",
                "type_name": "컴퓨터 자동 종료",
                "action_type": "auto_shutdown",
                "target_time_str": f"매주 월~금 {t_str}",
                "repeat_type": "매주 월~금 반복 (공휴일 제외)",
                "remaining_sec": -1,
                "memo": "퇴근 시간 자동 컴퓨터 끄기",
                "can_cancel": True
            })

        # 주간 자동 켜짐 설정
        if self.auto_power_config.get("auto_wake_enabled"):
            t_str = self.auto_power_config.get("auto_wake_time", "08:30")
            items.append({
                "id": "weekly_wake",
                "type_name": "컴퓨터 절전 깨우기",
                "action_type": "auto_wake",
                "target_time_str": f"매주 월~금 {t_str}",
                "repeat_type": "매주 월~금 반복 (공휴일 제외)",
                "remaining_sec": -1,
                "memo": "출근 시간 자동 켜짐",
                "can_cancel": True
            })

        return items

    def cancel_item_by_id(self, item_id: str) -> tuple[bool, str]:
        """항목 ID별 개별 예약 취소"""
        if item_id == "active_timer":
            return self.cancel_schedule(notify=True)
        elif item_id == "weekly_shutdown":
            self.auto_power_config["auto_shutdown_enabled"] = False
            self.save_auto_power_config({"auto_shutdown_enabled": False})
            return True, "주간 퇴근 자동 종료 예약이 취소되었습니다."
        elif item_id == "weekly_wake":
            self.auto_power_config["auto_wake_enabled"] = False
            self.save_auto_power_config({"auto_wake_enabled": False})
            return True, "주간 출근 자동 켜짐 예약이 취소되었습니다."
        return False, "취소할 항목을 찾을 수 없습니다."
