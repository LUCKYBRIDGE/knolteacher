import os
import sys
import random
import datetime
import winsound
import customtkinter as ctk
from src.font_config import setup_global_fonts, get_font
from src.sound_manager import sound_manager

class ClassroomToolsDialog(ctk.CTkToplevel):
    """
    수업 중 칠판이나 화면 구석에 띄워두고 사용하는 교실 수업 활동 도구 (타이머 & 발표자 뽑기)
    """
    def __init__(self, parent=None, initial_tab="timer"):
        super().__init__(parent)
        self.title("교실 활동 도구 (타이머 & 발표자 뽑기)")
        self.geometry("380x420")
        self.minsize(320, 360)
        self.attributes("-topmost", True)
        self.resizable(True, True)

        setup_global_fonts(self)
        self._load_icon()

        self.is_pinned = True
        self.timer_seconds = 0
        self.timer_running = False
        self.timer_job = None

        # 랜덤 뽑기 상태
        self.max_students = 25
        self.picked_numbers = []
        self.roulette_running = False

        self._build_ui(initial_tab)

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def _build_ui(self, initial_tab: str):
        container = ctk.CTkFrame(self, fg_color="#0b0f19", corner_radius=14, border_width=1, border_color="#0a84ff")
        container.pack(fill="both", expand=True, padx=6, pady=6)

        # 상단 헤더 (탭 & 제어 버튼)
        hdr = ctk.CTkFrame(container, fg_color="#161e31", corner_radius=10)
        hdr.pack(fill="x", padx=6, pady=(6, 4))

        self.seg_btn = ctk.CTkSegmentedButton(
            hdr,
            values=["⏱️ 활동 타이머", "🎲 발표자 뽑기"],
            font=get_font(12, "bold"),
            command=self._on_tab_changed
        )
        self.seg_btn.set("⏱️ 활동 타이머" if initial_tab == "timer" else "🎲 발표자 뽑기")
        self.seg_btn.pack(side="left", padx=6, pady=4)

        btn_box = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_box.pack(side="right", padx=6, pady=4)

        self.pin_btn = ctk.CTkButton(
            btn_box,
            text="📌",
            width=26,
            height=26,
            font=get_font(11),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            corner_radius=6,
            command=self._toggle_pin
        )
        self.pin_btn.pack(side="left", padx=2)

        ctk.CTkButton(
            btn_box,
            text="✕",
            width=26,
            height=26,
            font=get_font(11, "bold"),
            fg_color="#3f1d24",
            hover_color="#dc2626",
            text_color="#fca5a5",
            corner_radius=6,
            command=self.destroy
        ).pack(side="left", padx=2)

        self.content_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=6, pady=4)

        if initial_tab == "timer":
            self._render_timer_view()
        else:
            self._render_picker_view()

    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.attributes("-topmost", self.is_pinned)
        self.pin_btn.configure(
            text="📌" if self.is_pinned else "📍",
            fg_color="#2563eb" if self.is_pinned else "#334155"
        )

    def _on_tab_changed(self, choice: str):
        for w in self.content_frame.winfo_children():
            w.destroy()
        if "타이머" in choice:
            self._render_timer_view()
        else:
            self._render_picker_view()

    # =========================================================================
    # 1. 활동 타이머
    # =========================================================================
    def _render_timer_view(self):
        box = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        box.pack(fill="both", expand=True)

        # 타이머 디스플레이
        self.timer_disp_card = ctk.CTkFrame(box, fg_color="#181d28", corner_radius=12, border_width=1, border_color="#334155")
        self.timer_disp_card.pack(fill="both", expand=True, pady=(0, 6))

        self.timer_lbl = ctk.CTkLabel(
            self.timer_disp_card,
            text="05 : 00",
            font=ctk.CTkFont(family="Consolas", size=48, weight="bold"),
            text_color="#30d158"
        )
        self.timer_lbl.pack(expand=True, pady=10)

        # 빠른 프리셋 버튼 (1분, 3분, 5분, 10분)
        preset_row = ctk.CTkFrame(box, fg_color="transparent")
        preset_row.pack(fill="x", pady=4)

        for mins in [1, 3, 5, 10]:
            ctk.CTkButton(
                preset_row,
                text=f"{mins}분",
                font=get_font(12, "bold"),
                height=30,
                corner_radius=6,
                fg_color="#1e293b",
                hover_color="#334155",
                command=lambda m=mins: self._set_timer_minutes(m)
            ).pack(side="left", fill="x", expand=True, padx=2)

        # 컨트롤 버튼 (시작, 일시정지, 리셋)
        ctrl_row = ctk.CTkFrame(box, fg_color="transparent")
        ctrl_row.pack(fill="x", pady=6)

        self.start_btn = ctk.CTkButton(
            ctrl_row,
            text="▶ 시작",
            font=get_font(13, "bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=36,
            command=self._toggle_timer_start
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(
            ctrl_row,
            text="🔄 리셋",
            font=get_font(13, "bold"),
            fg_color="#374151",
            hover_color="#4b5563",
            width=80,
            height=36,
            command=self._reset_timer
        ).pack(side="right")

        self.timer_seconds = 300  # 기본 5분

    def _set_timer_minutes(self, mins: int):
        self._pause_timer()
        self.timer_seconds = mins * 60
        self._update_timer_label()

    def _update_timer_label(self):
        m = self.timer_seconds // 60
        s = self.timer_seconds % 60
        self.timer_lbl.configure(
            text=f"{m:02d} : {s:02d}",
            text_color="#30d158" if self.timer_seconds > 30 else ("#f59e0b" if self.timer_seconds > 10 else "#ef4444")
        )

    def _toggle_timer_start(self):
        if self.timer_running:
            self._pause_timer()
        else:
            if self.timer_seconds <= 0:
                self.timer_seconds = 300
            self.timer_running = True
            self.start_btn.configure(text="⏸ 일시정지", fg_color="#f59e0b", hover_color="#d97706")
            self._timer_tick()

    def _pause_timer(self):
        self.timer_running = False
        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None
        if hasattr(self, 'start_btn') and self.start_btn.winfo_exists():
            self.start_btn.configure(text="▶ 시작", fg_color="#10b981", hover_color="#059669")

    def _reset_timer(self):
        self._pause_timer()
        self.timer_seconds = 300
        self._update_timer_label()

    def _timer_tick(self):
        if not self.timer_running:
            return

        if self.timer_seconds > 0:
            self.timer_seconds -= 1
            self._update_timer_label()
            self.timer_job = self.after(1000, self._timer_tick)
        else:
            self.timer_running = False
            self.start_btn.configure(text="▶ 시작", fg_color="#10b981")
            self.timer_lbl.configure(text="⏰ 시간 종료!", text_color="#ef4444")
            sound_manager.preview_sound("chime")
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass

    # =========================================================================
    # 2. 발표자 뽑기 (랜덤 룰렛)
    # =========================================================================
    def _render_picker_view(self):
        box = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        box.pack(fill="both", expand=True)

        # 설정 행 (학급 인원수)
        cfg_row = ctk.CTkFrame(box, fg_color="transparent")
        cfg_row.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(cfg_row, text="학급 총 학생 수:", font=get_font(12, "bold")).pack(side="left", padx=(0, 6))

        self.num_combo = ctk.CTkComboBox(
            cfg_row,
            values=[str(i) for i in range(10, 41)],
            font=get_font(12),
            width=70,
            state="readonly",
            command=self._on_max_students_changed
        )
        self.num_combo.set(str(self.max_students))
        self.num_combo.pack(side="left")

        self.exclude_switch = ctk.CTkSwitch(
            cfg_row,
            text="중복 당첨 제외",
            font=get_font(11, "bold")
        )
        self.exclude_switch.select()
        self.exclude_switch.pack(side="right")

        # 당첨 디스플레이 카드
        self.pick_card = ctk.CTkFrame(box, fg_color="#181d28", corner_radius=12, border_width=2, border_color="#f59e0b")
        self.pick_card.pack(fill="both", expand=True, pady=4)

        self.pick_lbl = ctk.CTkLabel(
            self.pick_card,
            text="🎲\n발표자를 뽑아주세요!",
            font=get_font(22, "bold"),
            text_color="#fcd34d",
            justify="center"
        )
        self.pick_lbl.pack(expand=True, pady=10)

        self.history_lbl = ctk.CTkLabel(
            self.pick_card,
            text="뽑힌 번호: (없음)",
            font=get_font(11),
            text_color="#94a3b8"
        )
        self.history_lbl.pack(fill="x", padx=8, pady=(0, 6))

        # 뽑기 버튼
        act_row = ctk.CTkFrame(box, fg_color="transparent")
        act_row.pack(fill="x", pady=4)

        self.pick_btn = ctk.CTkButton(
            act_row,
            text="🎲 [원클릭] 랜덤 발표자 뽑기",
            font=get_font(13, "bold"),
            fg_color="#f59e0b",
            hover_color="#d97706",
            height=38,
            command=self._start_roulette
        )
        self.pick_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(
            act_row,
            text="초기화",
            font=get_font(11),
            fg_color="#374151",
            hover_color="#4b5563",
            width=60,
            height=38,
            command=self._reset_picker_history
        ).pack(side="right")

    def _on_max_students_changed(self, val: str):
        self.max_students = int(val)

    def _reset_picker_history(self):
        self.picked_numbers.clear()
        self.history_lbl.configure(text="뽑힌 번호: (없음)")
        self.pick_lbl.configure(text="🎲\n발표자를 뽑아주세요!", font=get_font(22, "bold"), text_color="#fcd34d")

    def _start_roulette(self):
        if self.roulette_running:
            return

        exclude_duplicates = self.exclude_switch.get() == 1
        available = [n for n in range(1, self.max_students + 1) if not (exclude_duplicates and n in self.picked_numbers)]

        if not available:
            self.pick_lbl.configure(text="🎉\n모든 학생이 발표했습니다!", font=get_font(18, "bold"), text_color="#38bdf8")
            return

        self.roulette_running = True
        self.pick_btn.configure(state="disabled")

        # 롤링 애니메이션 (약 1.5초 동안 번호가 빠르게 바뀜)
        self._animate_roulette(available, count=16)

    def _animate_roulette(self, pool: list[int], count: int):
        if count > 0:
            current_choice = random.choice(range(1, self.max_students + 1))
            self.pick_lbl.configure(
                text=f"🎲\n{current_choice} 번",
                font=ctk.CTkFont(family="Consolas", size=44, weight="bold"),
                text_color="#93c5fd"
            )
            # 틱 소리
            try:
                winsound.Beep(800 + (16 - count) * 40, 40)
            except Exception:
                pass
            delay = 50 + (16 - count) * 15
            self.after(delay, lambda: self._animate_roulette(pool, count - 1))
        else:
            final_winner = random.choice(pool)
            self.picked_numbers.append(final_winner)
            self.pick_lbl.configure(
                text=f"🎉 당첨! 🎉\n{final_winner} 번 학생",
                font=get_font(30, "bold"),
                text_color="#30d158"
            )
            self.history_lbl.configure(
                text=f"뽑힌 번호 ({len(self.picked_numbers)}명): {', '.join(map(str, self.picked_numbers))}"
            )
            self.roulette_running = False
            self.pick_btn.configure(state="normal")
            sound_manager.preview_sound("chime")
