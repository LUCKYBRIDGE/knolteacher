import os
import sys
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import ImageGrab
from src.font_config import get_font
from src.tooltip import attach_tooltip

class ScreenDrawingOverlay:
    """
    놀티쳐 데스크 전체화면 투명 판서 오버레이
    - 모니터 위 어떤 웹페이지/앱(나이스, 유튜브, PPT 등) 위에서도 자유롭게 판서
    - 판서 모드 중에는 화면의 어디를 클릭하더라도 다른 앱이 클릭되지 않고 100% 판서로만 작동
    - ESC 또는 [✕ 판서 종료]를 눌러야만 안전하게 판서 종료
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
        self.is_blackboard = False

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
        self.root.title("놀티쳐 데스크 - 화면 판서")
        self.root.attributes("-topmost", True)
        self.root.attributes("-fullscreen", True)

        # Windows 투명 배경 설정 (키 색상을 투명하게 처리하되 마우스 이벤트는 100% 캔버스가 캡처)
        self.trans_color = "#abcdef"
        self.root.configure(bg=self.trans_color)
        self.root.wm_attributes("-transparentcolor", self.trans_color)

        # 캔버스 생성 (전체화면 마우스 포커스 획득)
        self.canvas = tk.Canvas(
            self.root,
            bg=self.trans_color,
            highlightthickness=0,
            cursor="crosshair"
        )
        self.canvas.pack(fill="both", expand=True)

        # 마우스 판서 이벤트 바인딩
        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Button-3>", lambda e: self.undo())

        # 단축키 바인딩
        self.root.bind("<Escape>", lambda e: self.close())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-Z>", lambda e: self.undo())

        # 플로팅 판서 도구 바 생성
        self._build_toolbar()

        # 화면 최상위 고정
        self.root.lift()
        self.root.focus_force()

    def _build_toolbar(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        # 상단 중앙에 플로팅 툴바 배치
        tb_w = 640
        tb_h = 56
        tb_x = (sw - tb_w) // 2
        tb_y = 20

        self.toolbar = tk.Toplevel(self.root)
        self.toolbar.title("판서 도구함")
        self.toolbar.geometry(f"{tb_w}x{tb_h}+{tb_x}+{tb_y}")
        self.toolbar.overrideredirect(True)
        self.toolbar.attributes("-topmost", True)

        # macOS 스타일 플로팅 캡슐 프레임
        bg_frame = ctk.CTkFrame(
            self.toolbar,
            fg_color="#0f172a",
            corner_radius=18,
            border_width=2,
            border_color="#38bdf8"
        )
        bg_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # 드래그 이동 핸들
        drag_handle = ctk.CTkLabel(
            bg_frame,
            text="⋮⋮",
            font=get_font(14, "bold"),
            text_color="#94a3b8",
            width=20,
            cursor="fleur"
        )
        drag_handle.pack(side="left", padx=(8, 4))
        drag_handle.bind("<Button-1>", self._start_toolbar_drag)
        drag_handle.bind("<B1-Motion>", self._on_toolbar_drag)
        attach_tooltip(drag_handle, "드래그하여 판서 도구함 위치 이동")

        # 1. 도구 선택 (일반펜, 형광펜, 직선/화살표, 사각형, 지우개)
        self.tool_btns = {}
        tools = [
            ("pen", "✏️", "일반 펜 판서"),
            ("highlighter", "🖍️", "반투명 형광펜 강조"),
            ("arrow", "↗", "화살표 그리기"),
            ("rect", "▢", "사각형 박스 그리기"),
            ("eraser", "🧹", "부분 지우개")
        ]

        for t_key, icon, desc in tools:
            btn = ctk.CTkButton(
                bg_frame,
                text=icon,
                width=34,
                height=34,
                font=get_font(13, "bold"),
                fg_color="#0284c7" if t_key == "pen" else "transparent",
                hover_color="#0369a1",
                corner_radius=8,
                command=lambda k=t_key: self._select_tool(k)
            )
            btn.pack(side="left", padx=2)
            self.tool_btns[t_key] = btn
            attach_tooltip(btn, f"{desc}")

        ctk.CTkFrame(bg_frame, width=1, height=28, fg_color="#334155").pack(side="left", padx=4)

        # 2. 색상 팔레트 (빨강, 주황, 노랑, 초록, 파랑, 보라, 흰색, 검정)
        self.color_btns = {}
        colors = [
            ("#ff3b30", "빨간색"),
            ("#ff9500", "주황색"),
            ("#ffd60a", "노란색"),
            ("#30d158", "초록색"),
            ("#0a84ff", "파란색"),
            ("#bf5af2", "보라색"),
            ("#ffffff", "흰색")
        ]

        for c_hex, c_name in colors:
            btn = ctk.CTkButton(
                bg_frame,
                text="",
                width=24,
                height=24,
                corner_radius=12,
                fg_color=c_hex,
                hover_color=c_hex,
                border_width=2 if c_hex == self.current_color else 0,
                border_color="#ffffff",
                command=lambda c=c_hex: self._select_color(c)
            )
            btn.pack(side="left", padx=2)
            self.color_btns[c_hex] = btn
            attach_tooltip(btn, f"펜 색상: {c_name}")

        ctk.CTkFrame(bg_frame, width=1, height=28, fg_color="#334155").pack(side="left", padx=4)

        # 3. 굵기 조절 (가는선, 보통선, 굵은선)
        widths = [(3, "가는 펜 (3px)"), (6, "보통 펜 (6px)"), (12, "굵은 펜 (12px)")]
        for w_val, w_desc in widths:
            btn = ctk.CTkButton(
                bg_frame,
                text=f"{w_val}p",
                width=28,
                height=26,
                font=get_font(9, "bold"),
                corner_radius=6,
                fg_color="#334155",
                hover_color="#475569",
                command=lambda w=w_val: self._select_width(w)
            )
            btn.pack(side="left", padx=2)
            attach_tooltip(btn, f"펜 굵기: {w_desc}")

        ctk.CTkFrame(bg_frame, width=1, height=28, fg_color="#334155").pack(side="left", padx=4)

        # 4. 액션 버튼 (칠판모드, 실행취소, 전체삭제, 캡처저장, 판서종료)
        self.board_btn = ctk.CTkButton(
            bg_frame,
            text="⬛",
            width=32,
            height=32,
            font=get_font(12),
            fg_color="#1e293b",
            hover_color="#334155",
            corner_radius=8,
            command=self._toggle_blackboard
        )
        self.board_btn.pack(side="left", padx=2)
        attach_tooltip(self.board_btn, "칠판 모드 전환 (투명 ↔ 어두운 칠판)")

        undo_btn = ctk.CTkButton(
            bg_frame,
            text="↩",
            width=32,
            height=32,
            font=get_font(13, "bold"),
            fg_color="#334155",
            hover_color="#475569",
            corner_radius=8,
            command=self.undo
        )
        undo_btn.pack(side="left", padx=2)
        attach_tooltip(undo_btn, "실행 취소 (Undo / Ctrl+Z)")

        clear_btn = ctk.CTkButton(
            bg_frame,
            text="🗑️",
            width=32,
            height=32,
            font=get_font(12),
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            text_color="#fca5a5",
            corner_radius=8,
            command=self.clear_all
        )
        clear_btn.pack(side="left", padx=2)
        attach_tooltip(clear_btn, "화면 판서 전체 지우기")

        cap_btn = ctk.CTkButton(
            bg_frame,
            text="📸",
            width=32,
            height=32,
            font=get_font(12),
            fg_color="#059669",
            hover_color="#047857",
            corner_radius=8,
            command=self.save_screenshot
        )
        cap_btn.pack(side="left", padx=2)
        attach_tooltip(cap_btn, "판서 화면 전체 캡처 저장")

        close_btn = ctk.CTkButton(
            bg_frame,
            text="✕ 판서 종료",
            width=80,
            height=32,
            font=get_font(11, "bold"),
            fg_color="#dc2626",
            hover_color="#b91c1c",
            text_color="#ffffff",
            corner_radius=8,
            command=self.close
        )
        close_btn.pack(side="left", padx=(4, 6))
        attach_tooltip(close_btn, "판서 모드를 완전히 종료하고 마우스 제어 복원 (ESC)")

    def _toggle_blackboard(self):
        self.is_blackboard = not self.is_blackboard
        if self.is_blackboard:
            self.root.wm_attributes("-transparentcolor", "")
            self.root.configure(bg="#1c2826")
            self.canvas.configure(bg="#1c2826")
            self.board_btn.configure(text="🪟", fg_color="#0284c7")
        else:
            self.root.configure(bg=self.trans_color)
            self.canvas.configure(bg=self.trans_color)
            self.root.wm_attributes("-transparentcolor", self.trans_color)
            self.board_btn.configure(text="⬛", fg_color="#1e293b")

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

    def _select_width(self, width: int):
        self.current_width = width

    def _select_tool(self, tool_key: str):
        self.current_tool = tool_key
        for k, btn in self.tool_btns.items():
            if k == tool_key:
                btn.configure(fg_color="#0284c7")
            else:
                btn.configure(fg_color="transparent")

        if tool_key == "eraser":
            self.canvas.configure(cursor="circle")
        else:
            self.canvas.configure(cursor="crosshair")

    def _on_mouse_down(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.last_x = event.x
        self.last_y = event.y
        self.current_stroke = []

        if self.current_tool in ["pen", "highlighter"]:
            pass
        elif self.current_tool == "eraser":
            self._erase_at(event.x, event.y)

    def _on_mouse_move(self, event):
        if self.current_tool == "pen":
            item_id = self.canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                fill=self.current_color,
                width=self.current_width,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
                smooth=True
            )
            self.current_stroke.append(item_id)
            self.last_x = event.x
            self.last_y = event.y

        elif self.current_tool == "highlighter":
            # 형광펜 (굵은 선 + 반투명 stipple 질감)
            item_id = self.canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                fill=self.current_color,
                width=self.current_width * 3,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
                stipple="gray50",
                smooth=True
            )
            self.current_stroke.append(item_id)
            self.last_x = event.x
            self.last_y = event.y

        elif self.current_tool == "eraser":
            self._erase_at(event.x, event.y)

        elif self.current_tool == "arrow":
            if self.temp_shape_id:
                self.canvas.delete(self.temp_shape_id)
            self.temp_shape_id = self.canvas.create_line(
                self.start_x, self.start_y, event.x, event.y,
                fill=self.current_color,
                width=self.current_width,
                arrow=tk.LAST,
                arrowshape=(16, 20, 6)
            )

        elif self.current_tool == "rect":
            if self.temp_shape_id:
                self.canvas.delete(self.temp_shape_id)
            self.temp_shape_id = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline=self.current_color,
                width=self.current_width
            )

    def _on_mouse_up(self, event):
        if self.current_tool in ["pen", "highlighter"]:
            if self.current_stroke:
                self.history.append(("stroke", self.current_stroke))
                self.current_stroke = []

        elif self.current_tool in ["arrow", "rect"]:
            if self.temp_shape_id:
                self.history.append(("single", self.temp_shape_id))
                self.temp_shape_id = None

    def _erase_at(self, x, y, radius=18):
        items = self.canvas.find_overlapping(x - radius, y - radius, x + radius, y + radius)
        for item in items:
            self.canvas.delete(item)

    def undo(self):
        if not self.history:
            return
        last_action = self.history.pop()
        action_type, target = last_action
        if action_type == "stroke":
            for item_id in target:
                self.canvas.delete(item_id)
        elif action_type == "single":
            self.canvas.delete(target)

    def clear_all(self):
        self.canvas.delete("all")
        self.history.clear()

    def save_screenshot(self):
        try:
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_fn = f"놀티쳐데스크_판서_{now_str}.png"
            file_path = filedialog.asksaveasfilename(
                title="판서 화면 캡처 저장",
                initialfile=default_fn,
                defaultextension=".png",
                filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")]
            )
            if not file_path:
                return

            self.toolbar.withdraw()
            self.root.update()
            
            img = ImageGrab.grab()
            img.save(file_path)

            self.toolbar.deiconify()
            messagebox.showinfo("저장 완료", f"판서 화면이 저장되었습니다:\n{file_path}")
        except Exception as e:
            if self.toolbar:
                self.toolbar.deiconify()
            messagebox.showerror("저장 실패", f"캡처 저장 중 오류 발생:\n{e}")

    def close(self):
        if self.toolbar:
            try:
                self.toolbar.destroy()
            except Exception:
                pass
            self.toolbar = None

        if self.root:
            try:
                self.root.destroy()
            except Exception:
                pass
            self.root = None

        ScreenDrawingOverlay._instance = None
