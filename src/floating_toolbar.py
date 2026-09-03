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
    - 화면 위 어디든 자유 배치 & 상단/하단 스냅
    - 어떤 창보다 무조건 최상단 보장 (Always on Top 유지 루프)
    - 손쉬운 3단 크기 조절 (S 컴팩트 / M 기본 / L 대형 터치 모드)
    - 판서, 실물화상기, 학생화면, 타이머, 뽑기, 돌림판 원클릭 리모컨
    """
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
        self.title("놀티쳐 퀵 툴바")
        self.attributes("-topmost", True)
        self.overrideredirect(True)

        self.is_pinned = True
        self.is_collapsed = False
        self.size_mode = "M"  # "S", "M", "L"

        # 기본 크기 및 위치 (화면 상단 우측)
        sw = self.winfo_screenwidth()
        self._update_dimensions()
        x = max(10, sw - self.full_width - 40)
        y = 30
        self.geometry(f"{self.full_width}x{self.tb_height}+{x}+{y}")

        self._build_ui()
        system_monitor.register_listener(self._on_metrics_updated)
        self._keep_topmost_loop()

    def _update_dimensions(self):
        if self.size_mode == "S":
            self.full_width = 620
            self.tb_height = 42
            self.btn_w = 40
            self.btn_h = 32
            self.ico_sz = 18
            self.show_text = False
        elif self.size_mode == "L":
            self.full_width = 860
            self.tb_height = 62
            self.btn_w = 56
            self.btn_h = 46
            self.ico_sz = 24
            self.show_text = True
        else:  # "M"
            self.full_width = 750
            self.tb_height = 52
            self.btn_w = 48
            self.btn_h = 38
            self.ico_sz = 20
            self.show_text = True

        self.collapsed_width = 96

    def _keep_topmost_loop(self):
        """어떤 앱이나 브라우저보다 항상 최상단에 머무르도록 보장"""
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
        self.container = ctk.CTkFrame(
            self, fg_color="#0f172a", corner_radius=16,
            border_width=2, border_color="#38bdf8"
        )
        self.container.pack(fill="both", expand=True, padx=1, pady=1)

        btn = ctk.CTkButton(
            self.container, text="🛠️ 퀵바",
            font=get_font(11, "bold"), fg_color="#0284c7", hover_color="#0369a1",
            corner_radius=14, command=self._toggle_collapse
        )
        btn.pack(fill="both", expand=True, padx=2, pady=2)
        btn.bind("<Button-1>", self._start_drag)
        btn.bind("<B1-Motion>", self._on_drag)
        btn.bind("<ButtonRelease-1>", self._on_drag_end)
        attach_tooltip(btn, "클릭하여 퀵 툴바 펼치기 (드래그하여 이동)")

    def _build_expanded_ui(self):
        self.container = ctk.CTkFrame(
            self, fg_color="#090d16", corner_radius=18,
            border_width=1, border_color="#0284c7"
        )
        self.container.pack(fill="both", expand=True, padx=1, pady=1)

        from src.icon_renderer import get_icon, COL_MAIN, COL_ACTIVE, COL_DANGER, COL_ORANGE
        ICO = self.ico_sz

        # 1. 드래그 핸들
        drag_lbl = ctk.CTkLabel(
            self.container, text="", image=get_icon("drag", "#475569", ICO),
            width=16, cursor="fleur"
        )
        drag_lbl.pack(side="left", padx=(6, 2))
        drag_lbl.bind("<Button-1>", self._start_drag)
        drag_lbl.bind("<B1-Motion>", self._on_drag)
        drag_lbl.bind("<ButtonRelease-1>", self._on_drag_end)
        attach_tooltip(drag_lbl, "드래그하여 퀵 툴바 위치 이동 (화면 상하 모서리에 자석 스냅)")

        # 2. 실시간 CPU 미니 칩
        self.res_chip = ctk.CTkLabel(
            self.container, text="CPU --%",
            font=get_font(8 if self.size_mode == "S" else 9, "bold"),
            text_color="#38bdf8", fg_color="#1e293b", corner_radius=8,
            width=46 if self.size_mode == "S" else 52,
            height=24 if self.size_mode == "S" else 28
        )
        self.res_chip.pack(side="left", padx=(0, 2))
        attach_tooltip(self.res_chip, "현재 컴퓨터 CPU 실시간 사용량")

        def _sep():
            ctk.CTkFrame(self.container, width=1, height=22, fg_color="#334155").pack(side="left", padx=2)

        _sep()

        # 3. 핵심 수업 도구 단축 버튼들
        tools = [
            ("drawing",  "판서",   self._open_drawing,         COL_ORANGE, "화면 위 자유 판서 (펜/형광펜/도형)"),
            ("camera",   "화상기", self._open_visualizer,      COL_ACTIVE, "웹캠/USB 실물화상기 실시간 뷰어"),
            ("timer",    "타이머", self._open_timer,           COL_MAIN,   "교실 집중 수업 타이머 & 스톱워치"),
            ("dice",     "뽑기",   self._open_picker,          COL_MAIN,   "공정한 학생 발표자 무작위 추첨"),
            ("wheel",    "돌림판", self._open_wheel,           COL_MAIN,   "모둠/벌칙/보상 돌려돌려 돌림판"),
            ("widget",   "학생TV", self._open_student_display, COL_ACTIVE, "교실 TV/전자칠판용 대형 화면"),
            ("widget",   "위젯",   self._open_mini_widget,     COL_MAIN,   "바탕화면 올웨이즈온 시간표/급식 위젯"),
            ("home",     "메인",   self._open_main_app,        COL_ACTIVE, "놀티쳐 데스크 메인 창 열기"),
        ]

        for icon_name, label, cmd, icon_col, tip in tools:
            btn = ctk.CTkButton(
                self.container,
                text=label if self.show_text else "",
                image=get_icon(icon_name, icon_col, ICO),
                compound="top" if self.show_text else "none",
                font=get_font(8 if self.size_mode == "M" else 9, "bold"),
                width=self.btn_w, height=self.btn_h,
                corner_radius=8,
                fg_color="#1e293b",
                hover_color="#0284c7",
                text_color="#94a3b8",
                command=cmd
            )
            btn.pack(side="left", padx=1)
            attach_tooltip(btn, tip)

        _sep()

        # 4. 크기 조절 버튼 (S / M / L 토글)
        self.size_btn = ctk.CTkButton(
            self.container, text=self.size_mode,
            font=get_font(9, "bold"),
            width=24, height=28, corner_radius=6,
            fg_color="#1e293b", hover_color="#334155",
            text_color="#38bdf8", command=self._cycle_size_mode
        )
        self.size_btn.pack(side="left", padx=1)
        attach_tooltip(self.size_btn, f"퀵바 크기 조절 (현재: {self.size_mode} 모드 - 클릭 시 S/M/L 순환)")

        # 5. 윈도우 컨트롤러 (핀 고정, 최소화, 닫기)
        self.pin_btn = ctk.CTkButton(
            self.container, text="",
            image=get_icon("pin", COL_ACTIVE if self.is_pinned else COL_MAIN, ICO-2),
            width=26, height=28, corner_radius=6,
            fg_color="#1e293b" if self.is_pinned else "transparent",
            hover_color="#334155", command=self._toggle_pin
        )
        self.pin_btn.pack(side="left", padx=1)
        attach_tooltip(self.pin_btn, "항상 맨 위 상단 고정 토글")

        collapse_btn = ctk.CTkButton(
            self.container, text="",
            image=get_icon("minus", COL_MAIN, ICO-2),
            width=24, height=28, corner_radius=6,
            fg_color="#1e293b", hover_color="#334155",
            command=self._toggle_collapse
        )
        collapse_btn.pack(side="left", padx=1)
        attach_tooltip(collapse_btn, "미니 뱃지로 접기")

        close_btn = ctk.CTkButton(
            self.container, text="",
            image=get_icon("close", COL_DANGER, ICO-2),
            width=24, height=28, corner_radius=6,
            fg_color="#3f1d24", hover_color="#dc2626",
            command=self.close
        )
        close_btn.pack(side="left", padx=(1, 5))
        attach_tooltip(close_btn, "플로팅 퀵 툴바 닫기")

    def _cycle_size_mode(self):
        modes = ["S", "M", "L"]
        idx = modes.index(self.size_mode)
        self.size_mode = modes[(idx + 1) % len(modes)]
        self._update_dimensions()
        cur_x = self.winfo_x()
        cur_y = self.winfo_y()
        self.geometry(f"{self.full_width}x{self.tb_height}+{cur_x}+{cur_y}")
        self._build_ui()

    def _start_drag(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag(self, event):
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    def _on_drag_end(self, event):
        """화면 상단/하단 자석 스냅"""
        cur_y = self.winfo_y()
        cur_x = self.winfo_x()
        sh = self.winfo_screenheight()
        # 상단 80px 이내면 상단 스냅
        if cur_y < 80:
            self.geometry(f"+{cur_x}+20")
        # 하단 100px 이내면 하단 스냅
        elif cur_y > sh - 120:
            self.geometry(f"+{cur_x}+{sh - self.tb_height - 30}")

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
            from src.icon_renderer import get_icon, COL_ACTIVE, COL_MAIN
            self.pin_btn.configure(
                image=get_icon("pin", COL_ACTIVE if self.is_pinned else COL_MAIN, self.ico_sz - 2),
                fg_color="#1e293b" if self.is_pinned else "transparent"
            )

    def _on_metrics_updated(self, metrics: dict):
        if hasattr(self, "res_chip") and self.res_chip.winfo_exists():
            cpu_p = metrics.get("cpu_percent", 0.0)
            col = "#4ade80" if cpu_p < 50 else ("#fb923c" if cpu_p < 80 else "#f87171")
            self.res_chip.configure(
                text=f"CPU {int(cpu_p):2d}%",
                text_color=col
            )

    def _open_drawing(self):
        ScreenDrawingOverlay.get_instance(self.parent).show()

    def _open_visualizer(self):
        from src.visualizer_window import VisualizerWindow
        VisualizerWindow.get_instance(self.parent)

    def _open_timer(self):
        ClassroomToolsDialog.get_instance(self.parent, initial_tab="timer")

    def _open_picker(self):
        ClassroomToolsDialog.get_instance(self.parent, initial_tab="picker")

    def _open_wheel(self):
        ClassroomToolsDialog.get_instance(self.parent, initial_tab="wheel")

    def _open_student_display(self):
        if self.parent and hasattr(self.parent, "_open_student_display"):
            self.parent._open_student_display()

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
