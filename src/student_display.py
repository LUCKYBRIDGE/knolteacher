import os
import sys
import datetime
import customtkinter as ctk
from src.font_config import setup_global_fonts, get_font
from src.timetable_manager import timetable_manager, DAYS_KO

class StudentDisplayWindow(ctk.CTkToplevel):
    """
    듀얼 모니터(학생용 화면2, 교실 TV/전자칠판) 전용 대형 시간표 및 교실 안내 스크린
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("학생용 교실 화면 (오늘 시간표 & 알림판)")
        self.geometry("900x650")
        self.minsize(600, 420)
        self.resizable(True, True)

        setup_global_fonts(self)
        self._load_icon()

        self.is_fullscreen = False
        self.is_pinned = False
        self.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._exit_fullscreen())

        self._build_ui()
        self._update_clock_and_highlight()

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

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)

    def _exit_fullscreen(self):
        self.is_fullscreen = False
        self.attributes("-fullscreen", False)

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="#0f172a")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        # 1. 상단 대형 시계 및 날짜 바
        header = ctk.CTkFrame(container, fg_color="#1e293b", corner_radius=14)
        header.pack(fill="x", pady=(0, 14))

        h_inner = ctk.CTkFrame(header, fg_color="transparent")
        h_inner.pack(fill="x", padx=20, pady=14)

        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]

        self.date_lbl = ctk.CTkLabel(
            h_inner,
            text=f"📅 {today.strftime('%Y년 %m월 %d일')} ({weekday_str}요일)",
            font=get_font(18, "bold"),
            text_color="#38bdf8"
        )
        self.date_lbl.pack(side="left")

        btn_box = ctk.CTkFrame(h_inner, fg_color="transparent")
        btn_box.pack(side="right")

        self.clock_lbl = ctk.CTkLabel(
            btn_box,
            text="00:00:00",
            font=ctk.CTkFont(family="Consolas", size=24, weight="bold"),
            text_color="#4ade80"
        )
        self.clock_lbl.pack(side="left", padx=(0, 16))

        self.pin_btn = ctk.CTkButton(
            btn_box,
            text="📍",
            width=30,
            height=30,
            font=get_font(11),
            fg_color="#334155",
            hover_color="#475569",
            corner_radius=6,
            command=self._toggle_pin
        )
        self.pin_btn.pack(side="left", padx=2)

        ctk.CTkButton(
            btn_box,
            text="—",
            width=30,
            height=30,
            font=get_font(12, "bold"),
            fg_color="#334155",
            hover_color="#475569",
            corner_radius=6,
            command=self.iconify
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_box,
            text="🗖",
            width=30,
            height=30,
            font=get_font(12, "bold"),
            fg_color="#334155",
            hover_color="#475569",
            corner_radius=6,
            command=self._toggle_fullscreen
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_box,
            text="✕",
            width=30,
            height=30,
            font=get_font(12, "bold"),
            fg_color="#3f1d24",
            hover_color="#dc2626",
            text_color="#fca5a5",
            corner_radius=6,
            command=self.destroy
        ).pack(side="left", padx=2)

        # 2. 메인 컨텐츠 영역 (좌측: 오늘 시간표, 우측: 교실 알림장/메모)
        content_frame = ctk.CTkFrame(container, fg_color="transparent")
        content_frame.pack(fill="both", expand=True)

        # 좌측: 시간표 대형 카드 목록
        left_box = ctk.CTkFrame(content_frame, fg_color="#1e2230", corner_radius=12, border_width=1, border_color="#334155")
        left_box.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ctk.CTkLabel(
            left_box,
            text="📋 오늘의 수업 시간표",
            font=get_font(16, "bold"),
            text_color="#60a5fa"
        ).pack(anchor="w", padx=16, pady=(12, 8))

        self.tt_scroll = ctk.CTkScrollableFrame(left_box, fg_color="transparent")
        self.tt_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 우측: 오늘의 급식 식단표 & 교실 알림장
        right_box = ctk.CTkFrame(content_frame, fg_color="#1e2230", corner_radius=12, border_width=1, border_color="#334155", width=340)
        right_box.pack(side="right", fill="both", padx=(8, 0))
        right_box.pack_propagate(False)

        # 급식 카드
        meal_card = ctk.CTkFrame(right_box, fg_color="#221e10", corner_radius=10, border_width=1, border_color="#d97706")
        meal_card.pack(fill="x", padx=10, pady=(10, 8))

        m_hdr = ctk.CTkFrame(meal_card, fg_color="transparent")
        m_hdr.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(m_hdr, text="🍱 오늘의 점심 급식", font=get_font(14, "bold"), text_color="#fcd34d").pack(side="left")

        try:
            from src.neis_client import neis_client
            ok, meal_info, _ = neis_client.get_meal_for_date(today)
            if ok and meal_info.get("calorie"):
                ctk.CTkLabel(m_hdr, text=f"🔥 {meal_info['calorie']}", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color="#4ade80").pack(side="right")
            
            dishes = meal_info.get("dishes", []) if ok else []
            menu_text = " • " + "\n • ".join(dishes[:5]) if dishes else "오늘 등록된 급식 식단이 없습니다."
        except Exception:
            menu_text = "급식 정보 불러오기 대기 중"

        self.meal_lbl = ctk.CTkLabel(
            meal_card,
            text=menu_text,
            font=get_font(12, "bold"),
            text_color="#f8fafc",
            justify="left",
            anchor="w"
        )
        self.meal_lbl.pack(fill="x", padx=10, pady=(0, 8))

        # 교실 알림판
        ctk.CTkLabel(
            right_box,
            text="📌 오늘의 교실 알림판",
            font=get_font(14, "bold"),
            text_color="#f59e0b"
        ).pack(anchor="w", padx=14, pady=(4, 6))

        self.notice_box = ctk.CTkTextbox(
            right_box,
            font=get_font(12),
            fg_color="#0f172a",
            text_color="#f1f5f9",
            corner_radius=8
        )
        self.notice_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.notice_box.insert("1.0", "1. 수업 시작 3분 전 자리에 앉기\n2. 쉬는 시간 복도에서 뛰지 않기\n3. 준비물 및 숙제 챙기기\n\n[오늘의 명언]\n\"배움에는 끝이 없다.\"")

        # 하단 힌트
        ctk.CTkLabel(
            container,
            text="* [F11]을 누르면 전체화면으로 전환됩니다. ESC로 돌아오기.",
            font=get_font(11),
            text_color="#64748b"
        ).pack(anchor="w", pady=(8, 0))

    def _update_clock_and_highlight(self):
        now = datetime.datetime.now()
        self.clock_lbl.configure(text=now.strftime("%H:%M:%S"))

        # 시간표 갱신
        for w in self.tt_scroll.winfo_children():
            w.destroy()

        is_hol, hol_name, items = timetable_manager.get_today_schedule_items()
        now_str = now.strftime("%H:%M")

        if is_hol:
            c = ctk.CTkFrame(self.tt_scroll, fg_color="#3b1d11", corner_radius=10, height=80)
            c.pack(fill="x", pady=10)
            ctk.CTkLabel(c, text=f"🇰🇷 오늘은 [{hol_name}] 공휴일입니다.", font=get_font(16, "bold"), text_color="#fdba74").pack(expand=True)
        else:
            colors = ["#1e3a8a", "#065f46", "#831843", "#701a75", "#78350f", "#1e293b", "#312e81"]
            for idx, it in enumerate(items):
                name = it["name"]
                start_str = it["start"]
                end_str = it["end"]
                subj = it["subject"]
                tag = it.get("tag", "담임")
                is_lunch = it["is_lunch"]

                is_current = (start_str <= now_str <= end_str)

                if is_current:
                    card_bg = "#064e3b"
                    border_c = "#10b981"
                elif is_lunch:
                    card_bg = "#3b1d11"
                    border_c = "#ea580c"
                else:
                    card_bg = "#181d28"
                    border_c = "#334155"

                row_card = ctk.CTkFrame(self.tt_scroll, fg_color=card_bg, corner_radius=8, border_width=2 if is_current else 1, border_color=border_c)
                row_card.pack(fill="x", pady=4)

                badge_bg = "#ea580c" if is_lunch else colors[idx % len(colors)]
                badge = ctk.CTkLabel(row_card, text=name, font=get_font(12, "bold"), fg_color=badge_bg, text_color="#ffffff", corner_radius=6, width=64, height=28)
                badge.pack(side="left", padx=10, pady=8)

                time_lbl = ctk.CTkLabel(row_card, text=f"{start_str} ~ {end_str}", font=get_font(12), text_color="#94a3b8", width=95)
                time_lbl.pack(side="left")

                subj_lbl = ctk.CTkLabel(row_card, text=subj, font=get_font(14, "bold"), text_color="#ffffff" if not is_current else "#6ee7b7", anchor="w")
                subj_lbl.pack(side="left", fill="x", expand=True, padx=8)

                if tag in ["전담", "외강"]:
                    tag_bg = "#7c3aed" if tag == "전담" else "#0891b2"
                    tag_lbl = ctk.CTkLabel(row_card, text=f"[{tag}]", font=get_font(11, "bold"), fg_color=tag_bg, text_color="#ffffff", corner_radius=4, width=44, height=22)
                    tag_lbl.pack(side="right", padx=10)

        # 1초마다 시계 갱신
        self.after(1000, self._update_clock_and_highlight)
