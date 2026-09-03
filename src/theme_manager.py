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
        "sidebar_btn_active": "#b45309",      # 단정한 웜 앰버
        "sidebar_text": "#1c1917",            # 선명한 다크 에스프레소
        "header_bg": "#ffffff",
        "header_border": "#d8ccba",
        "card_bg": "#ffffff",
        "card_inner_bg": "#fcfbf9",
        "card_border": "#dbcdba",
        "text_main": "#1c1917",               # 본문 텍스트 (다크 에스프레소)
        "text_sub": "#44403c",                # 서브 텍스트 (미디엄 에스프레소)
        "text_muted": "#78716c",              # 보조/시간 텍스트 (소프트 뉴트럴)
        "accent": "#b45309",                  # ★ 유일한 메인 액센트 (웜 앰버)
        "accent_hover": "#92400e",            # 진한 앰버
        "accent_soft": "#fef3c7",             # 부드러운 앰버 틴트
        "accent_blue": "#b45309",             # 알록달록 방지: 메인 액센트 통일
        "accent_green": "#92400e",            # 알록달록 방지: 딥 앰버 통일
        "accent_orange": "#b45309",           # 알록달록 방지: 메인 액센트 통일
        "accent_purple": "#78350f",           # 알록달록 방지: 다크 앰버 통일
        "tag_bg": "#f5efe6",                  # 차분한 톤온톤 배지
        "tag_text": "#78350f",
        "lunch_bg": "#fbf7f0",
        "lunch_border": "#e7dac7",
        "lunch_text": "#92400e",
        "current_bg": "#fef9ee",
        "current_border": "#b45309",
        "current_text": "#78350f"
    },
    "Dark": {
        "name": "다크 모드 (Dark Indigo)",
        "ctk_mode": "Dark",
        "app_bg": "#0b0f19",
        "sidebar_bg": "#0d1321",
        "sidebar_btn_hover": "#1e293b",
        "sidebar_btn_active": "#38bdf8",
        "sidebar_text": "#f8fafc",
        "header_bg": "#182234",
        "header_border": "#26334d",
        "card_bg": "#161d2f",
        "card_inner_bg": "#111622",
        "card_border": "#26334d",
        "text_main": "#f8fafc",
        "text_sub": "#94a3b8",
        "text_muted": "#64748b",
        "accent": "#38bdf8",
        "accent_hover": "#0284c7",
        "accent_soft": "#0c4a6e",
        "accent_blue": "#38bdf8",
        "accent_green": "#38bdf8",
        "accent_orange": "#38bdf8",
        "accent_purple": "#38bdf8",
        "tag_bg": "#1e293b",
        "tag_text": "#e2e8f0",
        "lunch_bg": "#141e30",
        "lunch_border": "#293548",
        "lunch_text": "#cbd5e1",
        "current_bg": "#0c2b42",
        "current_border": "#38bdf8",
        "current_text": "#38bdf8"
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
        "accent_soft": "#e0f2fe",
        "accent_blue": "#0284c7",
        "accent_green": "#0284c7",
        "accent_orange": "#0284c7",
        "accent_purple": "#0284c7",
        "tag_bg": "#f1f5f9",
        "tag_text": "#334155",
        "lunch_bg": "#f8fafc",
        "lunch_border": "#cbd5e1",
        "lunch_text": "#475569",
        "current_bg": "#f0f9ff",
        "current_border": "#0284c7",
        "current_text": "#0369a1"
    }
}

class ThemeManager:
    """
    놀티쳐 데스크의 테마(베이지, 다크, 라이트) 관리자
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
