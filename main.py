import os
import sys
import ctypes
from ctypes import wintypes
import atexit

# ─────────────────────────────────────────────────────────────────────────────
# 🔒 단일 인스턴스(Single Instance) 보장 & 중복 트레이 아이콘 원천 차단
# ─────────────────────────────────────────────────────────────────────────────
ERROR_ALREADY_EXISTS = 183
_single_instance_mutex = None

def ensure_single_instance():
    global _single_instance_mutex
    if sys.platform != "win32":
        return True

    mutex_name = "Global\\KnolTeacher_SingleInstance_Mutex_v1"
    _single_instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()

    if last_error == ERROR_ALREADY_EXISTS:
        # 이미 놀티쳐가 실행 중! 기존 창을 화면 앞으로 복원하고 즉시 종료
        try:
            # "놀티쳐" 윈도우 찾기
            matches = []
            def _enum_win_cb(hwnd, lparam):
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    if "놀티쳐" in title and "보드" not in title:
                        matches.append(hwnd)
                return True

            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            ctypes.windll.user32.EnumWindows(EnumWindowsProc(_enum_win_cb), 0)

            if matches:
                target_hwnd = matches[0]
                ctypes.windll.user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
                ctypes.windll.user32.SetForegroundWindow(target_hwnd)
        except Exception:
            pass

        # 새로 뜬 프로세스는 트레이를 띄우지 않고 0초 만에 조용히 종료!
        sys.exit(0)

    return True

# 프로그램 시작 즉시 단일 인스턴스 체크
ensure_single_instance()

# Windows 고해상도(DPI) 선명도 최적화
if sys.platform == "win32":
    try:
        # Per-Monitor DPI Aware v2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from src.font_config import setup_global_fonts
from src.scheduler_manager import SchedulerManager
from src.ui import App

def main():
    manager = SchedulerManager()
    app = App(manager)
    setup_global_fonts(app)

    # --tray 옵션으로 실행된 경우 창을 띄우지 않고 트레이에 조용히 상주
    if "--tray" in sys.argv:
        app.withdraw()

    # 앱 종료 시 트레이 아이콘 깨끗이 제거 등록
    def _clean_tray():
        if hasattr(app, "tray") and app.tray:
            try:
                app.tray.stop()
            except Exception:
                pass
    atexit.register(_clean_tray)

    app.mainloop()

if __name__ == "__main__":
    main()
