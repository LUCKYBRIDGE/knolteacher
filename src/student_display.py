import os
import sys
import json
import time
import threading
import datetime
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

from src.font_config import setup_global_fonts, get_font
from src.timetable_manager import timetable_manager, DAYS_KO
from src.config_utils import get_config_dir
from src.tooltip import attach_tooltip


class StudentDisplayWindow(ctk.CTkToplevel):
    """
    놀티쳐 데스크 학생용 교실 대시보드 (Classroom Board)
    - 교실 대형 TV / 프로젝터 / 전자칠판 전용 대형 스크린
    - 빈 캔버스 위 원하는 모듈(시간표/급식/알림판/타이머/뽑기/돌림판/화상기) 자유 배치
    - 각 모듈 카드 헤더 드래그 이동 & 우하단 리사이즈
    - 원클릭 프리셋: [기본 배치], [수업/타이머 배치], [실물화상기 집중], [4분할 종합]
    - F11 전체화면 & 깜빡임 없는 고성능 렌더링
    """
    _instance = None
    LAYOUT_FILE = os.path.join(get_config_dir(), "student_board_layout.json")

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
        self.title("학생용 교실 화면 (놀티쳐 스마트 보드)")
        self.geometry("1180x760")
        self.minsize(800, 540)
        self.resizable(True, True)
        self.configure(fg_color="#090d16")

        setup_global_fonts(self)
        self._load_icon()

        self.is_fullscreen = False
        self.is_pinned = False
        self.global_zoom = 1.0

        # 모듈 인스턴스 딕셔너리: key -> {"frame": ..., "header": ..., "content": ..., "x": ..., "y": ..., "w": ..., "h": ...}
        self.modules = {}

        # 실물화상기 스트림 관련
        self.cam_running = False
        self.cam_cap = None
        self.cam_latest_frame = None
        self.cam_photo = None
        self.cam_freeze = False
        self.cam_frozen_frame = None
        self.cam_rot = 0
        self.cam_flip = False

        # 타이머 상태
        self.timer_seconds = 300
        self.timer_running = False
        self.timer_job = None

        # 돌림판 상태
        self.wheel_items = ["1모둠", "2모둠", "3모둠", "4모둠"]
        self.wheel_angle = 0.0
        self.wheel_spinning = False

        self.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._exit_fullscreen())
        self.protocol("WM_DELETE_WINDOW", self.close)

        self._build_ui()
        self._load_layout_or_default()
        self._start_clock_loop()

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    # ─── UI 상단 컨트롤 바 ────────────────────────────────────────────────
    def _build_ui(self):
        # 1. 상단 글로벌 컨트롤 바
        self.top_bar = ctk.CTkFrame(self, fg_color="#111827", height=52, corner_radius=0)
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)

        tb_in = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        tb_in.pack(fill="both", expand=True, padx=12, pady=6)

        # 날짜
        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]
        self.date_lbl = ctk.CTkLabel(
            tb_in, text=f"📅 {today.strftime('%Y년 %m월 %d일')} ({weekday_str})",
            font=get_font(13, "bold"), text_color="#38bdf8"
        )
        self.date_lbl.pack(side="left", padx=(4, 12))

        # 프리셋 자동 배치 버튼 그룹
        preset_box = ctk.CTkFrame(tb_in, fg_color="transparent")
        preset_box.pack(side="left", padx=4)

        presets = [
            ("🌟 기본형", self.preset_default, "시간표 + 급식 + 알림판 기본 배치"),
            ("⏱️ 타이머형", self.preset_activity, "대형 타이머 + 발표자 뽑기 집중 배치"),
            ("📷 화상기형", self.preset_visualizer, "대형 실물화상기 + 타이머 집중 배치"),
            ("🗂️ 4분할형", self.preset_quad, "시간표, 급식, 타이머, 뽑기 4분할 격자 배치")
        ]
        for p_name, p_cmd, p_tip in presets:
            b = ctk.CTkButton(
                preset_box, text=p_name, width=68, height=28,
                font=get_font(10, "bold"), fg_color="#1e293b", hover_color="#0284c7",
                corner_radius=6, command=p_cmd
            )
            b.pack(side="left", padx=2)
            attach_tooltip(b, p_tip)

        # 모듈 추가 드롭다운 메뉴 버튼
        add_btn = ctk.CTkButton(
            tb_in, text="➕ 모듈 띄우기▼", width=105, height=28,
            font=get_font(10, "bold"), fg_color="#059669", hover_color="#047857",
            corner_radius=6, command=self._open_add_module_menu
        )
        add_btn.pack(side="left", padx=8)
        attach_tooltip(add_btn, "숨겨진 수업 모듈을 화면에 다시 추가")
        self.add_btn_ref = add_btn

        # 우측: 시계 + 배율 + 전체화면 + 핀 + 닫기
        r_box = ctk.CTkFrame(tb_in, fg_color="transparent")
        r_box.pack(side="right")

        self.clock_lbl = ctk.CTkLabel(
            r_box, text="00:00:00",
            font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
            text_color="#4ade80"
        )
        self.clock_lbl.pack(side="left", padx=(0, 10))

        # 배율
        ctk.CTkButton(
            r_box, text="A-", width=26, height=26, font=get_font(9, "bold"),
            fg_color="#334155", command=lambda: self._zoom_step(-0.1)
        ).pack(side="left", padx=1)

        self.zoom_lbl = ctk.CTkLabel(r_box, text="100%", width=36, font=get_font(9, "bold"), text_color="#94a3b8")
        self.zoom_lbl.pack(side="left", padx=1)

        ctk.CTkButton(
            r_box, text="A+", width=26, height=26, font=get_font(9, "bold"),
            fg_color="#334155", command=lambda: self._zoom_step(0.1)
        ).pack(side="left", padx=1)

        # 핀
        self.pin_btn = ctk.CTkButton(
            r_box, text="📍", width=26, height=26, font=get_font(10),
            fg_color="#334155", hover_color="#475569", corner_radius=6,
            command=self._toggle_pin
        )
        self.pin_btn.pack(side="left", padx=2)
        attach_tooltip(self.pin_btn, "항상 위 고정")

        # 전체화면
        self.fs_btn = ctk.CTkButton(
            r_box, text="⛶", width=26, height=26, font=get_font(11),
            fg_color="#334155", hover_color="#475569", corner_radius=6,
            command=self._toggle_fullscreen
        )
        self.fs_btn.pack(side="left", padx=1)
        attach_tooltip(self.fs_btn, "교실 전체화면 (F11)")

        # 닫기
        ctk.CTkButton(
            r_box, text="✕", width=26, height=26, font=get_font(11, "bold"),
            fg_color="#3f1d24", hover_color="#dc2626", text_color="#fca5a5",
            corner_radius=6, command=self.close
        ).pack(side="left", padx=(2, 0))

        # 2. 메인 자유 대시보드 캔버스 컨테이너
        self.board_area = tk.Canvas(
            self, bg="#060911", highlightthickness=0
        )
        self.board_area.pack(fill="both", expand=True)

        # 하단 힌트
        self.hint_bar = ctk.CTkFrame(self, fg_color="#090d16", height=22)
        self.hint_bar.pack(fill="x", side="bottom")
        self.hint_bar.pack_propagate(False)

        ctk.CTkLabel(
            self.hint_bar,
            text="💡 각 카드의 헤더를 잡고 드래그하면 자유 이동, 우측 하단(◢)을 잡고 드래그하면 크기 조절이 가능합니다. [F11] 전체화면",
            font=get_font(9), text_color="#475569"
        ).pack(side="left", padx=12)

    # ─── 모듈 카드 생성 및 관리 ───────────────────────────────────────────
    def _create_module_card(self, mod_key: str, title: str, x: int, y: int, w: int, h: int):
        """대시보드 위에 드래그/리사이즈 가능한 독립 모듈 카드 생성"""
        if mod_key in self.modules:
            card = self.modules[mod_key]["frame"]
            card.place(x=x, y=y, width=w, height=h)
            card.lift()
            return

        card_frame = ctk.CTkFrame(
            self.board_area, fg_color="#131b2e", corner_radius=12,
            border_width=1, border_color="#334155"
        )
        card_frame.place(x=x, y=y, width=w, height=h)

        # 상단 헤더 (드래그 핸들)
        header = ctk.CTkFrame(card_frame, fg_color="#1e293b", height=32, corner_radius=10)
        header.pack(fill="x", side="top", padx=3, pady=3)
        header.pack_propagate(False)

        title_lbl = ctk.CTkLabel(
            header, text=title, font=get_font(11, "bold"), text_color="#38bdf8", cursor="fleur"
        )
        title_lbl.pack(side="left", padx=(8, 4))

        close_btn = ctk.CTkButton(
            header, text="✕", width=20, height=20, font=get_font(9, "bold"),
            fg_color="#3f1d24", hover_color="#dc2626", text_color="#fca5a5",
            corner_radius=4, command=lambda k=mod_key: self._hide_module(k)
        )
        close_btn.pack(side="right", padx=4)
        attach_tooltip(close_btn, "이 모듈 숨기기 (상단 [모듈 띄우기]로 다시 열기)")

        # 콘텐츠 영역
        body = ctk.CTkFrame(card_frame, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=4, pady=(0, 2))

        # 하단 리사이즈 핸들 바
        b_bar = ctk.CTkFrame(card_frame, fg_color="transparent", height=14)
        b_bar.pack(fill="x", side="bottom")
        b_bar.pack_propagate(False)

        rs_handle = ctk.CTkLabel(
            b_bar, text="◢", font=get_font(10, "bold"),
            text_color="#475569", width=16, cursor="size_nw_se"
        )
        rs_handle.pack(side="right", padx=2)

        # 바인딩 (이동 드래그)
        for w_elem in [header, title_lbl]:
            w_elem.bind("<Button-1>", lambda e, k=mod_key: self._start_card_drag(e, k))
            w_elem.bind("<B1-Motion>", lambda e, k=mod_key: self._on_card_drag(e, k))
            w_elem.bind("<ButtonRelease-1>", lambda e: self._save_layout())

        # 바인딩 (리사이즈 드래그)
        rs_handle.bind("<Button-1>", lambda e, k=mod_key: self._start_card_resize(e, k))
        rs_handle.bind("<B1-Motion>", lambda e, k=mod_key: self._on_card_resize(e, k))
        rs_handle.bind("<ButtonRelease-1>", lambda e: self._save_layout())

        self.modules[mod_key] = {
            "frame": card_frame,
            "header": header,
            "body": body,
            "title": title,
            "x": x, "y": y, "w": w, "h": h
        }

        # 내부 내용 렌더링
        self._populate_module_body(mod_key, body)

    def _start_card_drag(self, event, mod_key: str):
        card = self.modules[mod_key]["frame"]
        card.lift()
        self._drag_card_key = mod_key
        self._drag_mouse_x = event.x_root
        self._drag_mouse_y = event.y_root
        self._drag_card_x = card.winfo_x()
        self._drag_card_y = card.winfo_y()

    def _on_card_drag(self, event, mod_key: str):
        dx = event.x_root - self._drag_mouse_x
        dy = event.y_root - self._drag_mouse_y
        nx = max(0, self._drag_card_x + dx)
        ny = max(0, self._drag_card_y + dy)
        card = self.modules[mod_key]["frame"]
        card.place(x=nx, y=ny)
        self.modules[mod_key]["x"] = nx
        self.modules[mod_key]["y"] = ny

    def _start_card_resize(self, event, mod_key: str):
        card = self.modules[mod_key]["frame"]
        card.lift()
        self._rs_card_key = mod_key
        self._rs_mouse_x = event.x_root
        self._rs_mouse_y = event.y_root
        self._rs_orig_w = card.winfo_width()
        self._rs_orig_h = card.winfo_height()

    def _on_card_resize(self, event, mod_key: str):
        dx = event.x_root - self._rs_mouse_x
        dy = event.y_root - self._rs_mouse_y
        nw = max(220, self._rs_orig_w + dx)
        nh = max(180, self._rs_orig_h + dy)
        card = self.modules[mod_key]["frame"]
        card.place(width=nw, height=nh)
        self.modules[mod_key]["w"] = nw
        self.modules[mod_key]["h"] = nh

    def _hide_module(self, mod_key: str):
        if mod_key in self.modules:
            if mod_key == "visualizer":
                self._stop_camera_stream()
            self.modules[mod_key]["frame"].place_forget()
            self._save_layout()

    # ─── 각 모듈의 내부 내용 채우기 ───────────────────────────────────────
    def _populate_module_body(self, key: str, body):
        if key == "schedule":
            self._build_body_schedule(body)
        elif key == "meal":
            self._build_body_meal(body)
        elif key == "notice":
            self._build_body_notice(body)
        elif key == "timer":
            self._build_body_timer(body)
        elif key == "picker":
            self._build_body_picker(body)
        elif key == "wheel":
            self._build_body_wheel(body)
        elif key == "visualizer":
            self._build_body_visualizer(body)

    # 1. 시간표 모듈
    def _build_body_schedule(self, body):
        self.sd_sched_scroll = ctk.CTkScrollableFrame(body, fg_color="transparent")
        self.sd_sched_scroll.pack(fill="both", expand=True)
        self._render_schedule_items()

    def _render_schedule_items(self):
        if not hasattr(self, "sd_sched_scroll") or not self.sd_sched_scroll.winfo_exists():
            return
        for w in self.sd_sched_scroll.winfo_children():
            w.destroy()

        is_hol, hol_name, items = timetable_manager.get_today_schedule_items()
        now_str = datetime.datetime.now().strftime("%H:%M")

        if is_hol:
            c = ctk.CTkFrame(self.sd_sched_scroll, fg_color="#3b1d11", corner_radius=8)
            c.pack(fill="x", pady=10)
            ctk.CTkLabel(c, text=f"🇰🇷 [{hol_name}] 공휴일", font=get_font(13, "bold"), text_color="#fdba74").pack(pady=12)
            return

        colors = ["#1e3a8a", "#065f46", "#831843", "#701a75", "#78350f", "#1e293b", "#312e81"]
        for idx, it in enumerate(items):
            is_cur = (it["start"] <= now_str <= it["end"])
            is_lunch = it["is_lunch"]
            card_bg = "#064e3b" if is_cur else ("#3b1d11" if is_lunch else "#181d28")
            border_c = "#10b981" if is_cur else ("#ea580c" if is_lunch else "#334155")

            card = ctk.CTkFrame(self.sd_sched_scroll, fg_color=card_bg, corner_radius=6, border_width=1, border_color=border_c)
            card.pack(fill="x", pady=2)

            badge_bg = "#ea580c" if is_lunch else colors[idx % len(colors)]
            ctk.CTkLabel(card, text=it["name"], font=get_font(11, "bold"), fg_color=badge_bg, text_color="#ffffff", corner_radius=4, width=54, height=24).pack(side="left", padx=6, pady=4)
            ctk.CTkLabel(card, text=f"{it['start']}~{it['end']}", font=get_font(10), text_color="#94a3b8", width=74).pack(side="left")
            ctk.CTkLabel(card, text=it["subject"], font=get_font(12, "bold"), text_color="#6ee7b7" if is_cur else "#ffffff", anchor="w").pack(side="left", fill="x", expand=True, padx=4)

            tag = it.get("tag", "담임")
            if tag in ["전담", "외강"]:
                ctk.CTkLabel(card, text=f"[{tag}]", font=get_font(10, "bold"), fg_color="#7c3aed" if tag == "전담" else "#0891b2", text_color="#ffffff", corner_radius=3, width=38, height=18).pack(side="right", padx=6)

    # 2. 급식 모듈
    def _build_body_meal(self, body):
        scroll = ctk.CTkScrollableFrame(body, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        try:
            today = datetime.date.today()
            ok, meal_info, _ = neis_client.get_meal_for_date(today)
            dishes = meal_info.get("dishes", []) if ok else []
            cal = meal_info.get("calorie", "") if ok else ""
        except Exception:
            dishes, cal = [], ""

        if cal:
            ctk.CTkLabel(scroll, text=f"🔥 {cal}", font=get_font(11, "bold"), text_color="#4ade80").pack(pady=(2, 4))

        for i, dish in enumerate(dishes):
            row = ctk.CTkFrame(scroll, fg_color="#221e10" if i % 2 == 0 else "#181d28", corner_radius=4)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"• {dish}", font=get_font(11, "bold"), text_color="#f8fafc", anchor="w").pack(fill="x", padx=8, pady=4)

        if not dishes:
            ctk.CTkLabel(scroll, text="오늘 등록된 급식이 없습니다.", font=get_font(11), text_color="#64748b").pack(pady=20)

    # 3. 알림판 모듈
    def _build_body_notice(self, body):
        box = ctk.CTkTextbox(body, font=get_font(11), fg_color="#090d16", text_color="#f8fafc", corner_radius=6)
        box.pack(fill="both", expand=True, padx=2, pady=2)
        box.insert("1.0", "1. 수업 시작 3분 전 자리에 앉기\n2. 쉬는 시간 복도에서 뛰지 않기\n3. 준비물 및 과제 챙기기\n\n\"배움에는 끝이 없다.\"")

    # 4. 타이머 모듈
    def _build_body_timer(self, body):
        self.timer_disp = ctk.CTkLabel(body, text="05:00", font=ctk.CTkFont(family="Consolas", size=48, weight="bold"), text_color="#4ade80")
        self.timer_disp.pack(pady=(8, 4))

        presets = ctk.CTkFrame(body, fg_color="transparent")
        presets.pack(pady=2)
        for m in [1, 3, 5, 10, 15]:
            ctk.CTkButton(presets, text=f"{m}분", font=get_font(10, "bold"), width=38, height=24, fg_color="#1e293b", command=lambda mins=m: self._timer_set(mins * 60)).pack(side="left", padx=2)

        ctrl = ctk.CTkFrame(body, fg_color="transparent")
        ctrl.pack(pady=6)
        self.timer_btn = ctk.CTkButton(ctrl, text="▶ 시작", font=get_font(12, "bold"), width=72, height=32, fg_color="#059669", command=self._timer_toggle)
        self.timer_btn.pack(side="left", padx=4)
        ctk.CTkButton(ctrl, text="↺ 리셋", font=get_font(11), width=60, height=32, fg_color="#334155", command=lambda: self._timer_set(300)).pack(side="left", padx=4)

    def _timer_set(self, secs):
        self.timer_running = False
        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None
        self.timer_seconds = secs
        m, s = divmod(secs, 60)
        self.timer_disp.configure(text=f"{m:02d}:{s:02d}", text_color="#4ade80")
        self.timer_btn.configure(text="▶ 시작", fg_color="#059669")

    def _timer_toggle(self):
        if self.timer_running:
            self.timer_running = False
            if self.timer_job:
                self.after_cancel(self.timer_job)
                self.timer_job = None
            self.timer_btn.configure(text="▶ 계속", fg_color="#059669")
        else:
            self.timer_running = True
            self.timer_btn.configure(text="⏸ 정지", fg_color="#d97706")
            self._timer_tick()

    def _timer_tick(self):
        if not self.timer_running:
            return
        if self.timer_seconds <= 0:
            self.timer_running = False
            self.timer_disp.configure(text="00:00", text_color="#ef4444")
            self.timer_btn.configure(text="▶ 시작", fg_color="#059669")
            return
        self.timer_seconds -= 1
        m, s = divmod(self.timer_seconds, 60)
        col = "#ef4444" if self.timer_seconds <= 10 else ("#fb923c" if self.timer_seconds <= 30 else "#4ade80")
        self.timer_disp.configure(text=f"{m:02d}:{s:02d}", text_color=col)
        self.timer_job = self.after(1000, self._timer_tick)

    # 5. 발표자 뽑기 모듈
    def _build_body_picker(self, body):
        from src.student_manager import student_manager
        self.picker_lbl = ctk.CTkLabel(body, text="발표자 뽑기", font=get_font(20, "bold"), text_color="#fde047")
        self.picker_lbl.pack(expand=True, pady=10)

        def _pick():
            names = student_manager.get_student_names()
            if names:
                import random
                self.picker_lbl.configure(text=f"🎉  {random.choice(names)}  🎉", text_color="#4ade80")
            else:
                self.picker_lbl.configure(text="학생 명단 없음", text_color="#f87171")

        ctk.CTkButton(body, text="🎯 발표자 추첨!", font=get_font(13, "bold"), width=120, height=40, fg_color="#7c3aed", hover_color="#6d28d9", command=_pick).pack(pady=(0, 10))

    # 6. 돌림판 모듈
    def _build_body_wheel(self, body):
        import math, random
        self.wheel_canvas = tk.Canvas(body, bg="#131b2e", highlightthickness=0, width=180, height=180)
        self.wheel_canvas.pack(pady=4)

        def _draw():
            c = self.wheel_canvas
            c.delete("all")
            n = len(self.wheel_items)
            w = int(c["width"])
            cx, cy, r = w//2, w//2, w//2 - 6
            colors = ["#ef4444","#f97316","#f59e0b","#10b981","#06b6d4","#3b82f6","#8b5cf6"]
            slice_deg = 360.0 / n
            for i, itm in enumerate(self.wheel_items):
                st = self.wheel_angle + i * slice_deg
                c.create_arc(cx-r, cy-r, cx+r, cy+r, start=st, extent=slice_deg, fill=colors[i % len(colors)], outline="#ffffff")
                mid = math.radians(st + slice_deg / 2)
                c.create_text(cx + r*0.6*math.cos(mid), cy - r*0.6*math.sin(mid), text=itm[:4], fill="#ffffff", font=("Malgun Gothic", 9, "bold"))
            c.create_polygon(cx, cy-r-4, cx-6, cy-r+8, cx+6, cy-r+8, fill="#fbbf24")

        self._draw_board_wheel = _draw
        _draw()

        def _spin():
            if self.wheel_spinning:
                return
            self.wheel_spinning = True
            def _tick(sp):
                if sp > 0.6:
                    self.wheel_angle = (self.wheel_angle + sp) % 360
                    self._draw_board_wheel()
                    self.after(16, lambda: _tick(sp * 0.98))
                else:
                    self.wheel_spinning = False
            _tick(30.0)

        ctk.CTkButton(body, text="🚀 돌리기!", font=get_font(11, "bold"), width=90, height=28, fg_color="#ea580c", command=_spin).pack(pady=4)

    # 7. 실물화상기 모듈
    def _build_body_visualizer(self, body):
        import cv2
        self.cam_canvas = tk.Canvas(body, bg="#000000", highlightthickness=0)
        self.cam_canvas.pack(fill="both", expand=True)

        bar = ctk.CTkFrame(body, fg_color="transparent", height=28)
        bar.pack(fill="x", pady=2)
        ctk.CTkButton(bar, text="⟳ 회전", width=44, height=22, font=get_font(9), fg_color="#1e293b", command=self._rotate_cam).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="↔ 반전", width=44, height=22, font=get_font(9), fg_color="#1e293b", command=self._flip_cam).pack(side="left", padx=2)
        self.freeze_cam_btn = ctk.CTkButton(bar, text="❄️ 정지", width=46, height=22, font=get_font(9), fg_color="#1e293b", command=self._toggle_cam_freeze)
        self.freeze_cam_btn.pack(side="left", padx=2)

        self._start_camera_stream()

    def _rotate_cam(self):
        self.cam_rot = (self.cam_rot + 90) % 360

    def _flip_cam(self):
        self.cam_flip = not self.cam_flip

    def _toggle_cam_freeze(self):
        self.cam_freeze = not self.cam_freeze
        if self.cam_freeze:
            self.cam_frozen_frame = self.cam_latest_frame.copy() if self.cam_latest_frame is not None else None
            self.freeze_cam_btn.configure(text="▶ 재생", fg_color="#ea580c")
        else:
            self.cam_frozen_frame = None
            self.freeze_cam_btn.configure(text="❄️ 정지", fg_color="#1e293b")

    def _start_camera_stream(self):
        if self.cam_running:
            return
        self.cam_running = True
        threading.Thread(target=self._cam_worker, daemon=True).start()
        self._cam_render_tick()

    def _cam_worker(self):
        import cv2
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(0)
        self.cam_cap = cap
        while self.cam_running and cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                self.cam_latest_frame = frame
            else:
                time.sleep(0.03)
            time.sleep(0.01)
        cap.release()

    def _cam_render_tick(self):
        if not self.cam_running or not self.winfo_exists():
            return
        frame = self.cam_frozen_frame if self.cam_freeze else self.cam_latest_frame
        if frame is not None and hasattr(self, "cam_canvas") and self.cam_canvas.winfo_exists():
            import cv2
            cw = self.cam_canvas.winfo_width()
            ch = self.cam_canvas.winfo_height()
            if cw > 20 and ch > 20:
                img = frame.copy()
                if self.cam_rot == 90:
                    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                elif self.cam_rot == 180:
                    img = cv2.rotate(img, cv2.ROTATE_180)
                elif self.cam_rot == 270:
                    img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
                if self.cam_flip:
                    img = cv2.flip(img, 1)

                ih, iw = img.shape[:2]
                scale = min(cw / iw, ch / ih)
                nw = max(1, int(iw * scale))
                nh = max(1, int(ih * scale))
                img_rgb = cv2.cvtColor(cv2.resize(img, (nw, nh)), cv2.COLOR_BGR2RGB)
                self.cam_photo = ImageTk.PhotoImage(Image.fromarray(img_rgb))
                self.cam_canvas.delete("all")
                self.cam_canvas.create_image(cw // 2, ch // 2, image=self.cam_photo, anchor="center")

        self.after(33, self._cam_render_tick)

    def _stop_camera_stream(self):
        self.cam_running = False
        if self.cam_cap:
            try:
                self.cam_cap.release()
            except Exception:
                pass
            self.cam_cap = None

    # ─── 프리셋 원클릭 자동 배치 ──────────────────────────────────────────
    def preset_default(self):
        """기본 배치: 좌측 시간표 + 우측 급식 & 알림판"""
        self._stop_camera_stream()
        for k in list(self.modules.keys()):
            if k not in ["schedule", "meal", "notice"]:
                self._hide_module(k)

        self._create_module_card("schedule", "📋 오늘의 수업 시간표", 20, 20, 560, 640)
        self._create_module_card("meal", "🍱 오늘의 점심 급식", 600, 20, 520, 310)
        self._create_module_card("notice", "📌 교실 알림판", 600, 350, 520, 310)
        self._save_layout()

    def preset_activity(self):
        """활동/타이머 배치: 대형 타이머 + 우측 발표자 뽑기 & 알림판"""
        self._stop_camera_stream()
        for k in list(self.modules.keys()):
            if k not in ["timer", "picker", "notice", "wheel"]:
                self._hide_module(k)

        self._create_module_card("timer", "⏱ 집중 타이머", 20, 20, 580, 380)
        self._create_module_card("wheel", "🎡 돌림판", 20, 420, 580, 260)
        self._create_module_card("picker", "🎲 발표자 뽑기", 620, 20, 500, 260)
        self._create_module_card("notice", "📌 활동 안내", 620, 300, 500, 380)
        self._save_layout()

    def preset_visualizer(self):
        """실물화상기 집중 배치: 대형 실물화상기 + 우측 타이머 & 알림판"""
        for k in list(self.modules.keys()):
            if k not in ["visualizer", "timer", "notice"]:
                self._hide_module(k)

        self._create_module_card("visualizer", "📷 실물화상기 화면", 20, 20, 720, 650)
        self._create_module_card("timer", "⏱ 교실 타이머", 760, 20, 360, 300)
        self._create_module_card("notice", "📌 수업 메모", 760, 340, 360, 330)
        self._save_layout()

    def preset_quad(self):
        """4분할 종합 배치: 시간표, 급식, 타이머, 뽑기"""
        self._stop_camera_stream()
        for k in list(self.modules.keys()):
            if k not in ["schedule", "meal", "timer", "picker"]:
                self._hide_module(k)

        self._create_module_card("schedule", "📋 오늘의 시간표", 20, 20, 540, 320)
        self._create_module_card("meal", "🍱 오늘의 점심", 580, 20, 540, 320)
        self._create_module_card("timer", "⏱ 집중 타이머", 20, 360, 540, 300)
        self._create_module_card("picker", "🎲 발표자 뽑기", 580, 360, 540, 300)
        self._save_layout()

    # ─── 모듈 띄우기 드롭다운 ─────────────────────────────────────────────
    def _open_add_module_menu(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="📋 시간표 모듈 띄우기", command=lambda: self._show_or_add_module("schedule", "📋 오늘의 수업 시간표", 40, 40, 500, 450))
        menu.add_command(label="🍱 급식 식단 모듈 띄우기", command=lambda: self._show_or_add_module("meal", "🍱 오늘의 점심 급식", 80, 80, 420, 320))
        menu.add_command(label="📌 알림판/메모 띄우기", command=lambda: self._show_or_add_module("notice", "📌 교실 알림판", 120, 120, 400, 300))
        menu.add_command(label="⏱ 교실 타이머 띄우기", command=lambda: self._show_or_add_module("timer", "⏱ 집중 타이머", 160, 160, 460, 300))
        menu.add_command(label="🎲 발표자 뽑기 띄우기", command=lambda: self._show_or_add_module("picker", "🎲 발표자 뽑기", 200, 200, 380, 240))
        menu.add_command(label="🎡 돌려돌려 돌림판 띄우기", command=lambda: self._show_or_add_module("wheel", "🎡 돌림판", 240, 240, 340, 320))
        menu.add_command(label="📷 실물화상기 띄우기", command=lambda: self._show_or_add_module("visualizer", "📷 실물화상기 화면", 60, 60, 640, 500))

        x = self.winfo_rootx() + self.add_btn_ref.winfo_x()
        y = self.winfo_rooty() + self.add_btn_ref.winfo_y() + 28
        menu.tk_popup(x, y)

    def _show_or_add_module(self, key: str, title: str, def_x: int, def_y: int, def_w: int, def_h: int):
        self._create_module_card(key, title, def_x, def_y, def_w, def_h)
        self._save_layout()

    # ─── 레이아웃 저장 & 복원 ─────────────────────────────────────────────
    def _save_layout(self):
        data = {}
        for k, v in self.modules.items():
            card = v["frame"]
            if card.winfo_viewable():
                data[k] = {
                    "title": v["title"],
                    "x": card.winfo_x(),
                    "y": card.winfo_y(),
                    "w": card.winfo_width(),
                    "h": card.winfo_height()
                }
        try:
            with open(self.LAYOUT_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_layout_or_default(self):
        if os.path.exists(self.LAYOUT_FILE):
            try:
                with open(self.LAYOUT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    for k, info in data.items():
                        self._create_module_card(
                            k, info.get("title", k),
                            info.get("x", 40), info.get("y", 40),
                            info.get("w", 400), info.get("h", 300)
                        )
                    return
            except Exception:
                pass
        # 파일이 없으면 기본 프리셋 적용
        self.preset_default()

    # ─── 컨트롤 루프 및 이벤트 ───────────────────────────────────────────
    def _zoom_step(self, delta: float):
        self.global_zoom = max(0.7, min(2.0, round(self.global_zoom + delta, 1)))
        self.zoom_lbl.configure(text=f"{int(self.global_zoom * 100)}%")

    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.attributes("-topmost", self.is_pinned)
        self.pin_btn.configure(
            text="📌" if self.is_pinned else "📍",
            fg_color="#0284c7" if self.is_pinned else "#334155"
        )

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        if self.is_fullscreen:
            self.top_bar.pack_forget()
            self.hint_bar.pack_forget()
        else:
            self.top_bar.pack(fill="x", side="top", before=self.board_area)
            self.hint_bar.pack(fill="x", side="bottom")

    def _exit_fullscreen(self):
        if self.is_fullscreen:
            self._toggle_fullscreen()

    def _start_clock_loop(self):
        self._clock_tick()

    def _clock_tick(self):
        if not self.winfo_exists():
            return
        now = datetime.datetime.now()
        self.clock_lbl.configure(text=now.strftime("%H:%M:%S"))
        self.after(1000, self._clock_tick)

    def close(self):
        self._save_layout()
        self._stop_camera_stream()
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass
        StudentDisplayWindow._instance = None
