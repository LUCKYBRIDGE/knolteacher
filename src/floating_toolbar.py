"""
스마트 올인원 플로팅 독 (Knol Smart Dock)
- 파편화되어 난립하던 미니 시간표, 티커, 퀵바를 단 하나의 정돈된 슬림 캡슐 독으로 대통합
- 애플 Dynamic Island 감성의 초슬림 미니멀 디자인 (높이 38px)
- 좌측 실시간 시간표/남은시간 티커 + 중앙 핵심 수업도구 리모컨 + 우측 도구 설정(⚙️) 및 최소화
- 12종 수업 도구 지원 및 도구 넣고 빼기(On/Off) 커스텀 설정 완벽 지원
"""
import os
import sys
import json
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
from src.config_utils import get_config_dir

# 12종 전체 도구 마스터 정의
ALL_DOCK_TOOLS = [
    {"key": "pen",       "icon": "pencil",      "name": "판서",       "desc": "화면 위 자유 판서 및 자/각도기 (Alt+2)"},
    {"key": "timer",     "icon": "flat_timer",  "name": "타이머",     "desc": "수업 모둠 타이머 (Alt+3)"},
    {"key": "visualizer","icon": "camera",      "name": "화상기",     "desc": "웹캠 / 실물화상기 실시간 뷰어"},
    {"key": "board",     "icon": "desktop",     "name": "보드",       "desc": "학생용 대형 놀티쳐 보드 (F2)"},
    {"key": "picker",    "icon": "flat_picker", "name": "추첨",       "desc": "학생 이름/번호 랜덤 뽑기"},
    {"key": "wheel",     "icon": "wheel",       "name": "돌림판",     "desc": "모둠/벌칙 행운의 돌림판"},
    {"key": "dice",      "icon": "flat_dice",   "name": "주사위",     "desc": "스마트 주사위 및 비/비율 통계"},
    {"key": "ladder",    "icon": "ladder",      "name": "사다리",     "desc": "학생/모둠 사다리타기 게임"},
    {"key": "pinball",   "icon": "pinball",     "name": "핀볼",       "desc": "물리 아케이드 핀볼 추첨기"},
    {"key": "mouse",     "icon": "mouse",       "name": "마우스",     "desc": "수업용 마우스 강조 설정"},
    {"key": "cleaner",   "icon": "broom",       "name": "정리",       "desc": "바탕화면 1초 파일 자동 정리"},
    {"key": "sites",     "icon": "globe",       "name": "사이트",     "desc": "교육 사이트 바로가기 모음"},
]

DEFAULT_ACTIVE_KEYS = ["pen", "timer", "visualizer", "board", "picker", "wheel"]


class DockConfigDialog(ctk.CTkToplevel):
    """스마트 독 도구 넣고 빼기(On/Off) 커스텀 설정 팝업"""
    def __init__(self, parent_dock):
        super().__init__(parent_dock)
        self.parent_dock = parent_dock
        self.title("스마트 독 도구 설정")
        self.geometry("380x480")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self._check_vars = {}
        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=12, border_width=1, border_color="#334155")
        container.pack(fill="both", expand=True, padx=8, pady=8)

        ctk.CTkLabel(
            container, text="🛠️ 스마트 독 표시 도구 설정",
            font=get_font(13, "bold"), text_color="#38bdf8"
        ).pack(anchor="w", padx=16, pady=(14, 2))

        ctk.CTkLabel(
            container, text="독에 항상 띄워둘 도구를 자유롭게 넣고 뺄 수 있습니다.",
            font=get_font(10), text_color="#94a3b8"
        ).pack(anchor="w", padx=16, pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(container, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=12, pady=4)

        active_keys = self.parent_dock.load_dock_config()

        for t_info in ALL_DOCK_TOOLS:
            k = t_info["key"]
            nm = t_info["name"]
            desc = t_info["desc"]
            ico_name = t_info["icon"]

            row = ctk.CTkFrame(scroll, fg_color="#1e293b", corner_radius=8)
            row.pack(fill="x", pady=3)

            var = ctk.BooleanVar(value=(k in active_keys))
            self._check_vars[k] = var

            chk = ctk.CTkCheckBox(
                row, text=f"{nm}  ({desc})", variable=var,
                font=get_font(10, "bold"), text_color="#f8fafc",
                fg_color="#0284c7", hover_color="#0369a1",
                checkbox_width=18, checkbox_height=18
            )
            chk.pack(side="left", padx=10, pady=8)

        # 하단 저장 버튼 바
        b_row = ctk.CTkFrame(container, fg_color="transparent")
        b_row.pack(fill="x", padx=16, pady=(8, 12))

        ctk.CTkButton(
            b_row, text="💾 설정 저장 & 즉시 적용", font=get_font(11, "bold"),
            fg_color="#0284c7", hover_color="#0369a1", height=32,
            command=self._save_and_apply
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(
            b_row, text="닫기", font=get_font(10, "bold"), width=60, height=32,
            fg_color="#334155", hover_color="#475569", command=self.destroy
        ).pack(side="right", padx=(4, 0))

    def _save_and_apply(self):
        new_keys = [k for k, v in self._check_vars.items() if v.get()]
        if not new_keys:
            new_keys = ["board"]  # 최소 1개는 유지
        self.parent_dock.save_dock_config(new_keys)
        self.parent_dock._build_ui()
        self.destroy()


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

        self.config_file = os.path.join(get_config_dir(), "smart_dock_config.json")
        self.is_pinned = True
        self.is_collapsed = False
        self.tb_height = 38
        self.collapsed_width = 160

        # 다른 파편화된 서브 위젯들 자동 정리
        self._cleanup_other_widgets()

        # 화면 상단 중앙 기본 배치
        sw = self.winfo_screenwidth()
        active_keys = self.load_dock_config()
        self.tb_width = self._calc_width(len(active_keys))
        x = (sw - self.tb_width) // 2
        y = 12
        self.geometry(f"{self.tb_width}x{self.tb_height}+{x}+{y}")

        self._build_ui()
        self._keep_topmost_loop()
        self._start_ticker_loop()

    def _calc_width(self, num_tools: int) -> int:
        # 교시 티커(약 190px) + 도구 버튼들(개당 약 32px) + 우측 컨트롤(약 70px) + 여백
        return max(420, 200 + num_tools * 34 + 80)

    def load_dock_config(self) -> list:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("active_tools", DEFAULT_ACTIVE_KEYS)
            except Exception:
                pass
        return list(DEFAULT_ACTIVE_KEYS)

    def save_dock_config(self, keys: list):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({"active_tools": keys}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Dock Config Save Error] {e}")

    def _cleanup_other_widgets(self):
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
        active_keys = self.load_dock_config()
        self.tb_width = self._calc_width(len(active_keys))
        self.geometry(f"{self.tb_width}x{self.tb_height}+{cur_x}+{cur_y}")

        capsule = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=19, border_width=1, border_color="#334155")
        capsule.pack(fill="both", expand=True)

        # 1. 좌측 드래그 핸들 & 실시간 교시 티커
        left_box = ctk.CTkFrame(capsule, fg_color="transparent")
        left_box.pack(side="left", padx=(10, 4), fill="y")
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
        ctk.CTkFrame(capsule, width=1, height=18, fg_color="#334155").pack(side="left", padx=5)

        # 2. 중앙 선택된 수업 도구 버튼 세트
        center_box = ctk.CTkFrame(capsule, fg_color="transparent")
        center_box.pack(side="left", fill="y", expand=True)

        tool_map = {t["key"]: t for t in ALL_DOCK_TOOLS}

        for k in active_keys:
            if k not in tool_map:
                continue
            t_data = tool_map[k]
            ico_name = t_data["icon"]
            name = t_data["name"]
            desc = t_data["desc"]

            btn = ctk.CTkButton(
                center_box, text="", image=get_icon(ico_name, "#ffffff", 14),
                width=28, height=26, fg_color="transparent", hover_color="#1e293b",
                corner_radius=6, command=lambda key=k: self._dispatch_tool(key)
            )
            btn.pack(side="left", padx=1)
            attach_tooltip(btn, f"{name}: {desc}")

        # 구분선
        ctk.CTkFrame(capsule, width=1, height=18, fg_color="#334155").pack(side="left", padx=5)

        # 3. 우측 컨트롤 (도구 넣고 빼기 ⚙️ / 접기 — / 닫기 ✕)
        right_box = ctk.CTkFrame(capsule, fg_color="transparent")
        right_box.pack(side="right", padx=(4, 10))

        # ⚙️ 도구 설정 버튼 (넣고 빼기)
        cfg_btn = ctk.CTkButton(
            right_box, text="", image=get_icon("settings", "#94a3b8", 12),
            width=22, height=22, fg_color="transparent", hover_color="#1e293b",
            corner_radius=4, command=self._open_dock_config
        )
        cfg_btn.pack(side="left", padx=1)
        attach_tooltip(cfg_btn, "스마트 독 표시 도구 넣고 빼기 (커스텀 설정)")

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

    def _open_dock_config(self):
        DockConfigDialog(self)

    def _dispatch_tool(self, key: str):
        if key == "pen":
            ScreenDrawingOverlay.get_instance(self).show()
        elif key == "timer":
            ClassroomToolsDialog.get_instance(self, initial_tab="timer")
        elif key == "visualizer":
            from src.visualizer_window import VisualizerWindow
            VisualizerWindow.get_instance(self)
        elif key == "board":
            from src.student_display import StudentDisplayWindow
            StudentDisplayWindow.get_instance(self)
        elif key == "picker":
            ClassroomToolsDialog.get_instance(self, initial_tab="picker")
        elif key == "wheel":
            ClassroomToolsDialog.get_instance(self, initial_tab="wheel")
        elif key == "dice":
            from src.student_display import StudentDisplayWindow
            w = StudentDisplayWindow.get_instance(self)
            w._switch_main_tool("dice")
        elif key == "ladder":
            ClassroomToolsDialog.get_instance(self, initial_tab="ladder")
        elif key == "pinball":
            ClassroomToolsDialog.get_instance(self, initial_tab="pinball")
        elif key == "mouse":
            import subprocess
            try: subprocess.run("start ms-settings:easeofaccess-mousepointer", shell=True, check=True)
            except Exception: pass
        elif key == "cleaner":
            from src.desktop_cleaner import desktop_cleaner
            desktop_cleaner.organize_desktop()
        elif key == "sites":
            if self.parent and hasattr(self.parent, "_open_site_bookmarks"):
                self.parent._open_site_bookmarks()

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
                    eh, em = map(int, et.split(":"))
                    remain_min = max(0, (eh * 60 + em) - (now.hour * 60 + now.minute))
                    return f"🔔 {p_name} {sub} ({remain_min}분 남음)"
            
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
                if hasattr(self, "ticker_btn") and self.ticker_btn.winfo_exists():
                    self.ticker_btn.configure(text=self._get_current_lesson_text())
                self.after(30000, _tick)
        self.after(30000, _tick)

    def _show_timetable_popover(self):
        pop = ctk.CTkToplevel(self)
        pop.title("오늘의 시간표")
        pop.geometry("260x300")
        pop.resizable(False, False)
        pop.attributes("-topmost", True)
        pop.configure(fg_color="#0f172a")

        ctk.CTkLabel(pop, text="📅 오늘 시간표", font=get_font(12, "bold"), text_color="#38bdf8").pack(pady=8)
        scroll = ctk.CTkScrollableFrame(pop, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=4)

        _, _, items = timetable_manager.get_today_schedule_items()
        for it in items:
            sub = "점심시간" if it.get("is_lunch") else it.get("subject", "")
            r = ctk.CTkFrame(scroll, fg_color="#1e293b", corner_radius=6)
            r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text=f"{it['name']} ({it['start']})", font=get_font(9), text_color="#94a3b8").pack(side="left", padx=6, pady=3)
            ctk.CTkLabel(r, text=sub, font=get_font(10, "bold"), text_color="#f8fafc").pack(side="right", padx=6)

    def _toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        self._build_ui()

    def _start_drag(self, event):
        self._drag_start_x = event.x_root - self.winfo_x()
        self._drag_start_y = event.y_root - self.winfo_y()

    def _on_drag(self, event):
        new_x = event.x_root - self._drag_start_x
        new_y = event.y_root - self._drag_start_y
        self.geometry(f"+{new_x}+{new_y}")

    def close(self):
        FloatingQuickToolbar._instance = None
        self.destroy()
