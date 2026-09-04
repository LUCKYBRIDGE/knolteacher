"""
알람 화면 시각적 커스텀 디자이너 (AlarmCustomDesignerDialog)
- 실제 화면과 100% 동일한 WYSIWYG 캔버스 에디터에서 요소를 직접 드래그하여 배치
- 안내 메시지 문구 직접 수정, 타이머 위치/크기/색상 조정, 스티커/이미지 삽입/삭제
- 테마 색상, 창 크기, 모니터 위치 프리셋 설정
- [실제 화면 미리보기 팝업] 및 영구 저장 지원
"""
import os
import copy
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

from src.font_config import get_font
from src.theme_manager import theme_manager
from src.alarm_design_manager import alarm_design_manager
from src.monitor_utils import get_system_monitors

STICKER_PRESETS = ["📚", "⏰", "⭐", "💖", "👟", "🥛", "🧹", "🥕", "✏️", "🔔"]

THEME_PRESETS = [
    {"name": "🌙 다크 네이비", "bg": "#0f172a", "border": "#38bdf8", "accent": "#38bdf8", "text": "#ffffff", "sub": "#94a3b8"},
    {"name": "🏫 초록 칠판",   "bg": "#14291e", "border": "#4ade80", "accent": "#4ade80", "text": "#f0fdf4", "sub": "#86efac"},
    {"name": "📄 깔끔 화이트", "bg": "#ffffff", "border": "#0284c7", "accent": "#0284c7", "text": "#0f172a", "sub": "#64748b"},
    {"name": "🌾 따뜻 베이지", "bg": "#fdfbf7", "border": "#d97706", "accent": "#d97706", "text": "#292524", "sub": "#78716c"},
]


class AlarmCustomDesignerDialog(ctk.CTkToplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.title("알람 화면 시각적 디자인 커스텀")
        self.geometry("960x720")
        self.minsize(860, 620)
        self.attributes("-topmost", True)

        # 현재 작업 중인 디자인 복사본
        self.cfg = copy.deepcopy(alarm_design_manager.config)
        self.selected_key = "timer"  # 기본 선택
        self._drag_start_x = 0
        self._drag_start_y = 0

        self._build_ui()
        self._redraw_canvas()

    def _build_ui(self):
        palette = theme_manager.get_theme()
        self.configure(fg_color=palette["card_bg"])

        main_box = ctk.CTkFrame(self, fg_color=palette["card_bg"], corner_radius=0)
        main_box.pack(fill="both", expand=True, padx=12, pady=12)

        # 1. 상단 타이틀 바
        hdr = ctk.CTkFrame(main_box, fg_color="transparent")
        hdr.pack(fill="x", padx=6, pady=(4, 8))

        ctk.CTkLabel(
            hdr, text="🎨 알람 화면 시각적 디자인 커스텀 에디터",
            font=get_font(15, "bold"), text_color=palette["accent"]
        ).pack(side="left")

        # 2. 메인 바디 (좌측: 인터랙티브 캔버스 에디터 / 우측: 속성 편집 제어판)
        body = ctk.CTkFrame(main_box, fg_color="transparent")
        body.pack(fill="both", expand=True, pady=4)

        # [좌측] 인터랙티브 WYSIWYG 캔버스 에디터 영역
        left_area = ctk.CTkFrame(body, fg_color=palette["card_inner_bg"], corner_radius=12, border_width=1, border_color=palette["card_border"])
        left_area.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=2)

        l_hdr = ctk.CTkFrame(left_area, fg_color="transparent")
        l_hdr.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(l_hdr, text="🖱️ 실시간 화면 배치 (요소를 직접 마우스로 드래그하여 이동하세요)", font=get_font(11, "bold"), text_color=palette["text_main"]).pack(side="left")

        # 작업대 캔버스 컨테이너
        self.preview_workplace = ctk.CTkFrame(left_area, fg_color="#000000", corner_radius=8)
        self.preview_workplace.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        self.canvas = tk.Canvas(self.preview_workplace, bg="#0b0f19", highlightthickness=0, cursor="hand2")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)

        # [우측] 속성 편집 제어판 (스크롤)
        right_panel = ctk.CTkScrollableFrame(body, width=350, fg_color=palette["card_inner_bg"], corner_radius=12, border_width=1, border_color=palette["card_border"])
        right_panel.pack(side="right", fill="both", padx=(4, 0), pady=2)

        self._build_properties_panel(right_panel, palette)

        # 3. 하단 액션 바
        b_bar = ctk.CTkFrame(main_box, fg_color="transparent")
        b_bar.pack(fill="x", padx=6, pady=(10, 4))

        ctk.CTkButton(
            b_bar, text="🔔 실제 화면 미리보기 테스트", font=get_font(11, "bold"), height=36,
            fg_color="#ea580c", hover_color="#c2410c", text_color="#ffffff",
            command=self._test_popup
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            b_bar, text="↺ 기본값 복원", font=get_font(10, "bold"), height=36, width=100,
            fg_color=palette["sidebar_btn_hover"], hover_color=palette["card_border"],
            text_color=palette["text_sub"], command=self._reset_defaults
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            b_bar, text="닫기", font=get_font(11, "bold"), height=36, width=80,
            fg_color=palette["card_inner_bg"], hover_color=palette["sidebar_btn_hover"],
            text_color=palette["text_main"], command=self.destroy
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            b_bar, text="💾 설정 저장 & 알람에 즉시 적용", font=get_font(12, "bold"), height=36,
            fg_color=palette["accent"], hover_color=palette["accent_hover"], text_color="#ffffff",
            command=self._save_design
        ).pack(side="right", padx=4)

    # =========================================================================
    # 우측 속성 편집 제어판
    # =========================================================================
    def _build_properties_panel(self, parent, palette):
        # 1) 테마 프리셋
        ctk.CTkLabel(parent, text="🎨 알람 창 테마 색상", font=get_font(11, "bold"), text_color=palette["accent"]).pack(anchor="w", padx=4, pady=(6, 2))
        theme_row = ctk.CTkFrame(parent, fg_color="transparent")
        theme_row.pack(fill="x", padx=4, pady=(0, 8))

        for th in THEME_PRESETS:
            ctk.CTkButton(
                theme_row, text=th["name"], font=get_font(9, "bold"), height=26,
                fg_color=th["bg"], hover_color=th["border"], text_color=th["text"],
                border_width=1, border_color=th["border"],
                command=lambda t=th: self._apply_theme(t)
            ).pack(side="left", fill="x", expand=True, padx=1)

        # 2) 알람 창 전체 크기 조절
        ctk.CTkLabel(parent, text="📐 알람 창 크기 조절", font=get_font(11, "bold"), text_color=palette["accent"]).pack(anchor="w", padx=4, pady=(6, 2))
        sz_box = ctk.CTkFrame(parent, fg_color="transparent")
        sz_box.pack(fill="x", padx=4, pady=(0, 8))

        ctk.CTkLabel(sz_box, text=f"가로: {self.cfg['window_width']}px", font=get_font(9, "bold"), text_color=palette["text_sub"]).pack(side="left", padx=2)
        ctk.CTkButton(sz_box, text="-20", width=36, height=22, font=get_font(8, "bold"), command=lambda: self._adj_size(-20, 0)).pack(side="left", padx=1)
        ctk.CTkButton(sz_box, text="+20", width=36, height=22, font=get_font(8, "bold"), command=lambda: self._adj_size(20, 0)).pack(side="left", padx=1)

        ctk.CTkLabel(sz_box, text=f" 세로: {self.cfg['window_height']}px", font=get_font(9, "bold"), text_color=palette["text_sub"]).pack(side="left", padx=2)
        ctk.CTkButton(sz_box, text="-20", width=36, height=22, font=get_font(8, "bold"), command=lambda: self._adj_size(0, -20)).pack(side="left", padx=1)
        ctk.CTkButton(sz_box, text="+20", width=36, height=22, font=get_font(8, "bold"), command=lambda: self._adj_size(0, 20)).pack(side="left", padx=1)

        # 3) 화면 출력 위치 프리셋
        ctk.CTkLabel(parent, text="🖥️ 알람 화면 팝업 위치", font=get_font(11, "bold"), text_color=palette["accent"]).pack(anchor="w", padx=4, pady=(6, 2))
        pos_seg = ctk.CTkSegmentedButton(
            parent, values=["↗️ 우상단", "🎯 중앙", "⬇️ 하단중앙"], font=get_font(9, "bold"), height=26,
            command=self._on_pos_mode_changed
        )
        mode_map = {"top_right": "↗️ 우상단", "center": "🎯 중앙", "bottom_center": "⬇️ 하단중앙"}
        pos_seg.set(mode_map.get(self.cfg.get("position_mode", "top_right"), "↗️ 우상단"))
        pos_seg.pack(fill="x", padx=4, pady=(0, 8))

        # 모니터 선택
        mon_list = get_system_monitors()
        mon_opts = [f"모니터 {m['index']+1} ({m['width']}x{m['height']})" for m in mon_list]
        m_combo = ctk.CTkComboBox(
            parent, values=mon_opts, height=26, font=get_font(9, "bold"), state="readonly",
            command=lambda v: self._on_monitor_changed(v, mon_list)
        )
        cur_m_idx = min(self.cfg.get("monitor_index", 0), len(mon_opts)-1)
        if mon_opts:
            m_combo.set(mon_opts[cur_m_idx])
        m_combo.pack(fill="x", padx=4, pady=(0, 10))

        ctk.CTkFrame(parent, height=1, fg_color=palette["card_border"]).pack(fill="x", padx=4, pady=6)

        # 4) 선택된 요소 편집 영역
        self.elem_edit_box = ctk.CTkFrame(parent, fg_color="transparent")
        self.elem_edit_box.pack(fill="both", expand=True, padx=4, pady=4)
        self._refresh_element_editor(palette)

    def _refresh_element_editor(self, palette):
        for w in self.elem_edit_box.winfo_children():
            w.destroy()

        elem = self.cfg["elements"].get(self.selected_key, {})
        key_names = {
            "title": "🔔 수업 교시명",
            "timer": "⏱️ 타이머 숫자",
            "message": "📝 선생님 맞춤 안내 문구",
            "sub_notice": "💡 보조 안내 문구",
            "sticker": "🖼️ 캐릭터 / 스티커"
        }

        ctk.CTkLabel(
            self.elem_edit_box, text=f"선택 요소: {key_names.get(self.selected_key, self.selected_key)}",
            font=get_font(12, "bold"), text_color=palette["accent"]
        ).pack(anchor="w", pady=(0, 4))

        # 표시 여부 토글
        vis_var = ctk.BooleanVar(value=elem.get("visible", True))
        def _toggle_vis():
            elem["visible"] = vis_var.get()
            self._redraw_canvas()
        ctk.CTkCheckBox(self.elem_edit_box, text="화면에 표시하기", variable=vis_var, font=get_font(10, "bold"), command=_toggle_vis).pack(anchor="w", pady=3)

        # 텍스트 내용 수정 (title, message, sub_notice)
        if "text" in elem:
            ctk.CTkLabel(self.elem_edit_box, text="문구 내용 입력:", font=get_font(9, "bold"), text_color=palette["text_sub"]).pack(anchor="w", pady=(6, 1))
            txt_entry = ctk.CTkEntry(self.elem_edit_box, font=get_font(10), height=28)
            txt_entry.insert(0, elem["text"])
            txt_entry.pack(fill="x", pady=(0, 4))
            def _update_txt(e=None):
                elem["text"] = txt_entry.get()
                self._redraw_canvas()
            txt_entry.bind("<KeyRelease>", _update_txt)

        # 글꼴 크기 조절
        if "font_size" in elem:
            sz_row = ctk.CTkFrame(self.elem_edit_box, fg_color="transparent")
            sz_row.pack(fill="x", pady=4)
            ctk.CTkLabel(sz_row, text=f"글자 크기: {elem['font_size']}pt", font=get_font(9, "bold"), text_color=palette["text_sub"]).pack(side="left")
            ctk.CTkButton(sz_row, text="-4", width=36, height=22, font=get_font(8, "bold"), command=lambda: self._adj_font_size(-4)).pack(side="left", padx=2)
            ctk.CTkButton(sz_row, text="+4", width=36, height=22, font=get_font(8, "bold"), command=lambda: self._adj_font_size(4)).pack(side="left", padx=2)

        # 색상 선택
        if "color" in elem:
            ctk.CTkLabel(self.elem_edit_box, text="글자 색상 선택:", font=get_font(9, "bold"), text_color=palette["text_sub"]).pack(anchor="w", pady=(6, 1))
            col_row = ctk.CTkFrame(self.elem_edit_box, fg_color="transparent")
            col_row.pack(fill="x", pady=2)
            for c in ["#ffffff", "#f59e0b", "#ef4444", "#38bdf8", "#10b981", "#ec4899", "#cbd5e1"]:
                ctk.CTkButton(
                    col_row, text="", width=24, height=24, fg_color=c, hover_color=c, corner_radius=6,
                    command=lambda col=c: self._set_elem_color(col)
                ).pack(side="left", padx=1)

        # 스티커 선택기 (sticker 요소)
        if self.selected_key == "sticker":
            ctk.CTkLabel(self.elem_edit_box, text="학교 스티커 선택:", font=get_font(9, "bold"), text_color=palette["text_sub"]).pack(anchor="w", pady=(8, 2))
            st_row = ctk.CTkFrame(self.elem_edit_box, fg_color="transparent")
            st_row.pack(fill="x", pady=2)
            for st in STICKER_PRESETS:
                ctk.CTkButton(
                    st_row, text=st, width=28, height=28, font=get_font(12), fg_color=palette["card_bg"],
                    command=lambda s=st: self._set_sticker(s)
                ).pack(side="left", padx=1)

            ctk.CTkButton(
                self.elem_edit_box, text="📁 내 사진/이미지 파일 불러오기...", font=get_font(10, "bold"), height=28,
                command=self._load_custom_image
            ).pack(fill="x", pady=(6, 2))

    # =========================================================================
    # 캔버스 렌더링 & 드래그 인터랙션
    # =========================================================================
    def _redraw_canvas(self):
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 10 or ch <= 10:
            cw, ch = 540, 420

        ww = self.cfg["window_width"]
        wh = self.cfg["window_height"]

        # 알람 카드 중앙 배치 좌표
        ox = (cw - ww) // 2
        oy = (ch - wh) // 2

        # 1. 알람 팝업 카드 배경
        self.canvas.create_rectangle(
            ox, oy, ox + ww, oy + wh,
            fill=self.cfg.get("theme_bg", "#0f172a"),
            outline=self.cfg.get("theme_border", "#38bdf8"),
            width=2, tags="card_bg"
        )

        # 우상단 닫기 X 버튼 모형
        self.canvas.create_text(ox + ww - 18, oy + 16, text="✕", fill="#94a3b8", font=("Malgun Gothic", 10, "bold"))

        elems = self.cfg["elements"]

        # 2. 타이틀 (수업 교시명)
        if elems["title"].get("visible", True):
            e = elems["title"]
            t_id = self.canvas.create_text(
                ox + e["x"], oy + e["y"], text=e.get("text", "🔔 [수업 교시명]"),
                fill=e.get("color", "#38bdf8"), font=("Malgun Gothic", e.get("font_size", 13), "bold"),
                anchor="nw", tags=("elem", "title")
            )
            if self.selected_key == "title": self._draw_selection_box(t_id)

        # 3. 스티커 / 이미지
        if elems["sticker"].get("visible", True):
            e = elems["sticker"]
            st_type = e.get("sticker_type", "📚")
            s_id = self.canvas.create_text(
                ox + e["x"], oy + e["y"], text=st_type,
                font=("Segoe UI Emoji", e.get("size", 32)),
                anchor="center", tags=("elem", "sticker")
            )
            if self.selected_key == "sticker": self._draw_selection_box(s_id)

        # 4. 타이머 숫자
        if elems["timer"].get("visible", True):
            e = elems["timer"]
            tm_id = self.canvas.create_text(
                ox + e["x"], oy + e["y"], text="59",
                fill=e.get("color", "#f59e0b"), font=("Malgun Gothic", e.get("font_size", 52), "bold"),
                anchor="center", tags=("elem", "timer")
            )
            if self.selected_key == "timer": self._draw_selection_box(tm_id)

        # 5. 선생님 맞춤 안내 메시지
        if elems["message"].get("visible", True):
            e = elems["message"]
            m_id = self.canvas.create_text(
                ox + e["x"], oy + e["y"], text=e.get("text", "안내 문구"),
                fill=e.get("color", "#cbd5e1"), font=("Malgun Gothic", e.get("font_size", 11), "bold"),
                anchor="center", tags=("elem", "message")
            )
            if self.selected_key == "message": self._draw_selection_box(m_id)

        # 6. 보조 공지 (알람 카운트다운)
        if elems["sub_notice"].get("visible", True):
            e = elems["sub_notice"]
            sn_id = self.canvas.create_text(
                ox + e["x"], oy + e["y"], text=e.get("text", "수업 시작 알람 카운트다운"),
                fill=e.get("color", "#64748b"), font=("Malgun Gothic", e.get("font_size", 9), "bold"),
                anchor="center", tags=("elem", "sub_notice")
            )
            if self.selected_key == "sub_notice": self._draw_selection_box(sn_id)

    def _draw_selection_box(self, item_id):
        bbox = self.canvas.bbox(item_id)
        if bbox:
            pad = 4
            self.canvas.create_rectangle(
                bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad,
                outline="#38bdf8", width=1, dash=(3, 3), tags="selection_box"
            )

    def _on_canvas_click(self, event):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        ox = (cw - self.cfg["window_width"]) // 2
        oy = (ch - self.cfg["window_height"]) // 2

        # 클릭한 요소 탐색
        items = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        for itm in reversed(items):
            tags = self.canvas.gettags(itm)
            for k in ["title", "timer", "message", "sub_notice", "sticker"]:
                if k in tags:
                    self.selected_key = k
                    self._drag_start_x = event.x
                    self._drag_start_y = event.y
                    self._refresh_element_editor(theme_manager.get_theme())
                    self._redraw_canvas()
                    return

    def _on_canvas_drag(self, event):
        if not self.selected_key: return
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        self._drag_start_x = event.x
        self._drag_start_y = event.y

        elem = self.cfg["elements"].get(self.selected_key)
        if elem:
            elem["x"] = max(10, min(self.cfg["window_width"] - 10, elem["x"] + dx))
            elem["y"] = max(10, min(self.cfg["window_height"] - 10, elem["y"] + dy))
            self._redraw_canvas()

    # =========================================================================
    # 액션 핸들러들
    # =========================================================================
    def _apply_theme(self, th):
        self.cfg["theme_bg"] = th["bg"]
        self.cfg["theme_border"] = th["border"]
        self.cfg["theme_accent"] = th["accent"]
        self._redraw_canvas()

    def _adj_size(self, dw, dh):
        self.cfg["window_width"] = max(280, min(600, self.cfg["window_width"] + dw))
        self.cfg["window_height"] = max(160, min(400, self.cfg["window_height"] + dh))
        self._redraw_canvas()

    def _on_pos_mode_changed(self, val):
        rev_map = {"↗️ 우상단": "top_right", "🎯 중앙": "center", "⬇️ 하단중앙": "bottom_center"}
        self.cfg["position_mode"] = rev_map.get(val, "top_right")

    def _on_monitor_changed(self, val, mon_list):
        for m in mon_list:
            if f"모니터 {m['index']+1}" in val:
                self.cfg["monitor_index"] = m["index"]
                break

    def _adj_font_size(self, delta):
        elem = self.cfg["elements"].get(self.selected_key)
        if elem and "font_size" in elem:
            elem["font_size"] = max(8, min(80, elem["font_size"] + delta))
            self._refresh_element_editor(theme_manager.get_theme())
            self._redraw_canvas()

    def _set_elem_color(self, col):
        elem = self.cfg["elements"].get(self.selected_key)
        if elem:
            elem["color"] = col
            self._redraw_canvas()

    def _set_sticker(self, st):
        elem = self.cfg["elements"].get("sticker")
        if elem:
            elem["sticker_type"] = st
            self._redraw_canvas()

    def _load_custom_image(self):
        f = filedialog.askopenfilename(
            parent=self, title="스티커 이미지 파일 선택",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif")]
        )
        if f:
            elem = self.cfg["elements"].get("sticker")
            elem["image_path"] = f
            elem["sticker_type"] = "🖼️"
            self._redraw_canvas()

    def _test_popup(self):
        # 현재 편집 중인 설정으로 실제 화면 팝업 테스트
        alarm_design_manager.config = copy.deepcopy(self.cfg)
        from src.class_countdown_popup import ClassCountdownPopup
        ClassCountdownPopup.show(
            "1교시 국어", "선생님 맞춤 알람 테스트", 5, total_seconds=10,
            parent=self.parent, monitor_index=self.cfg.get("monitor_index", 0)
        )

    def _save_design(self):
        alarm_design_manager.save_config(self.cfg)
        messagebox.showinfo("저장 완료", "선생님만의 맞춤 알람 화면 디자인이 영구 저장되었습니다!\n수업 시작 알람이나 정기 알람 시 이 디자인으로 예쁘게 팝업됩니다.")
        self.destroy()

    def _reset_defaults(self):
        if messagebox.askyesno("기본값 복원", "알람 화면 디자인을 기본 형태로 초기화하시겠습니까?"):
            alarm_design_manager.reset_to_defaults()
            self.cfg = copy.deepcopy(alarm_design_manager.config)
            self._refresh_element_editor(theme_manager.get_theme())
            self._redraw_canvas()
