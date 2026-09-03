import os
import sys
import tkinter as tk
import customtkinter as ctk
from src.font_config import setup_global_fonts, get_font
from src.drawing_overlay import ScreenDrawingOverlay
from src.classroom_tools import ClassroomToolsDialog
from src.system_monitor import system_monitor
from src.tooltip import attach_tooltip


class FloatingQuickToolbar(tk.Toplevel):
    """
    놀티쳐 데스크 스마트 플로팅 퀵 툴바 (Apple Dynamic Island 스타일)
    - 화면 위 어디든 자유 배치 & 상단/하단 스냅
    - 어떤 창보다 무조건 최상단 보장 (Always on Top 유지 루프)
    - 손쉬운 3단 크기 조절 (S 컴팩트 / M 기본 / L 대형 터치 모드)
    - 판서, 실물화상기, 학생화면, 타이머, 뽑기, 돌림판 원클릭 리모컨
    """
    _instance = None

    @classmethod
    def get_instance(cls, parent=None):
        if cls._instance is None or not cls._instance.winfo_exists():
            cls._instance = cls(parent)
        else:
            cls._instance.deiconify()
            cls._instance.lift()
            cls._instance.attributes("-topmost", True)
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.title("놀티쳐 퀵 툴바")
        self.attributes("-topmost", True)
        self.overrideredirect(True)

        self.is_pinned = True
        self.is_collapsed = False
        self.size_mode = "M"  # "S", "M", "L"

        # 기본 크기 및 위치 (화면 상단 우측)
        sw = self.winfo_screenwidth()
        self._update_dimensions()
        x = max(10, sw - self.full_width - 40)
        y = 30
        self.geometry(f"{self.full_width}x{self.tb_height}+{x}+{y}")

        self._build_ui()
        system_monitor.register_listener(self._on_metrics_updated)
        self._keep_topmost_loop()

    def _update_dimensions(self):
        if self.size_mode == "S":
            self.full_width = 770
            self.tb_height = 42
            self.btn_w = 40
            self.btn_h = 32
            self.ico_sz = 18
            self.show_text = False
        elif self.size_mode == "L":
            self.full_width = 1060
            self.tb_height = 62
            self.btn_w = 56
            self.btn_h = 46
            self.ico_sz = 24
            self.show_text = True
        else:  # "M"
            self.full_width = 930
            self.tb_height = 52
            self.btn_w = 48
            self.btn_h = 38
            self.ico_sz = 20
            self.show_text = True

        self.collapsed_width = 96

    def _keep_topmost_loop(self):
        """어떤 앱이나 브라우저보다 항상 최상단에 머무르도록 보장"""
        if not self.winfo_exists():
            return
        if self.is_pinned:
            self.attributes("-topmost", True)
        self.after(1500, self._keep_topmost_loop)

    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        if self.is_collapsed:
            self._build_collapsed_ui()
        else:
            self._build_expanded_ui()

    def _build_collapsed_ui(self):
        self.container = ctk.CTkFrame(
            self, fg_color="#0f172a", corner_radius=16,
            border_width=2, border_color="#38bdf8"
        )
        self.container.pack(fill="both", expand=True, padx=1, pady=1)

        btn = ctk.CTkButton(
            self.container, text="🛠️ 퀵바",
            font=get_font(11, "bold"), fg_color="#0284c7", hover_color="#0369a1",
            corner_radius=14, command=self._toggle_collapse
        )
        btn.pack(fill="both", expand=True, padx=2, pady=2)
        btn.bind("<Button-1>", self._start_drag)
        btn.bind("<B1-Motion>", self._on_drag)
        btn.bind("<ButtonRelease-1>", self._on_drag_end)
        attach_tooltip(btn, "클릭하여 퀵 툴바 펼치기 (드래그하여 이동)")

    def _build_expanded_ui(self):
        self.container = ctk.CTkFrame(
            self, fg_color="#090d16", corner_radius=18,
            border_width=1, border_color="#0284c7"
        )
        self.container.pack(fill="both", expand=True, padx=1, pady=1)

        from src.icon_renderer import get_icon, COL_MAIN, COL_ACTIVE, COL_DANGER, COL_ORANGE, COL_GREEN
        ICO = self.ico_sz

        # 1. 드래그 핸들
        drag_lbl = ctk.CTkLabel(
            self.container, text="", image=get_icon("drag", "#475569", ICO),
            width=16, cursor="fleur"
        )
        drag_lbl.pack(side="left", padx=(6, 2))
        drag_lbl.bind("<Button-1>", self._start_drag)
        drag_lbl.bind("<B1-Motion>", self._on_drag)
        drag_lbl.bind("<ButtonRelease-1>", self._on_drag_end)
        attach_tooltip(drag_lbl, "드래그하여 퀵 툴바 위치 이동 (화면 상하 모서리에 자석 스냅)")

        # 2. 실시간 CPU 미니 칩
        self.res_chip = ctk.CTkLabel(
            self.container, text="CPU --%",
            font=get_font(8 if self.size_mode == "S" else 9, "bold"),
            text_color="#38bdf8", fg_color="#1e293b", corner_radius=8,
            width=46 if self.size_mode == "S" else 52,
            height=24 if self.size_mode == "S" else 28
        )
        self.res_chip.pack(side="left", padx=(0, 2))
        attach_tooltip(self.res_chip, "현재 컴퓨터 CPU 실시간 사용량")

        def _sep():
            ctk.CTkFrame(self.container, width=1, height=22, fg_color="#334155").pack(side="left", padx=2)

        _sep()

        # 3. 핵심 수업 도구 단축 버튼들
        from src.icon_renderer import COL_PURPLE
        tools = [
            ("pen",     "판서",     self._open_drawing,         COL_ORANGE, "화면 위 판서 (Alt+2)"),
            ("camera",  "화상기",   self._open_visualizer,      COL_ACTIVE, "실물화상기 실시간 뷰어"),
            ("timer",   "타이머",   self._open_timer,           COL_MAIN,   "교실 타이머 (Alt+3)"),
            ("rocket",  "바로가기", self._open_quick_launcher,  COL_ACTIVE, "자주 쓰는 프로그램 / 바로가기 빠른 실행 (➕ 등록)"),
            ("music",   "BGM",      self._open_bgm_player,      COL_GREEN,  "유튜브 교실 배경음악 BGM (소리만 재생)"),
            ("mouse",   "마우스",   self._open_mouse_settings,  COL_MAIN,   "수업용 마우스 크기 & 색상 설정"),
            ("dice",    "뽑기",     self._open_picker,          COL_PURPLE, "공정한 발표자 추첨"),
            ("wheel",   "돌림판",   self._open_wheel,           COL_MAIN,   "돌려돌려 돌림판"),
            ("screen",  "보드",     self._open_student_display, COL_ACTIVE, "놀티쳐 보드 (교실 TV 공유 화면)"),
            ("widget",  "위젯",     self._open_mini_widget,     COL_MAIN,   "바탕화면 미니 위젯"),
            ("home",    "메인",     self._open_main_app,        COL_ACTIVE, "놀티쳐 메인 창 열기"),
        ]

        for icon_name, label, cmd, icon_col, tip in tools:
            btn = ctk.CTkButton(
                self.container,
                text=label if self.show_text else "",
                image=get_icon(icon_name, icon_col, ICO),
                compound="top" if self.show_text else "none",
                font=get_font(8 if self.size_mode == "M" else 9, "bold"),
                width=self.btn_w, height=self.btn_h,
                corner_radius=8,
                fg_color="#1e293b",
                hover_color="#0284c7",
                text_color="#94a3b8",
                command=cmd
            )
            btn.pack(side="left", padx=1)
            attach_tooltip(btn, tip)

        _sep()

        # 4. 크기 조절 버튼 (S / M / L 토글)
        self.size_btn = ctk.CTkButton(
            self.container, text=self.size_mode,
            font=get_font(9, "bold"),
            width=24, height=28, corner_radius=6,
            fg_color="#1e293b", hover_color="#334155",
            text_color="#38bdf8", command=self._cycle_size_mode
        )
        self.size_btn.pack(side="left", padx=1)
        attach_tooltip(self.size_btn, f"퀵바 크기 조절 (현재: {self.size_mode} 모드 - 클릭 시 S/M/L 순환)")

        # 5. 윈도우 컨트롤러 (핀 고정, 최소화, 닫기)
        self.pin_btn = ctk.CTkButton(
            self.container, text="",
            image=get_icon("pin", COL_ACTIVE if self.is_pinned else COL_MAIN, ICO-2),
            width=26, height=28, corner_radius=6,
            fg_color="#1e293b" if self.is_pinned else "transparent",
            hover_color="#334155", command=self._toggle_pin
        )
        self.pin_btn.pack(side="left", padx=1)
        attach_tooltip(self.pin_btn, "항상 맨 위 상단 고정 토글")

        collapse_btn = ctk.CTkButton(
            self.container, text="",
            image=get_icon("minus", COL_MAIN, ICO-2),
            width=24, height=28, corner_radius=6,
            fg_color="#1e293b", hover_color="#334155",
            command=self._toggle_collapse
        )
        collapse_btn.pack(side="left", padx=1)
        attach_tooltip(collapse_btn, "미니 뱃지로 접기")

        close_btn = ctk.CTkButton(
            self.container, text="",
            image=get_icon("close", COL_DANGER, ICO-2),
            width=24, height=28, corner_radius=6,
            fg_color="#3f1d24", hover_color="#dc2626",
            command=self.close
        )
        close_btn.pack(side="left", padx=(1, 5))
        attach_tooltip(close_btn, "플로팅 퀵 툴바 닫기")

    def _cycle_size_mode(self):
        modes = ["S", "M", "L"]
        idx = modes.index(self.size_mode)
        self.size_mode = modes[(idx + 1) % len(modes)]
        self._update_dimensions()
        cur_x = self.winfo_x()
        cur_y = self.winfo_y()
        self.geometry(f"{self.full_width}x{self.tb_height}+{cur_x}+{cur_y}")
        self._build_ui()

    def _start_drag(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag(self, event):
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    def _on_drag_end(self, event):
        """화면 상단/하단 자석 스냅"""
        cur_y = self.winfo_y()
        cur_x = self.winfo_x()
        sh = self.winfo_screenheight()
        # 상단 80px 이내면 상단 스냅
        if cur_y < 80:
            self.geometry(f"+{cur_x}+20")
        # 하단 100px 이내면 하단 스냅
        elif cur_y > sh - 120:
            self.geometry(f"+{cur_x}+{sh - self.tb_height - 30}")

    def _toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        cur_x = self.winfo_x()
        cur_y = self.winfo_y()
        w = self.collapsed_width if self.is_collapsed else self.full_width
        self.geometry(f"{w}x{self.tb_height}+{cur_x}+{cur_y}")
        self._build_ui()

    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.attributes("-topmost", self.is_pinned)
        if hasattr(self, "pin_btn"):
            from src.icon_renderer import get_icon, COL_ACTIVE, COL_MAIN
            self.pin_btn.configure(
                image=get_icon("pin", COL_ACTIVE if self.is_pinned else COL_MAIN, self.ico_sz - 2),
                fg_color="#1e293b" if self.is_pinned else "transparent"
            )

    def _on_metrics_updated(self, metrics: dict):
        if hasattr(self, "res_chip") and self.res_chip.winfo_exists():
            cpu_p = metrics.get("cpu_percent", 0.0)
            col = "#4ade80" if cpu_p < 50 else ("#fb923c" if cpu_p < 80 else "#f87171")
            self.res_chip.configure(
                text=f"CPU {int(cpu_p):2d}%",
                text_color=col
            )

    def _open_drawing(self):
        ScreenDrawingOverlay.get_instance(self.parent).show()

    def _open_visualizer(self):
        from src.visualizer_window import VisualizerWindow
        VisualizerWindow.get_instance(self.parent)

    def _open_timer(self):
        ClassroomToolsDialog.get_instance(self.parent, initial_tab="timer")

    def _open_picker(self):
        ClassroomToolsDialog.get_instance(self.parent, initial_tab="picker")

    def _open_wheel(self):
        ClassroomToolsDialog.get_instance(self.parent, initial_tab="wheel")

    def _open_mouse_settings(self):
        import subprocess
        try:
            subprocess.run("start ms-settings:easeofaccess-mousepointer", shell=True, check=True)
        except Exception:
            subprocess.run("main.cpl", shell=True, check=False)

    def _open_student_display(self):
        if self.parent and hasattr(self.parent, "_open_student_display"):
            self.parent._open_student_display()

    def _open_mini_widget(self):
        if self.parent and hasattr(self.parent, "_open_mini_widget"):
            self.parent._open_mini_widget()

    def _open_main_app(self):
        if self.parent:
            self.parent.deiconify()
            self.parent.lift()
            self.parent.focus_force()

    def _open_quick_launcher(self):
        """자주 쓰는 프로그램 및 바로가기 빠른 실행 팝업 열기"""
        QuickLauncherPopup.get_instance(self)

    def _open_bgm_player(self):
        """유튜브 교실 BGM 오디오 플레이어 팝업 열기"""
        BGMPlayerPopup.get_instance(self)

    def close(self):
        try:
            self.destroy()
        except Exception:
            pass
        FloatingQuickToolbar._instance = None


class QuickLauncherPopup(ctk.CTkToplevel):
    """
    플로팅 바와 연동되는 '자주 쓰는 프로그램 / 바로가기 빠른 실행' 독 팝업
    """
    _instance = None

    @classmethod
    def get_instance(cls, parent=None):
        if cls._instance is None or not cls._instance.winfo_exists():
            cls._instance = cls(parent)
        else:
            cls._instance.deiconify()
            cls._instance.lift()
            cls._instance.focus_force()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.toolbar = parent
        self.title("자주 쓰는 프로그램 바로가기")
        self.attributes("-topmost", True)
        self.overrideredirect(True)

        from src.quick_launcher import quick_launcher
        self.ql = quick_launcher

        w = 340
        h = 360

        # 플로팅 바 아래에 자동 스냅 위치 잡기
        if self.toolbar and self.toolbar.winfo_exists():
            tx = self.toolbar.winfo_rootx()
            ty = self.toolbar.winfo_rooty()
            th = self.toolbar.winfo_height()
            px = max(10, min(self.winfo_screenwidth() - w - 10, tx + 80))
            py = ty + th + 8
        else:
            px = (self.winfo_screenwidth() - w) // 2
            py = (self.winfo_screenheight() - h) // 2

        self.geometry(f"{w}x{h}+{px}+{py}")
        self._build_ui()

    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        card = ctk.CTkFrame(
            self, fg_color="#0f172a", corner_radius=16,
            border_width=2, border_color="#0284c7"
        )
        card.pack(fill="both", expand=True, padx=2, pady=2)

        # 상단 타이틀 바
        header = ctk.CTkFrame(card, fg_color="#1e293b", height=38, corner_radius=12)
        header.pack(fill="x", side="top", padx=4, pady=4)
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="🚀 자주 쓰는 앱 / 바로가기",
            font=get_font(11, "bold"), text_color="#38bdf8"
        ).pack(side="left", padx=10)

        # 닫기
        ctk.CTkButton(
            header, text="✕", width=22, height=22, font=get_font(10, "bold"),
            fg_color="#3f1d24", hover_color="#dc2626", text_color="#fca5a5",
            corner_radius=6, command=self.destroy
        ).pack(side="right", padx=6)

        # 바로가기 추가 버튼
        add_btn = ctk.CTkButton(
            header, text="➕ 추가", width=52, height=24, font=get_font(10, "bold"),
            fg_color="#059669", hover_color="#047857", text_color="#ffffff",
            corner_radius=6, command=self._on_add_click
        )
        add_btn.pack(side="right", padx=2)
        attach_tooltip(add_btn, "새 프로그램(.exe), 문서(.hwp, .pdf), 웹사이트 추가")

        # 본문 리스트 (스크롤)
        scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=4)

        shortcuts = self.ql.get_shortcuts()
        if not shortcuts:
            ctk.CTkLabel(
                scroll, text="등록된 바로가기가 없습니다.\n상단의 [➕ 추가] 버튼을 눌러보세요!",
                font=get_font(11), text_color="#64748b"
            ).pack(pady=40)
        else:
            for item in shortcuts:
                s_id = item.get("id")
                s_name = item.get("name")
                s_target = item.get("target")
                s_emoji = item.get("emoji", "🚀")

                row = ctk.CTkFrame(scroll, fg_color="#1e293b", corner_radius=8, border_width=1, border_color="#334155")
                row.pack(fill="x", pady=2)

                # 클릭 시 실행되는 메인 버튼 영역
                btn = ctk.CTkButton(
                    row, text=f"{s_emoji}  {s_name}",
                    font=get_font(11, "bold"), fg_color="transparent",
                    hover_color="#0284c7", text_color="#f8fafc",
                    anchor="w", height=34,
                    command=lambda t=s_target: self._launch(t)
                )
                btn.pack(side="left", fill="x", expand=True, padx=(4, 0))
                attach_tooltip(btn, f"클릭하여 실행\n경로: {s_target}")

                # 삭제 버튼 (✕)
                del_btn = ctk.CTkButton(
                    row, text="✕", width=22, height=22, font=get_font(9),
                    fg_color="transparent", hover_color="#dc2626", text_color="#64748b",
                    corner_radius=4, command=lambda sid=s_id: self._remove(sid)
                )
                del_btn.pack(side="right", padx=4)
                attach_tooltip(del_btn, "이 바로가기 삭제")

        # 하단 도움말 바
        b_bar = ctk.CTkFrame(card, fg_color="transparent", height=22)
        b_bar.pack(fill="x", side="bottom", pady=2)
        ctk.CTkLabel(
            b_bar, text="💡 내 컴퓨터의 모든 파일 및 웹링크 등록 가능",
            font=get_font(8), text_color="#475569"
        ).pack(expand=True)

    def _launch(self, target: str):
        self.ql.launch(target)

    def _remove(self, shortcut_id: str):
        self.ql.remove_shortcut(shortcut_id)
        self._build_ui()

    def _on_add_click(self):
        self.ql.open_add_dialog(parent=self, on_success=self._build_ui)


class BGMPlayerPopup(ctk.CTkToplevel):
    """
    플로팅 바와 연동되는 '유튜브 교실 BGM 오디오 플레이어' 팝업 (화면 없이 소리만 재생)
    """
    _instance = None

    @classmethod
    def get_instance(cls, parent=None):
        if cls._instance is None or not cls._instance.winfo_exists():
            cls._instance = cls(parent)
        else:
            cls._instance.deiconify()
            cls._instance.lift()
            cls._instance.focus_force()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.toolbar = parent
        self.title("교실 BGM 플레이어 (유튜브 소리만 재생)")
        self.attributes("-topmost", True)
        self.overrideredirect(True)

        from src.youtube_audio_manager import youtube_audio
        self.audio = youtube_audio

        w = 380
        h = 420

        # 플로팅 바 아래에 자동 스냅 위치
        if self.toolbar and self.toolbar.winfo_exists():
            tx = self.toolbar.winfo_rootx()
            ty = self.toolbar.winfo_rooty()
            th = self.toolbar.winfo_height()
            px = max(10, min(self.winfo_screenwidth() - w - 10, tx + 140))
            py = ty + th + 8
        else:
            px = (self.winfo_screenwidth() - w) // 2
            py = (self.winfo_screenheight() - h) // 2

        self.geometry(f"{w}x{h}+{px}+{py}")
        self._build_ui()

    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        card = ctk.CTkFrame(
            self, fg_color="#090d16", corner_radius=16,
            border_width=2, border_color="#10b981"
        )
        card.pack(fill="both", expand=True, padx=2, pady=2)

        # 상단 헤더
        header = ctk.CTkFrame(card, fg_color="#1e293b", height=38, corner_radius=12)
        header.pack(fill="x", side="top", padx=4, pady=4)
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="🎵 교실 BGM (유튜브 소리만 재생)",
            font=get_font(11, "bold"), text_color="#34d399"
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            header, text="✕", width=22, height=22, font=get_font(10, "bold"),
            fg_color="#3f1d24", hover_color="#dc2626", text_color="#fca5a5",
            corner_radius=6, command=self.destroy
        ).pack(side="right", padx=6)

        add_btn = ctk.CTkButton(
            header, text="➕ 링크 추가", width=74, height=24, font=get_font(10, "bold"),
            fg_color="#059669", hover_color="#047857", text_color="#ffffff",
            corner_radius=6, command=lambda: self.audio.open_add_dialog(parent=self, on_success=self._build_ui)
        )
        add_btn.pack(side="right", padx=2)
        attach_tooltip(add_btn, "유튜브 영상 링크를 입력하여 BGM으로 등록")

        # 재생 컨트롤 바
        ctrl = ctk.CTkFrame(card, fg_color="#131d31", corner_radius=10, border_width=1, border_color="#1e293b")
        ctrl.pack(fill="x", padx=8, pady=(4, 6))

        cur_title = self.audio.current_track["name"] if self.audio.current_track else "재생 중인 음악 없음"
        disp = ctk.CTkLabel(
            ctrl, text=f"🎶 {cur_title}",
            font=get_font(10, "bold"),
            text_color="#38bdf8" if self.audio.is_playing else "#64748b",
            anchor="w"
        )
        disp.pack(fill="x", padx=8, pady=(6, 2))

        ctrl_btns = ctk.CTkFrame(ctrl, fg_color="transparent")
        ctrl_btns.pack(fill="x", padx=8, pady=(2, 6))

        def _toggle():
            if self.audio.is_playing:
                self.audio.pause()
            else:
                if self.audio.current_track:
                    self.audio.resume()
                else:
                    plist = self.audio.get_playlist()
                    if plist:
                        self.audio.play(plist[0])
            self._build_ui()

        play_btn = ctk.CTkButton(
            ctrl_btns, text="일시정지 ⏸" if self.audio.is_playing else "재생 ▶",
            width=78, height=26, font=get_font(9, "bold"),
            fg_color="#0284c7" if self.audio.is_playing else "#10b981",
            command=_toggle
        )
        play_btn.pack(side="left", padx=2)

        stop_btn = ctk.CTkButton(
            ctrl_btns, text="정지 ⏹", width=52, height=26, font=get_font(9),
            fg_color="#334155", hover_color="#475569",
            command=lambda: (self.audio.stop(), self._build_ui())
        )
        stop_btn.pack(side="left", padx=2)

        ctk.CTkLabel(ctrl_btns, text="🔊", font=get_font(9)).pack(side="left", padx=(6, 2))
        vol = ctk.CTkSlider(
            ctrl_btns, from_=0, to=100, number_of_steps=20, width=90, height=12,
            command=lambda v: self.audio.set_volume(int(v))
        )
        vol.set(self.audio.volume)
        vol.pack(side="left", padx=2)

        # 플레이리스트 스크롤
        scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=2)

        plist = self.audio.get_playlist()
        for track in plist:
            vid = track.get("video_id")
            t_name = track.get("name")
            t_emoji = track.get("emoji", "🎵")
            t_cat = track.get("category", "수업")
            is_cur = (self.audio.current_track and self.audio.current_track.get("video_id") == vid)

            row = ctk.CTkFrame(
                scroll,
                fg_color="#064e3b" if (is_cur and self.audio.is_playing) else "#1e293b",
                corner_radius=8, border_width=1,
                border_color="#34d399" if (is_cur and self.audio.is_playing) else "#334155"
            )
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row, text=t_cat, font=get_font(8, "bold"), width=32,
                fg_color="#0284c7" if is_cur else "#334155", text_color="#ffffff", corner_radius=4
            ).pack(side="left", padx=6, pady=4)

            btn = ctk.CTkButton(
                row, text=f"{t_emoji} {t_name}",
                font=get_font(10, "bold" if is_cur else "normal"),
                anchor="w", fg_color="transparent",
                hover_color="#0284c7", text_color="#f8fafc",
                height=30,
                command=lambda trk=track: (self.audio.play(trk), self._build_ui())
            )
            btn.pack(side="left", fill="x", expand=True, padx=2)
            attach_tooltip(btn, f"클릭하여 소리만 재생\n유튜브 ID: {vid}")

            del_btn = ctk.CTkButton(
                row, text="✕", width=20, height=20, font=get_font(9),
                fg_color="transparent", hover_color="#dc2626", text_color="#64748b",
                corner_radius=4,
                command=lambda v=vid: (self.audio.remove_track(v), self._build_ui())
            )
            del_btn.pack(side="right", padx=4)
            attach_tooltip(del_btn, "이 BGM 삭제")


