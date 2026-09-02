import os
import sys
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import customtkinter as ctk
from PIL import ImageGrab, ImageTk, Image
from src.font_config import get_font
from src.tooltip import attach_tooltip

class ScreenDrawingOverlay:
    """
    놀티쳐 데스크 전체화면 스크린 판서 오버레이
    - 바탕화면, 웹 브라우저, 나이스, 유튜브, PPT 등 어떤 화면 위에서도 완벽하게 판서
    - 화면 캡처 동결(Freeze) 레이어로 뒤의 웹/앱 클릭 관통 오류 100% 차단
    - 펜, 형광펜, 직선/화살표, 사각형, 텍스트 입력(T), 칠판 모드, 캡처 저장 지원
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

        # 화면 배경 이미지
        self.bg_photo = None
        self.bg_mode = "screen"  # "screen", "greenboard", "blackboard"

        # 그리기 상태 변수
        self.current_tool = "pen"  # pen, highlighter, arrow, rect, text, eraser
        self.current_color = "#ff3b30"  # 기본 빨강
        self.current_width = 4

        self.history = []  # Undo history
        self.current_stroke = []

        # 마우스 드래그 좌표
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

        # 1. 켜는 순간 현재 화면 전체 고해상도 캡처 (웹/바탕화면 동결)
        try:
            screen_img = ImageGrab.grab()
        except Exception:
            screen_img = None

        self.root = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.root.title("놀티쳐 데스크 - 화면 판서")
        self.root.attributes("-topmost", True)
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#000000")

        # 2. 전체화면 캔버스 생성
        self.canvas = tk.Canvas(
            self.root,
            bg="#000000",
            highlightthickness=0,
            cursor="crosshair"
        )
        self.canvas.pack(fill="both", expand=True)

        # 3. 캡처한 화면을 캔버스 배경으로 1:1 렌더링
        if screen_img:
            self.bg_photo = ImageTk.PhotoImage(screen_img)
            self.bg_item_id = self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw", tags="bg_layer")
        else:
            self.bg_item_id = None

        # 4. 마우스 판서 이벤트 바인딩 (뒤의 웹이나 앱이 전혀 클릭되지 않고 100% 판서로만 동작)
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

        tb_w = 680
        tb_h = 56
        tb_x = (sw - tb_w) // 2
        tb_y = 20

        self.toolbar = tk.Toplevel(self.root)
        self.toolbar.title("판서 도구함")
        self.toolbar.geometry(f"{tb_w}x{tb_h}+{tb_x}+{tb_y}")
        self.toolbar.overrideredirect(True)
        self.toolbar.attributes("-topmost", True)

        bg_frame = ctk.CTkFrame(
            self.toolbar,
            fg_color="#090d16",
            corner_radius=20,
            border_width=1,
            border_color="#0284c7"
        )
        bg_frame.pack(fill="both", expand=True, padx=1, pady=1)

        from src.icon_renderer import get_icon, COL_MAIN, COL_ACTIVE, COL_DANGER, COL_GREEN, COL_ORANGE
        ICO = 22  # 아이콘 표시 크기

        # ── 드래그 핸들 ──────────────────────────────────────────────────
        drag_lbl = ctk.CTkLabel(
            bg_frame, text="", image=get_icon("drag", "#475569", ICO),
            width=20, cursor="fleur"
        )
        drag_lbl.pack(side="left", padx=(8, 2))
        drag_lbl.bind("<Button-1>", self._start_toolbar_drag)
        drag_lbl.bind("<B1-Motion>", self._on_toolbar_drag)
        attach_tooltip(drag_lbl, "드래그하여 판서 도구함 위치 이동")

        def _sep():
            ctk.CTkFrame(bg_frame, width=1, height=24, fg_color="#334155").pack(side="left", padx=3)

        # ── 도구 선택 버튼 ────────────────────────────────────────────────
        self.tool_btns = {}
        tools = [
            ("pen",         "pen",         COL_MAIN,   "일반 펜 판서 (P)"),
            ("highlighter", "highlighter", COL_ORANGE, "반투명 형광펜 강조 (H)"),
            ("arrow",       "arrow",       COL_MAIN,   "화살표 그리기 (A)"),
            ("rect",        "rect",        COL_MAIN,   "사각형 박스 그리기 (R)"),
            ("text",        "text",        COL_MAIN,   "화면에 텍스트 입력 (T)"),
            ("eraser",      "eraser",      COL_MAIN,   "부분 지우개 (E)"),
        ]

        for t_key, icon_name, icon_col, desc in tools:
            is_active = (t_key == self.current_tool)
            ico = get_icon(icon_name, COL_ACTIVE if is_active else icon_col, ICO)
            btn = ctk.CTkButton(
                bg_frame, text="", image=ico,
                width=34, height=34,
                fg_color="#0284c7" if is_active else "transparent",
                hover_color="#0369a1",
                corner_radius=10,
                command=lambda k=t_key: self._select_tool(k)
            )
            btn.pack(side="left", padx=1)
            self.tool_btns[t_key] = btn
            attach_tooltip(btn, desc)

        _sep()

        # ── 색상 팔레트 ───────────────────────────────────────────────────
        self.color_btns = {}
        colors = [
            ("#ff3b30", "빨간색"), ("#ff9500", "주황색"),
            ("#ffd60a", "노란색"), ("#30d158", "초록색"),
            ("#0a84ff", "파란색"), ("#bf5af2", "보라색"),
            ("#ffffff",  "흰색"),
        ]
        for c_hex, c_name in colors:
            btn = ctk.CTkButton(
                bg_frame, text="",
                width=20, height=20, corner_radius=10,
                fg_color=c_hex, hover_color=c_hex,
                border_width=2 if c_hex == self.current_color else 0,
                border_color="#ffffff",
                command=lambda c=c_hex: self._select_color(c)
            )
            btn.pack(side="left", padx=1)
            self.color_btns[c_hex] = btn
            attach_tooltip(btn, f"펜 색상: {c_name}")

        _sep()

        # ── 굵기 (슬라이더처럼 보이는 3단 점 버튼) ───────────────────────
        widths = [(3, 6, "가는 펜 (3px)"), (6, 10, "보통 펜 (6px)"), (12, 14, "굵은 펜 (12px)")]
        for w_val, dot_sz, w_desc in widths:
            # 원 크기로 굵기를 시각화
            from PIL import Image as PILImage, ImageDraw as PILDraw
            dot_img = PILImage.new("RGBA", (22, 22), (0, 0, 0, 0))
            dd = PILDraw.Draw(dot_img)
            r = dot_sz // 2
            c = 11
            dd.ellipse([c-r, c-r, c+r, c+r], fill=(226, 232, 240, 255))
            import customtkinter as ctk2
            dot_ctk = ctk2.CTkImage(dot_img, dot_img, size=(22, 22))

            btn = ctk.CTkButton(
                bg_frame, text="", image=dot_ctk,
                width=26, height=26, corner_radius=8,
                fg_color="#1e293b", hover_color="#334155",
                command=lambda w=w_val: self._select_width(w)
            )
            btn.pack(side="left", padx=1)
            attach_tooltip(btn, f"펜 굵기: {w_desc}")

        _sep()

        # ── 배경 모드 전환 ────────────────────────────────────────────────
        self.board_btn = ctk.CTkButton(
            bg_frame, text="화면",
            font=get_font(10, "bold"),
            width=44, height=30,
            fg_color="#0284c7", hover_color="#0369a1",
            corner_radius=8,
            command=self._cycle_background_mode
        )
        self.board_btn.pack(side="left", padx=2)
        attach_tooltip(self.board_btn, "배경 전환: 현재 화면 ↔ 초록 칠판 ↔ 블랙보드")

        _sep()

        # ── 액션 버튼 (실행취소, 전체삭제, 캡처저장, 종료) ──────────────
        undo_btn = ctk.CTkButton(
            bg_frame, text="", image=get_icon("undo", COL_MAIN, ICO),
            width=32, height=30, fg_color="#334155", hover_color="#475569",
            corner_radius=8, command=self.undo
        )
        undo_btn.pack(side="left", padx=1)
        attach_tooltip(undo_btn, "실행 취소 (Ctrl+Z / 우클릭)")

        clear_btn = ctk.CTkButton(
            bg_frame, text="", image=get_icon("trash", COL_DANGER, ICO),
            width=32, height=30, fg_color="#7f1d1d", hover_color="#991b1b",
            corner_radius=8, command=self.clear_all
        )
        clear_btn.pack(side="left", padx=1)
        attach_tooltip(clear_btn, "화면 판서 전체 지우기")

        cap_btn = ctk.CTkButton(
            bg_frame, text="", image=get_icon("camera", COL_GREEN, ICO),
            width=32, height=30, fg_color="#064e3b", hover_color="#047857",
            corner_radius=8, command=self.save_screenshot
        )
        cap_btn.pack(side="left", padx=1)
        attach_tooltip(cap_btn, "판서 화면 캡처 저장 (PNG)")

        close_btn = ctk.CTkButton(
            bg_frame, text="종료", image=get_icon("close", COL_DANGER, ICO),
            font=get_font(10, "bold"),
            width=58, height=30,
            fg_color="#dc2626", hover_color="#b91c1c", text_color="#ffffff",
            corner_radius=8, compound="left",
            command=self.close
        )
        close_btn.pack(side="left", padx=(2, 6))
        attach_tooltip(close_btn, "판서 종료 — 일반 마우스 모드 복귀 (ESC)")

    def _cycle_background_mode(self):
        modes = ["screen", "greenboard", "blackboard"]
        cur_idx = modes.index(self.bg_mode) if self.bg_mode in modes else 0
        self.bg_mode = modes[(cur_idx + 1) % len(modes)]

        if self.bg_mode == "screen":
            self.canvas.configure(bg="#000000")
            if self.bg_item_id:
                self.canvas.itemconfigure(self.bg_item_id, state="normal")
            self.board_btn.configure(text="화면", fg_color="#0284c7")
        elif self.bg_mode == "greenboard":
            if self.bg_item_id:
                self.canvas.itemconfigure(self.bg_item_id, state="hidden")
            self.canvas.configure(bg="#1e3a2f")
            self.board_btn.configure(text="초록칠판", fg_color="#059669")
        elif self.bg_mode == "blackboard":
            if self.bg_item_id:
                self.canvas.itemconfigure(self.bg_item_id, state="hidden")
            self.canvas.configure(bg="#111827")
            self.board_btn.configure(text="블랙보드", fg_color="#374151")

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
        elif tool_key == "text":
            self.canvas.configure(cursor="xterm")
        else:
            self.canvas.configure(cursor="crosshair")

    def _on_mouse_down(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.last_x = event.x
        self.last_y = event.y
        self.current_stroke = []

        if self.current_tool == "eraser":
            self._erase_at(event.x, event.y)
        elif self.current_tool == "text":
            self._prompt_text_input(event.x, event.y)

    def _prompt_text_input(self, x, y):
        txt = simpledialog.askstring("텍스트 입력", "화면에 표시할 글자를 입력하세요:", parent=self.root)
        if txt:
            f_size = max(14, self.current_width * 5)
            item_id = self.canvas.create_text(
                x, y,
                text=txt,
                fill=self.current_color,
                font=("Malgun Gothic", f_size, "bold"),
                anchor="nw"
            )
            self.history.append(("single", item_id))

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
            # 배경 이미지는 지우지 않음
            if item != self.bg_item_id:
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
        # 배경 이미지만 남기고 판서 획만 삭제
        for item in self.canvas.find_all():
            if item != self.bg_item_id:
                self.canvas.delete(item)
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

