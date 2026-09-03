import os
import sys
import time
import uuid
import ctypes
import datetime
import threading
import subprocess
import json
from typing import Callable, Optional, Dict, Any, Tuple
from src.holidays_kr import get_korean_holiday
from src.config_utils import get_config_dir

class SchedulerManager:
    """
    종합 다중 스케줄러 관리자:
    - 다중 예약(Multiple Schedules) 동시 등록 및 카운트다운
    - 양립할 수 없는 전원 예약 충돌 자동 감지
    - 최대 2개월(60일) 엄격 제한
    - 윈도우 절전 모드 해제 타이머(WakeToRun)를 통한 컴퓨터 자동 켜짐/부팅 지원
    - 월~금 주간 반복 자동 꺼짐/켜짐 (공휴일 자동 제외)
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        # 다중 스케줄 저장소 {id: schedule_dict}
        self.schedules: Dict[str, Dict[str, Any]] = {}

        # 하위 호환성을 위한 단일 대표 예약 상태 (가장 임박한 스케줄)
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
            "auto_shutdown_time": "16:40",
            "skip_holidays": True,
            "auto_wake_enabled": False,
            "auto_wake_time": "08:30"
        }
        self.load_auto_power_config()

        # 콜백 변수 선언 (스레드 시작 전 초기화 필수)
        self.on_tick: Optional[Callable[[int, str], None]] = None
        self.on_state_change: Optional[Callable[[bool, Optional[str], str], None]] = None
        self.on_alarm_triggered: Optional[Callable[[str, str], None]] = None

        # 주간 스케줄러 루프
        self._auto_worker_thread = threading.Thread(target=self._auto_power_loop, daemon=True)
        self._auto_worker_thread.start()

        # 다중 스케줄 감시 메인 카운트다운 루프
        self._main_timer_thread = threading.Thread(target=self._multi_countdown_loop, daemon=True)
        self._main_timer_thread.start()

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

    def check_conflict(self, action_type: str, target_time: datetime.datetime) -> Tuple[bool, Optional[dict]]:
        """
        양립할 수 없는 전원 제어 예약 충돌 검사
        - 전원 제어 동작(종료, 재시작, 절전, 자동 켜짐) 간에 5분 이내 시간대가 겹치는 경우 충돌로 판정
        """
        power_actions = {"shutdown", "restart", "sleep", "wake"}
        if action_type not in power_actions:
            return False, None

        with self._lock:
            for s_id, itm in self.schedules.items():
                if itm.get("action_type") in power_actions:
                    diff = abs((itm["target_time"] - target_time).total_seconds())
                    if diff < 300:  # 5분 이내 충돌
                        return True, itm
        return False, None

    def schedule_action(
        self,
        action_type: str,
        seconds: int = 0,
        target_datetime: Optional[datetime.datetime] = None,
        memo: str = "",
        sound_id: str = "chime",
        force: bool = False
    ) -> Tuple[bool, str]:
        """
        새로운 예약 등록 (상대 초 또는 절대 일시 지원, 다중 예약 완벽 지원)
        """
        now = datetime.datetime.now()
        if target_datetime:
            target_time = target_datetime
            seconds = int((target_time - now).total_seconds())
        else:
            if seconds <= 0:
                return False, "예약 시간은 1초 이상이어야 합니다."
            target_time = now + datetime.timedelta(seconds=seconds)

        if seconds <= 0:
            return False, "지정한 시각이 이미 지나갔습니다. 현재 시각 이후로 설정해주세요."

        # 최대 2개월 (60일) 예약 제한
        MAX_SCHEDULE_SECONDS = 60 * 86400
        if seconds > MAX_SCHEDULE_SECONDS:
            return False, "⚠️ 컴퓨터 전원 및 알람 예약은 시스템 안정성을 위해 최대 2개월(60일)까지만 지원됩니다."

        # 충돌 검사 (강제가 아닐 때)
        if not force:
            has_conflict, conflicted_item = self.check_conflict(action_type, target_time)
            if has_conflict and conflicted_item:
                c_name = self._get_action_name(conflicted_item.get("action_type", ""))
                c_time = conflicted_item["target_time"].strftime("%Y-%m-%d %H:%M:%S")
                return False, f"CONFLICT:{conflicted_item['id']}:{c_name}:{c_time}"

        sch_id = f"sch_{uuid.uuid4().hex[:8]}"
        action_name = self._get_action_name(action_type)

        # 윈도우 컴퓨터 켜기(절전 깨우기)인 경우 작업 스케줄러 등록
        if action_type == "wake":
            ok, wake_msg = self._register_windows_wake_task(target_time)
            if not ok:
                return False, f"절전 깨우기 등록 실패: {wake_msg}"

        # 윈도우 전원 예약인 경우
        if action_type in ("shutdown", "restart"):
            sec_param = min(seconds, 315360000)
            flag = "/s" if action_type == "shutdown" else "/r"
            try:
                subprocess.run(
                    ["shutdown", flag, "/t", str(sec_param), "/c", f"놀티쳐 예약에 의해 {target_time.strftime('%H:%M:%S')}에 실행됩니다."],
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    capture_output=True,
                    text=True,
                    check=False
                )
            except Exception:
                pass

        with self._lock:
            self.schedules[sch_id] = {
                "id": sch_id,
                "action_type": action_type,
                "target_time": target_time,
                "total_seconds": seconds,
                "remaining_seconds": seconds,
                "memo": memo.strip() or f"컴퓨터 {action_name} 예약",
                "sound_id": sound_id,
                "repeat_type": "오늘 1회성",
                "created_at": now
            }
            self._sync_primary_state()

        msg = f"{target_time.strftime('%Y-%m-%d %H:%M:%S')}에 [{action_name}] 예약이 등록되었습니다."
        if self.on_state_change:
            self.on_state_change(True, self.action_type, msg)

        return True, msg

    def _sync_primary_state(self):
        """가장 임박한 스케줄을 단일 대표 상태 변수에 동기화"""
        if not self.schedules:
            self.is_scheduled = False
            self.action_type = None
            self.target_time = None
            self.remaining_seconds = 0
            self.total_seconds = 0
            self.memo = ""
            return

        earliest = min(self.schedules.values(), key=lambda x: x["target_time"])
        now = datetime.datetime.now()
        rem = max(0, int((earliest["target_time"] - now).total_seconds()))

        self.is_scheduled = True
        self.action_type = earliest["action_type"]
        self.target_time = earliest["target_time"]
        self.total_seconds = earliest["total_seconds"]
        self.remaining_seconds = rem
        self.memo = earliest["memo"]
        self.sound_id = earliest["sound_id"]

    def cancel_schedule_by_id(self, item_id: str) -> Tuple[bool, str]:
        """고유 ID를 통한 개별 예약 취소"""
        with self._lock:
            if item_id in self.schedules:
                itm = self.schedules.pop(item_id)
                if itm["action_type"] in ("shutdown", "restart"):
                    self._run_windows_cancel()
                elif itm["action_type"] == "wake":
                    self._remove_windows_wake_task()

                self._sync_primary_state()
                action_name = self._get_action_name(itm["action_type"])
                msg = f"[{action_name}] 예약이 정상 취소되었습니다."
                if self.on_state_change:
                    self.on_state_change(self.is_scheduled, self.action_type, msg)
                return True, msg

        # 주간 퇴근 자동 종료 설정 취소
        if item_id == "weekly_shutdown":
            self.auto_power_config["auto_shutdown_enabled"] = False
            self.save_auto_power_config({"auto_shutdown_enabled": False})
            return True, "주간 퇴근 자동 종료 예약이 취소되었습니다."
        elif item_id == "weekly_wake":
            self.auto_power_config["auto_wake_enabled"] = False
            self.save_auto_power_config({"auto_wake_enabled": False})
            self._remove_windows_wake_task()
            return True, "주간 출근 자동 켜짐 예약이 취소되었습니다."

        return False, "취소할 예약 항목을 찾을 수 없습니다."

    def cancel_schedule(self, notify: bool = True) -> Tuple[bool, str]:
        """모든 예약 일괄 취소"""
        with self._lock:
            was_scheduled = bool(self.schedules) or self.is_scheduled
            self.schedules.clear()
            self._run_windows_cancel()
            self._remove_windows_wake_task()
            self._sync_primary_state()

            msg = "모든 예약이 취소되었습니다." if was_scheduled else "진행 중인 예약이 없습니다."
            if notify and self.on_state_change:
                self.on_state_change(False, None, msg)
            return True, msg

    def _multi_countdown_loop(self):
        """다중 스케줄 실시간 감시 및 실행 루프"""
        while not self._stop_event.is_set():
            now = datetime.datetime.now()
            due_items = []

            with self._lock:
                for s_id, itm in list(self.schedules.items()):
                    rem = int((itm["target_time"] - now).total_seconds())
                    itm["remaining_seconds"] = max(0, rem)
                    if rem <= 0:
                        due_items.append(self.schedules.pop(s_id))

                self._sync_primary_state()

                if self.on_tick and self.is_scheduled:
                    target_str = self.target_time.strftime("%Y-%m-%d %H:%M:%S") if self.target_time else ""
                    self.on_tick(self.remaining_seconds, target_str)

            for itm in due_items:
                self._execute_due_item(itm)

            time.sleep(1.0)

    def _execute_due_item(self, itm: dict):
        act = itm["action_type"]
        memo_to_show = itm["memo"]
        sound_to_play = itm["sound_id"]

        if act == "alarm":
            if self.on_alarm_triggered:
                self.on_alarm_triggered(memo_to_show, sound_to_play)
        elif act == "sleep":
            self._trigger_sleep()
        elif act == "wake":
            # 이미 윈도우가 켜졌으므로 알림만 표시
            if self.on_alarm_triggered:
                self.on_alarm_triggered("컴퓨터가 지정된 시각에 자동 구동되었습니다.", sound_to_play)
        elif act in ("shutdown", "restart"):
            flag = "/s" if act == "shutdown" else "/r"
            try:
                subprocess.run(
                    ["shutdown", flag, "/f", "/t", "0"],
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    check=False
                )
            except Exception:
                pass

    def _register_windows_wake_task(self, target_time: datetime.datetime) -> Tuple[bool, str]:
        """Windows 작업 스케줄러에 절전 해제 타이머(WakeToRun) 작업 등록"""
        if os.name != "nt":
            return True, "Windows 전용 기능입니다."

        time_str = target_time.strftime("%m/%d/%Y %H:%M:%S")
        ps_script = f"""
        $Action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c echo KNOLTEACHER_WAKE'
        $Trigger = New-ScheduledTaskTrigger -Once -At '{time_str}'
        $Settings = New-ScheduledTaskSettingsSet -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
        Register-ScheduledTask -TaskName 'KnolTeacher_AutoWake' -Action $Action -Trigger $Trigger -Settings $Settings -Force
        """
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if res.returncode == 0:
                return True, "절전 깨우기 작업 등록 성공"
            return False, res.stderr or "작업 스케줄러 등록 실패"
        except Exception as e:
            return False, str(e)

    def _remove_windows_wake_task(self):
        """Windows 절전 깨우기 작업 스케줄러 삭제"""
        if os.name != "nt":
            return
        ps_cmd = "Unregister-ScheduledTask -TaskName 'KnolTeacher_AutoWake' -Confirm:$false -ErrorAction SilentlyContinue"
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass

    def get_active_schedules(self) -> list[dict]:
        """현재 가동 중인 모든 예약 목록 반환"""
        items = []
        now = datetime.datetime.now()

        with self._lock:
            for s_id, itm in sorted(self.schedules.items(), key=lambda x: x[1]["target_time"]):
                action_kr = self._get_action_name(itm["action_type"])
                rem = max(0, int((itm["target_time"] - now).total_seconds()))
                items.append({
                    "id": s_id,
                    "type_name": action_kr,
                    "action_type": itm["action_type"],
                    "target_time_str": itm["target_time"].strftime("%Y-%m-%d %H:%M:%S"),
                    "repeat_type": itm.get("repeat_type", "오늘 1회성"),
                    "remaining_sec": rem,
                    "memo": itm.get("memo", ""),
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

    def _auto_power_loop(self):
        """월~금 퇴근 자동 종료 및 자동 켜짐 감시 루프"""
        last_triggered_date = None
        while not self._stop_event.is_set():
            now = datetime.datetime.now()
            today_date = now.date()

            # 월~금 (0~4) 확인
            if today_date.weekday() < 5:
                is_hol, _ = get_korean_holiday(today_date)
                skip = self.auto_power_config.get("skip_holidays", True) and is_hol

                if not skip:
                    # 1. 자동 퇴근 종료
                    if self.auto_power_config.get("auto_shutdown_enabled"):
                        target_t_str = self.auto_power_config.get("auto_shutdown_time", "16:40")
                        try:
                            t_hour, t_min = map(int, target_t_str.split(":"))
                            if now.hour == t_hour and now.minute == t_min and last_triggered_date != (today_date, "shutdown"):
                                last_triggered_date = (today_date, "shutdown")
                                self.execute_immediate("shutdown")
                        except Exception:
                            pass

            time.sleep(15.0)

    def execute_immediate(self, action_type: str) -> Tuple[bool, str]:
        self.cancel_schedule(notify=False)
        action_name = self._get_action_name(action_type)
        try:
            if action_type == "shutdown":
                subprocess.run(["shutdown", "/s", "/f", "/t", "0"], 
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                               check=False)
            elif action_type == "restart":
                subprocess.run(["shutdown", "/r", "/f", "/t", "0"], 
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                               check=False)
            elif action_type == "sleep":
                self._trigger_sleep()
            else:
                return False, "알 수 없는 동작입니다."
            return True, f"컴퓨터 {action_name}을(를) 즉시 실행합니다."
        except Exception as e:
            return False, f"{action_name} 실행 실패: {str(e)}"

    def _trigger_sleep(self):
        try:
            ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
        except Exception:
            subprocess.run(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                check=False
            )

    def _run_windows_cancel(self):
        try:
            subprocess.run(
                ["shutdown", "/a"],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                capture_output=True,
                text=True,
                check=False
            )
        except Exception:
            pass

    @staticmethod
    def _get_action_name(action_type: str) -> str:
        names = {
            "shutdown": "컴퓨터 종료",
            "restart": "다시 시작",
            "sleep": "절전 모드",
            "wake": "컴퓨터 자동 켜기 (절전 깨우기)",
            "alarm": "알람 / 리마인더"
        }
        return names.get(action_type, "동작")
