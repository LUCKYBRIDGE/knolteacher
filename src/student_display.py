"""
놀티쳐 보드 (StudentDisplayWindow) - 자유 조절 반응형 위젯 보드
1. 네이티브 PanedWindow 기반 무한 자유 크기 조절:
   - 좌우 수평 분할 경계선 드래그로 메인 도구 vs 허브 크기 자유 조절
   - 우측 허브 내부 수직 분할 경계선 드래그로 시간표, 급식, 알림장 높이 개별 자유 조절
2. 위젯별 닫기(✕) 및 하단 독에서 원클릭 다시 켜기
3. 하단 도구 독 접기/펼치기 (▲/▼) 및 수평 스크롤 지원 (좁은 창에서도 도구 절대 안 잘림)
4. 모든 카드(시간표, 급식, 알림장, 주사위 통계, 추첨 기록) 마우스 휠 스크롤 완벽 지원
5. 창 크기에 비례하는 폰트 반응형 자동 확대/축소
"""
import os
import sys
import json
import random
import datetime
import winsound
import tkinter as tk
from tkinter import simpledialog, messagebox
import customtkinter as ctk
from typing import Dict, Any, Optional, List

from src.font_config import get_font
from src.icon_renderer import get_icon
from src.theme_manager import theme_manager
from src.timetable_manager import timetable_manager, DAYS_KO
from src.neis_client import neis_client
from src.student_manager import student_manager
from src.config_utils import get_config_dir
from src.drawing_overlay import ScreenDrawingOverlay

THEMES = {
    "dark": {
        "name": "다크 네이비",
        "bg": "#0b0f19",
        "card": "#111827",
        "card_inner": "#1f2937",
        "border": "#374151",
        "sash": "#2563eb",
        "accent": "#38bdf8",
        "accent_hover": "#0284c7",
        "text_main": "#f9fafb",
        "text_sub": "#9ca3af"
    },
    "chalkboard": {
        "name": "초록 칠판",
        "bg": "#14291e",
        "card": "#1c3829",
        "card_inner": "#254a37",
        "border": "#2d5a43",
        "sash": "#22c55e",
        "accent": "#4ade80",
        "accent_hover": "#22c55e",
        "text_main": "#f0fdf4",
        "text_sub": "#86efac"
    },
    "white": {
        "name": "화이트보드",
        "bg": "#f8fafc",
        "card": "#ffffff",
        "card_inner": "#f1f5f9",
        "border": "#cbd5e1",
        "sash": "#0284c7",
        "accent": "#0284c7",
        "accent_hover": "#0369a1",
        "text_main": "#0f172a",
        "text_sub": "#475569"
    },
    "warm": {
        "name": "따뜻한 베이지",
        "bg": "#fdfbf7",
        "card": "#ffffff",
        "card_inner": "#f7f3ec",
        "border": "#e5e0d8",
        "sash": "#d97706",
        "accent": "#d97706",
        "accent_hover": "#b45309",
        "text_main": "#292524",
        "text_sub": "#78716c"
    }
}


class StudentDisplayWindow(ctk.CTkToplevel):
    _instance = None

    @classmethod
    def get_instance(cls, parent=None, custom_config: dict = None):
        if cls._instance is None or not cls._instance.winfo_exists():
            cls._instance = cls(parent, custom_config=custom_config)
        else:
            if custom_config:
                cls._instance.apply_custom_config(custom_config)
            cls._instance.lift()
            cls._instance.focus_force()
        return cls._instance

    def __init__(self, parent=None, custom_config: dict = None):
        super().__init__(parent)
        StudentDisplayWindow._instance = self

        self.parent = parent
        self.custom_config = custom_config or {}

        self.title("놀티쳐 보드 (Knol Board)")
        self.geometry("1280x840")
        self.minsize(860, 580)
        self.resizable(True, True)

        self.theme_key = self.custom_config.get("theme_key", "dark")
        self.is_fullscreen_mode = False

        # 하단 독 접기/펼치기 상태
        self.is_dock_collapsed = False

        self.custom_tabs_file = os.path.join(get_config_dir(), "board_tabs_v2.json")
        self.active_tab_id = "tab_split"
        self.custom_tabs = self._load_custom_tabs()

        # 도구 및 허브 위젯 On/Off 상태
        self.active_tool = "timer"
        self.show_timetable = True
        self.show_meal = True
        self.show_memo = True

        # 타이머 상태
        self.timer_total_sec = 300
        self.timer_rem_sec = 300
        self.timer_running = False
        self._timer_job = None

        # 발표자 뽑기 상태
        self.picker_picked = []
        self.picker_running = False

        # 주사위 상태
        self.dice_faces = 6
        self.dice_count = 1
        self.dice_history = []
        self.dice_counts = {}
        self.dice_rolling = False

        # 점수판 상태
        self.scores = {f"{i}모둠": 0 for i in range(1, 7)}

        self._load_icon()
        self._build_ui()
        self._start_clock_loop()

        self.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._exit_fullscreen())

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try: self.iconbitmap(icon_path)
            except Exception: pass

    def _t(self) -> dict:
        return THEMES.get(self.theme_key, THEMES["dark"])

    def _load_custom_tabs(self) -> list:
        if os.path.exists(self.custom_tabs_file):
            try:
                with open(self.custom_tabs_file, "r", encoding="utf-8") as f:
                    return json.load(f).get("tabs", [])
            except Exception: pass
        return []

    def _save_custom_tabs(self):
        try:
            with open(self.custom_tabs_file, "w", encoding="utf-8") as f:
                json.dump({"tabs": self.custom_tabs}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Tabs Save Error] {e}")

    # =========================================================================
    # UI 전체 레이아웃 (상단 헤더 + 하단 독 + 중앙 자유 조절 PanedWindow)
    # =========================================================================
    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        t = self._t()
        self.configure(fg_color=t["bg"])

        # 1. 상단 스마트 헤더 & 탭 바 (높이 48px)
        self.top_bar = ctk.CTkFrame(self, fg_color=t["card"], corner_radius=0, height=48, border_width=1, border_color=t["border"])
        self.top_bar.pack(side="top", fill="x")
        self.top_bar.pack_propagate(False)

        l_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        l_box.pack(side="left", padx=(14, 8))

        ctk.CTkLabel(l_box, text="📺 놀티쳐 보드", font=get_font(14, "bold"), text_color=t["accent"]).pack(side="left")
        ctk.CTkFrame(l_box, width=1, height=16, fg_color=t["border"]).pack(side="left", padx=10)

        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]
        self.clock_lbl = ctk.CTkLabel(
            l_box,
            text=f"{today.strftime('%m/%d')} ({weekday_str}) --:--:--",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=t["text_sub"]
        )
        self.clock_lbl.pack(side="left")

        # 상단 탭 네비게이션
        self.tab_row = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.tab_row.pack(side="left", fill="x", expand=True, padx=8)
        self._render_tabs()

        # 우측 제어 버튼 (테마, 전체화면, 닫기)
        r_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        r_box.pack(side="right", padx=(6, 12))

        theme_ico = get_icon("theme", t["text_main"], 15)
        ctk.CTkButton(
            r_box, text=" 테마", image=theme_ico, compound="left", width=64, height=28, font=get_font(10, "bold"),
            fg_color=t["card_inner"], hover_color=t["border"], text_color=t["text_main"],
            corner_radius=6, command=self._open_theme_picker
        ).pack(side="left", padx=2)

        fs_ico = get_icon("fullscreen", "#ffffff", 15)
        self.fs_btn = ctk.CTkButton(
            r_box, text=" 전체화면", image=fs_ico, compound="left", width=76, height=28, font=get_font(10, "bold"),
            fg_color=t["accent"], hover_color=t["accent_hover"], text_color="#ffffff",
            corner_radius=6, command=self._toggle_fullscreen
        )
        self.fs_btn.pack(side="left", padx=2)

        close_ico = get_icon("close", "#ffffff", 13)
        ctk.CTkButton(
            r_box, text="", image=close_ico, width=28, height=28,
            fg_color="#dc2626", hover_color="#b91c1c",
            corner_radius=6, command=self.close
        ).pack(side="left", padx=2)

        # 2. 하단 스마트 도구 바 (접기/펼치기 가능 & 수평 스크롤 컨테이너)
        self._build_bottom_dock_container()

        # 3. 중앙 메인 바디 영역: 네이티브 PanedWindow 자유 분할
        self.body_container = ctk.CTkFrame(self, fg_color="transparent")
        self.body_container.pack(side="top", fill="both", expand=True, padx=8, pady=(4, 4))

        self._build_paned_layout()

    # =========================================================================
    # 상단 탭 시스템
    # =========================================================================
    def _render_tabs(self):
        for w in self.tab_row.winfo_children():
            w.destroy()

        t = self._t()
        std_tabs = [
            ("tab_split", "⚖️ 올인원 분할"),
            ("tab_tools", "🎯 수업도구 집중"),
            ("tab_board", "📋 학급 게시판"),
        ]
        for tid, tname in std_tabs:
            is_act = (self.active_tab_id == tid)
            btn = ctk.CTkButton(
                self.tab_row, text=tname, font=get_font(10, "bold"), height=28,
                fg_color=t["accent"] if is_act else t["card_inner"],
                hover_color=t["accent_hover"],
                text_color="#ffffff" if is_act else t["text_main"],
                corner_radius=6,
                command=lambda k=tid: self._switch_tab(k)
            )
            btn.pack(side="left", padx=2)

        ctk.CTkFrame(self.tab_row, width=1, height=16, fg_color=t["border"]).pack(side="left", padx=6)

        for ctab in self.custom_tabs:
            cid = ctab["id"]
            cname = ctab["name"]
            is_act = (self.active_tab_id == cid)

            c_frame = ctk.CTkFrame(self.tab_row, fg_color=t["accent"] if is_act else t["card_inner"], corner_radius=6, height=28)
            c_frame.pack(side="left", padx=2)

            ctk.CTkButton(
                c_frame, text=cname, font=get_font(10, "bold"), height=26,
                fg_color="transparent", hover_color=t["accent_hover"],
                text_color="#ffffff" if is_act else t["text_main"],
                command=lambda k=cid: self._switch_tab(k)
            ).pack(side="left", padx=(4, 1))

            ctk.CTkButton(
                c_frame, text="✏️", width=16, height=20, font=get_font(8),
                fg_color="transparent", hover_color=t["card"],
                text_color="#ffffff" if is_act else t["text_sub"],
                command=lambda k=cid, cn=cname: self._rename_custom_tab(k, cn)
            ).pack(side="left", padx=1)

            ctk.CTkButton(
                c_frame, text="✕", width=16, height=20, font=get_font(8, "bold"),
                fg_color="transparent", hover_color="#ef4444",
                text_color="#ffffff" if is_act else t["text_sub"],
                command=lambda k=cid: self._delete_custom_tab(k)
            ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            self.tab_row, text="➕ 새 탭", font=get_font(10, "bold"), height=28, width=60,
            fg_color=t["card_inner"], hover_color=t["accent"], text_color=t["text_main"],
            corner_radius=6, command=self._add_custom_tab
        ).pack(side="left", padx=4)

    def _switch_tab(self, tab_id: str):
        self.active_tab_id = tab_id
        if tab_id == "tab_split":
            self.show_timetable = True
            self.show_meal = True
            self.show_memo = True
        elif tab_id == "tab_tools":
            self.show_timetable = False
            self.show_meal = False
            self.show_memo = False
        elif tab_id == "tab_board":
            self.show_timetable = True
            self.show_meal = True
            self.show_memo = True
        else:
            for ctab in self.custom_tabs:
                if ctab["id"] == tab_id:
                    self.show_timetable = ctab.get("show_timetable", True)
                    self.show_meal = ctab.get("show_meal", True)
                    self.show_memo = ctab.get("show_memo", True)
                    self.active_tool = ctab.get("active_tool", "timer")
                    break

        self._build_ui()

    def _add_custom_tab(self):
        name = simpledialog.askstring("새 탭 만들기", "새 커스텀 보드 탭의 이름을 입력하세요:\n(예: 1교시 수학, 모둠 활동실)")
        if name and name.strip():
            new_tab = {
                "id": f"custom_{random.randint(1000, 9999)}",
                "name": name.strip(),
                "show_timetable": True,
                "show_meal": True,
                "show_memo": True,
                "active_tool": "timer"
            }
            self.custom_tabs.append(new_tab)
            self._save_custom_tabs()
            self._switch_tab(new_tab["id"])

    def _rename_custom_tab(self, tab_id: str, old_name: str):
        new_name = simpledialog.askstring("탭 이름 변경", "변경할 이름을 입력하세요:", initialvalue=old_name)
        if new_name and new_name.strip():
            for ctab in self.custom_tabs:
                if ctab["id"] == tab_id:
                    ctab["name"] = new_name.strip()
                    break
            self._save_custom_tabs()
            self._render_tabs()

    def _delete_custom_tab(self, tab_id: str):
        if messagebox.askyesno("탭 삭제", "이 커스텀 보드 탭을 삭제하시겠습니까?"):
            self.custom_tabs = [c for c in self.custom_tabs if c["id"] != tab_id]
            self._save_custom_tabs()
            self._switch_tab("tab_split")

    def _save_current_custom_tab_state(self):
        for ctab in self.custom_tabs:
            if ctab["id"] == self.active_tab_id:
                ctab["show_timetable"] = self.show_timetable
                ctab["show_meal"] = self.show_meal
                ctab["show_memo"] = self.show_memo
                ctab["active_tool"] = self.active_tool
                self._save_custom_tabs()
                break

    # =========================================================================
    # PanedWindow 기반 무한 자유 크기 조절 분할 레이아웃
    # =========================================================================
    def _build_paned_layout(self):
        for w in self.body_container.winfo_children():
            w.destroy()

        t = self._t()
        has_hub = (self.show_timetable or self.show_meal or self.show_memo)
        has_tool = (self.active_tab_id != "tab_board")

        if has_tool and has_hub:
            # 좌우 수평 PanedWindow (자유로운 좌우 크기 조절)
            self.h_paned = tk.PanedWindow(
                self.body_container, orient="horizontal",
                sashwidth=8, sashrelief="flat", bg=t["bg"], bd=0, opaqueresize=True
            )
            self.h_paned.pack(fill="both", expand=True)

            # 좌측 메인 도구 영역
            self.stage_frame = ctk.CTkFrame(self.h_paned, fg_color=t["card"], corner_radius=12, border_width=1, border_color=t["border"])
            self.h_paned.add(self.stage_frame, minsize=320)
            self._render_stage_tool()

            # 우측 허브 영역 (상하 수직 PanedWindow: 시간표, 급식, 메모 크기 각각 조절 가능!)
            self._build_v_paned_hub(self.h_paned)

        elif has_tool:
            # 도구 집중 모드 (100%)
            self.stage_frame = ctk.CTkFrame(self.body_container, fg_color=t["card"], corner_radius=12, border_width=1, border_color=t["border"])
            self.stage_frame.pack(fill="both", expand=True)
            self._render_stage_tool()

        elif has_hub:
            # 게시판 전면 모드 (100%)
            self._build_v_paned_hub(self.body_container)

    def _build_v_paned_hub(self, parent_container):
        t = self._t()
        # 수직 PanedWindow (위젯별 상하 높이 자유 조절)
        self.v_paned = tk.PanedWindow(
            parent_container, orient="vertical",
            sashwidth=6, sashrelief="flat", bg=t["bg"], bd=0, opaqueresize=True
        )
        if isinstance(parent_container, tk.PanedWindow):
            parent_container.add(self.v_paned, minsize=260)
        else:
            self.v_paned.pack(fill="both", expand=True)

        # 1. 시간표 카드
        if self.show_timetable:
            tt_box = self._create_timetable_widget(self.v_paned, t)
            self.v_paned.add(tt_box, minsize=100)

        # 2. 급식 카드
        if self.show_meal:
            meal_box = self._create_meal_widget(self.v_paned, t)
            self.v_paned.add(meal_box, minsize=100)

        # 3. 알림장 카드
        if self.show_memo:
            memo_box = self._create_memo_widget(self.v_paned, t)
            self.v_paned.add(memo_box, minsize=80)

    # 1. 시간표 위젯 (완벽 마우스 휠 스크롤 지원)
    def _create_timetable_widget(self, parent, t):
        card = ctk.CTkFrame(parent, fg_color=t["card"], corner_radius=10, border_width=1, border_color=t["border"])

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(hdr, text="📅 오늘의 시간표", font=get_font(11, "bold"), text_color=t["text_main"]).pack(side="left")
        ctk.CTkButton(hdr, text="✕", width=20, height=20, font=get_font(9, "bold"), fg_color="transparent", hover_color="#ef4444", text_color=t["text_sub"], command=self._toggle_hide_timetable).pack(side="right")

        scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        _, _, items = timetable_manager.get_today_schedule_items()
        now_s = datetime.datetime.now().strftime("%H:%M")
        for it in items:
            is_cur = (it["start"] <= now_s <= it["end"])
            r = ctk.CTkFrame(scroll, fg_color=t["accent"] if is_cur else t["card_inner"], corner_radius=6)
            r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text=f"{it['name']} ({it['start']})", font=get_font(9, "bold"), text_color="#ffffff" if is_cur else t["text_sub"]).pack(side="left", padx=6, pady=3)
            sub = "점심시간" if it.get("is_lunch") else it.get("subject", "")
            ctk.CTkLabel(r, text=sub, font=get_font(10, "bold"), text_color="#ffffff" if is_cur else t["text_main"]).pack(side="right", padx=6)

        return card

    # 2. 급식 위젯 (완벽 마우스 휠 스크롤 지원)
    def _create_meal_widget(self, parent, t):
        card = ctk.CTkFrame(parent, fg_color=t["card"], corner_radius=10, border_width=1, border_color=t["border"])

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(hdr, text="🍱 오늘의 급식", font=get_font(11, "bold"), text_color=t["text_main"]).pack(side="left")
        ctk.CTkButton(hdr, text="✕", width=20, height=20, font=get_font(9, "bold"), fg_color="transparent", hover_color="#ef4444", text_color=t["text_sub"], command=self._toggle_hide_meal).pack(side="right")

        scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        today = datetime.date.today()
        ok, meal_info, _ = neis_client.get_meal_for_date(today)
        if not ok or not meal_info.get("dishes"):
            ctk.CTkLabel(scroll, text="오늘 등록된 급식이 없습니다.", font=get_font(10), text_color=t["text_sub"]).pack(pady=14)
        else:
            for d in meal_info.get("dishes", []):
                ctk.CTkLabel(scroll, text=f"• {d}", font=get_font(10), text_color=t["text_main"], anchor="w").pack(fill="x", pady=1, padx=4)

        return card

    # 3. 알림장 위젯 (자유 스크롤 지원)
    def _create_memo_widget(self, parent, t):
        card = ctk.CTkFrame(parent, fg_color=t["card"], corner_radius=10, border_width=1, border_color=t["border"])

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(hdr, text="📝 학급 알림장", font=get_font(11, "bold"), text_color=t["text_main"]).pack(side="left")
        ctk.CTkButton(hdr, text="✕", width=20, height=20, font=get_font(9, "bold"), fg_color="transparent", hover_color="#ef4444", text_color=t["text_sub"], command=self._toggle_hide_memo).pack(side="right")

        txt = ctk.CTkTextbox(card, font=get_font(10), fg_color=t["card_inner"], text_color=t["text_main"])
        txt.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        txt.insert("1.0", "• 1교시: 수학익힘책 42~45쪽\n• 5교시: 체육복 착용\n• 하교 후 손 씻기!\n• 준비물 챙기기")

        return card

    def _toggle_hide_timetable(self):
        self.show_timetable = False
        self._build_paned_layout()
        self._render_dock_buttons()
        self._save_current_custom_tab_state()

    def _toggle_hide_meal(self):
        self.show_meal = False
        self._build_paned_layout()
        self._render_dock_buttons()
        self._save_current_custom_tab_state()

    def _toggle_hide_memo(self):
        self.show_memo = False
        self._build_paned_layout()
        self._render_dock_buttons()
        self._save_current_custom_tab_state()

    # =========================================================================
    # 하단 도구 독: 접기/펼치기 (▲/▼) 및 수평 스크롤 컨테이너 (잘림 0%)
    # =========================================================================
    def _build_bottom_dock_container(self):
        t = self._t()
        # 하단 독 래퍼
        self.bottom_dock_wrapper = ctk.CTkFrame(self, fg_color=t["card"], corner_radius=0, border_width=1, border_color=t["border"])
        self.bottom_dock_wrapper.pack(side="bottom", fill="x")

        # 상단 얇은 접기/펼치기 핸들 바 (높이 18px)
        handle_bar = ctk.CTkFrame(self.bottom_dock_wrapper, fg_color=t["card_inner"], height=18, corner_radius=0)
        handle_bar.pack(fill="x")
        handle_bar.pack_propagate(False)

        self.dock_toggle_btn = ctk.CTkButton(
            handle_bar,
            text="▲ 도구 바 펼치기" if self.is_dock_collapsed else "▼ 도구 바 접기",
            font=get_font(8, "bold"), height=16,
            fg_color="transparent", hover_color=t["border"], text_color=t["text_sub"],
            command=self._toggle_dock
        )
        self.dock_toggle_btn.pack(side="right", padx=12)

        # 도구 독 본체 프레임
        self.dock_body = ctk.CTkFrame(self.bottom_dock_wrapper, fg_color="transparent", height=48)
        if not self.is_dock_collapsed:
            self.dock_body.pack(fill="x", padx=6, pady=(2, 4))
            self.dock_body.pack_propagate(False)
            self._render_dock_buttons()

    def _toggle_dock(self):
        self.is_dock_collapsed = not self.is_dock_collapsed
        self.bottom_dock_wrapper.destroy()
        self._build_bottom_dock_container()

    def _render_dock_buttons(self):
        for w in self.dock_body.winfo_children():
            w.destroy()

        t = self._t()
        # 수평 스크롤 컨테이너: 창이 아무리 좁아도 버튼들이 절대 잘리지 않음!
        scroll_dock = ctk.CTkScrollableFrame(self.dock_body, orientation="horizontal", height=42, fg_color="transparent")
        scroll_dock.pack(fill="both", expand=True)

        # 1. 수업 도구 전환 스위치들
        tools = [
            ("timer",      "⏱️ 타이머"),
            ("picker",     "🎯 발표자 추첨"),
            ("dice",       "🎲 주사위·통계"),
            ("wheel",      "🎡 돌림판"),
            ("scoreboard", "🏆 점수판"),
            ("drawing",    "✏️ 학급 판서"),
        ]
        for tkey, tname in tools:
            is_act = (self.active_tool == tkey and self.active_tab_id != "tab_board")
            ctk.CTkButton(
                scroll_dock, text=tname, font=get_font(10, "bold"), height=32,
                fg_color=t["accent"] if is_act else t["card_inner"],
                hover_color=t["accent_hover"],
                text_color="#ffffff" if is_act else t["text_main"],
                corner_radius=6,
                command=lambda k=tkey: self._switch_main_tool(k)
            ).pack(side="left", padx=2)

        ctk.CTkFrame(scroll_dock, width=1, height=22, fg_color=t["border"]).pack(side="left", padx=8)

        # 2. 허브 위젯 On/Off 스위치들
        ctk.CTkLabel(scroll_dock, text="허브 위젯:", font=get_font(10, "bold"), text_color=t["text_sub"]).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            scroll_dock, text="📅 시간표" if self.show_timetable else "+ 시간표", height=30, width=74, font=get_font(9, "bold"),
            fg_color=t["accent"] if self.show_timetable else t["card_inner"],
            hover_color=t["accent_hover"], text_color="#ffffff" if self.show_timetable else t["text_sub"],
            corner_radius=6, command=self._toggle_timetable
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            scroll_dock, text="🍱 급식" if self.show_meal else "+ 급식", height=30, width=68, font=get_font(9, "bold"),
            fg_color=t["accent"] if self.show_meal else t["card_inner"],
            hover_color=t["accent_hover"], text_color="#ffffff" if self.show_meal else t["text_sub"],
            corner_radius=6, command=self._toggle_meal
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            scroll_dock, text="📝 알림장" if self.show_memo else "+ 알림장", height=30, width=74, font=get_font(9, "bold"),
            fg_color=t["accent"] if self.show_memo else t["card_inner"],
            hover_color=t["accent_hover"], text_color="#ffffff" if self.show_memo else t["text_sub"],
            corner_radius=6, command=self._toggle_memo
        ).pack(side="left", padx=2)

    def _switch_main_tool(self, tool_key: str):
        self.active_tool = tool_key
        if self.active_tab_id == "tab_board":
            self.active_tab_id = "tab_split"
        self._build_ui()
        self._save_current_custom_tab_state()

    def _toggle_timetable(self):
        self.show_timetable = not self.show_timetable
        self._build_paned_layout()
        self._render_dock_buttons()
        self._save_current_custom_tab_state()

    def _toggle_meal(self):
        self.show_meal = not self.show_meal
        self._build_paned_layout()
        self._render_dock_buttons()
        self._save_current_custom_tab_state()

    def _toggle_memo(self):
        self.show_memo = not self.show_memo
        self._build_paned_layout()
        self._render_dock_buttons()
        self._save_current_custom_tab_state()

    # =========================================================================
    # 메인 도구 렌더링 & 반응형 폰트 자동 리사이징
    # =========================================================================
    def _render_stage_tool(self):
        for w in self.stage_frame.winfo_children():
            w.destroy()

        t = self._t()
        k = self.active_tool

        if k == "timer":
            self._render_timer_tool(t)
        elif k == "picker":
            self._render_picker_tool(t)
        elif k == "dice":
            self._render_dice_tool(t)
        elif k == "wheel":
            self._render_wheel_tool(t)
        elif k == "scoreboard":
            self._render_scoreboard_tool(t)
        elif k == "drawing":
            self._render_drawing_tool(t)

        self.stage_frame.bind("<Configure>", lambda e: self._on_stage_resized())

    def _on_stage_resized(self):
        """창 크기 및 분할 경계선 변경 시 내부 숫자/글씨 반응형 자동 확대"""
        if not hasattr(self, "stage_frame") or not self.stage_frame or not self.stage_frame.winfo_exists():
            return
        w = self.stage_frame.winfo_width()
        h = self.stage_frame.winfo_height()
        if w < 100 or h < 100: return

        if self.active_tool == "timer" and hasattr(self, "timer_lbl") and self.timer_lbl.winfo_exists():
            ideal_sz = max(44, min(140, int(min(w * 0.22, h * 0.32))))
            self.timer_lbl.configure(font=ctk.CTkFont(family="Consolas", size=ideal_sz, weight="bold"))

        elif self.active_tool == "picker" and hasattr(self, "picker_lbl") and self.picker_lbl.winfo_exists():
            ideal_sz = max(34, min(96, int(min(w * 0.15, h * 0.25))))
            self.picker_lbl.configure(font=ctk.CTkFont(family="Malgun Gothic", size=ideal_sz, weight="bold"))

        elif self.active_tool == "dice" and hasattr(self, "dice_lbl") and self.dice_lbl.winfo_exists():
            ideal_sz = max(44, min(100, int(min(w * 0.16, h * 0.26))))
            self.dice_lbl.configure(font=ctk.CTkFont(family="Segoe UI Symbol", size=ideal_sz))

    # 1. 타이머 도구
    def _render_timer_tool(self, t):
        hdr = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(14, 2))
        ctk.CTkLabel(hdr, text="⏱️ 교실 집중 타이머", font=get_font(15, "bold"), text_color=t["accent"]).pack(side="left")

        self.timer_lbl = ctk.CTkLabel(
            self.stage_frame,
            text=self._fmt_timer(self.timer_rem_sec),
            font=ctk.CTkFont(family="Consolas", size=84, weight="bold"),
            text_color=t["accent"]
        )
        self.timer_lbl.pack(expand=True, pady=4)

        p_row = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        p_row.pack(pady=4)
        for s, l in [(60, "1분"), (180, "3분"), (300, "5분"), (600, "10분"), (900, "15분")]:
            ctk.CTkButton(
                p_row, text=l, width=60, height=30, font=get_font(10, "bold"),
                fg_color=t["card_inner"], hover_color=t["accent"], text_color=t["text_main"],
                command=lambda sec=s: self._preset_timer(sec)
            ).pack(side="left", padx=3)

        c_row = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        c_row.pack(pady=(8, 16))

        self.btn_timer_run = ctk.CTkButton(
            c_row, text="▶ 시작", width=130, height=40, font=get_font(13, "bold"),
            fg_color=t["accent"], hover_color=t["accent_hover"],
            command=self._toggle_timer
        )
        self.btn_timer_run.pack(side="left", padx=6)

        ctk.CTkButton(
            c_row, text="↺ 리셋", width=84, height=40, font=get_font(11, "bold"),
            fg_color=t["card_inner"], hover_color=t["border"], text_color=t["text_main"],
            command=self._reset_timer
        ).pack(side="left", padx=6)

    def _fmt_timer(self, s: int) -> str:
        return f"{s // 60:02d}:{s % 60:02d}"

    def _preset_timer(self, s):
        self._reset_timer()
        self.timer_total_sec = s
        self.timer_rem_sec = s
        self.timer_lbl.configure(text=self._fmt_timer(s))

    def _toggle_timer(self):
        if self.timer_running:
            self.timer_running = False
            if self._timer_job: self.after_cancel(self._timer_job)
            self.btn_timer_run.configure(text="▶ 재개", fg_color=self._t()["accent"])
        else:
            self.timer_running = True
            self.btn_timer_run.configure(text="⏸ 일시정지", fg_color="#ea580c")
            self._timer_tick()

    def _timer_tick(self):
        if not self.timer_running: return
        if self.timer_rem_sec > 0:
            self.timer_rem_sec -= 1
            self.timer_lbl.configure(text=self._fmt_timer(self.timer_rem_sec))
            self._timer_job = self.after(1000, self._timer_tick)
        else:
            self.timer_running = False
            self.btn_timer_run.configure(text="▶ 시작", fg_color=self._t()["accent"])
            self.timer_lbl.configure(text="시간 종료!", text_color="#ef4444")
            try: winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception: pass

    def _reset_timer(self):
        self.timer_running = False
        if self._timer_job: self.after_cancel(self._timer_job)
        self.timer_rem_sec = self.timer_total_sec
        if hasattr(self, "timer_lbl"):
            self.timer_lbl.configure(text=self._fmt_timer(self.timer_rem_sec), text_color=self._t()["accent"])
        if hasattr(self, "btn_timer_run"):
            self.btn_timer_run.configure(text="▶ 시작", fg_color=self._t()["accent"])

    # 2. 발표자 뽑기 도구 (스크롤 기록창 완벽 지원)
    def _render_picker_tool(self, t):
        hdr = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(14, 2))
        ctk.CTkLabel(hdr, text="🎯 공정한 발표자 무작위 추첨", font=get_font(15, "bold"), text_color=t["accent"]).pack(side="left")

        ctrl_bar = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        ctrl_bar.pack(fill="x", padx=20, pady=4)

        self.picker_mode_seg = ctk.CTkSegmentedButton(
            ctrl_bar, values=["👦 학생 이름 모드", "🔢 번호 모드"], font=get_font(10, "bold"), height=28
        )
        self.picker_mode_seg.set("👦 학생 이름 모드")
        self.picker_mode_seg.pack(side="left", padx=(0, 10))

        self.picker_gender_seg = ctk.CTkSegmentedButton(
            ctrl_bar, values=["전체", "👦남학생", "👧여학생"], font=get_font(10, "bold"), height=28
        )
        self.picker_gender_seg.set("전체")
        self.picker_gender_seg.pack(side="left")

        disp_card = ctk.CTkFrame(self.stage_frame, fg_color=t["card_inner"], corner_radius=12, border_width=1, border_color=t["border"])
        disp_card.pack(fill="both", expand=True, padx=20, pady=6)

        self.picker_lbl = ctk.CTkLabel(
            disp_card, text="?", font=ctk.CTkFont(family="Malgun Gothic", size=60, weight="bold"),
            text_color=t["accent"]
        )
        self.picker_lbl.pack(expand=True)

        b_row = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        b_row.pack(pady=4)

        self.btn_pick = ctk.CTkButton(
            b_row, text="🎲 추첨하기!", width=140, height=40, font=get_font(13, "bold"),
            fg_color=t["accent"], hover_color=t["accent_hover"], command=self._do_pick
        )
        self.btn_pick.pack(side="left", padx=6)

        ctk.CTkButton(
            b_row, text="기록 초기화", width=84, height=40, font=get_font(11, "bold"),
            fg_color=t["card_inner"], hover_color=t["border"], text_color=t["text_main"],
            command=self._reset_pick_history
        ).pack(side="left", padx=6)

        # 뽑힌 기록 스크롤 영역
        h_scroll = ctk.CTkScrollableFrame(self.stage_frame, height=46, fg_color="transparent")
        h_scroll.pack(fill="x", padx=20, pady=(0, 10))

        self.pick_hist_lbl = ctk.CTkLabel(
            h_scroll, text="뽑힌 기록: 없음", font=get_font(10), text_color=t["text_sub"], wraplength=560
        )
        self.pick_hist_lbl.pack(anchor="w")

    def _do_pick(self):
        if self.picker_running: return

        is_name = ("이름" in self.picker_mode_seg.get())
        g_raw = self.picker_gender_seg.get()
        gender = "남" if "남" in g_raw else ("여" if "여" in g_raw else None)

        students = student_manager.get_student_list(gender)
        if is_name and students:
            cands = []
            for s in students:
                nm = s.get("name", "")
                gen = s.get("gender", "")
                tag = " 👦" if gen == "남" else (" 👧" if gen == "여" else "")
                cands.append(f"{s['number']}번 {nm}{tag}" if nm else f"{s['number']}번{tag}")
        else:
            cands = [f"{i}번" for i in range(1, 26)]

        avail = [c for c in cands if c not in self.picker_picked]
        if not avail:
            self.picker_lbl.configure(text="추첨 완료!", text_color="#10b981")
            self.pick_hist_lbl.configure(text="모든 대상이 다 뽑혔습니다!")
            return

        self.picker_running = True
        self.btn_pick.configure(state="disabled")

        def _anim(step=0):
            if step < 14:
                self.picker_lbl.configure(text=random.choice(cands), text_color=self._t()["text_main"])
                self.after(50 + step * 10, lambda: _anim(step + 1))
            else:
                winner = random.choice(avail)
                self.picker_picked.append(winner)
                self.picker_lbl.configure(text=winner, text_color="#10b981")
                self.pick_hist_lbl.configure(text=f"뽑힌 명단 ({len(self.picker_picked)}명): {', '.join(self.picker_picked)}")
                self.picker_running = False
                self.btn_pick.configure(state="normal")
                try: winsound.MessageBeep(winsound.MB_OK)
                except Exception: pass

        _anim()

    def _reset_pick_history(self):
        self.picker_picked.clear()
        self.picker_lbl.configure(text="?", text_color=self._t()["accent"])
        self.pick_hist_lbl.configure(text="뽑힌 기록: 없음")

    # 3. 주사위 도구 (통계 표 스크롤 완벽 지원)
    def _render_dice_tool(self, t):
        hdr = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(14, 2))
        ctk.CTkLabel(hdr, text="🎲 스마트 주사위 & 비·비율·백분율 통계", font=get_font(15, "bold"), text_color=t["accent"]).pack(side="left")

        cfg_bar = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        cfg_bar.pack(fill="x", padx=20, pady=4)

        ctk.CTkLabel(cfg_bar, text="개수:", font=get_font(11, "bold"), text_color=t["text_sub"]).pack(side="left")
        self.dice_cnt_seg = ctk.CTkSegmentedButton(
            cfg_bar, values=["1개", "2개"], font=get_font(10, "bold"), height=26,
            command=lambda v: setattr(self, "dice_count", 2 if v == "2개" else 1)
        )
        self.dice_cnt_seg.set("2개" if self.dice_count == 2 else "1개")
        self.dice_cnt_seg.pack(side="left", padx=(4, 14))

        ctk.CTkLabel(cfg_bar, text="면수:", font=get_font(11, "bold"), text_color=t["text_sub"]).pack(side="left")
        self.dice_face_combo = ctk.CTkComboBox(
            cfg_bar, values=["D6 (6면)", "D4 (4면)", "D8 (8면)", "D10 (10면)", "D12 (12면)", "D20 (20면)"],
            width=110, height=26, font=get_font(10, "bold"), state="readonly", command=self._on_dice_face_changed
        )
        self.dice_face_combo.set(f"D{self.dice_faces} ({self.dice_faces}면)")
        self.dice_face_combo.pack(side="left", padx=4)

        split = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        split.pack(fill="both", expand=True, padx=20, pady=6)

        d_card = ctk.CTkFrame(split, fg_color=t["card_inner"], corner_radius=12)
        d_card.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.dice_lbl = ctk.CTkLabel(
            d_card, text="⚅", font=ctk.CTkFont(family="Segoe UI Symbol", size=72),
            text_color=t["accent"]
        )
        self.dice_lbl.pack(expand=True)

        self.dice_sub_lbl = ctk.CTkLabel(d_card, text="결과: 6", font=get_font(13, "bold"), text_color=t["text_main"])
        self.dice_sub_lbl.pack(pady=(0, 10))

        s_card = ctk.CTkFrame(split, fg_color=t["card_inner"], corner_radius=12)
        s_card.pack(side="right", fill="both", expand=True, padx=(6, 0))

        ctk.CTkLabel(s_card, text="📊 실시간 비 / 비율 / 백분율 통계 표", font=get_font(11, "bold"), text_color=t["accent"]).pack(pady=(8, 4))
        self.dice_tbl_scroll = ctk.CTkScrollableFrame(s_card, fg_color="transparent")
        self.dice_tbl_scroll.pack(fill="both", expand=True, padx=8, pady=4)
        self._render_dice_stats_table()

        b_bar = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        b_bar.pack(pady=(4, 14))

        self.btn_roll_dice = ctk.CTkButton(
            b_bar, text="🎲 주사위 굴리기!", width=150, height=40, font=get_font(13, "bold"),
            fg_color=t["accent"], hover_color=t["accent_hover"], command=self._roll_dice
        )
        self.btn_roll_dice.pack(side="left", padx=6)

        ctk.CTkButton(
            b_bar, text="통계 초기화", width=84, height=40, font=get_font(11, "bold"),
            fg_color=t["card_inner"], hover_color="#dc2626", text_color=t["text_main"],
            command=self._reset_dice_stats
        ).pack(side="left", padx=6)

    def _on_dice_face_changed(self, val):
        self.dice_faces = int(val.split("(")[1].replace("면)", ""))
        self._reset_dice_stats()

    def _roll_dice(self):
        if self.dice_rolling: return
        self.dice_rolling = True
        self.btn_roll_dice.configure(state="disabled")

        chars = {1:"⚀", 2:"⚁", 3:"⚂", 4:"⚃", 5:"⚄", 6:"⚅"}

        def _anim(step=0):
            if step < 12:
                r1 = random.randint(1, self.dice_faces)
                r2 = random.randint(1, self.dice_faces) if self.dice_count == 2 else None
                if self.dice_faces == 6 and r1 in chars and (r2 is None or r2 in chars):
                    txt = chars[r1] if r2 is None else f"{chars[r1]} {chars[r2]}"
                    self.dice_lbl.configure(text=txt, font=ctk.CTkFont(family="Segoe UI Symbol", size=56 if r2 else 72))
                else:
                    txt = str(r1) if r2 is None else f"{r1} + {r2}"
                    self.dice_lbl.configure(text=txt, font=ctk.CTkFont(family="Consolas", size=48, weight="bold"))
                self.after(50 + step * 8, lambda: _anim(step + 1))
            else:
                f1 = random.randint(1, self.dice_faces)
                f2 = random.randint(1, self.dice_faces) if self.dice_count == 2 else None
                if self.dice_faces == 6 and f1 in chars and (f2 is None or f2 in chars):
                    txt = chars[f1] if f2 is None else f"{chars[f1]} {chars[f2]}"
                    self.dice_lbl.configure(text=txt, font=ctk.CTkFont(family="Segoe UI Symbol", size=56 if f2 else 72))
                else:
                    txt = str(f1) if f2 is None else f"{f1} + {f2}"
                    self.dice_lbl.configure(text=txt, font=ctk.CTkFont(family="Consolas", size=48, weight="bold"))

                if f2 is not None:
                    self.dice_sub_lbl.configure(text=f"A={f1}, B={f2} (합계={f1+f2})")
                else:
                    self.dice_sub_lbl.configure(text=f"결과: {f1}")

                self.dice_counts[f1] = self.dice_counts.get(f1, 0) + 1
                if f2 is not None:
                    self.dice_counts[f2] = self.dice_counts.get(f2, 0) + 1
                self.dice_history.append((f1, f2))

                self._render_dice_stats_table()
                self.dice_rolling = False
                self.btn_roll_dice.configure(state="normal")
                try: winsound.MessageBeep(winsound.MB_OK)
                except Exception: pass

        _anim()

    def _render_dice_stats_table(self):
        for w in self.dice_tbl_scroll.winfo_children():
            w.destroy()

        t = self._t()
        tot = sum(self.dice_counts.values())
        if tot == 0:
            ctk.CTkLabel(self.dice_tbl_scroll, text="주사위를 굴리면\n비·비율·백분율이 집계됩니다.", font=get_font(10), text_color=t["text_sub"]).pack(pady=30)
            return

        h_row = ctk.CTkFrame(self.dice_tbl_scroll, fg_color=t["card"], corner_radius=4)
        h_row.pack(fill="x", pady=2)
        ctk.CTkLabel(h_row, text="눈", width=30, font=get_font(9, "bold"), text_color=t["accent"]).pack(side="left")
        ctk.CTkLabel(h_row, text="빈도", width=40, font=get_font(9, "bold"), text_color=t["text_main"]).pack(side="left")
        ctk.CTkLabel(h_row, text="비(比)", width=60, font=get_font(9, "bold"), text_color=t["text_sub"]).pack(side="left")
        ctk.CTkLabel(h_row, text="비율", width=50, font=get_font(9, "bold"), text_color=t["text_sub"]).pack(side="left")
        ctk.CTkLabel(h_row, text="백분율(%)", width=64, font=get_font(9, "bold"), text_color="#10b981").pack(side="left")

        for face in range(1, min(self.dice_faces + 1, 21)):
            cnt = self.dice_counts.get(face, 0)
            ratio = (cnt / tot) if tot > 0 else 0.0
            pct = ratio * 100

            row = ctk.CTkFrame(self.dice_tbl_scroll, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=str(face), width=30, font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color=t["text_main"]).pack(side="left")
            ctk.CTkLabel(row, text=f"{cnt}회", width=40, font=get_font(9), text_color=t["text_sub"]).pack(side="left")
            ctk.CTkLabel(row, text=f"{cnt}:{tot}", width=60, font=ctk.CTkFont(family="Consolas", size=9), text_color=t["text_sub"]).pack(side="left")
            ctk.CTkLabel(row, text=f"{ratio:.3f}", width=50, font=ctk.CTkFont(family="Consolas", size=9), text_color=t["text_sub"]).pack(side="left")
            ctk.CTkLabel(row, text=f"{pct:.1f}%", width=64, font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#10b981").pack(side="left")

    def _reset_dice_stats(self):
        self.dice_counts.clear()
        self.dice_history.clear()
        if hasattr(self, "dice_lbl"):
            self.dice_lbl.configure(text="⚅" if self.dice_faces == 6 else str(self.dice_faces))
            self.dice_sub_lbl.configure(text=f"면수: D{self.dice_faces}")
        if hasattr(self, "dice_tbl_scroll"):
            self._render_dice_stats_table()

    # 4. 돌림판 도구
    def _render_wheel_tool(self, t):
        hdr = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(14, 2))
        ctk.CTkLabel(hdr, text="🎡 돌려돌려 행운의 돌림판", font=get_font(15, "bold"), text_color=t["accent"]).pack(side="left")

        ctk.CTkLabel(self.stage_frame, text="🎡", font=ctk.CTkFont(size=96)).pack(expand=True)
        self.wheel_res_lbl = ctk.CTkLabel(self.stage_frame, text="돌림판을 돌려보세요!", font=get_font(16, "bold"), text_color=t["text_main"])
        self.wheel_res_lbl.pack(pady=10)

        ctk.CTkButton(
            self.stage_frame, text="🎡 돌리기!", width=150, height=42, font=get_font(13, "bold"),
            fg_color=t["accent"], hover_color=t["accent_hover"], command=self._spin_wheel
        ).pack(pady=(0, 20))

    def _spin_wheel(self):
        items = ["1모둠", "2모둠", "3모둠", "4모둠", "5모둠", "6모둠"]
        def _step(c=0):
            if c < 16:
                self.wheel_res_lbl.configure(text=f"▶ {random.choice(items)}", text_color=self._t()["accent"])
                self.after(50 + c * 15, lambda: _step(c + 1))
            else:
                winner = random.choice(items)
                self.wheel_res_lbl.configure(text=f"🎉 당첨: {winner}!", text_color="#10b981")
                try: winsound.MessageBeep(winsound.MB_OK)
                except Exception: pass
        _step()

    # 5. 점수판 도구
    def _render_scoreboard_tool(self, t):
        hdr = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(14, 2))
        ctk.CTkLabel(hdr, text="🏆 모둠 점수판", font=get_font(15, "bold"), text_color=t["accent"]).pack(side="left")

        grid = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=20, pady=10)

        self.sc_lbls = {}
        for idx, (grp, sc) in enumerate(self.scores.items()):
            r = idx // 3
            c = idx % 3
            card = ctk.CTkFrame(grid, fg_color=t["card_inner"], corner_radius=10)
            card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
            grid.grid_columnconfigure(c, weight=1)
            grid.grid_rowconfigure(r, weight=1)

            ctk.CTkLabel(card, text=grp, font=get_font(12, "bold"), text_color=t["text_sub"]).pack(pady=(8, 2))
            lbl = ctk.CTkLabel(card, text=str(sc), font=ctk.CTkFont(family="Consolas", size=32, weight="bold"), text_color=t["accent"])
            lbl.pack(expand=True)
            self.sc_lbls[grp] = lbl

            b_row = ctk.CTkFrame(card, fg_color="transparent")
            b_row.pack(pady=(0, 8))
            ctk.CTkButton(b_row, text="+1", width=44, height=28, font=get_font(10, "bold"), command=lambda g=grp: self._add_sc(g, 1)).pack(side="left", padx=2)
            ctk.CTkButton(b_row, text="-1", width=44, height=28, font=get_font(10, "bold"), fg_color="#334155", command=lambda g=grp: self._add_sc(g, -1)).pack(side="left", padx=2)

    def _add_sc(self, grp, delta):
        self.scores[grp] = max(0, self.scores[grp] + delta)
        self.sc_lbls[grp].configure(text=str(self.scores[grp]))

    # 6. 판서 도구
    def _render_drawing_tool(self, t):
        hdr = ctk.CTkFrame(self.stage_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(14, 2))
        ctk.CTkLabel(hdr, text="✏️ 화면 위 자유 판서 & 측정 도구", font=get_font(15, "bold"), text_color=t["accent"]).pack(side="left")

        box = ctk.CTkFrame(self.stage_frame, fg_color=t["card_inner"], corner_radius=12)
        box.pack(fill="both", expand=True, padx=20, pady=12)

        ctk.CTkLabel(box, text="✏️", font=ctk.CTkFont(size=64)).pack(pady=(30, 10))
        ctk.CTkLabel(
            box,
            text="모니터 화면 전체 위에서 자유롭게 펜으로 판서할 수 있습니다.\n반투명 자(Ruler), 직각 삼각자, 180도 각도기, 모눈종이 격자선이 지원됩니다.",
            font=get_font(12), text_color=t["text_sub"], justify="center"
        ).pack(pady=6)

        ctk.CTkButton(
            box, text="✏️ 지금 화면 위 판서 시작 (Alt+2)", font=get_font(13, "bold"), height=44, width=240,
            fg_color=t["accent"], hover_color=t["accent_hover"],
            command=lambda: ScreenDrawingOverlay.get_instance(self).show()
        ).pack(pady=20)

    # =========================================================================
    # 유틸리티 (시계, 테마, 전체화면, 닫기)
    # =========================================================================
    def _start_clock_loop(self):
        def _tick():
            if self.winfo_exists():
                today = datetime.date.today()
                weekday_str = DAYS_KO[today.weekday()]
                now_str = datetime.datetime.now().strftime("%H:%M:%S")
                if hasattr(self, "clock_lbl") and self.clock_lbl.winfo_exists():
                    self.clock_lbl.configure(text=f"{today.strftime('%m/%d')} ({weekday_str}) {now_str}")
                self.after(1000, _tick)
        self.after(1000, _tick)

    def _open_theme_picker(self):
        pop = ctk.CTkToplevel(self)
        pop.title("테마 선택")
        pop.geometry("260x220")
        pop.resizable(False, False)
        pop.attributes("-topmost", True)

        ctk.CTkLabel(pop, text="🎨 놀티쳐 보드 테마", font=get_font(12, "bold")).pack(pady=10)
        for k, v in THEMES.items():
            ctk.CTkButton(
                pop, text=v["name"], fg_color=v["card"], text_color=v["text_main"],
                border_width=1, border_color=v["border"], hover_color=v["accent"],
                command=lambda tk_val=k, p=pop: (self._set_theme(tk_val), p.destroy())
            ).pack(fill="x", padx=16, pady=3)

    def _set_theme(self, theme_key: str):
        self.theme_key = theme_key
        self._build_ui()

    def _toggle_fullscreen(self):
        self.is_fullscreen_mode = not self.is_fullscreen_mode
        self.attributes("-fullscreen", self.is_fullscreen_mode)
        if hasattr(self, "fs_btn"):
            self.fs_btn.configure(text=" 창모드" if self.is_fullscreen_mode else " 전체화면")
        self.after(100, self._on_stage_resized)

    def _exit_fullscreen(self):
        if self.is_fullscreen_mode:
            self._toggle_fullscreen()

    def apply_custom_config(self, cfg: dict):
        self.custom_config.update(cfg)
        if "theme_key" in cfg:
            self.theme_key = cfg["theme_key"]
        self._build_ui()

    def close(self):
        StudentDisplayWindow._instance = None
        self.destroy()
