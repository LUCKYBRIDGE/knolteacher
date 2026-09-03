"""
수업 준비 사전 카운트다운 팝업 (Class Countdown Popup)
- 수업 시작 n분 전 알람이 울리기 전(기본 1분 전)에 화면에 세련되게 등장하여 60초 카운트다운 진행
- 카운트다운이 0초가 되는 순간 수업 알람 차임벨 종료음 자동 재생 및 팝업 소멸
- 교실 TV/전자칠판 및 교사 모니터 상시 최상위 플로팅
"""

import os
import sys
import threading
import tkinter as tk
import customtkinter as ctk

from src.font_config import setup_global_fonts, get_font
from src.sound_manager import sound_manager
from src.theme_manager import theme_manager

class ClassCountdownPopup(ctk.CTkToplevel):
    _instance = None

    @classmethod
    def show(cls, lesson_name: str, subject: str, lead_min: int, total_seconds: int = 60, parent=None):
        if cls._instance is not None and cls._instance.winfo_exists():
            try:
                cls._instance.destroy()
            except Exception:
                pass
        cls._instance = cls(lesson_name, subject, lead_min, total_seconds, parent)
        return cls._instance

    def __init__(self, lesson_name: str, subject: str, lead_min: int, total_seconds: int = 60, parent=None):
        super().__init__(parent)
        self.lesson_name = lesson_name
        self.subject = subject
        self.lead_min = lead_min
        self.remaining_sec = total_seconds
        self.total_seconds = total_seconds
        self.timer_job = None

        setup_global_fonts(self)
        self._setup_window()
        self._build_ui()
        self._start_countdown()

    def _setup_window(self):
        self.title("수업 준비 카운트다운")
        self.attributes("-topmost", True)
        self.overrideredirect(True)

        w, h = 340, 180
        sw = self.winfo_screenwidth()
        x = max(10, sw - w - 24)
        y = 24
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
        palette = theme_manager.get_theme()
        bg_col = "#0f172a" if palette.get("ctk_mode") == "dark" else "#ffffff"
        border_col = palette.get("accent", "#38bdf8")
        text_sub = "#94a3b8" if palette.get("ctk_mode") == "dark" else "#64748b"

        self.configure(fg_color=bg_col)

        main_card = ctk.CTkFrame(
            self,
            fg_color=bg_col,
            corner_radius=12,
            border_width=2,
            border_color=border_col
        )
        main_card.pack(fill="both", expand=True, padx=2, pady=2)

        top_row = ctk.CTkFrame(main_card, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=(12, 2))

        title_txt = f"🔔 [{self.lesson_name}] {self.subject}" if self.subject else f"🔔 [{self.lesson_name}]"
        ctk.CTkLabel(
            top_row,
            text=title_txt,
            font=get_font(12, "bold"),
            text_color=palette["accent"]
        ).pack(side="left")

        ctk.CTkButton(
            top_row,
            text="✕",
            width=24,
            height=24,
            font=get_font(11, "bold"),
            fg_color="transparent",
            hover_color="#dc2626",
            text_color=text_sub,
            corner_radius=4,
            command=self.close
        ).pack(side="right")

        self.cnt_lbl = ctk.CTkLabel(
            main_card,
            text=str(self.remaining_sec),
            font=ctk.CTkFont(family="Consolas", size=56, weight="bold"),
            text_color="#f59e0b"
        )
        self.cnt_lbl.pack(pady=(0, 2))

        sub_text = f"수업 시작 {self.lead_min}분 전 알람 카운트다운"
        self.sub_lbl = ctk.CTkLabel(
            main_card,
            text=sub_text,
            font=get_font(10, "bold"),
            text_color=text_sub
        )
        self.sub_lbl.pack(pady=(0, 10))

    def _start_countdown(self):
        if self.remaining_sec > 0:
            self.cnt_lbl.configure(text=str(self.remaining_sec))
            if self.remaining_sec <= 10:
                self.cnt_lbl.configure(text_color="#ef4444")
            self.remaining_sec -= 1
            self.timer_job = self.after(1000, self._start_countdown)
        else:
            self.cnt_lbl.configure(text="0", text_color="#10b981")
            self.sub_lbl.configure(text="수업 준비 알람 시간입니다!")

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
