import os
import sys
import time
import ctypes
import datetime
import threading
import subprocess
from typing import Callable, Optional

class ShutdownManager:
    """
    Windows 시스템 종료/재부팅/절전 예약 및 즉시 실행 관리자
    - 최신 예약 우선 (새 예약 시 과거 예약 자동 취소)
    - 실시간 1초 단위 타이머 및 상태 콜백
    - Windows native shutdown 명령 연동
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._timer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        self.is_scheduled: bool = False
        self.action_type: Optional[str] = None  # 'shutdown', 'restart', 'sleep'
        self.target_time: Optional[datetime.datetime] = None
        self.total_seconds: int = 0
        self.remaining_seconds: int = 0
        
        # 콜백 함수들
        self.on_tick: Optional[Callable[[int, str], None]] = None
        self.on_state_change: Optional[Callable[[bool, Optional[str], str], None]] = None

    def cancel_schedule(self, notify: bool = True) -> tuple[bool, str]:
        """
        현재 진행 중인 모든 예약을 취소합니다.
        """
        with self._lock:
            # 1. 내부 타이머 스레드 정지
            self._stop_event.set()
            
            # 2. Windows 네이티브 shutdown 취소 (/a)
            self._run_windows_cancel()
            
            was_scheduled = self.is_scheduled
            self.is_scheduled = False
            self.action_type = None
            self.target_time = None
            self.remaining_seconds = 0
            self.total_seconds = 0

            msg = "예약이 취소되었습니다." if was_scheduled else "진행 중인 예약이 없습니다."
            if notify and self.on_state_change:
                self.on_state_change(False, None, msg)
            
            return True, msg

    def schedule_action(self, action_type: str, seconds: int) -> tuple[bool, str]:
        """
        새로운 동작(종료/재부팅/절전)을 예약합니다.
        최신 예약 우선 원칙에 따라 기존 예약은 자동으로 취소되고 교체됩니다.
        """
        if seconds <= 0:
            return False, "예약 시간은 1초 이상이어야 합니다."
        
        # 1. 기존 예약 무조건 취소 (최신 예약 우선)
        self.cancel_schedule(notify=False)
        
        with self._lock:
            self._stop_event.clear()
            self.action_type = action_type
            self.total_seconds = seconds
            self.remaining_seconds = seconds
            now = datetime.datetime.now()
            self.target_time = now + datetime.timedelta(seconds=seconds)
            self.is_scheduled = True
            
            # Windows 네이티브 shutdown 명령도 함께 걸어두어 신뢰성 보장 (절전 모드 제외)
            if action_type in ('shutdown', 'restart'):
                # Windows shutdown.exe 지원 최대 시간(10년 = 315360000초)
                sec_param = min(seconds, 315360000)
                flag = '/s' if action_type == 'shutdown' else '/r'
                try:
                    subprocess.run(
                        ['shutdown', flag, '/t', str(sec_param), '/c', f'컴퓨터종료예약 앱에 의해 {self.target_time.strftime("%H:%M:%S")}에 실행됩니다.'],
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                except Exception as e:
                    print(f"Windows shutdown native call error: {e}")

            # 백그라운드 타이머 스레드 시작
            self._timer_thread = threading.Thread(target=self._countdown_loop, daemon=True)
            self._timer_thread.start()

            action_name = self._get_action_name(action_type)
            msg = f"{self.target_time.strftime('%Y-%m-%d %H:%M:%S')}에 {action_name} 예약이 완료되었습니다."
            
            if self.on_state_change:
                self.on_state_change(True, action_type, msg)
                
            return True, msg

    def execute_immediate(self, action_type: str) -> tuple[bool, str]:
        """
        즉시 동작 (종료, 재부팅, 절전) 실행
        """
        # 기존 예약 취소
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
        """
        1초마다 카운트다운을 수행하고 UI 콜백을 호출합니다.
        """
        while not self._stop_event.is_set():
            if self.remaining_seconds <= 0:
                # 시간 도달 시 동작 실행
                self._execute_due_action()
                break
            
            # 콜백 호출
            if self.on_tick:
                target_str = self.target_time.strftime('%Y-%m-%d %H:%M:%S') if self.target_time else ""
                self.on_tick(self.remaining_seconds, target_str)
            
            # 1초 대기 (중간에 stop_event가 켜지면 즉시 종료)
            if self._stop_event.wait(timeout=1.0):
                break
            
            self.remaining_seconds -= 1

    def _execute_due_action(self):
        """예약 시간에 도달했을 때 실행"""
        with self._lock:
            act = self.action_type
            self.is_scheduled = False
            
        if act == 'sleep':
            self._trigger_sleep()
        elif act in ('shutdown', 'restart'):
            # 네이티브 셧다운이 이미 걸려있지만, 오차 없이 정확히 즉시 트리거
            flag = '/s' if act == 'shutdown' else '/r'
            try:
                subprocess.run(['shutdown', flag, '/f', '/t', '0'],
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                               check=False)
            except Exception:
                pass

    def _trigger_sleep(self):
        """Windows 절전 모드 진입"""
        try:
            # powrprof.dll SetSuspendState(bHibernate, bForce, bWakeupEventsDisabled)
            # bHibernate=0 (절전), bForce=1 (강제), bWakeupEventsDisabled=0 (깨어남 이벤트 허용)
            ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
        except Exception:
            # Fallback
            subprocess.run(
                ['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0'],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                check=False
            )

    def _run_windows_cancel(self):
        """Windows shutdown.exe /a 실행"""
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
            'sleep': '절전 모드'
        }
        return names.get(action_type, '동작')
