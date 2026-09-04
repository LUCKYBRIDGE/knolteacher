"""
정기 반복 알람 & 예약 관리 센터 (RecurringScheduleDialog)
- 매일 반복, 평일(월~금) 반복, 지정 요일 반복 스케줄 추가/수정/삭제/On-Off
"""
import os
import datetime
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from src.font_config import get_font
from src.theme_manager import theme_manager
from src.repeat_schedule_manager import recurring_manager, DAYS_NAME
from src.icon_renderer import get_icon


class RecurringScheduleDialog(ctk.CTkToplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.title("정기 반복 알람 & 예약 센터")
        self.geometry("680x700")
        self.minsize(620, 580)
        self.attributes("-topmost", True)

        self._day_vars = {}
        self._build_ui()

    def _build_ui(self):
        palette = theme_manager.get_theme()
        self.configure(fg_color=palette["card_bg"])

        container = ctk.CTkFrame(self, fg_color=palette["card_bg"], corner_radius=12)
        container.pack(fill="both", expand=True, padx=12, pady=12)

        # 1. 상단 타이틀
        hdr = ctk.CTkFrame(container, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(6, 8))

        ctk.CTkLabel(
            hdr, text="🔄 정기 반복 알람 & 전원 자동화 센터",
            font=get_font(15, "bold"), text_color=palette["accent"]
        ).pack(side="left")

        # 안내 배너
        banner = ctk.CTkFrame(container, fg_color=palette["card_inner_bg"], corner_radius=8, border_width=1, border_color=palette["card_border"])
        banner.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(
            banner,
            text="💡 [정기 반복 자동화 안내]\n• 매일 또는 특정 요일마다 지정된 시각에 알람이나 컴퓨터 전원 제어가 자동으로 실행됩니다.\n• 학교 공휴일(국경일/재량휴업일 등)에는 자동으로 동작을 건너뛰어 안심하고 사용하실 수 있습니다.",
            font=get_font(10), text_color=palette["text_main"], justify="left"
        ).pack(padx=12, pady=8, anchor="w")

        # 2. 메인 스크롤 (새 규칙 추가 카드 + 현재 등록된 목록)
        scroll = ctk.CTkScrollableFrame(container, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self._build_add_card(scroll, palette)
        self._build_list_card(scroll, palette)

        # 3. 하단 닫기 바
        b_bar = ctk.CTkFrame(container, fg_color="transparent")
        b_bar.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkButton(
            b_bar, text="닫기", font=get_font(11, "bold"), width=80, height=32,
            fg_color=palette["card_inner_bg"], hover_color=palette["sidebar_btn_hover"],
            text_color=palette["text_main"], command=self.destroy
        ).pack(side="right")

    # =========================================================================
    # 1. 새 반복 규칙 추가 카드
    # =========================================================================
    def _build_add_card(self, parent, palette):
        card = ctk.CTkFrame(parent, fg_color=palette["card_inner_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
        card.pack(fill="x", pady=(0, 10))

        c_hdr = ctk.CTkFrame(card, fg_color="transparent")
        c_hdr.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(c_hdr, text="➕ 새 정기 반복 규칙 만들기", font=get_font(12, "bold"), text_color=palette["accent"]).pack(side="left")

        # 1) 제목 입력
        r1 = ctk.CTkFrame(card, fg_color="transparent")
        r1.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(r1, text="규칙 제목:", width=70, font=get_font(10, "bold"), text_color=palette["text_main"], anchor="w").pack(side="left")
        self.title_entry = ctk.CTkEntry(r1, placeholder_text="예: 퇴근 시간 자동 종료, 우유 급식 알람", font=get_font(10), height=28)
        self.title_entry.pack(side="left", fill="x", expand=True)

        # 2) 동작 선택
        r2 = ctk.CTkFrame(card, fg_color="transparent")
        r2.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(r2, text="동작 구분:", width=70, font=get_font(10, "bold"), text_color=palette["text_main"], anchor="w").pack(side="left")
        self.act_seg = ctk.CTkSegmentedButton(
            r2, values=["🔔 수업/일과 알람", "💻 PC 자동 종료", "🌙 절전 모드", "🔄 다시시작"],
            font=get_font(10, "bold"), height=28
        )
        self.act_seg.set("🔔 수업/일과 알람")
        self.act_seg.pack(side="left", fill="x", expand=True)

        # 3) 시각 선택 (오전/오후 + 시 + 분)
        r3 = ctk.CTkFrame(card, fg_color="transparent")
        r3.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(r3, text="실행 시각:", width=70, font=get_font(10, "bold"), text_color=palette["text_main"], anchor="w").pack(side="left")

        self.ampm_seg = ctk.CTkSegmentedButton(r3, values=["오전", "오후"], font=get_font(10, "bold"), width=76, height=26)
        self.ampm_seg.set("오후")
        self.ampm_seg.pack(side="left", padx=(0, 4))

        self.hour_combo = ctk.CTkComboBox(r3, values=[f"{h}시" for h in range(1, 13)], width=64, height=26, font=get_font(10, "bold"), state="readonly")
        self.hour_combo.set("4시")
        self.hour_combo.pack(side="left", padx=2)

        self.min_combo = ctk.CTkComboBox(r3, values=[f"{m:02d}분" for m in range(0, 60, 5)], width=68, height=26, font=get_font(10, "bold"), state="readonly")
        self.min_combo.set("40분")
        self.min_combo.pack(side="left", padx=2)

        # 4) 반복 주기 (평일 / 매일 / 요일 선택)
        r4 = ctk.CTkFrame(card, fg_color="transparent")
        r4.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(r4, text="반복 요일:", width=70, font=get_font(10, "bold"), text_color=palette["text_main"], anchor="w").pack(side="left")

        self.cycle_seg = ctk.CTkSegmentedButton(
            r4, values=["🏢 평일 (월~금)", "📅 매일 (월~일)", "✏️ 요일 직접 선택"],
            font=get_font(10, "bold"), height=26, command=self._on_cycle_changed
        )
        self.cycle_seg.set("🏢 평일 (월~금)")
        self.cycle_seg.pack(side="left", fill="x", expand=True)

        # 요일 직접 선택 체크박스 바 (기본 숨김)
        self.days_box = ctk.CTkFrame(card, fg_color="transparent")
        self._day_vars.clear()
        for idx, d_name in enumerate(DAYS_NAME):
            var = ctk.BooleanVar(value=(idx < 5))
            self._day_vars[idx] = var
            chk = ctk.CTkCheckBox(self.days_box, text=d_name, variable=var, width=44, font=get_font(9, "bold"), checkbox_width=16, checkbox_height=16)
            chk.pack(side="left", padx=2)

        # 5) 공휴일 제외 옵션 및 등록 버튼
        r5 = ctk.CTkFrame(card, fg_color="transparent")
        r5.pack(fill="x", padx=14, pady=(6, 12))

        self.skip_hol_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            r5, text="🇰🇷 공휴일/재량휴업일은 자동으로 건너뛰기", variable=self.skip_hol_var,
            font=get_font(9, "bold"), checkbox_width=16, checkbox_height=16
        ).pack(side="left")

        ctk.CTkButton(
            r5, text="➕ 반복 규칙 등록", font=get_font(11, "bold"), height=30, width=120,
            fg_color=palette["accent"], hover_color=palette["accent_hover"],
            command=self._add_recurring_rule
        ).pack(side="right")

    def _on_cycle_changed(self, val):
        if "요일 직접 선택" in val:
            self.days_box.pack(fill="x", padx=84, pady=(2, 6))
        else:
            self.days_box.pack_forget()

    def _add_recurring_rule(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("입력 안내", "규칙 제목을 입력해주세요.")
            return

        act_raw = self.act_seg.get()
        act_type = "alarm"
        if "종료" in act_raw: act_type = "shutdown"
        elif "절전" in act_raw: act_type = "sleep"
        elif "다시시작" in act_raw: act_type = "restart"

        ampm = self.ampm_seg.get()
        h_str = self.hour_combo.get().replace("시", "")
        m_str = self.min_combo.get().replace("분", "")
        h = int(h_str)
        m = int(m_str)
        if ampm == "오후" and h < 12: h += 12
        elif ampm == "오전" and h == 12: h = 0
        time_str = f"{h:02d}:{m:02d}"

        cycle_raw = self.cycle_seg.get()
        if "평일" in cycle_raw:
            rep_mode = "weekdays"
            rep_days = [0, 1, 2, 3, 4]
        elif "매일" in cycle_raw:
            rep_mode = "daily"
            rep_days = [0, 1, 2, 3, 4, 5, 6]
        else:
            rep_mode = "custom"
            rep_days = [k for k, v in self._day_vars.items() if v.get()]
            if not rep_days:
                messagebox.showwarning("입력 안내", "최소 1개 이상의 요일을 선택해주세요.")
                return

        new_item = {
            "title": title,
            "action_type": act_type,
            "time_str": time_str,
            "ampm": ampm,
            "hour12": int(h_str),
            "minute": m,
            "repeat_mode": rep_mode,
            "repeat_days": rep_days,
            "skip_holidays": self.skip_hol_var.get(),
            "enabled": True,
            "memo": f"{title} ({ampm} {h_str}시 {m_str}분)"
        }

        recurring_manager.add_schedule(new_item)
        self.title_entry.delete(0, "end")
        self._refresh_list()
        messagebox.showinfo("등록 완료", f"[{title}] 정기 반복 규칙이 성공적으로 등록되었습니다!")

    # =========================================================================
    # 2. 현재 등록된 반복 규칙 리스트 카드
    # =========================================================================
    def _build_list_card(self, parent, palette):
        self.list_card = ctk.CTkFrame(parent, fg_color=palette["card_inner_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
        self.list_card.pack(fill="both", expand=True)

        self._refresh_list()

    def _refresh_list(self):
        for w in self.list_card.winfo_children():
            w.destroy()

        palette = theme_manager.get_theme()
        hdr = ctk.CTkFrame(self.list_card, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(10, 6))

        schedules = recurring_manager.schedules
        active_cnt = len([s for s in schedules if s.get("enabled", True)])
        ctk.CTkLabel(
            hdr, text=f"📋 등록된 정기 반복 규칙 ({len(schedules)}개 중 {active_cnt}개 활성화)",
            font=get_font(12, "bold"), text_color=palette["text_main"]
        ).pack(side="left")

        if not schedules:
            ctk.CTkLabel(
                self.list_card, text="등록된 정기 반복 규칙이 없습니다.\n위의 양식을 통해 매일 반복 또는 평일 반복 규칙을 등록해보세요.",
                font=get_font(10), text_color=palette["text_sub"], justify="center"
            ).pack(pady=24)
            return

        for itm in schedules:
            self._render_schedule_item(itm, palette)

    def _render_schedule_item(self, itm: dict, palette):
        sid = itm["id"]
        is_en = itm.get("enabled", True)

        row = ctk.CTkFrame(self.list_card, fg_color=palette["card_bg"], corner_radius=8, border_width=1, border_color=palette["card_border"])
        row.pack(fill="x", padx=12, pady=4)

        # 좌측 뱃지 (주기)
        rep_mode = itm.get("repeat_mode", "weekdays")
        if rep_mode == "weekdays":
            badge_txt = "🏢 평일"
            badge_col = "#0284c7"
        elif rep_mode == "daily":
            badge_txt = "📅 매일"
            badge_col = "#16a34a"
        else:
            d_str = ",".join([DAYS_NAME[d] for d in itm.get("repeat_days", [])])
            badge_txt = f"✏️ {d_str}"
            badge_col = "#d97706"

        badge = ctk.CTkLabel(
            row, text=f" {badge_txt} ", font=get_font(9, "bold"),
            fg_color=badge_col, text_color="#ffffff", corner_radius=4
        )
        badge.pack(side="left", padx=(10, 6), pady=8)

        # 시각 표시
        t_str = itm.get("time_str", "16:40")
        ampm = itm.get("ampm", "오후")
        h12 = itm.get("hour12", 4)
        m = itm.get("minute", 40)
        time_display = f"{ampm} {h12:02d}:{m:02d}"

        t_lbl = ctk.CTkLabel(
            row, text=time_display, font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=palette["accent"] if is_en else palette["text_sub"]
        )
        t_lbl.pack(side="left", padx=4)

        # 제목 및 동작 아이콘
        act = itm.get("action_type", "alarm")
        act_icon = "🔔" if act == "alarm" else ("💻" if act == "shutdown" else ("🌙" if act == "sleep" else "🔄"))
        title_txt = f"{act_icon} {itm.get('title', '')}"

        ctk.CTkLabel(
            row, text=title_txt, font=get_font(10, "bold"),
            text_color=palette["text_main"] if is_en else palette["text_sub"], anchor="w"
        ).pack(side="left", fill="x", expand=True, padx=8)

        # 우측 스위치 & 삭제 버튼
        sw_var = ctk.BooleanVar(value=is_en)
        sw = ctk.CTkSwitch(
            row, text="켜짐" if is_en else "꺼짐", variable=sw_var,
            font=get_font(9, "bold"), text_color=palette["text_sub"],
            command=lambda i=sid: self._toggle_item(i)
        )
        sw.pack(side="left", padx=6)

        ctk.CTkButton(
            row, text="✕", width=22, height=22, font=get_font(9, "bold"),
            fg_color="transparent", hover_color="#ef4444", text_color=palette["text_sub"],
            command=lambda i=sid: self._delete_item(i)
        ).pack(side="right", padx=(2, 8))

    def _toggle_item(self, item_id: str):
        recurring_manager.toggle_enable(item_id)
        self._refresh_list()

    def _delete_item(self, item_id: str):
        if messagebox.askyesno("삭제 확인", "이 정기 반복 규칙을 삭제하시겠습니까?"):
            recurring_manager.delete_schedule(item_id)
            self._refresh_list()
