import os
import sys
import datetime
import customtkinter as ctk
from src.font_config import setup_global_fonts, get_font
from src.timetable_manager import timetable_manager, DAYS_KO
from src.neis_client import neis_client
from src.theme_manager import theme_manager
from src.tooltip import attach_tooltip

class MiniTimetableWidget(ctk.CTkToplevel):
    """
    놀티쳐 데스크 바탕화면 올웨이즈온 미니 위젯
    - 상단 탭 세그먼트 (📅 시간표 / 🍱 오늘 급식)
    - 상단 고정 핀(📌), 새로고침(🔄), 최소화(—), 닫기(✕) 컨트롤러 완비
    - 모든 버튼에 직관적인 풍선도움말(Tooltip) 탑재
    - 자유로운 리사이즈 및 베이지/다크 테마 고대비 지원
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.title("놀티쳐 미니 위젯")
        self.geometry("320x480")
        self.minsize(260, 320)
        self.resizable(True, True)
        self.attributes("-topmost", True)
        self.is_pinned = True
        self.current_tab = "timetable"  # timetable | meal

        setup_global_fonts(self)
        self._load_icon()

        # 화면 우측 상단에 기본 배치
        sw = self.winfo_screenwidth()
        x = max(10, sw - 350)
        y = 60
        self.geometry(f"320x480+{x}+{y}")

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

    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.attributes("-topmost", self.is_pinned)
        self.pin_btn.configure(
            text="📌" if self.is_pinned else "📍",
            fg_color="#0284c7" if self.is_pinned else "#334155"
        )

    def _build_ui(self):
        palette = theme_manager.get_theme()
        
        self.container = ctk.CTkFrame(
            self,
            fg_color=palette["card_bg"],
            corner_radius=14,
            border_width=2,
            border_color=palette["accent_blue"]
        )
        self.container.pack(fill="both", expand=True, padx=4, pady=4)

        # 1. 상단 헤더 (서브 탭 세그먼트 & 창 제어 버튼)
        header = ctk.CTkFrame(self.container, fg_color=palette["sidebar_bg"], corner_radius=10)
        header.pack(fill="x", padx=4, pady=4)

        self.seg_btn = ctk.CTkSegmentedButton(
            header,
            values=["📅 시간표", "🍱 오늘 급식"],
            font=get_font(11, "bold"),
            command=self._on_tab_changed
        )
        self.seg_btn.set("📅 시간표")
        self.seg_btn.pack(side="left", padx=4, pady=4)

        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right", padx=4, pady=4)

        self.pin_btn = ctk.CTkButton(
            btn_box,
            text="📌",
            width=24,
            height=24,
            font=get_font(10),
            fg_color="#0284c7",
            hover_color="#0369a1",
            corner_radius=6,
            command=self._toggle_pin
        )
        self.pin_btn.pack(side="left", padx=1)
        attach_tooltip(self.pin_btn, "항상 맨 위 상단 고정 토글")

        refresh_btn = ctk.CTkButton(
            btn_box,
            text="🔄",
            width=24,
            height=24,
            font=get_font(10),
            fg_color="#334155",
            hover_color="#475569",
            corner_radius=6,
            command=self._refresh_content
        )
        refresh_btn.pack(side="left", padx=1)
        attach_tooltip(refresh_btn, "시간표/급식 새로고침")

        min_btn = ctk.CTkButton(
            btn_box,
            text="—",
            width=24,
            height=24,
            font=get_font(10, "bold"),
            fg_color="#334155",
            hover_color="#475569",
            corner_radius=6,
            command=self.iconify
        )
        min_btn.pack(side="left", padx=1)
        attach_tooltip(min_btn, "작업표시줄로 최소화")

        close_btn = ctk.CTkButton(
            btn_box,
            text="✕",
            width=24,
            height=24,
            font=get_font(10, "bold"),
            fg_color="#3f1d24",
            hover_color="#dc2626",
            text_color="#fca5a5",
            corner_radius=6,
            command=self.destroy
        )
        close_btn.pack(side="left", padx=1)
        attach_tooltip(close_btn, "미니 위젯 닫기")

        # 2. 메인 스크롤 프레임
        self.scroll = ctk.CTkScrollableFrame(self.container, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=4, pady=2)

    def _on_tab_changed(self, choice: str):
        if "급식" in choice:
            self.current_tab = "meal"
        else:
            self.current_tab = "timetable"
        self._refresh_content()

    def _refresh_content(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        if self.current_tab == "timetable":
            self._render_timetable_view()
        else:
            self._render_meal_view()

    def _render_timetable_view(self):
        palette = theme_manager.get_theme()
        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]
        is_hol, hol_name, items = timetable_manager.get_today_schedule_items()
        now_str = datetime.datetime.now().strftime("%H:%M")

        # 오늘 날짜 배너
        date_box = ctk.CTkFrame(self.scroll, fg_color=palette["sidebar_bg"], corner_radius=8)
        date_box.pack(fill="x", pady=(0, 4))
        
        t_str = f"📅 {today.strftime('%m월 %d일')} ({weekday_str}요일)"
        if is_hol:
            t_str += f" - [{hol_name}]"
        
        ctk.CTkLabel(
            date_box,
            text=t_str,
            font=get_font(11, "bold"),
            text_color=palette["text_main"] if not is_hol else "#f97316"
        ).pack(pady=4)

        if is_hol:
            c = ctk.CTkFrame(self.scroll, fg_color="#3b1d11", corner_radius=8)
            c.pack(fill="x", pady=8)
            ctk.CTkLabel(c, text=f"🇰🇷 오늘은 [{hol_name}] 공휴일입니다.\n오늘 설정된 정규 수업은 없습니다.", font=get_font(11, "bold"), text_color="#fdba74").pack(pady=14)
            return

        colors = ["#1e3a8a", "#065f46", "#831843", "#701a75", "#78350f", "#1e293b"]

        for idx, it in enumerate(items):
            is_lunch = it["is_lunch"]
            start_s, end_s = it["start"], it["end"]
            is_current = (start_s <= now_str <= end_s)

            if is_current:
                card_border = "#15803d"
                card_bg = "#f0fdf4" if palette["ctk_mode"] == "Light" else "#0f231c"
            elif is_lunch:
                card_border = "#ea580c"
                card_bg = "#fff7ed" if palette["ctk_mode"] == "Light" else "#27170a"
            else:
                card_border = palette["card_border"]
                card_bg = palette["card_bg"]

            c_frame = ctk.CTkFrame(
                self.scroll, 
                corner_radius=8, 
                fg_color=card_bg, 
                border_width=2 if is_current else 1, 
                border_color=card_border
            )
            c_frame.pack(fill="x", pady=2)

            badge_bg = "#15803d" if is_current else ("#ea580c" if is_lunch else colors[idx % len(colors)])
            badge_text = f"▶ {it['name']}" if is_current else it["name"]

            badge = ctk.CTkLabel(
                c_frame,
                text=badge_text,
                font=get_font(9, "bold"),
                fg_color=badge_bg,
                text_color="#ffffff",
                corner_radius=4,
                width=50,
                height=22
            )
            badge.pack(side="left", padx=(6, 6), pady=3)

            time_lbl = ctk.CTkLabel(
                c_frame,
                text=f"{it['start']}~{it['end']}",
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                text_color=palette["accent_blue"] if not is_lunch else "#ea580c"
            )
            time_lbl.pack(side="left", padx=(0, 6))

            subj_lbl = ctk.CTkLabel(
                c_frame,
                text=it["subject"],
                font=get_font(11, "bold"),
                text_color=palette["text_main"] if not is_lunch else "#c2410c",
                anchor="w"
            )
            subj_lbl.pack(side="left", fill="x", expand=True, pady=3)

            tag = it.get("tag", "담임")
            if tag in ["전담", "외강"]:
                tag_bg = "#5e5ce6" if tag == "전담" else "#0284c7"
                ctk.CTkLabel(c_frame, text=f"[{tag}]", font=get_font(9, "bold"), fg_color=tag_bg, text_color="#ffffff", corner_radius=3, width=32, height=18).pack(side="right", padx=4)

    def _render_meal_view(self):
        palette = theme_manager.get_theme()
        today = datetime.date.today()
        cfg = neis_client.config
        school_nm = cfg.get("school_name", "")

        if not school_nm:
            c = ctk.CTkFrame(self.scroll, fg_color=palette["sidebar_bg"], corner_radius=8)
            c.pack(fill="x", pady=10)
            ctk.CTkLabel(
                c,
                text="🏫 학교 설정이 필요합니다.\n[놀티쳐 데스크] 메인 창에서\n학교를 검색하여 선택해주세요.",
                font=get_font(11),
                text_color=palette["text_sub"],
                justify="center"
            ).pack(pady=16)
            return

        ok, meal_info, msg = neis_client.get_meal_for_date(today)
        if not ok or not meal_info.get("dishes"):
            c = ctk.CTkFrame(self.scroll, fg_color="#27170a", corner_radius=8, border_width=1, border_color="#ea580c")
            c.pack(fill="x", pady=10)
            ctk.CTkLabel(
                c,
                text=f"🍱 오늘 등록된 급식이 없습니다.\n({school_nm})\n방학 또는 공휴일일 수 있습니다.",
                font=get_font(11, "bold"),
                text_color="#fdba74",
                justify="center"
            ).pack(pady=16)
            return

        # 요약 헤더
        cal_str = meal_info.get("calorie", "")
        hdr_box = ctk.CTkFrame(self.scroll, fg_color=palette["sidebar_bg"], corner_radius=8, border_width=1, border_color=palette["card_border"])
        hdr_box.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            hdr_box,
            text=f"🍽️ 중식 ({school_nm})",
            font=get_font(11, "bold"),
            text_color=palette["text_main"]
        ).pack(side="left", padx=8, pady=4)

        if cal_str:
            ctk.CTkLabel(
                hdr_box,
                text=f"🔥 {cal_str}",
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                text_color="#15803d"
            ).pack(side="right", padx=8, pady=4)

        # 메뉴 리스트
        for d in meal_info.get("dishes", []):
            d_card = ctk.CTkFrame(self.scroll, fg_color=palette["card_bg"], corner_radius=6, border_width=1, border_color=palette["card_border"])
            d_card.pack(fill="x", pady=2)
            ctk.CTkLabel(
                d_card,
                text=f"• {d}",
                font=get_font(11, "bold"),
                text_color=palette["text_main"],
                anchor="w"
            ).pack(fill="x", padx=6, pady=4)

        # 알레르기 안내
        ctk.CTkLabel(
            self.scroll,
            text="* 번호는 알레르기 유발물질 표시입니다.",
            font=get_font(9),
            text_color=palette["text_sub"]
        ).pack(anchor="w", pady=(4, 0))
