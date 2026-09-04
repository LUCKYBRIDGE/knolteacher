import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from src.font_config import get_font
from src.theme_manager import theme_manager
from src.scheduler_manager import SchedulerManager

class ScheduleManagerDialog(ctk.CTkToplevel):
    def __init__(self, parent, manager: SchedulerManager, on_updated_callback=None):
        super().__init__(parent)
        self.manager = manager
        self.on_updated_callback = on_updated_callback
        self.title("통합 예약 & 알람 관리 센터 - 놀티쳐")
        self.geometry("640x580")
        self.minsize(560, 480)
        self.attributes("-topmost", True)

        self._build_ui()
        self.focus_force()

    def _build_ui(self):
        palette = theme_manager.get_theme()

        top_bar = ctk.CTkFrame(self, fg_color=palette["accent"], corner_radius=0, height=54)
        top_bar.pack(fill="x", side="top")
        top_bar.pack_propagate(False)

        ctk.CTkLabel(
            top_bar,
            text="📅 통합 예약 & 알람 관리 센터",
            font=get_font(13, "bold"),
            text_color="#ffffff"
        ).pack(side="left", padx=16, pady=10)

        ctk.CTkButton(
            top_bar,
            text="🛑 전체 예약 일괄 취소",
            font=get_font(10, "bold"),
            fg_color="#ef4444",
            hover_color="#dc2626",
            text_color="#ffffff",
            height=28,
            corner_radius=6,
            command=self._cancel_all_schedules
        ).pack(side="right", padx=16)

        notice_box = ctk.CTkFrame(self, fg_color=palette["card_inner_bg"], corner_radius=0, height=36, border_width=0)
        notice_box.pack(fill="x", side="top")
        notice_box.pack_propagate(False)

        ctk.CTkLabel(
            notice_box,
            text="💡 컴퓨터 전원 예약은 시스템 안정성을 위해 최대 2개월(60일)까지만 지원됩니다.",
            font=get_font(9, "bold"),
            text_color=palette["accent"]
        ).pack(side="left", padx=16, pady=6)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=16, pady=12)

        self._render_schedule_cards()

        btm_bar = ctk.CTkFrame(self, fg_color=palette["card_inner_bg"], height=48, corner_radius=0, border_width=1, border_color=palette["card_border"])
        btm_bar.pack(fill="x", side="bottom")
        btm_bar.pack_propagate(False)

        ctk.CTkButton(
            btm_bar,
            text="확인 및 닫기",
            font=get_font(11, "bold"),
            fg_color=palette["accent"],
            hover_color=palette["accent_hover"],
            text_color="#ffffff",
            width=110,
            height=30,
            corner_radius=6,
            command=self.destroy
        ).pack(side="right", padx=14)

    def _render_schedule_cards(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        palette = theme_manager.get_theme()
        items = self.manager.get_active_schedules()

        if not items:
            empty_card = ctk.CTkFrame(self.scroll, fg_color=palette["card_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
            empty_card.pack(fill="x", pady=30, padx=20)
            ctk.CTkLabel(
                empty_card,
                text="현재 대기 중인 예약이나 알람이 없습니다.\n상단 또는 PC 설정 탭에서 새로운 예약을 등록해보세요.",
                font=get_font(11),
                text_color=palette["text_sub"],
                justify="center"
            ).pack(pady=24)
            return

        for itm in items:
            card = ctk.CTkFrame(self.scroll, fg_color=palette["card_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
            card.pack(fill="x", pady=(0, 10))

            top_r = ctk.CTkFrame(card, fg_color="transparent")
            top_r.pack(fill="x", padx=14, pady=(10, 4))

            ctk.CTkLabel(
                top_r,
                text=f"⏰ {itm['type_name']}",
                font=get_font(12, "bold"),
                text_color=palette["text_main"]
            ).pack(side="left")

            rep_text = itm.get("repeat_type", "오늘 1회성")
            badge_bg = "#0284c7" if "1회" in rep_text else "#d97706"
            rep_badge = ctk.CTkLabel(
                top_r,
                text=f"  {rep_text}  ",
                font=get_font(9, "bold"),
                fg_color=badge_bg,
                text_color="#ffffff",
                corner_radius=6
            )
            rep_badge.pack(side="left", padx=(8, 0))

            ctk.CTkButton(
                top_r,
                text="🗑️ 취소",
                font=get_font(10, "bold"),
                fg_color="#ef4444",
                hover_color="#dc2626",
                text_color="#ffffff",
                width=64,
                height=26,
                corner_radius=6,
                command=lambda i_id=itm["id"]: self._cancel_single_item(i_id)
            ).pack(side="right")

            info_r = ctk.CTkFrame(card, fg_color="transparent")
            info_r.pack(fill="x", padx=14, pady=(2, 10))

            time_text = f"목표 일시: {itm['target_time_str']}"
            if itm.get("remaining_sec", -1) > 0:
                rem_m = itm["remaining_sec"] // 60
                rem_s = itm["remaining_sec"] % 60
                time_text += f" (남은 시간: 약 {rem_m}분 {rem_s}초)"

            ctk.CTkLabel(
                info_r,
                text=time_text,
                font=get_font(10),
                text_color=palette["accent"]
            ).pack(anchor="w")

            if itm.get("memo"):
                ctk.CTkLabel(
                    info_r,
                    text=f"상세 메모: {itm['memo']}",
                    font=get_font(9),
                    text_color=palette["text_sub"]
                ).pack(anchor="w", pady=(2, 0))

    def _cancel_single_item(self, item_id: str):
        ok, msg = self.manager.cancel_item_by_id(item_id)
        if ok:
            messagebox.showinfo("예약 취소", msg)
            self._render_schedule_cards()
            if self.on_updated_callback:
                self.on_updated_callback()
        else:
            messagebox.showwarning("알림", msg)

    def _cancel_all_schedules(self):
        if not messagebox.askyesno("전체 예약 취소", "현재 등록된 모든 예약 및 주간 자동 전원 설정을 취소하시겠습니까?"):
            return
        self.manager.cancel_schedule(notify=True)
        self.manager.auto_power_config["auto_shutdown_enabled"] = False
        self.manager.auto_power_config["auto_wake_enabled"] = False
        self.manager.save_auto_power_config({"auto_shutdown_enabled": False, "auto_wake_enabled": False})
        messagebox.showinfo("취소 완료", "모든 예약 및 자동 전원 일정이 취소되었습니다.")
        self._render_schedule_cards()
        if self.on_updated_callback:
            self.on_updated_callback()

def open_schedule_dialog(parent, manager: SchedulerManager, on_updated_callback=None):
    return ScheduleManagerDialog(parent, manager, on_updated_callback)
