import sys
import tkinter as tk
from typing import Optional, Union, Tuple
import customtkinter as ctk

from src.theme_manager import theme_manager

class CTk2DScrollableFrame(ctk.CTkFrame):
    """
    세로(수직)와 가로(수평) 양방향 스크롤을 모두 지원하는 2D 스크롤 프레임.
    창의 크기를 아무리 줄여도 내부 콘텐츠가 찌그러지지 않고,
    수평/수직 스크롤바로 모든 콘텐츠(시간표, 급식 식단표, 우측 버튼 등)를 완벽하게 확인 가능.
    """
    def __init__(
        self,
        master,
        min_content_width: int = 740,
        fg_color: Optional[Union[str, Tuple[str, str]]] = "transparent",
        bg_color: Optional[Union[str, Tuple[str, str]]] = "transparent",
        corner_radius: int = 0,
        border_width: int = 0,
        **kwargs
    ):
        super().__init__(
            master=master,
            fg_color=fg_color,
            bg_color=bg_color,
            corner_radius=corner_radius,
            border_width=border_width,
            **kwargs
        )
        self.min_content_width = min_content_width

        # 그리드 구성:
        # row 0, col 0: 캔버스
        # row 0, col 1: 세로 스크롤바
        # row 1, col 0: 가로 스크롤바
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        palette = theme_manager.get_theme()

        # 배경 캔버스
        self._canvas = tk.Canvas(
            self,
            highlightthickness=0,
            borderwidth=0,
            bg=self._get_canvas_bg(palette)
        )
        self._canvas.grid(row=0, column=0, sticky="nsew")

        # 세로(수직) 스크롤바
        self._y_scrollbar = ctk.CTkScrollbar(
            self,
            orientation="vertical",
            command=self._canvas.yview,
            fg_color="transparent",
            button_color=palette["accent"],
            button_hover_color=palette["accent_hover"],
            width=12
        )
        self._y_scrollbar.grid(row=0, column=1, sticky="ns", padx=(2, 0))

        # 가로(수평) 스크롤바
        self._x_scrollbar = ctk.CTkScrollbar(
            self,
            orientation="horizontal",
            command=self._canvas.xview,
            fg_color="transparent",
            button_color=palette["accent"],
            button_hover_color=palette["accent_hover"],
            height=12
        )
        self._x_scrollbar.grid(row=1, column=0, sticky="ew", pady=(2, 0))

        self._canvas.configure(
            xscrollcommand=self._x_scrollbar.set,
            yscrollcommand=self._y_scrollbar.set
        )

        # 실제 위젯들이 배치될 내부 콘텐츠 프레임
        self.viewport = ctk.CTkFrame(self._canvas, fg_color="transparent")
        self._window_id = self._canvas.create_window(0, 0, window=self.viewport, anchor="nw")

        self.viewport.bind("<Configure>", self._on_viewport_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # 마우스 휠 바인딩
        self._bind_mouse_wheel(self._canvas)
        self._bind_mouse_wheel(self.viewport)

    def _get_canvas_bg(self, palette: dict) -> str:
        # 캔버스 배경색을 테마 메인 카드/배경에 맞춤
        ctk_mode = palette.get("ctk_mode", "Light")
        if ctk_mode == "Dark":
            return palette.get("card_bg", "#0f172a")
        return palette.get("card_bg", "#fefdfa")

    def _on_viewport_configure(self, event=None):
        """내부 위젯 변경 시 전체 스크롤 영역 갱신"""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """캔버스 크기 변경 시: 창이 넓으면 100% 채우고, 창이 좁으면 최소 폭 유지"""
        target_width = max(event.width, self.min_content_width)
        self._canvas.itemconfigure(self._window_id, width=target_width)
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _bind_mouse_wheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        widget.bind("<Shift-MouseWheel>", self._on_shift_mousewheel, add="+")
        # 리눅스 X11 마우스 휠
        widget.bind("<Button-4>", lambda e: self._canvas.yview_scroll(-2, "units"), add="+")
        widget.bind("<Button-5>", lambda e: self._canvas.yview_scroll(2, "units"), add="+")
        widget.bind("<Shift-Button-4>", lambda e: self._canvas.xview_scroll(-2, "units"), add="+")
        widget.bind("<Shift-Button-5>", lambda e: self._canvas.xview_scroll(2, "units"), add="+")

    def _on_mousewheel(self, event):
        # 일반 휠: 위아래(세로) 스크롤
        if event.delta:
            delta = int(-1 * (event.delta / 120)) * 2
            self._canvas.yview_scroll(delta, "units")

    def _on_shift_mousewheel(self, event):
        # Shift + 휠: 좌우(가로) 스크롤
        if event.delta:
            delta = int(-1 * (event.delta / 120)) * 2
            self._canvas.xview_scroll(delta, "units")

    def update_theme(self):
        """테마 변경 시 캔버스 및 스크롤바 색상 즉시 동기화"""
        palette = theme_manager.get_theme()
        self._canvas.configure(bg=self._get_canvas_bg(palette))
        self._y_scrollbar.configure(
            button_color=palette["accent"],
            button_hover_color=palette["accent_hover"]
        )
        self._x_scrollbar.configure(
            button_color=palette["accent"],
            button_hover_color=palette["accent_hover"]
        )

    def bind_children_mousewheel(self, widget=None):
        """자식 위젯들 위에서도 휠이 동작하도록 재귀 바인딩"""
        target = widget or self.viewport
        self._bind_mouse_wheel(target)
        for child in target.winfo_children():
            self.bind_children_mousewheel(child)
