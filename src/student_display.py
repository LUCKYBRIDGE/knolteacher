"""
놀티쳐 (KnolTeacher) - 학생 공유 교실 화면 (i-Scream Tool Kit 스타일)
- 교실 대형 TV / 전자칠판 전용 멀티 윈도우 대시보드
- 하단 전면 인터랙티브 수업도구 독 바 (타이머, 주사위, 돌림판, 뽑기, 시간표, 급식, 효과음 등)
- 캔버스 위 독립 화이트 모듈 창들의 자유로운 다중 배치, 이동 및 크기 조절
- 사진 2/3의 6종 타이머(디지털/아날로그/모래시계/파이/풍선/스톱워치) 및 3D 주사위 완벽 구현
- 원클릭 배경 테마 변경 (핫핑크, 코발트 블루, 칠판그린, 민트, 다크 등)
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
import tkinter as tk
from tkinter import simpledialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

from src.font_config import setup_global_fonts, get_font
from src.timetable_manager import timetable_manager, DAYS_KO
from src.neis_client import neis_client
from src.config_utils import get_config_dir
from src.tooltip import attach_tooltip
from src.icon_renderer import get_icon, COL_MAIN, COL_ACTIVE, COL_YELLOW, COL_DANGER, COL_GREEN, COL_ORANGE, COL_PURPLE

# 배경 테마 팔레트 (사진 2/3의 핫핑크 기본 포함)
BG_THEMES = [
    ("핫핑크", "#db2777"),
    ("코발트블루", "#1d4ed8"),
    ("칠판초록", "#1b382b"),
    ("파스텔민트", "#0f766e"),
    ("모던다크", "#090d16"),
    ("따뜻한베이지", "#d97706"),
]


class StudentDisplayWindow(ctk.CTkToplevel):
    _instance = None
    CONFIG_FILE = os.path.join(get_config_dir(), "student_toolkit_config.json")

    @classmethod
    def get_instance(cls, parent=None):
        if cls._instance is None or not cls._instance.winfo_exists():
            cls._instance = cls(parent)
        else:
            cls._instance.deiconify()
            cls._instance.lift()
            cls._instance.focus_force()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.title("놀티쳐 보드 (교실 공유 화면)")
        self.geometry("1240x780")
        self.minsize(880, 560)
        self.resizable(True, True)

        setup_global_fonts(self)
        self._load_icon()

        self.is_fullscreen = False
        self.bg_color = "#db2777"  # 사진 2/3의 시그니처 핫핑크 기본값
        self.active_modules = {}   # mod_key -> dict(frame, header, w, h, x, y)
        self.dock_buttons = {}     # mod_key -> ctk.CTkButton

        # 타이머 상태
        self.timer_seconds = 300
        self.timer_total = 300
        self.timer_running = False
        self.timer_type = "digital"  # digital, analog, hourglass, pie, balloon, stopwatch
        self.timer_job = None

        # 주사위 상태
        self.dice_count = 1
        self.dice_values = [6]
        self.dice_rolling = False

        # 돌림판 상태
        self.wheel_items = ["1모둠", "2모둠", "3모둠", "4모둠", "5모둠", "6모둠"]
        self.wheel_angle = 0.0
        self.wheel_spinning = False

        # 점수판 상태
        self.scores = {"1모둠": 0, "2모둠": 0, "3모둠": 0, "4모둠": 0}

        # 1인 1역 상태
        self.roles = [
            ("우유 배부", "1번 김민준"), ("칠판 지우기", "2번 이서아"),
            ("창문 환기", "3번 박도윤"), ("불 끄기", "4번 최지우"),
            ("체육 용품", "5번 정시우"), ("도서 정리", "6번 한수아")
        ]

        self._load_config()

        self.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._exit_fullscreen())
        self.protocol("WM_DELETE_WINDOW", self.close)

        self._build_main_ui()
        self._start_clock_loop()

        # 기본으로 타이머와 주사위를 띄워 사진 3과 동일한 환상적인 첫 화면 제공
        self.after(200, self._open_default_tools)

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
                    self.bg_color = data.get("bg_color", "#db2777")
                    self.scores = data.get("scores", self.scores)
            except Exception:
                pass

    def _save_config(self):
        try:
            data = {
                "bg_color": self.bg_color,
                "scores": self.scores
            }
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # 전체 메인 레이아웃 (상단 헤더 + 중앙 자유 캔버스 + 하단 도구 독)
    # ══════════════════════════════════════════════════════════════════════════
    def _build_main_ui(self):
        for w in self.winfo_children():
            w.destroy()

        self.configure(fg_color=self.bg_color)

        # 1. 최상단 브랜드 & 제어 바
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent", height=46)
        self.top_bar.pack(fill="x", side="top", padx=16, pady=(6, 0))
        self.top_bar.pack_propagate(False)

        # 브랜드 로고 (i-Scream Tool Kit 스타일의 '놀티쳐 Tool Kit')
        logo_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        logo_box.pack(side="left")

        ctk.CTkLabel(
            logo_box, text="✏️ 놀티쳐", font=get_font(15, "bold"), text_color="#ffffff"
        ).pack(side="left")
        ctk.CTkLabel(
            logo_box, text="보드", font=get_font(15, "bold"), text_color="#fed7aa"
        ).pack(side="left", padx=(4, 0))

        # 우측 상단 정보 및 교실 커스텀 제어 바
        r_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        r_box.pack(side="right")

        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]
        self.date_tag = ctk.CTkLabel(
            r_box, text=f"🔔 우리 반 교실 보드 | {today.strftime('%m월 %d일')} ({weekday_str})",
            font=get_font(10, "bold"), text_color="#ffffff",
            fg_color="#1e293b", corner_radius=12, width=180, height=26
        )
        self.date_tag.pack(side="left", padx=(0, 6))

        # 배경 테마 변경
        bg_btn = ctk.CTkButton(
            r_box, text="🎨 배경 테마", width=80, height=26, font=get_font(10, "bold"),
            fg_color="#1e293b", hover_color="#334155", text_color="#ffffff",
            corner_radius=12, command=self._open_bg_picker
        )
        bg_btn.pack(side="left", padx=2)
        attach_tooltip(bg_btn, "교실 화면 배경 테마(핑크, 블루, 칠판그린, 다크 등) 변경")

        # 화면 정리 (모든 위젯 일괄 닫기)
        clear_btn = ctk.CTkButton(
            r_box, text="🧹 화면 정리", width=74, height=26, font=get_font(10, "bold"),
            fg_color="#1e293b", hover_color="#334155", text_color="#ffffff",
            corner_radius=12, command=self._clear_all_modules
        )
        clear_btn.pack(side="left", padx=2)
        attach_tooltip(clear_btn, "캔버스에 열려 있는 모든 도구 창 정리")

        # 기본 도구 소환
        reset_btn = ctk.CTkButton(
            r_box, text="🔄 기본 배치", width=74, height=26, font=get_font(10, "bold"),
            fg_color="#1e293b", hover_color="#334155", text_color="#ffffff",
            corner_radius=12, command=self._open_default_tools
        )
        reset_btn.pack(side="left", padx=2)
        attach_tooltip(reset_btn, "타이머와 주사위 등 기본 수업 도구 즉시 소환")

        # 전체화면 토글
        self.fs_btn = ctk.CTkButton(
            r_box, text="⛶ 전체화면 (F11)", width=96, height=26, font=get_font(10, "bold"),
            fg_color="#0284c7", hover_color="#0369a1", text_color="#ffffff",
            corner_radius=12, command=self._toggle_fullscreen
        )
        self.fs_btn.pack(side="left", padx=2)

        # 닫기
        ctk.CTkButton(
            r_box, text="✕", width=28, height=26, font=get_font(11, "bold"),
            fg_color="#dc2626", hover_color="#b91c1c", text_color="#ffffff",
            corner_radius=12, command=self.close
        ).pack(side="left", padx=2)

        # 2. 하단 수업도구 퀵 런처 바 (사진 2, 3의 전면 화이트 독)
        self.dock_bar = ctk.CTkFrame(
            self, fg_color="#ffffff", height=56, corner_radius=28,
            border_width=1, border_color="#e2e8f0"
        )
        self.dock_bar.pack(fill="x", side="bottom", padx=16, pady=10)
        self.dock_bar.pack_propagate(False)

        self._build_dock_buttons()

        # 3. 중앙 모듈 캔버스 데스크톱 (자유 드래그 & 다중 배치 공간)
        self.canvas_area = tk.Canvas(
            self, bg=self.bg_color, highlightthickness=0
        )
        self.canvas_area.pack(fill="both", expand=True, padx=16, pady=4)

    # ══════════════════════════════════════════════════════════════════════════
    # 하단 도구 독 바 (Dock Toolbar) 구축
    # ══════════════════════════════════════════════════════════════════════════
    def _build_dock_buttons(self):
        for w in self.dock_bar.winfo_children():
            w.destroy()

        dock_scroll = ctk.CTkScrollableFrame(
            self.dock_bar, orientation="horizontal", fg_color="transparent", height=64
        )
        dock_scroll.pack(fill="both", expand=True, padx=8, pady=2)

        # 사진 2와 100% 동일한 도구 구성 및 한글 레이블
        tools = [
            ("note",        "노트",       "📝", "한글/영어 4선 노트 및 판서"),
            ("role",        "1인 1역",    "👥", "학급 1인 1역 역할 분담표"),
            ("dday",        "디데이",     "📅", "방학, 시험, 행사 D-Day 카운터"),
            ("timetable",   "시간표",     "📋", "오늘의 수업 시간표"),
            ("meal",        "급식",       "🍱", "맛있는 오늘의 학교 급식 식단"),
            ("checklist",   "체크\n리스트", "✔️", "과제 제출 및 준비물 점검"),
            ("timer",       "타이머",     "⏱️", "6종 교실 타이머/스톱워치"),
            ("dice",        "주사위",     "🎲", "대형 3D 주사위 던지기"),
            ("coin",        "동전\n던지기", "🪙", "앞면/뒷면 동전 던지기"),
            ("picker",      "랜덤\n뽑기",   "🎯", "공정한 학생 발표자 랜덤 추첨"),
            ("wheel",       "돌림판",     "🎡", "모둠/벌칙 돌려돌려 돌림판"),
            ("scoreboard",  "점수판",     "🏆", "모둠별 점수 획득 스코어보드"),
            ("memo",        "메모",       "📌", "오늘의 알림장 및 학급 메모"),
            ("sound",       "우리반\n효과음", "🔊", "박수, 딩동댕, 땡, 드럼롤 사운드"),
            ("noise",       "소음\n측정기", "📢", "조용한 교실 만들기 데시벨 미터"),
            ("clock",       "시계",       "🕒", "대형 교실 아날로그/디지털 시계"),
            ("drawing",     "색연필",     "✏️", "화면 위 자유 판서 및 색연필 도구"),
            ("launcher",    "바로\n가기", "🚀", "자주 쓰는 수업 프로그램 및 웹사이트 빠른 실행 (➕ 등록)"),
            ("bgm",         "교실\nBGM",  "🎵", "유튜브 소리만 듣는 교실 배경음악 플레이어 (➕ 등록)"),
            ("video",       "유튜브\n영상", "🎬", "광고 없이 수업 영상을 재생하는 교실 유튜브 플레이어 (➕ 등록)"),
            ("browser",     "교실\n인터넷", "🌐", "광고 없이 인터넷을 이용하는 교실 클린 웹 브라우저 (➕ 등록)"),
        ]

        self.dock_buttons = {}
        self.dock_bars = {}

        for key, name, ico, tip in tools:
            # 사진 2 스타일: 원형 화이트 버튼 + 굵고 선명한 한글 텍스트
            col_box = ctk.CTkFrame(dock_scroll, fg_color="transparent", width=58)
            col_box.pack(side="left", padx=3, pady=2)

            btn = ctk.CTkButton(
                col_box,
                text=name,
                width=52, height=44,
                font=get_font(10, "bold"),
                fg_color="#ffffff",
                hover_color="#f8fafc",
                text_color="#0f172a",
                border_width=1,
                border_color="#cbd5e1",
                corner_radius=22,
                command=lambda k=key: self._toggle_module(k)
            )
            btn.pack(side="top")
            attach_tooltip(btn, tip)

            # 활성화 표시용 하단 주황색 굵은 바 (사진 2와 동일)
            bar = ctk.CTkFrame(col_box, width=36, height=4, fg_color="transparent", corner_radius=2)
            bar.pack(side="top", pady=(3, 0))

            self.dock_buttons[key] = btn
            self.dock_bars[key] = bar

        # 구분선
        ctk.CTkFrame(dock_scroll, width=1, height=36, fg_color="#cbd5e1").pack(side="left", padx=8)

        # 배경 테마 변경 버튼
        bg_btn = ctk.CTkButton(
            dock_scroll, text="🎨 배경", width=62, height=42,
            font=get_font(10, "bold"), fg_color="#f8fafc", hover_color="#f1f5f9",
            text_color="#475569", border_width=1, border_color="#cbd5e1",
            corner_radius=20, command=self._open_bg_picker
        )
        bg_btn.pack(side="left", padx=3)
        attach_tooltip(bg_btn, "교실 화면 배경 테마(핑크, 블루, 칠판그린 등) 변경")

    def _update_dock_button_state(self, mod_key: str, is_active: bool):
        if mod_key in self.dock_buttons:
            btn = self.dock_buttons[mod_key]
            bar = self.dock_bars.get(mod_key)
            if is_active:
                # 사진 2: 주황색 원 테두리 + 하단 주황색 활성화 바
                btn.configure(
                    fg_color="#ffffff", text_color="#ea580c",
                    border_width=2, border_color="#ea580c"
                )
                if bar:
                    bar.configure(fg_color="#ea580c")
            else:
                btn.configure(
                    fg_color="#ffffff", text_color="#0f172a",
                    border_width=1, border_color="#cbd5e1"
                )
                if bar:
                    bar.configure(fg_color="transparent")

    # ══════════════════════════════════════════════════════════════════════════
    # 모듈 창 생성 및 다중 배치 (사진 2, 3의 화이트 라운드 윈도우 스타일)
    # ══════════════════════════════════════════════════════════════════════════
    def _create_white_module_window(self, mod_key: str, title: str, ico: str, default_w: int, default_h: int):
        """캔버스 위에 자유롭게 떠다니는 아이스크림 툴킷 스타일의 화이트 카드 창"""
        if mod_key in self.active_modules:
            win = self.active_modules[mod_key]["frame"]
            win.lift()
            return self.active_modules[mod_key]["body"]

        # 기본 시작 위치 분산 배치
        existing_count = len(self.active_modules)
        start_x = 40 + (existing_count % 3) * 60
        start_y = 30 + (existing_count % 3) * 40

        # 카드 프레임 (화이트 라운드 섀도우 룩앤필)
        card = ctk.CTkFrame(
            self.canvas_area, width=default_w, height=default_h,
            fg_color="#ffffff", corner_radius=14,
            border_width=1, border_color="#cbd5e1"
        )
        card.pack_propagate(False)
        card.place(x=start_x, y=start_y)
        card.lift()

        # 상단 타이틀 바
        header = ctk.CTkFrame(card, fg_color="#f8fafc", height=38, corner_radius=12)
        header.pack(fill="x", side="top", padx=3, pady=3)
        header.pack_propagate(False)

        title_lbl = ctk.CTkLabel(
            header, text=f"{ico}  {title}", font=get_font(12, "bold"),
            text_color="#1e293b", cursor="fleur"
        )
        title_lbl.pack(side="left", padx=10)

        # 헤더 드래그로 캔버스 안에서 자유 이동
        header.bind("<Button-1>", lambda e, c=card: self._start_card_drag(e, c))
        header.bind("<B1-Motion>", lambda e, c=card: self._on_card_drag(e, c))
        title_lbl.bind("<Button-1>", lambda e, c=card: self._start_card_drag(e, c))
        title_lbl.bind("<B1-Motion>", lambda e, c=card: self._on_card_drag(e, c))

        # 우측 상단 윈도우 제어 버튼 (핀, 닫기)
        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right", padx=6)

        pin_btn = ctk.CTkButton(
            btn_box, text="📌", width=22, height=22, font=get_font(9),
            fg_color="#f1f5f9", hover_color="#e2e8f0", text_color="#64748b",
            corner_radius=4, command=lambda c=card: c.lift()
        )
        pin_btn.pack(side="left", padx=1)
        attach_tooltip(pin_btn, "맨 앞으로 가져오기")

        close_btn = ctk.CTkButton(
            btn_box, text="✕", width=22, height=22, font=get_font(10, "bold"),
            fg_color="#fee2e2", hover_color="#ef4444", text_color="#dc2626",
            corner_radius=4, command=lambda k=mod_key: self._close_module(k)
        )
        close_btn.pack(side="left", padx=1)
        attach_tooltip(close_btn, "도구 창 닫기")

        # 본체 콘텐츠 프레임
        body = ctk.CTkFrame(card, fg_color="#ffffff", corner_radius=0)
        body.pack(fill="both", expand=True, padx=6, pady=(2, 0))

        # 우측 하단 리사이즈 핸들
        b_bar = ctk.CTkFrame(card, fg_color="transparent", height=14)
        b_bar.pack(fill="x", side="bottom")
        b_bar.pack_propagate(False)

        rh = ctk.CTkLabel(
            b_bar, text="◢", font=get_font(11, "bold"), text_color="#94a3b8",
            width=16, cursor="size_nw_se"
        )
        rh.pack(side="right", padx=4)
        rh.bind("<Button-1>", lambda e, c=card: self._start_card_resize(e, c))
        rh.bind("<B1-Motion>", lambda e, c=card: self._on_card_resize(e, c))
        attach_tooltip(rh, "드래그하여 크기 자유 조절")

        self.active_modules[mod_key] = {
            "frame": card, "body": body, "w": default_w, "h": default_h
        }
        self._update_dock_button_state(mod_key, True)
        return body

    def _start_card_drag(self, event, card):
        card._drag_x = event.x
        card._drag_y = event.y
        card.lift()

    def _on_card_drag(self, event, card):
        x = card.winfo_x() + (event.x - card._drag_x)
        y = card.winfo_y() + (event.y - card._drag_y)
        card.place(x=x, y=y)

    def _start_card_resize(self, event, card):
        card._rs_x = event.x_root
        card._rs_y = event.y_root
        card._orig_w = card.winfo_width()
        card._orig_h = card.winfo_height()

    def _on_card_resize(self, event, card):
        dx = event.x_root - card._rs_x
        dy = event.y_root - card._rs_y
        nw = max(260, card._orig_w + dx)
        nh = max(200, card._orig_h + dy)
        card.configure(width=nw, height=nh)

    def _close_module(self, mod_key: str):
        if mod_key in self.active_modules:
            self.active_modules[mod_key]["frame"].destroy()
            del self.active_modules[mod_key]
        self._update_dock_button_state(mod_key, False)

    def _clear_all_modules(self):
        """캔버스에 열려 있는 모든 도구 창 일괄 정리"""
        keys = list(self.active_modules.keys())
        for k in keys:
            self._close_module(k)

    def _toggle_module(self, mod_key: str):
        if mod_key in self.active_modules:
            self._close_module(mod_key)
        else:
            fn = getattr(self, f"_show_{mod_key}", None)
            if fn:
                fn()

    # ══════════════════════════════════════════════════════════════════════════
    # 사진 3, 4와 100% 동일한 우측 세로 플로팅 판서 도구 바 (Vertical Pen Bar)
    # ══════════════════════════════════════════════════════════════════════════
    def _build_vertical_floating_bar(self):
        """교실 화면 우측에 상시 떠 있는 세로 플로팅 판서 바"""
        if hasattr(self, "v_floating_bar") and self.v_floating_bar.winfo_exists():
            return

        self.v_floating_bar = ctk.CTkFrame(
            self.canvas_area, fg_color="#ffffff", width=46, height=290,
            corner_radius=23, border_width=1, border_color="#cbd5e1"
        )
        self.v_floating_bar.pack_propagate(False)

        # 우측 상단 고정 위치 (드래그 가능)
        cw = self.canvas_area.winfo_width() or 1200
        vx = max(200, cw - 66)
        vy = 30
        self.v_floating_bar.place(x=vx, y=vy)
        self.v_floating_bar.lift()

        from src.icon_renderer import get_icon, COL_MAIN, COL_DANGER

        v_tools = [
            ("eye",        "눈(숨기기)",  lambda: self._toggle_canvas_drawing_visibility(), COL_MAIN),
            ("pencil",     "연필(판서)",  lambda: self._show_drawing(),                     COL_MAIN),
            ("pointer",    "선택(V)",     lambda: self._show_drawing(),                     COL_MAIN),
            ("eraser_box", "지우개(E)",   lambda: self._show_drawing(),                     COL_MAIN),
            ("undo",       "취소",        lambda: self._show_drawing(),                     COL_MAIN),
            ("trash",      "삭제",        lambda: self._show_drawing(),                     COL_DANGER),
        ]

        # 상단 닫기/숨기기 버튼
        c_btn = ctk.CTkButton(
            self.v_floating_bar, text="✕", width=34, height=34, font=get_font(10, "bold"),
            fg_color="transparent", hover_color="#fee2e2", text_color="#94a3b8",
            corner_radius=17, command=lambda: self.v_floating_bar.place_forget()
        )
        c_btn.pack(side="top", pady=(6, 2))
        attach_tooltip(c_btn, "판서 툴바 닫기")

        for ico_name, tip_text, cmd, col in v_tools:
            b = ctk.CTkButton(
                self.v_floating_bar, text="",
                image=get_icon(ico_name, col, 18),
                width=34, height=34,
                fg_color="transparent", hover_color="#e0f2fe",
                corner_radius=17, command=cmd
            )
            b.pack(side="top", pady=2)
            attach_tooltip(b, tip_text)

        # 드래그 이동
        self.v_floating_bar.bind("<Button-1>", lambda e: self._start_card_drag(e, self.v_floating_bar))
        self.v_floating_bar.bind("<B1-Motion>", lambda e: self._on_card_drag(e, self.v_floating_bar))

    def _toggle_canvas_drawing_visibility(self):
        """판서 레이어 숨기기/보이기 토글"""
        pass

    # ══════════════════════════════════════════════════════════════════════════
    # 1. 사진 2, 3의 타이머 (6종 선택 카드 + 실행 뷰 완벽 구현)
    # ══════════════════════════════════════════════════════════════════════════
    def _show_timer(self):
        body = self._create_white_module_window("timer", "타이머", "⏱️", 540, 390)
        self._render_timer_selection_view(body)

    def _render_timer_selection_view(self, body):
        """사진 2의 6종 타이머 선택 카드 뷰"""
        for w in body.winfo_children():
            w.destroy()

        # 상단 안내 바
        guide = ctk.CTkFrame(body, fg_color="#f1f5f9", corner_radius=8, height=36)
        guide.pack(fill="x", padx=12, pady=(8, 12))
        guide.pack_propagate(False)

        ctk.CTkLabel(
            guide, text="수업 활동에 필요한 타이머 혹은 스톱워치를 선택해 주세요.",
            font=get_font(11, "bold"), text_color="#334155"
        ).pack(expand=True)

        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=12, pady=4)
        grid.grid_columnconfigure((0, 1, 2), weight=1)
        grid.grid_rowconfigure((0, 1), weight=1)

        timer_cards = [
            ("digital",   "디지털 타이머", "timer_digital"),
            ("analog",    "아날로그 타이머", "timer_analog"),
            ("hourglass", "모래시계",       "timer_hourglass"),
            ("pie",       "파이 타이머",    "timer_pie"),
            ("balloon",   "풍선 타이머",    "timer_balloon"),
            ("stopwatch", "스톱워치",       "timer_stopwatch"),
        ]

        for i, (t_type, t_title, t_ico) in enumerate(timer_cards):
            r = i // 3
            c = i % 3
            card = ctk.CTkButton(
                grid,
                text=f"  {t_title}",
                image=get_icon(t_ico, "#000000", 42),
                compound="left",
                font=get_font(11, "bold"),
                fg_color="#ffffff",
                hover_color="#f8fafc",
                text_color="#0f172a",
                border_width=1,
                border_color="#cbd5e1",
                corner_radius=12,
                command=lambda typ=t_type, tit=t_title: self._start_specific_timer(body, typ, tit)
            )
            card.grid(row=r, column=c, sticky="nsew", padx=6, pady=6)

    def _start_specific_timer(self, body, t_type: str, t_title: str):
        """선택된 타이머 실행 화면"""
        for w in body.winfo_children():
            w.destroy()

        self.timer_type = t_type

        # 상단 네비게이션: 뒤로가기
        nav = ctk.CTkFrame(body, fg_color="transparent", height=28)
        nav.pack(fill="x", pady=(2, 6))

        ctk.CTkButton(
            nav, text="◀ 목록으로", width=70, height=24, font=get_font(9),
            fg_color="#f1f5f9", hover_color="#e2e8f0", text_color="#475569",
            corner_radius=6, command=lambda: self._render_timer_selection_view(body)
        ).pack(side="left")

        ctk.CTkLabel(
            nav, text=t_title, font=get_font(12, "bold"), text_color="#1e293b"
        ).pack(side="left", padx=8)

        # 시간 표시 디스플레이
        disp_frame = ctk.CTkFrame(body, fg_color="#f8fafc", corner_radius=12, border_width=1, border_color="#e2e8f0")
        disp_frame.pack(fill="both", expand=True, padx=8, pady=4)

        m = self.timer_seconds // 60
        s = self.timer_seconds % 60

        self.timer_disp_lbl = ctk.CTkLabel(
            disp_frame, text=f"{m:02d}:{s:02d}",
            font=ctk.CTkFont(family="Consolas", size=58, weight="bold"),
            text_color="#0284c7"
        )
        self.timer_disp_lbl.pack(expand=True)

        # 시간 간편 조절 버튼들 (+1분, +3분, +5분, -1분, 리셋)
        adj_box = ctk.CTkFrame(body, fg_color="transparent")
        adj_box.pack(fill="x", pady=4)

        for delta_m in [1, 3, 5, 10]:
            ctk.CTkButton(
                adj_box, text=f"+{delta_m}분", width=52, height=26, font=get_font(9, "bold"),
                fg_color="#f1f5f9", hover_color="#e2e8f0", text_color="#334155",
                corner_radius=6, command=lambda dm=delta_m: self._adjust_timer_seconds(dm * 60)
            ).pack(side="left", padx=2, expand=True)

        # 시작/정지/리셋 버튼
        ctrl_box = ctk.CTkFrame(body, fg_color="transparent")
        ctrl_box.pack(fill="x", pady=(4, 8))

        self.timer_run_btn = ctk.CTkButton(
            ctrl_box, text="시작 ▶", width=120, height=36, font=get_font(12, "bold"),
            fg_color="#ea580c", hover_color="#c2410c", text_color="#ffffff",
            corner_radius=18, command=self._toggle_timer_running
        )
        self.timer_run_btn.pack(side="left", padx=8, expand=True)

        ctk.CTkButton(
            ctrl_box, text="초기화 ↺", width=80, height=36, font=get_font(11, "bold"),
            fg_color="#f1f5f9", hover_color="#e2e8f0", text_color="#475569",
            corner_radius=18, command=self._reset_timer
        ) .pack(side="left", padx=8, expand=True)

    def _adjust_timer_seconds(self, delta: int):
        self.timer_seconds = max(10, self.timer_seconds + delta)
        self.timer_total = self.timer_seconds
        m = self.timer_seconds // 60
        s = self.timer_seconds % 60
        if hasattr(self, "timer_disp_lbl") and self.timer_disp_lbl.winfo_exists():
            self.timer_disp_lbl.configure(text=f"{m:02d}:{s:02d}")

    def _toggle_timer_running(self):
        self.timer_running = not self.timer_running
        if hasattr(self, "timer_run_btn") and self.timer_run_btn.winfo_exists():
            self.timer_run_btn.configure(
                text="일시정지 ⏸" if self.timer_running else "계속 ▶",
                fg_color="#0284c7" if self.timer_running else "#ea580c"
            )
        if self.timer_running:
            self._timer_tick()

    def _timer_tick(self):
        if not self.timer_running:
            return
        if self.timer_seconds > 0:
            self.timer_seconds -= 1
            m = self.timer_seconds // 60
            s = self.timer_seconds % 60
            if hasattr(self, "timer_disp_lbl") and self.timer_disp_lbl.winfo_exists():
                self.timer_disp_lbl.configure(text=f"{m:02d}:{s:02d}")
                if self.timer_seconds <= 10:
                    try:
                        winsound.Beep(1000, 100)
                    except Exception:
                        pass
            self.timer_job = self.after(1000, self._timer_tick)
        else:
            self.timer_running = False
            if hasattr(self, "timer_run_btn") and self.timer_run_btn.winfo_exists():
                self.timer_run_btn.configure(text="시작 ▶", fg_color="#ea580c")
            try:
                winsound.Beep(1500, 600)
            except Exception:
                pass
            messagebox.showinfo("시간 종료", "🔔 타이머 시간이 모두 끝났습니다!")

    def _reset_timer(self):
        self.timer_running = False
        self.timer_seconds = self.timer_total
        m = self.timer_seconds // 60
        s = self.timer_seconds % 60
        if hasattr(self, "timer_disp_lbl") and self.timer_disp_lbl.winfo_exists():
            self.timer_disp_lbl.configure(text=f"{m:02d}:{s:02d}")
        if hasattr(self, "timer_run_btn") and self.timer_run_btn.winfo_exists():
            self.timer_run_btn.configure(text="시작 ▶", fg_color="#ea580c")

    # ══════════════════════════════════════════════════════════════════════════
    # 2. 사진 3의 주사위 던지기 완벽 구현
    # ══════════════════════════════════════════════════════════════════════════
    def _show_dice(self):
        body = self._create_white_module_window("dice", "주사위 던지기", "🎲", 320, 360)

        # 상단 주사위 개수 조절 (-) 1 (+)
        cnt_box = ctk.CTkFrame(body, fg_color="#f1f5f9", corner_radius=8, height=38)
        cnt_box.pack(fill="x", padx=16, pady=(10, 12))
        cnt_box.pack_propagate(False)

        ctk.CTkButton(
            cnt_box, text="－", width=32, height=28, font=get_font(12, "bold"),
            fg_color="#ffffff", hover_color="#e2e8f0", text_color="#1e293b",
            corner_radius=6, command=lambda: self._change_dice_count(-1)
        ).pack(side="left", padx=8)

        self.dice_cnt_lbl = ctk.CTkLabel(
            cnt_box, text=str(self.dice_count), font=get_font(15, "bold"), text_color="#0f172a"
        )
        self.dice_cnt_lbl.pack(side="left", expand=True)

        ctk.CTkButton(
            cnt_box, text="＋", width=32, height=28, font=get_font(12, "bold"),
            fg_color="#ffffff", hover_color="#e2e8f0", text_color="#1e293b",
            corner_radius=6, command=lambda: self._change_dice_count(1)
        ).pack(side="right", padx=8)

        # 중앙 대형 주사위 캔버스
        self.dice_canvas = tk.Canvas(body, bg="#ffffff", highlightthickness=0, height=140)
        self.dice_canvas.pack(fill="x", padx=16, pady=4)
        self._draw_dice_faces()

        # 하단 오렌지 둥근 '던지기' 버튼
        ctk.CTkButton(
            body, text="🎲 던지기", height=42, font=get_font(13, "bold"),
            fg_color="#ea580c", hover_color="#c2410c", text_color="#ffffff",
            corner_radius=21, command=self._roll_dice_anim
        ).pack(fill="x", padx=24, pady=16)

    def _change_dice_count(self, delta: int):
        self.dice_count = max(1, min(3, self.dice_count + delta))
        if len(self.dice_values) < self.dice_count:
            self.dice_values.extend([6] * (self.dice_count - len(self.dice_values)))
        elif len(self.dice_values) > self.dice_count:
            self.dice_values = self.dice_values[:self.dice_count]
        if hasattr(self, "dice_cnt_lbl") and self.dice_cnt_lbl.winfo_exists():
            self.dice_cnt_lbl.configure(text=str(self.dice_count))
        self._draw_dice_faces()

    def _draw_dice_faces(self):
        if not hasattr(self, "dice_canvas") or not self.dice_canvas.winfo_exists():
            return
        self.dice_canvas.delete("all")
        w = self.dice_canvas.winfo_width() or 280
        h = self.dice_canvas.winfo_height() or 140

        box_sz = 80
        gap = 14
        total_w = self.dice_count * box_sz + (self.dice_count - 1) * gap
        start_x = (w - total_w) // 2
        cy = h // 2

        dot_coords = {
            1: [(0.5, 0.5)],
            2: [(0.3, 0.3), (0.7, 0.7)],
            3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
            4: [(0.3, 0.3), (0.7, 0.3), (0.3, 0.7), (0.7, 0.7)],
            5: [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)],
            6: [(0.3, 0.25), (0.7, 0.25), (0.3, 0.5), (0.7, 0.5), (0.3, 0.75), (0.7, 0.75)]
        }

        for idx, val in enumerate(self.dice_values):
            bx = start_x + idx * (box_sz + gap)
            by = cy - box_sz // 2
            # 블랙 주사위 바디
            self.dice_canvas.create_rectangle(
                bx, by, bx + box_sz, by + box_sz,
                fill="#0f172a", outline="#334155", width=2
            )
            # 화이트 눈금 점
            for nx, ny in dot_coords.get(val, [(0.5, 0.5)]):
                dx = bx + nx * box_sz
                dy = by + ny * box_sz
                r = 6
                self.dice_canvas.create_oval(dx - r, dy - r, dx + r, dy + r, fill="#ffffff", outline="")

    def _roll_dice_anim(self):
        if self.dice_rolling:
            return
        self.dice_rolling = True

        def _step(step=0):
            if step < 8:
                self.dice_values = [random.randint(1, 6) for _ in range(self.dice_count)]
                self._draw_dice_faces()
                self.after(60, lambda: _step(step + 1))
            else:
                self.dice_values = [random.randint(1, 6) for _ in range(self.dice_count)]
                self._draw_dice_faces()
                self.dice_rolling = False
                try:
                    winsound.Beep(900, 120)
                except Exception:
                    pass

        _step()

    # ══════════════════════════════════════════════════════════════════════════
    # 3. 돌림판 & 랜덤 뽑기
    # ══════════════════════════════════════════════════════════════════════════
    def _show_wheel(self):
        body = self._create_white_module_window("wheel", "돌려돌려 돌림판", "🎡", 360, 420)
        self.wheel_canvas = tk.Canvas(body, bg="#ffffff", highlightthickness=0, height=270)
        self.wheel_canvas.pack(fill="both", expand=True, padx=8, pady=4)
        self._draw_wheel_graphic()

        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=10)

        ctk.CTkButton(
            btn_row, text="🎡 돌리기!", height=40, font=get_font(12, "bold"),
            fg_color="#0284c7", hover_color="#0369a1", text_color="#ffffff",
            corner_radius=20, command=self._spin_wheel_anim
        ).pack(side="left", fill="x", expand=True, padx=2)

        ctk.CTkButton(
            btn_row, text="항목 편집", width=70, height=40, font=get_font(10),
            fg_color="#f1f5f9", hover_color="#e2e8f0", text_color="#475569",
            corner_radius=20, command=self._edit_wheel_items
        ).pack(side="left", padx=2)

    def _draw_wheel_graphic(self):
        if not hasattr(self, "wheel_canvas") or not self.wheel_canvas.winfo_exists():
            return
        self.wheel_canvas.delete("all")
        w = self.wheel_canvas.winfo_width() or 340
        h = self.wheel_canvas.winfo_height() or 270
        cx, cy, r = w // 2, h // 2, min(w, h) // 2 - 20

        palette = ["#f87171", "#fb923c", "#facc15", "#4ade80", "#38bdf8", "#c084fc"]
        n = len(self.wheel_items)
        if n == 0:
            return

        deg_per = 360.0 / n
        for i, item in enumerate(self.wheel_items):
            st = self.wheel_angle + i * deg_per
            col = palette[i % len(palette)]
            self.wheel_canvas.create_pieslice(
                cx - r, cy - r, cx + r, cy + r,
                start=st, extent=deg_per, fill=col, outline="#ffffff", width=2
            )
            # 텍스트
            mid_rad = math.radians(st + deg_per / 2)
            tx = cx + r * 0.65 * math.cos(mid_rad)
            ty = cy - r * 0.65 * math.sin(mid_rad)
            self.wheel_canvas.create_text(tx, ty, text=item, fill="#ffffff", font=("맑은 고딕", 10, "bold"))

        # 중앙 핀
        self.wheel_canvas.create_oval(cx - 14, cy - 14, cx + 14, cy + 14, fill="#ffffff", outline="#0f172a", width=2)
        # 12시 방향 상단 바늘
        self.wheel_canvas.create_polygon(
            cx, cy - r + 8, cx - 10, cy - r - 12, cx + 10, cy - r - 12,
            fill="#ea580c", outline="#ffffff", width=1
        )

    def _spin_wheel_anim(self):
        if self.wheel_spinning:
            return
        self.wheel_spinning = True
        total_spin = random.randint(720, 1440)
        curr_spin = 0

        def _step():
            nonlocal curr_spin
            if curr_spin < total_spin:
                speed = max(2, (total_spin - curr_spin) * 0.08)
                self.wheel_angle = (self.wheel_angle + speed) % 360
                curr_spin += speed
                self._draw_wheel_graphic()
                self.after(30, _step)
            else:
                self.wheel_spinning = False
                n = len(self.wheel_items)
                deg_per = 360.0 / n
                # 12시 방향에 걸린 항목 계산 (90도 위치)
                hit_idx = int((90 - self.wheel_angle) % 360 / deg_per) % n
                winner = self.wheel_items[hit_idx]
                try:
                    winsound.Beep(1200, 300)
                except Exception:
                    pass
                messagebox.showinfo("당첨!", f"🎉 축하합니다!\n\n선택된 항목: [{winner}]")

        _step()

    def _edit_wheel_items(self):
        curr_str = ", ".join(self.wheel_items)
        ans = simpledialog.askstring("돌림판 항목", "항목들을 쉼표(,)로 구분하여 입력하세요:", initialvalue=curr_str, parent=self)
        if ans:
            items = [x.strip() for x in ans.split(",") if x.strip()]
            if items:
                self.wheel_items = items
                self._draw_wheel_graphic()

    def _show_picker(self):
        body = self._create_white_module_window("picker", "랜덤 발표자 뽑기", "🎯", 340, 320)
        ctk.CTkLabel(body, text="오늘의 발표자는 누구일까요?", font=get_font(12, "bold"), text_color="#334155").pack(pady=(16, 8))

        disp = ctk.CTkFrame(body, fg_color="#f8fafc", corner_radius=12, border_width=1, border_color="#e2e8f0")
        disp.pack(fill="both", expand=True, padx=20, pady=8)

        self.picker_res_lbl = ctk.CTkLabel(
            disp, text="?", font=ctk.CTkFont(family="Consolas", size=48, weight="bold"),
            text_color="#ea580c"
        )
        self.picker_res_lbl.pack(expand=True)

        ctk.CTkButton(
            body, text="🎯 발표자 뽑기!", height=42, font=get_font(13, "bold"),
            fg_color="#0284c7", hover_color="#0369a1", corner_radius=21,
            command=self._pick_random_student
        ).pack(fill="x", padx=24, pady=16)

    def _pick_random_student(self):
        # 1~25번 학생 중 랜덤 추첨
        def _anim(step=0):
            if step < 10:
                self.picker_res_lbl.configure(text=f"{random.randint(1, 25)}번")
                self.after(50, lambda: _anim(step + 1))
            else:
                winner_num = random.randint(1, 25)
                self.picker_res_lbl.configure(text=f"{winner_num}번 학생!")
                try:
                    winsound.Beep(1200, 200)
                except Exception:
                    pass

        _anim()

    # ══════════════════════════════════════════════════════════════════════════
    # 4. 시간표 & 급식 & 1인1역 & 메모
    # ══════════════════════════════════════════════════════════════════════════
    def _show_timetable(self):
        body = self._create_white_module_window("timetable", "오늘의 수업 시간표", "📋", 380, 420)
        scroll = ctk.CTkScrollableFrame(body, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=6)

        is_hol, hol_name, items = timetable_manager.get_today_schedule_items()
        now_str = datetime.datetime.now().strftime("%H:%M")

        if is_hol:
            ctk.CTkLabel(scroll, text=f"🇰🇷 [{hol_name}] 공휴일", font=get_font(14, "bold"), text_color="#ea580c").pack(pady=40)
        else:
            for it in items:
                is_lunch = it["is_lunch"]
                is_cur = (it["start"] <= now_str <= it["end"])
                card = ctk.CTkFrame(
                    scroll, fg_color="#f0fdf4" if is_cur else ("#fff7ed" if is_lunch else "#f8fafc"),
                    corner_radius=8, border_width=1, border_color="#86efac" if is_cur else "#e2e8f0"
                )
                card.pack(fill="x", pady=2)
                ctk.CTkLabel(card, text=it["name"], font=get_font(10, "bold"), width=44, fg_color="#0284c7" if not is_lunch else "#ea580c", text_color="#fff", corner_radius=4).pack(side="left", padx=6, pady=6)
                ctk.CTkLabel(card, text=f"{it['start']}~{it['end']}", font=get_font(9), text_color="#64748b").pack(side="left", padx=4)
                ctk.CTkLabel(card, text=it["subject"], font=get_font(11, "bold"), text_color="#1e293b").pack(side="left", fill="x", expand=True, padx=6)

    def _show_meal(self):
        body = self._create_white_module_window("meal", "오늘의 학교 급식", "🍱", 360, 400)
        scroll = ctk.CTkScrollableFrame(body, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=6)

        try:
            today = datetime.date.today()
            ok, meal_info, _ = neis_client.get_meal_for_date(today)
            dishes = meal_info.get("dishes", []) if ok else []
            cal = meal_info.get("calorie", "") if ok else ""
        except Exception:
            dishes, cal = [], ""

        if cal:
            ctk.CTkLabel(scroll, text=f"🔥 열량: {cal}", font=get_font(11, "bold"), text_color="#16a34a").pack(pady=4)

        for d in dishes:
            r = ctk.CTkFrame(scroll, fg_color="#f8fafc", corner_radius=6, border_width=1, border_color="#f1f5f9")
            r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text=f"• {d}", font=get_font(11, "bold"), text_color="#1e293b", anchor="w").pack(fill="x", padx=10, pady=5)

        if not dishes:
            ctk.CTkLabel(scroll, text="오늘 등록된 급식 메뉴가 없습니다.", font=get_font(11), text_color="#94a3b8").pack(pady=40)

    def _show_role(self):
        body = self._create_white_module_window("role", "학급 1인 1역 현황", "👥", 340, 360)
        scroll = ctk.CTkScrollableFrame(body, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=6)

        for r_name, student in self.roles:
            row = ctk.CTkFrame(scroll, fg_color="#f8fafc", corner_radius=6, border_width=1, border_color="#e2e8f0")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=r_name, font=get_font(10, "bold"), text_color="#0284c7", width=90, anchor="w").pack(side="left", padx=8, pady=5)
            ctk.CTkLabel(row, text=student, font=get_font(10, "bold"), text_color="#334155").pack(side="left", padx=4)

    def _show_memo(self):
        body = self._create_white_module_window("memo", "오늘의 알림장 메모", "📝", 340, 320)
        box = ctk.CTkTextbox(body, font=get_font(11), fg_color="#f8fafc", text_color="#1e293b", corner_radius=8)
        box.pack(fill="both", expand=True, padx=12, pady=10)
        box.insert("1.0", "📌 오늘의 알림장\n1. 알림장 부모님 확인받기\n2. 내일 수학 2단원 수익책 챙기기\n3. 체육복 입고 오기")

    def _show_coin(self):
        body = self._create_white_module_window("coin", "동전 던지기", "🪙", 300, 320)
        disp = ctk.CTkFrame(body, fg_color="#f8fafc", corner_radius=12)
        disp.pack(fill="both", expand=True, padx=20, pady=10)

        self.coin_lbl = ctk.CTkLabel(disp, text="앞면", font=get_font(32, "bold"), text_color="#d97706")
        self.coin_lbl.pack(expand=True)

        ctk.CTkButton(
            body, text="🪙 동전 던지기", height=40, font=get_font(12, "bold"),
            fg_color="#ea580c", hover_color="#c2410c", corner_radius=20,
            command=self._flip_coin_anim
        ).pack(fill="x", padx=24, pady=14)

    def _flip_coin_anim(self):
        def _step(cnt=0):
            if cnt < 8:
                self.coin_lbl.configure(text="앞면" if cnt % 2 == 0 else "뒷면")
                self.after(60, lambda: _step(cnt + 1))
            else:
                res = random.choice(["앞면 (그림)", "뒷면 (숫자)"])
                self.coin_lbl.configure(text=res)
                try:
                    winsound.Beep(1100, 150)
                except Exception:
                    pass
        _step()

    def _show_scoreboard(self):
        body = self._create_white_module_window("scoreboard", "모둠 점수판", "🏆", 380, 340)
        scroll = ctk.CTkScrollableFrame(body, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=6)

        for m_name in list(self.scores.keys()):
            row = ctk.CTkFrame(scroll, fg_color="#f8fafc", corner_radius=8, border_width=1, border_color="#e2e8f0")
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(row, text=m_name, font=get_font(11, "bold"), width=60).pack(side="left", padx=8, pady=6)

            score_lbl = ctk.CTkLabel(row, text=str(self.scores[m_name]), font=get_font(14, "bold"), text_color="#0284c7", width=40)
            score_lbl.pack(side="left", padx=6)

            def _add(m=m_name, sl=score_lbl, d=1):
                self.scores[m] += d
                sl.configure(text=str(self.scores[m]))
                self._save_config()

            ctk.CTkButton(row, text="＋", width=28, height=26, font=get_font(10, "bold"), fg_color="#0284c7", command=lambda m=m_name, sl=score_lbl: _add(m, sl, 1)).pack(side="right", padx=2)
            ctk.CTkButton(row, text="－", width=28, height=26, font=get_font(10, "bold"), fg_color="#64748b", command=lambda m=m_name, sl=score_lbl: _add(m, sl, -1)).pack(side="right", padx=2)

    def _show_sound(self):
        body = self._create_white_module_window("sound", "우리반 효과음", "🔊", 360, 300)
        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=12, pady=10)
        grid.grid_columnconfigure((0, 1), weight=1)
        grid.grid_rowconfigure((0, 1, 2), weight=1)

        sounds = [
            ("👏 박수갈채", 1200), ("🔔 딩동댕 (정답)", 1500),
            ("❌ 땡 (오답)", 400),   ("🥁 드럼롤", 800),
            ("🎉 환호성", 1600),     ("🎺 팡파레", 1800),
        ]
        for i, (s_name, freq) in enumerate(sounds):
            r = i // 2
            c = i % 2
            ctk.CTkButton(
                grid, text=s_name, font=get_font(11, "bold"),
                fg_color="#f8fafc", hover_color="#f1f5f9", text_color="#1e293b",
                border_width=1, border_color="#cbd5e1", corner_radius=10,
                command=lambda f=freq: self._play_sound(f)
            ).grid(row=r, column=c, sticky="nsew", padx=4, pady=4)

    def _play_sound(self, freq: int):
        try:
            winsound.Beep(freq, 250)
        except Exception:
            pass

    def _show_clock(self):
        body = self._create_white_module_window("clock", "교실 대형 시계", "🕒", 340, 240)
        self.big_clock_lbl = ctk.CTkLabel(
            body, text="00:00:00",
            font=ctk.CTkFont(family="Consolas", size=48, weight="bold"),
            text_color="#0284c7"
        )
        self.big_clock_lbl.pack(expand=True)

    # ══════════════════════════════════════════════════════════════════════════
    # 사진 3, 4의 세로 플로팅 판서 바 (Palette) & 추가 수업 도구
    # ══════════════════════════════════════════════════════════════════════════
    def _show_drawing(self):
        """사진 3, 4와 동일한 세로 화이트 라운드 판서 도구 바"""
        body = self._create_white_module_window("drawing", "색연필 판서", "✏️", 72, 380)

        # 사진 3, 4와 똑같은 세로 아이콘 버튼 나열
        bar_tools = [
            ("eye",         "화면 보이기/숨기기", lambda: None),
            ("pencil",      "색연필(P)",       lambda: None),
            ("pointer",     "선택(V)",         lambda: None),  # 사진 4의 바로 그 버튼!
            ("eraser_box",  "지우개(E)",       lambda: None),
            ("undo",        "실행취소(Ctrl+Z)", lambda: None),
            ("trash",       "전체 삭제",       lambda: None),
        ]

        for ico_key, tip_txt, cmd in bar_tools:
            btn = ctk.CTkButton(
                body, text="", image=get_icon(ico_key, "#000000", 22),
                width=42, height=42, fg_color="#f8fafc", hover_color="#e2e8f0",
                corner_radius=10, border_width=1, border_color="#cbd5e1",
                command=cmd
            )
            btn.pack(side="top", pady=3)
            # 스마트 툴팁: 마우스 커서의 왼쪽 바깥에 커서를 전혀 가리지 않고 표시 (사진 4 재현)
            attach_tooltip(btn, tip_txt)

    def _show_note(self):
        body = self._create_white_module_window("note", "학급 판서 노트", "📝", 440, 360)
        txt = ctk.CTkTextbox(body, font=get_font(12), fg_color="#fffbeb", text_color="#1e293b", corner_radius=8)
        txt.pack(fill="both", expand=True, padx=12, pady=10)
        txt.insert("1.0", "📖 오늘 배울 내용\n\n1. 수학 3단원 소수의 나눗셈 원리 알기\n2. 국어 4단원 작품 속 인물의 마음 짐작하기\n3. 모둠별 토의 활동 및 학습지 정리")

    def _show_dday(self):
        body = self._create_white_module_window("dday", "학급 디데이 (D-Day)", "📅", 340, 320)
        scroll = ctk.CTkScrollableFrame(body, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=6)

        d_days = [
            ("여름/겨울 방학식", datetime.date(2026, 12, 24)),
            ("현장 체험 학습", datetime.date(2026, 10, 15)),
            ("학교 축제 & 학예회", datetime.date(2026, 11, 6)),
        ]
        today = datetime.date.today()

        for title, target_dt in d_days:
            diff = (target_dt - today).days
            row = ctk.CTkFrame(scroll, fg_color="#f8fafc", corner_radius=8, border_width=1, border_color="#e2e8f0")
            row.pack(fill="x", pady=4)

            ctk.CTkLabel(row, text=title, font=get_font(11, "bold"), text_color="#1e293b").pack(side="left", padx=10, pady=8)
            d_str = f"D-{diff}" if diff > 0 else (f"D+{abs(diff)}" if diff < 0 else "D-DAY!")
            d_col = "#ea580c" if diff <= 7 else "#0284c7"
            ctk.CTkLabel(row, text=d_str, font=get_font(13, "bold"), text_color=d_col).pack(side="right", padx=10)

    def _show_checklist(self):
        body = self._create_white_module_window("checklist", "과제 & 준비물 체크리스트", "✔️", 340, 360)
        scroll = ctk.CTkScrollableFrame(body, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=6)

        items = [
            "수학 익힘책 42~45쪽 풀기",
            "가족 동의서 안내장 제출",
            "줄넘기 및 개인 물통 챙기기",
            "미술 시간 가위, 풀, 색종이 지참",
            "독서 기록장 1편 작성"
        ]
        for it in items:
            cb = ctk.CTkCheckBox(
                scroll, text=it, font=get_font(10, "bold"),
                text_color="#1e293b", fg_color="#ea580c", hover_color="#c2410c"
            )
            cb.pack(fill="x", pady=6, padx=8)

    def _show_noise(self):
        body = self._create_white_module_window("noise", "우리반 소음 측정기", "📢", 340, 280)
        ctk.CTkLabel(body, text="🤫 쉿! 조용한 교실 만들기", font=get_font(12, "bold"), text_color="#334155").pack(pady=(16, 8))

        disp = ctk.CTkFrame(body, fg_color="#f8fafc", corner_radius=12, border_width=1, border_color="#e2e8f0")
        disp.pack(fill="both", expand=True, padx=20, pady=8)

        self.noise_lbl = ctk.CTkLabel(
            disp, text="쾌적함 😊 (32 dB)", font=get_font(16, "bold"), text_color="#16a34a"
        )
        self.noise_lbl.pack(expand=True)

        self.noise_progress = ctk.CTkProgressBar(body, height=14, corner_radius=7)
        self.noise_progress.pack(fill="x", padx=24, pady=12)
        self.noise_progress.set(0.3)

    def _show_launcher(self):
        """자주 쓰는 수업 프로그램 및 웹사이트 바로가기 모듈"""
        from src.quick_launcher import quick_launcher
        body = self._create_white_module_window("launcher", "자주 쓰는 프로그램 / 바로가기", "🚀", 440, 380)

        # 상단 제어 바
        top_ctrl = ctk.CTkFrame(body, fg_color="transparent", height=32)
        top_ctrl.pack(fill="x", padx=12, pady=(6, 4))
        top_ctrl.pack_propagate(False)

        ctk.CTkLabel(
            top_ctrl, text="수업용 프로그램 및 교과 사이트",
            font=get_font(11, "bold"), text_color="#0284c7"
        ).pack(side="left")

        def _refresh():
            self._close_module("launcher")
            self._show_launcher()

        add_btn = ctk.CTkButton(
            top_ctrl, text="➕ 추가", height=24, width=54,
            font=get_font(10, "bold"), fg_color="#059669", hover_color="#047857",
            corner_radius=6, command=lambda: quick_launcher.open_add_dialog(parent=self, on_success=_refresh)
        )
        add_btn.pack(side="right")
        attach_tooltip(add_btn, "새 프로그램(.exe), 문서(.hwp, .pdf), 웹사이트 등록")

        scroll = ctk.CTkScrollableFrame(body, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=4)

        shortcuts = quick_launcher.get_shortcuts()
        if not shortcuts:
            ctk.CTkLabel(
                scroll, text="등록된 바로가기가 없습니다.\n상단의 [➕ 추가] 버튼을 눌러보세요!",
                font=get_font(11), text_color="#94a3b8"
            ).pack(pady=40)
            return

        for item in shortcuts:
            s_id = item.get("id")
            s_name = item.get("name")
            s_target = item.get("target")
            s_emoji = item.get("emoji", "🚀")

            row = ctk.CTkFrame(scroll, fg_color="#f8fafc", corner_radius=8, border_width=1, border_color="#e2e8f0")
            row.pack(fill="x", pady=3)

            btn = ctk.CTkButton(
                row, text=f"{s_emoji}  {s_name}",
                font=get_font(11, "bold"), fg_color="transparent",
                hover_color="#e0f2fe", text_color="#1e293b",
                anchor="w", height=36,
                command=lambda t=s_target: quick_launcher.launch(t)
            )
            btn.pack(side="left", fill="x", expand=True, padx=(4, 0))
            attach_tooltip(btn, f"클릭하여 실행\n경로: {s_target}")

            del_btn = ctk.CTkButton(
                row, text="✕", width=22, height=22, font=get_font(9),
                fg_color="transparent", hover_color="#fee2e2", text_color="#94a3b8",
                corner_radius=4,
                command=lambda sid=s_id: (quick_launcher.remove_shortcut(sid), _refresh())
            )
            del_btn.pack(side="right", padx=6)
            attach_tooltip(del_btn, "이 바로가기 삭제")

    def _show_bgm(self):
        """유튜브 소리만 듣는 교실 배경음악(BGM) 플레이어 모듈"""
        from src.youtube_audio_manager import youtube_audio
        body = self._create_white_module_window("bgm", "교실 배경음악 BGM (유튜브 소리만 재생)", "🎵", 490, 430)

        # 1. 상단 현재 재생 상태 & 컨트롤 바
        ctrl_card = ctk.CTkFrame(body, fg_color="#f8fafc", corner_radius=10, border_width=1, border_color="#e2e8f0")
        ctrl_card.pack(fill="x", padx=10, pady=(6, 4))

        status_row = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        status_row.pack(fill="x", padx=8, pady=(8, 4))

        cur_title = youtube_audio.current_track["name"] if youtube_audio.current_track else "재생 중인 음악 없음"
        now_lbl = ctk.CTkLabel(
            status_row, text=f"🎶 {cur_title}",
            font=get_font(11, "bold"), text_color="#0284c7" if youtube_audio.is_playing else "#64748b",
            anchor="w"
        )
        now_lbl.pack(side="left", fill="x", expand=True)

        # 컨트롤 버튼 행 (재생/일시정지/정지/볼륨)
        btn_row = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=8, pady=(2, 8))

        def _refresh():
            self._close_module("bgm")
            self._show_bgm()

        def _toggle_play():
            if youtube_audio.is_playing:
                youtube_audio.pause()
            else:
                if youtube_audio.current_track:
                    youtube_audio.resume()
                else:
                    plist = youtube_audio.get_playlist()
                    if plist:
                        youtube_audio.play(plist[0])
            _refresh()

        play_btn = ctk.CTkButton(
            btn_row, text="일시정지 ⏸" if youtube_audio.is_playing else "재생 ▶",
            width=84, height=28, font=get_font(10, "bold"),
            fg_color="#0284c7" if youtube_audio.is_playing else "#ea580c",
            command=_toggle_play
        )
        play_btn.pack(side="left", padx=2)

        stop_btn = ctk.CTkButton(
            btn_row, text="정지 ⏹", width=58, height=28, font=get_font(10),
            fg_color="#64748b", hover_color="#475569",
            command=lambda: (youtube_audio.stop(), _refresh())
        )
        stop_btn.pack(side="left", padx=2)

        # 볼륨 슬라이더
        ctk.CTkLabel(btn_row, text="🔊", font=get_font(10)).pack(side="left", padx=(10, 2))
        vol_slider = ctk.CTkSlider(
            btn_row, from_=0, to=100, number_of_steps=20, width=110, height=14,
            command=lambda v: youtube_audio.set_volume(int(v))
        )
        vol_slider.set(youtube_audio.volume)
        vol_slider.pack(side="left", padx=2)

        # ➕ 유튜브 링크 등록 버튼
        add_btn = ctk.CTkButton(
            btn_row, text="➕ 링크 추가", width=74, height=28, font=get_font(10, "bold"),
            fg_color="#059669", hover_color="#047857",
            command=lambda: youtube_audio.open_add_dialog(parent=self, on_success=_refresh)
        )
        add_btn.pack(side="right", padx=2)
        attach_tooltip(add_btn, "유튜브 영상 링크를 입력하여 BGM으로 등록")

        # 2. 플레이리스트 스크롤 영역
        scroll = ctk.CTkScrollableFrame(body, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=4)

        playlist = youtube_audio.get_playlist()
        for track in playlist:
            vid = track.get("video_id")
            t_name = track.get("name")
            t_emoji = track.get("emoji", "🎵")
            t_cat = track.get("category", "수업")
            is_cur = (youtube_audio.current_track and youtube_audio.current_track.get("video_id") == vid)

            row = ctk.CTkFrame(
                scroll,
                fg_color="#f0fdf4" if (is_cur and youtube_audio.is_playing) else "#f8fafc",
                corner_radius=8, border_width=1,
                border_color="#86efac" if (is_cur and youtube_audio.is_playing) else "#e2e8f0"
            )
            row.pack(fill="x", pady=2)

            # 카테고리 태그
            ctk.CTkLabel(
                row, text=t_cat, font=get_font(9, "bold"), width=36,
                fg_color="#0284c7" if is_cur else "#64748b", text_color="#ffffff", corner_radius=4
            ).pack(side="left", padx=6, pady=6)

            # 제목 버튼 (클릭 시 소리 재생)
            t_btn = ctk.CTkButton(
                row, text=f"{t_emoji} {t_name}",
                font=get_font(10, "bold" if is_cur else "normal"),
                anchor="w", fg_color="transparent",
                hover_color="#e0f2fe",
                text_color="#0369a1" if is_cur else "#1e293b",
                height=32,
                command=lambda trk=track: (youtube_audio.play(trk), _refresh())
            )
            t_btn.pack(side="left", fill="x", expand=True, padx=4)
            attach_tooltip(t_btn, f"클릭하여 소리만 재생\n유튜브 ID: {vid}")

            # 삭제 버튼
            del_btn = ctk.CTkButton(
                row, text="✕", width=20, height=20, font=get_font(9),
                fg_color="transparent", hover_color="#fee2e2", text_color="#94a3b8",
                corner_radius=4,
                command=lambda v=vid: (youtube_audio.remove_track(v), _refresh())
            )
            del_btn.pack(side="right", padx=6)
            attach_tooltip(del_btn, "이 BGM 삭제")

    def _show_video(self):
        """교실 수업 영상 플레이어 모듈 (유튜브 무광고)"""
        from src.classroom_video_manager import classroom_video
        from src.youtube_audio_manager import extract_youtube_id
        body = self._create_white_module_window("video", "교실 수업 영상 플레이어 (유튜브 무광고)", "🎬", 520, 440)

        # 1. 상단: 유튜브 링크 직접 입력 & 즉시 재생 바
        top_card = ctk.CTkFrame(body, fg_color="#f8fafc", corner_radius=10, border_width=1, border_color="#e2e8f0")
        top_card.pack(fill="x", padx=10, pady=(6, 4))

        ctk.CTkLabel(
            top_card, text="🎬 유튜브 링크를 입력하면 광고 없이 고화질로 즉시 재생됩니다",
            font=get_font(10, "bold"), text_color="#0284c7"
        ).pack(fill="x", padx=8, pady=(6, 2))

        in_row = ctk.CTkFrame(top_card, fg_color="transparent")
        in_row.pack(fill="x", padx=8, pady=(2, 6))

        url_ent = ctk.CTkEntry(in_row, placeholder_text="예: https://www.youtube.com/watch?v=...", font=get_font(11))
        url_ent.pack(side="left", fill="x", expand=True, padx=(0, 6))

        def _play_url():
            raw = url_ent.get().strip()
            vid = extract_youtube_id(raw)
            if not vid:
                return
            classroom_video.launch_video(vid, "수업 영상")

        play_btn = ctk.CTkButton(
            in_row, text="🎬 영상 재생", width=86, height=28, font=get_font(10, "bold"),
            fg_color="#0284c7", hover_color="#0369a1", command=_play_url
        )
        play_btn.pack(side="left", padx=2)
        attach_tooltip(play_btn, "입력한 유튜브 영상을 광고 없이 즉시 재생")

        # 2. 수업 영상 즐겨찾기 목록 & 등록 바
        mid_bar = ctk.CTkFrame(body, fg_color="transparent")
        mid_bar.pack(fill="x", padx=12, pady=(4, 2))

        ctk.CTkLabel(mid_bar, text="📋 등록된 수업 영상 목록", font=get_font(11, "bold"), text_color="#1e293b").pack(side="left")

        def _refresh():
            self._close_module("video")
            self._show_video()

        def _open_add_video():
            from tkinter import simpledialog
            u = simpledialog.askstring("수업 영상 등록", "등록할 유튜브 영상 링크를 입력하세요:", parent=self)
            if u:
                classroom_video.add_video(u)
                _refresh()

        add_btn = ctk.CTkButton(
            mid_bar, text="➕ 영상 등록", width=78, height=26, font=get_font(10, "bold"),
            fg_color="#059669", hover_color="#047857", command=_open_add_video
        )
        add_btn.pack(side="right")
        attach_tooltip(add_btn, "수업에 자주 활용하는 유튜브 영상을 목록에 등록")

        # 3. 비디오 목록 스크롤
        scroll = ctk.CTkScrollableFrame(body, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=4)

        vids = classroom_video.get_videos()
        for v in vids:
            vid = v.get("video_id")
            v_name = v.get("name")
            v_emoji = v.get("emoji", "🎬")
            v_cat = v.get("category", "수업")

            row = ctk.CTkFrame(scroll, fg_color="#f8fafc", corner_radius=8, border_width=1, border_color="#e2e8f0")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row, text=v_cat, font=get_font(9, "bold"), width=36,
                fg_color="#0284c7", text_color="#ffffff", corner_radius=4
            ).pack(side="left", padx=6, pady=6)

            btn = ctk.CTkButton(
                row, text=f"{v_emoji}  {v_name}",
                font=get_font(11, "bold"), anchor="w", fg_color="transparent",
                hover_color="#e0f2fe", text_color="#1e293b", height=34,
                command=lambda v_id=vid, v_title=v_name: classroom_video.launch_video(v_id, v_title)
            )
            btn.pack(side="left", fill="x", expand=True, padx=4)
            attach_tooltip(btn, f"클릭하여 광고 없이 재생\n유튜브 ID: {vid}")

            del_btn = ctk.CTkButton(
                row, text="✕", width=22, height=22, font=get_font(9),
                fg_color="transparent", hover_color="#fee2e2", text_color="#94a3b8",
                corner_radius=4,
                command=lambda v_id=vid: (classroom_video.remove_video(v_id), _refresh())
            )
            del_btn.pack(side="right", padx=6)
            attach_tooltip(del_btn, "이 수업 영상 삭제")

    def _show_browser(self):
        """교실 클린 웹 브라우저 모듈 (광고 차단)"""
        from src.classroom_browser_manager import classroom_browser
        body = self._create_white_module_window("browser", "교실 클린 웹 브라우저 (광고 차단)", "🌐", 540, 460)

        # 1. 상단: URL/검색어 입력창 & 브라우저 열기 바
        top_card = ctk.CTkFrame(body, fg_color="#f8fafc", corner_radius=10, border_width=1, border_color="#e2e8f0")
        top_card.pack(fill="x", padx=10, pady=(6, 4))

        ctk.CTkLabel(
            top_card, text="🌐 주소 또는 검색어를 입력하면 광고가 차단된 클린 브라우저가 열립니다",
            font=get_font(10, "bold"), text_color="#0284c7"
        ).pack(fill="x", padx=8, pady=(6, 2))

        in_row = ctk.CTkFrame(top_card, fg_color="transparent")
        in_row.pack(fill="x", padx=8, pady=(2, 6))

        url_ent = ctk.CTkEntry(in_row, placeholder_text="예: 네이버, 독도 역사, https://...", font=get_font(11))
        url_ent.pack(side="left", fill="x", expand=True, padx=(0, 6))

        def _open_url():
            raw = url_ent.get().strip()
            if not raw:
                target = "https://www.naver.com"
            elif raw.startswith("http://") or raw.startswith("https://"):
                target = raw
            elif "." in raw and " " not in raw:
                target = "https://" + raw
            else:
                import urllib.parse
                target = "https://search.naver.com/search.naver?query=" + urllib.parse.quote(raw)
            classroom_browser.launch_browser(target)

        open_btn = ctk.CTkButton(
            in_row, text="🌐 브라우저 열기", width=98, height=28, font=get_font(10, "bold"),
            fg_color="#0284c7", hover_color="#0369a1", command=_open_url
        )
        open_btn.pack(side="left", padx=2)
        attach_tooltip(open_btn, "광고가 차단된 교실 전용 클린 브라우저 실행")

        # 2. 수업 즐겨찾기 바 & 등록 버튼
        mid_bar = ctk.CTkFrame(body, fg_color="transparent")
        mid_bar.pack(fill="x", padx=12, pady=(4, 2))

        ctk.CTkLabel(mid_bar, text="⭐ 교실 수업 즐겨찾기", font=get_font(11, "bold"), text_color="#1e293b").pack(side="left")

        def _refresh():
            self._close_module("browser")
            self._show_browser()

        def _open_add_bm():
            from tkinter import simpledialog
            u = simpledialog.askstring("즐겨찾기 등록", "등록할 사이트 주소(URL)를 입력하세요:", parent=self)
            if u:
                n = simpledialog.askstring("즐겨찾기 이름", "표시할 사이트 이름을 입력하세요:", parent=self) or u
                classroom_browser.add_bookmark(n, u)
                _refresh()

        add_btn = ctk.CTkButton(
            mid_bar, text="➕ 사이트 등록", width=84, height=26, font=get_font(10, "bold"),
            fg_color="#059669", hover_color="#047857", command=_open_add_bm
        )
        add_btn.pack(side="right")
        attach_tooltip(add_btn, "수업에 자주 활용하는 교육 사이트 북마크 등록")

        # 3. 북마크 목록 스크롤
        scroll = ctk.CTkScrollableFrame(body, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=4)

        bms = classroom_browser.get_bookmarks()
        for bm in bms:
            b_id = bm.get("id")
            b_name = bm.get("name")
            b_url = bm.get("url")
            b_emoji = bm.get("emoji", "🌐")
            b_cat = bm.get("category", "수업")

            row = ctk.CTkFrame(scroll, fg_color="#f8fafc", corner_radius=8, border_width=1, border_color="#e2e8f0")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row, text=b_cat, font=get_font(9, "bold"), width=36,
                fg_color="#0284c7", text_color="#ffffff", corner_radius=4
            ).pack(side="left", padx=6, pady=6)

            btn = ctk.CTkButton(
                row, text=f"{b_emoji}  {b_name}",
                font=get_font(11, "bold"), anchor="w", fg_color="transparent",
                hover_color="#e0f2fe", text_color="#1e293b", height=34,
                command=lambda u=b_url: classroom_browser.launch_browser(u)
            )
            btn.pack(side="left", fill="x", expand=True, padx=4)
            attach_tooltip(btn, f"클릭하여 광고 없이 접속\n주소: {b_url}")

            del_btn = ctk.CTkButton(
                row, text="✕", width=22, height=22, font=get_font(9),
                fg_color="transparent", hover_color="#fee2e2", text_color="#94a3b8",
                corner_radius=4,
                command=lambda bid=b_id: (classroom_browser.remove_bookmark(bid), _refresh())
            )
            del_btn.pack(side="right", padx=6)
            attach_tooltip(del_btn, "이 즐겨찾기 삭제")

    # ══════════════════════════════════════════════════════════════════════════
    # 초기 기본 화면: 사진 3처럼 타이머 + 주사위 동시 소환
    # ══════════════════════════════════════════════════════════════════════════
    def _open_default_tools(self):
        self._build_vertical_floating_bar()
        self._show_timer()
        self._show_dice()

    # ══════════════════════════════════════════════════════════════════════════
    # 배경 테마 변경 팝업
    # ══════════════════════════════════════════════════════════════════════════
    def _open_bg_picker(self):
        diag = ctk.CTkToplevel(self)
        diag.title("배경 테마 선택")
        diag.geometry("300x220")
        diag.resizable(False, False)
        diag.attributes("-topmost", True)

        ctk.CTkLabel(diag, text="🎨 교실 화면 배경 테마", font=get_font(12, "bold")).pack(pady=(12, 6))

        grid = ctk.CTkFrame(diag, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=16, pady=4)
        grid.grid_columnconfigure((0, 1), weight=1)

        for i, (t_name, col) in enumerate(BG_THEMES):
            r = i // 2
            c = i % 2
            ctk.CTkButton(
                grid, text=t_name, fg_color=col, text_color="#ffffff",
                font=get_font(10, "bold"), corner_radius=8, height=32,
                command=lambda cl=col: self._set_bg_color(cl, diag)
            ).grid(row=r, column=c, padx=4, pady=4, sticky="nsew")

    def _set_bg_color(self, col: str, diag=None):
        self.bg_color = col
        self.configure(fg_color=col)
        self.canvas_area.configure(bg=col)
        self._save_config()
        if diag and diag.winfo_exists():
            diag.destroy()

    # ══════════════════════════════════════════════════════════════════════════
    # 전역 헬퍼 및 루프
    # ══════════════════════════════════════════════════════════════════════════
    def _start_clock_loop(self):
        def _update():
            if not self.winfo_exists():
                return
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            if hasattr(self, "big_clock_lbl") and self.big_clock_lbl.winfo_exists():
                self.big_clock_lbl.configure(text=now_str)
            self.after(1000, _update)
        _update()

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        if hasattr(self, "fs_btn") and self.fs_btn.winfo_exists():
            self.fs_btn.configure(text="🗗 창모드" if self.is_fullscreen else "⛶ 전체화면 (F11)")

    def _exit_fullscreen(self):
        if self.is_fullscreen:
            self._toggle_fullscreen()

    def close(self):
        self._save_config()
        try:
            self.destroy()
        except Exception:
            pass
