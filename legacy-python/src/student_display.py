"""
놀티쳐 보드 (StudentDisplayWindow) - 자유 배치 다중 위젯 데스크톱 시스템
1. 화면 전환이 아니라, 놀보드 위에 여러 도구 위젯 창을 동시에 자유롭게 띄우는 시스템
2. 각 위젯 창: 상하좌우 8방향 자유 크기 조절 + 타이틀바 드래그 자유 이동 + 우상단 닫기(✕)
3. 하단 도구 바: 누르면 화면 전환이 아닌 해당 도구 창을 띄우거나 끄는 토글 스위치 (현재 켜진 위젯 하이라이트)
4. 창 폭에 맞춘 하단 도구 바 자동 줄바꿈 (멀티라인 랩) + 접기/펼치기 (▲/▼)
5. 마우스 휠 스크롤 & 창 크기에 비례하는 반응형 글씨 크기
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
        "handle": "#38bdf8",
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
        "handle": "#4ade80",
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
        "handle": "#0284c7",
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
        "handle": "#d97706",
        "accent": "#d97706",
        "accent_hover": "#b45309",
        "text_main": "#292524",
        "text_sub": "#78716c"
    }
}


class BoardDrawingCanvasWidget(ctk.CTkFrame):
    """
    놀티쳐 보드 전용 인터랙티브 미니 칠판 / 화이트보드 판서 위젯
    - 초록 칠판 / 흰색 화이트보드 모드 원클릭 전환
    - 자유 손글씨 펜, 형광펜, 지우개, 텍스트 글상자(T) 입력
    - 다양한 분필/마커 색상 및 굵기 조절
    - 실행 취소(Undo) 및 캔버스 전체 지우기 지원
    """
    def __init__(self, parent_area, parent_window, theme_dict):
        super().__init__(parent_area, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.parent_window = parent_window
        self.t = theme_dict

        # 판서 상태
        self.board_mode = "green"  # green (초록 칠판) or white (화이트보드)
        self.current_tool = "pen"  # pen, highlighter, eraser, text
        self.current_color = "#ffffff"  # 초록 칠판 기본 흰색 분필
        self.current_width = 4
        self.history = []
        self.current_stroke = []
        self.last_x = 0
        self.last_y = 0
        self.active_text_entry = None

        self._build_toolbar()
        self._build_canvas()

    def _build_toolbar(self):
        tb = ctk.CTkFrame(self, fg_color=self.t["card_inner"], height=34, corner_radius=6)
        tb.pack(fill="x", padx=2, pady=(0, 4))
        tb.pack_propagate(False)

        # 1. 칠판 / 화이트보드 전환 토글
        self.mode_btn = ctk.CTkButton(
            tb, text="🏫 초록칠판", width=74, height=24, font=get_font(9, "bold"),
            fg_color="#15803d", hover_color="#166534", text_color="#ffffff",
            corner_radius=4, command=self._toggle_board_mode
        )
        self.mode_btn.pack(side="left", padx=3)

        # 구분선
        ctk.CTkFrame(tb, width=1, height=18, fg_color=self.t["border"]).pack(side="left", padx=4)

        # 2. 도구 선택 (펜, 형광펜, 텍스트, 지우개)
        self.tool_btns = {}
        tools = [("pen", "✏️ 펜"), ("highlighter", "🖍️ 형광"), ("text", "🔤 텍스트"), ("eraser", "🧹 지우개")]
        for t_key, t_label in tools:
            is_act = (t_key == self.current_tool)
            btn = ctk.CTkButton(
                tb, text=t_label, width=54, height=24, font=get_font(9, "bold"),
                fg_color=self.t["accent"] if is_act else "transparent",
                hover_color=self.t["card"],
                text_color="#ffffff" if is_act else self.t["text_main"],
                corner_radius=4, command=lambda k=t_key: self._select_tool(k)
            )
            btn.pack(side="left", padx=1)
            self.tool_btns[t_key] = btn

        # 구분선
        ctk.CTkFrame(tb, width=1, height=18, fg_color=self.t["border"]).pack(side="left", padx=4)

        # 3. 색상 팔레트
        self.color_box = ctk.CTkFrame(tb, fg_color="transparent")
        self.color_box.pack(side="left", padx=2)
        self._refresh_palette()

        # 구분선
        ctk.CTkFrame(tb, width=1, height=18, fg_color=self.t["border"]).pack(side="left", padx=4)

        # 4. 굵기 조절
        for w_val, w_txt in [(3, "가는"), (6, "보통"), (12, "굵은")]:
            ctk.CTkButton(
                tb, text=w_txt, width=32, height=22, font=get_font(8),
                fg_color=self.t["card"], hover_color=self.t["border"],
                text_color=self.t["text_sub"], corner_radius=4,
                command=lambda w=w_val: self._select_width(w)
            ).pack(side="left", padx=1)

        # 5. 우측: 실행 취소 & 전체 지우기
        ctk.CTkButton(
            tb, text="전체지우기", width=64, height=24, font=get_font(9, "bold"),
            fg_color="#dc2626", hover_color="#b91c1c", text_color="#ffffff",
            corner_radius=4, command=self._clear_all
        ).pack(side="right", padx=3)

        ctk.CTkButton(
            tb, text="↩ 취소", width=46, height=24, font=get_font(9, "bold"),
            fg_color=self.t["card"], hover_color=self.t["border"],
            text_color=self.t["text_main"], corner_radius=4,
            command=self._undo
        ).pack(side="right", padx=1)

    def _refresh_palette(self):
        for w in self.color_box.winfo_children():
            w.destroy()

        if self.board_mode == "green":
            colors = ["#ffffff", "#fef08a", "#f87171", "#38bdf8", "#4ade80", "#fb923c"]
        else:
            colors = ["#0f172a", "#ef4444", "#0284c7", "#16a34a", "#d97706", "#7c3aed"]

        for c in colors:
            ctk.CTkButton(
                self.color_box, text="", width=18, height=18, corner_radius=9,
                fg_color=c, hover_color=c, border_width=2 if c == self.current_color else 0,
                border_color="#ffffff" if self.board_mode == "green" else "#000000",
                command=lambda col=c: self._select_color(col)
            ).pack(side="left", padx=1)

    def _build_canvas(self):
        bg_col = "#14291e" if self.board_mode == "green" else "#ffffff"
        self.canvas = tk.Canvas(self, bg=bg_col, highlightthickness=0, cursor="pencil")
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)

        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_up)

    def _toggle_board_mode(self):
        if self.board_mode == "green":
            self.board_mode = "white"
            self.mode_btn.configure(text="📋 화이트보드", fg_color="#0284c7", hover_color="#0369a1")
            self.canvas.configure(bg="#ffffff")
            self.current_color = "#0f172a"
        else:
            self.board_mode = "green"
            self.mode_btn.configure(text="🏫 초록칠판", fg_color="#15803d", hover_color="#166534")
            self.canvas.configure(bg="#14291e")
            self.current_color = "#ffffff"
        self._refresh_palette()

    def _select_tool(self, key: str):
        self.current_tool = key
        for k, btn in self.tool_btns.items():
            is_act = (k == key)
            btn.configure(
                fg_color=self.t["accent"] if is_act else "transparent",
                text_color="#ffffff" if is_act else self.t["text_main"]
            )
        cursor_map = {"pen": "pencil", "highlighter": "crosshair", "eraser": "dotbox", "text": "xterm"}
        self.canvas.configure(cursor=cursor_map.get(key, "arrow"))

    def _select_color(self, col: str):
        self.current_color = col
        self._refresh_palette()

    def _select_width(self, w: int):
        self.current_width = w

    def _on_canvas_click(self, event):
        if self.active_text_entry:
            self._finalize_text()

        self.last_x = event.x
        self.last_y = event.y
        self.current_stroke = []

        if self.current_tool == "text":
            self._start_text_input(event.x, event.y)
        elif self.current_tool == "eraser":
            self._erase_at(event.x, event.y)

    def _on_canvas_move(self, event):
        if self.current_tool == "pen":
            line_id = self.canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                fill=self.current_color, width=self.current_width,
                capstyle=tk.ROUND, joinstyle=tk.ROUND, smooth=True
            )
            self.current_stroke.append(line_id)
            self.last_x = event.x
            self.last_y = event.y
        elif self.current_tool == "highlighter":
            line_id = self.canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                fill=self.current_color, width=self.current_width * 3,
                capstyle=tk.ROUND, joinstyle=tk.ROUND, stipple="gray50", smooth=True
            )
            self.current_stroke.append(line_id)
            self.last_x = event.x
            self.last_y = event.y
        elif self.current_tool == "eraser":
            self._erase_at(event.x, event.y)

    def _on_canvas_up(self, event):
        if self.current_stroke:
            self.history.append(("stroke", self.current_stroke))
            self.current_stroke = []

    def _erase_at(self, x, y):
        r = self.current_width * 3 + 10
        items = self.canvas.find_overlapping(x - r, y - r, x + r, y + r)
        for itm in items:
            self.canvas.delete(itm)

    def _start_text_input(self, x, y):
        f_sz = max(14, self.current_width * 4)
        entry_bg = "#0f172a" if self.board_mode == "green" else "#f1f5f9"
        txt_w = tk.Entry(
            self.canvas, font=("Malgun Gothic", f_sz, "bold"),
            fg=self.current_color, bg=entry_bg, insertbackground=self.current_color,
            relief="solid", bd=1
        )
        win_id = self.canvas.create_window(x, y, window=txt_w, anchor="nw")
        txt_w.focus_set()

        self.active_text_entry = {
            "entry": txt_w, "win_id": win_id, "x": x, "y": y, "font_size": f_sz, "color": self.current_color
        }

        txt_w.bind("<Return>", lambda e: self._finalize_text())
        txt_w.bind("<Escape>", lambda e: self._cancel_text())

    def _finalize_text(self):
        if not self.active_text_entry:
            return
        info = self.active_text_entry
        txt = info["entry"].get().strip()
        self.canvas.delete(info["win_id"])
        info["entry"].destroy()
        self.active_text_entry = None

        if txt:
            t_id = self.canvas.create_text(
                info["x"], info["y"], text=txt,
                font=("Malgun Gothic", info["font_size"], "bold"),
                fill=info["color"], anchor="nw"
            )
            self.history.append(("single", t_id))

    def _cancel_text(self):
        if self.active_text_entry:
            self.canvas.delete(self.active_text_entry["win_id"])
            self.active_text_entry["entry"].destroy()
            self.active_text_entry = None

    def _undo(self):
        if not self.history:
            return
        act_type, itms = self.history.pop()
        if act_type == "stroke":
            for i in itms:
                self.canvas.delete(i)
        elif act_type == "single":
            self.canvas.delete(itms)

    def _clear_all(self):
        self.canvas.delete("all")
        self.history.clear()



class BoardWidgetWindow(ctk.CTkFrame):
    """
    놀티쳐 보드 작업대(Desktop) 위의 고성능 플로팅 윈도우
    - 끝단이 완벽하게 정리된 모던 라운드 카드 디자인 (10px radius, 1.5px border)
    - 튀어나오는 파란 블록/회색 띠 완전 제거 -> 단정하고 세련된 우하단 슬림 그립 및 4변 리사이즈
    - 순수 델타(Delta) 마우스 트래킹으로 1픽셀의 튐이나 불안정함 없이 100% 견고한 이동/리사이즈
    - 60 FPS 쓰로틀링으로 잔상(Ghosting)과 렉 완전 박멸
    """
    def __init__(self, parent_board, widget_key: str, title: str, x: int, y: int, w: int, h: int, min_w=240, min_h=150):
        t = parent_board._t()
        super().__init__(
            parent_board.desktop_area,
            fg_color=t["card"],
            corner_radius=10,
            border_width=1.5,
            border_color=t["border"],
            width=w,
            height=h
        )
        self.parent_board = parent_board
        self.widget_key = widget_key
        self.widget_title = title
        self.current_x = x
        self.current_y = y
        self.current_w = w
        self.current_h = h
        self.min_w = min_w
        self.min_h = min_h

        self._last_event_time = 0
        self.place(x=x, y=y)

        # 1. 일체형 슬림 타이틀 바
        self.title_bar = ctk.CTkFrame(self, fg_color=t["card_inner"], height=32, corner_radius=6)
        self.title_bar.pack(fill="x", padx=3, pady=(3, 2))
        self.title_bar.pack_propagate(False)

        self.title_lbl = ctk.CTkLabel(
            self.title_bar, text=title, font=get_font(11, "bold"), text_color=t["text_main"], cursor="fleur"
        )
        self.title_lbl.pack(side="left", padx=10)

        self.close_btn = ctk.CTkButton(
            self.title_bar, text="✕", width=22, height=22, font=get_font(9, "bold"),
            fg_color="transparent", hover_color="#dc2626", text_color=t["text_sub"],
            corner_radius=4, command=self.close
        )
        self.close_btn.pack(side="right", padx=3)

        # 타이틀바 이동 이벤트 (순수 마우스 델타 트래킹)
        for w_item in (self.title_bar, self.title_lbl):
            w_item.bind("<Button-1>", self._start_move)
            w_item.bind("<B1-Motion>", self._on_move)

        # 2. 메인 컨텐츠 영역
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.pack(fill="both", expand=True, padx=4, pady=(0, 2))

        # 3. 하단 슬림 상태 & 리사이즈 바 (모서리 돌출 전혀 없는 깔끔한 마감)
        self.bottom_bar = tk.Frame(self, bg=t["card"], height=12)
        self.bottom_bar.pack(fill="x", side="bottom")
        self.bottom_bar.pack_propagate(False)

        # 우측 하단 미니멀 슬림 리사이즈 그립 (⤡)
        self.resize_grip = tk.Label(
            self.bottom_bar, text="⤡", font=("Malgun Gothic", 9, "bold"),
            fg=t["accent"], bg=t["card"], cursor="size_nw_se", anchor="se"
        )
        self.resize_grip.pack(side="right", padx=(0, 4), pady=(0, 1))
        self.resize_grip.bind("<Button-1>", lambda e: self._start_resize(e, "se"))
        self.resize_grip.bind("<B1-Motion>", lambda e: self._on_resize(e, "se"))

        # 우측변 리사이즈 (E)
        self.border_e = tk.Frame(self, bg=t["card"], width=5, cursor="sb_h_double_arrow")
        self.border_e.place(relx=1.0, rely=0.1, relheight=0.8, anchor="ne")
        self.border_e.bind("<Button-1>", lambda e: self._start_resize(e, "e"))
        self.border_e.bind("<B1-Motion>", lambda e: self._on_resize(e, "e"))

        # 하단변 리사이즈 (S)
        self.bottom_bar.bind("<Button-1>", lambda e: self._start_resize(e, "s"))
        self.bottom_bar.bind("<B1-Motion>", lambda e: self._on_resize(e, "s"))

        self.bind("<Button-1>", lambda e: self.lift())

    # ─── 견고한 델타 기반 이동 (Jump/Drift 0% 보장) ─────────────────────────
    def _start_move(self, event):
        self.lift()
        self._last_event_time = 0
        self._start_mouse_x = event.x_root
        self._start_mouse_y = event.y_root
        self._start_win_x = self.current_x
        self._start_win_y = self.current_y

    def _on_move(self, event):
        import time
        now = time.time()
        if now - self._last_event_time < 0.016:  # 60 FPS 제어
            return
        self._last_event_time = now

        dx = event.x_root - self._start_mouse_x
        dy = event.y_root - self._start_mouse_y

        nx = self._start_win_x + dx
        ny = self._start_win_y + dy

        # 보드 영역 경계 안전 클램핑
        dw = self.parent_board.desktop_area.winfo_width()
        dh = self.parent_board.desktop_area.winfo_height()
        if dw > 200 and dh > 200:
            nx = max(-self.current_w + 80, min(dw - 80, nx))
            ny = max(0, min(dh - 40, ny))

        self.current_x = nx
        self.current_y = ny
        self.place(x=nx, y=ny)

    # ─── 견고한 델타 기반 크기 조절 (100% 부드러운 리사이즈) ──────────────────
    def _start_resize(self, event, direction: str):
        self.lift()
        self._last_event_time = 0
        self._res_dir = direction
        self._start_mouse_x = event.x_root
        self._start_mouse_y = event.y_root
        self._start_win_w = self.current_w
        self._start_win_h = self.current_h

    def _on_resize(self, event, direction: str):
        import time
        now = time.time()
        if now - self._last_event_time < 0.016:  # 60 FPS 제어
            return
        self._last_event_time = now

        dx = event.x_root - self._start_mouse_x
        dy = event.y_root - self._start_mouse_y

        new_w = self._start_win_w
        new_h = self._start_win_h

        if "e" in direction or direction == "se":
            new_w = max(self.min_w, self._start_win_w + dx)
        if "s" in direction or direction == "se":
            new_h = max(self.min_h, self._start_win_h + dy)

        if new_w != self.current_w or new_h != self.current_h:
            self.current_w = new_w
            self.current_h = new_h
            self.configure(width=new_w, height=new_h)
            self._on_content_resized()

    def _on_content_resized(self):
        pass

    def close(self):
        self.parent_board.close_widget(self.widget_key)


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
        self.is_dock_collapsed = False

        # 활성화된 위젯 객체 맵 (key -> BoardWidgetWindow)
        self.active_widgets: Dict[str, BoardWidgetWindow] = {}

        # 탭 및 설정 관리
        self.custom_tabs_file = os.path.join(get_config_dir(), "board_tabs_v3.json")
        self.active_tab_id = "std_split"
        self.custom_tabs = self._load_custom_tabs()

        # 도구 상태 변수들
        self.timer_total_sec = 300
        self.timer_rem_sec = 300
        self.timer_running = False
        self._timer_job = None

        self.picker_picked = []
        self.picker_running = False

        self.dice_faces = 6
        self.dice_count = 1
        self.dice_counts = {}
        self.dice_rolling = False

        self.scores = {f"{i}모둠": 0 for i in range(1, 7)}

        self._last_wrap_state = None

        self._load_icon()
        self._build_ui()
        self._start_clock_loop()

        self.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._exit_fullscreen())
        self.bind("<Configure>", self._on_window_configure)

        # 초기 기본 위젯들 배치
        self.after(200, self._apply_initial_layout)

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        # 놀티쳐 보드는 일반 메인 창과 작업표시줄에서 뚜렷이 구분되도록 산뜻한 블루톤 전용 아이콘 적용
        board_icon = os.path.join(base_dir, "assets", "board_icon.ico")
        app_icon = os.path.join(base_dir, "assets", "app_icon.ico")
        icon_path = board_icon if os.path.exists(board_icon) else app_icon
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
                # Windows 작업표시줄 개별 분리 아이콘 ID 설정
                if sys.platform == "win32":
                    import ctypes
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("knolteacher.student.board.v1")
            except Exception:
                pass

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
    # 메인 UI 조립 (상단 헤더 + 하단 도구 독 + 중앙 위젯 캔버스 데스크톱)
    # =========================================================================
    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        t = self._t()
        self.configure(fg_color=t["bg"])

        # 1. 상단 스마트 헤더 & 탭 네비게이션
        self.top_bar = ctk.CTkFrame(self, fg_color=t["card"], corner_radius=0, height=46, border_width=1, border_color=t["border"])
        self.top_bar.pack(side="top", fill="x")
        self.top_bar.pack_propagate(False)

        l_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        l_box.pack(side="left", padx=(14, 8))

        ctk.CTkLabel(l_box, text="📺 놀티쳐 보드", font=get_font(13, "bold"), text_color=t["accent"]).pack(side="left")
        ctk.CTkFrame(l_box, width=1, height=16, fg_color=t["border"]).pack(side="left", padx=10)

        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]
        self.clock_lbl = ctk.CTkLabel(
            l_box,
            text=f"{today.strftime('%m/%d')} ({weekday_str}) --:--:--",
            font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"),
            text_color=t["text_sub"]
        )
        self.clock_lbl.pack(side="left")

        # 탭 바
        self.tab_row = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.tab_row.pack(side="left", fill="x", expand=True, padx=8)
        self._render_tabs()

        # 우측 버튼들
        r_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        r_box.pack(side="right", padx=(6, 12))

        theme_ico = get_icon("theme", t["text_main"], 14)
        ctk.CTkButton(
            r_box, text=" 테마", image=theme_ico, compound="left", width=62, height=26, font=get_font(9, "bold"),
            fg_color=t["card_inner"], hover_color=t["border"], text_color=t["text_main"],
            corner_radius=6, command=self._open_theme_picker
        ).pack(side="left", padx=2)

        fs_ico = get_icon("fullscreen", "#ffffff", 14)
        self.fs_btn = ctk.CTkButton(
            r_box, text=" 전체화면", image=fs_ico, compound="left", width=74, height=26, font=get_font(9, "bold"),
            fg_color=t["accent"], hover_color=t["accent_hover"], text_color="#ffffff",
            corner_radius=6, command=self._toggle_fullscreen
        )
        self.fs_btn.pack(side="left", padx=2)

        close_ico = get_icon("close", "#ffffff", 12)
        ctk.CTkButton(
            r_box, text="", image=close_ico, width=26, height=26,
            fg_color="#dc2626", hover_color="#b91c1c",
            corner_radius=6, command=self.close
        ).pack(side="left", padx=2)

        # 2. 하단 도구 독 바 (접기/펼치기 및 멀티라인 자동 줄바꿈)
        self._build_bottom_dock_container()

        # 3. 중앙 캔버스 데스크톱 (Solid BG, 여러 위젯이 자유롭게 뜨는 작업대)
        self.desktop_area = ctk.CTkFrame(self, fg_color=t["bg"], corner_radius=0)
        self.desktop_area.pack(side="top", fill="both", expand=True)

    # =========================================================================
    # 하단 도구 바 (도구 스위치 & 토글 런처)
    # =========================================================================
    ALL_TOOLS = [
        ("timer",      "⏱️ 타이머",     500, 360),
        ("picker",     "🎯 발표자 추첨",  460, 320),
        ("dice",       "🎲 주사위·통계", 540, 380),
        ("wheel",      "🎡 돌림판",     400, 320),
        ("scoreboard", "🏆 점수판",     520, 340),
        ("drawing",    "✏️ 칠판·판서",   560, 400),
        ("timetable",  "📅 시간표",     320, 360),
        ("meal",       "🍱 급식",       320, 360),
        ("memo",       "📝 알림장",     320, 320),
    ]

    def _build_bottom_dock_container(self):
        t = self._t()
        self.bottom_dock_wrapper = ctk.CTkFrame(self, fg_color=t["card"], corner_radius=0, border_width=1, border_color=t["border"])
        self.bottom_dock_wrapper.pack(side="bottom", fill="x")

        handle_bar = ctk.CTkFrame(self.bottom_dock_wrapper, fg_color=t["card_inner"], height=18, corner_radius=0)
        handle_bar.pack(fill="x")
        handle_bar.pack_propagate(False)

        ctk.CTkLabel(handle_bar, text="💡 아래 버튼을 눌러 원하는 도구 위젯을 보드 위에 띄우거나 끕니다 (상하좌우 자유 조절/이동)", font=get_font(8), text_color=t["text_sub"]).pack(side="left", padx=14)

        self.dock_toggle_btn = ctk.CTkButton(
            handle_bar,
            text="▲ 도구 바 펼치기" if self.is_dock_collapsed else "▼ 도구 바 접기",
            font=get_font(8, "bold"), height=16,
            fg_color="transparent", hover_color=t["border"], text_color=t["text_sub"],
            command=self._toggle_dock
        )
        self.dock_toggle_btn.pack(side="right", padx=12)

        self.dock_body = ctk.CTkFrame(self.bottom_dock_wrapper, fg_color="transparent")
        if not self.is_dock_collapsed:
            self.dock_body.pack(fill="x", padx=10, pady=(4, 6))
            self._render_dock_buttons()

    def _toggle_dock(self):
        self.is_dock_collapsed = not self.is_dock_collapsed
        self.bottom_dock_wrapper.destroy()
        self._build_bottom_dock_container()

    def _render_dock_buttons(self):
        for w in self.dock_body.winfo_children():
            w.destroy()

        t = self._t()
        win_w = self.winfo_width()
        is_multi = (win_w > 0 and win_w < 1080)

        if not is_multi:
            # 넓은 화면: 1줄 가로 정렬
            line = ctk.CTkFrame(self.dock_body, fg_color="transparent")
            line.pack(fill="x", expand=True)

            for key, name, def_w, def_h in self.ALL_TOOLS:
                is_on = (key in self.active_widgets)
                btn = ctk.CTkButton(
                    line, text=name, font=get_font(10, "bold"), height=32,
                    fg_color=t["accent"] if is_on else t["card_inner"],
                    hover_color=t["accent_hover"],
                    text_color="#ffffff" if is_on else t["text_main"],
                    border_width=1, border_color=t["accent"] if is_on else t["border"],
                    corner_radius=6,
                    command=lambda k=key: self.toggle_widget(k)
                )
                btn.pack(side="left", padx=2)

            # 우측 정렬 퀵 액션
            ctk.CTkButton(
                line, text="📐 자동 정렬", height=30, width=74, font=get_font(9, "bold"),
                fg_color=t["card_inner"], hover_color=t["border"], text_color=t["text_main"],
                corner_radius=6, command=self._tile_active_widgets
            ).pack(side="right", padx=2)

            ctk.CTkButton(
                line, text="🧹 전체 닫기", height=30, width=74, font=get_font(9, "bold"),
                fg_color=t["card_inner"], hover_color="#dc2626", text_color=t["text_sub"],
                corner_radius=6, command=self._close_all_widgets
            ).pack(side="right", padx=2)

        else:
            # 좁은 화면: 2줄 자동 줄바꿈 (버튼 잘림 0%)
            line1 = ctk.CTkFrame(self.dock_body, fg_color="transparent")
            line1.pack(fill="x", expand=True, pady=(0, 2))

            # 첫 번째 줄: 앞쪽 도구 5개
            for key, name, _, _ in self.ALL_TOOLS[:5]:
                is_on = (key in self.active_widgets)
                ctk.CTkButton(
                    line1, text=name, font=get_font(9, "bold"), height=28,
                    fg_color=t["accent"] if is_on else t["card_inner"],
                    hover_color=t["accent_hover"],
                    text_color="#ffffff" if is_on else t["text_main"],
                    border_width=1, border_color=t["accent"] if is_on else t["border"],
                    corner_radius=6,
                    command=lambda k=key: self.toggle_widget(k)
                ).pack(side="left", fill="x", expand=True, padx=2)

            line2 = ctk.CTkFrame(self.dock_body, fg_color="transparent")
            line2.pack(fill="x", expand=True, pady=(2, 0))

            # 두 번째 줄: 뒤쪽 도구 4개 + 정렬
            for key, name, _, _ in self.ALL_TOOLS[5:]:
                is_on = (key in self.active_widgets)
                ctk.CTkButton(
                    line2, text=name, font=get_font(9, "bold"), height=28,
                    fg_color=t["accent"] if is_on else t["card_inner"],
                    hover_color=t["accent_hover"],
                    text_color="#ffffff" if is_on else t["text_main"],
                    border_width=1, border_color=t["accent"] if is_on else t["border"],
                    corner_radius=6,
                    command=lambda k=key: self.toggle_widget(k)
                ).pack(side="left", fill="x", expand=True, padx=2)

            ctk.CTkButton(
                line2, text="📐 정렬", height=28, width=54, font=get_font(9, "bold"),
                fg_color=t["card_inner"], hover_color=t["border"], text_color=t["text_main"],
                corner_radius=6, command=self._tile_active_widgets
            ).pack(side="right", padx=2)

    # =========================================================================
    # 위젯 띄우기 / 닫기 / 토글 관리
    # =========================================================================
    def toggle_widget(self, key: str):
        if key in self.active_widgets:
            # 이미 떠 있으면 닫기
            self.close_widget(key)
        else:
            # 새로 띄우기
            self.spawn_widget(key)

    def spawn_widget(self, key: str, x=None, y=None, w=None, h=None):
        if key in self.active_widgets:
            self.active_widgets[key].lift()
            return self.active_widgets[key]

        # 기본 크기 및 좌표 산출
        tool_info = next((t for t in self.ALL_TOOLS if t[0] == key), None)
        title = tool_info[1] if tool_info else key
        def_w = w or (tool_info[2] if tool_info else 400)
        def_h = h or (tool_info[3] if tool_info else 300)

        dw = max(800, self.desktop_area.winfo_width())
        dh = max(500, self.desktop_area.winfo_height())

        if x is None or y is None:
            # 화면 내 적절한 위치 산출
            offset = (len(self.active_widgets) * 35) % 200
            px = min(dw - def_w - 20, 40 + offset)
            py = min(dh - def_h - 20, 30 + offset)
        else:
            px, py = x, y

        win = BoardWidgetWindow(self, key, title, px, py, def_w, def_h)
        self._populate_widget_content(key, win)
        self.active_widgets[key] = win

        self._render_dock_buttons()
        self._save_custom_state_if_needed()
        return win

    def close_widget(self, key: str):
        if key in self.active_widgets:
            win = self.active_widgets.pop(key)
            win.destroy()
            self._render_dock_buttons()
            self._save_custom_state_if_needed()

    def _close_all_widgets(self):
        for k in list(self.active_widgets.keys()):
            self.close_widget(k)

    def _tile_active_widgets(self):
        """현재 띄워진 위젯들을 화면에 바둑판 형태로 자동 정렬"""
        wins = list(self.active_widgets.values())
        if not wins: return

        dw = self.desktop_area.winfo_width() - 20
        dh = self.desktop_area.winfo_height() - 20
        n = len(wins)

        if n == 1:
            wins[0].current_x, wins[0].current_y = 40, 20
            wins[0].current_w, wins[0].current_h = dw - 80, dh - 40
            wins[0].configure(width=wins[0].current_w, height=wins[0].current_h)
            wins[0].place(x=wins[0].current_x, y=wins[0].current_y)
        elif n == 2:
            half_w = (dw - 30) // 2
            for i, w in enumerate(wins):
                w.current_x, w.current_y = 15 + i * (half_w + 15), 20
                w.current_w, w.current_h = half_w, dh - 40
                w.configure(width=w.current_w, height=w.current_h)
                w.place(x=w.current_x, y=w.current_y)
        elif n <= 4:
            hw = (dw - 30) // 2
            hh = (dh - 30) // 2
            for i, w in enumerate(wins):
                r, c = i // 2, i % 2
                w.current_x, w.current_y = 15 + c * (hw + 15), 15 + r * (hh + 15)
                w.current_w, w.current_h = hw, hh
                w.configure(width=w.current_w, height=w.current_h)
                w.place(x=w.current_x, y=w.current_y)
        else:
            # 3열 타일
            cols = 3
            rows = (n + cols - 1) // cols
            cw = (dw - (cols + 1) * 10) // cols
            ch = (dh - (rows + 1) * 10) // rows
            for i, w in enumerate(wins):
                r, c = i // cols, i % cols
                w.current_x, w.current_y = 10 + c * (cw + 10), 10 + r * (ch + 10)
                w.current_w, w.current_h = cw, ch
                w.configure(width=w.current_w, height=w.current_h)
                w.place(x=w.current_x, y=w.current_y)

        self.desktop_area.update_idletasks()
        for w in wins:
            w._on_content_resized()

    # =========================================================================
    # 상단 탭 시스템 (사전 설정 탭 vs 커스텀 탭)
    # =========================================================================
    def _render_tabs(self):
        for w in self.tab_row.winfo_children():
            w.destroy()

        t = self._t()
        std_tabs = [
            ("std_split", "⚖️ 올인원 모드"),
            ("std_tools", "🎯 수업도구 집중"),
            ("std_board", "📋 학급 게시판"),
        ]
        for tid, tname in std_tabs:
            is_act = (self.active_tab_id == tid)
            btn = ctk.CTkButton(
                self.tab_row, text=tname, font=get_font(10, "bold"), height=26,
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

            c_frame = ctk.CTkFrame(self.tab_row, fg_color=t["accent"] if is_act else t["card_inner"], corner_radius=6, height=26)
            c_frame.pack(side="left", padx=2)

            ctk.CTkButton(
                c_frame, text=cname, font=get_font(10, "bold"), height=24,
                fg_color="transparent", hover_color=t["accent_hover"],
                text_color="#ffffff" if is_act else t["text_main"],
                command=lambda k=cid: self._switch_tab(k)
            ).pack(side="left", padx=(4, 1))

            ctk.CTkButton(
                c_frame, text="✏️", width=16, height=18, font=get_font(8),
                fg_color="transparent", hover_color=t["card"],
                text_color="#ffffff" if is_act else t["text_sub"],
                command=lambda k=cid, cn=cname: self._rename_custom_tab(k, cn)
            ).pack(side="left", padx=1)

            ctk.CTkButton(
                c_frame, text="✕", width=16, height=18, font=get_font(8, "bold"),
                fg_color="transparent", hover_color="#ef4444",
                text_color="#ffffff" if is_act else t["text_sub"],
                command=lambda k=cid: self._delete_custom_tab(k)
            ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            self.tab_row, text="➕ 새 탭", font=get_font(10, "bold"), height=26, width=56,
            fg_color=t["card_inner"], hover_color=t["accent"], text_color=t["text_main"],
            corner_radius=6, command=self._add_custom_tab
        ).pack(side="left", padx=4)

    def _switch_tab(self, tab_id: str):
        self.active_tab_id = tab_id
        self._close_all_widgets()

        if tab_id == "std_split":
            # 올인원 기본 배치 (타이머 + 시간표 + 급식)
            self.spawn_widget("timer", x=30, y=20, w=580, h=420)
            self.spawn_widget("timetable", x=630, y=20, w=300, h=420)
            self.spawn_widget("meal", x=950, y=20, w=300, h=420)
        elif tab_id == "std_tools":
            # 수업 도구 집중 (타이머 + 주사위)
            self.spawn_widget("timer", x=40, y=30, w=580, h=480)
            self.spawn_widget("dice", x=640, y=30, w=560, h=480)
        elif tab_id == "std_board":
            # 게시판 3열 (시간표 + 급식 + 알림장)
            self.spawn_widget("timetable", x=30, y=30, w=380, h=520)
            self.spawn_widget("meal", x=430, y=30, w=380, h=520)
            self.spawn_widget("memo", x=830, y=30, w=380, h=520)
        else:
            # 커스텀 탭 복원
            for ctab in self.custom_tabs:
                if ctab["id"] == tab_id:
                    for w_cfg in ctab.get("widgets", []):
                        self.spawn_widget(w_cfg["key"], w_cfg.get("x"), w_cfg.get("y"), w_cfg.get("w"), w_cfg.get("h"))
                    break

        self._render_tabs()

    def _apply_initial_layout(self):
        self._switch_tab(self.active_tab_id)

    def _add_custom_tab(self):
        name = simpledialog.askstring("새 탭 만들기", "새 커스텀 보드 탭의 이름을 입력하세요:\n(예: 1교시 수학, 모둠 활동실)")
        if name and name.strip():
            new_tab = {
                "id": f"custom_{random.randint(1000, 9999)}",
                "name": name.strip(),
                "widgets": []
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
            self._switch_tab("std_split")

    def _save_custom_state_if_needed(self):
        if not self.active_tab_id.startswith("custom_"):
            return
        # 현재 커스텀 탭의 위젯들 저장
        w_list = []
        for k, win in self.active_widgets.items():
            w_list.append({
                "key": k,
                "x": win.current_x,
                "y": win.current_y,
                "w": win.current_w,
                "h": win.current_h
            })
        for ctab in self.custom_tabs:
            if ctab["id"] == self.active_tab_id:
                ctab["widgets"] = w_list
                break
        self._save_custom_tabs()

    # =========================================================================
    # 위젯 내부 컨텐츠 주입 (8개 위젯 구현체)
    # =========================================================================
    def _populate_widget_content(self, key: str, win: BoardWidgetWindow):
        t = self._t()
        p = win.content_area

        if key == "timer":
            self._build_timer_content(win, p, t)
        elif key == "picker":
            self._build_picker_content(win, p, t)
        elif key == "dice":
            self._build_dice_content(win, p, t)
        elif key == "wheel":
            self._build_wheel_content(win, p, t)
        elif key == "scoreboard":
            self._build_scoreboard_content(win, p, t)
        elif key == "drawing":
            self._build_drawing_content(win, p, t)
        elif key == "timetable":
            self._build_timetable_content(win, p, t)
        elif key == "meal":
            self._build_meal_content(win, p, t)
        elif key == "memo":
            self._build_memo_content(win, p, t)

    # 1. 타이머 위젯
    def _build_timer_content(self, win, p, t):
        lbl = ctk.CTkLabel(
            p, text=self._fmt_timer(self.timer_rem_sec),
            font=ctk.CTkFont(family="Malgun Gothic", size=64, weight="bold"),
            text_color=t["accent"]
        )
        lbl.pack(expand=True, pady=4)
        win.timer_lbl = lbl

        p_row = ctk.CTkFrame(p, fg_color="transparent")
        p_row.pack(pady=4)
        for s, l in [(60, "1분"), (180, "3분"), (300, "5분"), (600, "10분")]:
            ctk.CTkButton(
                p_row, text=l, width=54, height=28, font=get_font(9, "bold"),
                fg_color=t["card_inner"], hover_color=t["accent"], text_color=t["text_main"],
                command=lambda sec=s, w=win: self._preset_timer(sec, w)
            ).pack(side="left", padx=2)

        c_row = ctk.CTkFrame(p, fg_color="transparent")
        c_row.pack(pady=(4, 10))

        btn_run = ctk.CTkButton(
            c_row, text="▶ 시작", width=110, height=36, font=get_font(12, "bold"),
            fg_color=t["accent"], hover_color=t["accent_hover"],
            command=lambda w=win: self._toggle_timer(w)
        )
        btn_run.pack(side="left", padx=4)
        win.btn_run = btn_run

        ctk.CTkButton(
            c_row, text="↺ 리셋", width=70, height=36, font=get_font(11, "bold"),
            fg_color=t["card_inner"], hover_color=t["border"], text_color=t["text_main"],
            command=lambda w=win: self._reset_timer(w)
        ).pack(side="left", padx=4)

        def _resize():
            sz = max(40, min(120, int(min(win.current_w * 0.22, win.current_h * 0.35))))
            lbl.configure(font=ctk.CTkFont(family="Malgun Gothic", size=sz, weight="bold"))
        win._on_content_resized = _resize

    def _fmt_timer(self, s: int) -> str:
        return f"{s // 60:02d}:{s % 60:02d}"

    def _preset_timer(self, s, win):
        self._reset_timer(win)
        self.timer_total_sec = s
        self.timer_rem_sec = s
        if hasattr(win, "timer_lbl"):
            win.timer_lbl.configure(text=self._fmt_timer(s))

    def _toggle_timer(self, win):
        if self.timer_running:
            self.timer_running = False
            if self._timer_job: self.after_cancel(self._timer_job)
            win.btn_run.configure(text="▶ 재개", fg_color=self._t()["accent"])
        else:
            self.timer_running = True
            win.btn_run.configure(text="⏸ 일시정지", fg_color="#ea580c")
            self._timer_tick(win)

    def _timer_tick(self, win):
        if not self.timer_running: return
        if self.timer_rem_sec > 0:
            self.timer_rem_sec -= 1
            if hasattr(win, "timer_lbl") and win.timer_lbl.winfo_exists():
                win.timer_lbl.configure(text=self._fmt_timer(self.timer_rem_sec))
            self._timer_job = self.after(1000, lambda: self._timer_tick(win))
        else:
            self.timer_running = False
            if hasattr(win, "btn_run") and win.btn_run.winfo_exists():
                win.btn_run.configure(text="▶ 시작", fg_color=self._t()["accent"])
            if hasattr(win, "timer_lbl") and win.timer_lbl.winfo_exists():
                win.timer_lbl.configure(text="시간 종료!", text_color="#ef4444")
            try: winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception: pass

    def _reset_timer(self, win):
        self.timer_running = False
        if self._timer_job: self.after_cancel(self._timer_job)
        self.timer_rem_sec = self.timer_total_sec
        if hasattr(win, "timer_lbl") and win.timer_lbl.winfo_exists():
            win.timer_lbl.configure(text=self._fmt_timer(self.timer_rem_sec), text_color=self._t()["accent"])
        if hasattr(win, "btn_run") and win.btn_run.winfo_exists():
            win.btn_run.configure(text="▶ 시작", fg_color=self._t()["accent"])

    # 2. 발표자 뽑기 위젯
    def _build_picker_content(self, win, p, t):
        ctrl = ctk.CTkFrame(p, fg_color="transparent")
        ctrl.pack(fill="x", pady=2)

        p_mode = ctk.CTkSegmentedButton(ctrl, values=["학생이름", "번호"], font=get_font(9, "bold"), height=24)
        p_mode.set("학생이름")
        p_mode.pack(side="left", padx=2)
        win.p_mode = p_mode

        p_gen = ctk.CTkSegmentedButton(ctrl, values=["전체", "👦남", "👧여"], font=get_font(9, "bold"), height=24)
        p_gen.set("전체")
        p_gen.pack(side="left", padx=2)
        win.p_gen = p_gen

        disp = ctk.CTkFrame(p, fg_color=t["card_inner"], corner_radius=10)
        disp.pack(fill="both", expand=True, padx=4, pady=4)

        p_lbl = ctk.CTkLabel(disp, text="?", font=ctk.CTkFont(family="Malgun Gothic", size=52, weight="bold"), text_color=t["accent"])
        p_lbl.pack(expand=True)
        win.p_lbl = p_lbl

        b_row = ctk.CTkFrame(p, fg_color="transparent")
        b_row.pack(pady=3)

        btn_p = ctk.CTkButton(
            b_row, text="🎲 추첨하기!", width=120, height=36, font=get_font(12, "bold"),
            fg_color=t["accent"], hover_color=t["accent_hover"],
            command=lambda w=win: self._do_pick(w)
        )
        btn_p.pack(side="left", padx=3)
        win.btn_p = btn_p

        ctk.CTkButton(
            b_row, text="초기화", width=64, height=36, font=get_font(10, "bold"),
            fg_color=t["card_inner"], hover_color=t["border"], text_color=t["text_main"],
            command=lambda w=win: self._reset_pick_history(w)
        ).pack(side="left", padx=3)

        hist = ctk.CTkScrollableFrame(p, height=40, fg_color="transparent")
        hist.pack(fill="x", padx=4, pady=(0, 4))
        h_lbl = ctk.CTkLabel(hist, text="기록: 없음", font=get_font(9), text_color=t["text_sub"], wraplength=400)
        h_lbl.pack(anchor="w")
        win.h_lbl = h_lbl

    def _do_pick(self, win):
        if self.picker_running: return
        is_name = ("이름" in win.p_mode.get())
        g_raw = win.p_gen.get()
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
            win.p_lbl.configure(text="추첨 완료!", text_color="#10b981")
            win.h_lbl.configure(text="모든 대상이 다 뽑혔습니다!")
            return

        self.picker_running = True
        win.btn_p.configure(state="disabled")

        def _anim(step=0):
            if step < 12:
                if win.winfo_exists():
                    win.p_lbl.configure(text=random.choice(cands), text_color=self._t()["text_main"])
                self.after(50 + step * 8, lambda: _anim(step + 1))
            else:
                winner = random.choice(avail)
                self.picker_picked.append(winner)
                if win.winfo_exists():
                    win.p_lbl.configure(text=winner, text_color="#10b981")
                    win.h_lbl.configure(text=f"기록 ({len(self.picker_picked)}명): {', '.join(self.picker_picked)}")
                    win.btn_p.configure(state="normal")
                self.picker_running = False
                try: winsound.MessageBeep(winsound.MB_OK)
                except Exception: pass
        _anim()

    def _reset_pick_history(self, win):
        self.picker_picked.clear()
        if hasattr(win, "p_lbl"):
            win.p_lbl.configure(text="?", text_color=self._t()["accent"])
        if hasattr(win, "h_lbl"):
            win.h_lbl.configure(text="기록: 없음")

    # 3. 주사위 & 통계 위젯
    def _build_dice_content(self, win, p, t):
        ctrl = ctk.CTkFrame(p, fg_color="transparent")
        ctrl.pack(fill="x", pady=2)

        ctk.CTkLabel(ctrl, text="개수:", font=get_font(9, "bold"), text_color=t["text_sub"]).pack(side="left")
        d_cnt = ctk.CTkSegmentedButton(ctrl, values=["1개", "2개"], font=get_font(9, "bold"), height=22, command=lambda v: setattr(self, "dice_count", 2 if v=="2개" else 1))
        d_cnt.set("1개" if self.dice_count == 1 else "2개")
        d_cnt.pack(side="left", padx=4)

        ctk.CTkLabel(ctrl, text="면수:", font=get_font(9, "bold"), text_color=t["text_sub"]).pack(side="left", padx=(6, 0))
        d_face = ctk.CTkComboBox(ctrl, values=["D6 (6면)", "D4 (4면)", "D8 (8면)", "D10 (10면)", "D12 (12면)", "D20 (20면)"], width=96, height=22, font=get_font(9, "bold"), state="readonly")
        d_face.set(f"D{self.dice_faces} ({self.dice_faces}면)")
        d_face.pack(side="left", padx=2)
        d_face.configure(command=lambda v, w=win: self._on_dice_face_changed(v, w))

        split = ctk.CTkFrame(p, fg_color="transparent")
        split.pack(fill="both", expand=True, pady=4)

        d_box = ctk.CTkFrame(split, fg_color=t["card_inner"], corner_radius=10)
        d_box.pack(side="left", fill="both", expand=True, padx=(0, 3))

        d_lbl = ctk.CTkLabel(d_box, text="🎲 6", font=ctk.CTkFont(family="Malgun Gothic", size=52, weight="bold"), text_color=t["accent"])
        d_lbl.pack(expand=True)
        win.d_lbl = d_lbl

        d_sub = ctk.CTkLabel(d_box, text="결과: 6", font=get_font(10, "bold"), text_color=t["text_main"])
        d_sub.pack(pady=(0, 6))
        win.d_sub = d_sub

        s_box = ctk.CTkFrame(split, fg_color=t["card_inner"], corner_radius=10)
        s_box.pack(side="right", fill="both", expand=True, padx=(3, 0))
        ctk.CTkLabel(s_box, text="📊 비·비율·백분율 통계", font=get_font(9, "bold"), text_color=t["accent"]).pack(pady=3)

        tbl = ctk.CTkScrollableFrame(s_box, fg_color="transparent")
        tbl.pack(fill="both", expand=True, padx=4, pady=2)
        win.tbl = tbl
        self._render_dice_table(win)

        b_row = ctk.CTkFrame(p, fg_color="transparent")
        b_row.pack(pady=(2, 6))

        btn_roll = ctk.CTkButton(b_row, text="🎲 굴리기!", width=120, height=34, font=get_font(11, "bold"), fg_color=t["accent"], command=lambda w=win: self._roll_dice(w))
        btn_roll.pack(side="left", padx=3)
        win.btn_roll = btn_roll

        ctk.CTkButton(b_row, text="초기화", width=64, height=34, font=get_font(10, "bold"), fg_color=t["card_inner"], hover_color="#dc2626", command=lambda w=win: self._reset_dice_stats(w)).pack(side="left", padx=3)

    def _on_dice_face_changed(self, val, win):
        self.dice_faces = int(val.split("(")[1].replace("면)", ""))
        self._reset_dice_stats(win)

    def _roll_dice(self, win):
        if self.dice_rolling: return
        self.dice_rolling = True
        win.btn_roll.configure(state="disabled")

        chars = {1:"⚀", 2:"⚁", 3:"⚂", 4:"⚃", 5:"⚄", 6:"⚅"}

        def _anim(step=0):
            if step < 10:
                r1 = random.randint(1, self.dice_faces)
                r2 = random.randint(1, self.dice_faces) if self.dice_count == 2 else None
                if self.dice_faces == 6 and r1 in chars and (r2 is None or r2 in chars):
                    txt = chars[r1] if r2 is None else f"{chars[r1]} {chars[r2]}"
                    win.d_lbl.configure(text=f"🎲 {txt}", font=ctk.CTkFont(family="Malgun Gothic", size=44, weight="bold"))
                else:
                    txt = str(r1) if r2 is None else f"{r1} + {r2}"
                    win.d_lbl.configure(text=f"🎲 {txt}", font=ctk.CTkFont(family="Malgun Gothic", size=44, weight="bold"))
                self.after(50 + step * 8, lambda: _anim(step + 1))
            else:
                f1 = random.randint(1, self.dice_faces)
                f2 = random.randint(1, self.dice_faces) if self.dice_count == 2 else None
                if self.dice_faces == 6 and f1 in chars and (f2 is None or f2 in chars):
                    txt = chars[f1] if f2 is None else f"{chars[f1]} {chars[f2]}"
                    win.d_lbl.configure(text=txt, font=ctk.CTkFont(family="Segoe UI Symbol", size=48 if f2 else 60))
                else:
                    txt = str(f1) if f2 is None else f"{f1} + {f2}"
                    win.d_lbl.configure(text=f"🎲 {txt}", font=ctk.CTkFont(family="Malgun Gothic", size=44, weight="bold"))

                if f2 is not None:
                    win.d_sub.configure(text=f"A={f1}, B={f2} (합={f1+f2})")
                else:
                    win.d_sub.configure(text=f"결과: {f1}")

                self.dice_counts[f1] = self.dice_counts.get(f1, 0) + 1
                if f2 is not None:
                    self.dice_counts[f2] = self.dice_counts.get(f2, 0) + 1

                self._render_dice_table(win)
                self.dice_rolling = False
                win.btn_roll.configure(state="normal")
                try: winsound.MessageBeep(winsound.MB_OK)
                except Exception: pass
        _anim()

    def _render_dice_table(self, win):
        if not hasattr(win, "tbl") or not win.tbl.winfo_exists(): return
        for c in win.tbl.winfo_children(): c.destroy()

        t = self._t()
        tot = sum(self.dice_counts.values())
        if tot == 0:
            ctk.CTkLabel(win.tbl, text="주사위를 굴리면\n통계가 집계됩니다.", font=get_font(9), text_color=t["text_sub"]).pack(pady=20)
            return

        for face in range(1, min(self.dice_faces + 1, 21)):
            cnt = self.dice_counts.get(face, 0)
            ratio = (cnt / tot) if tot > 0 else 0.0
            pct = ratio * 100

            r = ctk.CTkFrame(win.tbl, fg_color="transparent")
            r.pack(fill="x", pady=1)
            ctk.CTkLabel(r, text=f"{face}눈", width=26, font=get_font(8, "bold"), text_color=t["text_main"]).pack(side="left")
            ctk.CTkLabel(r, text=f"{cnt}회", width=30, font=get_font(8), text_color=t["text_sub"]).pack(side="left")
            ctk.CTkLabel(r, text=f"{cnt}:{tot}", width=46, font=ctk.CTkFont(family="Malgun Gothic", size=8, weight="bold"), text_color=t["text_sub"]).pack(side="left")
            ctk.CTkLabel(r, text=f"{pct:.1f}%", width=46, font=ctk.CTkFont(family="Malgun Gothic", size=8, weight="bold"), text_color="#10b981").pack(side="left")

    def _reset_dice_stats(self, win):
        self.dice_counts.clear()
        if hasattr(win, "d_lbl"):
            win.d_lbl.configure(text=f"🎲 {self.dice_faces}")
            win.d_sub.configure(text=f"면수: D{self.dice_faces}")
        self._render_dice_table(win)

    # 4. 돌림판 위젯
    def _build_wheel_content(self, win, p, t):
        ctk.CTkLabel(p, text="🎡", font=ctk.CTkFont(size=64)).pack(expand=True)
        res_lbl = ctk.CTkLabel(p, text="돌림판을 돌려보세요!", font=get_font(13, "bold"), text_color=t["text_main"])
        res_lbl.pack(pady=6)

        def _spin():
            items = ["1모둠", "2모둠", "3모둠", "4모둠", "5모둠", "6모둠"]
            def _step(c=0):
                if c < 14:
                    res_lbl.configure(text=f"▶ {random.choice(items)}", text_color=t["accent"])
                    self.after(50 + c * 15, lambda: _step(c + 1))
                else:
                    winner = random.choice(items)
                    res_lbl.configure(text=f"🎉 당첨: {winner}!", text_color="#10b981")
                    try: winsound.MessageBeep(winsound.MB_OK)
                    except Exception: pass
            _step()

        ctk.CTkButton(p, text="🎡 돌리기!", width=130, height=36, font=get_font(12, "bold"), fg_color=t["accent"], command=_spin).pack(pady=(0, 12))

    # 5. 점수판 위젯
    def _build_scoreboard_content(self, win, p, t):
        grid = ctk.CTkFrame(p, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=4, pady=4)

        lbls = {}
        for idx, (grp, sc) in enumerate(self.scores.items()):
            r, c = idx // 3, idx % 3
            card = ctk.CTkFrame(grid, fg_color=t["card_inner"], corner_radius=8)
            card.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")
            grid.grid_columnconfigure(c, weight=1)
            grid.grid_rowconfigure(r, weight=1)

            ctk.CTkLabel(card, text=grp, font=get_font(10, "bold"), text_color=t["text_sub"]).pack(pady=(4, 0))
            lbl = ctk.CTkLabel(card, text=str(sc), font=ctk.CTkFont(family="Malgun Gothic", size=22, weight="bold"), text_color=t["accent"])
            lbl.pack(expand=True)
            lbls[grp] = lbl

            def _chg(g=grp, delta=1):
                self.scores[g] = max(0, self.scores[g] + delta)
                lbls[g].configure(text=str(self.scores[g]))

            b_row = ctk.CTkFrame(card, fg_color="transparent")
            b_row.pack(pady=(0, 4))
            ctk.CTkButton(b_row, text="+1", width=36, height=22, font=get_font(8, "bold"), command=lambda g=grp: _chg(g, 1)).pack(side="left", padx=1)
            ctk.CTkButton(b_row, text="-1", width=36, height=22, font=get_font(8, "bold"), fg_color="#334155", command=lambda g=grp: _chg(g, -1)).pack(side="left", padx=1)

    # 6. 보드 전용 인터랙티브 판서 위젯 (칠판 / 화이트보드 / 텍스트 입력)
    def _build_drawing_content(self, win, p, t):
        BoardDrawingCanvasWidget(p, win, t)

    # 7. 시간표 위젯 (완벽 마우스 휠 스크롤)
    def _build_timetable_content(self, win, p, t):
        scroll = ctk.CTkScrollableFrame(p, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        _, _, items = timetable_manager.get_today_schedule_items()
        now_s = datetime.datetime.now().strftime("%H:%M")
        for it in items:
            is_cur = (it["start"] <= now_s <= it["end"])
            r = ctk.CTkFrame(scroll, fg_color=t["accent"] if is_cur else t["card_inner"], corner_radius=6)
            r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text=f"{it['name']} ({it['start']})", font=get_font(8, "bold"), text_color="#ffffff" if is_cur else t["text_sub"]).pack(side="left", padx=6, pady=3)
            sub = "점심시간" if it.get("is_lunch") else it.get("subject", "")
            ctk.CTkLabel(r, text=sub, font=get_font(9, "bold"), text_color="#ffffff" if is_cur else t["text_main"]).pack(side="right", padx=6)

    # 8. 급식 식단 위젯 (완벽 마우스 휠 스크롤)
    def _build_meal_content(self, win, p, t):
        scroll = ctk.CTkScrollableFrame(p, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        today = datetime.date.today()
        ok, meal_info, _ = neis_client.get_meal_for_date(today)
        if not ok or not meal_info.get("dishes"):
            ctk.CTkLabel(scroll, text="오늘 등록된 급식이 없습니다.", font=get_font(9), text_color=t["text_sub"]).pack(pady=20)
        else:
            for d in meal_info.get("dishes", []):
                ctk.CTkLabel(scroll, text=f"• {d}", font=get_font(9), text_color=t["text_main"], anchor="w").pack(fill="x", pady=1, padx=4)

    # 9. 알림장 위젯
    def _build_memo_content(self, win, p, t):
        txt = ctk.CTkTextbox(p, font=get_font(10), fg_color=t["card_inner"], text_color=t["text_main"])
        txt.pack(fill="both", expand=True, padx=4, pady=4)
        txt.insert("1.0", "• 1교시: 수학익힘책 42~45쪽\n• 5교시: 체육복 착용\n• 하교 후 손 씻기!\n• 준비물 챙기기")

    # =========================================================================
    # 유틸리티 (창 리사이즈, 시계, 테마, 전체화면, 닫기)
    # =========================================================================
    def _on_window_configure(self, event):
        if event.widget == self:
            w = event.width
            is_multi = (w < 1080)
            if self._last_wrap_state != is_multi:
                self._last_wrap_state = is_multi
                if hasattr(self, "dock_body") and self.dock_body.winfo_exists() and not self.is_dock_collapsed:
                    self._render_dock_buttons()

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
        self._apply_initial_layout()

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
        self._apply_initial_layout()

    def close(self):
        StudentDisplayWindow._instance = None
        self.destroy()
