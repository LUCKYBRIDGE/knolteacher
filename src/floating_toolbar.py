import os
import sys
import tkinter as tk
import customtkinter as ctk
from src.font_config import setup_global_fonts, get_font
from src.drawing_overlay import ScreenDrawingOverlay
from src.classroom_tools import ClassroomToolsDialog
from src.system_monitor import system_monitor
from src.tooltip import attach_tooltip

class FloatingQuickToolbar(tk.Toplevel):
    """
    놀티쳐 데스크 스마트 플로팅 퀵 툴바 (Apple Dynamic Island 스타일)
    - 화면 위 어디든 자유 배치 & 상단 고정
    - 판서, 타이머, 발표자 뽑기, 시간표, 급식, 바로가기, 메인 창 원클릭 호출
    - 최소화(—), 닫기(✕), 핀 고정(📌) 완비
    - 모든 버튼에 직관적인 고품질 툴팁(Tooltip) 탑재
    """
    _instance = None

    @classmethod
    def get_instance(cls, parent=None):
        if cls._instance is None or not cls._instance.winfo_exists():
            cls._instance = cls(parent)
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.title("놀티쳐 퀵 툴바")
        self.attributes("-topmost", True)
        self.overrideredirect(True)

        self.is_pinned = True
        self.is_collapsed = False

        # 기본 크기 및 위치 (화면 상단 우측)
        sw = self.winfo_screenwidth()
        self.full_width = 690
        self.collapsed_width = 90
        self.tb_height = 46
        x = max(10, sw - self.full_width - 40)
        y = 30
        self.geometry(f"{self.full_width}x{self.tb_height}+{x}+{y}")

        self._build_ui()
        system_monitor.register_listener(self._on_metrics_updated)

    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        if self.is_collapsed:
            self._build_collapsed_ui()
        else:
            self._build_expanded_ui()

    def _build_collapsed_ui(self):
        # 접힌 상태: 컴팩트한 원형/캡슐 뱃지
        self.container = ctk.CTkFrame(
            self,
            fg_color="#0f172a",
            corner_radius=16,
            border_width=2,
            border_color="#38bdf8"
        )
        self.container.pack(fill="both", expand=True, padx=1, pady=1)

        # 클릭하면 펼쳐지는 뱃지 버튼
        btn = ctk.CTkButton(
            self.container,
            text="📅 퀵데스크",
            font=get_font(11, "bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            corner_radius=14,
            command=self._toggle_collapse
        )
        btn.pack(fill="both", expand=True, padx=2, pady=2)
        btn.bind("<Button-1>", self._start_drag)
        btn.bind("<B1-Motion>", self._on_drag)
        attach_tooltip(btn, "클릭하여 퀵 툴바 펼치기 (드래그하여 이동)")

    def _build_expanded_ui(self):
        self.container = ctk.CTkFrame(
            self,
            fg_color="#090d16",
            corner_radius=18,
            border_width=1,
            border_color="#0284c7"
        )
        self.container.pack(fill="both", expand=True, padx=1, pady=1)

        # 1. 드래그 핸들
        self.drag_handle = ctk.CTkLabel(
            self.container,
            text="⋮⋮",
            font=get_font(13, "bold"),
            text_color="#64748b",
            width=16,
            cursor="fleur"
        )
        self.drag_handle.pack(side="left", padx=(8, 2))
        self.drag_handle.bind("<Button-1>", self._start_drag)
        self.drag_handle.bind("<B1-Motion>", self._on_drag)
        attach_tooltip(self.drag_handle, "드래그하여 퀵 툴바 위치 이동")

        # 2. 실시간 CPU 미니 칩
        self.res_chip = ctk.CTkLabel(
            self.container,
            text="💻 15%",
            font=get_font(10, "bold"),
            text_color="#38bdf8",
            fg_color="#1e293b",
            corner_radius=8,
            width=48,
            height=28
        )
        self.res_chip.pack(side="left", padx=(0, 4))
        attach_tooltip(self.res_chip, "현재 컴퓨터 CPU 실시간 사용량")

        # 3. 주요 도구 단축 버튼들 (5대 교실 도구 완비)
        tools = [
            ("✏️ 판서", "#ea580c", "#c2410c", self._open_drawing, "화면 위 자유 판서 (펜/형광펜/도형)"),
            ("⏱️ 타이머", "#0284c7", "#0369a1", self._open_timer, "교실 집중 수업 타이머 & 스톱워치"),
            ("🎲 뽑기", "#10b981", "#059669", self._open_picker, "공정한 학생 발표자 무작위 추첨"),
            ("🎡 돌림판", "#f59e0b", "#d97706", self._open_wheel, "모둠/벌칙/보상 돌려돌려 돌림판"),
            ("🪜 사다리", "#8b5cf6", "#7c3aed", self._open_ladder, "짜릿한 학생/모둠 사다리타기 게임"),
            ("⚾ 핀볼", "#ec4899", "#db2777", self._open_pinball, "아케이드 통통 튀는 핀볼 추첨기"),
            ("📅 위젯", "#0ea5e9", "#0284c7", self._open_mini_widget, "바탕화면 올웨이즈온 시간표/급식 위젯"),
            ("💻 메인", "#334155", "#475569", self._open_main_app, "놀티쳐 데스크 메인 창 열기")
        ]

        for label, bg_c, hov_c, cmd, tip in tools:
            btn = ctk.CTkButton(
                self.container,
                text=label,
                font=get_font(10, "bold"),
                width=50,
                height=30,
                corner_radius=10,
                fg_color=bg_c,
                hover_color=hov_c,
                command=cmd
            )
            btn.pack(side="left", padx=1)
            attach_tooltip(btn, tip)

        ctk.CTkFrame(self.container, width=1, height=22, fg_color="#334155").pack(side="left", padx=3)

        # 4. 윈도우 컨트롤러 (핀 고정, 최소화, 닫기)
        self.pin_btn = ctk.CTkButton(
            self.container,
            text="📌" if self.is_pinned else "📍",
            font=get_font(10),
            width=24,
            height=28,
            corner_radius=8,
            fg_color="#1e293b" if self.is_pinned else "transparent",
            hover_color="#334155",
            command=self._toggle_pin
        )
        self.pin_btn.pack(side="left", padx=1)
        attach_tooltip(self.pin_btn, "항상 맨 위 상단 고정 토글")

        collapse_btn = ctk.CTkButton(
            self.container,
            text="—",
            font=get_font(12, "bold"),
            width=24,
            height=28,
            corner_radius=8,
            fg_color="#1e293b",
            hover_color="#334155",
            command=self._toggle_collapse
        )
        collapse_btn.pack(side="left", padx=1)
        attach_tooltip(collapse_btn, "미니 뱃지로 최소화 접기")

        close_btn = ctk.CTkButton(
            self.container,
            text="✕",
            font=get_font(11, "bold"),
            width=24,
            height=28,
            corner_radius=8,
            fg_color="#3f1d24",
            hover_color="#dc2626",
            text_color="#fca5a5",
            command=self.close
        )
        close_btn.pack(side="left", padx=(1, 6))
        attach_tooltip(close_btn, "플로팅 퀵 툴바 닫기")

    def _start_drag(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag(self, event):
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    def _toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        cur_x = self.winfo_x()
        cur_y = self.winfo_y()
        w = self.collapsed_width if self.is_collapsed else self.full_width
        self.geometry(f"{w}x{self.tb_height}+{cur_x}+{cur_y}")
        self._build_ui()

    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.attributes("-topmost", self.is_pinned)
        if hasattr(self, "pin_btn"):
            self.pin_btn.configure(
                text="📌" if self.is_pinned else "📍",
                fg_color="#1e293b" if self.is_pinned else "transparent"
            )

    def _on_metrics_updated(self, metrics: dict):
        if hasattr(self, "res_chip") and self.res_chip.winfo_exists():
            cpu_p = metrics.get("cpu_percent", 0.0)
            self.res_chip.configure(text=f"💻 {int(cpu_p)}%")

    def _open_drawing(self):
        ScreenDrawingOverlay.get_instance(self.parent).show()

    def _open_timer(self):
        ClassroomToolsDialog.get_instance(self.parent, initial_tab="timer")

    def _open_picker(self):
        ClassroomToolsDialog.get_instance(self.parent, initial_tab="picker")

    def _open_wheel(self):
        ClassroomToolsDialog.get_instance(self.parent, initial_tab="wheel")

    def _open_ladder(self):
        ClassroomToolsDialog.get_instance(self.parent, initial_tab="ladder")

    def _open_pinball(self):
        ClassroomToolsDialog.get_instance(self.parent, initial_tab="pinball")

    def _open_bookmarks(self):
        from src.site_bookmarks import SiteBookmarksDialog
        SiteBookmarksDialog(self.parent)

    def _open_mini_widget(self):
        if self.parent and hasattr(self.parent, "_open_mini_widget"):
            self.parent._open_mini_widget()

    def _open_main_app(self):
        if self.parent:
            self.parent.deiconify()
            self.parent.lift()
            self.parent.focus_force()

    def close(self):
        try:
            self.destroy()
        except Exception:
            pass
        FloatingQuickToolbar._instance = None
