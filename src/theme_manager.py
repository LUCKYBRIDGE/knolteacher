import os
import sys
from typing import Dict, Any

THEMES: Dict[str, Dict[str, Any]] = {
    "Beige": {
        "name": "따뜻한 베이지 (Warm Beige)",
        "ctk_mode": "Light",
        "app_bg": "#f8f5ee",
        "sidebar_bg": "#ece3d4",
        "sidebar_btn_hover": "#dfd2be",
        "sidebar_btn_active": "#b45309",      # 따뜻한 앰버 카라멜
        "sidebar_text": "#1c1917",            # ★ 선명한 다크 에스프레소 (가독성 100%)
        "header_bg": "#ffffff",
        "header_border": "#d8ccba",
        "card_bg": "#ffffff",
        "card_inner_bg": "#fcfbf9",
        "card_border": "#dbcdba",
        "text_main": "#1c1917",               # ★ 가장 진한 본문 텍스트
        "text_sub": "#44403c",                # ★ 또렷한 서브 텍스트
        "text_muted": "#78716c",
        "accent": "#b45309",
        "accent_hover": "#92400e",
        "accent_blue": "#0284c7",
        "accent_green": "#15803d",
        "accent_orange": "#c2410c",
        "accent_purple": "#6d28d9",
        "tag_bg": "#e6dac7"
    },
    "Dark": {
        "name": "다크 모드 (Dark Indigo)",
        "ctk_mode": "Dark",
        "app_bg": "#0b0f19",
        "sidebar_bg": "#0d1321",
        "sidebar_btn_hover": "#1e293b",
        "sidebar_btn_active": "#0284c7",
        "sidebar_text": "#f8fafc",
        "header_bg": "#182234",
        "header_border": "#38bdf8",
        "card_bg": "#161d2f",
        "card_inner_bg": "#111622",
        "card_border": "#26334d",
        "text_main": "#f8fafc",
        "text_sub": "#94a3b8",
        "text_muted": "#64748b",
        "accent": "#0284c7",
        "accent_hover": "#0369a1",
        "accent_blue": "#0284c7",
        "accent_green": "#10b981",
        "accent_orange": "#ea580c",
        "accent_purple": "#7c3aed",
        "tag_bg": "#1e293b"
    },
    "Light": {
        "name": "모던 라이트 (Clean Light)",
        "ctk_mode": "Light",
        "app_bg": "#f1f5f9",
        "sidebar_bg": "#e2e8f0",
        "sidebar_btn_hover": "#cbd5e1",
        "sidebar_btn_active": "#0284c7",
        "sidebar_text": "#0f172a",
        "header_bg": "#ffffff",
        "header_border": "#cbd5e1",
        "card_bg": "#ffffff",
        "card_inner_bg": "#f8fafc",
        "card_border": "#e2e8f0",
        "text_main": "#0f172a",
        "text_sub": "#334155",
        "text_muted": "#64748b",
        "accent": "#0284c7",
        "accent_hover": "#0369a1",
        "accent_blue": "#2563eb",
        "accent_green": "#059669",
        "accent_orange": "#ea580c",
        "accent_purple": "#7c3aed",
        "tag_bg": "#e2e8f0"
    }
}

class ThemeManager:
    """
    티처메이트의 테마(베이지, 다크, 라이트) 관리자
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.current_theme_key = "Beige"  # 기본값: 따뜻한 베이지

    def get_theme(self, theme_key: str = None) -> Dict[str, Any]:
        key = theme_key or self.current_theme_key
        return THEMES.get(key, THEMES["Beige"])

    def set_theme(self, theme_key: str):
        if theme_key in THEMES:
            self.current_theme_key = theme_key

theme_manager = ThemeManager.get_instance()
