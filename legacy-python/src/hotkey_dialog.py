"""
단축키 안내 및 커스텀 설정 다이얼로그 (HotkeyGuideDialog)
1. ⌨️ 빠른 도구 활용 단축키 안내 치트시트
2. ⚙️ 단축키 자유 변경 및 On/Off 설정
"""
import os
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from src.font_config import get_font
from src.theme_manager import theme_manager
from src.hotkey_manager import hotkey_manager, MOD_MAP, VK_MAP, DEFAULT_HOTKEYS
from src.icon_renderer import get_icon


class HotkeyGuideDialog(ctk.CTkToplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.title("교실 수업 도구 단축키 안내 및 설정")
        self.geometry("640x620")
        self.minsize(580, 500)
        self.attributes("-topmost", True)

        self._hotkey_vars = []
        self._build_ui()

    def _build_ui(self):
        palette = theme_manager.get_theme()
        self.configure(fg_color=palette["card_bg"])

        container = ctk.CTkFrame(self, fg_color=palette["card_bg"], corner_radius=12)
        container.pack(fill="both", expand=True, padx=12, pady=12)

        # 1. 상단 타이틀
        hdr = ctk.CTkFrame(container, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(6, 10))

        ctk.CTkLabel(
            hdr, text="⌨️ 빠른 도구 활용 전역 단축키 안내 & 설정",
            font=get_font(15, "bold"), text_color=palette["accent"]
        ).pack(side="left")

        # 💡 안내 배너
        banner = ctk.CTkFrame(container, fg_color=palette["card_inner_bg"], corner_radius=8, border_width=1, border_color=palette["card_border"])
        banner.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(
            banner,
            text="💡 [수업 중 원클릭 단축키 안내]\n• PPT, 웹 브라우저, 한글 등 다른 프로그램을 사용 중이어도 키보드를 누르면 즉시 실행됩니다.\n• 아래 목록에서 단축키를 직접 변경하거나 필요 없는 키를 끌 수 있습니다.",
            font=get_font(10), text_color=palette["text_main"], justify="left"
        ).pack(padx=12, pady=8, anchor="w")

        # 2. 탭뷰 (단축키 안내 치트시트 vs 단축키 변경 설정)
        self.tabview = ctk.CTkTabview(container, fg_color="transparent")
        self.tabview.pack(fill="both", expand=True, padx=4, pady=4)

        tab_guide = self.tabview.add("📋 단축키 치트시트")
        tab_setting = self.tabview.add("⚙️ 단축키 변경 설정")

        self._build_guide_tab(tab_guide, palette)
        self._build_setting_tab(tab_setting, palette)

        # 3. 하단 닫기 바
        b_bar = ctk.CTkFrame(container, fg_color="transparent")
        b_bar.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkButton(
            b_bar, text="닫기", font=get_font(11, "bold"), width=80, height=32,
            fg_color=palette["card_inner_bg"], hover_color=palette["sidebar_btn_hover"],
            text_color=palette["text_main"], command=self.destroy
        ).pack(side="right")

    # =========================================================================
    # 탭 1: 단축키 안내 치트시트 (한눈에 보기)
    # =========================================================================
    def _build_guide_tab(self, parent, palette):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        hotkeys = hotkey_manager.hotkeys

        for hk in hotkeys:
            if not hk.get("enabled", True):
                continue
            row = ctk.CTkFrame(scroll, fg_color=palette["card_inner_bg"], corner_radius=8, border_width=1, border_color=palette["card_border"])
            row.pack(fill="x", pady=3)

            mod = hk.get("mod", "Alt")
            k = hk.get("key", "1")
            key_txt = k if mod == "None" else f"{mod} + {k}"

            # 단축키 뱃지 (키보드 키캡 모양)
            keycap = ctk.CTkFrame(row, fg_color=palette["accent"], corner_radius=6)
            keycap.pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(
                keycap, text=f" {key_txt} ", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                text_color="#ffffff"
            ).pack(padx=8, pady=3)

            # 기능 이름 및 설명
            info_box = ctk.CTkFrame(row, fg_color="transparent")
            info_box.pack(side="left", fill="both", expand=True, padx=6, pady=4)

            ctk.CTkLabel(
                info_box, text=hk.get("name", ""), font=get_font(11, "bold"),
                text_color=palette["text_main"], anchor="w"
            ).pack(fill="x")

            ctk.CTkLabel(
                info_box, text=hk.get("desc", ""), font=get_font(9),
                text_color=palette["text_sub"], anchor="w"
            ).pack(fill="x")

    # =========================================================================
    # 탭 2: 단축키 변경 설정 (조합키, 키 선택, On/Off)
    # =========================================================================
    def _build_setting_tab(self, parent, palette):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self._hotkey_vars.clear()
        hotkeys = hotkey_manager.hotkeys

        mod_options = ["Alt", "Ctrl", "Ctrl+Alt", "Shift+Alt", "None"]
        key_options = [
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
            "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
            "A", "B", "C", "D", "E", "P", "S", "T", "Q", "Z"
        ]

        for hk in hotkeys:
            hk_id = hk["id"]
            row = ctk.CTkFrame(scroll, fg_color=palette["card_inner_bg"], corner_radius=8, border_width=1, border_color=palette["card_border"])
            row.pack(fill="x", pady=3)

            # 사용 여부 체크박스
            en_var = ctk.BooleanVar(value=hk.get("enabled", True))
            chk = ctk.CTkCheckBox(
                row, text="", variable=en_var, width=20, height=20,
                checkbox_width=18, checkbox_height=18, fg_color=palette["accent"]
            )
            chk.pack(side="left", padx=(10, 4))

            # 이름
            ctk.CTkLabel(
                row, text=hk.get("name", ""), width=120, font=get_font(10, "bold"),
                text_color=palette["text_main"], anchor="w"
            ).pack(side="left", padx=4)

            # 조합키 콤보
            mod_combo = ctk.CTkComboBox(
                row, values=mod_options, width=86, height=26, font=get_font(9, "bold"), state="readonly"
            )
            mod_combo.set(hk.get("mod", "Alt"))
            mod_combo.pack(side="left", padx=3)

            ctk.CTkLabel(row, text="+", font=get_font(11, "bold"), text_color=palette["text_sub"]).pack(side="left", padx=1)

            # 키 콤보
            key_combo = ctk.CTkComboBox(
                row, values=key_options, width=68, height=26, font=get_font(9, "bold"), state="readonly"
            )
            key_combo.set(hk.get("key", "1"))
            key_combo.pack(side="left", padx=3)

            self._hotkey_vars.append({
                "id": hk_id,
                "action": hk.get("action", ""),
                "name": hk.get("name", ""),
                "desc": hk.get("desc", ""),
                "enabled_var": en_var,
                "mod_combo": mod_combo,
                "key_combo": key_combo
            })

        # 설정 하단 버튼들
        ctrl_bar = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl_bar.pack(fill="x", padx=4, pady=(6, 2))

        ctk.CTkButton(
            ctrl_bar, text="💾 설정 저장 & 즉시 적용", font=get_font(11, "bold"), height=34,
            fg_color=palette["accent"], hover_color=palette["accent_hover"],
            command=self._save_settings
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(
            ctrl_bar, text="↺ 기본값 복원", font=get_font(10, "bold"), height=34, width=100,
            fg_color=palette["card_inner_bg"], hover_color=palette["sidebar_btn_hover"],
            text_color=palette["text_sub"], command=self._reset_defaults
        ).pack(side="right")

    def _save_settings(self):
        new_list = []
        for item in self._hotkey_vars:
            new_list.append({
                "id": item["id"],
                "action": item["action"],
                "name": item["name"],
                "desc": item["desc"],
                "mod": item["mod_combo"].get(),
                "key": item["key_combo"].get(),
                "enabled": item["enabled_var"].get()
            })

        hotkey_manager.save_config(new_list)
        hotkey_manager.reload()
        messagebox.showinfo("단축키 저장", "새로운 전역 단축키 설정이 즉시 시스템에 적용되었습니다!\n수업 중 언제든 키보드로 바로 실행하실 수 있습니다.")
        self.destroy()

    def _reset_defaults(self):
        if messagebox.askyesno("기본값 복원", "모든 단축키를 처음 기본값(Alt+1 ~ Alt+9, F2)으로 복원하시겠습니까?"):
            hotkey_manager.reset_to_defaults()
            messagebox.showinfo("복원 완료", "기본 단축키로 복원되었습니다.")
            self.destroy()
