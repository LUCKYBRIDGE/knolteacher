"""
놀티쳐 보드 (KnolTeacher Board) - 스마트 클래스룸 스튜디오 대시보드
- 과한 3D 그래픽과 무거운 디자인을 완전히 걷어낸 미니멀 플랫(Minimalist Flat) 디자인
- 애플 SF Symbols / 노션 감성의 단정하고 간결한 2D 라인 심볼 세트 (18x18px)
- 테마 색상과 완벽하게 동기화되는 쾌적하고 눈이 편안한 소프트 슬레이트 & 칠판 팔레트
- 2단 분할 스튜디오 레이아웃:
  - [좌측 65% 메인 스테이지]: 수업 집중 도구 (대형 타이머, 발표자 추첨, 주사위, 돌림판, 점수판, 판서)
  - [우측 35% 교실 상시 허브]: 오늘의 시간표 + 오늘의 급식 + 학급 알림장 메모
"""

import os
import sys
import json
import time
import math
import random
import threading
import datetime
import winsound
import webbrowser
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from src.font_config import setup_global_fonts, get_font
from src.timetable_manager import timetable_manager, DAYS_KO
from src.neis_client import neis_client
from src.config_utils import get_config_dir
from src.icon_renderer import get_icon
from src.board_preset_manager import board_preset_manager
from src.custom_board_dialog import CustomBoardLaunchDialog

# 교실 TV 전용 눈이 편안한 테마 팔레트 (핫핑크 영구 퇴출)
THEMES = {
    "slate_dark": {
        "name": "소프트 슬레이트 다크 (추천)",
        "bg": "#0f172a",
        "card": "#1e293b",
        "card_inner": "#0f172a",
        "border": "#334155",
        "accent": "#38bdf8",
        "accent_hover": "#0284c7",
        "text_main": "#f8fafc",
        "text_sub": "#94a3b8"
    },
    "chalkboard": {
        "name": "스마트 칠판 딥그린",
        "bg": "#12231b",
        "card": "#1a3529",
        "card_inner": "#12231b",
        "border": "#284e3e",
        "accent": "#34d399",
        "accent_hover": "#10b981",
        "text_main": "#f8fafc",
        "text_sub": "#a7f3d0"
    },
    "warm_beige": {
        "name": "모던 웜베이지 (주간용)",
        "bg": "#f4f1eb",
        "card": "#ffffff",
        "card_inner": "#fbfaf8",
        "border": "#e5e0d8",
        "accent": "#ea580c",
        "accent_hover": "#c2410c",
        "text_main": "#1e293b",
        "text_sub": "#64748b"
    },
    "indigo_night": {
        "name": "오션 딥인디고",
        "bg": "#0a1128",
        "card": "#141f42",
        "card_inner": "#0a1128",
        "border": "#233362",
        "accent": "#60a5fa",
        "accent_hover": "#3b82f6",
        "text_main": "#f8fafc",
        "text_sub": "#93c5fd"
    }
}

class StudentDisplayWindow(ctk.CTkToplevel):
    _instance = None
    CONFIG_FILE = os.path.join(get_config_dir(), "student_board_config.json")

    @classmethod
    def get_instance(cls, parent=None, custom_config: dict = None):
        if cls._instance is None or not cls._instance.winfo_exists():
            cls._instance = cls(parent, custom_config)
        else:
            if custom_config:
                cls._instance.apply_custom_config(custom_config)
            cls._instance.deiconify()
            cls._instance.lift()
            cls._instance.focus_force()
        return cls._instance

    def __init__(self, parent=None, custom_config: dict = None):
        super().__init__(parent)
        self.parent_app = parent
        self.title("놀티쳐 보드 (스마트 교실 스튜디오 대시보드)")
        self.geometry("1280x820")
        self.minsize(960, 640)
        self.resizable(True, True)

        setup_global_fonts(self)
        self._load_icon()

        self.is_fullscreen = False
        
        # 활성 프리셋 설정 로드
        active_preset_cfg = board_preset_manager.get_active_preset()
        self.custom_config = custom_config or {}
        self.theme_key = self.custom_config.get("theme_key") or active_preset_cfg.get("theme_key", "slate_dark")
        self.active_tool = self.custom_config.get("active_tool") or active_preset_cfg.get("active_tool", "timer")

        # 타이머 상태
        self.timer_seconds = 300
        self.timer_total = 300
        self.timer_running = False
        self.timer_type = "digital"
        self.timer_job = None

        # 주사위 상태
        self.dice_val = 6

        # 돌림판 상태
        self.wheel_items = ["1모둠", "2모둠", "3모둠", "4모둠", "5모둠", "6모둠"]
        self.wheel_spinning = False

        # 점수판 상태
        self.scores = {"1모둠": 0, "2모둠": 0, "3모둠": 0, "4모둠": 0, "5모둠": 0, "6모둠": 0}

        self._load_config()

        self.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._exit_fullscreen())
        self.protocol("WM_DELETE_WINDOW", self.close)

        self._build_ui()
        self._start_clock_loop()

        from src.timetable_manager import timetable_manager
        timetable_manager.add_listener(self._on_timetable_changed)

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def _load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.theme_key = data.get("theme_key", "slate_dark")
                    if self.theme_key not in THEMES:
                        self.theme_key = "slate_dark"
                    self.scores = data.get("scores", self.scores)
            except Exception:
                pass

    def _save_config(self):
        try:
            data = {
                "theme_key": self.theme_key,
                "scores": self.scores
            }
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _t(self):
        return THEMES.get(self.theme_key, THEMES["slate_dark"])

    # ══════════════════════════════════════════════════════════════════════════
    # 전체 메인 UI: 단순하고 단정한 미니멀 스튜디오 대시보드
    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        t = self._t()
        self.configure(fg_color=t["bg"])

        # 1. 상단 스마트 헤더 바 (높이 54px, 단정한 1px 보더)
        top_bar = ctk.CTkFrame(self, fg_color=t["card"], corner_radius=10, height=54, border_width=1, border_color=t["border"])
        top_bar.pack(fill="x", padx=16, pady=(12, 10))
        top_bar.pack_propagate(False)

        # [좌측] 브랜드 & 실시간 시계
        l_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        l_box.pack(side="left", padx=14)

        ctk.CTkLabel(l_box, text="놀티쳐 보드", font=get_font(15, "bold"), text_color=t["accent"]).pack(side="left")
        ctk.CTkFrame(l_box, width=1, height=18, fg_color=t["border"]).pack(side="left", padx=12)

        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]
        self.clock_lbl = ctk.CTkLabel(
            l_box,
            text=f"{today.strftime('%m/%d')} ({weekday_str})  --:--:--",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=t["text_sub"]
        )
        self.clock_lbl.pack(side="left")

        # [중앙] 단순화된 미니멀 플랫 라인 도구 전환 바 (18x18px 심볼)
        c_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        c_box.pack(side="left", fill="x", expand=True, padx=10)

        tools = [
            ("timer", "flat_timer", "타이머"),
            ("picker", "flat_picker", "발표자 추첨"),
            ("dice", "flat_dice", "주사위"),
            ("wheel", "flat_wheel", "돌림판"),
            ("scoreboard", "flat_trophy", "점수판"),
            ("drawing", "flat_pen", "학급 판서"),
        ]

        self.tool_buttons = {}
        for key, sym_key, name in tools:
            is_active = self.active_tool == key
            ico_col = "#0f172a" if (is_active and t["bg"] != "#f4f1eb") else (t["accent"] if is_active else t["text_sub"])
            ico = get_icon(sym_key, ico_col, 18)

            btn = ctk.CTkButton(
                c_box,
                text=f"  {name}",
                image=ico,
                compound="left",
                font=get_font(11, "bold"),
                fg_color=t["accent"] if is_active else t["card_inner"],
                hover_color=t["accent_hover"],
                text_color="#0f172a" if (is_active and t["bg"] != "#f4f1eb") else (t["text_main"]),
                height=34,
                corner_radius=8,
                command=lambda k=key: self._switch_main_tool(k)
            )
            btn.pack(side="left", padx=3, fill="x", expand=True)
            self.tool_buttons[key] = (btn, sym_key)

        # [우측] 프리셋 스위처, 테마, 전체화면, 닫기
        r_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        r_box.pack(side="right", padx=12)

        # 🎛️ 프리셋 프로필 선택 드롭다운
        preset_names = board_preset_manager.get_preset_names()
        cur_preset = board_preset_manager.get_active_preset_name()
        
        self.preset_combo = ctk.CTkComboBox(
            r_box,
            values=preset_names,
            width=135,
            height=32,
            font=get_font(10, "bold"),
            dropdown_font=get_font(10),
            state="readonly",
            command=self._on_preset_changed
        )
        self.preset_combo.set(cur_preset)
        self.preset_combo.pack(side="left", padx=3)

        # ⚙️ 프리셋 관리 다이얼로그 버튼
        gear_ico = get_icon("settings", t["text_main"], 15)
        ctk.CTkButton(
            r_box, text="", image=gear_ico, width=32, height=32,
            fg_color=t["card_inner"], hover_color=t["border"], text_color=t["text_main"],
            corner_radius=6, command=self._open_preset_manager_dialog
        ).pack(side="left", padx=(0, 4))

        theme_ico = get_icon("theme", t["text_main"], 16)
        ctk.CTkButton(
            r_box, text=" 테마", image=theme_ico, compound="left", width=64, height=32, font=get_font(10, "bold"),
            fg_color=t["card_inner"], hover_color=t["border"], text_color=t["text_main"],
            corner_radius=6, command=self._open_theme_picker
        ).pack(side="left", padx=2)

        fs_ico = get_icon("fullscreen", "#0f172a" if t["bg"] != "#f4f1eb" else "#ffffff", 16)
        self.fs_btn = ctk.CTkButton(
            r_box, text=" 전체화면", image=fs_ico, compound="left", width=80, height=32, font=get_font(10, "bold"),
            fg_color=t["accent"], hover_color=t["accent_hover"],
            text_color="#0f172a" if t["bg"] != "#f4f1eb" else "#ffffff",
            corner_radius=6, command=self._toggle_fullscreen
        )
        self.fs_btn.pack(side="left", padx=2)

        close_ico = get_icon("close", "#ffffff", 14)
        ctk.CTkButton(
            r_box, text="", image=close_ico, width=32, height=32,
            fg_color="#dc2626", hover_color="#b91c1c",
            corner_radius=6, command=self.close
        ).pack(side="left", padx=2)

        # 2. 메인 바디: 커스텀 레이아웃 모드 지원 (standard / focus_tool / board_only)
        layout_mode = self.custom_config.get("layout_mode", "standard")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        if layout_mode == "focus_tool":
            # 🎯 수업 도구 집중 풀화면 모드 (우측 허브 완전 숨김)
            self.stage_frame = ctk.CTkFrame(
                body, fg_color=t["card"], corner_radius=12, border_width=1, border_color=t["border"]
            )
            self.stage_frame.pack(fill="both", expand=True)
            self.hub_frame = None
            self._render_active_tool()
        elif layout_mode == "board_only":
            # 📋 학급 게시판 전면 모드 (시간표+급식+알림장 3열 대형 카드)
            self.stage_frame = None
            self.hub_frame = ctk.CTkFrame(body, fg_color="transparent")
            self.hub_frame.pack(fill="both", expand=True)
            self._render_board_only_content(t)
        else:
            # ⚖️ 표준 2단 분할 모드 (도구 65% + 교실 허브 35%)
            self.stage_frame = ctk.CTkFrame(
                body, fg_color=t["card"], corner_radius=12, border_width=1, border_color=t["border"]
            )
            self.stage_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

            self.hub_frame = ctk.CTkFrame(body, fg_color="transparent", width=400)
            self.hub_frame.pack(side="right", fill="both", padx=(8, 0))
            self.hub_frame.pack_propagate(False)

            self._render_active_tool()
            self._render_hub_content()

    def _switch_main_tool(self, tool_key: str):
        self.active_tool = tool_key
        t = self._t()
        for k, (btn, sym_key) in self.tool_buttons.items():
            is_active = k == tool_key
            ico_col = "#0f172a" if (is_active and t["bg"] != "#f4f1eb") else (t["accent"] if is_active else t["text_sub"])
            ico = get_icon(sym_key, ico_col, 18)
            btn.configure(
                image=ico,
                fg_color=t["accent"] if is_active else t["card_inner"],
                text_color="#0f172a" if (is_active and t["bg"] != "#f4f1eb") else (t["text_main"])
            )
        self._render_active_tool()

    def _render_active_tool(self):
        for w in self.stage_frame.winfo_children():
            w.destroy()

        t = self._t()
        if self.active_tool == "timer":
            self._build_stage_timer(t)
        elif self.active_tool == "picker":
            self._build_stage_picker(t)
        elif self.active_tool == "dice":
            self._build_stage_dice(t)
        elif self.active_tool == "wheel":
            self._build_stage_wheel(t)
        elif self.active_tool == "scoreboard":
            self._build_stage_scoreboard(t)
        elif self.active_tool == "drawing":
            self._build_stage_drawing(t)

    # ── 1. 메인 스테이지: 수업 타이머 ──
    def _build_stage_timer(self, t: dict):
        header = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))

        ico = get_icon("flat_timer", t["accent"], 22)
        ctk.CTkLabel(header, text="  수업 집중 타이머", image=ico, compound="left", font=get_font(14, "bold"), text_color=t["accent"]).pack(side="left")

        # 타이머 모드 칩
        modes = [("디지털", "digital"), ("스톱워치", "stopwatch")]
        for m_name, m_key in modes:
            is_sel = self.timer_type == m_key
            ctk.CTkButton(
                header, text=m_name, width=64, height=28, font=get_font(10, "bold"),
                fg_color=t["accent"] if is_sel else t["card_inner"],
                text_color="#0f172a" if (is_sel and t["bg"] != "#f4f1eb") else t["text_main"],
                corner_radius=6, command=lambda k=m_key: self._set_timer_mode(k)
            ).pack(side="right", padx=2)

        disp = ctk.CTkFrame(self.stage_frame, fg_color=t["card_inner"], corner_radius=12, border_width=1, border_color=t["border"])
        disp.pack(fill="both", expand=True, padx=24, pady=10)

        m = self.timer_seconds // 60
        s = self.timer_seconds % 60
        self.stage_timer_lbl = ctk.CTkLabel(
            disp, text=f"{m:02d}:{s:02d}",
            font=ctk.CTkFont(family="Consolas", size=96, weight="bold"),
            text_color=t["accent"]
        )
        self.stage_timer_lbl.pack(expand=True)

        # 프리셋 칩 (단순한 1클릭 칩)
        p_row = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        p_row.pack(fill="x", padx=24, pady=(0, 12))
        for mins in [1, 3, 5, 10, 15, 20]:
            ctk.CTkButton(
                p_row, text=f"{mins}분", font=get_font(11, "bold"),
                height=32, fg_color=t["card_inner"], hover_color=t["border"],
                text_color=t["text_main"], corner_radius=6,
                command=lambda m=mins: self._preset_timer(m * 60)
            ).pack(side="left", fill="x", expand=True, padx=3)

        ctrl_bar = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        ctrl_bar.pack(fill="x", padx=24, pady=(0, 24))

        play_ico = get_icon("play", "#ffffff", 16)
        self.stage_timer_btn = ctk.CTkButton(
            ctrl_bar, text=" 수업 타이머 시작", image=play_ico, compound="left", font=get_font(14, "bold"),
            fg_color="#10b981", hover_color="#059669", text_color="#ffffff",
            height=44, corner_radius=8, command=self._toggle_timer_run
        )
        self.stage_timer_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        reset_ico = get_icon("reset", t["text_main"], 16)
        ctk.CTkButton(
            ctrl_bar, text=" 리셋", image=reset_ico, compound="left", font=get_font(13, "bold"),
            fg_color=t["card_inner"], hover_color=t["border"], text_color=t["text_main"],
            height=44, width=100, corner_radius=8, command=self._reset_timer
        ).pack(side="right")

    def _set_timer_mode(self, mode_key: str):
        self.timer_type = mode_key
        self._render_active_tool()

    def _preset_timer(self, secs: int):
        self.timer_seconds = secs
        self.timer_total = secs
        self._update_timer_disp()

    def _toggle_timer_run(self):
        self.timer_running = not self.timer_running
        if self.timer_running:
            pause_ico = get_icon("pause", "#ffffff", 16)
            self.stage_timer_btn.configure(text=" 일시정지", image=pause_ico, fg_color="#f59e0b", hover_color="#d97706")
            self._run_timer_tick()
        else:
            play_ico = get_icon("play", "#ffffff", 16)
            self.stage_timer_btn.configure(text=" 수업 타이머 시작", image=play_ico, fg_color="#10b981", hover_color="#059669")
            if self.timer_job:
                self.after_cancel(self.timer_job)

    def _run_timer_tick(self):
        if not self.timer_running:
            return
        if self.timer_type == "stopwatch":
            self.timer_seconds += 1
        else:
            if self.timer_seconds > 0:
                self.timer_seconds -= 1
            else:
                self.timer_running = False
                play_ico = get_icon("play", "#ffffff", 16)
                self.stage_timer_btn.configure(text=" 수업 타이머 시작", image=play_ico, fg_color="#10b981")
                threading.Thread(target=lambda: winsound.Beep(1200, 800), daemon=True).start()
                messagebox.showinfo("타이머 종료", "지정된 활동 시간이 종료되었습니다!")
                return
        self._update_timer_disp()
        self.timer_job = self.after(1000, self._run_timer_tick)

    def _reset_timer(self):
        self.timer_running = False
        if self.timer_job:
            self.after_cancel(self.timer_job)
        self.timer_seconds = self.timer_total if self.timer_type != "stopwatch" else 0
        if hasattr(self, "stage_timer_btn") and self.stage_timer_btn.winfo_exists():
            play_ico = get_icon("play", "#ffffff", 16)
            self.stage_timer_btn.configure(text=" 수업 타이머 시작", image=play_ico, fg_color="#10b981")
        self._update_timer_disp()

    def _update_timer_disp(self):
        if hasattr(self, "stage_timer_lbl") and self.stage_timer_lbl.winfo_exists():
            m = self.timer_seconds // 60
            s = self.timer_seconds % 60
            self.stage_timer_lbl.configure(text=f"{m:02d}:{s:02d}")

    # ── 2. 메인 스테이지: 발표자 추첨 ──
    def _build_stage_picker(self, t: dict):
        header = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))

        ico = get_icon("flat_picker", t["accent"], 22)
        ctk.CTkLabel(header, text="  학생 발표자 랜덤 추첨", image=ico, compound="left", font=get_font(14, "bold"), text_color=t["accent"]).pack(side="left")

        disp = ctk.CTkFrame(self.stage_frame, fg_color=t["card_inner"], corner_radius=12, border_width=1, border_color=t["border"])
        disp.pack(fill="both", expand=True, padx=24, pady=10)

        self.stage_pick_num = ctk.CTkLabel(
            disp, text="READY", font=ctk.CTkFont(family="Consolas", size=88, weight="bold"), text_color=t["accent"]
        )
        self.stage_pick_num.pack(expand=True, pady=(20, 0))

        self.stage_pick_sub = ctk.CTkLabel(
            disp, text="아래 [발표자 추첨하기] 버튼을 눌러주세요", font=get_font(13), text_color=t["text_sub"]
        )
        self.stage_pick_sub.pack(pady=(0, 24))

        b_box = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        b_box.pack(fill="x", padx=24, pady=(0, 24))

        cfg_box = ctk.CTkFrame(b_box, fg_color=t["card_inner"], corner_radius=8, height=44)
        cfg_box.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(cfg_box, text="학생 번호:", font=get_font(11, "bold"), text_color=t["text_main"]).pack(side="left", padx=(10, 4))
        self.pick_min = ctk.CTkEntry(cfg_box, width=44, font=get_font(11, "bold"), justify="center")
        self.pick_min.insert(0, "1")
        self.pick_min.pack(side="left", padx=2)
        ctk.CTkLabel(cfg_box, text="~", font=get_font(11), text_color=t["text_main"]).pack(side="left")
        self.pick_max = ctk.CTkEntry(cfg_box, width=44, font=get_font(11, "bold"), justify="center")
        self.pick_max.insert(0, "25")
        self.pick_max.pack(side="left", padx=(2, 10))

        ctk.CTkButton(
            b_box, text="발표자 추첨하기", font=get_font(14, "bold"),
            fg_color=t["accent"], hover_color=t["accent_hover"],
            text_color="#0f172a" if t["bg"] != "#f4f1eb" else "#ffffff",
            height=44, corner_radius=8, command=self._do_stage_pick
        ).pack(side="left", fill="x", expand=True)

    def _do_stage_pick(self):
        try:
            s_min = int(self.pick_min.get())
            s_max = int(self.pick_max.get())
        except Exception:
            s_min, s_max = 1, 25

        def _anim(count):
            if count > 0:
                val = random.randint(s_min, s_max)
                self.stage_pick_num.configure(text=f"{val} 번", text_color="#f59e0b")
                self.stage_pick_sub.configure(text="추첨 중...")
                self.after(50, lambda: _anim(count - 1))
            else:
                final_val = random.randint(s_min, s_max)
                self.stage_pick_num.configure(text=f"{final_val} 번", text_color="#10b981")
                self.stage_pick_sub.configure(text="오늘의 발표 주인공입니다!")
                threading.Thread(target=lambda: winsound.Beep(1400, 300), daemon=True).start()
        _anim(16)

    # ── 3. 메인 스테이지: 주사위 ──
    def _build_stage_dice(self, t: dict):
        header = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))

        ico = get_icon("flat_dice", t["accent"], 22)
        ctk.CTkLabel(header, text="  대형 3D 주사위", image=ico, compound="left", font=get_font(14, "bold"), text_color=t["accent"]).pack(side="left")

        disp = ctk.CTkFrame(self.stage_frame, fg_color=t["card_inner"], corner_radius=12, border_width=1, border_color=t["border"])
        disp.pack(fill="both", expand=True, padx=24, pady=10)

        dice_chars = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
        self.stage_dice_lbl = ctk.CTkLabel(
            disp, text=f"{dice_chars.get(self.dice_val, '⚅')}  {self.dice_val}",
            font=ctk.CTkFont(family="Segoe UI Symbol", size=96, weight="bold"), text_color="#f59e0b"
        )
        self.stage_dice_lbl.pack(expand=True)

        b_box = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        b_box.pack(fill="x", padx=24, pady=(0, 24))

        ctk.CTkButton(
            b_box, text="주사위 굴리기", font=get_font(14, "bold"),
            fg_color="#d97706", hover_color="#b45309", text_color="#ffffff",
            height=44, corner_radius=8, command=self._do_stage_dice
        ).pack(fill="x")

    def _do_stage_dice(self):
        dice_chars = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
        def _anim(step):
            if step > 0:
                v = random.randint(1, 6)
                self.stage_dice_lbl.configure(text=f"{dice_chars[v]}  {v}")
                self.after(50, lambda: _anim(step - 1))
            else:
                v = random.randint(1, 6)
                self.dice_val = v
                self.stage_dice_lbl.configure(text=f"{dice_chars[v]}  {v}")
                threading.Thread(target=lambda: winsound.Beep(1100, 200), daemon=True).start()
        _anim(14)

    # ── 4. 메인 스테이지: 돌림판 ──
    def _build_stage_wheel(self, t: dict):
        header = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))

        ico = get_icon("flat_wheel", t["accent"], 22)
        ctk.CTkLabel(header, text="  모둠 돌림판", image=ico, compound="left", font=get_font(14, "bold"), text_color=t["accent"]).pack(side="left")

        disp = ctk.CTkFrame(self.stage_frame, fg_color=t["card_inner"], corner_radius=12, border_width=1, border_color=t["border"])
        disp.pack(fill="both", expand=True, padx=24, pady=10)

        self.stage_wheel_lbl = ctk.CTkLabel(
            disp, text="1모둠", font=get_font(36, "bold"), text_color=t["accent"]
        )
        self.stage_wheel_lbl.pack(expand=True)

        b_box = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        b_box.pack(fill="x", padx=24, pady=(0, 24))

        ctk.CTkButton(
            b_box, text="돌림판 회전하기", font=get_font(14, "bold"),
            fg_color=t["accent"], hover_color=t["accent_hover"],
            text_color="#0f172a" if t["bg"] != "#f4f1eb" else "#ffffff",
            height=44, corner_radius=8, command=self._do_stage_wheel
        ).pack(fill="x")

    def _do_stage_wheel(self):
        def _anim(step):
            if step > 0:
                itm = random.choice(self.wheel_items)
                self.stage_wheel_lbl.configure(text=itm, text_color="#f59e0b")
                self.after(50, lambda: _anim(step - 1))
            else:
                itm = random.choice(self.wheel_items)
                self.stage_wheel_lbl.configure(text=f"{itm} 당첨!", text_color="#10b981")
                threading.Thread(target=lambda: winsound.Beep(1300, 300), daemon=True).start()
        _anim(16)

    # ── 5. 메인 스테이지: 모둠 점수판 ──
    def _build_stage_scoreboard(self, t: dict):
        header = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))

        ico = get_icon("flat_trophy", t["accent"], 22)
        ctk.CTkLabel(header, text="  모둠 점수판", image=ico, compound="left", font=get_font(14, "bold"), text_color=t["accent"]).pack(side="left")

        grid_box = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        grid_box.pack(fill="both", expand=True, padx=24, pady=10)

        for i in range(2):
            grid_box.grid_rowconfigure(i, weight=1)
        for j in range(3):
            grid_box.grid_columnconfigure(j, weight=1)

        groups = list(self.scores.keys())
        for idx, g in enumerate(groups[:6]):
            r = idx // 3
            c = idx % 3

            cell = ctk.CTkFrame(grid_box, fg_color=t["card_inner"], corner_radius=10, border_width=1, border_color=t["border"])
            cell.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

            ctk.CTkLabel(cell, text=g, font=get_font(13, "bold"), text_color=t["text_main"]).pack(pady=(12, 4))
            score_lbl = ctk.CTkLabel(cell, text=f"{self.scores[g]}점", font=ctk.CTkFont(family="Consolas", size=32, weight="bold"), text_color="#f59e0b")
            score_lbl.pack(pady=4)

            btn_box = ctk.CTkFrame(cell, fg_color="transparent")
            btn_box.pack(pady=(4, 12))

            ctk.CTkButton(
                btn_box, text="+1", width=44, height=30, font=get_font(11, "bold"), fg_color="#10b981",
                corner_radius=6, command=lambda grp=g: self._add_score(grp, 1)
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                btn_box, text="-1", width=44, height=30, font=get_font(11, "bold"), fg_color="#dc2626",
                corner_radius=6, command=lambda grp=g: self._add_score(grp, -1)
            ).pack(side="left", padx=2)

    def _add_score(self, g: str, delta: int):
        self.scores[g] = max(0, self.scores.get(g, 0) + delta)
        self._render_active_tool()
        self._save_config()

    # ── 6. 메인 스테이지: 학급 판서 ──
    def _build_stage_drawing(self, t: dict):
        header = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))

        ico = get_icon("flat_pen", t["accent"], 22)
        ctk.CTkLabel(header, text="  학급 판서 & 화면 펜", image=ico, compound="left", font=get_font(14, "bold"), text_color=t["accent"]).pack(side="left")

        btn_box = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        btn_box.pack(fill="x", padx=24, pady=(0, 10))

        ctk.CTkButton(
            btn_box, text="화면 위 자유 판서 펜 실행", font=get_font(12, "bold"), fg_color="#ea580c",
            hover_color="#c2410c", height=38, corner_radius=8,
            command=lambda: getattr(self.parent_app, "_open_screen_drawing", lambda: None)()
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            btn_box, text="스마트 플로팅 퀵바", font=get_font(12, "bold"), fg_color=t["accent"],
            hover_color=t["accent_hover"], text_color="#0f172a" if t["bg"] != "#f4f1eb" else "#ffffff",
            height=38, corner_radius=8,
            command=lambda: getattr(self.parent_app, "_open_floating_bar", lambda: None)()
        ).pack(side="left", fill="x", expand=True)

        txt_box = ctk.CTkTextbox(
            self.stage_frame, font=get_font(14), fg_color=t["card_inner"], text_color=t["text_main"],
            corner_radius=10, border_width=1, border_color=t["border"]
        )
        txt_box.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        txt_box.insert("1.0", "[오늘 배울 내용]\n\n1. 수학 3단원: 소수의 나눗셈 원리 알기\n2. 국어 4단원: 작품 속 인물의 마음 짐작하기\n3. 모둠별 토의 활동 및 배움 공책 정리하기")

    # ══════════════════════════════════════════════════════════════════════════
    # 우측 상시 교실 허브 (시간표 + 급식 + 알림장)
    # ══════════════════════════════════════════════════════════════════════════
    def _render_hub_content(self):
        if not self.hub_frame:
            return
        for w in self.hub_frame.winfo_children():
            w.destroy()

        t = self._t()
        show_tt = self.custom_config.get("show_timetable", True)
        show_ml = self.custom_config.get("show_meal", True)
        show_mm = self.custom_config.get("show_memo", True)

        if show_tt:
            self._build_timetable_card(self.hub_frame, t)
        if show_ml:
            self._build_meal_card(self.hub_frame, t)
        if show_mm:
            self._build_memo_card(self.hub_frame, t)

    def _build_timetable_card(self, parent, t: dict):
        tt_card = ctk.CTkFrame(parent, fg_color=t["card"], corner_radius=10, border_width=1, border_color=t["border"])
        tt_card.pack(fill="both", expand=True, pady=(0, 10))

        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]
        tt_hdr = ctk.CTkFrame(tt_card, fg_color="transparent")
        tt_hdr.pack(fill="x", padx=12, pady=(10, 4))

        tt_ico = get_icon("flat_timetable", t["accent"], 18)
        ctk.CTkLabel(tt_hdr, text="  오늘의 시간표", image=tt_ico, compound="left", font=get_font(12, "bold"), text_color=t["accent"]).pack(side="left")
        ctk.CTkLabel(tt_hdr, text=f"{today.strftime('%m/%d')} ({weekday_str})", font=get_font(10), text_color=t["text_sub"]).pack(side="right")

        is_hol, hol_name, items = timetable_manager.get_today_schedule_items()
        tt_box = ctk.CTkScrollableFrame(tt_card, fg_color="transparent", height=150)
        tt_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        if not items:
            ctk.CTkLabel(tt_box, text="등록된 수업 시간표가 없습니다.", font=get_font(10), text_color=t["text_sub"]).pack(pady=10)
        else:
            for itm in items[:7]:
                p_str = itm.get("period_str", "") or itm.get("name", "")
                sub = itm.get("subject", "")
                t_str = itm.get("start", "")

                row = ctk.CTkFrame(tt_box, fg_color=t["card_inner"], corner_radius=6)
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=p_str, font=get_font(10, "bold"), text_color="#f59e0b", width=44).pack(side="left", padx=6, pady=4)
                ctk.CTkLabel(row, text=sub, font=get_font(11, "bold"), text_color=t["text_main"]).pack(side="left", padx=4)
                ctk.CTkLabel(row, text=t_str, font=ctk.CTkFont(family="Consolas", size=9), text_color=t["text_sub"]).pack(side="right", padx=8)

    def _build_meal_card(self, parent, t: dict):
        meal_card = ctk.CTkFrame(parent, fg_color=t["card"], corner_radius=10, border_width=1, border_color=t["border"])
        meal_card.pack(fill="both", expand=True, pady=(0, 10))

        today = datetime.date.today()
        ok, meal_info, msg = neis_client.get_meal_for_date(today)
        school_nm = neis_client.config.get("school_name", "학교 미설정")

        m_hdr = ctk.CTkFrame(meal_card, fg_color="transparent")
        m_hdr.pack(fill="x", padx=12, pady=(10, 4))

        m_ico = get_icon("flat_meal", t["accent"], 18)
        ctk.CTkLabel(m_hdr, text="  오늘의 급식", image=m_ico, compound="left", font=get_font(12, "bold"), text_color=t["accent"]).pack(side="left")
        ctk.CTkLabel(m_hdr, text=school_nm, font=get_font(9), text_color=t["text_sub"]).pack(side="right")

        m_box = ctk.CTkScrollableFrame(meal_card, fg_color="transparent", height=130)
        m_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        dishes = meal_info.get("dishes", []) if (ok and meal_info) else []
        if not dishes:
            ctk.CTkLabel(m_box, text="등록된 급식 식단이 없습니다.", font=get_font(10), text_color=t["text_sub"]).pack(pady=10)
        else:
            for d in dishes:
                row = ctk.CTkFrame(m_box, fg_color=t["card_inner"], corner_radius=6)
                row.pack(fill="x", pady=2)
                ctk.CTkLabel(row, text=f"• {d}", font=get_font(10), text_color=t["text_main"]).pack(anchor="w", padx=8, pady=3)

    def _build_memo_card(self, parent, t: dict):
        memo_card = ctk.CTkFrame(parent, fg_color=t["card"], corner_radius=10, border_width=1, border_color=t["border"])
        memo_card.pack(fill="both", expand=True)

        mem_hdr = ctk.CTkFrame(memo_card, fg_color="transparent")
        mem_hdr.pack(fill="x", padx=12, pady=(10, 4))

        memo_ico = get_icon("flat_memo", t["accent"], 18)
        ctk.CTkLabel(mem_hdr, text="  학급 알림장 메모", image=memo_ico, compound="left", font=get_font(12, "bold"), text_color=t["accent"]).pack(side="left")

        txt = ctk.CTkTextbox(memo_card, font=get_font(11), fg_color=t["card_inner"], text_color=t["text_main"], corner_radius=6)
        txt.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        txt.insert("1.0", "1. 내일 준비물: 수학익힘책, 미술 색연필\n2. 안내장 부모님 확인 서명\n3. 하교 시 신호등 잘 건너기")

    def _open_theme_picker(self):
        pop = ctk.CTkToplevel(self)
        pop.title("테마 선택")
        pop.geometry("280x240")
        pop.resizable(False, False)
        pop.attributes("-topmost", True)
        t = self._t()
        pop.configure(fg_color=t["card"])

        ctk.CTkLabel(pop, text="교실 보드 테마 선택", font=get_font(12, "bold"), text_color=t["accent"]).pack(pady=(14, 8))

        for key, cfg in THEMES.items():
            f = ctk.CTkFrame(pop, fg_color="transparent")
            f.pack(fill="x", padx=14, pady=3)

            ctk.CTkFrame(f, width=22, height=22, fg_color=cfg["bg"], corner_radius=4, border_width=1, border_color="#64748b").pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                f, text=cfg["name"], font=get_font(10, "bold"), anchor="w", height=30,
                fg_color=t["accent"] if self.theme_key == key else t["card_inner"],
                text_color="#0f172a" if (self.theme_key == key and t["bg"] != "#f4f1eb") else t["text_main"],
                corner_radius=6, command=lambda k=key, p=pop: (self._set_theme(k), p.destroy())
            ).pack(side="left", fill="x", expand=True)

    def _set_theme(self, k: str):
        self.theme_key = k
        self._build_ui()
        self._save_config()

    def _start_clock_loop(self):
        def _tick():
            if self.winfo_exists():
                now = datetime.datetime.now()
                today = now.date()
                weekday_str = DAYS_KO[today.weekday()]
                time_str = now.strftime("%H:%M:%S")
                if hasattr(self, "clock_lbl") and self.clock_lbl.winfo_exists():
                    self.clock_lbl.configure(text=f"{today.strftime('%m/%d')} ({weekday_str})  {time_str}")
                self.after(1000, _tick)
        _tick()

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        if hasattr(self, "fs_btn") and self.fs_btn.winfo_exists():
            self.fs_btn.configure(text=" 창 모드" if self.is_fullscreen else " 전체화면")

    def _exit_fullscreen(self):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.attributes("-fullscreen", False)
            if hasattr(self, "fs_btn") and self.fs_btn.winfo_exists():
                self.fs_btn.configure(text=" 전체화면")

    def _on_timetable_changed(self):
        self._render_hub_content()

    def close(self):
        StudentDisplayWindow._instance = None
        self.destroy()


    def _on_preset_changed(self, choice: str):
        board_preset_manager.set_active_preset(choice)
        cfg = board_preset_manager.get_active_preset()
        self.theme_key = cfg.get("theme_key", self.theme_key)
        self.active_tool = cfg.get("active_tool", self.active_tool)
        self._build_ui()

    def _open_preset_manager_dialog(self):
        BoardPresetDialog(self)


    def apply_custom_config(self, cfg: dict):
        self.custom_config = cfg
        if cfg.get("theme_key"):
            self.theme_key = cfg["theme_key"]
        if cfg.get("active_tool"):
            self.active_tool = cfg["active_tool"]
        
        if cfg.get("compact_size"):
            self.geometry("960x640")
        elif not cfg.get("is_fullscreen"):
            self.geometry("1280x820")

        if cfg.get("is_fullscreen") and not self.is_fullscreen:
            self._toggle_fullscreen()
        elif not cfg.get("is_fullscreen") and self.is_fullscreen:
            self._exit_fullscreen()

        self._build_ui()

    def _render_board_only_content(self, t: dict):
        row = ctk.CTkFrame(self.hub_frame, fg_color="transparent")
        row.pack(fill="both", expand=True)

        col1 = ctk.CTkFrame(row, fg_color="transparent")
        col1.pack(side="left", fill="both", expand=True, padx=4)
        col2 = ctk.CTkFrame(row, fg_color="transparent")
        col2.pack(side="left", fill="both", expand=True, padx=4)
        col3 = ctk.CTkFrame(row, fg_color="transparent")
        col3.pack(side="left", fill="both", expand=True, padx=4)

        self._build_timetable_card(col1, t)
        self._build_meal_card(col2, t)
        self._build_memo_card(col3, t)

    def _open_preset_manager_dialog(self):
        CustomBoardLaunchDialog(self, self.apply_custom_config)


class BoardPresetDialog(ctk.CTkToplevel):
    def __init__(self, parent_board):
        super().__init__(parent_board)
        self.board = parent_board
        self.title("놀티쳐 보드 프리셋 프로필 설정")
        self.geometry("520x460")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.transient(parent_board)
        self.grab_set()

        setup_global_fonts(self)
        self._build_ui()

    def _build_ui(self):
        palette = self.board._t()
        self.configure(fg_color=palette["bg"])

        main_frame = ctk.CTkFrame(self, fg_color=palette["card"], corner_radius=12, border_width=1, border_color=palette["border"])
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        # 상단 타이틀
        hdr = ctk.CTkFrame(main_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(hdr, text="🎛️ 놀티쳐 보드 프리셋 프로필 관리", font=get_font(14, "bold"), text_color=palette["accent"]).pack(side="left")

        ctk.CTkLabel(
            main_frame,
            text="수업 스타일에 맞춰 시작 도구와 보드 테마를 프리셋으로 저장하고 빠르게 전환하세요.",
            font=get_font(10), text_color=palette["text_sub"]
        ).pack(anchor="w", padx=16, pady=(0, 10))

        # 현재 프리셋 목록
        list_box = ctk.CTkScrollableFrame(main_frame, fg_color=palette["card_inner"], corner_radius=8, height=180)
        list_box.pack(fill="x", padx=16, pady=(0, 12))

        cur_active = board_preset_manager.get_active_preset_name()
        for p_name in board_preset_manager.get_preset_names():
            cfg = board_preset_manager.data["presets"][p_name]
            p_row = ctk.CTkFrame(list_box, fg_color=palette["card"] if p_name == cur_active else "transparent", corner_radius=6)
            p_row.pack(fill="x", pady=2, padx=4)

            badge = " [현재 활성]" if p_name == cur_active else ""
            tool_ko = {"timer": "타이머", "picker": "추첨", "dice": "주사위", "wheel": "돌림판", "scoreboard": "점수판", "drawing": "판서"}.get(cfg.get("active_tool", ""), cfg.get("active_tool", ""))
            
            ctk.CTkLabel(
                p_row,
                text=f"• {p_name}{badge}  (시작 도구: {tool_ko})",
                font=get_font(11, "bold" if p_name == cur_active else "normal"),
                text_color=palette["accent"] if p_name == cur_active else palette["text_main"]
            ).pack(side="left", padx=8, pady=6)

            if len(board_preset_manager.get_preset_names()) > 1:
                ctk.CTkButton(
                    p_row, text="삭제", width=42, height=22, font=get_font(9, "bold"),
                    fg_color="#dc2626", hover_color="#b91c1c", text_color="#ffffff", corner_radius=4,
                    command=lambda n=p_name: self._delete_preset(n)
                ).pack(side="right", padx=6)

            ctk.CTkButton(
                p_row, text="적용", width=42, height=22, font=get_font(9, "bold"),
                fg_color=palette["accent"], hover_color=palette["accent_hover"], text_color="#0f172a" if palette["bg"] != "#f4f1eb" else "#ffffff", corner_radius=4,
                command=lambda n=p_name: self._apply_preset(n)
            ).pack(side="right", padx=2)

        # 신규 프리셋 등록 구역
        new_box = ctk.CTkFrame(main_frame, fg_color=palette["card_inner"], corner_radius=8)
        new_box.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(new_box, text="➕ 현재 보드 상태를 새 프리셋으로 저장", font=get_font(11, "bold"), text_color=palette["text_main"]).pack(anchor="w", padx=12, pady=(10, 4))
        
        in_row = ctk.CTkFrame(new_box, fg_color="transparent")
        in_row.pack(fill="x", padx=12, pady=(0, 10))

        self.name_entry = ctk.CTkEntry(in_row, placeholder_text="새 프리셋 이름 입력 (예: 수학 수업 모드)", font=get_font(11), height=32)
        self.name_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            in_row, text="저장", font=get_font(11, "bold"), width=60, height=32,
            fg_color=palette["accent"], hover_color=palette["accent_hover"], text_color="#0f172a" if palette["bg"] != "#f4f1eb" else "#ffffff", corner_radius=6,
            command=self._save_current_as_new
        ).pack(side="right")

        # 하단 닫기
        ctk.CTkButton(
            main_frame, text="닫기", font=get_font(11, "bold"), height=34,
            fg_color=palette["card_inner"], hover_color=palette["border"], text_color=palette["text_main"],
            corner_radius=6, command=self.destroy
        ).pack(fill="x", padx=16, pady=(0, 12))

    def _apply_preset(self, name: str):
        board_preset_manager.set_active_preset(name)
        cfg = board_preset_manager.get_active_preset()
        self.board.theme_key = cfg.get("theme_key", self.board.theme_key)
        self.board.active_tool = cfg.get("active_tool", self.board.active_tool)
        self.board._build_ui()
        self.destroy()

    def _delete_preset(self, name: str):
        if messagebox.askyesno("프리셋 삭제", f"'{name}' 프리셋을 삭제하시겠습니까?"):
            board_preset_manager.delete_preset(name)
            self.board._build_ui()
            self.destroy()

    def _save_current_as_new(self):
        val = self.name_entry.get().strip()
        if not val:
            messagebox.showwarning("입력 필요", "프리셋 이름을 입력해주세요.")
            return
        cfg = {
            "active_tool": self.board.active_tool,
            "theme_key": self.board.theme_key,
            "is_fullscreen": self.board.is_fullscreen,
            "desc": f"사용자 정의 프리셋 ({val})"
        }
        board_preset_manager.save_preset(val, cfg)
        self.board._build_ui()
        self.destroy()


