import os
import sys
import tkinter as tk
import customtkinter as ctk
from src.font_config import setup_global_fonts, get_font
from src.drawing_overlay import ScreenDrawingOverlay
from src.classroom_tools import ClassroomToolsDialog
from src.system_monitor import system_monitor

class FloatingQuickToolbar(tk.Toplevel):
    """
    모니터 위 어느 곳이든 둥둥 띄워놓고 자주 쓰는 교사용 도구를 원클릭으로 실행하는 스마트 플로팅 퀵 툴바
    (접기/펼치기, 실시간 자원 칩, 판서, 시간표, 타이머, 뽑기, 사이트 바로가기 완비)
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
        self.title("티처메이트 퀵 툴바")
        self.attributes("-topmost", True)
        self.overrideredirect(True)  # 테두리 없는 모던 캡슐 디자인

        self.is_pinned = True
        self.is_collapsed = False

        # 기본 크기 및 위치 (화면 상단 우측)
        sw = self.winfo_screenwidth()
        self.full_width = 510
        self.collapsed_width = 72
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
            text="📅 툴바",
            font=get_font(11, "bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            corner_radius=14,
            command=self._toggle_collapse
        )
        btn.pack(fill="both", expand=True, padx=2, pady=2)
        btn.bind("<Button-1>", self._start_drag)
        btn.bind("<B1-Motion>", self._on_drag)

    def _build_expanded_ui(self):
        self.container = ctk.CTkFrame(
            self,
            fg_color="#0f172a",
            corner_radius=16,
            border_width=2,
            border_color="#38bdf8"
        )
        self.container.pack(fill="both", expand=True, padx=1, pady=1)

        # 드래그 핸들
        self.drag_handle = ctk.CTkLabel(
            self.container,
            text="⠿",
            font=get_font(13, "bold"),
            text_color="#64748b",
            width=16,
            cursor="fleur"
        )
        self.drag_handle.pack(side="left", padx=(5, 1))
        self.drag_handle.bind("<Button-1>", self._start_drag)
        self.drag_handle.bind("<B1-Motion>", self._on_drag)

        # 1. ✏️ 화면 판서
        self.btn_draw = ctk.CTkButton(
            self.container,
            text="✏️ 판서",
            font=get_font(11, "bold"),
            width=54,
            height=30,
            fg_color="#ea580c",
            hover_color="#c2410c",
            corner_radius=8,
            command=self._toggle_screen_drawing
        )
        self.btn_draw.pack(side="left", padx=1)

        # 2. 📅 미니 시간표/급식
        self.btn_tt = ctk.CTkButton(
            self.container,
            text="📅 시간표",
            font=get_font(11, "bold"),
            width=58,
            height=30,
            fg_color="#1e293b",
            hover_color="#334155",
            corner_radius=8,
            command=self._open_mini_timetable
        )
        self.btn_tt.pack(side="left", padx=1)

        # 3. ⏱️ 교실 타이머
        self.btn_timer = ctk.CTkButton(
            self.container,
            text="⏱️ 타이머",
            font=get_font(11, "bold"),
            width=58,
            height=30,
            fg_color="#10b981",
            hover_color="#059669",
            corner_radius=8,
            command=lambda: self._open_classroom_tools("timer")
        )
        self.btn_timer.pack(side="left", padx=1)

        # 4. 🎲 발표자 뽑기
        self.btn_picker = ctk.CTkButton(
            self.container,
            text="🎲 뽑기",
            font=get_font(11, "bold"),
            width=52,
            height=30,
            fg_color="#f59e0b",
            hover_color="#d97706",
            corner_radius=8,
            command=lambda: self._open_classroom_tools("picker")
        )
        self.btn_picker.pack(side="left", padx=1)

        # 5. 🌐 교육 사이트
        self.btn_sites = ctk.CTkButton(
            self.container,
            text="🌐 사이트",
            font=get_font(11, "bold"),
            width=58,
            height=30,
            fg_color="#0284c7",
            hover_color="#0369a1",
            corner_radius=8,
            command=self._open_site_bookmarks
        )
        self.btn_sites.pack(side="left", padx=1)

        # 6. 💻 실시간 자원 칩
        self.res_chip = ctk.CTkLabel(
            self.container,
            text="💻--%",
            font=get_font(9, "bold"),
            text_color="#38bdf8",
            width=42
        )
        self.res_chip.pack(side="left", padx=2)

        # 구분선
        ctk.CTkFrame(self.container, width=1, height=20, fg_color="#334155").pack(side="left", padx=2)

        # 7. 📌 고정 핀
        self.pin_btn = ctk.CTkButton(
            self.container,
            text="📌",
            width=24,
            height=26,
            font=get_font(10),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            corner_radius=6,
            command=self._toggle_pin
        )
        self.pin_btn.pack(side="left", padx=1)

        # 8. — 접기 (아이콘 모드로 축소)
        ctk.CTkButton(
            self.container,
            text="—",
            width=24,
            height=26,
            font=get_font(10, "bold"),
            fg_color="#374151",
            hover_color="#4b5563",
            corner_radius=6,
            command=self._toggle_collapse
        ).pack(side="left", padx=1)

        # 9. ✕ 닫기
        ctk.CTkButton(
            self.container,
            text="✕",
            width=24,
            height=26,
            font=get_font(10, "bold"),
            fg_color="#3f1d24",
            hover_color="#dc2626",
            text_color="#fca5a5",
            corner_radius=6,
            command=self.destroy
        ).pack(side="left", padx=(1, 4))

    def _on_metrics_updated(self, m: dict):
        if not self.winfo_exists():
            return
        try:
            self.after(0, self._update_res_chip, m)
        except Exception:
            pass

    def _update_res_chip(self, m: dict):
        if hasattr(self, "res_chip") and self.res_chip.winfo_exists():
            c_p = int(m.get("cpu_percent", 0))
            self.res_chip.configure(
                text=f"💻{c_p}%",
                text_color="#ef4444" if c_p > 85 else ("#f59e0b" if c_p > 60 else "#38bdf8")
            )

    def _toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        cur_x = self.winfo_x()
        cur_y = self.winfo_y()

        if self.is_collapsed:
            self.geometry(f"{self.collapsed_width}x{self.tb_height}+{cur_x}+{cur_y}")
        else:
            self.geometry(f"{self.full_width}x{self.tb_height}+{cur_x}+{cur_y}")

        self._build_ui()

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.attributes("-topmost", self.is_pinned)
        self.pin_btn.configure(
            text="📌" if self.is_pinned else "📍",
            fg_color="#2563eb" if self.is_pinned else "#334155"
        )

    def _toggle_screen_drawing(self):
        overlay = ScreenDrawingOverlay.get_instance(self.parent or self)
        if overlay.is_alive():
            overlay.close()
            self.btn_draw.configure(fg_color="#ea580c")
        else:
            overlay.show()
            self.btn_draw.configure(fg_color="#10b981")

    def _open_mini_timetable(self):
        if self.parent and hasattr(self.parent, "_open_mini_widget"):
            self.parent._open_mini_widget()
        else:
            from src.mini_widget import MiniTimetableWidget
            MiniTimetableWidget(self)

    def _open_classroom_tools(self, tab: str):
        ClassroomToolsDialog(self.parent or self, initial_tab=tab)

    def _open_site_bookmarks(self):
        from src.site_bookmarks import SiteBookmarksDialog
        SiteBookmarksDialog(self.parent or self)
