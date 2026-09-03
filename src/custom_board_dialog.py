"""
커스텀 놀티쳐 보드 설정 및 실행 다이얼로그 (Custom Board Launch Dialog)
- 교사가 원하는 레이아웃, 시작 도구, 표시할 교실 허브 요소(시간표/급식/알림장), 테마, 창 모드를 직접 조합하여 즉시 실행
- 설정한 조합을 새 프리셋으로 영구 저장 가능
"""

import os
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from src.font_config import setup_global_fonts, get_font
from src.theme_manager import theme_manager
from src.board_preset_manager import board_preset_manager

class CustomBoardLaunchDialog(ctk.CTkToplevel):
    def __init__(self, parent_app, on_launch_callback):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.on_launch_callback = on_launch_callback

        self.title("🛠️ 커스텀 놀티쳐 보드 설정 및 실행")
        self.geometry("560x640")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.transient(parent_app)
        self.grab_set()

        setup_global_fonts(self)
        self._build_ui()

    def _build_ui(self):
        palette = theme_manager.get_theme()
        bg_col = "#0f172a" if palette.get("ctk_mode") == "dark" else "#ffffff"
        card_bg = "#1e293b" if palette.get("ctk_mode") == "dark" else "#f8fafc"
        border_col = palette.get("card_border", "#334155")
        text_main = palette.get("text_main", "#ffffff")
        text_sub = palette.get("text_sub", "#94a3b8")
        accent = palette.get("accent", "#38bdf8")

        self.configure(fg_color=bg_col)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        # 헤더
        hdr = ctk.CTkFrame(scroll, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(hdr, text="🛠️ 커스텀 놀티쳐 보드 런처", font=get_font(16, "bold"), text_color=accent).pack(side="left")
        ctk.CTkLabel(scroll, text="수업 목적에 맞게 레이아웃과 표시할 항목을 자유롭게 조합하여 띄웁니다.", font=get_font(11), text_color=text_sub).pack(anchor="w", pady=(0, 14))

        # 1. 화면 레이아웃 선택 카드
        c1 = ctk.CTkFrame(scroll, fg_color=card_bg, corner_radius=10, border_width=1, border_color=border_col)
        c1.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(c1, text="1. 화면 레이아웃 모드", font=get_font(12, "bold"), text_color=text_main).pack(anchor="w", padx=14, pady=(10, 4))

        self.layout_var = ctk.StringVar(value="standard")
        layouts = [
            ("standard", "표준 2단 분할 (수업 도구 65% + 교실 허브 35%)"),
            ("focus_tool", "수업 도구 집중 풀화면 (교실 허브 숨김, 도구 100% 꽉 채움)"),
            ("board_only", "학급 게시판 전면 모드 (시간표+급식+알림장 3열 대형 표출)")
        ]
        for val, desc in layouts:
            ctk.CTkRadioButton(
                c1, text=desc, variable=self.layout_var, value=val,
                font=get_font(11), text_color=text_main, fg_color=accent,
                hover_color=accent
            ).pack(anchor="w", padx=16, pady=4)
        c1.pack_configure(pady=(0, 10))

        # 2. 시작 기본 도구 선택 카드
        c2 = ctk.CTkFrame(scroll, fg_color=card_bg, corner_radius=10, border_width=1, border_color=border_col)
        c2.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(c2, text="2. 시작 기본 수업 도구", font=get_font(12, "bold"), text_color=text_main).pack(anchor="w", padx=14, pady=(10, 6))

        tool_row = ctk.CTkFrame(c2, fg_color="transparent")
        tool_row.pack(fill="x", padx=14, pady=(0, 10))

        self.tool_seg = ctk.CTkSegmentedButton(
            tool_row,
            values=["타이머", "발표자 추첨", "주사위", "돌림판", "점수판", "학급 판서"],
            font=get_font(10, "bold"), height=28,
            selected_color=accent, selected_hover_color=palette.get("accent_hover", "#0284c7"),
            unselected_color=palette.get("sidebar_btn_hover", "#334155"), text_color=text_main
        )
        self.tool_seg.set("타이머")
        self.tool_seg.pack(fill="x")

        # 3. 교실 허브 표시 요소 선택 (체크박스)
        c3 = ctk.CTkFrame(scroll, fg_color=card_bg, corner_radius=10, border_width=1, border_color=border_col)
        c3.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(c3, text="3. 교실 허브 표시 요소 (다중 선택 가능)", font=get_font(12, "bold"), text_color=text_main).pack(anchor="w", padx=14, pady=(10, 6))

        self.cb_timetable_var = ctk.BooleanVar(value=True)
        self.cb_meal_var = ctk.BooleanVar(value=True)
        self.cb_memo_var = ctk.BooleanVar(value=True)

        cb_row = ctk.CTkFrame(c3, fg_color="transparent")
        cb_row.pack(fill="x", padx=16, pady=(0, 10))

        ctk.CTkCheckBox(cb_row, text="오늘의 시간표", variable=self.cb_timetable_var, font=get_font(11), text_color=text_main, fg_color=accent).pack(side="left", padx=(0, 14))
        ctk.CTkCheckBox(cb_row, text="오늘의 급식 식단", variable=self.cb_meal_var, font=get_font(11), text_color=text_main, fg_color=accent).pack(side="left", padx=(0, 14))
        ctk.CTkCheckBox(cb_row, text="학급 알림장 메모", variable=self.cb_memo_var, font=get_font(11), text_color=text_main, fg_color=accent).pack(side="left")

        # 4. 색상 테마 및 창 모드
        c4 = ctk.CTkFrame(scroll, fg_color=card_bg, corner_radius=10, border_width=1, border_color=border_col)
        c4.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(c4, text="4. 테마 및 화면 모드", font=get_font(12, "bold"), text_color=text_main).pack(anchor="w", padx=14, pady=(10, 6))

        opt_row = ctk.CTkFrame(c4, fg_color="transparent")
        opt_row.pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(opt_row, text="테마:", font=get_font(11, "bold"), text_color=text_sub).pack(side="left", padx=(0, 4))
        self.theme_combo = ctk.CTkComboBox(
            opt_row, values=["소프트 슬레이트 다크", "스마트 칠판 딥그린", "모던 웜베이지", "오션 딥인디고"],
            width=140, height=28, font=get_font(10, "bold"), state="readonly"
        )
        self.theme_combo.set("소프트 슬레이트 다크")
        self.theme_combo.pack(side="left", padx=(0, 14))

        ctk.CTkLabel(opt_row, text="창 모드:", font=get_font(11, "bold"), text_color=text_sub).pack(side="left", padx=(0, 4))
        self.win_mode_combo = ctk.CTkComboBox(
            opt_row, values=["일반 창 모드 (1280x820)", "전체화면 (F11)", "컴팩트 창 모드 (960x640)"],
            width=160, height=28, font=get_font(10, "bold"), state="readonly"
        )
        self.win_mode_combo.set("일반 창 모드 (1280x820)")
        self.win_mode_combo.pack(side="left")

        # 5. 새 프리셋으로 저장 (선택 사항)
        save_box = ctk.CTkFrame(scroll, fg_color="transparent")
        save_box.pack(fill="x", pady=(0, 10))

        self.preset_name_entry = ctk.CTkEntry(save_box, placeholder_text="이 조합을 새 프리셋으로 저장하려면 이름 입력 (선택사항)", font=get_font(10), height=30)
        self.preset_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            save_box, text="💾 프리셋 저장", font=get_font(10, "bold"), width=90, height=30,
            fg_color=palette.get("sidebar_btn_hover", "#334155"), hover_color=accent, text_color=text_main,
            corner_radius=6, command=self._save_as_preset
        ).pack(side="right")

        # 하단 액션 버튼
        btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_row.pack(fill="x", pady=(6, 12))

        ctk.CTkButton(
            btn_row, text="취소", width=80, height=38, font=get_font(11, "bold"),
            fg_color="transparent", hover_color=palette.get("sidebar_btn_hover", "#334155"),
            text_color=text_sub, corner_radius=8, command=self.destroy
        ).pack(side="left")

        ctk.CTkButton(
            btn_row, text="📺 커스텀 설정으로 바로 띄우기", height=40, font=get_font(13, "bold"),
            fg_color=accent, hover_color=palette.get("accent_hover", "#0284c7"),
            text_color="#ffffff", corner_radius=8, command=self._launch_custom_board
        ).pack(side="right", fill="x", expand=True, padx=(10, 0))

    def _get_config_dict(self):
        tool_map = {
            "타이머": "timer", "발표자 추첨": "picker", "주사위": "dice",
            "돌림판": "wheel", "점수판": "scoreboard", "학급 판서": "drawing"
        }
        theme_map = {
            "소프트 슬레이트 다크": "slate_dark",
            "스마트 칠판 딥그린": "chalkboard",
            "모던 웜베이지": "warm_beige",
            "오션 딥인디고": "indigo_night"
        }
        return {
            "layout_mode": self.layout_var.get(),
            "active_tool": tool_map.get(self.tool_seg.get(), "timer"),
            "show_timetable": self.cb_timetable_var.get(),
            "show_meal": self.cb_meal_var.get(),
            "show_memo": self.cb_memo_var.get(),
            "theme_key": theme_map.get(self.theme_combo.get(), "slate_dark"),
            "is_fullscreen": "전체화면" in self.win_mode_combo.get(),
            "compact_size": "컴팩트" in self.win_mode_combo.get()
        }

    def _save_as_preset(self):
        name = self.preset_name_entry.get().strip()
        if not name:
            messagebox.showwarning("입력 필요", "프리셋 이름을 입력해주세요.")
            return
        cfg = self._get_config_dict()
        board_preset_manager.save_preset(name, cfg)
        messagebox.showinfo("저장 완료", f"'{name}' 프리셋으로 저장되었습니다!")

    def _launch_custom_board(self):
        cfg = self._get_config_dict()
        self.destroy()
        if self.on_launch_callback:
            self.on_launch_callback(cfg)
