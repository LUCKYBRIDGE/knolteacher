import tkinter as tk
import customtkinter as ctk
from src.font_config import get_font

class ToolTip:
    """
    모든 CustomTkinter 및 Tkinter 위젯에 장착 가능한 부드러운 풍선도움말 (Tooltip)
    - 마우스를 올리면 0.25초 후 세련된 반투명 캡슐 툴팁 표시
    - 마우스가 벗어나면 즉시 제거
    """
    def __init__(self, widget, text: str, delay_ms: int = 250):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.tip_window = None
        self._after_id = None

        try:
            self.widget.bind("<Enter>", self._on_enter, add="+")
            self.widget.bind("<Leave>", self._on_leave, add="+")
            self.widget.bind("<ButtonPress>", self._on_leave, add="+")
        except Exception:
            pass

    def _on_enter(self, event=None):
        self._schedule()

    def _on_leave(self, event=None):
        self._cancel()
        self._hide()

    def _schedule(self):
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self):
        if not self.text or not self.widget.winfo_exists():
            return
        if self.tip_window:
            return

        try:
            x = self.widget.winfo_rootx() + 10
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8

            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_attributes("-topmost", True)
            try:
                tw.wm_attributes("-alpha", 0.95)
            except Exception:
                pass

            # 세련된 다크/골드 캡슐 툴팁 프레임
            frame = tk.Frame(
                tw,
                background="#0f172a",
                highlightbackground="#38bdf8",
                highlightcolor="#38bdf8",
                highlightthickness=1,
                padx=8,
                pady=4
            )
            frame.pack()

            label = tk.Label(
                frame,
                text=self.text,
                justify=tk.LEFT,
                background="#0f172a",
                foreground="#f8fafc",
                font=("Malgun Gothic", 10, "bold")
            )
            label.pack()

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
