import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk, ImageGrab
from src.font_config import setup_global_fonts, get_font
from src.tooltip import attach_tooltip


class ScreenDrawingOverlay:
    """
    Alt+2: 현재 화면 위 자유 판서 오버레이 (선생님 전용 고도화 판서 시스템)
    - 단축키 색상 즉시 변경: R(빨강), B(파랑), P(분홍), Y(노랑), G(녹색)
    - T: 텍스트 모드 (Shift+Enter 줄바꿈, Enter 글상자 완성)
    - 완성된 글상자: 마우스 선택 후 자유 이동, 우하단 드래그 크기 조절, Delete 키로 삭제
    - ESC 2단계: 텍스트 모드 중엔 펜 모드 복귀, 일반 상태에선 판서 종료
    - 배경 전환: F1(현재 화면), F2(흰 화면 화이트보드), F3(초록 분필 칠판)
    """
    _instance = None

    @classmethod
    def get_instance(cls, parent=None):
        if cls._instance is None:
            cls._instance = cls(parent)
        return cls._instance

    @classmethod
    def toggle(cls, parent=None):
        inst = cls.get_instance(parent)
        if inst.is_active:
            inst.close()
        else:
            inst.show()

    def __init__(self, parent=None):
        self.parent = parent
        self.is_active = False
        self.root = None
        self.canvas = None
        self.toolbar = None

        # 그리기 상태
        self.current_tool = "pen"  # pen, highlighter, arrow, rect, text, emoji_stamp, eraser
        self.current_color = "#ef4444"  # 기본 빨강
        self.current_width = 4
        self.bg_mode = "screen"  # screen (현재화면), whiteboard (흰화면), greenboard (초록칠판)

        # 히스토리 (실행취소용)
        self.history = []
        self.current_stroke = []

        # 텍스트 박스 관리
        self.text_boxes = []  # list of dict
        self.active_text_entry = None
        self.selected_text_box = None
        self._tb_drag_start_x = 0
        self._tb_drag_start_y = 0
        self._tb_resize_mode = False

        # 마우스 좌표 추적
        self.start_x = 0
        self.start_y = 0
        self.last_x = 0
        self.last_y = 0
        self.temp_shape_id = None
        self.bg_item_id = None
        self.bg_photo = None

    def show(self):
        if self.is_active:
            return
        self.is_active = True

        # 1. 화면 캡처
        try:
            screen_img = ImageGrab.grab()
        except Exception:
            screen_img = None

        self.root = tk.Toplevel()
        self.root.title("놀티쳐 판서 오버레이")
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#000000")

        # 2. 캔버스
        self.canvas = tk.Canvas(self.root, bg="#000000", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        if screen_img:
            self.bg_photo = ImageTk.PhotoImage(screen_img)
            self.bg_item_id = self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw", tags="bg_layer")
        else:
            self.bg_item_id = None

        # 마우스 바인딩
        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Button-3>", lambda e: self.undo())

        # 전역 단축키 바인딩
        self.root.bind("<Escape>", self._on_escape)
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-Z>", lambda e: self.undo())
        self.root.bind("<Delete>", lambda e: self._delete_selected_text_box())
        self.root.bind("<BackSpace>", lambda e: self._delete_selected_text_box())

        # 색상 단축키: R(빨강), B(파랑), P(분홍), Y(노랑), G(녹색)
        for k, col in [("r", "#ef4444"), ("R", "#ef4444"),
                       ("b", "#3b82f6"), ("B", "#3b82f6"),
                       ("p", "#ec4899"), ("P", "#ec4899"),
                       ("y", "#eab308"), ("Y", "#eab308"),
                       ("g", "#22c55e"), ("G", "#22c55e"),
                       ("w", "#ffffff"), ("W", "#ffffff")]:
            self.root.bind(f"<{k}>", lambda e, c=col: self._select_color(c))

        # 배경 모드 단축키: F1(현재화면), F2(흰화면 화이트보드), F3(초록칠판)
        self.root.bind("<F1>", lambda e: self._set_background_mode("screen"))
        self.root.bind("<F2>", lambda e: self._set_background_mode("whiteboard"))
        self.root.bind("<F3>", lambda e: self._set_background_mode("greenboard"))

        # 도구 단축키
        self.root.bind("<t>", lambda e: self._select_tool("text"))
        self.root.bind("<T>", lambda e: self._select_tool("text"))
        self.root.bind("<h>", lambda e: self._select_tool("highlighter"))
        self.root.bind("<H>", lambda e: self._select_tool("highlighter"))
        self.root.bind("<a>", lambda e: self._select_tool("arrow"))
        self.root.bind("<A>", lambda e: self._select_tool("arrow"))
        self.root.bind("<e>", lambda e: self._select_tool("eraser"))
        self.root.bind("<E>", lambda e: self._select_tool("eraser"))

        self._build_toolbar()
        self.root.lift()
        self.root.focus_force()

    def _build_toolbar(self):
        sw = self.root.winfo_screenwidth()
        tb_w = 720
        tb_h = 56
        tb_x = (sw - tb_w) // 2
        tb_y = 20

        self.toolbar = tk.Toplevel(self.root)
        self.toolbar.title("판서 도구함")
        self.toolbar.geometry(f"{tb_w}x{tb_h}+{tb_x}+{tb_y}")
        self.toolbar.overrideredirect(True)
        self.toolbar.attributes("-topmost", True)

        bg_frame = ctk.CTkFrame(self.toolbar, fg_color="#090d16", corner_radius=20, border_width=1, border_color="#0284c7")
        bg_frame.pack(fill="both", expand=True, padx=1, pady=1)

        from src.icon_renderer import get_icon, COL_MAIN, COL_ACTIVE, COL_DANGER, COL_GREEN, COL_ORANGE, COL_YELLOW
        ICO = 22

        # 드래그 핸들
        drag_lbl = ctk.CTkLabel(bg_frame, text="", image=get_icon("drag", "#475569", ICO), width=20, cursor="fleur")
        drag_lbl.pack(side="left", padx=(8, 2))
        drag_lbl.bind("<Button-1>", self._start_toolbar_drag)
        drag_lbl.bind("<B1-Motion>", self._on_toolbar_drag)

        def _sep():
            ctk.CTkFrame(bg_frame, width=1, height=24, fg_color="#334155").pack(side="left", padx=3)

        # 도구 선택 버튼들
        self.tool_btns = {}
        tools = [
            ("pen",         "pen",         COL_MAIN,   "일반 펜 (P)"),
            ("highlighter", "highlighter", COL_YELLOW, "형광펜 (H)"),
            ("arrow",       "arrow",       COL_MAIN,   "화살표 (A)"),
            ("rect",        "rect",        COL_MAIN,   "사각형 (R)"),
            ("text",        "text",        COL_MAIN,   "텍스트 글상자 (T)"),
            ("emoji_stamp", "emoji_stamp", COL_YELLOW, "스마일 스탬프 (S)"),
            ("eraser",      "eraser",      COL_MAIN,   "부분 지우개 (E)"),
        ]
        for t_key, icon_name, icon_col, desc in tools:
            is_active = (t_key == self.current_tool)
            ico = get_icon(icon_name, COL_ACTIVE if is_active else icon_col, ICO)
            btn = ctk.CTkButton(
                bg_frame, text="", image=ico, width=34, height=34,
                fg_color="#0284c7" if is_active else "transparent",
                hover_color="#0369a1", corner_radius=10,
                command=lambda k=t_key: self._select_tool(k)
            )
            btn.pack(side="left", padx=1)
            self.tool_btns[t_key] = btn
            attach_tooltip(btn, desc)

        _sep()

        # 색상 팔레트 (R, B, P, Y, G + W)
        self.color_btns = {}
        colors = [
            ("#ef4444", "빨강 (R)"),
            ("#3b82f6", "파랑 (B)"),
            ("#ec4899", "분홍 (P)"),
            ("#eab308", "노랑 (Y)"),
            ("#22c55e", "녹색 (G)"),
            ("#ffffff", "흰색 (W)"),
        ]
        for c_hex, c_name in colors:
            btn = ctk.CTkButton(
                bg_frame, text="", width=20, height=20, corner_radius=10,
                fg_color=c_hex, hover_color=c_hex,
                border_width=2 if c_hex == self.current_color else 0,
                border_color="#ffffff",
                command=lambda c=c_hex: self._select_color(c)
            )
            btn.pack(side="left", padx=1)
            self.color_btns[c_hex] = btn
            attach_tooltip(btn, f"색상: {c_name}")

        _sep()

        # 펜 굵기 (소/중/대)
        widths = [(3, 6, "가는 펜"), (6, 10, "보통 펜"), (12, 14, "굵은 펜")]
        for w_val, dot_sz, w_desc in widths:
            dot_img = Image.new("RGBA", (22, 22), (0, 0, 0, 0))
            import PIL.ImageDraw as PD
            dd = PD.Draw(dot_img)
            r = dot_sz // 2
            dd.ellipse([11-r, 11-r, 11+r, 11+r], fill=(226, 232, 240, 255))
            dot_ctk = ctk.CTkImage(dot_img, dot_img, size=(22, 22))

            btn = ctk.CTkButton(
                bg_frame, text="", image=dot_ctk, width=26, height=26,
                corner_radius=8, fg_color="#1e293b", hover_color="#334155",
                command=lambda w=w_val: self._select_width(w)
            )
            btn.pack(side="left", padx=1)
            attach_tooltip(btn, f"펜 굵기: {w_desc}")

        _sep()

        # 배경 모드 전환 (화면 F1 / 화이트보드 F2 / 칠판 F3)
        self.board_btn = ctk.CTkButton(
            bg_frame, text="화면(F1)", font=get_font(10, "bold"),
            width=62, height=30, fg_color="#0284c7", hover_color="#0369a1",
            corner_radius=8, command=self._cycle_background_mode
        )
        self.board_btn.pack(side="left", padx=2)
        attach_tooltip(self.board_btn, "배경 전환: 화면(F1) ↔ 화이트보드(F2) ↔ 칠판(F3)")

        _sep()

        # 실행취소, 삭제, 캡처, 종료
        undo_btn = ctk.CTkButton(
            bg_frame, text="", image=get_icon("undo", COL_MAIN, ICO),
            width=32, height=30, fg_color="#334155", hover_color="#475569",
            corner_radius=8, command=self.undo
        )
        undo_btn.pack(side="left", padx=1)
        attach_tooltip(undo_btn, "실행 취소 (Ctrl+Z / 마우스 우클릭)")

        clear_btn = ctk.CTkButton(
            bg_frame, text="", image=get_icon("trash", COL_DANGER, ICO),
            width=32, height=30, fg_color="#7f1d1d", hover_color="#991b1b",
            corner_radius=8, command=self.clear_all
        )
        clear_btn.pack(side="left", padx=1)
        attach_tooltip(clear_btn, "전체 판서 지우기")

        cap_btn = ctk.CTkButton(
            bg_frame, text="", image=get_icon("camera", COL_GREEN, ICO),
            width=32, height=30, fg_color="#064e3b", hover_color="#047857",
            corner_radius=8, command=self.save_screenshot
        )
        cap_btn.pack(side="left", padx=1)
        attach_tooltip(cap_btn, "판서 화면 캡처 저장")

        close_btn = ctk.CTkButton(
            bg_frame, text="종료", image=get_icon("close", COL_DANGER, ICO),
            font=get_font(10, "bold"), width=58, height=30,
            fg_color="#dc2626", hover_color="#b91c1c", text_color="#ffffff",
            corner_radius=8, compound="left", command=self.close
        )
        close_btn.pack(side="left", padx=(2, 6))
        attach_tooltip(close_btn, "판서 종료 (ESC)")

    # ─── 배경 전환 (F1, F2, F3) ───────────────────────────────────────────
    def _set_background_mode(self, mode: str):
        self.bg_mode = mode
        if mode == "screen":
            self.canvas.configure(bg="#000000")
            if self.bg_item_id:
                self.canvas.itemconfigure(self.bg_item_id, state="normal")
            if hasattr(self, "board_btn"):
                self.board_btn.configure(text="화면(F1)", fg_color="#0284c7")
        elif mode == "whiteboard":
            if self.bg_item_id:
                self.canvas.itemconfigure(self.bg_item_id, state="hidden")
            self.canvas.configure(bg="#ffffff")
            if hasattr(self, "board_btn"):
                self.board_btn.configure(text="화이트(F2)", fg_color="#475569")
        elif mode == "greenboard":
            if self.bg_item_id:
                self.canvas.itemconfigure(self.bg_item_id, state="hidden")
            self.canvas.configure(bg="#1e3a2f")
            if hasattr(self, "board_btn"):
                self.board_btn.configure(text="칠판(F3)", fg_color="#059669")

    def _cycle_background_mode(self):
        modes = ["screen", "whiteboard", "greenboard"]
        cur_idx = modes.index(self.bg_mode) if self.bg_mode in modes else 0
        next_mode = modes[(cur_idx + 1) % len(modes)]
        self._set_background_mode(next_mode)

    # ─── 색상 & 도구 선택 ─────────────────────────────────────────────────
    def _select_color(self, hex_code: str):
        self.current_color = hex_code
        for c, btn in getattr(self, "color_btns", {}).items():
            btn.configure(border_width=2 if c == hex_code else 0)

    def _select_tool(self, tool_key: str):
        # 활성 인라인 텍스트가 있다면 확정
        if self.active_text_entry:
            self._finalize_text_box()

        self.current_tool = tool_key
        for k, btn in getattr(self, "tool_btns", {}).items():
            btn.configure(fg_color="#0284c7" if k == tool_key else "transparent")

        if tool_key == "eraser":
            self.canvas.configure(cursor="circle")
        elif tool_key == "text":
            self.canvas.configure(cursor="xterm")
        else:
            self.canvas.configure(cursor="crosshair")

    def _select_width(self, w: int):
        self.current_width = w

    def _start_toolbar_drag(self, event):
        self._tb_drag_x = event.x
        self._tb_drag_y = event.y

    def _on_toolbar_drag(self, event):
        dx = event.x - self._tb_drag_x
        dy = event.y - self._tb_drag_y
        x = self.toolbar.winfo_x() + dx
        y = self.toolbar.winfo_y() + dy
        self.toolbar.geometry(f"+{x}+{y}")

    # ─── 마우스 이벤트 & 도구별 그리기 ────────────────────────────────────
    def _on_mouse_down(self, event):
        # 1. 기존 완성된 글상자 클릭 체크 (선택/이동/리사이즈)
        clicked_box, is_resize = self._hit_test_text_box(event.x, event.y)
        if clicked_box:
            self._select_text_box(clicked_box)
            self._tb_drag_start_x = event.x
            self._tb_drag_start_y = event.y
            self._tb_resize_mode = is_resize
            return
        else:
            self._deselect_text_box()

        # 2. 인라인 텍스트 입력 중 다른 곳 클릭 시 이전 텍스트 완성
        if self.active_text_entry:
            self._finalize_text_box()

        self.start_x = event.x
        self.start_y = event.y
        self.last_x = event.x
        self.last_y = event.y
        self.current_stroke = []

        if self.current_tool == "eraser":
            self._erase_at(event.x, event.y)
        elif self.current_tool == "text":
            self._start_inline_text_input(event.x, event.y)
        elif self.current_tool == "emoji_stamp":
            self._place_emoji_stamp(event.x, event.y)

    def _on_mouse_move(self, event):
        # 글상자 이동 또는 크기조절 중인 경우
        if self.selected_text_box and hasattr(self, "_tb_drag_start_x"):
            dx = event.x - self._tb_drag_start_x
            dy = event.y - self._tb_drag_start_y
            if self._tb_resize_mode:
                self._resize_selected_text_box(dx, dy)
            else:
                self._move_selected_text_box(dx, dy)
            self._tb_drag_start_x = event.x
            self._tb_drag_start_y = event.y
            return

        if self.current_tool == "pen":
            item_id = self.canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                fill=self.current_color, width=self.current_width,
                capstyle=tk.ROUND, joinstyle=tk.ROUND, smooth=True
            )
            self.current_stroke.append(item_id)
            self.last_x = event.x
            self.last_y = event.y

        elif self.current_tool == "highlighter":
            item_id = self.canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                fill=self.current_color, width=self.current_width * 3,
                capstyle=tk.ROUND, joinstyle=tk.ROUND, stipple="gray50", smooth=True
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
                fill=self.current_color, width=self.current_width,
                arrow=tk.LAST, arrowshape=(16, 20, 6)
            )

        elif self.current_tool == "rect":
            if self.temp_shape_id:
                self.canvas.delete(self.temp_shape_id)
            self.temp_shape_id = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline=self.current_color, width=self.current_width
            )

    def _on_mouse_up(self, event):
        if self.selected_text_box:
            self._tb_resize_mode = False
            return

        if self.current_stroke:
            self.history.append(("stroke", self.current_stroke))
            self.current_stroke = []

        if self.temp_shape_id:
            self.history.append(("single", self.temp_shape_id))
            self.temp_shape_id = None

    # ─── 텍스트 글상자 시스템 (T, Shift+Enter, Enter, 이동/크기조절/삭제) ───
    def _start_inline_text_input(self, x, y):
        """클릭 위치에 인라인 텍스트 에디터 생성"""
        f_size = max(14, self.current_width * 5)

        # 텍스트 에디터 프레임
        entry_frame = tk.Frame(self.canvas, bg="#111827", bd=1, relief="solid")
        text_w = tk.Text(
            entry_frame, font=("Malgun Gothic", f_size, "bold"),
            fg=self.current_color, bg="#111827",
            insertbackground="#ffffff", width=20, height=2,
            bd=0, highlightthickness=0
        )
        text_w.pack(padx=4, pady=4)

        win_id = self.canvas.create_window(x, y, window=entry_frame, anchor="nw")

        self.active_text_entry = {
            "frame": entry_frame,
            "text_w": text_w,
            "win_id": win_id,
            "x": x, "y": y,
            "font_size": f_size,
            "color": self.current_color
        }

        # 바인딩: Shift+Enter 줄바꿈, Enter 글상자 완성, ESC 취소
        text_w.bind("<Shift-Return>", lambda e: None)  # 기본 줄바꿈 허용
        text_w.bind("<Return>", self._on_enter_pressed)
        text_w.bind("<Escape>", lambda e: self._cancel_inline_text())

        text_w.focus_set()

    def _on_enter_pressed(self, event):
        # Shift가 안 눌린 순수 Enter인 경우 글상자 완성
        if not (event.state & 0x0001):
            self._finalize_text_box()
            return "break"
        return None

    def _finalize_text_box(self):
        """인라인 입력을 완료하고 선택/이동/리사이즈 가능한 글상자로 캔버스에 등록"""
        if not self.active_text_entry:
            return

        info = self.active_text_entry
        content = info["text_w"].get("1.0", "end-1c").strip()
        x, y = info["x"], info["y"]
        f_size = info["font_size"]
        color = info["color"]

        # 에디터 위젯 제거
        self.canvas.delete(info["win_id"])
        info["frame"].destroy()
        self.active_text_entry = None

        if not content:
            return

        # 캔버스에 텍스트 아이템 생성
        t_id = self.canvas.create_text(
            x, y, text=content,
            font=("Malgun Gothic", f_size, "bold"),
            fill=color, anchor="nw"
        )
        bbox = self.canvas.bbox(t_id)  # (x0, y0, x1, y1)

        # 글상자 객체 등록
        box_data = {
            "text_id": t_id,
            "content": content,
            "x": x, "y": y,
            "font_size": f_size,
            "color": color,
            "box_id": None,
            "handle_id": None
        }
        self.text_boxes.append(box_data)
        self.history.append(("text_box", box_data))
        self._select_text_box(box_data)

    def _cancel_inline_text(self):
        if self.active_text_entry:
            self.canvas.delete(self.active_text_entry["win_id"])
            self.active_text_entry["frame"].destroy()
            self.active_text_entry = None
        self._select_tool("pen")

    def _select_text_box(self, box_data):
        self._deselect_text_box()
        self.selected_text_box = box_data

        # 선택 점선 테두리 및 우하단 리사이즈 핸들 그리기
        bbox = self.canvas.bbox(box_data["text_id"])
        if bbox:
            x0, y0, x1, y1 = bbox
            pad = 4
            box_data["box_id"] = self.canvas.create_rectangle(
                x0 - pad, y0 - pad, x1 + pad, y1 + pad,
                outline="#38bdf8", width=1, dash=(4, 2)
            )
            box_data["handle_id"] = self.canvas.create_rectangle(
                x1 + pad - 6, y1 + pad - 6, x1 + pad + 2, y1 + pad + 2,
                fill="#38bdf8", outline="#ffffff"
            )

    def _deselect_text_box(self):
        if self.selected_text_box:
            b = self.selected_text_box
            if b.get("box_id"):
                self.canvas.delete(b["box_id"])
                b["box_id"] = None
            if b.get("handle_id"):
                self.canvas.delete(b["handle_id"])
                b["handle_id"] = None
            self.selected_text_box = None

    def _hit_test_text_box(self, x, y):
        """글상자 본체 및 리사이즈 핸들 클릭 여부 검사 (box, is_resize)"""
        for b in reversed(self.text_boxes):
            bbox = self.canvas.bbox(b["text_id"])
            if bbox:
                x0, y0, x1, y1 = bbox
                # 리사이즈 핸들 영역 (우측 하단)
                if abs(x - (x1 + 4)) <= 10 and abs(y - (y1 + 4)) <= 10:
                    return b, True
                # 글상자 내부 영역
                if x0 - 6 <= x <= x1 + 6 and y0 - 6 <= y <= y1 + 6:
                    return b, False
        return None, False

    def _move_selected_text_box(self, dx, dy):
        if not self.selected_text_box:
            return
        b = self.selected_text_box
        self.canvas.move(b["text_id"], dx, dy)
        if b.get("box_id"):
            self.canvas.move(b["box_id"], dx, dy)
        if b.get("handle_id"):
            self.canvas.move(b["handle_id"], dx, dy)
        b["x"] += dx
        b["y"] += dy

    def _resize_selected_text_box(self, dx, dy):
        if not self.selected_text_box:
            return
        b = self.selected_text_box
        # 가로/세로 확장에 맞춰 폰트 크기 동적 조절
        delta_sz = int((dx + dy) / 10)
        new_sz = max(10, min(72, b["font_size"] + delta_sz))
        if new_sz != b["font_size"]:
            b["font_size"] = new_sz
            self.canvas.itemconfigure(b["text_id"], font=("Malgun Gothic", new_sz, "bold"))
            # 테두리 업데이트
            self._select_text_box(b)

    def _delete_selected_text_box(self):
        if self.selected_text_box:
            b = self.selected_text_box
            self.canvas.delete(b["text_id"])
            if b.get("box_id"):
                self.canvas.delete(b["box_id"])
            if b.get("handle_id"):
                self.canvas.delete(b["handle_id"])
            if b in self.text_boxes:
                self.text_boxes.remove(b)
            self.selected_text_box = None

    # ─── ESC 2단계 처리 ───────────────────────────────────────────────────
    def _on_escape(self, event):
        """텍스트 모드/글상자 선택 중이면 펜으로 복귀, 일반 상태면 판서 종료"""
        if self.active_text_entry:
            self._cancel_inline_text()
            return
        if self.selected_text_box:
            self._deselect_text_box()
            return
        if self.current_tool == "text":
            self._select_tool("pen")
            return
        self.close()

    # ─── 기타 도구 ────────────────────────────────────────────────────────
    def _place_emoji_stamp(self, x, y):
        emojis = ["😊", "⭐", "👍", "🔥", "💡", "❓", "‼️", "✅"]
        if not hasattr(self, "_emoji_idx"):
            self._emoji_idx = 0
        emoji = emojis[self._emoji_idx % len(emojis)]
        self._emoji_idx += 1
        sz = max(24, self.current_width * 7)
        item_id = self.canvas.create_text(x, y, text=emoji, font=("Segoe UI Emoji", sz), anchor="center")
        self.history.append(("single", item_id))

    def _erase_at(self, x, y):
        r = 16
        items = self.canvas.find_overlapping(x - r, y - r, x + r, y + r)
        for item in items:
            if item != self.bg_item_id:
                self.canvas.delete(item)

    def undo(self):
        if not self.history:
            return
        h_type, item = self.history.pop()
        if h_type == "stroke":
            for i in item:
                self.canvas.delete(i)
        elif h_type == "single":
            self.canvas.delete(item)
        elif h_type == "text_box":
            self.canvas.delete(item["text_id"])
            if item in self.text_boxes:
                self.text_boxes.remove(item)
            self._deselect_text_box()

    def clear_all(self):
        for item in self.canvas.find_all():
            if item != self.bg_item_id:
                self.canvas.delete(item)
        self.history.clear()
        self.text_boxes.clear()
        self.selected_text_box = None

    def save_screenshot(self):
        import datetime
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title="판서 화면 저장",
            initialfile=f"놀티쳐_판서_{now_str}.png",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")]
        )
        if not path:
            return
        try:
            if self.toolbar and self.toolbar.winfo_exists():
                self.toolbar.withdraw()
            self.root.update()
            img = ImageGrab.grab()
            img.save(path)
            if self.toolbar and self.toolbar.winfo_exists():
                self.toolbar.deiconify()
            messagebox.showinfo("저장 완료", f"판서 화면이 저장되었습니다:\n{path}")
        except Exception as e:
            messagebox.showerror("저장 실패", f"오류 발생: {e}")

    def close(self):
        if not self.is_active:
            return
        self.is_active = False
        if self.toolbar and self.toolbar.winfo_exists():
            self.toolbar.destroy()
        if self.root and self.root.winfo_exists():
            self.root.destroy()
        self.root = None
        self.canvas = None
        self.toolbar = None
