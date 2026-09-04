import tkinter as tk
import customtkinter as ctk

class ToolTip:
    """
    모든 CustomTkinter 및 Tkinter 위젯에 장착 가능한 스마트 풍선도움말 (Tooltip)
    - 마우스 커서에 글씨가 절대 가려지지 않도록 위젯 바깥(상단/좌측/안전 영역)에 스마트 배치
    - 사진 4와 동일한 깔끔한 화이트 카드 + 또렷한 블랙 텍스트 디자인
    """
    def __init__(self, widget, text: str, delay_ms: int = 150):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.tip_window = None
        self._after_id = None
        self._cursor_x = 0
        self._cursor_y = 0

        try:
            self.widget.bind("<Enter>", self._on_enter, add="+")
            self.widget.bind("<Motion>", self._on_motion, add="+")
            self.widget.bind("<Leave>", self._on_leave, add="+")
            self.widget.bind("<ButtonPress>", self._on_leave, add="+")
        except Exception:
            pass

    def _on_enter(self, event=None):
        if event:
            self._cursor_x = event.x_root
            self._cursor_y = event.y_root
        self._schedule()

    def _on_motion(self, event=None):
        if event:
            self._cursor_x = event.x_root
            self._cursor_y = event.y_root

    def _on_leave(self, event=None):
        self._cancel()
        self._hide()

    def _schedule(self):
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        if not self.text or not self.widget.winfo_exists():
            return
        if self.tip_window:
            return

        try:
            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_attributes("-topmost", True)

            # 사진 4와 완벽히 동일한 화이트 박스 + 얇은 블랙 테두리 + 볼드 텍스트
            frame = tk.Frame(
                tw,
                background="#ffffff",
                highlightbackground="#000000",
                highlightcolor="#000000",
                highlightthickness=1,
                padx=6,
                pady=3
            )
            frame.pack()

            label = tk.Label(
                frame,
                text=self.text,
                justify=tk.LEFT,
                background="#ffffff",
                foreground="#000000",
                font=("맑은 고딕", 9, "bold")
            )
            label.pack()

            tw.update_idletasks()
            tip_w = tw.winfo_reqwidth()
            tip_h = tw.winfo_reqheight()

            # 위젯 위치 및 화면 크기
            wx = self.widget.winfo_rootx()
            wy = self.widget.winfo_rooty()
            ww = self.widget.winfo_width()
            wh = self.widget.winfo_height()
            sw = self.widget.winfo_screenwidth()
            sh = self.widget.winfo_screenheight()

            # 마우스 커서에 절대 가려지지 않는 스마트 위치 계산
            # 1. 세로 툴바의 경우 (사진 4): 위젯의 왼쪽 바깥에 배치
            if wx > sw // 2:
                # 화면 오른쪽에 있는 세로 툴바 등 -> 위젯 왼쪽 바깥에 띄움
                x = wx - tip_w - 6
                y = wy + (wh - tip_h) // 2
            elif wy > sh - 100:
                # 화면 최하단(하단 독 바 등) -> 위젯 위쪽 바깥에 띄움
                x = max(10, min(sw - tip_w - 10, wx + (ww - tip_w) // 2))
                y = wy - tip_h - 6
            elif wx < 100:
                # 화면 맨 왼쪽 툴바 -> 위젯 오른쪽 바깥에 띄움
                x = wx + ww + 6
                y = wy + (wh - tip_h) // 2
            else:
                # 기본: 위젯의 상단 또는 마우스 커서에서 충분히 떨어진 위치
                x = max(10, min(sw - tip_w - 10, wx + (ww - tip_w) // 2))
                y = wy - tip_h - 6
                if y < 10:  # 상단 공간이 부족하면 위젯 아래로
                    y = wy + wh + 8

            tw.wm_geometry(f"+{x}+{y}")
        except Exception:
            self._hide()

    def _hide(self):
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None

def attach_tooltip(widget, text: str):
    """위젯에 손쉽게 툴팁을 연결하는 헬퍼 함수"""
    if widget and text:
        return ToolTip(widget, text)
    return None
