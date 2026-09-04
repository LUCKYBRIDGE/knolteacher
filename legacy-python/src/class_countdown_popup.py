"""
수업 준비 사전 카운트다운 팝업 (Class Countdown Popup)
- alarm_design_manager에 설정된 선생님만의 커스텀 디자인(크기, 테마, 위치, 요소별 좌표/폰트)을 100% 반영
- 카운트다운이 0초가 되는 순간 수업 알람 차임벨 종료음 자동 재생 및 팝업 소멸
- 맑은 고딕(Malgun Gothic) 볼드 폰트로 통일하여 어떤 해상도에서도 깨짐 없이 선명함
"""
import os
import sys
import threading
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

from src.font_config import setup_global_fonts, get_font
from src.sound_manager import sound_manager
from src.theme_manager import theme_manager
from src.monitor_utils import get_monitor_by_index
from src.alarm_design_manager import alarm_design_manager


class ClassCountdownPopup(ctk.CTkToplevel):
    _instance = None

    @classmethod
    def show(cls, lesson_name: str, subject: str, lead_min: int, total_seconds: int = 60, parent=None, monitor_index: int = None):
        if cls._instance is not None and cls._instance.winfo_exists():
            try:
                cls._instance.destroy()
            except Exception:
                pass
        cls._instance = cls(lesson_name, subject, lead_min, total_seconds, parent, monitor_index)
        return cls._instance

    def __init__(self, lesson_name: str, subject: str, lead_min: int, total_seconds: int = 60, parent=None, monitor_index: int = None):
        super().__init__(parent)
        self.lesson_name = lesson_name
        self.subject = subject
        self.lead_min = lead_min
        self.remaining_sec = total_seconds
        self.total_seconds = total_seconds

        # 디자인 설정 로드
        self.cfg = alarm_design_manager.config
        self.monitor_index = monitor_index if monitor_index is not None else self.cfg.get("monitor_index", 0)
        self.timer_job = None

        setup_global_fonts(self)
        self._setup_window()
        self._build_ui()
        self._start_countdown()

    def _setup_window(self):
        self.title("수업 준비 카운트다운")
        self.attributes("-topmost", True)
        self.overrideredirect(True)

        w = self.cfg.get("window_width", 380)
        h = self.cfg.get("window_height", 210)
        pos_mode = self.cfg.get("position_mode", "top_right")

        m = get_monitor_by_index(self.monitor_index)

        if pos_mode == "center":
            x = m["x"] + (m["width"] - w) // 2
            y = m["y"] + (m["height"] - h) // 2
        elif pos_mode == "bottom_center":
            x = m["x"] + (m["width"] - w) // 2
            y = m["y"] + m["height"] - h - 60
        else:
            # top_right
            x = max(m["x"] + 10, m["x"] + m["width"] - w - 28)
            y = m["y"] + 28

        self.geometry(f"{w}x{h}+{x}+{y}")

        self.bind("<ButtonPress-1>", self._start_drag)
        self.bind("<B1-Motion>", self._do_drag)

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        bg_col = self.cfg.get("theme_bg", "#0f172a")
        border_col = self.cfg.get("theme_border", "#38bdf8")
        w = self.cfg.get("window_width", 380)
        h = self.cfg.get("window_height", 210)

        self.configure(fg_color=bg_col)

        # 캔버스 기반 픽셀 완벽 렌더러 (선생님의 커스텀 위치 100% 반영)
        self.canvas = tk.Canvas(self, bg=bg_col, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)

        # 테두리 라운드 사각형
        self.canvas.create_rectangle(1, 1, w - 2, h - 2, outline=border_col, width=2)

        # 우상단 닫기 ✕ 버튼
        close_id = self.canvas.create_text(
            w - 20, 18, text="✕", fill="#94a3b8",
            font=("Malgun Gothic", 10, "bold"), tags="close_btn"
        )
        self.canvas.tag_bind("close_btn", "<Button-1>", lambda e: self.close())

        elems = self.cfg.get("elements", {})

        # 1. 타이틀 (수업 교시명)
        if elems.get("title", {}).get("visible", True):
            e = elems["title"]
            title_txt = f"🔔 [{self.lesson_name}] {self.subject}" if self.subject else f"🔔 [{self.lesson_name}]"
            self.title_id = self.canvas.create_text(
                e.get("x", 20), e.get("y", 16), text=title_txt,
                fill=e.get("color", "#38bdf8"),
                font=("Malgun Gothic", e.get("font_size", 13), "bold"),
                anchor="nw"
            )

        # 2. 스티커 / 이미지
        if elems.get("sticker", {}).get("visible", True):
            e = elems["sticker"]
            st_type = e.get("sticker_type", "📚")
            img_path = e.get("image_path", "")
            if img_path and os.path.exists(img_path):
                try:
                    pil_im = Image.open(img_path).resize((e.get("size", 32), e.get("size", 32)))
                    self._st_photo = ImageTk.PhotoImage(pil_im)
                    self.canvas.create_image(e.get("x", 330), e.get("y", 20), image=self._st_photo, anchor="center")
                except Exception:
                    self.canvas.create_text(
                        e.get("x", 330), e.get("y", 20), text=st_type,
                        font=("Segoe UI Emoji", e.get("size", 32)), anchor="center"
                    )
            else:
                self.canvas.create_text(
                    e.get("x", 330), e.get("y", 20), text=st_type,
                    font=("Segoe UI Emoji", e.get("size", 32)), anchor="center"
                )

        # 3. 타이머 숫자 (맑은 고딕 볼드로 통일)
        if elems.get("timer", {}).get("visible", True):
            e = elems["timer"]
            self.cnt_id = self.canvas.create_text(
                e.get("x", 190), e.get("y", 80), text=str(self.remaining_sec),
                fill=e.get("color", "#f59e0b"),
                font=("Malgun Gothic", e.get("font_size", 52), "bold"),
                anchor="center"
            )

        # 4. 선생님 맞춤 안내 메시지
        if elems.get("message", {}).get("visible", True):
            e = elems["message"]
            self.msg_id = self.canvas.create_text(
                e.get("x", 190), e.get("y", 145), text=e.get("text", ""),
                fill=e.get("color", "#cbd5e1"),
                font=("Malgun Gothic", e.get("font_size", 11), "bold"),
                anchor="center"
            )

        # 5. 보조 공지 (알람 카운트다운)
        if elems.get("sub_notice", {}).get("visible", True):
            e = elems["sub_notice"]
            sub_txt = f"수업 시작 {self.lead_min}분 전 알람 카운트다운"
            self.sub_id = self.canvas.create_text(
                e.get("x", 190), e.get("y", 178), text=sub_txt,
                fill=e.get("color", "#64748b"),
                font=("Malgun Gothic", e.get("font_size", 9), "bold"),
                anchor="center"
            )

    def _start_countdown(self):
        if self.remaining_sec > 0:
            if hasattr(self, "cnt_id"):
                self.canvas.itemconfig(self.cnt_id, text=str(self.remaining_sec))
                if self.remaining_sec <= 10:
                    self.canvas.itemconfig(self.cnt_id, fill="#ef4444")
            self.remaining_sec -= 1
            self.timer_job = self.after(1000, self._start_countdown)
        else:
            if hasattr(self, "cnt_id"):
                self.canvas.itemconfig(self.cnt_id, text="0", fill="#10b981")
            if hasattr(self, "msg_id"):
                self.canvas.itemconfig(self.msg_id, text="🔔 수업 준비 알람 시간입니다!", fill="#10b981")

            def _play():
                try:
                    sound_manager.play_sound("chime")
                except Exception:
                    pass
            threading.Thread(target=_play, daemon=True).start()

            self.after(2000, self.close)

    def close(self):
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None
        ClassCountdownPopup._instance = None
        try:
            self.destroy()
        except Exception:
            pass
