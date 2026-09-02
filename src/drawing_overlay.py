import os
import sys
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import ImageGrab
from src.font_config import get_font

class ScreenDrawingOverlay:
    """
    모니터 위 어떤 웹페이지나 앱 위에서도 자유롭게 판서할 수 있는 투명 스크린 드로잉 오버레이
    """
    _instance = None

    @classmethod
    def get_instance(cls, parent=None):
        if cls._instance is None or not cls._instance.is_alive():
            cls._instance = cls(parent)
        return cls._instance

    def __init__(self, parent=None):
        self.parent = parent
        self.root = None
        self.canvas = None
        self.toolbar = None

        # 그리기 상태 변수
        self.current_tool = "pen"  # pen, highlighter, arrow, rect, line, eraser
        self.current_color = "#ff3b30"  # 기본 빨강
        self.current_width = 4
        self.mouse_mode = False

        self.history = []  # Undo history: list of item IDs
        self.current_stroke = []

        # 드래그 좌표
        self.last_x = None
        self.last_y = None
        self.start_x = None
        self.start_y = None
        self.temp_shape_id = None

    def is_alive(self) -> bool:
        return self.root is not None and self.root.winfo_exists()

    def show(self):
        if self.is_alive():
            self.root.deiconify()
            self.root.lift()
            return

        self.root = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.root.title("티처메이트 화면 판서")
        self.root.attributes("-topmost", True)
        self.root.attributes("-fullscreen", True)

        # Windows 투명 배경 설정 (키 색상을 투명하게 처리)
        self.trans_color = "#abcdef"
        self.root.configure(bg=self.trans_color)
        self.root.wm_attributes("-transparentcolor", self.trans_color)

        # 캔버스 생성
        self.canvas = tk.Canvas(
            self.root,
            bg=self.trans_color,
            highlightthickness=0,
            cursor="crosshair"
        )
        self.canvas.pack(fill="both", expand=True)

        # 마우스 이벤트 바인딩
        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Button-3>", lambda e: self.undo())

        # 단축키 바인딩
        self.root.bind("<Escape>", lambda e: self.close())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-Z>", lambda e: self.undo())
        self.root.bind("<c>", lambda e: self.clear_all())
        self.root.bind("<C>", lambda e: self.clear_all())

        # 플로팅 펜 툴바 생성
        self._build_floating_toolbar()

    def _build_floating_toolbar(self):
        self.toolbar = tk.Toplevel(self.root)
        self.toolbar.title("판서 도구")
        self.toolbar.attributes("-topmost", True)
        self.toolbar.overrideredirect(True)

        sw = self.root.winfo_screenwidth()
        tb_w, tb_h = 680, 52
        x = (sw - tb_w) // 2
        y = 20
        self.toolbar.geometry(f"{tb_w}x{tb_h}+{x}+{y}")

        bg_frame = ctk.CTkFrame(self.toolbar, fg_color="#181d28", corner_radius=14, border_width=2, border_color="#0a84ff")
        bg_frame.pack(fill="both", expand=True, padx=2, pady=2)

        drag_handle = ctk.CTkLabel(bg_frame, text="⠿", font=get_font(14, "bold"), text_color="#64748b", width=20, cursor="fleur")
        drag_handle.pack(side="left", padx=(8, 2))
        drag_handle.bind("<Button-1>", self._start_toolbar_drag)
        drag_handle.bind("<B1-Motion>", self._on_toolbar_drag)

        # 1. 펜 색상 버튼들
        colors = [
            ("빨강", "#ff3b30"),
            ("노랑", "#ffcc00"),
            ("초록", "#34c759"),
            ("파랑", "#007aff"),
            ("보라", "#af52de"),
            ("흰색", "#ffffff"),
            ("검정", "#1c1c1e")
        ]
        self.color_btns = {}
        for name, hex_code in colors:
            btn = ctk.CTkButton(
                bg_frame,
                text="",
                width=24,
                height=24,
                corner_radius=12,
                fg_color=hex_code,
                hover_color=hex_code,
                border_width=2 if hex_code == self.current_color else 0,
                border_color="#ffffff",
                command=lambda c=hex_code: self._select_color(c)
            )
            btn.pack(side="left", padx=2)
            self.color_btns[hex_code] = btn

        ctk.CTkFrame(bg_frame, width=1, height=26, fg_color="#334155").pack(side="left", padx=6)

        # 2. 도구 선택
        tools = [
            ("✏️", "pen", "일반 펜"),
            ("🖍️", "highlighter", "형광펜"),
            ("📏", "line", "직선"),
            ("➡️", "arrow", "화살표"),
            ("🔲", "rect", "사각형"),
            ("🧹", "eraser", "지우개")
        ]
        self.tool_btns = {}
        for icon, t_key, tip in tools:
            btn = ctk.CTkButton(
                bg_frame,
                text=icon,
                width=32,
                height=32,
                font=get_font(13),
                corner_radius=8,
                fg_color="#0a84ff" if t_key == self.current_tool else "#222a3a",
                hover_color="#1d4ed8",
                command=lambda k=t_key: self._select_tool(k)
            )
            btn.pack(side="left", padx=2)
            self.tool_btns[t_key] = btn

        ctk.CTkFrame(bg_frame, width=1, height=26, fg_color="#334155").pack(side="left", padx=6)

        # 3. 굵기 조절
        for w_val, w_label in [(3, "얇게"), (6, "보통"), (12, "굵게")]:
            ctk.CTkButton(
                bg_frame,
                text=w_label,
                width=36,
                height=26,
                font=get_font(10, "bold"),
                corner_radius=6,
                fg_color="#334155",
                hover_color="#475569",
                command=lambda w=w_val: self._select_width(w)
            ).pack(side="left", padx=2)

        ctk.CTkFrame(bg_frame, width=1, height=26, fg_color="#334155").pack(side="left", padx=6)

        # 4. 액션 버튼 (Undo, 전체지우기, 캡처저장, 닫기)
        ctk.CTkButton(
            bg_frame,
            text="↩",
            width=30,
            height=30,
            font=get_font(13, "bold"),
            fg_color="#334155",
            hover_color="#475569",
            corner_radius=8,
            command=self.undo
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            bg_frame,
            text="🗑️",
            width=30,
            height=30,
            font=get_font(12),
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            text_color="#fca5a5",
            corner_radius=8,
            command=self.clear_all
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            bg_frame,
            text="📸",
            width=30,
            height=30,
            font=get_font(12),
            fg_color="#059669",
            hover_color="#047857",
            corner_radius=8,
            command=self.save_screenshot
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            bg_frame,
            text="✕",
            width=30,
            height=30,
            font=get_font(12, "bold"),
            fg_color="#3f1d24",
            hover_color="#dc2626",
            text_color="#fca5a5",
            corner_radius=8,
            command=self.close
        ).pack(side="left", padx=(2, 6))

    def _start_toolbar_drag(self, event):
        self._tb_drag_x = event.x
        self._tb_drag_y = event.y

    def _on_toolbar_drag(self, event):
        dx = event.x - self._tb_drag_x
        dy = event.y - self._tb_drag_y
        x = self.toolbar.winfo_x() + dx
        y = self.toolbar.winfo_y() + dy
        self.toolbar.geometry(f"+{x}+{y}")

    def _select_color(self, hex_code: str):
        self.current_color = hex_code
        for c, btn in self.color_btns.items():
            if c == hex_code:
                btn.configure(border_width=2, border_color="#ffffff")
            else:
                btn.configure(border_width=0)
        if self.current_tool == "eraser":
            self._select_tool("pen")

    def _select_tool(self, tool_key: str):
        self.current_tool = tool_key
        for k, btn in self.tool_btns.items():
            if k == tool_key:
                btn.configure(fg_color="#0a84ff")
            else:
                btn.configure(fg_color="#222a3a")

        if tool_key == "eraser":
            self.canvas.configure(cursor="circle")
        else:
            self.canvas.configure(cursor="crosshair")

    def _select_width(self, width: int):
        self.current_width = width

    def _on_mouse_down(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.last_x = event.x
        self.last_y = event.y
        self.current_stroke = []

        if self.current_tool == "eraser":
            self._erase_at(event.x, event.y)

    def _on_mouse_move(self, event):
        if self.current_tool == "pen":
            line_id = self.canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                fill=self.current_color,
                width=self.current_width,
                capstyle=tk.ROUND,
                smooth=True
            )
            self.current_stroke.append(line_id)
            self.last_x = event.x
            self.last_y = event.y

        elif self.current_tool == "highlighter":
            hl_id = self.canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                fill=self.current_color,
                width=self.current_width + 10,
                capstyle=tk.ROUND,
                stipple="gray50",
                smooth=True
            )
            self.current_stroke.append(hl_id)
            self.last_x = event.x
            self.last_y = event.y

        elif self.current_tool == "line":
            if self.temp_shape_id:
                self.canvas.delete(self.temp_shape_id)
            self.temp_shape_id = self.canvas.create_line(
                self.start_x, self.start_y, event.x, event.y,
                fill=self.current_color,
                width=self.current_width,
                capstyle=tk.ROUND
            )

        elif self.current_tool == "arrow":
            if self.temp_shape_id:
                self.canvas.delete(self.temp_shape_id)
            self.temp_shape_id = self.canvas.create_line(
                self.start_x, self.start_y, event.x, event.y,
                fill=self.current_color,
                width=self.current_width,
                arrow=tk.LAST,
                arrowshape=(14, 18, 6),
                capstyle=tk.ROUND
            )

        elif self.current_tool == "rect":
            if self.temp_shape_id:
                self.canvas.delete(self.temp_shape_id)
            self.temp_shape_id = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline=self.current_color,
                width=self.current_width
            )

        elif self.current_tool == "eraser":
            self._erase_at(event.x, event.y)

    def _on_mouse_up(self, event):
        if self.temp_shape_id:
            self.history.append([self.temp_shape_id])
            self.temp_shape_id = None
        elif self.current_stroke:
            self.history.append(self.current_stroke)
            self.current_stroke = []

    def _erase_at(self, x, y):
        radius = 20
        overlapping = self.canvas.find_overlapping(x - radius, y - radius, x + radius, y + radius)
        for item in overlapping:
            self.canvas.delete(item)

    def undo(self):
        if self.history:
            last_stroke = self.history.pop()
            for item_id in last_stroke:
                self.canvas.delete(item_id)

    def clear_all(self):
        self.canvas.delete("all")
        self.history.clear()

    def save_screenshot(self):
        if self.toolbar:
            self.toolbar.withdraw()
        self.root.update()

        try:
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_path = f"티처메이트_판서캡처_{now_str}.png"
            fp = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg")],
                initialfile=default_path
            )
            if fp:
                img = ImageGrab.grab()
                img.save(fp)
                messagebox.showinfo("캡처 완료", f"판서 화면이 저장되었습니다!\n경로: {fp}")
        except Exception as ex:
            messagebox.showerror("오류", f"화면 캡처 저장 실패: {ex}")
        finally:
            if self.toolbar and self.toolbar.winfo_exists():
                self.toolbar.deiconify()

    def close(self):
        if self.toolbar and self.toolbar.winfo_exists():
            self.toolbar.destroy()
        if self.root and self.root.winfo_exists():
            self.root.destroy()
        self.root = None
        self.canvas = None
        self.toolbar = None
