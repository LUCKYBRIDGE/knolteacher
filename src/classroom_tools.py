import os
import sys
import math
import time
import random
import datetime
import winsound
import tkinter as tk
import customtkinter as ctk
from src.font_config import setup_global_fonts, get_font
from src.sound_manager import sound_manager
from src.theme_manager import theme_manager
from src.tooltip import attach_tooltip

class ClassroomToolsDialog(ctk.CTkToplevel):
    """
    놀티쳐 데스크 교실 활동 도구 모음 (Classroom Interactive Tools)
    1. ⏱️ 활동 타이머 & 스톱워치
    2. 🎲 학생 무작위 뽑기 (Random Student Picker)
    3. 🎡 돌려돌려 돌림판 (Spin the Wheel / Roulette)
    4. 🪜 짜릿한 사다리타기 (Ghost Leg Ladder Game)
    """
    _instance = None

    @classmethod
    def get_instance(cls, parent=None, initial_tab="timer"):
        if cls._instance is None or not cls._instance.winfo_exists():
            cls._instance = cls(parent, initial_tab)
        else:
            cls._instance.deiconify()
            cls._instance.lift()
            cls._instance._switch_to_tab(initial_tab)
        return cls._instance

    def __init__(self, parent=None, initial_tab="timer"):
        super().__init__(parent)
        self.parent = parent
        self.title("놀티쳐 교실 도구 (타이머 · 뽑기 · 돌림판 · 사다리)")
        self.geometry("480x580")
        self.minsize(420, 500)
        self.attributes("-topmost", True)
        self.resizable(True, True)

        setup_global_fonts(self)
        self._load_icon()

        self.is_pinned = True
        
        # 타이머 상태
        self.timer_seconds = 0
        self.timer_running = False
        self.timer_job = None

        # 뽑기 상태
        self.max_students = 25
        self.picked_numbers = []
        self.roulette_running = False

        # 돌림판 상태
        self.wheel_items = ["1모둠", "2모둠", "3모둠", "4모둠", "5모둠", "6모둠"]
        self.wheel_angle = 0.0
        self.wheel_animating = False

        # 사다리타기 상태
        self.ladder_players = ["1번", "2번", "3번", "4번"]
        self.ladder_goals = ["발표", "통과", "보너스", "청소"]
        self.ladder_lines = []
        self.ladder_animating = False

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
        palette = theme_manager.get_theme()
        
        self.container = ctk.CTkFrame(
            self,
            fg_color=palette["card_bg"],
            corner_radius=14,
            border_width=2,
            border_color=palette["accent_blue"]
        )
        self.container.pack(fill="both", expand=True, padx=6, pady=6)

        # 상단 헤더 (탭 & 제어 버튼)
        hdr = ctk.CTkFrame(self.container, fg_color=palette["sidebar_bg"], corner_radius=10)
        hdr.pack(fill="x", padx=6, pady=(6, 4))

        self.tab_map = {
            "timer": "⏱️ 타이머",
            "picker": "🎲 뽑기",
            "wheel": "🎡 돌림판",
            "ladder": "🪜 사다리"
        }

        self.seg_btn = ctk.CTkSegmentedButton(
            hdr,
            values=["⏱️ 타이머", "🎲 뽑기", "🎡 돌림판", "🪜 사다리"],
            font=get_font(11, "bold"),
            command=self._on_tab_changed
        )
        
        # initial_tab 설정
        def_tab = self.tab_map.get(initial_tab, "⏱️ 타이머")
        self.seg_btn.set(def_tab)
        self.seg_btn.pack(side="left", padx=4, pady=4)

        btn_box = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_box.pack(side="right", padx=4, pady=4)

        self.pin_btn = ctk.CTkButton(
            btn_box,
            text="📌",
            width=26,
            height=26,
            font=get_font(11),
            fg_color="#0284c7",
            hover_color="#0369a1",
            corner_radius=6,
            command=self._toggle_pin
        )
        self.pin_btn.pack(side="left", padx=1)
        attach_tooltip(self.pin_btn, "화면 상단 고정 토글")

        close_btn = ctk.CTkButton(
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
        )
        close_btn.pack(side="left", padx=1)
        attach_tooltip(close_btn, "교실 도구 닫기")

        self.content_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=6, pady=4)

        self._switch_to_tab(initial_tab)

    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.attributes("-topmost", self.is_pinned)
        self.pin_btn.configure(
            text="📌" if self.is_pinned else "📍",
            fg_color="#0284c7" if self.is_pinned else "#334155"
        )

    def _on_tab_changed(self, choice: str):
        if "타이머" in choice:
            self._switch_to_tab("timer")
        elif "뽑기" in choice:
            self._switch_to_tab("picker")
        elif "돌림판" in choice:
            self._switch_to_tab("wheel")
        elif "사다리" in choice:
            self._switch_to_tab("ladder")

    def _switch_to_tab(self, tab_key: str):
        for w in self.content_frame.winfo_children():
            w.destroy()

        tab_names = {"timer": "⏱️ 타이머", "picker": "🎲 뽑기", "wheel": "🎡 돌림판", "ladder": "🪜 사다리"}
        if tab_key in tab_names:
            self.seg_btn.set(tab_names[tab_key])

        if tab_key == "timer":
            self._render_timer_view()
        elif tab_key == "picker":
            self._render_picker_view()
        elif tab_key == "wheel":
            self._render_wheel_view()
        elif tab_key == "ladder":
            self._render_ladder_view()

    # ==========================================
    # 1. ⏱️ 타이머 뷰
    # ==========================================
    def _render_timer_view(self):
        palette = theme_manager.get_theme()

        box = ctk.CTkFrame(self.content_frame, fg_color=palette["sidebar_bg"], corner_radius=12)
        box.pack(fill="both", expand=True, padx=4, pady=4)

        self.timer_display = ctk.CTkLabel(
            box,
            text=self._format_timer(self.timer_seconds),
            font=ctk.CTkFont(family="Consolas", size=48, weight="bold"),
            text_color="#38bdf8"
        )
        self.timer_display.pack(pady=(20, 10))

        # 프리셋 버튼
        p_row = ctk.CTkFrame(box, fg_color="transparent")
        p_row.pack(pady=6)

        presets = [(60, "+1분"), (180, "+3분"), (300, "+5분"), (600, "+10분"), (900, "+15분")]
        for sec, txt in presets:
            btn = ctk.CTkButton(
                p_row,
                text=txt,
                width=54,
                height=30,
                font=get_font(10, "bold"),
                fg_color="#334155",
                hover_color="#475569",
                command=lambda s=sec: self._add_timer(s)
            )
            btn.pack(side="left", padx=2)
            attach_tooltip(btn, f"타이머에 {txt} 추가")

        # 제어 버튼
        ctrl_row = ctk.CTkFrame(box, fg_color="transparent")
        ctrl_row.pack(pady=(12, 16))

        self.start_btn = ctk.CTkButton(
            ctrl_row,
            text="▶ 시작",
            width=90,
            height=38,
            font=get_font(13, "bold"),
            fg_color="#10b981",
            hover_color="#059669",
            command=self._toggle_timer
        )
        self.start_btn.pack(side="left", padx=4)
        attach_tooltip(self.start_btn, "타이머 시작 / 일시정지")

        reset_btn = ctk.CTkButton(
            ctrl_row,
            text="🔄 초기화",
            width=80,
            height=38,
            font=get_font(12, "bold"),
            fg_color="#475569",
            hover_color="#64748b",
            command=self._reset_timer
        )
        reset_btn.pack(side="left", padx=4)
        attach_tooltip(reset_btn, "타이머 00:00으로 초기화")

    def _format_timer(self, s: int) -> str:
        m, sec = divmod(s, 60)
        return f"{m:02d}:{sec:02d}"

    def _add_timer(self, sec: int):
        self.timer_seconds += sec
        if hasattr(self, "timer_display") and self.timer_display.winfo_exists():
            self.timer_display.configure(text=self._format_timer(self.timer_seconds))

    def _toggle_timer(self):
        if self.timer_running:
            self.timer_running = False
            if self.timer_job:
                self.after_cancel(self.timer_job)
                self.timer_job = None
            self.start_btn.configure(text="▶ 재개", fg_color="#10b981")
        else:
            if self.timer_seconds <= 0:
                self.timer_seconds = 180  # 기본 3분
            self.timer_running = True
            self.start_btn.configure(text="⏸ 일시정지", fg_color="#ea580c")
            self._timer_tick()

    def _timer_tick(self):
        if not self.timer_running:
            return
        if self.timer_seconds > 0:
            self.timer_seconds -= 1
            if hasattr(self, "timer_display") and self.timer_display.winfo_exists():
                self.timer_display.configure(text=self._format_timer(self.timer_seconds))
            self.timer_job = self.after(1000, self._timer_tick)
        else:
            self.timer_running = False
            self.start_btn.configure(text="▶ 시작", fg_color="#10b981")
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass

    def _reset_timer(self):
        self.timer_running = False
        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None
        self.timer_seconds = 0
        if hasattr(self, "timer_display") and self.timer_display.winfo_exists():
            self.timer_display.configure(text="00:00")
        if hasattr(self, "start_btn") and self.start_btn.winfo_exists():
            self.start_btn.configure(text="▶ 시작", fg_color="#10b981")

    # ==========================================
    # 2. 🎲 발표자 뽑기 뷰
    # ==========================================
    def _render_picker_view(self):
        palette = theme_manager.get_theme()

        box = ctk.CTkFrame(self.content_frame, fg_color=palette["sidebar_bg"], corner_radius=12)
        box.pack(fill="both", expand=True, padx=4, pady=4)

        # 상단 학생 수 설정
        opt_row = ctk.CTkFrame(box, fg_color="transparent")
        opt_row.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(opt_row, text="학급 총 학생 수:", font=get_font(11, "bold"), text_color=palette["text_main"]).pack(side="left")
        
        self.num_spin = ctk.CTkEntry(opt_row, width=50, height=28, font=get_font(11, "bold"))
        self.num_spin.insert(0, str(self.max_students))
        self.num_spin.pack(side="left", padx=6)

        self.no_dup_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt_row, text="중복 제외", variable=self.no_dup_var, font=get_font(11)).pack(side="left", padx=10)

        # 번호 대형 전광판
        self.picker_num_lbl = ctk.CTkLabel(
            box,
            text="?",
            font=ctk.CTkFont(family="Malgun Gothic", size=72, weight="bold"),
            text_color="#f59e0b"
        )
        self.picker_num_lbl.pack(pady=(15, 10))

        # 추첨 버튼
        btn_row = ctk.CTkFrame(box, fg_color="transparent")
        btn_row.pack(pady=4)

        self.pick_btn = ctk.CTkButton(
            btn_row,
            text="🎲 번호 뽑기!",
            width=120,
            height=38,
            font=get_font(13, "bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self._start_pick
        )
        self.pick_btn.pack(side="left", padx=4)
        attach_tooltip(self.pick_btn, "학생 번호를 랜덤으로 롤링 추첨")

        reset_btn = ctk.CTkButton(
            btn_row,
            text="초기화",
            width=70,
            height=38,
            font=get_font(11, "bold"),
            fg_color="#475569",
            hover_color="#64748b",
            command=self._reset_picker
        )
        reset_btn.pack(side="left", padx=4)
        attach_tooltip(reset_btn, "뽑힌 번호 기록 초기화")

        # 뽑힌 번호 목록
        self.picked_list_lbl = ctk.CTkLabel(
            box,
            text="뽑힌 번호: 없음",
            font=get_font(11),
            text_color=palette["text_sub"],
            wraplength=380
        )
        self.picked_list_lbl.pack(pady=(10, 12))

    def _start_pick(self):
        if self.roulette_running:
            return
        try:
            self.max_students = max(1, int(self.num_spin.get()))
        except Exception:
            self.max_students = 25

        candidates = list(range(1, self.max_students + 1))
        if self.no_dup_var.get():
            candidates = [c for c in candidates if c not in self.picked_numbers]

        if not candidates:
            self.picker_num_lbl.configure(text="완료!")
            self.picked_list_lbl.configure(text=f"모든 학생({self.max_students}명)이 한 번씩 다 뽑혔습니다!")
            return

        self.roulette_running = True
        self.pick_btn.configure(state="disabled")

        # 롤링 애니메이션
        def _rolling(count=0, max_count=18):
            if count < max_count:
                temp_pick = random.randint(1, self.max_students)
                self.picker_num_lbl.configure(text=f"{temp_pick}번")
                self.after(50 + count * 15, lambda: _rolling(count + 1, max_count))
            else:
                final_winner = random.choice(candidates)
                self.picked_numbers.append(final_winner)
                self.picker_num_lbl.configure(text=f"{final_winner}번", text_color="#10b981")
                self.picked_list_lbl.configure(text=f"뽑힌 번호 ({len(self.picked_numbers)}명): {', '.join(map(lambda x: str(x)+'번', self.picked_numbers))}")
                self.roulette_running = False
                self.pick_btn.configure(state="normal")
                try:
                    winsound.MessageBeep(winsound.MB_OK)
                except Exception:
                    pass

        _rolling()

    def _reset_picker(self):
        self.picked_numbers.clear()
        self.picker_num_lbl.configure(text="?", text_color="#f59e0b")
        self.picked_list_lbl.configure(text="뽑힌 번호: 없음")

    # ==========================================
    # 3. 🎡 돌려돌려 돌림판 뷰
    # ==========================================
    def _render_wheel_view(self):
        palette = theme_manager.get_theme()

        box = ctk.CTkFrame(self.content_frame, fg_color=palette["sidebar_bg"], corner_radius=12)
        box.pack(fill="both", expand=True, padx=4, pady=4)

        # 항목 입력 바
        input_row = ctk.CTkFrame(box, fg_color="transparent")
        input_row.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(input_row, text="항목 (쉼표구분):", font=get_font(10, "bold"), text_color=palette["text_main"]).pack(side="left")
        
        self.wheel_entry = ctk.CTkEntry(input_row, height=26, font=get_font(10))
        self.wheel_entry.insert(0, ", ".join(self.wheel_items))
        self.wheel_entry.pack(side="left", fill="x", expand=True, padx=6)

        set_btn = ctk.CTkButton(
            input_row,
            text="적용",
            width=46,
            height=26,
            font=get_font(10, "bold"),
            fg_color="#334155",
            hover_color="#475569",
            command=self._apply_wheel_items
        )
        set_btn.pack(side="left")
        attach_tooltip(set_btn, "입력한 항목으로 돌림판 갱신")

        # 룰렛 캔버스
        self.wheel_canvas = tk.Canvas(
            box,
            width=280,
            height=280,
            bg=palette["sidebar_bg"],
            highlightthickness=0
        )
        self.wheel_canvas.pack(pady=4)

        self._draw_wheel(self.wheel_angle)

        # 돌리기 버튼
        self.spin_btn = ctk.CTkButton(
            box,
            text="🚀 돌려돌려 돌림판!",
            width=150,
            height=38,
            font=get_font(13, "bold"),
            fg_color="#ea580c",
            hover_color="#c2410c",
            command=self._start_spin_wheel
        )
        self.spin_btn.pack(pady=(4, 6))
        attach_tooltip(self.spin_btn, "돌림판을 힘차게 회전!")

        self.wheel_result_lbl = ctk.CTkLabel(
            box,
            text="돌림판을 돌려 당첨 항목을 뽑아보세요!",
            font=get_font(11, "bold"),
            text_color="#38bdf8"
        )
        self.wheel_result_lbl.pack(pady=(0, 6))

    def _apply_wheel_items(self):
        txt = self.wheel_entry.get().strip()
        if txt:
            items = [x.strip() for x in txt.split(",") if x.strip()]
            if items:
                self.wheel_items = items
                self._draw_wheel(self.wheel_angle)
                self.wheel_result_lbl.configure(text=f"{len(self.wheel_items)}개 항목으로 설정되었습니다.")

    def _draw_wheel(self, start_angle: float):
        self.wheel_canvas.delete("all")
        cx, cy, r = 140, 140, 120
        n = len(self.wheel_items)
        if n == 0:
            return

        slice_deg = 360.0 / n
        wheel_colors = ["#ef4444", "#f97316", "#f59e0b", "#10b981", "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899"]

        for i, it in enumerate(self.wheel_items):
            cur_start = start_angle + i * slice_deg
            col = wheel_colors[i % len(wheel_colors)]
            self.wheel_canvas.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=cur_start, extent=slice_deg,
                fill=col, outline="#ffffff", width=2
            )

            # 텍스트 위치 계산
            mid_rad = math.radians(cur_start + slice_deg / 2.0)
            tx = cx + (r * 0.65) * math.cos(mid_rad)
            ty = cy - (r * 0.65) * math.sin(mid_rad)

            self.wheel_canvas.create_text(
                tx, ty,
                text=it[:6],
                fill="#ffffff",
                font=("Malgun Gothic", 10, "bold")
            )

        # 중앙 허브
        self.wheel_canvas.create_oval(cx - 18, cy - 18, cx + 18, cy + 18, fill="#0f172a", outline="#ffffff", width=2)

        # 상단 가리키는 바늘 (Pointer)
        self.wheel_canvas.create_polygon(
            cx, cy - r - 8,
            cx - 12, cy - r + 14,
            cx + 12, cy - r + 14,
            fill="#fbbf24", outline="#b45309", width=2
        )

    def _start_spin_wheel(self):
        if self.wheel_animating or not self.wheel_items:
            return

        self.wheel_animating = True
        self.spin_btn.configure(state="disabled")
        self.wheel_result_lbl.configure(text="🎡 돌림판이 힘차게 회전하는 중...", text_color="#f59e0b")

        total_spins = random.randint(1080, 1800)  # 3~5바퀴 이상
        step_speed = 35.0
        decel = 0.982

        def _spin_step(speed):
            if speed > 0.4:
                self.wheel_angle = (self.wheel_angle + speed) % 360.0
                self._draw_wheel(self.wheel_angle)
                self.after(16, lambda: _spin_step(speed * decel))
            else:
                self.wheel_animating = False
                self.spin_btn.configure(state="normal")
                
                # 당첨 항목 계산 (바늘은 90도 상단 위치)
                n = len(self.wheel_items)
                slice_deg = 360.0 / n
                
                # 바늘 각도(90도)에 걸린 조각 인덱스
                pointer_angle = (90.0 - self.wheel_angle) % 360.0
                win_idx = int(pointer_angle // slice_deg) % n
                winner = self.wheel_items[win_idx]

                self.wheel_result_lbl.configure(
                    text=f"🎉 당첨 결과: [ {winner} ] !",
                    text_color="#10b981"
                )
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

        _spin_step(step_speed)

    # ==========================================
    # 4. 🪜 사다리타기 뷰
    # ==========================================
    def _render_ladder_view(self):
        palette = theme_manager.get_theme()

        box = ctk.CTkFrame(self.content_frame, fg_color=palette["sidebar_bg"], corner_radius=12)
        box.pack(fill="both", expand=True, padx=4, pady=4)

        # 플레이어 & 목표 입력 바
        p_row = ctk.CTkFrame(box, fg_color="transparent")
        p_row.pack(fill="x", padx=10, pady=(6, 2))
        ctk.CTkLabel(p_row, text="출발 (위):", font=get_font(10, "bold"), text_color=palette["text_main"]).pack(side="left")
        self.lad_p_entry = ctk.CTkEntry(p_row, height=24, font=get_font(10))
        self.lad_p_entry.insert(0, ", ".join(self.ladder_players))
        self.lad_p_entry.pack(side="left", fill="x", expand=True, padx=4)

        g_row = ctk.CTkFrame(box, fg_color="transparent")
        g_row.pack(fill="x", padx=10, pady=(2, 4))
        ctk.CTkLabel(g_row, text="도착 (아래):", font=get_font(10, "bold"), text_color=palette["text_main"]).pack(side="left")
        self.lad_g_entry = ctk.CTkEntry(g_row, height=24, font=get_font(10))
        self.lad_g_entry.insert(0, ", ".join(self.ladder_goals))
        self.lad_g_entry.pack(side="left", fill="x", expand=True, padx=4)

        # 사다리 캔버스
        self.lad_canvas = tk.Canvas(
            box,
            width=380,
            height=260,
            bg=palette["sidebar_bg"],
            highlightthickness=0
        )
        self.lad_canvas.pack(pady=4)

        self._generate_and_draw_ladder()

        # 제어 버튼
        btn_row = ctk.CTkFrame(box, fg_color="transparent")
        btn_row.pack(pady=4)

        gen_btn = ctk.CTkButton(
            btn_row,
            text="🪜 새 사다리 생성",
            width=110,
            height=32,
            font=get_font(11, "bold"),
            fg_color="#334155",
            hover_color="#475569",
            command=self._generate_and_draw_ladder
        )
        gen_btn.pack(side="left", padx=3)
        attach_tooltip(gen_btn, "새로운 무작위 사다리 발판 생성")

        self.lad_start_btn = ctk.CTkButton(
            btn_row,
            text="▶ 사다리 타기!",
            width=110,
            height=32,
            font=get_font(11, "bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self._start_ladder_animation
        )
        self.lad_start_btn.pack(side="left", padx=3)
        attach_tooltip(self.lad_start_btn, "모든 참가자의 사다리 결과 애니메이션 시작")

        self.lad_result_lbl = ctk.CTkLabel(
            box,
            text="사다리 타기를 시작해보세요!",
            font=get_font(11, "bold"),
            text_color="#38bdf8"
        )
        self.lad_result_lbl.pack(pady=(0, 6))

    def _generate_and_draw_ladder(self):
        # 1. 항목 동기화
        p_txt = self.lad_p_entry.get().strip()
        g_txt = self.lad_g_entry.get().strip()
        if p_txt:
            self.ladder_players = [x.strip() for x in p_txt.split(",") if x.strip()]
        if g_txt:
            self.ladder_goals = [x.strip() for x in g_txt.split(",") if x.strip()]

        num_col = min(len(self.ladder_players), len(self.ladder_goals))
        if num_col < 2:
            num_col = 2
            self.ladder_players = ["1번", "2번"]
            self.ladder_goals = ["당첨", "꽝"]

        self.lad_canvas.delete("all")

        w, h = 380, 260
        margin_x = 40
        top_y = 35
        bot_y = 225
        col_gap = (w - margin_x * 2) / (num_col - 1)

        self.ladder_col_x = [margin_x + i * col_gap for i in range(num_col)]
        self.ladder_horiz_lines = []

        # 세로선 그리기 및 라벨 표시
        for i in range(num_col):
            x = self.ladder_col_x[i]
            self.lad_canvas.create_line(x, top_y, x, bot_y, fill="#64748b", width=3)
            # 상단 출발 라벨
            self.lad_canvas.create_text(x, top_y - 15, text=self.ladder_players[i][:5], fill="#38bdf8", font=("Malgun Gothic", 10, "bold"))
            # 하단 도착 라벨
            self.lad_canvas.create_text(x, bot_y + 15, text=self.ladder_goals[i][:5], fill="#f59e0b", font=("Malgun Gothic", 10, "bold"))

        # 무작위 가로선 생성 (사다리 발판)
        levels = 6
        step_h = (bot_y - top_y) / (levels + 1)

        for lvl in range(1, levels + 1):
            ly = top_y + lvl * step_h
            for col in range(num_col - 1):
                if random.random() > 0.45:
                    x1 = self.ladder_col_x[col]
                    x2 = self.ladder_col_x[col + 1]
                    self.lad_canvas.create_line(x1, ly, x2, ly, fill="#94a3b8", width=2)
                    self.ladder_horiz_lines.append((ly, col, col + 1))

    def _start_ladder_animation(self):
        if self.ladder_animating:
            return

        self.ladder_animating = True
        self.lad_start_btn.configure(state="disabled")
        self.lad_result_lbl.configure(text="🪜 사다리를 타고 내려가는 중...", text_color="#f59e0b")

        num_col = len(self.ladder_col_x)
        results = []

        # 각 플레이어별 경로 추적
        colors = ["#ef4444", "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"]

        for p_idx in range(num_col):
            cur_col = p_idx
            cur_y = 35
            bot_y = 225
            path = [(self.ladder_col_x[cur_col], cur_y)]

            # y 정렬된 가로선 순회
            sorted_lines = sorted(self.ladder_horiz_lines, key=lambda x: x[0])
            for ly, c1, c2 in sorted_lines:
                if ly > cur_y:
                    if cur_col == c1:
                        path.append((self.ladder_col_x[c1], ly))
                        path.append((self.ladder_col_x[c2], ly))
                        cur_col = c2
                        cur_y = ly
                    elif cur_col == c2:
                        path.append((self.ladder_col_x[c2], ly))
                        path.append((self.ladder_col_x[c1], ly))
                        cur_col = c1
                        cur_y = ly

            path.append((self.ladder_col_x[cur_col], bot_y))
            results.append((self.ladder_players[p_idx], self.ladder_goals[cur_col]))

            # 경로 하이라이트 선 그리기
            for pt_i in range(len(path) - 1):
                x1, y1 = path[pt_i]
                x2, y2 = path[pt_i + 1]
                self.lad_canvas.create_line(x1, y1, x2, y2, fill=colors[p_idx % len(colors)], width=3)

        res_str = " | ".join([f"{p} ➜ {g}" for p, g in results])
        self.lad_result_lbl.configure(text=f"🎉 결과: {res_str}", text_color="#10b981")
        self.ladder_animating = False
        self.lad_start_btn.configure(state="normal")
        try:
            winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass
