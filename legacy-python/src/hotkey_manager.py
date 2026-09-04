"""
Windows 네이티브 전역 단축키(Global Hotkey) 매니저
- Alt+1 ~ Alt+9 및 F2 단축키 기본 제공
- 사용자가 원하는 키로 단축키 커스텀 변경 및 hotkeys_config.json 영구 저장 지원
- UI 실행 중 실시간 핫키 재등록(reload) 지원
"""
import os
import sys
import json
import ctypes
from ctypes import wintypes
import threading
from typing import Callable, Dict, Any, List

from src.config_utils import get_config_dir

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Win32 상수
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# 가상 키코드 매핑 딕셔너리
VK_MAP = {
    "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34, "5": 0x35,
    "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39, "0": 0x30,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F5": 0x74,
    "F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79,
    "F11": 0x7A, "F12": 0x7B,
    "A": 0x41, "B": 0x42, "C": 0x43, "D": 0x44, "E": 0x45,
    "P": 0x50, "S": 0x53, "T": 0x54, "Q": 0x51, "Z": 0x5A
}

MOD_MAP = {
    "Alt": MOD_ALT,
    "Ctrl": MOD_CONTROL,
    "Ctrl+Alt": MOD_CONTROL | MOD_ALT,
    "Shift+Alt": MOD_SHIFT | MOD_ALT,
    "None": 0
}

# 기본 핫키 설정 목록
DEFAULT_HOTKEYS = [
    {"id": 1, "action": "magnifier", "name": "화면 돋보기",       "desc": "마우스 주변 부분 확대경",          "mod": "Alt", "key": "1", "enabled": True},
    {"id": 2, "action": "drawing",   "name": "화면 판서",         "desc": "화면 위 자유 펜 판서 & 기하도구",  "mod": "Alt", "key": "2", "enabled": True},
    {"id": 3, "action": "timer",     "name": "교실 타이머",       "desc": "초점 집중 카운트다운 타이머",      "mod": "Alt", "key": "3", "enabled": True},
    {"id": 4, "action": "live_zoom", "name": "라이브 줌",         "desc": "화면 전체 실시간 줌인",            "mod": "Alt", "key": "4", "enabled": True},
    {"id": 5, "action": "recorder",  "name": "화면 녹화",         "desc": "수업 화면 및 음성 녹화 시작/종료", "mod": "Alt", "key": "5", "enabled": True},
    {"id": 6, "action": "snip",      "name": "화면 캡처",         "desc": "사각 영역 즉시 캡처 & 복사",       "mod": "Alt", "key": "6", "enabled": True},
    {"id": 7, "action": "board",     "name": "놀티쳐 보드",       "desc": "학생용 대형 올인원 보드 실행",     "mod": "Alt", "key": "7", "enabled": True},
    {"id": 8, "action": "picker",    "name": "발표자 추첨",       "desc": "무작위 발표자 학생 이름 뽑기",     "mod": "Alt", "key": "8", "enabled": True},
    {"id": 9, "action": "dock",      "name": "스마트 플로팅 독", "desc": "화면 상단 미니 리모컨 토글",       "mod": "Alt", "key": "9", "enabled": True},
    {"id": 10,"action": "board_f2",  "name": "놀티쳐 보드 (F2)",  "desc": "놀티쳐 보드 1초 원클릭 실행",     "mod": "None","key": "F2","enabled": True},
]


class GlobalHotkeyManager:
    _instance = None

    @classmethod
    def get_instance(cls, app=None):
        if cls._instance is None:
            cls._instance = cls(app)
        return cls._instance

    def __init__(self, app=None):
        self.app = app
        self.is_running = False
        self._thread = None
        self._thread_id = None
        self._callbacks: Dict[int, Callable] = {}
        self.config_path = os.path.join(get_config_dir(), "hotkeys_config.json")
        self.hotkeys = self.load_config()

    def load_config(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    saved = data.get("hotkeys", [])
                    # 기본 항목과 병합
                    saved_map = {item["id"]: item for item in saved}
                    result = []
                    for def_hk in DEFAULT_HOTKEYS:
                        hk_id = def_hk["id"]
                        if hk_id in saved_map:
                            m = dict(def_hk)
                            m.update(saved_map[hk_id])
                            result.append(m)
                        else:
                            result.append(dict(def_hk))
                    return result
            except Exception as e:
                print(f"[Hotkey Config Load Error] {e}")
        return [dict(h) for h in DEFAULT_HOTKEYS]

    def save_config(self, hotkeys_list: List[Dict[str, Any]]):
        self.hotkeys = hotkeys_list
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"hotkeys": hotkeys_list}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Hotkey Config Save Error] {e}")

    def reset_to_defaults(self):
        self.save_config([dict(h) for h in DEFAULT_HOTKEYS])
        self.reload()

    def get_display_shortcut(self, action: str) -> str:
        for hk in self.hotkeys:
            if hk["action"] == action and hk.get("enabled", True):
                mod = hk.get("mod", "None")
                k = hk.get("key", "")
                if mod == "None":
                    return k
                return f"{mod}+{k}"
        return ""

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._msg_loop, daemon=True)
        self._thread.start()

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)

    def reload(self):
        """실시간 단축키 재등록"""
        self.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.8)
        self.hotkeys = self.load_config()
        self.start()

    def _msg_loop(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        self._callbacks.clear()

        # 단축키 등록
        for hk in self.hotkeys:
            if not hk.get("enabled", True):
                continue
            hk_id = hk["id"]
            mod_str = hk.get("mod", "Alt")
            key_str = hk.get("key", "1")
            act = hk.get("action", "")

            mod_flag = MOD_MAP.get(mod_str, MOD_ALT)
            if mod_flag != 0:
                mod_flag |= MOD_NOREPEAT
            vk_code = VK_MAP.get(key_str, 0)

            if vk_code == 0:
                continue

            cb = self._get_action_callback(act)
            if cb is None:
                continue

            res = user32.RegisterHotKey(None, hk_id, mod_flag, vk_code)
            if res:
                self._callbacks[hk_id] = cb

        # 메시지 루프
        msg = wintypes.MSG()
        while self.is_running:
            b_ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if b_ret == 0 or b_ret == -1:
                break
            if msg.message == WM_HOTKEY:
                hk_id = msg.wParam
                if hk_id in self._callbacks:
                    cb = self._callbacks[hk_id]
                    if self.app and hasattr(self.app, "after"):
                        self.app.after(0, cb)
                    else:
                        cb()

        # 해제
        for hk_id in list(self._callbacks.keys()):
            user32.UnregisterHotKey(None, hk_id)

    def _get_action_callback(self, action: str):
        if action == "magnifier":
            return self._on_magnifier
        elif action == "drawing":
            return self._on_drawing
        elif action == "timer":
            return self._on_timer
        elif action == "live_zoom":
            return self._on_live_zoom
        elif action == "recorder":
            return self._on_recorder
        elif action == "snip":
            return self._on_snip
        elif action in ("board", "board_f2"):
            return self._on_board
        elif action == "picker":
            return self._on_picker
        elif action == "dock":
            return self._on_dock
        return None

    def _on_magnifier(self):
        from src.screen_magnifier import ScreenMagnifierWindow
        ScreenMagnifierWindow.toggle()

    def _on_drawing(self):
        from src.drawing_overlay import ScreenDrawingOverlay
        ScreenDrawingOverlay.toggle(self.app)

    def _on_timer(self):
        from src.focus_timer_overlay import FocusTimerOverlayWindow
        FocusTimerOverlayWindow.toggle()

    def _on_live_zoom(self):
        from src.screen_magnifier import LiveZoomController
        LiveZoomController.toggle()

    def _on_recorder(self):
        from src.screen_recorder import ScreenRecorderController
        ScreenRecorderController.toggle()

    def _on_snip(self):
        from src.screen_snip import ScreenSnipOverlay
        ScreenSnipOverlay.start_snip()

    def _on_board(self):
        from src.student_display import StudentDisplayWindow
        StudentDisplayWindow.get_instance(self.app)

    def _on_picker(self):
        from src.classroom_tools import ClassroomToolsDialog
        ClassroomToolsDialog.get_instance(self.app, initial_tab="picker")

    def _on_dock(self):
        from src.floating_toolbar import FloatingQuickToolbar
        FloatingQuickToolbar.get_instance(self.app)


hotkey_manager = GlobalHotkeyManager.get_instance()
