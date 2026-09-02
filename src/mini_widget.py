import os
import sys
import datetime
import customtkinter as ctk
from src.font_config import setup_global_fonts, get_font
from src.timetable_manager import timetable_manager, DAYS_KO
from src.neis_client import neis_client

class MiniTimetableWidget(ctk.CTkToplevel):
    """
    바탕화면에 상시 띄워두고 오늘 시간표 및 오늘 급식을 바로 확인할 수 있는 플로팅 미니 위젯
    (상단 탭 전환, 자유 리사이즈, 상단 고정 핀 완비)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("미니 시간표 & 급식")
        self.geometry("310x460")
        self.minsize(250, 320)
        self.resizable(True, True)
        self.attributes("-topmost", True)
        self.is_pinned = True
        self.current_tab = "timetable"  # timetable | meal

        setup_global_fonts(self)
        self._load_icon()

        # 화면 우측 상단에 기본 배치
        sw = self.winfo_screenwidth()
        x = max(10, sw - 340)
        y = 60
        self.geometry(f"310x460+{x}+{y}")

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
            fg_color="#2563eb" if self.is_pinned else "#334155"
        )

    def _build_ui(self):
        self.container = ctk.CTkFrame(self, fg_color="#0b0f19", corner_radius=14, border_width=1, border_color="#0a84ff")
        self.container.pack(fill="both", expand=True, padx=6, pady=6)

        # 1. 상단 헤더 (서브 탭 세그먼트 & 창 제어 버튼)
        header = ctk.CTkFrame(self.container, fg_color="#161e31", corner_radius=10)
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
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            corner_radius=6,
            command=self._toggle_pin
        )
        self.pin_btn.pack(side="left", padx=1)

        refresh_btn = ctk.CTkButton(
            btn_box,
            text="🔄",
            width=24,
            height=24,
            font=get_font(10),
            fg_color="#1e293b",
            hover_color="#334155",
            corner_radius=6,
            command=self._refresh_content
        )
        refresh_btn.pack(side="left", padx=1)

        min_btn = ctk.CTkButton(
            btn_box,
            text="—",
            width=24,
            height=24,
            font=get_font(10, "bold"),
            fg_color="#1e293b",
            hover_color="#334155",
            corner_radius=6,
            command=self.iconify
        )
        min_btn.pack(side="left", padx=1)

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

        # 2. 메인 스크롤 프레임
        self.scroll = ctk.CTkScrollableFrame(self.container, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=4, pady=2)

    def _on_tab_changed(self, choice: str):
        if "시간표" in choice:
            self.current_tab = "timetable"
        else:
            self.current_tab = "meal"
        self._refresh_content()

    def _refresh_content(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        if self.current_tab == "timetable":
            self._render_timetable_view()
        else:
            self._render_meal_view()

    def _render_timetable_view(self):
        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]
        is_hol, hol_name, items = timetable_manager.get_today_schedule_items()
        now_time_str = datetime.datetime.now().strftime("%H:%M")

        # 날짜 안내 라벨
        date_lbl = ctk.CTkLabel(
            self.scroll,
            text=f"📅 {today.strftime('%m/%d')} ({weekday_str}요일)",
            font=get_font(12, "bold"),
            text_color="#38bdf8"
        )
        date_lbl.pack(anchor="w", padx=6, pady=(2, 6))

        if is_hol:
            c = ctk.CTkFrame(self.scroll, fg_color="#3b1d11", corner_radius=8, border_width=1, border_color="#f97316")
            c.pack(fill="x", pady=10)
            ctk.CTkLabel(c, text=f"🇰🇷 [{hol_name}]\n수업 없음 (공휴일)", font=get_font(12, "bold"), text_color="#fdba74").pack(pady=16)
            return

        for item in items:
            name = item["name"]
            subject = item["subject"]
            tag = item.get("tag", "담임")
            start_str = item["start"]
            end_str = item["end"]
            is_lunch = item["is_lunch"]

            is_current = (start_str <= now_time_str <= end_str)

            if is_current:
                card_bg = "#0f231c"
                border_col = "#30d158"
                border_w = 2
            elif is_lunch:
                card_bg = "#27170a"
                border_col = "#ea580c"
                border_w = 1
            else:
                card_bg = "#161d2f"
                border_col = "#26334d"
                border_w = 1

            card = ctk.CTkFrame(self.scroll, fg_color=card_bg, corner_radius=8, border_width=border_w, border_color=border_col)
            card.pack(fill="x", pady=3)

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=8, pady=(4, 1))

            perio_text = f"▶ {name}" if is_current else name
            perio_lbl = ctk.CTkLabel(
                top_row,
                text=perio_text,
                font=get_font(11, "bold"),
                text_color="#30d158" if is_current else ("#fb923c" if is_lunch else "#38bdf8")
            )
            perio_lbl.pack(side="left")

            time_lbl = ctk.CTkLabel(
                top_row,
                text=f"{start_str} ~ {end_str}",
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                text_color="#94a3b8" if not is_current else "#6ee7b7"
            )
            time_lbl.pack(side="right")

            bot_row = ctk.CTkFrame(card, fg_color="transparent")
            bot_row.pack(fill="x", padx=8, pady=(0, 5))

            subj_lbl = ctk.CTkLabel(
                bot_row,
                text=subject,
                font=get_font(13, "bold"),
                text_color="#ffffff" if not is_lunch else "#fed7aa",
                anchor="w"
            )
            subj_lbl.pack(side="left", fill="x", expand=True)

            if tag in ["전담", "외강"]:
                tag_col = "#5e5ce6" if tag == "전담" else "#0284c7"
                ctk.CTkLabel(bot_row, text=f"[{tag}]", font=get_font(10, "bold"), fg_color=tag_col, text_color="#ffffff", corner_radius=4, width=38, height=18).pack(side="right")

    def _render_meal_view(self):
        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]
        ok, meal_info, _ = neis_client.get_meal_for_date(today)
        school_nm = neis_client.config.get("school_name", "")

        # 급식 헤더 카드
        cal_str = meal_info.get("calorie", "") if ok else ""
        hdr_box = ctk.CTkFrame(self.scroll, fg_color="#221e10", corner_radius=8, border_width=1, border_color="#d97706")
        hdr_box.pack(fill="x", pady=(0, 6))

        h_in = ctk.CTkFrame(hdr_box, fg_color="transparent")
        h_in.pack(fill="x", padx=10, pady=6)

        ctk.CTkLabel(
            h_in,
            text=f"🍱 오늘 중식 ({today.strftime('%m/%d')})",
            font=get_font(12, "bold"),
            text_color="#fcd34d"
        ).pack(side="left")

        if cal_str:
            ctk.CTkLabel(
                h_in,
                text=f"🔥 {cal_str}",
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                text_color="#4ade80"
            ).pack(side="right")

        if not ok or not meal_info.get("dishes"):
            c = ctk.CTkFrame(self.scroll, fg_color="#181d28", corner_radius=8)
            c.pack(fill="x", pady=10)
            ctk.CTkLabel(
                c,
                text=f"🍱 오늘 등록된 급식이 없습니다.\n({school_nm if school_nm else '학교 설정 필요'})",
                font=get_font(11),
                text_color="#94a3b8",
                justify="center"
            ).pack(pady=20)
            return

        for d in meal_info.get("dishes", []):
            d_card = ctk.CTkFrame(self.scroll, fg_color="#161d2f", corner_radius=6, border_width=1, border_color="#26334d")
            d_card.pack(fill="x", pady=2)
            ctk.CTkLabel(
                d_card,
                text=f"• {d}",
                font=get_font(12, "bold"),
                text_color="#f8fafc",
                anchor="w"
            ).pack(fill="x", padx=8, pady=5)

        ctk.CTkLabel(
            self.scroll,
            text="* 번호는 알레르기 유발물질 표시입니다.",
            font=get_font(10),
            text_color="#64748b"
        ).pack(anchor="w", pady=(6, 0))
