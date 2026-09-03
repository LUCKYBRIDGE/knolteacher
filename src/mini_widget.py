import os
import sys
import json
import calendar
import datetime
import tkinter as tk
from tkinter import simpledialog, messagebox
import customtkinter as ctk

from src.font_config import setup_global_fonts, get_font
from src.timetable_manager import timetable_manager, DAYS_KO
from src.neis_client import neis_client
from src.config_utils import get_config_dir
from src.tooltip import attach_tooltip
from src.icon_renderer import get_icon, COL_MAIN, COL_ACTIVE, COL_YELLOW, COL_DANGER, COL_GREEN

try:
    from korean_lunar_calendar import KoreanLunarCalendar
    _lunar_calc = KoreanLunarCalendar()
except Exception:
    _lunar_calc = None

# 한국 주요 24절기 및 공휴일 매핑 (연도별/월별/일별)
SOLAR_TERMS = {
    # 2026년
    (2026, 1, 1): "신정", (2026, 1, 5): "소한", (2026, 1, 20): "대한",
    (2026, 2, 4): "입춘", (2026, 2, 16): "설날연휴", (2026, 2, 17): "설날", (2026, 2, 18): "우수",
    (2026, 3, 1): "삼일절", (2026, 3, 5): "경칩", (2026, 3, 20): "춘분",
    (2026, 4, 5): "청명/식목일", (2026, 4, 20): "곡우",
    (2026, 5, 5): "어린이날", (2026, 5, 6): "입하", (2026, 5, 21): "소만", (2026, 5, 24): "부처님오신날",
    (2026, 6, 5): "망종", (2026, 6, 6): "현충일", (2026, 6, 21): "하지",
    (2026, 7, 7): "소서", (2026, 7, 17): "제헌절", (2026, 7, 23): "대서",
    (2026, 8, 7): "입추", (2026, 8, 15): "광복절", (2026, 8, 23): "처서",
    (2026, 9, 7): "백로", (2026, 9, 23): "추분", (2026, 9, 24): "추석연휴", (2026, 9, 25): "추석", (2026, 9, 26): "추석연휴",
    (2026, 10, 3): "개천절", (2026, 10, 8): "한로", (2026, 10, 9): "한글날", (2026, 10, 23): "상강",
    (2026, 11, 7): "입동", (2026, 11, 22): "소설",
    (2026, 12, 7): "대설", (2026, 12, 21): "동지", (2026, 12, 25): "성탄절",
}

def get_lunar_str(year: int, month: int, day: int) -> str:
    """한국 음력 날짜 문자열 반환 (예: (음)7.22)"""
    if _lunar_calc:
        try:
            _lunar_calc.setSolarDate(year, month, day)
            return f"(음){_lunar_calc.lunarMonth}.{_lunar_calc.lunarDay}"
        except Exception:
            pass
    return ""


class MiniTimetableWidget(ctk.CTkToplevel):
    """
    놀티쳐 바탕화면 일체형 스마트 글래스 캘린더 & 시간표 위젯
    - 웹/앱들보다 상위 레이어에 뜨지 않고 바탕화면에 착 달라붙는 Desktop Layer
    - 배경화면의 아름다운 이미지와 자연스럽게 어우러지는 반투명 글래스모피즘
    - 오늘 날짜 네온 골드 테두리 하이라이트
    - 음력 날짜 및 24절기 표기
    - 셀별 일정/메모 더블클릭 작성 및 시간표 연동
    """
    _instance = None
    CONFIG_FILE = os.path.join(get_config_dir(), "widget_config.json")
    EVENTS_FILE = os.path.join(get_config_dir(), "widget_calendar_events.json")

    @classmethod
    def get_instance(cls, parent=None):
        if cls._instance is None or not cls._instance.winfo_exists():
            cls._instance = cls(parent)
        else:
            cls._instance.deiconify()
            cls._instance._send_to_desktop_bottom()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.title("놀티쳐 바탕화면 달력 위젯")
        self.minsize(460, 320)
        self.resizable(True, True)

        setup_global_fonts(self)
        self._load_icon()

        # 기본 설정값 (넓고 시원한 월간 글래스 캘린더 형태)
        self.width = 920
        self.height = 580
        self.opacity = 0.85
        self.is_pinned = False  # 웹/앱보다 위에 있지 않고 바탕화면 레이어에 상주!
        self.view_mode = "month"  # month (글래스 캘린더) | today (오늘 시간표/급식 카드)

        today = datetime.date.today()
        self.curr_year = today.year
        self.curr_month = today.month

        self._load_config()
        self._load_events()

        # 위치 및 크기 복원
        sw = self.winfo_screenwidth()
        pos_x = getattr(self, "pos_x", max(30, (sw - self.width) // 2))
        pos_y = getattr(self, "pos_y", 60)
        self.geometry(f"{self.width}x{self.height}+{pos_x}+{pos_y}")

        # 바탕화면 레이어 (Topmost가 아니며 최하단 레이어에 위치)
        self.attributes("-topmost", self.is_pinned)
        try:
            self.attributes("-alpha", self.opacity)
        except Exception:
            pass

        self._drag_start_x = 0
        self._drag_start_y = 0

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<FocusOut>", lambda e: self._send_to_desktop_bottom())

        self._build_ui()
        self._send_to_desktop_bottom()

        # 시간표 변경 실시간 감지 리스너 등록
        timetable_manager.add_listener(self._on_timetable_changed)

        # 주기적으로 바탕화면 최하단 레이어 유지 (다른 앱들이 열리면 그 뒤로 자연스럽게 배치)
        self._keep_bottom_timer()

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def _send_to_desktop_bottom(self):
        """웹/앱들보다 상위 레이어에 뜨지 않고 바탕화면 최하단 레이어로 밀착시킴"""
        if self.is_pinned:
            return
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()
            # HWND_BOTTOM = 1, SWP_NOSIZE = 1, SWP_NOMOVE = 2, SWP_NOACTIVATE = 0x0010
            ctypes.windll.user32.SetWindowPos(hwnd, 1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
            self.lower()
        except Exception:
            try:
                self.lower()
            except Exception:
                pass

    def _keep_bottom_timer(self):
        """1초 주기로 백그라운드에서 바탕화면 하단 레이어 유지"""
        if not self.is_pinned and self.winfo_exists():
            self._send_to_desktop_bottom()
        if self.winfo_exists():
            self.after(2000, self._keep_bottom_timer)

    def _load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.width = data.get("width", 920)
                    self.height = data.get("height", 580)
                    self.pos_x = data.get("x", 100)
                    self.pos_y = data.get("y", 60)
                    self.opacity = data.get("opacity", 0.85)
                    self.is_pinned = data.get("is_pinned", False)
                    self.view_mode = data.get("view_mode", "month")
            except Exception:
                pass

    def _save_config(self):
        try:
            data = {
                "width": self.winfo_width(),
                "height": self.winfo_height(),
                "x": self.winfo_x(),
                "y": self.winfo_y(),
                "opacity": self.opacity,
                "is_pinned": self.is_pinned,
                "view_mode": self.view_mode
            }
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_events(self):
        self.events = {}
        if os.path.exists(self.EVENTS_FILE):
            try:
                with open(self.EVENTS_FILE, "r", encoding="utf-8") as f:
                    self.events = json.load(f)
            except Exception:
                self.events = {}

    def _save_events(self):
        try:
            with open(self.EVENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.events, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # UI 구축: 첨부 이미지 감성의 글래스모피즘 바탕화면 달력
    # ══════════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        # 전체 반투명 바다/하늘 틴트 컨테이너
        self.container = ctk.CTkFrame(
            self, fg_color="#102534", corner_radius=12,
            border_width=1, border_color="#1b4660"
        )
        self.container.pack(fill="both", expand=True, padx=2, pady=2)

        # ── 1. 최상단 헤더 바 (이미지 스타일: "오늘은 2026년 9월 3일 목요일 (음) 7.22" + 미니멀 아이콘들) ──
        top_bar = ctk.CTkFrame(self.container, fg_color="#16384e", corner_radius=8, height=36)
        top_bar.pack(fill="x", padx=4, pady=(4, 2))
        top_bar.pack_propagate(False)

        # 드래그 이동 핸들러
        top_bar.bind("<Button-1>", self._start_drag)
        top_bar.bind("<B1-Motion>", self._on_drag)

        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]
        lunar_today = get_lunar_str(today.year, today.month, today.day)
        header_text = f"오늘은 {today.year}년{today.month}월{today.day}일 {weekday_str}요일 {lunar_today}"

        today_lbl = ctk.CTkLabel(
            top_bar, text=header_text, font=get_font(11, "bold"),
            text_color="#93c5fd", cursor="fleur"
        )
        today_lbl.pack(side="left", padx=12)
        today_lbl.bind("<Button-1>", self._start_drag)
        today_lbl.bind("<B1-Motion>", self._on_drag)

        # 우측 미니 액션 버튼들
        right_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        right_box.pack(side="right", padx=6)

        # 이전달
        prev_btn = ctk.CTkButton(
            right_box, text="◀", width=24, height=22, font=get_font(9),
            fg_color="#1f4b66", hover_color="#2b6589", text_color="#cbd5e1",
            corner_radius=4, command=self._prev_month
        )
        prev_btn.pack(side="left", padx=1)
        attach_tooltip(prev_btn, "이전 달로 이동")

        # 현재 월 라벨 (클릭 시 이번 달로 복귀)
        self.month_lbl = ctk.CTkButton(
            right_box, text=f"{self.curr_year}년 {self.curr_month}월", height=22,
            font=get_font(10, "bold"), fg_color="#0284c7", hover_color="#0369a1",
            text_color="#ffffff", corner_radius=4, command=self._go_today
        )
        self.month_lbl.pack(side="left", padx=2)
        attach_tooltip(self.month_lbl, "클릭하여 오늘(이번 달)로 바로 이동")

        # 다음달
        next_btn = ctk.CTkButton(
            right_box, text="▶", width=24, height=22, font=get_font(9),
            fg_color="#1f4b66", hover_color="#2b6589", text_color="#cbd5e1",
            corner_radius=4, command=self._next_month
        )
        next_btn.pack(side="left", padx=1)
        attach_tooltip(next_btn, "다음 달로 이동")

        # 뷰 모드 전환 (달력 ↔ 시간표 ↔ 바로가기)
        self.cal_btn = ctk.CTkButton(
            right_box, text="📅 달력", width=48, height=22, font=get_font(9, "bold"),
            fg_color="#0284c7" if self.view_mode == "month" else "#1f4b66",
            hover_color="#0369a1", text_color="#ffffff",
            corner_radius=4, command=lambda: self._set_view_mode("month")
        )
        self.cal_btn.pack(side="left", padx=1)
        attach_tooltip(self.cal_btn, "월간 글래스 달력")

        self.tt_btn = ctk.CTkButton(
            right_box, text="📋 시간표", width=52, height=22, font=get_font(9, "bold"),
            fg_color="#0284c7" if self.view_mode == "today" else "#1f4b66",
            hover_color="#0369a1", text_color="#ffffff",
            corner_radius=4, command=lambda: self._set_view_mode("today")
        )
        self.tt_btn.pack(side="left", padx=1)
        attach_tooltip(self.tt_btn, "오늘 시간표 & 급식 식단")

        self.sc_btn = ctk.CTkButton(
            right_box, text="🚀 바로가기", width=58, height=22, font=get_font(9, "bold"),
            fg_color="#059669" if self.view_mode == "shortcuts" else "#1f4b66",
            hover_color="#047857", text_color="#ffffff",
            corner_radius=4, command=lambda: self._set_view_mode("shortcuts")
        )
        self.sc_btn.pack(side="left", padx=2)
        attach_tooltip(self.sc_btn, "자주 쓰는 프로그램 / 웹사이트 빠른 실행")

        # 투명도 설정 버튼
        opt_btn = ctk.CTkButton(
            right_box, text="💧", width=22, height=22, font=get_font(9),
            fg_color="#1f4b66", hover_color="#2b6589", corner_radius=4,
            command=self._open_settings_dialog
        )
        opt_btn.pack(side="left", padx=1)
        attach_tooltip(opt_btn, "배경 투명도(글래스 강도) 조절")

        # 핀 고정 (기본: 바탕화면 레이어 밀착)
        self.pin_btn = ctk.CTkButton(
            right_box, text="📌" if self.is_pinned else "📍", width=22, height=22,
            font=get_font(9), fg_color="#0284c7" if self.is_pinned else "#1f4b66",
            hover_color="#0369a1", corner_radius=4, command=self._toggle_pin
        )
        self.pin_btn.pack(side="left", padx=1)
        attach_tooltip(self.pin_btn, "항상 위 고정 토글 (기본: 바탕화면 고정 레이어)")

        # 닫기
        close_btn = ctk.CTkButton(
            right_box, text="✕", width=22, height=22, font=get_font(10, "bold"),
            fg_color="#451a1a", hover_color="#dc2626", text_color="#fca5a5",
            corner_radius=4, command=self.close
        )
        close_btn.pack(side="left", padx=(1, 2))
        attach_tooltip(close_btn, "위젯 닫기")

        # ── 2. 메인 콘텐츠 영역 (월간 캘린더 or 오늘 시간표 or 바로가기) ──
        self.main_content = ctk.CTkFrame(self.container, fg_color="transparent")
        self.main_content.pack(fill="both", expand=True, padx=4, pady=2)

        if self.view_mode == "month":
            self._render_month_calendar()
        elif self.view_mode == "today":
            self._render_today_view()
        elif self.view_mode == "shortcuts":
            self._render_shortcuts_view()

        # ── 3. 최하단 얇은 리사이즈 그립 바 ──
        btm_bar = ctk.CTkFrame(self.container, fg_color="transparent", height=14)
        btm_bar.pack(fill="x", side="bottom", padx=4, pady=(0, 2))
        btm_bar.pack_propagate(False)

        info_lbl = ctk.CTkLabel(
            btm_bar, text="💡 날짜를 더블클릭하면 학급 일정/메모를 등록할 수 있습니다.",
            font=get_font(8), text_color="#64748b"
        )
        info_lbl.pack(side="left", padx=4)

        resize_handle = ctk.CTkLabel(
            btm_bar, text="◢", font=get_font(10, "bold"),
            text_color="#475569", width=16, cursor="size_nw_se"
        )
        resize_handle.pack(side="right")
        resize_handle.bind("<Button-1>", self._start_resize)
        resize_handle.bind("<B1-Motion>", self._on_resize)
        attach_tooltip(resize_handle, "드래그하여 위젯 크기 자유 조절")

    # ══════════════════════════════════════════════════════════════════════════
    # 월간 캘린더 그리드 렌더링 (사진과 100% 동일한 비주얼 & 인터랙션)
    # ══════════════════════════════════════════════════════════════════════════
    def _render_month_calendar(self):
        for w in self.main_content.winfo_children():
            w.destroy()

        cal_grid = ctk.CTkFrame(self.main_content, fg_color="transparent")
        cal_grid.pack(fill="both", expand=True)

        for c in range(7):
            cal_grid.grid_columnconfigure(c, weight=1)

        # 1. 요일 헤더: 일요일(레드), 월~금, 토요일(블루)
        days_header = [
            ("일요일", "#fca5a5"), ("월요일", "#bae6fd"), ("화요일", "#bae6fd"),
            ("수요일", "#bae6fd"), ("목요일", "#bae6fd"), ("금요일", "#bae6fd"),
            ("토요일", "#93c5fd")
        ]
        h_frame = ctk.CTkFrame(cal_grid, fg_color="#183f58", corner_radius=6, height=24)
        h_frame.grid(row=0, column=0, columnspan=7, sticky="nsew", pady=(0, 2))
        for c in range(7):
            h_frame.grid_columnconfigure(c, weight=1)

        for col_idx, (d_name, d_col) in enumerate(days_header):
            ctk.CTkLabel(
                h_frame, text=d_name, font=get_font(9, "bold"), text_color=d_col
            ).grid(row=0, column=col_idx, sticky="ew", pady=2)

        # 2. 날짜 타일 계산 (일요일 시작 캘린더)
        cal = calendar.Calendar(firstweekday=6)  # 6 = Sunday
        month_days = cal.monthdatescalendar(self.curr_year, self.curr_month)

        today = datetime.date.today()

        # 각 행 가중치 설정
        for r_idx in range(1, len(month_days) + 1):
            cal_grid.grid_rowconfigure(r_idx, weight=1)

        for r_idx, week in enumerate(month_days, start=1):
            for c_idx, dt in enumerate(week):
                is_curr_m = (dt.month == self.curr_month)
                is_today = (dt == today)
                is_sun = (c_idx == 0)
                is_sat = (c_idx == 6)

                # 타일 배경색 (평일: 은은한 청록 글래스, 주말: 차분한 다크그레이 글래스)
                if is_sun or is_sat:
                    tile_bg = "#1b262e" if is_curr_m else "#12191f"
                else:
                    tile_bg = "#15364a" if is_curr_m else "#0d202c"

                # 오늘 날짜는 사진과 똑같이 황금색/골드 네온 테두리!
                if is_today:
                    border_color = "#fef08a"
                    border_width = 2
                else:
                    border_color = "#1e4c68" if is_curr_m else "#143142"
                    border_width = 1

                tile = ctk.CTkFrame(
                    cal_grid, fg_color=tile_bg, corner_radius=4,
                    border_width=border_width, border_color=border_color
                )
                tile.grid(row=r_idx, column=c_idx, sticky="nsew", padx=1, pady=1)

                # 상단 헤더: 날짜 번호 + 음력/절기
                top_row = ctk.CTkFrame(tile, fg_color="transparent", height=18)
                top_row.pack(fill="x", padx=3, pady=(2, 0))

                num_color = "#f87171" if is_sun else ("#60a5fa" if is_sat else "#f1f5f9")
                if not is_curr_m:
                    num_color = "#475569"

                day_num_lbl = ctk.CTkLabel(
                    top_row, text=str(dt.day), font=get_font(9, "bold"), text_color=num_color
                )
                day_num_lbl.pack(side="left")

                # 절기 또는 음력 표기
                term_name = SOLAR_TERMS.get((dt.year, dt.month, dt.day))
                lunar_str = get_lunar_str(dt.year, dt.month, dt.day)

                if term_name:
                    ctk.CTkLabel(
                        top_row, text=f" {term_name}", font=get_font(8, "bold"), text_color="#4ade80"
                    ).pack(side="left", padx=1)
                elif lunar_str and is_curr_m:
                    ctk.CTkLabel(
                        top_row, text=f" {lunar_str}", font=get_font(7), text_color="#64748b"
                    ).pack(side="left", padx=1)

                # 타일 본문: 사용자 일정 메모 & 해당 요일 시간표 과목 미리보기
                body_box = ctk.CTkFrame(tile, fg_color="transparent")
                body_box.pack(fill="both", expand=True, padx=2, pady=1)

                date_key = dt.strftime("%Y-%m-%d")
                event_text = self.events.get(date_key, "")

                if event_text:
                    ctk.CTkLabel(
                        body_box, text=event_text, font=get_font(8, "bold"),
                        text_color="#fef08a", anchor="nw", justify="left"
                    ).pack(fill="both", expand=True)
                elif is_curr_m and not (is_sun or is_sat):
                    # 주중 평일에는 해당 요일의 시간표 요약 표시 (1~4교시 등)
                    weekday_idx = dt.weekday()  # 0: 월 ~ 4: 금
                    subjs = self._get_day_subjects(weekday_idx)
                    if subjs:
                        ctk.CTkLabel(
                            body_box, text=subjs, font=get_font(7),
                            text_color="#64748b", anchor="nw", justify="left"
                        ).pack(fill="both", expand=True)

                # 더블클릭 시 일정 메모 등록 팝업
                tile.bind("<Double-Button-1>", lambda e, d=dt: self._edit_event_dialog(d))
                day_num_lbl.bind("<Double-Button-1>", lambda e, d=dt: self._edit_event_dialog(d))
                body_box.bind("<Double-Button-1>", lambda e, d=dt: self._edit_event_dialog(d))

    def _get_day_subjects(self, weekday_idx: int) -> str:
        """해당 요일의 등록된 시간표 과목 간략 요약 (예: 1.국어 2.수학...)"""
        try:
            day_keys = ["mon", "tue", "wed", "thu", "fri"]
            if 0 <= weekday_idx < len(day_keys):
                d_key = day_keys[weekday_idx]
                sched = timetable_manager.weekly_timetable.get(d_key, [])
                parts = []
                for p, item in enumerate(sched[:6], 1):
                    subj = item.get("subject", "") if isinstance(item, dict) else str(item)
                    if subj:
                        parts.append(f"{p}.{subj}")
                return " ".join(parts[:3]) + ("..." if len(parts) > 3 else "")
        except Exception:
            pass
        return ""

    def _edit_event_dialog(self, dt: datetime.date):
        """특정 날짜 일정/메모 편집 팝업"""
        date_key = dt.strftime("%Y-%m-%d")
        curr_val = self.events.get(date_key, "")

        diag = ctk.CTkToplevel(self)
        diag.title(f"{dt.month}월 {dt.day}일 일정/메모")
        diag.geometry("320x200")
        diag.resizable(False, False)
        diag.attributes("-topmost", True)

        ctk.CTkLabel(
            diag, text=f"📅 {dt.year}년 {dt.month}월 {dt.day}일 메모 등록",
            font=get_font(11, "bold"), text_color="#38bdf8"
        ).pack(pady=(12, 4))

        txt = ctk.CTkTextbox(diag, height=80, font=get_font(10))
        txt.pack(fill="x", padx=16, pady=4)
        if curr_val:
            txt.insert("1.0", curr_val)
        txt.focus_set()

        btn_row = ctk.CTkFrame(diag, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=8)

        def _save():
            v = txt.get("1.0", "end-1c").strip()
            if v:
                self.events[date_key] = v
            else:
                self.events.pop(date_key, None)
            self._save_events()
            diag.destroy()
            self._render_month_calendar()

        def _delete():
            self.events.pop(date_key, None)
            self._save_events()
            diag.destroy()
            self._render_month_calendar()

        ctk.CTkButton(btn_row, text="저장", font=get_font(10, "bold"), width=70, fg_color="#0284c7", command=_save).pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text="삭제", font=get_font(10), width=60, fg_color="#7f1d1d", command=_delete).pack(side="left", padx=2)
        ctk.CTkButton(btn_row, text="취소", font=get_font(10), width=60, fg_color="#334155", command=diag.destroy).pack(side="right", padx=2)

    # ══════════════════════════════════════════════════════════════════════════
    # 오늘 시간표 & 급식 뷰 (모드 전환 시 사용)
    # ══════════════════════════════════════════════════════════════════════════
    def _render_today_view(self):
        for w in self.main_content.winfo_children():
            w.destroy()

        split = ctk.CTkFrame(self.main_content, fg_color="transparent")
        split.pack(fill="both", expand=True)
        split.grid_columnconfigure(0, weight=1)
        split.grid_columnconfigure(1, weight=1)
        split.grid_rowconfigure(0, weight=1)

        # 좌측: 오늘 시간표
        left_box = ctk.CTkScrollableFrame(split, fg_color="#132e42", corner_radius=8)
        left_box.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        hdr_row = ctk.CTkFrame(left_box, fg_color="transparent")
        hdr_row.pack(fill="x", pady=(2, 6))

        ctk.CTkLabel(
            hdr_row, text="📋 오늘의 수업 시간표",
            font=get_font(11, "bold"), text_color="#38bdf8"
        ).pack(side="left", padx=4)

        from src.timetable_quick_editor import open_timetable_quick_editor
        edit_btn = ctk.CTkButton(
            hdr_row, text="✏️ 수정", width=52, height=24,
            font=get_font(9, "bold"), fg_color="#0284c7", hover_color="#0369a1",
            text_color="#ffffff", corner_radius=4,
            command=lambda: open_timetable_quick_editor(self)
        )
        edit_btn.pack(side="right", padx=4)
        attach_tooltip(edit_btn, "오늘의 시간표 과목을 원클릭으로 수정합니다")

        is_hol, hol_name, items = timetable_manager.get_today_schedule_items()
        now_str = datetime.datetime.now().strftime("%H:%M")

        if is_hol:
            ctk.CTkLabel(left_box, text=f"🇰🇷 [{hol_name}] 공휴일", font=get_font(12, "bold"), text_color="#fdba74").pack(pady=30)
        else:
            lesson_counter = 0
            for it in items:
                is_lunch = it["is_lunch"]
                is_cur = (it["start"] <= now_str <= it["end"])
                card = ctk.CTkFrame(
                    left_box, fg_color="#064e3b" if is_cur else ("#3b1d11" if is_lunch else "#1b3c54"),
                    corner_radius=4, border_width=1, border_color="#10b981" if is_cur else "#255375",
                    cursor="hand2" if not is_lunch else "arrow"
                )
                card.pack(fill="x", pady=2)
                ctk.CTkLabel(card, text=it["name"], font=get_font(9, "bold"), width=38, fg_color="#0284c7" if not is_lunch else "#ea580c", text_color="#fff", corner_radius=3).pack(side="left", padx=4, pady=3)
                ctk.CTkLabel(card, text=f"{it['start']}~{it['end']}", font=get_font(8), text_color="#94a3b8").pack(side="left", padx=4)
                ctk.CTkLabel(card, text=it["subject"], font=get_font(10, "bold"), text_color="#6ee7b7" if is_cur else "#ffffff").pack(side="left", fill="x", expand=True, padx=4)
                if not is_lunch:
                    ctk.CTkLabel(card, text="✏️", font=get_font(9), text_color="#64748b").pack(side="right", padx=4)
                    cur_idx = lesson_counter
                    def _edit_it(e, idx=cur_idx):
                        open_timetable_quick_editor(self, focus_period=idx)
                    card.bind("<Button-1>", _edit_it)
                    for ch in card.winfo_children():
                        ch.bind("<Button-1>", _edit_it)
                    attach_tooltip(card, f"클릭하여 {it['name']}({it['subject']}) 과목 즉시 수정")
                    lesson_counter += 1

        # 우측: 오늘 급식 식단
        right_box = ctk.CTkScrollableFrame(split, fg_color="#132e42", corner_radius=8, label_text="🍱 오늘의 급식 식단")
        right_box.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)

        try:
            today = datetime.date.today()
            ok, meal_info, _ = neis_client.get_meal_for_date(today)
            dishes = meal_info.get("dishes", []) if ok else []
            cal = meal_info.get("calorie", "") if ok else ""
        except Exception:
            dishes, cal = [], ""

        if cal:
            ctk.CTkLabel(right_box, text=f"🔥 {cal}", font=get_font(10, "bold"), text_color="#4ade80").pack(pady=2)

        for d in dishes:
            r = ctk.CTkFrame(right_box, fg_color="#193a52", corner_radius=4)
            r.pack(fill="x", pady=2)
            ctk.CTkLabel(r, text=f"• {d}", font=get_font(10, "bold"), text_color="#f1f5f9", anchor="w").pack(fill="x", padx=8, pady=4)

        if not dishes:
            ctk.CTkLabel(right_box, text="등록된 급식이 없습니다.", font=get_font(10), text_color="#64748b").pack(pady=30)

    # ══════════════════════════════════════════════════════════════════════════
    # 헬퍼 액션들: 달 이동, 뷰 전환, 핀, 투명도, 리사이즈
    # ══════════════════════════════════════════════════════════════════════════
    def _prev_month(self):
        if self.curr_month == 1:
            self.curr_month = 12
            self.curr_year -= 1
        else:
            self.curr_month -= 1
        self.month_lbl.configure(text=f"{self.curr_year}년 {self.curr_month}월")
        if self.view_mode == "month":
            self._render_month_calendar()

    def _next_month(self):
        if self.curr_month == 12:
            self.curr_month = 1
            self.curr_year += 1
        else:
            self.curr_month += 1
        self.month_lbl.configure(text=f"{self.curr_year}년 {self.curr_month}월")
        if self.view_mode == "month":
            self._render_month_calendar()

    def _go_today(self):
        today = datetime.date.today()
        self.curr_year = today.year
        self.curr_month = today.month
        self.month_lbl.configure(text=f"{self.curr_year}년 {self.curr_month}월")
        if self.view_mode == "month":
            self._render_month_calendar()

    def _set_view_mode(self, mode: str):
        self.view_mode = mode
        self._build_ui()
        self._save_config()

    def _render_shortcuts_view(self):
        """바탕화면 글래스 위젯 안의 자주 쓰는 프로그램/바로가기 그리드 뷰"""
        from src.quick_launcher import quick_launcher

        for w in self.main_content.winfo_children():
            w.destroy()

        # 상단 제어 바
        top_ctrl = ctk.CTkFrame(self.main_content, fg_color="transparent", height=32)
        top_ctrl.pack(fill="x", padx=12, pady=(6, 4))
        top_ctrl.pack_propagate(False)

        ctk.CTkLabel(
            top_ctrl, text="🚀 바탕화면 자주 쓰는 프로그램 및 바로가기",
            font=get_font(12, "bold"), text_color="#38bdf8"
        ).pack(side="left")

        add_btn = ctk.CTkButton(
            top_ctrl, text="➕ 프로그램/바로가기 추가", height=26,
            font=get_font(10, "bold"), fg_color="#059669", hover_color="#047857",
            corner_radius=6, command=lambda: quick_launcher.open_add_dialog(parent=self, on_success=self._render_shortcuts_view)
        )
        add_btn.pack(side="right")
        attach_tooltip(add_btn, "내 컴퓨터의 프로그램(.exe), 문서(.hwp, .pdf), 웹사이트 등록")

        # 스크롤 그리드
        scroll = ctk.CTkScrollableFrame(self.main_content, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=4)
        scroll.grid_columnconfigure((0, 1, 2), weight=1)

        shortcuts = quick_launcher.get_shortcuts()
        if not shortcuts:
            ctk.CTkLabel(
                scroll, text="등록된 바로가기가 없습니다.\n우측 상단의 [➕ 프로그램/바로가기 추가] 버튼을 눌러 등록해보세요!",
                font=get_font(12), text_color="#64748b"
            ).grid(row=0, column=0, columnspan=3, pady=60)
            return

        for idx, item in enumerate(shortcuts):
            r = idx // 3
            c = idx % 3
            s_id = item.get("id")
            s_name = item.get("name")
            s_target = item.get("target")
            s_emoji = item.get("emoji", "🚀")

            card = ctk.CTkFrame(
                scroll, fg_color="#102a3c", corner_radius=10,
                border_width=1, border_color="#1b4660", height=66
            )
            card.grid(row=r, column=c, sticky="nsew", padx=6, pady=6)
            card.pack_propagate(False)

            # 좌측 이모지
            ctk.CTkLabel(
                card, text=s_emoji, font=get_font(20), width=38
            ).pack(side="left", padx=(8, 2))

            # 중간 텍스트 (이름 + 경로)
            mid = ctk.CTkFrame(card, fg_color="transparent")
            mid.pack(side="left", fill="both", expand=True, pady=6)

            title_btn = ctk.CTkButton(
                mid, text=s_name, font=get_font(11, "bold"),
                anchor="w", fg_color="transparent", hover_color="#16384e",
                text_color="#f8fafc", height=24,
                command=lambda t=s_target: quick_launcher.launch(t)
            )
            title_btn.pack(fill="x")
            attach_tooltip(title_btn, f"클릭하여 실행\n경로: {s_target}")

            disp_sub = s_target if len(s_target) < 28 else (s_target[:12] + "..." + s_target[-12:])
            ctk.CTkLabel(
                mid, text=disp_sub, font=get_font(8), text_color="#64748b", anchor="w"
            ).pack(fill="x")

            # 우측 삭제 버튼
            del_btn = ctk.CTkButton(
                card, text="✕", width=20, height=20, font=get_font(9),
                fg_color="transparent", hover_color="#dc2626", text_color="#64748b",
                corner_radius=4,
                command=lambda sid=s_id: (quick_launcher.remove_shortcut(sid), self._render_shortcuts_view())
            )
            del_btn.pack(side="right", padx=6)
            attach_tooltip(del_btn, "이 바로가기 삭제")

    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.attributes("-topmost", self.is_pinned)
        self.pin_btn.configure(
            text="📌" if self.is_pinned else "📍",
            fg_color="#0284c7" if self.is_pinned else "#1f4b66"
        )
        if not self.is_pinned:
            self._send_to_desktop_bottom()
        self._save_config()

    def _open_settings_dialog(self):
        diag = ctk.CTkToplevel(self)
        diag.title("글래스 투명도 조절")
        diag.geometry("280x160")
        diag.resizable(False, False)
        diag.attributes("-topmost", True)

        ctk.CTkLabel(diag, text="💧 배경화면 비침 투명도", font=get_font(11, "bold")).pack(pady=(16, 4))
        val_lbl = ctk.CTkLabel(diag, text=f"{int(self.opacity * 100)}%", font=get_font(11, "bold"), text_color="#38bdf8")
        val_lbl.pack()

        def _on_slider(val):
            self.opacity = float(val)
            val_lbl.configure(text=f"{int(self.opacity * 100)}%")
            try:
                self.attributes("-alpha", self.opacity)
            except Exception:
                pass
            self._save_config()

        sl = ctk.CTkSlider(diag, from_=0.35, to=0.98, number_of_steps=15, command=_on_slider)
        sl.set(self.opacity)
        sl.pack(fill="x", padx=24, pady=6)

        ctk.CTkButton(diag, text="확인", width=80, height=28, command=diag.destroy).pack(pady=(8, 0))

    # 드래그 이동
    def _start_drag(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag(self, event):
        x = self.winfo_x() + (event.x - self._drag_start_x)
        y = self.winfo_y() + (event.y - self._drag_start_y)
        self.geometry(f"+{x}+{y}")
        self._save_config()

    # 리사이즈
    def _start_resize(self, event):
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._orig_w = self.winfo_width()
        self._orig_h = self.winfo_height()

    def _on_resize(self, event):
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        nw = max(460, self._orig_w + dx)
        nh = max(320, self._orig_h + dy)
        self.geometry(f"{nw}x{nh}")
        self._save_config()

    def _on_timetable_changed(self):
        """시간표 실시간 변경 감지 -> 위젯 화면 즉각 갱신"""
        if self.winfo_exists():
            self.after(0, self._refresh_current_view)

    def _refresh_current_view(self):
        if self.view_mode == "today":
            self._render_today_view()
        elif self.view_mode == "month":
            self._render_month_calendar()

    def close(self):
        try:
            timetable_manager.remove_listener(self._on_timetable_changed)
        except Exception:
            pass
        self._save_config()
        try:
            self.destroy()
        except Exception:
            pass
