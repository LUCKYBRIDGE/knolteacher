import os
import sys
import datetime
import customtkinter as ctk
import tkinter as tk
from src.font_config import setup_global_fonts, get_font
from src.timetable_manager import timetable_manager, DAYS_KO


class StudentDisplayWindow(ctk.CTkToplevel):
    """
    듀얼 모니터(학생용 화면2, 교실 TV/전자칠판) 전용 대형 시간표 및 교실 안내 스크린
    - 깜빡임 없는 안정적 업데이트 (카드 재생성 최소화)
    - 줌 확대/축소 (A+ / A- 버튼)
    - 내장 수업 도구 탭 (시간표, 급식, 타이머, 뽑기, 돌림판)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.title("학생용 교실 화면 (오늘 시간표 & 알림판)")
        self.geometry("1024x720")
        self.minsize(700, 500)
        self.resizable(True, True)

        setup_global_fonts(self)
        self._load_icon()

        self.is_fullscreen = False
        self.is_pinned = False

        # 줌 레벨 (0.7 ~ 2.0)
        self.zoom = 1.0
        self._zoom_min = 0.6
        self._zoom_max = 2.2

        # 이전 수업 상태 (깜빡임 방지용 변경 감지)
        self._last_highlight_idx = -1
        self._schedule_cards = []   # (idx, frame, subj_lbl, badge) 보관
        self._last_item_count = -1

        # 내장 수업 도구 상태
        self._tool_tab = "schedule"  # schedule | meal | timer | picker | wheel
        self._timer_running = False
        self._timer_seconds = 0
        self._timer_job = None

        self.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._exit_fullscreen())

        self._build_ui()
        self._start_clock_loop()

    # ─── 아이콘 ────────────────────────────────────────────────────────────
    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    # ─── 전체화면 / 핀 ────────────────────────────────────────────────────
    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.attributes("-topmost", self.is_pinned)
        self.pin_btn.configure(
            text="📌" if self.is_pinned else "📍",
            fg_color="#2563eb" if self.is_pinned else "#334155"
        )

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)

    def _exit_fullscreen(self):
        self.is_fullscreen = False
        self.attributes("-fullscreen", False)

    # ─── 줌 ───────────────────────────────────────────────────────────────
    def _zoom_step(self, delta: float):
        self.zoom = max(self._zoom_min, min(self._zoom_max, round(self.zoom + delta, 1)))
        self._zoom_lbl.configure(text=f"{int(self.zoom * 100)}%")
        self._refresh_schedule_cards(force=True)

    # ─── UI 빌드 ──────────────────────────────────────────────────────────
    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="#0f172a")
        container.pack(fill="both", expand=True, padx=14, pady=14)

        # ── 1. 상단 바 (시계 + 줌 + 탭 + 컨트롤) ──────────────────────────
        header = ctk.CTkFrame(container, fg_color="#1e293b", corner_radius=14)
        header.pack(fill="x", pady=(0, 10))

        h_in = ctk.CTkFrame(header, fg_color="transparent")
        h_in.pack(fill="x", padx=16, pady=10)

        # 날짜
        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]
        self.date_lbl = ctk.CTkLabel(
            h_in,
            text=f"📅 {today.strftime('%Y년 %m월 %d일')} ({weekday_str}요일)",
            font=get_font(16, "bold"), text_color="#38bdf8"
        )
        self.date_lbl.pack(side="left")

        # 중앙 탭 버튼 영역
        tab_frame = ctk.CTkFrame(h_in, fg_color="transparent")
        tab_frame.pack(side="left", fill="x", expand=True, padx=16)

        self._tab_btns = {}
        tabs = [
            ("schedule", "📋 시간표"),
            ("meal",     "🍱 급식"),
            ("timer",    "⏱ 타이머"),
            ("picker",   "🎲 뽑기"),
            ("wheel",    "🎡 돌림판"),
        ]
        for tab_key, tab_label in tabs:
            btn = ctk.CTkButton(
                tab_frame, text=tab_label,
                font=get_font(11, "bold"),
                width=72, height=28, corner_radius=8,
                fg_color="#0284c7" if tab_key == "schedule" else "#1e293b",
                hover_color="#0369a1",
                text_color="#ffffff" if tab_key == "schedule" else "#94a3b8",
                command=lambda k=tab_key: self._switch_tab(k)
            )
            btn.pack(side="left", padx=2)
            self._tab_btns[tab_key] = btn

        # 우측 컨트롤 그룹
        ctrl = ctk.CTkFrame(h_in, fg_color="transparent")
        ctrl.pack(side="right")

        # 시계
        self.clock_lbl = ctk.CTkLabel(
            ctrl, text="00:00:00",
            font=ctk.CTkFont(family="Consolas", size=22, weight="bold"),
            text_color="#4ade80"
        )
        self.clock_lbl.pack(side="left", padx=(0, 10))

        # 줌 컨트롤
        ctk.CTkButton(
            ctrl, text="A-", font=get_font(10, "bold"),
            width=28, height=26, corner_radius=6,
            fg_color="#334155", hover_color="#475569",
            command=lambda: self._zoom_step(-0.1)
        ).pack(side="left", padx=1)

        self._zoom_lbl = ctk.CTkLabel(
            ctrl, text="100%", font=get_font(10, "bold"),
            text_color="#94a3b8", width=36
        )
        self._zoom_lbl.pack(side="left", padx=1)

        ctk.CTkButton(
            ctrl, text="A+", font=get_font(10, "bold"),
            width=28, height=26, corner_radius=6,
            fg_color="#334155", hover_color="#475569",
            command=lambda: self._zoom_step(0.1)
        ).pack(side="left", padx=1)

        ctk.CTkFrame(ctrl, width=1, height=20, fg_color="#475569").pack(side="left", padx=4)

        # 핀 / 최소화 / 전체화면 / 닫기
        self.pin_btn = ctk.CTkButton(
            ctrl, text="📍", width=28, height=26, font=get_font(10),
            fg_color="#334155", hover_color="#475569", corner_radius=6,
            command=self._toggle_pin
        )
        self.pin_btn.pack(side="left", padx=1)

        ctk.CTkButton(
            ctrl, text="—", width=28, height=26, font=get_font(11, "bold"),
            fg_color="#334155", hover_color="#475569", corner_radius=6,
            command=self.iconify
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            ctrl, text="⛶", width=28, height=26, font=get_font(11),
            fg_color="#334155", hover_color="#475569", corner_radius=6,
            command=self._toggle_fullscreen
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            ctrl, text="✕", width=28, height=26, font=get_font(11, "bold"),
            fg_color="#3f1d24", hover_color="#dc2626", text_color="#fca5a5",
            corner_radius=6, command=self.destroy
        ).pack(side="left", padx=(1, 0))

        # ── 2. 탭 콘텐츠 영역 ─────────────────────────────────────────────
        self.content_area = ctk.CTkFrame(container, fg_color="transparent")
        self.content_area.pack(fill="both", expand=True)

        # 시간표 탭 (기본 표시)
        self._build_schedule_tab()

        # 하단 힌트
        ctk.CTkLabel(
            container,
            text="[F11] 전체화면  |  [ESC] 창모드  |  탭으로 수업 도구 전환",
            font=get_font(10), text_color="#475569"
        ).pack(anchor="w", pady=(6, 0))

    # ─── 탭 전환 ──────────────────────────────────────────────────────────
    def _switch_tab(self, key: str):
        self._tool_tab = key
        for k, btn in self._tab_btns.items():
            if k == key:
                btn.configure(fg_color="#0284c7", text_color="#ffffff")
            else:
                btn.configure(fg_color="#1e293b", text_color="#94a3b8")

        for w in self.content_area.winfo_children():
            w.destroy()
        self._schedule_cards.clear()
        self._last_item_count = -1
        self._last_highlight_idx = -1

        if key == "schedule":
            self._build_schedule_tab()
        elif key == "meal":
            self._build_meal_tab()
        elif key == "timer":
            self._build_timer_tab()
        elif key == "picker":
            self._build_picker_tab()
        elif key == "wheel":
            self._build_wheel_tab()

    # ─── 시간표 탭 ────────────────────────────────────────────────────────
    def _build_schedule_tab(self):
        frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        left_box = ctk.CTkFrame(frame, fg_color="#1e2230", corner_radius=12,
                                border_width=1, border_color="#334155")
        left_box.pack(side="left", fill="both", expand=True, padx=(0, 8))

        title_bar = ctk.CTkFrame(left_box, fg_color="transparent")
        title_bar.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(title_bar, text="📋 오늘의 수업 시간표",
                     font=get_font(15, "bold"), text_color="#60a5fa").pack(side="left")

        self.tt_scroll = ctk.CTkScrollableFrame(left_box, fg_color="transparent")
        self.tt_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # 우측 : 급식 + 알림판
        right_box = ctk.CTkFrame(frame, fg_color="#1e2230", corner_radius=12,
                                 border_width=1, border_color="#334155", width=300)
        right_box.pack(side="right", fill="both", padx=(8, 0))
        right_box.pack_propagate(False)

        self._build_meal_snippet(right_box)

        ctk.CTkLabel(right_box, text="📌 오늘의 교실 알림판",
                     font=get_font(13, "bold"), text_color="#f59e0b").pack(anchor="w", padx=14, pady=(6, 4))

        self.notice_box = ctk.CTkTextbox(
            right_box, font=get_font(12), fg_color="#0f172a",
            text_color="#f1f5f9", corner_radius=8
        )
        self.notice_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.notice_box.insert("1.0",
            "1. 수업 시작 3분 전 자리에 앉기\n"
            "2. 쉬는 시간 복도에서 뛰지 않기\n"
            "3. 준비물 및 숙제 챙기기\n\n"
            "[오늘의 명언]\n\"배움에는 끝이 없다.\""
        )

        # 초기 시간표 카드 렌더링
        self._refresh_schedule_cards(force=True)

    def _build_meal_snippet(self, parent):
        """우측 상단 급식 미리보기"""
        try:
            from src.neis_client import neis_client
            today = datetime.date.today()
            ok, meal_info, _ = neis_client.get_meal_for_date(today)
            dishes = meal_info.get("dishes", []) if ok else []
        except Exception:
            dishes = []

        meal_card = ctk.CTkFrame(parent, fg_color="#221e10", corner_radius=10,
                                 border_width=1, border_color="#d97706")
        meal_card.pack(fill="x", padx=10, pady=(10, 6))

        m_hdr = ctk.CTkFrame(meal_card, fg_color="transparent")
        m_hdr.pack(fill="x", padx=10, pady=(6, 2))
        ctk.CTkLabel(m_hdr, text="🍱 오늘의 점심", font=get_font(12, "bold"),
                     text_color="#fcd34d").pack(side="left")

        menu_text = "\n".join(f"• {d}" for d in dishes[:6]) if dishes else "급식 정보 없음"
        ctk.CTkLabel(meal_card, text=menu_text, font=get_font(11),
                     text_color="#f8fafc", justify="left", anchor="w"
                     ).pack(fill="x", padx=10, pady=(0, 6))

    def _refresh_schedule_cards(self, force=False):
        """시간표 카드를 최소한으로 업데이트 (깜빡임 방지)"""
        if self._tool_tab != "schedule":
            return

        is_hol, hol_name, items = timetable_manager.get_today_schedule_items()
        now_str = datetime.datetime.now().strftime("%H:%M")

        # 현재 강조 인덱스 계산
        cur_idx = -1
        for i, it in enumerate(items):
            if it["start"] <= now_str <= it["end"]:
                cur_idx = i
                break

        # 항목 수가 달라진 경우에만 전체 재구성
        if force or len(items) != self._last_item_count:
            for w in self.tt_scroll.winfo_children():
                w.destroy()
            self._schedule_cards.clear()
            self._last_item_count = len(items)
            self._last_highlight_idx = -99  # 강제 업데이트 트리거

            if is_hol:
                c = ctk.CTkFrame(self.tt_scroll, fg_color="#3b1d11", corner_radius=10, height=80)
                c.pack(fill="x", pady=10)
                ctk.CTkLabel(c, text=f"🇰🇷 오늘은 [{hol_name}] 공휴일입니다.",
                             font=get_font(int(16 * self.zoom), "bold"),
                             text_color="#fdba74").pack(expand=True)
                return

            colors = ["#1e3a8a", "#065f46", "#831843", "#701a75",
                      "#78350f", "#1e293b", "#312e81"]

            for idx, it in enumerate(items):
                is_lunch = it["is_lunch"]
                is_cur = (idx == cur_idx)

                card_bg = "#064e3b" if is_cur else ("#3b1d11" if is_lunch else "#181d28")
                border_c = "#10b981" if is_cur else ("#ea580c" if is_lunch else "#334155")

                row_card = ctk.CTkFrame(
                    self.tt_scroll, fg_color=card_bg,
                    corner_radius=8,
                    border_width=2 if is_cur else 1,
                    border_color=border_c
                )
                row_card.pack(fill="x", pady=int(3 * self.zoom))

                badge_bg = "#ea580c" if is_lunch else colors[idx % len(colors)]
                badge_sz = max(14, int(12 * self.zoom))
                badge_w = max(52, int(64 * self.zoom))
                badge_h = max(22, int(28 * self.zoom))
                badge = ctk.CTkLabel(
                    row_card, text=it["name"],
                    font=get_font(badge_sz, "bold"),
                    fg_color=badge_bg, text_color="#ffffff",
                    corner_radius=6, width=badge_w, height=badge_h
                )
                badge.pack(side="left", padx=int(8 * self.zoom),
                           pady=int(6 * self.zoom))

                time_sz = max(10, int(11 * self.zoom))
                ctk.CTkLabel(
                    row_card, text=f"{it['start']} ~ {it['end']}",
                    font=get_font(time_sz),
                    text_color="#94a3b8", width=max(80, int(90 * self.zoom))
                ).pack(side="left")

                subj_sz = max(13, int(15 * self.zoom))
                subj_lbl = ctk.CTkLabel(
                    row_card, text=it["subject"],
                    font=get_font(subj_sz, "bold"),
                    text_color="#6ee7b7" if is_cur else "#ffffff",
                    anchor="w"
                )
                subj_lbl.pack(side="left", fill="x", expand=True,
                              padx=int(6 * self.zoom))

                tag = it.get("tag", "담임")
                if tag in ["전담", "외강"]:
                    tag_bg = "#7c3aed" if tag == "전담" else "#0891b2"
                    tag_sz = max(10, int(11 * self.zoom))
                    ctk.CTkLabel(
                        row_card, text=f"[{tag}]",
                        font=get_font(tag_sz, "bold"),
                        fg_color=tag_bg, text_color="#ffffff",
                        corner_radius=4,
                        width=max(36, int(44 * self.zoom)),
                        height=max(18, int(22 * self.zoom))
                    ).pack(side="right", padx=8)

                self._schedule_cards.append((idx, row_card, subj_lbl, badge))

        # 강조 표시만 업데이트 (configure만, destroy 없음 → 깜빡임 0)
        elif cur_idx != self._last_highlight_idx:
            colors = ["#1e3a8a", "#065f46", "#831843", "#701a75",
                      "#78350f", "#1e293b", "#312e81"]
            for idx, row_card, subj_lbl, badge in self._schedule_cards:
                it = items[idx] if idx < len(items) else None
                if not it:
                    continue
                is_lunch = it["is_lunch"]
                is_cur = (idx == cur_idx)

                card_bg = "#064e3b" if is_cur else ("#3b1d11" if is_lunch else "#181d28")
                border_c = "#10b981" if is_cur else ("#ea580c" if is_lunch else "#334155")

                row_card.configure(
                    fg_color=card_bg,
                    border_width=2 if is_cur else 1,
                    border_color=border_c
                )
                subj_lbl.configure(
                    text_color="#6ee7b7" if is_cur else "#ffffff"
                )

        self._last_highlight_idx = cur_idx

    # ─── 급식 탭 ──────────────────────────────────────────────────────────
    def _build_meal_tab(self):
        frame = ctk.CTkFrame(self.content_area, fg_color="#1e2230",
                             corner_radius=12, border_width=1, border_color="#334155")
        frame.pack(fill="both", expand=True)

        ctk.CTkLabel(frame, text="🍱 오늘의 점심 급식",
                     font=get_font(20, "bold"), text_color="#fcd34d"
                     ).pack(pady=(20, 10))

        try:
            from src.neis_client import neis_client
            today = datetime.date.today()
            ok, meal_info, _ = neis_client.get_meal_for_date(today)
            dishes = meal_info.get("dishes", []) if ok else []
            cal = meal_info.get("calorie", "") if ok else ""
        except Exception:
            dishes, cal = [], ""

        if cal:
            ctk.CTkLabel(frame, text=f"🔥 {cal}",
                         font=get_font(14, "bold"), text_color="#4ade80").pack()

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=40, pady=10)

        for i, dish in enumerate(dishes):
            row_bg = "#221e10" if i % 2 == 0 else "#1a1608"
            row = ctk.CTkFrame(scroll, fg_color=row_bg, corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"• {dish}",
                         font=get_font(int(15 * self.zoom), "bold"),
                         text_color="#f8fafc", anchor="w"
                         ).pack(fill="x", padx=16, pady=6)

        if not dishes:
            ctk.CTkLabel(frame, text="오늘 등록된 급식 식단이 없습니다.",
                         font=get_font(14), text_color="#64748b").pack(pady=20)

    # ─── 타이머 탭 ────────────────────────────────────────────────────────
    def _build_timer_tab(self):
        frame = ctk.CTkFrame(self.content_area, fg_color="#0f172a",
                             corner_radius=12, border_width=1, border_color="#334155")
        frame.pack(fill="both", expand=True)

        ctk.CTkLabel(frame, text="⏱ 교실 집중 타이머",
                     font=get_font(20, "bold"), text_color="#38bdf8"
                     ).pack(pady=(24, 8))

        self._timer_display = ctk.CTkLabel(
            frame, text="05:00",
            font=ctk.CTkFont(family="Consolas", size=int(72 * self.zoom), weight="bold"),
            text_color="#4ade80"
        )
        self._timer_display.pack(pady=10)

        # 프리셋 버튼
        preset_frame = ctk.CTkFrame(frame, fg_color="transparent")
        preset_frame.pack(pady=6)
        for mins in [1, 3, 5, 10, 15, 20]:
            ctk.CTkButton(
                preset_frame, text=f"{mins}분",
                font=get_font(12, "bold"), width=52, height=32,
                corner_radius=8, fg_color="#1e293b", hover_color="#334155",
                command=lambda m=mins: self._timer_set(m * 60)
            ).pack(side="left", padx=3)

        # 제어 버튼
        ctrl = ctk.CTkFrame(frame, fg_color="transparent")
        ctrl.pack(pady=10)

        self._timer_start_btn = ctk.CTkButton(
            ctrl, text="▶ 시작", font=get_font(14, "bold"),
            width=90, height=40, corner_radius=10,
            fg_color="#059669", hover_color="#047857",
            command=self._timer_toggle
        )
        self._timer_start_btn.pack(side="left", padx=6)

        ctk.CTkButton(
            ctrl, text="↺ 초기화", font=get_font(12, "bold"),
            width=80, height=40, corner_radius=10,
            fg_color="#334155", hover_color="#475569",
            command=self._timer_reset
        ).pack(side="left", padx=6)

        # 기본값 5분
        self._timer_seconds = 300

    def _timer_set(self, seconds: int):
        self._timer_running = False
        if self._timer_job:
            self.after_cancel(self._timer_job)
            self._timer_job = None
        self._timer_seconds = seconds
        m, s = divmod(seconds, 60)
        self._timer_display.configure(
            text=f"{m:02d}:{s:02d}", text_color="#4ade80"
        )
        self._timer_start_btn.configure(text="▶ 시작", fg_color="#059669")

    def _timer_toggle(self):
        if self._timer_running:
            self._timer_running = False
            if self._timer_job:
                self.after_cancel(self._timer_job)
                self._timer_job = None
            self._timer_start_btn.configure(text="▶ 계속", fg_color="#059669")
        else:
            self._timer_running = True
            self._timer_start_btn.configure(text="⏸ 일시정지", fg_color="#d97706")
            self._timer_tick()

    def _timer_tick(self):
        if not self._timer_running:
            return
        if self._timer_seconds <= 0:
            self._timer_running = False
            self._timer_display.configure(text="00:00", text_color="#ef4444")
            self._timer_start_btn.configure(text="▶ 시작", fg_color="#059669")
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass
            return
        self._timer_seconds -= 1
        m, s = divmod(self._timer_seconds, 60)
        col = "#ef4444" if self._timer_seconds <= 10 else \
              "#fb923c" if self._timer_seconds <= 30 else "#4ade80"
        self._timer_display.configure(text=f"{m:02d}:{s:02d}", text_color=col)
        self._timer_job = self.after(1000, self._timer_tick)

    def _timer_reset(self):
        self._timer_set(300)

    # ─── 뽑기 탭 ──────────────────────────────────────────────────────────
    def _build_picker_tab(self):
        from src.student_manager import student_manager

        frame = ctk.CTkFrame(self.content_area, fg_color="#0f172a",
                             corner_radius=12, border_width=1, border_color="#334155")
        frame.pack(fill="both", expand=True)

        ctk.CTkLabel(frame, text="🎲 발표자 랜덤 뽑기",
                     font=get_font(20, "bold"), text_color="#38bdf8"
                     ).pack(pady=(24, 8))

        self._picker_result = ctk.CTkLabel(
            frame, text="버튼을 눌러 발표자를 뽑으세요!",
            font=get_font(int(28 * self.zoom), "bold"),
            text_color="#fde047"
        )
        self._picker_result.pack(pady=20, expand=True)

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.pack(pady=12)

        ctk.CTkButton(
            btns, text="🎯 뽑기!", font=get_font(18, "bold"),
            width=160, height=56, corner_radius=14,
            fg_color="#7c3aed", hover_color="#6d28d9",
            command=lambda: self._do_pick(student_manager, frame)
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btns, text="🔄 다시뽑기", font=get_font(14, "bold"),
            width=110, height=56, corner_radius=14,
            fg_color="#334155", hover_color="#475569",
            command=lambda: self._picker_result.configure(
                text="버튼을 눌러 발표자를 뽑으세요!", text_color="#fde047"
            )
        ).pack(side="left", padx=8)

    def _do_pick(self, student_manager, frame):
        import random
        names = student_manager.get_student_names()
        if names:
            winner = random.choice(names)
            self._picker_result.configure(
                text=f"🎉  {winner}  🎉", text_color="#4ade80"
            )
        else:
            self._picker_result.configure(
                text="학생 명단이 없습니다.\n설정에서 학생 명단을 등록해 주세요.",
                text_color="#f87171"
            )

    # ─── 돌림판 탭 ────────────────────────────────────────────────────────
    def _build_wheel_tab(self):
        import math as _math
        import tkinter as _tk

        frame = ctk.CTkFrame(self.content_area, fg_color="#0f172a",
                             corner_radius=12, border_width=1, border_color="#334155")
        frame.pack(fill="both", expand=True)

        ctk.CTkLabel(frame, text="🎡 돌려돌려 돌림판",
                     font=get_font(18, "bold"), text_color="#38bdf8").pack(pady=(16, 4))

        # 항목 입력
        inp_row = ctk.CTkFrame(frame, fg_color="transparent")
        inp_row.pack(fill="x", padx=40, pady=(0, 4))
        ctk.CTkLabel(inp_row, text="항목(쉼표구분):", font=get_font(11)).pack(side="left")
        self._wheel_entry_sd = ctk.CTkEntry(inp_row, height=26, font=get_font(11))
        self._wheel_entry_sd.insert(0, "1모둠, 2모둠, 3모둠, 4모둠")
        self._wheel_entry_sd.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkButton(inp_row, text="적용", width=42, height=26,
                      font=get_font(10, "bold"), fg_color="#1e293b",
                      command=self._sd_apply_wheel).pack(side="left")

        # 캔버스
        canvas_size = min(380, int(340 * self.zoom))
        self._sd_wheel_canvas = _tk.Canvas(
            frame, width=canvas_size, height=canvas_size,
            bg="#0f172a", highlightthickness=0
        )
        self._sd_wheel_canvas.pack(pady=4)

        self._sd_wheel_items = ["1모둠", "2모둠", "3모둠", "4모둠"]
        self._sd_wheel_angle = 0.0
        self._sd_wheel_spinning = False
        self._sd_draw_wheel()

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(pady=4)

        ctk.CTkButton(
            btn_row, text="🚀 돌리기!", font=get_font(14, "bold"),
            width=130, height=44, corner_radius=12,
            fg_color="#ea580c", hover_color="#c2410c",
            command=self._sd_spin_wheel
        ).pack(side="left", padx=6)

        self._sd_wheel_result = ctk.CTkLabel(
            frame, text="돌림판을 돌려보세요!",
            font=get_font(14, "bold"), text_color="#38bdf8"
        )
        self._sd_wheel_result.pack(pady=(4, 10))

    def _sd_apply_wheel(self):
        txt = self._wheel_entry_sd.get().strip()
        items = [x.strip() for x in txt.split(",") if x.strip()]
        if items:
            self._sd_wheel_items = items
            self._sd_draw_wheel()

    def _sd_draw_wheel(self):
        import math as _m
        c = self._sd_wheel_canvas
        c.delete("all")
        n = len(self._sd_wheel_items)
        if n == 0:
            return
        w = int(c["width"])
        cx, cy, r = w//2, w//2, w//2 - 10
        colors = ["#ef4444","#f97316","#f59e0b","#10b981",
                  "#06b6d4","#3b82f6","#8b5cf6","#ec4899"]
        c.create_oval(cx-r-4, cy-r-4, cx+r+4, cy+r+4, outline="#f59e0b", width=3)
        slice_deg = 360.0 / n
        for i, item in enumerate(self._sd_wheel_items):
            start = self._sd_wheel_angle + i * slice_deg
            col = colors[i % len(colors)]
            c.create_arc(cx-r, cy-r, cx+r, cy+r,
                         start=start, extent=slice_deg,
                         fill=col, outline="#ffffff", width=2)
            mid = _m.radians(start + slice_deg / 2)
            tx = cx + r * 0.65 * _m.cos(mid)
            ty = cy - r * 0.65 * _m.sin(mid)
            c.create_text(tx, ty, text=item[:6], fill="#ffffff",
                          font=("Malgun Gothic", max(10, w//22), "bold"))
        c.create_oval(cx-16, cy-16, cx+16, cy+16, fill="#0f172a", outline="#f59e0b", width=3)
        c.create_polygon(cx, cy-r-6, cx-8, cy-r+10, cx+8, cy-r+10,
                         fill="#fbbf24", outline="#b45309", width=2)

    def _sd_spin_wheel(self):
        if self._sd_wheel_spinning or not self._sd_wheel_items:
            return
        self._sd_wheel_spinning = True
        speed = 32.0
        decel = 0.984

        def _tick(sp):
            if sp > 0.5:
                self._sd_wheel_angle = (self._sd_wheel_angle + sp) % 360
                self._sd_draw_wheel()
                self.after(16, lambda: _tick(sp * decel))
            else:
                self._sd_wheel_spinning = False
                n = len(self._sd_wheel_items)
                sd = 360.0 / n
                pa = (90.0 - self._sd_wheel_angle) % 360
                win = self._sd_wheel_items[int(pa // sd) % n]
                self._sd_wheel_result.configure(
                    text=f"🎉 당첨: [ {win} ] !",
                    text_color="#10b981"
                )

        _tick(speed)

    # ─── 시계 루프 ────────────────────────────────────────────────────────
    def _start_clock_loop(self):
        self._clock_tick()

    def _clock_tick(self):
        if not self.winfo_exists():
            return
        now = datetime.datetime.now()
        self.clock_lbl.configure(text=now.strftime("%H:%M:%S"))
        # 시간표만 주기적 강조 업데이트 (위젯 재생성 없음)
        self._refresh_schedule_cards()
        self.after(1000, self._clock_tick)
