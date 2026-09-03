"""
스마트 올인원 플로팅 독 (Knol Smart Dock)
- 파편화되어 난립하던 미니 시간표, 티커, 퀵바를 단 하나의 정돈된 슬림 캡슐 독으로 대통합
- 애플 Dynamic Island 감성의 초슬림 미니멀 디자인 (높이 38px)
- 좌측 실시간 시간표/남은시간 티커 + 중앙 핵심 수업도구 리모컨 + 우측 최소화
"""

import os
import sys
import datetime
import tkinter as tk
import customtkinter as ctk

from src.font_config import setup_global_fonts, get_font
from src.drawing_overlay import ScreenDrawingOverlay
from src.classroom_tools import ClassroomToolsDialog
from src.system_monitor import system_monitor
from src.tooltip import attach_tooltip
from src.timetable_manager import timetable_manager, DAYS_KO
from src.icon_renderer import get_icon

class FloatingQuickToolbar(tk.Toplevel):
    _instance = None

    @classmethod
    def get_instance(cls, parent=None):
        if cls._instance is None or not cls._instance.winfo_exists():
            cls._instance = cls(parent)
        else:
            cls._instance.deiconify()
            cls._instance.lift()
            cls._instance.attributes("-topmost", True)
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.title("스마트 플로팅 독")
        self.attributes("-topmost", True)
        self.overrideredirect(True)

        self.is_pinned = True
        self.is_collapsed = False
        self.tb_width = 560
        self.tb_height = 38
        self.collapsed_width = 160

        # 다른 파편화된 서브 위젯들 자동 정리 (중복 방지)
        self._cleanup_other_widgets()

        # 화면 상단 중앙 기본 배치
        sw = self.winfo_screenwidth()
        x = (sw - self.tb_width) // 2
        y = 12
        self.geometry(f"{self.tb_width}x{self.tb_height}+{x}+{y}")

        self._build_ui()
        self._keep_topmost_loop()
        self._start_ticker_loop()

    def _cleanup_other_widgets(self):
        """스마트 독 실행 시 다른 어수선한 위젯 창들을 자동으로 정리하여 화면을 깨끗하게 유지"""
        if self.parent:
            if hasattr(self.parent, "mini_widget") and self.parent.mini_widget and self.parent.mini_widget.winfo_exists():
                try: self.parent.mini_widget.withdraw()
                except Exception: pass
            if hasattr(self.parent, "mini_ticker") and self.parent.mini_ticker and self.parent.mini_ticker.winfo_exists():
                try: self.parent.mini_ticker.withdraw()
                except Exception: pass

    def _keep_topmost_loop(self):
        if not self.winfo_exists():
            return
        if self.is_pinned:
            self.attributes("-topmost", True)
        self.after(1500, self._keep_topmost_loop)

    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        if self.is_collapsed:
            self._build_collapsed_ui()
        else:
            self._build_expanded_ui()

    def _build_collapsed_ui(self):
        # 접힘 상태: 초미니 알약 형태
        cur_x = self.winfo_x()
        cur_y = self.winfo_y()
        self.geometry(f"{self.collapsed_width}x{self.tb_height}+{cur_x}+{cur_y}")

        pill = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=19, border_width=1, border_color="#38bdf8")
        pill.pack(fill="both", expand=True)

        info_txt = self._get_current_lesson_short()
        btn = ctk.CTkButton(
            pill, text=f"🔔 {info_txt}", font=get_font(10, "bold"),
            fg_color="transparent", hover_color="#1e293b", text_color="#38bdf8",
            corner_radius=18, command=self._toggle_collapse
        )
        btn.pack(fill="both", expand=True, padx=4, pady=2)
        btn.bind("<Button-1>", self._start_drag)
        btn.bind("<B1-Motion>", self._on_drag)
        attach_tooltip(btn, "클릭 시 스마트 독 펼치기 / 드래그로 이동")

    def _build_expanded_ui(self):
        cur_x = self.winfo_x()
        cur_y = self.winfo_y()
        self.geometry(f"{self.tb_width}x{self.tb_height}+{cur_x}+{cur_y}")

        # 메인 캡슐 프레임 (슬림 알약 형태, 다크 슬레이트 & 스카이블루 테두리)
        capsule = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=19, border_width=1, border_color="#334155")
        capsule.pack(fill="both", expand=True)

        # 1. 좌측 드래그 핸들 & 실시간 교시 티커
        left_box = ctk.CTkFrame(capsule, fg_color="transparent")
        left_box.pack(side="left", padx=(10, 6), fill="y")
        left_box.bind("<Button-1>", self._start_drag)
        left_box.bind("<B1-Motion>", self._on_drag)

        drag_ico = ctk.CTkLabel(left_box, text="⋮⋮", font=ctk.CTkFont(size=11, weight="bold"), text_color="#64748b", cursor="fleur")
        drag_ico.pack(side="left", padx=(0, 6))
        drag_ico.bind("<Button-1>", self._start_drag)
        drag_ico.bind("<B1-Motion>", self._on_drag)

        self.ticker_btn = ctk.CTkButton(
            left_box, text=self._get_current_lesson_text(), font=get_font(10, "bold"),
            fg_color="#1e293b", hover_color="#334155", text_color="#38bdf8",
            height=26, corner_radius=6, command=self._show_timetable_popover
        )
        self.ticker_btn.pack(side="left")
        attach_tooltip(self.ticker_btn, "클릭 시 오늘 시간표 팝업 보기")

        # 구분선
        ctk.CTkFrame(capsule, width=1, height=18, fg_color="#334155").pack(side="left", padx=6)

        # 2. 중앙 핵심 수업 도구 버튼 세트 (컴팩트 26x26px)
        tools = [
            ("pencil", "판서 펜", self._open_pen),
            ("flat_timer", "타이머", self._open_timer),
            ("camera", "화상기", self._open_visualizer),
            ("desktop", "놀티쳐 보드", self._open_board),
            ("flat_picker", "추첨", self._open_picker),
        ]

        center_box = ctk.CTkFrame(capsule, fg_color="transparent")
        center_box.pack(side="left", fill="y", expand=True)

        for ico_name, name, cmd in tools:
            ico = get_icon(ico_name, "#ffffff", 14)
            btn = ctk.CTkButton(
                center_box, text="", image=ico, width=28, height=26,
                fg_color="transparent", hover_color="#1e293b", corner_radius=6,
                command=cmd
            )
            btn.pack(side="left", padx=2)
            attach_tooltip(btn, name)

        # 구분선
        ctk.CTkFrame(capsule, width=1, height=18, fg_color="#334155").pack(side="left", padx=6)

        # 3. 우측 컨트롤 (접기 / 닫기)
        right_box = ctk.CTkFrame(capsule, fg_color="transparent")
        right_box.pack(side="right", padx=(4, 10))

        # 접기 버튼
        collapse_btn = ctk.CTkButton(
            right_box, text="—", width=22, height=22, font=get_font(10, "bold"),
            fg_color="transparent", hover_color="#1e293b", text_color="#94a3b8",
            corner_radius=4, command=self._toggle_collapse
        )
        collapse_btn.pack(side="left", padx=1)
        attach_tooltip(collapse_btn, "스마트 독 슬림 접기")

        # 닫기 버튼
        close_btn = ctk.CTkButton(
            right_box, text="✕", width=22, height=22, font=get_font(9, "bold"),
            fg_color="transparent", hover_color="#dc2626", text_color="#94a3b8",
            corner_radius=4, command=self.close
        )
        close_btn.pack(side="left", padx=1)
        attach_tooltip(close_btn, "스마트 독 닫기")

    def _get_current_lesson_text(self) -> str:
        try:
            _, _, items = timetable_manager.get_today_schedule_items()
            now = datetime.datetime.now()
            cur_time_str = now.strftime("%H:%M")

            for itm in items:
                st = itm.get("start", "")
                et = itm.get("end", "")
                if st and et and st <= cur_time_str <= et:
                    p_name = itm.get("name", "")
                    sub = itm.get("subject", "")
                    # 남은 분 계산
                    eh, em = map(int, et.split(":"))
                    remain_min = max(0, (eh * 60 + em) - (now.hour * 60 + now.minute))
                    return f"🔔 {p_name} {sub} ({remain_min}분 남음)"
            
            # 다음 수업 찾기
            for itm in items:
                st = itm.get("start", "")
                if st and cur_time_str < st:
                    p_name = itm.get("name", "")
                    sub = itm.get("subject", "")
                    return f"다음: {p_name} {sub} ({st})"

            return "오늘 수업 종료 🌿"
        except Exception:
            return "놀티쳐 스마트 독"

    def _get_current_lesson_short(self) -> str:
        txt = self._get_current_lesson_text()
        if len(txt) > 14:
            return txt[:13] + ".."
        return txt

    def _start_ticker_loop(self):
        def _tick():
            if self.winfo_exists():
                if not self.is_collapsed and hasattr(self, "ticker_btn") and self.ticker_btn.winfo_exists():
                    self.ticker_btn.configure(text=self._get_current_lesson_text())
                self.after(30000, _tick)  # 30초마다 갱신
        self.after(30000, _tick)

    def _toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        self._build_ui()

    def _show_timetable_popover(self):
        pop = ctk.CTkToplevel(self)
        pop.title("오늘의 시간표")
        pop.geometry("320x340")
        pop.attributes("-topmost", True)

        px = self.winfo_x()
        py = self.winfo_y() + self.tb_height + 6
        pop.geometry(f"+{px}+{py}")

        pop.configure(fg_color="#0f172a")

        hdr = ctk.CTkFrame(pop, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(hdr, text="📅 오늘의 수업 시간표", font=get_font(12, "bold"), text_color="#38bdf8").pack(side="left")
        ctk.CTkButton(hdr, text="✕", width=22, height=22, fg_color="transparent", hover_color="#dc2626", text_color="#ffffff", command=pop.destroy).pack(side="right")

        scroll = ctk.CTkScrollableFrame(pop, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        _, _, items = timetable_manager.get_today_schedule_items()
        for itm in items:
            p_name = itm.get("name", "")
            sub = itm.get("subject", "")
            st = itm.get("start", "")
            et = itm.get("end", "")

            row = ctk.CTkFrame(scroll, fg_color="#1e293b", corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=p_name, font=get_font(10, "bold"), text_color="#f59e0b", width=44).pack(side="left", padx=6, pady=4)
            ctk.CTkLabel(row, text=sub, font=get_font(11, "bold"), text_color="#ffffff").pack(side="left", padx=4)
            ctk.CTkLabel(row, text=f"{st}~{et}", font=ctk.CTkFont(family="Consolas", size=9), text_color="#94a3b8").pack(side="right", padx=8)

    # ─── 도구 실행 콜백 ───
    def _open_pen(self):
        if self.parent and hasattr(self.parent, "_open_screen_drawing"):
            self.parent._open_screen_drawing()

    def _open_timer(self):
        if self.parent:
            ClassroomToolsDialog.open_tool(self.parent, "timer")

    def _open_visualizer(self):
        if self.parent and hasattr(self.parent, "_open_visualizer"):
            self.parent._open_visualizer()

    def _open_board(self):
        if self.parent and hasattr(self.parent, "_open_student_display"):
            self.parent._open_student_display()

    def _open_picker(self):
        if self.parent:
            ClassroomToolsDialog.open_tool(self.parent, "picker")

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")

    def close(self):
        FloatingQuickToolbar._instance = None
        try:
            self.destroy()
        except Exception:
            pass
