import os
import sys
import json
import datetime
import tkinter as tk
import customtkinter as ctk
from src.font_config import setup_global_fonts, get_font
from src.timetable_manager import timetable_manager, DAYS_KO
from src.neis_client import neis_client
from src.theme_manager import theme_manager
from src.config_utils import get_config_dir
from src.tooltip import attach_tooltip


class MiniTimetableWidget(ctk.CTkToplevel):
    """
    놀티쳐 데스크 바탕화면 올웨이즈온 스마트 위젯
    - 상시 바탕화면에 상주하며 시간표/급식/알림메모 한눈에 확인
    - 손쉬운 원클릭 크기 프리셋 (소/중/대) 및 A-/A+ 배율 조절
    - 우측 하단 모서리 드래그 크기 리사이징 완비
    - 투명도 조절, 상시 상주 핀 고정, 설정 자동 저장/복원
    """
    _instance = None
    CONFIG_FILE = os.path.join(get_config_dir(), "widget_config.json")

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
        self.parent = parent
        self.title("놀티쳐 바탕화면 위젯")
        self.minsize(240, 280)
        self.resizable(True, True)

        setup_global_fonts(self)
        self._load_icon()

        # 설정 기본값
        self.width = 330
        self.height = 460
        self.opacity = 0.95
        self.is_pinned = True
        self.current_tab = "timetable"  # timetable | meal | memo
        self.zoom = 1.0

        self._load_config()

        # 위치 및 크기 복원
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        pos_x = getattr(self, "pos_x", max(10, sw - self.width - 30))
        pos_y = getattr(self, "pos_y", 80)
        self.geometry(f"{self.width}x{self.height}+{pos_x}+{pos_y}")

        self.attributes("-topmost", self.is_pinned)
        try:
            self.attributes("-alpha", self.opacity)
        except Exception:
            pass

        self._drag_start_x = 0
        self._drag_start_y = 0

        self.protocol("WM_DELETE_WINDOW", self.close)
        self._build_ui()
        self._refresh_content()

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
                    self.width = data.get("width", 330)
                    self.height = data.get("height", 460)
                    self.pos_x = data.get("x", 100)
                    self.pos_y = data.get("y", 100)
                    self.opacity = data.get("opacity", 0.95)
                    self.is_pinned = data.get("is_pinned", True)
                    self.current_tab = data.get("current_tab", "timetable")
                    self.zoom = data.get("zoom", 1.0)
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
                "current_tab": self.current_tab,
                "zoom": self.zoom
            }
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        palette = theme_manager.get_theme()

        self.container = ctk.CTkFrame(
            self, fg_color=palette["card_bg"],
            corner_radius=14, border_width=2, border_color=palette["accent_blue"]
        )
        self.container.pack(fill="both", expand=True, padx=4, pady=4)

        # ── 1. 상단 바 (탭 세그먼트 + 크기 버튼 + 핀/설정/닫기) ─────────────
        top_bar = ctk.CTkFrame(self.container, fg_color=palette["sidebar_bg"], corner_radius=10)
        top_bar.pack(fill="x", padx=6, pady=(6, 4))

        # 세그먼트 버튼 (시간표 / 급식 / 메모)
        tab_names = ["시간표", "급식", "메모"]
        tab_keys = ["timetable", "meal", "memo"]
        cur_label = tab_names[tab_keys.index(self.current_tab)] if self.current_tab in tab_keys else "시간표"

        self.seg_btn = ctk.CTkSegmentedButton(
            top_bar, values=tab_names, font=get_font(10, "bold"),
            command=self._on_seg_changed, height=26
        )
        self.seg_btn.set(cur_label)
        self.seg_btn.pack(side="left", padx=4, pady=4)

        btn_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_box.pack(side="right", padx=4, pady=4)

        # 크기 조절 프리셋 메뉴 버튼
        self.size_btn = ctk.CTkButton(
            btn_box, text="크기▼", width=42, height=24,
            font=get_font(9, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=self._open_size_menu
        )
        self.size_btn.pack(side="left", padx=1)
        attach_tooltip(self.size_btn, "위젯 크기 원클릭 조절 (소/중/대/배율)")

        # 설정 (투명도)
        opt_btn = ctk.CTkButton(
            btn_box, text="⚙️", width=24, height=24,
            font=get_font(10), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=self._open_settings_dialog
        )
        opt_btn.pack(side="left", padx=1)
        attach_tooltip(opt_btn, "투명도 및 위젯 설정")

        # 핀 고정
        self.pin_btn = ctk.CTkButton(
            btn_box, text="📌" if self.is_pinned else "📍",
            width=24, height=24, font=get_font(10),
            fg_color="#0284c7" if self.is_pinned else "#334155",
            hover_color="#0369a1", corner_radius=6, command=self._toggle_pin
        )
        self.pin_btn.pack(side="left", padx=1)
        attach_tooltip(self.pin_btn, "항상 맨 위 상단 고정 토글")

        # 닫기
        close_btn = ctk.CTkButton(
            btn_box, text="✕", width=24, height=24,
            font=get_font(11, "bold"), fg_color="#3f1d24", hover_color="#dc2626",
            text_color="#fca5a5", corner_radius=6, command=self.close
        )
        close_btn.pack(side="left", padx=(1, 2))
        attach_tooltip(close_btn, "위젯 닫기")

        # ── 2. 메인 콘텐츠 스크롤 영역 ────────────────────────────────────
        self.content_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=4, pady=2)

        # ── 3. 하단 상태 바 및 리사이즈 핸들 ──────────────────────────────
        btm_bar = ctk.CTkFrame(self.container, fg_color="transparent", height=20)
        btm_bar.pack(fill="x", side="bottom", padx=6, pady=(0, 2))
        btm_bar.pack_propagate(False)

        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]
        self.date_lbl = ctk.CTkLabel(
            btm_bar, text=f"{today.strftime('%m/%d')} ({weekday_str})",
            font=get_font(9), text_color="#64748b"
        )
        self.date_lbl.pack(side="left")

        # 우측 하단 리사이즈 핸들
        resize_handle = ctk.CTkLabel(
            btm_bar, text="◢", font=get_font(11, "bold"),
            text_color="#475569", width=16, cursor="size_nw_se"
        )
        resize_handle.pack(side="right")
        resize_handle.bind("<Button-1>", self._start_resize)
        resize_handle.bind("<B1-Motion>", self._on_resize)
        attach_tooltip(resize_handle, "드래그하여 위젯 크기 자유 조절")

    # ─── 탭 전환 ──────────────────────────────────────────────────────────
    def _on_seg_changed(self, val: str):
        mapping = {"시간표": "timetable", "급식": "meal", "메모": "memo"}
        self.current_tab = mapping.get(val, "timetable")
        self._refresh_content()
        self._save_config()

    def _refresh_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

        if self.current_tab == "timetable":
            self._render_timetable()
        elif self.current_tab == "meal":
            self._render_meal()
        elif self.current_tab == "memo":
            self._render_memo()

    # ─── 시간표 렌더링 ────────────────────────────────────────────────────
    def _render_timetable(self):
        scroll = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        is_hol, hol_name, items = timetable_manager.get_today_schedule_items()
        now_str = datetime.datetime.now().strftime("%H:%M")

        if is_hol:
            c = ctk.CTkFrame(scroll, fg_color="#3b1d11", corner_radius=8)
            c.pack(fill="x", pady=10)
            ctk.CTkLabel(c, text=f"🇰🇷 [{hol_name}] 공휴일", font=get_font(13, "bold"), text_color="#fdba74").pack(pady=16)
            return

        colors = ["#1e3a8a", "#065f46", "#831843", "#701a75", "#78350f", "#1e293b", "#312e81"]

        for idx, it in enumerate(items):
            is_lunch = it["is_lunch"]
            is_cur = (it["start"] <= now_str <= it["end"])

            card_bg = "#064e3b" if is_cur else ("#3b1d11" if is_lunch else "#181d28")
            border_c = "#10b981" if is_cur else ("#ea580c" if is_lunch else "#334155")

            card = ctk.CTkFrame(scroll, fg_color=card_bg, corner_radius=6,
                                border_width=1, border_color=border_c)
            card.pack(fill="x", pady=2)

            badge_bg = "#ea580c" if is_lunch else colors[idx % len(colors)]
            badge = ctk.CTkLabel(
                card, text=it["name"],
                font=get_font(int(10 * self.zoom), "bold"),
                fg_color=badge_bg, text_color="#ffffff",
                corner_radius=4, width=max(44, int(52 * self.zoom)), height=max(20, int(24 * self.zoom))
            )
            badge.pack(side="left", padx=4, pady=4)

            time_lbl = ctk.CTkLabel(
                card, text=f"{it['start']}~{it['end']}",
                font=get_font(int(9 * self.zoom)),
                text_color="#94a3b8", width=max(68, int(76 * self.zoom))
            )
            time_lbl.pack(side="left")

            subj_lbl = ctk.CTkLabel(
                card, text=it["subject"],
                font=get_font(int(11 * self.zoom), "bold"),
                text_color="#6ee7b7" if is_cur else "#ffffff",
                anchor="w"
            )
            subj_lbl.pack(side="left", fill="x", expand=True, padx=4)

            tag = it.get("tag", "담임")
            if tag in ["전담", "외강"]:
                tag_bg = "#7c3aed" if tag == "전담" else "#0891b2"
                ctk.CTkLabel(
                    card, text=f"[{tag}]", font=get_font(int(9 * self.zoom), "bold"),
                    fg_color=tag_bg, text_color="#ffffff", corner_radius=3,
                    width=max(32, int(38 * self.zoom)), height=18
                ).pack(side="right", padx=4)

    # ─── 급식 렌더링 ──────────────────────────────────────────────────────
    def _render_meal(self):
        scroll = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        try:
            today = datetime.date.today()
            ok, meal_info, _ = neis_client.get_meal_for_date(today)
            dishes = meal_info.get("dishes", []) if ok else []
            cal = meal_info.get("calorie", "") if ok else ""
        except Exception:
            dishes, cal = [], ""

        if cal:
            ctk.CTkLabel(scroll, text=f"🔥 {cal}", font=get_font(int(11 * self.zoom), "bold"),
                         text_color="#4ade80").pack(pady=(2, 6))

        for i, dish in enumerate(dishes):
            row_bg = "#221e10" if i % 2 == 0 else "#181d28"
            row = ctk.CTkFrame(scroll, fg_color=row_bg, corner_radius=6)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"• {dish}",
                         font=get_font(int(11 * self.zoom), "bold"),
                         text_color="#f8fafc", anchor="w").pack(fill="x", padx=10, pady=5)

        if not dishes:
            ctk.CTkLabel(scroll, text="오늘 등록된 급식이 없습니다.",
                         font=get_font(11), text_color="#64748b").pack(pady=20)

    # ─── 알림 메모 렌더링 ────────────────────────────────────────────────
    def _render_memo(self):
        memo_file = os.path.join(get_config_dir(), "widget_memo.txt")
        saved_text = ""
        if os.path.exists(memo_file):
            try:
                with open(memo_file, "r", encoding="utf-8") as f:
                    saved_text = f.read()
            except Exception:
                pass

        box = ctk.CTkTextbox(
            self.content_frame, font=get_font(int(11 * self.zoom)),
            fg_color="#0f172a", text_color="#f8fafc", corner_radius=8
        )
        box.pack(fill="both", expand=True, padx=4, pady=4)
        box.insert("1.0", saved_text if saved_text else "📌 오늘의 알림 메모\n• 준비물 챙기기\n• 전달사항 기록")

        def _auto_save(event=None):
            try:
                with open(memo_file, "w", encoding="utf-8") as f:
                    f.write(box.get("1.0", "end-1c"))
            except Exception:
                pass

        box.bind("<KeyRelease>", _auto_save)

    # ─── 크기 프리셋 메뉴 ─────────────────────────────────────────────────
    def _open_size_menu(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="📱 소형 (280x380)", command=lambda: self._set_preset_size(280, 380, 0.9))
        menu.add_command(label="💻 중형 (340x480 - 기본)", command=lambda: self._set_preset_size(340, 480, 1.0))
        menu.add_command(label="🖥️ 대형 (420x600)", command=lambda: self._set_preset_size(420, 600, 1.2))
        menu.add_separator()
        menu.add_command(label="🔍 글자 확대 (A+)", command=lambda: self._adjust_zoom(0.1))
        menu.add_command(label="🔍 글자 축소 (A-)", command=lambda: self._adjust_zoom(-0.1))

        x = self.winfo_rootx() + self.size_btn.winfo_x()
        y = self.winfo_rooty() + self.size_btn.winfo_y() + 26
        menu.tk_popup(x, y)

    def _set_preset_size(self, w: int, h: int, zoom: float):
        self.width = w
        self.height = h
        self.zoom = zoom
        self.geometry(f"{w}x{h}")
        self._refresh_content()
        self._save_config()

    def _adjust_zoom(self, delta: float):
        self.zoom = max(0.7, min(1.8, round(self.zoom + delta, 1)))
        self._refresh_content()
        self._save_config()

    # ─── 리사이즈 드래그 ─────────────────────────────────────────────────
    def _start_resize(self, event):
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._orig_w = self.winfo_width()
        self._orig_h = self.winfo_height()

    def _on_resize(self, event):
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        nw = max(240, self._orig_w + dx)
        nh = max(280, self._orig_h + dy)
        self.geometry(f"{nw}x{nh}")
        self._save_config()

    # ─── 투명도 설정 팝업 ─────────────────────────────────────────────────
    def _open_settings_dialog(self):
        diag = ctk.CTkToplevel(self)
        diag.title("위젯 설정")
        diag.geometry("260x160")
        diag.resizable(False, False)
        diag.attributes("-topmost", True)

        ctk.CTkLabel(diag, text="⚙️ 위젯 배경 투명도", font=get_font(12, "bold")).pack(pady=(16, 4))
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

        sl = ctk.CTkSlider(diag, from_=0.35, to=1.0, number_of_steps=13, command=_on_slider)
        sl.set(self.opacity)
        sl.pack(fill="x", padx=24, pady=6)

        ctk.CTkButton(diag, text="확인", width=80, height=28, command=diag.destroy).pack(pady=(8, 0))

    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.attributes("-topmost", self.is_pinned)
        self.pin_btn.configure(
            text="📌" if self.is_pinned else "📍",
            fg_color="#0284c7" if self.is_pinned else "#334155"
        )
        self._save_config()

    def close(self):
        self._save_config()
        try:
            self.destroy()
        except Exception:
            pass
        MiniTimetableWidget._instance = None
