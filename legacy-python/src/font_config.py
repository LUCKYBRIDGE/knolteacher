import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk

FONT_FAMILY = "Malgun Gothic"

def setup_global_fonts(root: tk.Tk = None):
    """
    Tkinter 및 시스템의 모든 기본 비트맵 폰트를 '맑은 고딕 (Malgun Gothic)'으로 전역 강제 치환
    비트맵 글꼴(굴림 등)로 인한 글씨 뭉개짐/깨짐 현상을 원천 차단
    """
    font_names = [
        "TkDefaultFont",
        "TkTextFont",
        "TkFixedFont",
        "TkMenuFont",
        "TkHeadingFont",
        "TkCaptionFont",
        "TkSmallCaptionFont",
        "TkIconFont",
        "TkTooltipFont"
    ]
    
    for fname in font_names:
        try:
            f = tkfont.nametofont(fname)
            f.configure(family=FONT_FAMILY)
        except Exception:
            pass

def get_font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    """일관된 맑은 고딕 폰트 객체 반환"""
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)
