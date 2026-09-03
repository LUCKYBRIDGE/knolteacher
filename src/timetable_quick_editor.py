import datetime
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from typing import Optional

from src.font_config import get_font
from src.timetable_manager import timetable_manager, DAYS_KO, DAY_KEYS
from src.theme_manager import theme_manager
from src.tooltip import attach_tooltip

# 초등학교 대표 과목 퀵 프리셋
QUICK_SUBJECTS = [
    "국어", "수학", "사회", "과학", "영어", "음악",
    "미술", "체육", "도덕", "실과", "창체", "동아리", "자율", "안전"
]

class TimetableQuickEditorDialog(ctk.CTkToplevel):
    """
    놀티쳐 어디서든 (놀티쳐 보드, 바탕화면 위젯, 메인 창) 1초 만에
    시간표를 수정하고 전체 화면에 실시간 연동하는 스마트 편집기
    """
    def __init__(self, parent=None, initial_day_key: Optional[str] = None, focus_period: Optional[int] = None):
        super().__init__(parent)
        self.title("✏️ 시간표 빠른 수정 (실시간 전체 연동)")
        self.geometry("540x600")
        self.minsize(480, 500)
        self.attributes("-topmost", True)

        today_w = datetime.date.today().weekday()
        default_key = DAY_KEYS[today_w] if 0 <= today_w < len(DAY_KEYS) else "mon"
        self.current_day_key = initial_day_key or default_key
        self.focus_period = focus_period

        self._active_entry = None
        self.entries = []
        self.tag_btns = []

        self._build_ui()
        self.focus_force()

    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        palette = theme_manager.get_theme()

        top_frame = ctk.CTkFrame(self, fg_color=palette["accent"], corner_radius=0, height=54)
        top_frame.pack(fill="x", side="top")
        top_frame.pack_propagate(False)

        ctk.CTkLabel(
            top_frame, text="✏️ 시간표 빠른 수정",
            font=get_font(14, "bold"), text_color="#ffffff"
        ).pack(side="left", padx=16, pady=10)

        ctk.CTkLabel(
            top_frame, text="💡 수정 즉시 놀티쳐 보드와 위젯에 실시간 자동 반영됩니다",
            font=get_font(10), text_color="#fef3c7" if palette["ctk_mode"] == "Light" else "#bae6fd"
        ).pack(side="right", padx=16)

        day_bar = ctk.CTkFrame(self, fg_color="transparent", height=42)
        day_bar.pack(fill="x", padx=16, pady=(10, 4))

        day_labels = {"mon": "월요일", "tue": "화요일", "wed": "수요일", "thu": "목요일", "fri": "금요일"}
        self.day_seg = ctk.CTkSegmentedButton(
            day_bar,
            values=[day_labels[k] for k in DAY_KEYS],
            font=get_font(11, "bold"),
            height=32,
            selected_color=palette["accent"],
            selected_hover_color=palette["accent_hover"],
            command=self._on_day_changed
        )
        self.day_seg.set(day_labels.get(self.current_day_key, "월요일"))
        self.day_seg.pack(fill="x")

        palette_card = ctk.CTkFrame(self, fg_color="#f8fafc", corner_radius=8, border_width=1, border_color="#e2e8f0")
        palette_card.pack(fill="x", padx=16, pady=4)

        p_lbl_row = ctk.CTkFrame(palette_card, fg_color="transparent")
        p_lbl_row.pack(fill="x", padx=8, pady=(4, 2))
        ctk.CTkLabel(
            p_lbl_row, text="🎯 원클릭 과목 입력 (원하는 교시 클릭 후 아래 과목 선택):",
            font=get_font(10, "bold"), text_color="#64748b"
        ).pack(side="left")

        p_grid = ctk.CTkFrame(palette_card, fg_color="transparent")
        p_grid.pack(fill="x", padx=6, pady=(0, 6))

        for idx, subj in enumerate(QUICK_SUBJECTS):
            r = idx // 7
            c = idx % 7
            btn = ctk.CTkButton(
                p_grid, text=subj, width=54, height=26, font=get_font(10, "bold"),
                fg_color="#ffffff", hover_color="#e0f2fe", text_color="#0f172a",
                border_width=1, border_color="#cbd5e1", corner_radius=6,
                command=lambda s=subj: self._insert_quick_subject(s)
            )
            btn.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
            p_grid.grid_columnconfigure(c, weight=1)

        self.scroll_list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_list.pack(fill="both", expand=True, padx=16, pady=6)
        self._load_day_periods()

        btm_bar = ctk.CTkFrame(self, fg_color="#f8fafc", height=50, corner_radius=0, border_width=1, border_color="#e2e8f0")
        btm_bar.pack(fill="x", side="bottom")
        btm_bar.pack_propagate(False)

        ctk.CTkButton(
            btm_bar, text="✕ 닫기", width=70, height=34, font=get_font(11),
            fg_color="#94a3b8", hover_color="#64748b", text_color="#ffffff",
            corner_radius=6, command=self.destroy
        ).pack(side="left", padx=12)

        palette = theme_manager.get_theme()
        save_btn = ctk.CTkButton(
            btm_bar, text="💾 저장 및 전체 화면 즉시 반영", width=190, height=34, font=get_font(12, "bold"),
            fg_color=palette["accent"], hover_color=palette["accent_hover"], text_color="#ffffff",
            corner_radius=6, command=self._save_and_sync
        )
        save_btn.pack(side="right", padx=12)
        attach_tooltip(save_btn, "수정된 시간표를 저장하고 놀티쳐 보드, 위젯, 메인 창에 즉각 반영합니다")

    def _on_day_changed(self, choice: str):
        rev_map = {"월요일": "mon", "화요일": "tue", "수요일": "wed", "목요일": "thu", "금요일": "fri"}
        self.current_day_key = rev_map.get(choice, "mon")
        self._load_day_periods()

    def _load_day_periods(self):
        for w in self.scroll_list.winfo_children():
            w.destroy()

        self.entries.clear()
        self.tag_btns.clear()

        palette = theme_manager.get_theme()
        day_data = timetable_manager.weekly_timetable.get(self.current_day_key, [])
        periods = timetable_manager.periods
        lesson_periods = [p for p in periods if not p.get("is_lunch", False)]
        max_p = timetable_manager.max_periods

        for idx in range(max_p):
            p_info = lesson_periods[idx] if idx < len(lesson_periods) else {"name": f"{idx+1}교시", "start": "", "end": ""}
            cur_item = day_data[idx] if idx < len(day_data) else {"subject": "", "tag": "담임"}
            cur_subj = cur_item.get("subject", "") if isinstance(cur_item, dict) else str(cur_item)
            cur_tag = cur_item.get("tag", "담임") if isinstance(cur_item, dict) else "담임"

            row = ctk.CTkFrame(self.scroll_list, fg_color="#ffffff", corner_radius=8, border_width=1, border_color="#e2e8f0")
            row.pack(fill="x", pady=3)

            p_name = p_info.get("name", f"{idx+1}교시")
            s_val = p_info.get('start', '')
            e_val = p_info.get('end', '')
            time_str = f"{s_val} ~ {e_val}" if s_val and e_val else ""
            badge = ctk.CTkFrame(row, fg_color=palette["accent"], corner_radius=6, width=64, height=36)
            badge.pack(side="left", padx=8, pady=6)
            badge.pack_propagate(False)

            ctk.CTkLabel(badge, text=p_name, font=get_font(10, "bold"), text_color="#ffffff").pack(pady=(3, 0))
            if time_str:
                sub_tc = "#fef3c7" if palette["ctk_mode"] == "Light" else "#bae6fd"
                ctk.CTkLabel(badge, text=time_str, font=get_font(7), text_color=sub_tc).pack()

            ent = ctk.CTkEntry(row, placeholder_text="과목명 입력 (예: 국어)", font=get_font(12, "bold"), height=34)
            ent.pack(side="left", fill="x", expand=True, padx=8)
            ent.insert(0, cur_subj)
            ent.bind("<FocusIn>", lambda e, en=ent: self._set_active_entry(en))
            self.entries.append(ent)

            if self.focus_period is not None and self.focus_period == idx:
                self.after(100, ent.focus_set)
                self._active_entry = ent

            tag_seg = ctk.CTkSegmentedButton(
                row, values=["담임", "전담", "외강"],
                font=get_font(9, "bold"), width=130, height=28,
                selected_color=palette["accent"],
                selected_hover_color=palette["accent_hover"]
            )
            tag_seg.set(cur_tag if cur_tag in ["담임", "전담", "외강"] else "담임")
            tag_seg.pack(side="right", padx=8)
            self.tag_btns.append(tag_seg)

        if not self._active_entry and self.entries:
            self._active_entry = self.entries[0]

    def _set_active_entry(self, ent):
        self._active_entry = ent

    def _insert_quick_subject(self, subj: str):
        if self._active_entry:
            self._active_entry.delete(0, "end")
            self._active_entry.insert(0, subj)

    def _save_and_sync(self):
        new_list = []
        for i in range(len(self.entries)):
            subj = self.entries[i].get().strip()
            tag = self.tag_btns[i].get()
            new_list.append({"subject": subj, "tag": tag})

        timetable_manager.weekly_timetable[self.current_day_key] = new_list
        ok = timetable_manager.save_weekly_timetable(timetable_manager.weekly_timetable)
        if ok:
            messagebox.showinfo(
                "시간표 연동 완료",
                "✓ 시간표가 성공적으로 저장되었습니다!\n\n놀티쳐 보드(학생 화면)와 바탕화면 위젯, 메인 창에 실시간으로 즉시 반영되었습니다."
            )
            self.destroy()
        else:
            messagebox.showerror("저장 실패", "시간표 저장 중 오류가 발생했습니다.")

def open_timetable_quick_editor(parent=None, initial_day_key: Optional[str] = None, focus_period: Optional[int] = None):
    return TimetableQuickEditorDialog(parent, initial_day_key, focus_period)
