import ctypes
from ctypes import wintypes
import threading
import traceback
from typing import Callable, Dict

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Win32 상수
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


class GlobalHotkeyManager:
    """
    Windows 네이티브 전역 단축키(Global Hotkey) 매니저
    - Alt+1: 컴퓨터 화면 확대 (ScreenMagnifier)
    - Alt+2: 화면 위 자유 판서 (ScreenDrawingOverlay)
    - Alt+3: 화이트 검정 타이머 (FocusTimerOverlay)
    - Alt+4: 라이브 줌 (LiveZoomController)
    - Alt+5: 화면 녹화 시작/종료 (ScreenRecorderController)
    - Alt+6: 영역 캡처 (ScreenSnipOverlay)
    """
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
            user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT = 0x0012

    def _msg_loop(self):
        self._thread_id = kernel32.GetCurrentThreadId()

        # 1. 단축키 등록
        hotkeys = [
            (1, MOD_ALT | MOD_NOREPEAT, 0x31, self._on_alt_1),  # Alt + 1
            (2, MOD_ALT | MOD_NOREPEAT, 0x32, self._on_alt_2),  # Alt + 2
            (3, MOD_ALT | MOD_NOREPEAT, 0x33, self._on_alt_3),  # Alt + 3
            (4, MOD_ALT | MOD_NOREPEAT, 0x34, self._on_alt_4),  # Alt + 4
            (5, MOD_ALT | MOD_NOREPEAT, 0x35, self._on_alt_5),  # Alt + 5
            (6, MOD_ALT | MOD_NOREPEAT, 0x36, self._on_alt_6),  # Alt + 6
        ]

        for hk_id, mod, vk, cb in hotkeys:
            res = user32.RegisterHotKey(None, hk_id, mod, vk)
            if res:
                self._callbacks[hk_id] = cb

        # 2. 메시지 루프
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

        # 3. 해제
        for hk_id in list(self._callbacks.keys()):
            user32.UnregisterHotKey(None, hk_id)

    # ─── 각 핫키 콜백 ──────────────────────────────────────────────────────
    def _on_alt_1(self):
        from src.screen_magnifier import ScreenMagnifierWindow
        ScreenMagnifierWindow.toggle()

    def _on_alt_2(self):
        from src.drawing_overlay import ScreenDrawingOverlay
        ScreenDrawingOverlay.toggle(self.app)

    def _on_alt_3(self):
        from src.focus_timer_overlay import FocusTimerOverlayWindow
        FocusTimerOverlayWindow.toggle()

    def _on_alt_4(self):
        from src.screen_magnifier import LiveZoomController
        LiveZoomController.toggle()

    def _on_alt_5(self):
        from src.screen_recorder import ScreenRecorderController
        ScreenRecorderController.toggle()

    def _on_alt_6(self):
        from src.screen_snip import ScreenSnipOverlay
        ScreenSnipOverlay.start_snip()


hotkey_manager = GlobalHotkeyManager.get_instance()
