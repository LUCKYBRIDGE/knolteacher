"""
놀티쳐 보드 (StudentDisplayWindow) - 전면 개편
1. 상단: 사전 설정 표준 모드(수업 도구, 학급 게시판, 올인원 분할) + 커스텀 탭 (자유 이름 설정, 탭 추가/삭제)
2. 중앙: 위젯 드래그 이동 및 크기 조절 캔버스
   - 표준 탭: 재실행 시 원래 사전 설정 배치로 자동 복구
   - 커스텀 탭: 마지막에 사용한 위젯과 위치, 크기 그대로 영구 보존
3. 하단: 스마트 도구 독 (위젯 바)
   - [⏱️ 타이머] [🎯 발표자 추첨] [🎲 주사위(D4~D20, 2개, 통계표)] [🎡 돌림판] [🏆 점수판] [✏️ 판서] [📅 시간표] [🍱 급식] [📝 알림장]
   - 클릭 시 캔버스에 크기조절/이동 가능한 위젯 즉시 팝업
"""
import os
import sys
import uuid
import random
import datetime
import tkinter as tk
from tkinter import simpledialog, messagebox
import customtkinter as ctk
from typing import Dict, Any, Optional, List

from src.font_config import get_font
from src.icon_renderer import get_icon
from src.theme_manager import theme_manager
from src.timetable_manager import timetable_manager, DAYS_KO
from src.neis_client import neis_client
from src.config_utils import get_config_dir
from src.drawing_overlay import ScreenDrawingOverlay
from src.board_tab_manager import board_tab_manager
from src.board_widgets import create_board_widget, FloatingBoardWidget

THEMES = {
    "dark": {
        "name": "다크 네이비",
        "bg": "#0b0f19",
        "card": "#111827",
        "card_inner": "#1f2937",
        "border": "#374151",
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

        # 윈도우 초기 설정
        self.title("놀티쳐 보드 (Knol Board)")
        self.geometry("1280x840")
        self.minsize(980, 680)
        self.resizable(True, True)

        self.theme_key = "dark"
        self.is_fullscreen_mode = False
        self.active_tab_id = board_tab_manager.active_tab_id
        self.active_widgets: Dict[str, FloatingBoardWidget] = {}

        self._load_icon()
        self._build_ui()
        self._start_clock_loop()

        # F11 전체화면, ESC 복귀 단축키
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

    # =========================================================================
    # UI 전체 레이아웃 빌더
    # =========================================================================
    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        t = self._t()
        self.configure(fg_color=t["bg"])

        # 1. 상단 스마트 헤더 & 탭 네비게이션 바 (높이 54px)
        self.top_bar = ctk.CTkFrame(self, fg_color=t["card"], corner_radius=0, height=54, border_width=1, border_color=t["border"])
        self.top_bar.pack(fill="x")
        self.top_bar.pack_propagate(False)

        # [좌측] 로고 + 실시간 시계
        l_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        l_box.pack(side="left", padx=(14, 8))

        ctk.CTkLabel(l_box, text="📺 놀티쳐 보드", font=get_font(15, "bold"), text_color=t["accent"]).pack(side="left")
        ctk.CTkFrame(l_box, width=1, height=18, fg_color=t["border"]).pack(side="left", padx=10)

        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]
        self.clock_lbl = ctk.CTkLabel(
            l_box,
            text=f"{today.strftime('%m/%d')} ({weekday_str})  --:--:--",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=t["text_sub"]
        )
        self.clock_lbl.pack(side="left")

        # [중앙] 스크롤 가능한 탭 네비게이션 바 (표준 탭 + 커스텀 탭 + 새 탭)
        self.tab_container = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.tab_container.pack(side="left", fill="x", expand=True, padx=6)
        self._render_tab_navigation()

        # [우측] 유틸리티 컨트롤 (테마, 전체화면, 닫기)
        r_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        r_box.pack(side="right", padx=(6, 12))

        # 테마 버튼
        theme_ico = get_icon("theme", t["text_main"], 15)
        ctk.CTkButton(
            r_box, text=" 테마", image=theme_ico, compound="left", width=64, height=32, font=get_font(10, "bold"),
            fg_color=t["card_inner"], hover_color=t["border"], text_color=t["text_main"],
            corner_radius=6, command=self._open_theme_picker
        ).pack(side="left", padx=2)

        # 전체화면 버튼
        fs_ico = get_icon("fullscreen", "#ffffff", 15)
        self.fs_btn = ctk.CTkButton(
            r_box, text=" 전체화면", image=fs_ico, compound="left", width=80, height=32, font=get_font(10, "bold"),
            fg_color=t["accent"], hover_color=t["accent_hover"], text_color="#ffffff",
            corner_radius=6, command=self._toggle_fullscreen
        )
        self.fs_btn.pack(side="left", padx=2)

        # 닫기 버튼
        close_ico = get_icon("close", "#ffffff", 13)
        ctk.CTkButton(
            r_box, text="", image=close_ico, width=32, height=32,
            fg_color="#dc2626", hover_color="#b91c1c",
            corner_radius=6, command=self.close
        ).pack(side="left", padx=2)

        # 2. 중앙 메인 캔버스 영역 (자유 위젯 배치 스테이지)
        self.canvas_frame = ctk.CTkFrame(self, fg_color=t["bg"], corner_radius=0)
        self.canvas_frame.pack(fill="both", expand=True)

        # 3. 하단 스마트 도구 독 (Bottom Widget Bar - 높이 56px)
        self.bottom_bar = ctk.CTkFrame(self, fg_color=t["card"], corner_radius=0, height=56, border_width=1, border_color=t["border"])
        self.bottom_bar.pack(fill="x", side="bottom")
        self.bottom_bar.pack_propagate(False)
        self._build_bottom_dock()

        # 현재 활성 탭의 위젯들 로드 및 렌더링
        self._load_and_render_tab_content(self.active_tab_id)

    # =========================================================================
    # 상단 탭 네비게이션
    # =========================================================================
    def _render_tab_navigation(self):
        for w in self.tab_container.winfo_children():
            w.destroy()

        t = self._t()
        all_tabs = board_tab_manager.get_all_tabs()

        for tab in all_tabs:
            tid = tab["id"]
            name = tab["name"]
            is_active = (tid == self.active_tab_id)
            is_custom = tab.get("is_custom", False)

            tab_frame = ctk.CTkFrame(
                self.tab_container,
                fg_color=t["accent"] if is_active else t["card_inner"],
                corner_radius=8,
                height=32
            )
            tab_frame.pack(side="left", padx=2)

            btn = ctk.CTkButton(
                tab_frame,
                text=name,
                font=get_font(10, "bold"),
                fg_color="transparent",
                hover_color=t["accent_hover"],
                text_color="#ffffff" if is_active else t["text_main"],
                height=30,
                command=lambda tid_val=tid: self._switch_tab(tid_val)
            )
            btn.pack(side="left", padx=(6, 2))

            # 커스텀 탭인 경우: 이름 수정 및 삭제 버튼 제공
            if is_custom:
                edit_btn = ctk.CTkButton(
                    tab_frame, text="✏️", width=18, height=22, font=get_font(8),
                    fg_color="transparent", hover_color=t["card"],
                    text_color="#ffffff" if is_active else t["text_sub"],
                    command=lambda tid_val=tid, cur_name=name: self._rename_custom_tab(tid_val, cur_name)
                )
                edit_btn.pack(side="left", padx=1)

                del_btn = ctk.CTkButton(
                    tab_frame, text="✕", width=18, height=22, font=get_font(9, "bold"),
                    fg_color="transparent", hover_color="#ef4444",
                    text_color="#ffffff" if is_active else t["text_sub"],
                    command=lambda tid_val=tid: self._delete_custom_tab(tid_val)
                )
                del_btn.pack(side="left", padx=(0, 4))

        # 구분선
        ctk.CTkFrame(self.tab_container, width=1, height=18, fg_color=t["border"]).pack(side="left", padx=6)

        # ➕ 새 커스텀 탭 추가 버튼
        add_btn = ctk.CTkButton(
            self.tab_container,
            text="➕ 새 탭 추가",
            font=get_font(10, "bold"),
            fg_color=t["card_inner"],
            hover_color=t["accent"],
            text_color=t["text_main"],
            height=30,
            corner_radius=8,
            command=self._add_new_custom_tab
        )
        add_btn.pack(side="left", padx=2)

    def _switch_tab(self, tab_id: str):
        self.active_tab_id = tab_id
        board_tab_manager.active_tab_id = tab_id
        board_tab_manager._save_config()
        self._render_tab_navigation()
        self._load_and_render_tab_content(tab_id)

    def _add_new_custom_tab(self):
        name = simpledialog.askstring("새 탭 만들기", "새 커스텀 보드 탭의 이름을 입력하세요:\n(예: 1교시 수학, 모둠 활동실)")
        if name:
            new_tab = board_tab_manager.add_custom_tab(name)
            self._switch_tab(new_tab["id"])

    def _rename_custom_tab(self, tab_id: str, cur_name: str):
        new_name = simpledialog.askstring("탭 이름 변경", "변경할 탭 이름을 입력하세요:", initialvalue=cur_name)
        if new_name and new_name.strip():
            board_tab_manager.rename_tab(tab_id, new_name.strip())
            self._render_tab_navigation()

    def _delete_custom_tab(self, tab_id: str):
        if messagebox.askyesno("탭 삭제", "이 커스텀 보드 탭을 삭제하시겠습니까?"):
            board_tab_manager.delete_tab(tab_id)
            self._switch_tab(board_tab_manager.active_tab_id)

    # =========================================================================
    # 하단 스마트 도구 독 (위젯 바)
    # =========================================================================
    def _build_bottom_dock(self):
        t = self._t()
        dock_inner = ctk.CTkFrame(self.bottom_bar, fg_color="transparent")
        dock_inner.pack(fill="both", expand=True, padx=12, pady=8)

        tools = [
            ("timer",      "⏱️ 타이머",       "수업 시간 카운트다운 타이머"),
            ("picker",     "🎯 발표자 추첨",   "공정한 학생 이름/번호 무작위 추첨"),
            ("dice",       "🎲 주사위·통계",   "면수 조절(D4~D20), 2개, 비·비율·백분율 표"),
            ("wheel",      "🎡 돌림판",       "돌려돌려 모둠/벌칙 행운의 돌림판"),
            ("scoreboard", "🏆 점수판",       "학급 1~6모둠 실시간 점수판"),
            ("drawing",    "✏️ 학급 판서",     "화면 위 자유 펜 판서 및 자/삼각자/각도기"),
            ("timetable",  "📅 시간표",       "오늘의 수업 시간표 및 교시 정보"),
            ("meal",       "🍱 오늘의 급식",   "오늘의 중식 식단 및 영양 정보"),
            ("memo",       "📝 알림장",       "학급 숙제/준비물 알림장 판서"),
        ]

        for w_type, title, tip in tools:
            btn = ctk.CTkButton(
                dock_inner,
                text=title,
                font=get_font(10, "bold"),
                height=38,
                corner_radius=10,
                fg_color=t["card_inner"],
                hover_color=t["accent"],
                text_color=t["text_main"],
                border_width=1,
                border_color=t["border"],
                command=lambda wt=w_type: self._spawn_or_lift_widget(wt)
            )
            btn.pack(side="left", fill="x", expand=True, padx=3)

        # 구분선
        ctk.CTkFrame(dock_inner, width=1, height=24, fg_color=t["border"]).pack(side="left", padx=6)

        # 화면 초기화 버튼
        reset_btn = ctk.CTkButton(
            dock_inner,
            text="🧹 화면 초기화",
            font=get_font(10, "bold"),
            height=38,
            width=90,
            corner_radius=10,
            fg_color="#334155",
            hover_color="#dc2626",
            text_color="#ffffff",
            command=self._reset_current_canvas
        )
        reset_btn.pack(side="left", padx=3)

    # =========================================================================
    # 캔버스 위젯 관리 및 영구 저장
    # =========================================================================
    def _load_and_render_tab_content(self, tab_id: str):
        # 기존 캔버스 위의 모든 위젯 파괴
        for w in list(self.active_widgets.values()):
            try: w.destroy()
            except Exception: pass
        self.active_widgets.clear()

        tab_data = board_tab_manager.get_tab_by_id(tab_id)
        if not tab_data:
            return

        widgets_list = tab_data.get("widgets", [])
        for wd in widgets_list:
            wt = wd.get("type", "timer")
            wid = wd.get("id", f"w_{uuid.uuid4().hex[:6]}")
            x = wd.get("x", 50)
            y = wd.get("y", 50)
            w = wd.get("w", 340)
            h = wd.get("h", 280)

            widget_obj = create_board_widget(
                self.canvas_frame,
                wt,
                wid,
                x=x,
                y=y,
                w=w,
                h=h,
                on_change_callback=self._on_widget_geometry_changed,
                on_close_callback=self._on_widget_closed
            )
            self.active_widgets[wid] = widget_obj

    def _spawn_or_lift_widget(self, widget_type: str):
        if widget_type == "drawing":
            ScreenDrawingOverlay.get_instance(self).show()
            return

        # 이미 같은 타입의 위젯이 있으면 포커스(lift)
        for wid, wobj in self.active_widgets.items():
            if wobj.widget_type == widget_type:
                wobj.lift()
                return

        # 새 위젯 생성
        wid = f"w_{uuid.uuid4().hex[:6]}"
        default_sizes = {
            "timer": (340, 260),
            "picker": (360, 300),
            "dice": (480, 330),
            "wheel": (320, 280),
            "scoreboard": (320, 280),
            "timetable": (320, 480),
            "meal": (320, 420),
            "memo": (340, 360),
        }
        dw, dh = default_sizes.get(widget_type, (340, 280))

        # 화면 중앙 부근에 스폰
        cw = self.canvas_frame.winfo_width() or 1200
        ch = self.canvas_frame.winfo_height() or 700
        sx = max(30, (cw - dw) // 2 + random.randint(-40, 40))
        sy = max(30, (ch - dh) // 2 + random.randint(-40, 40))

        widget_obj = create_board_widget(
            self.canvas_frame,
            widget_type,
            wid,
            x=sx,
            y=sy,
            w=dw,
            h=dh,
            on_change_callback=self._on_widget_geometry_changed,
            on_close_callback=self._on_widget_closed
        )
        self.active_widgets[wid] = widget_obj
        self._save_active_tab_widgets()

    def _on_widget_geometry_changed(self):
        self._save_active_tab_widgets()

    def _on_widget_closed(self, wid: str):
        if wid in self.active_widgets:
            del self.active_widgets[wid]
        self._save_active_tab_widgets()

    def _save_active_tab_widgets(self):
        """커스텀 탭인 경우에만 실시간 배치와 크기를 영구 저장"""
        cur_tab = board_tab_manager.get_tab_by_id(self.active_tab_id)
        if cur_tab and cur_tab.get("is_custom", False):
            data = [w.to_dict() for w in self.active_widgets.values()]
            board_tab_manager.update_tab_widgets(self.active_tab_id, data)

    def _reset_current_canvas(self):
        if messagebox.askyesno("화면 초기화", "현재 탭의 모든 위젯 배치를 초기화하시겠습니까?"):
            cur_tab = board_tab_manager.get_tab_by_id(self.active_tab_id)
            if cur_tab and not cur_tab.get("is_custom", False):
                # 표준 탭은 원본 사전설정으로 복구
                self._load_and_render_tab_content(self.active_tab_id)
            else:
                # 커스텀 탭은 위젯 전체 지우기
                for w in list(self.active_widgets.values()):
                    try: w.destroy()
                    except Exception: pass
                self.active_widgets.clear()
                self._save_active_tab_widgets()

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
                    self.clock_lbl.configure(text=f"{today.strftime('%m/%d')} ({weekday_str})  {now_str}")
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
            btn = ctk.CTkButton(
                pop,
                text=v["name"],
                fg_color=v["card"],
                text_color=v["text_main"],
                border_width=1,
                border_color=v["border"],
                hover_color=v["accent"],
                command=lambda tk_val=k, p=pop: (self._set_theme(tk_val), p.destroy())
            )
            btn.pack(fill="x", padx=16, pady=3)

    def _set_theme(self, theme_key: str):
        self.theme_key = theme_key
        self._build_ui()

    def _toggle_fullscreen(self):
        self.is_fullscreen_mode = not self.is_fullscreen_mode
        self.attributes("-fullscreen", self.is_fullscreen_mode)
        if hasattr(self, "fs_btn"):
            self.fs_btn.configure(text=" 창모드" if self.is_fullscreen_mode else " 전체화면")

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
