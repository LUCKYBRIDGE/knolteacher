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
from src.student_manager import student_manager

class StudentRosterEditDialog(ctk.CTkToplevel):
    """
    학생 명렬표 로컬 등록 및 편집 팝업
    - 🔒 100% 로컬 영구 저장 안내 명시
    - 엑셀/한글 복사-붙여넣기 1초 일괄 등록
    """
    def __init__(self, parent=None, on_saved_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.on_saved_callback = on_saved_callback

        self.title("👥 우리 반 학생 명렬표 관리")
        self.geometry("440x520")
        self.minsize(380, 440)
        self.attributes("-topmost", True)

        setup_global_fonts(self)
        self._load_icon()
        self._build_ui()

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def _build_ui(self):
        palette = theme_manager.get_theme()
        
        container = ctk.CTkFrame(self, fg_color=palette["card_bg"], corner_radius=14, border_width=1, border_color=palette["card_border"])
        container.pack(fill="both", expand=True, padx=8, pady=8)

        # 상단 타이틀
        ctk.CTkLabel(
            container,
            text="👥 우리 반 학생 명렬표 등록 & 수정",
            font=get_font(13, "bold"),
            text_color=palette["text_main"]
        ).pack(anchor="w", padx=14, pady=(12, 4))

        # 로컬 보안 안내 배너
        sec_box = ctk.CTkFrame(container, fg_color=palette["card_inner_bg"], corner_radius=8, border_width=1, border_color=palette["accent_green"])
        sec_box.pack(fill="x", padx=12, pady=(0, 8))

        sec_lbl = ctk.CTkLabel(
            sec_box,
            text="🔒 100% 로컬 단독 보관: 학생 이름은 외부 서버로 절대 전송되지 않으며\n선생님의 PC에만 안전하게 보관되어 연속해서 계속 사용하실 수 있습니다.",
            font=get_font(10),
            text_color=palette["accent_green"],
            justify="left"
        )
        sec_lbl.pack(padx=10, pady=6)

        ctk.CTkLabel(
            container,
            text="• 엑셀/한글 명단을 복사하여 아래에 붙여넣으세요 (한 줄에 1명씩 / 예: 1번 김민수 또는 김민수):",
            font=get_font(10),
            text_color=palette["text_sub"],
            justify="left"
        ).pack(anchor="w", padx=14, pady=(0, 4))

        # 텍스트 박스
        self.text_box = ctk.CTkTextbox(container, font=get_font(11), fg_color=palette["card_inner_bg"], text_color=palette["text_main"])
        self.text_box.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        # 기존 학생 목록 로드
        existing = student_manager.get_student_list()
        if existing:
            raw_lines = [f"{s['number']}번 {s['name']}" if s.get('name') else f"{s['number']}번" for s in existing]
            self.text_box.insert("1.0", "\n".join(raw_lines))
        else:
            sample_lines = [f"{i}번 학생{i}" for i in range(1, 26)]
            self.text_box.insert("1.0", "\n".join(sample_lines))

        # 하단 버튼 바
        btn_bar = ctk.CTkFrame(container, fg_color="transparent")
        btn_bar.pack(fill="x", padx=12, pady=(0, 10))

        save_btn = ctk.CTkButton(
            btn_bar,
            text="💾 학생 명렬표 로컬 저장",
            font=get_font(12, "bold"),
            fg_color=palette["accent_green"],
            hover_color="#059669",
            height=34,
            command=self._save_roster
        )
        save_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        cancel_btn = ctk.CTkButton(
            btn_bar,
            text="닫기",
            font=get_font(11, "bold"),
            fg_color=palette["sidebar_btn_hover"],
            hover_color=palette["accent_blue"],
            text_color=palette["text_main"],
            height=34,
            command=self.destroy
        )
        cancel_btn.pack(side="right", padx=(6, 0))

    def _save_roster(self):
        txt = self.text_box.get("1.0", "end").strip()
        count = student_manager.import_from_text(txt)
        if self.on_saved_callback:
            self.on_saved_callback()
        self.destroy()


class ClassroomToolsDialog(ctk.CTkToplevel):
    """
    놀티쳐 데스크 교실 5대 인터랙티브 수업 도구 모음 (Classroom Interactive Tools)
    1. ⏱️ 활동 타이머 & 스톱워치
    2. 🎲 학생 무작위 뽑기 (이름 모드 / 번호 모드 로컬 연동)
    3. 🎡 돌려돌려 돌림판 (학생 명단 원클릭 불러오기)
    4. 🪜 짜릿한 사다리타기 (학생 명단 원클릭 불러오기)
    5. ⚾ 아케이드 핀볼 뽑기 (학생 명단 원클릭 불러오기)
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
        self.title("놀티쳐 교실 도구")
        self.geometry("520x620")
        self.minsize(460, 540)
        self.attributes("-topmost", True)
        self.resizable(True, True)

        setup_global_fonts(self)
        self._load_icon()

        self.is_pinned = True
        
        # 1. 타이머 상태
        self.timer_seconds = 0
        self.timer_running = False
        self.timer_job = None

        # 2. 뽑기 상태
        self.picked_candidates = []
        self.picked_history = []
        self.picker_running = False
        self.picker_mode = "name" if student_manager.use_names_in_picker else "num"

        # 3. 돌림판 상태
        self.wheel_items = ["1모둠", "2모둠", "3모둠", "4모둠", "5모둠", "6모둠"]
        self.wheel_angle = 0.0
        self.wheel_animating = False

        # 4. 사다리타기 상태
        self.ladder_players = ["1번", "2번", "3번", "4번"]
        self.ladder_goals = ["발표", "통과", "보너스", "청소"]
        self.ladder_lines = []
        self.ladder_animating = False

        # 5. 핀볼 뽑기 상태
        self.pinball_slots = ["1등(선물)", "2등(간식)", "3등(칭찬)", "4등(발표)", "5등(청소)"]
        self.pinball_animating = False
        self.pinball_pegs = []
        self.ball_x = 0.0
        self.ball_y = 0.0
        self.ball_vx = 0.0
        self.ball_vy = 0.0

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
            corner_radius=16,
            border_width=1,
            border_color=palette["card_border"]
        )
        self.container.pack(fill="both", expand=True, padx=6, pady=6)

        # 상단 헤더 (탭 & 제어 버튼)
        hdr = ctk.CTkFrame(self.container, fg_color=palette["sidebar_bg"], corner_radius=12)
        hdr.pack(fill="x", padx=6, pady=(6, 4))

        self.tab_map = {
            "timer": "⏱️ 타이머",
            "picker": "🎲 뽑기",
            "wheel": "🎡 돌림판",
            "ladder": "🪜 사다리",
            "pinball": "⚾ 핀볼"
        }

        self.seg_btn = ctk.CTkSegmentedButton(
            hdr,
            values=["⏱️ 타이머", "🎲 뽑기", "🎡 돌림판", "🪜 사다리", "⚾ 핀볼"],
            font=get_font(11, "bold"),
            command=self._on_tab_changed
        )
        
        def_tab = self.tab_map.get(initial_tab, "⏱️ 타이머")
        self.seg_btn.set(def_tab)
        self.seg_btn.pack(side="left", padx=6, pady=6)

        btn_box = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_box.pack(side="right", padx=6, pady=6)

        self.pin_btn = ctk.CTkButton(
            btn_box,
            text="📌",
            width=28,
            height=28,
            font=get_font(11),
            fg_color=palette["accent_blue"],
            hover_color="#0369a1",
            corner_radius=8,
            command=self._toggle_pin
        )
        self.pin_btn.pack(side="left", padx=1)
        attach_tooltip(self.pin_btn, "화면 상단 고정 토글")

        close_btn = ctk.CTkButton(
            btn_box,
            text="✕",
            width=28,
            height=28,
            font=get_font(11, "bold"),
            fg_color="#3f1d24",
            hover_color="#dc2626",
            text_color="#fca5a5",
            corner_radius=8,
            command=self.destroy
        )
        close_btn.pack(side="left", padx=1)
        attach_tooltip(close_btn, "창 닫기")

        self.content_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=6, pady=4)

        self._switch_to_tab(initial_tab)

    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        palette = theme_manager.get_theme()
        self.attributes("-topmost", self.is_pinned)
        self.pin_btn.configure(
            text="📌" if self.is_pinned else "📍",
            fg_color=palette["accent_blue"] if self.is_pinned else palette["sidebar_btn_hover"]
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
        elif "핀볼" in choice:
            self._switch_to_tab("pinball")

    def _switch_to_tab(self, tab_key: str):
        for w in self.content_frame.winfo_children():
            w.destroy()

        tab_names = {
            "timer": "⏱️ 타이머",
            "picker": "🎲 뽑기",
            "wheel": "🎡 돌림판",
            "ladder": "🪜 사다리",
            "pinball": "⚾ 핀볼"
        }
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
        elif tab_key == "pinball":
            self._render_pinball_view()

    # ==========================================
    # 1. ⏱️ 타이머 뷰
    # ==========================================
    def _render_timer_view(self):
        palette = theme_manager.get_theme()

        box = ctk.CTkFrame(self.content_frame, fg_color=palette["card_inner_bg"], corner_radius=14, border_width=1, border_color=palette["card_border"])
        box.pack(fill="both", expand=True, padx=4, pady=4)

        disp_card = ctk.CTkFrame(box, fg_color="#090d16", corner_radius=16, border_width=2, border_color="#0284c7")
        disp_card.pack(fill="x", padx=16, pady=(18, 12))

        self.timer_display = ctk.CTkLabel(
            disp_card,
            text=self._format_timer(self.timer_seconds),
            font=ctk.CTkFont(family="Consolas", size=54, weight="bold"),
            text_color="#38bdf8"
        )
        self.timer_display.pack(pady=16)

        p_row = ctk.CTkFrame(box, fg_color="transparent")
        p_row.pack(pady=6)

        presets = [(60, "+1분"), (180, "+3분"), (300, "+5분"), (600, "+10분"), (900, "+15분")]
        for sec, txt in presets:
            btn = ctk.CTkButton(
                p_row,
                text=txt,
                width=56,
                height=32,
                font=get_font(10, "bold"),
                corner_radius=10,
                fg_color=palette["sidebar_btn_hover"],
                hover_color=palette["accent_blue"],
                text_color=palette["text_main"],
                command=lambda s=sec: self._add_timer(s)
            )
            btn.pack(side="left", padx=3)
            attach_tooltip(btn, f"타이머에 {txt} 추가")

        ctrl_row = ctk.CTkFrame(box, fg_color="transparent")
        ctrl_row.pack(pady=(12, 16))

        self.start_btn = ctk.CTkButton(
            ctrl_row,
            text="▶ 시작",
            width=100,
            height=40,
            font=get_font(13, "bold"),
            corner_radius=12,
            fg_color=palette["accent_green"],
            hover_color="#059669",
            command=self._toggle_timer
        )
        self.start_btn.pack(side="left", padx=4)
        attach_tooltip(self.start_btn, "타이머 시작 / 일시정지")

        reset_btn = ctk.CTkButton(
            ctrl_row,
            text="🔄 초기화",
            width=90,
            height=40,
            font=get_font(12, "bold"),
            corner_radius=12,
            fg_color=palette["sidebar_btn_hover"],
            hover_color=palette["accent_blue"],
            text_color=palette["text_main"],
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
                self.timer_seconds = 180
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
    # 2. 🎲 발표자 뽑기 뷰 (이름 모드 / 번호 모드 지원)
    # ==========================================
    def _render_picker_view(self):
        palette = theme_manager.get_theme()

        box = ctk.CTkFrame(self.content_frame, fg_color=palette["card_inner_bg"], corner_radius=14, border_width=1, border_color=palette["card_border"])
        box.pack(fill="both", expand=True, padx=4, pady=4)

        # 상단 모드 선택 바 (👦 학생 이름으로 뽑기 | 🔢 번호로만 뽑기)
        mode_row = ctk.CTkFrame(box, fg_color="transparent")
        mode_row.pack(fill="x", padx=14, pady=(10, 4))

        self.mode_seg = ctk.CTkSegmentedButton(
            mode_row,
            values=["👦 학생 이름 모드", "🔢 번호 전용 모드"],
            font=get_font(10, "bold"),
            command=self._on_picker_mode_changed
        )
        self.mode_seg.set("👦 학생 이름 모드" if self.picker_mode == "name" else "🔢 번호 전용 모드")
        self.mode_seg.pack(side="left")

        # 학생 명단 편집 버튼
        roster_btn = ctk.CTkButton(
            mode_row,
            text="👥 학생 명단 등록/수정",
            font=get_font(10, "bold"),
            fg_color=palette["sidebar_btn_hover"],
            hover_color=palette["accent_blue"],
            text_color=palette["text_main"],
            height=28,
            command=self._open_roster_dialog
        )
        roster_btn.pack(side="right")
        attach_tooltip(roster_btn, "우리 반 학생 이름 명렬표를 1초 만에 등록 및 수정 (로컬 영구 저장)")

        # 옵션 바 (총 인원 수 / 중복 제외)
        opt_row = ctk.CTkFrame(box, fg_color="transparent")
        opt_row.pack(fill="x", padx=14, pady=(4, 4))

        ctk.CTkLabel(opt_row, text="추첨 대상 인원:", font=get_font(11, "bold"), text_color=palette["text_main"]).pack(side="left")
        
        cur_cnt = student_manager.get_count()
        self.num_spin = ctk.CTkEntry(opt_row, width=54, height=28, font=get_font(11, "bold"), fg_color=palette["card_bg"], text_color=palette["text_main"])
        self.num_spin.insert(0, str(cur_cnt))
        self.num_spin.pack(side="left", padx=6)

        self.no_dup_var = ctk.BooleanVar(value=True)
        chk = ctk.CTkCheckBox(opt_row, text="중복 제외", variable=self.no_dup_var, font=get_font(11), text_color=palette["text_main"])
        chk.pack(side="left", padx=10)

        # 번호/이름 대형 전광판 카드
        card = ctk.CTkFrame(box, fg_color="#090d16", corner_radius=16, border_width=2, border_color="#f59e0b")
        card.pack(fill="x", padx=16, pady=(8, 8))

        self.picker_num_lbl = ctk.CTkLabel(
            card,
            text="?",
            font=ctk.CTkFont(family="Malgun Gothic", size=56, weight="bold"),
            text_color="#f59e0b"
        )
        self.picker_num_lbl.pack(pady=12)

        # 추첨 버튼 바
        btn_row = ctk.CTkFrame(box, fg_color="transparent")
        btn_row.pack(pady=4)

        self.pick_btn = ctk.CTkButton(
            btn_row,
            text="🎲 발표자 뽑기!",
            width=140,
            height=40,
            font=get_font(13, "bold"),
            corner_radius=12,
            fg_color=palette["accent_blue"],
            hover_color="#0369a1",
            command=self._start_pick
        )
        self.pick_btn.pack(side="left", padx=4)
        attach_tooltip(self.pick_btn, "학생을 랜덤으로 롤링 추첨")

        reset_btn = ctk.CTkButton(
            btn_row,
            text="초기화",
            width=80,
            height=40,
            font=get_font(11, "bold"),
            corner_radius=12,
            fg_color=palette["sidebar_btn_hover"],
            hover_color=palette["accent_blue"],
            text_color=palette["text_main"],
            command=self._reset_picker
        )
        reset_btn.pack(side="left", padx=4)
        attach_tooltip(reset_btn, "뽑힌 기록 초기화")

        # 뽑힌 명단 목록
        self.picked_list_lbl = ctk.CTkLabel(
            box,
            text="뽑힌 기록: 없음",
            font=get_font(11),
            text_color=palette["text_sub"],
            wraplength=440
        )
        self.picked_list_lbl.pack(pady=(6, 8))

        # 하단 로컬 저장 안내 문구
        ctk.CTkLabel(
            box,
            text="🔒 학생 명단은 외부 서버로 전송되지 않고 로컬 PC에만 100% 안전하게 저장됩니다.",
            font=get_font(9),
            text_color=palette["text_muted"]
        ).pack(pady=(0, 6))

    def _on_picker_mode_changed(self, choice: str):
        self.picker_mode = "name" if "이름" in choice else "num"
        student_manager.save_roster(student_manager.get_student_list(), use_names=(self.picker_mode == "name"))
        self._reset_picker()

    def _open_roster_dialog(self):
        StudentRosterEditDialog(self, on_saved_callback=self._on_roster_saved)

    def _on_roster_saved(self):
        cur_cnt = student_manager.get_count()
        if hasattr(self, "num_spin") and self.num_spin.winfo_exists():
            self.num_spin.delete(0, "end")
            self.num_spin.insert(0, str(cur_cnt))
        self._reset_picker()

    def _start_pick(self):
        if self.picker_running:
            return

        is_name_mode = (self.picker_mode == "name")
        students = student_manager.get_student_list()

        try:
            target_count = max(1, int(self.num_spin.get()))
        except Exception:
            target_count = len(students) if (students and is_name_mode) else 25

        if is_name_mode and students:
            candidates = [f"{s['number']}번 {s['name']}" if s.get('name') else f"{s['number']}번" for s in students[:target_count]]
        else:
            candidates = [f"{i}번" for i in range(1, target_count + 1)]

        if self.no_dup_var.get():
            available = [c for c in candidates if c not in self.picked_history]
        else:
            available = candidates

        if not available:
            self.picker_num_lbl.configure(text="추첨 완료!")
            self.picked_list_lbl.configure(text=f"모든 대상({len(candidates)}명)이 한 번씩 다 뽑혔습니다!")
            return

        self.picker_running = True
        self.pick_btn.configure(state="disabled")

        def _rolling(count=0, max_count=18):
            if count < max_count:
                temp_pick = random.choice(candidates)
                self.picker_num_lbl.configure(text=temp_pick)
                self.after(50 + count * 15, lambda: _rolling(count + 1, max_count))
            else:
                final_winner = random.choice(available)
                self.picked_history.append(final_winner)
                self.picker_num_lbl.configure(text=final_winner, text_color="#10b981")
                self.picked_list_lbl.configure(text=f"뽑힌 명단 ({len(self.picked_history)}명): {', '.join(self.picked_history)}")
                self.picker_running = False
                self.pick_btn.configure(state="normal")
                try:
                    winsound.MessageBeep(winsound.MB_OK)
                except Exception:
                    pass

        _rolling()

    def _reset_picker(self):
        self.picked_history.clear()
        self.picker_num_lbl.configure(text="?", text_color="#f59e0b")
        self.picked_list_lbl.configure(text="뽑힌 기록: 없음")

    # ==========================================
    # 3. 🎡 돌려돌려 돌림판 뷰 (학생명단 불러오기 지원)
    # ==========================================
    def _render_wheel_view(self):
        palette = theme_manager.get_theme()

        box = ctk.CTkFrame(self.content_frame, fg_color=palette["card_inner_bg"], corner_radius=14, border_width=1, border_color=palette["card_border"])
        box.pack(fill="both", expand=True, padx=4, pady=4)

        input_row = ctk.CTkFrame(box, fg_color="transparent")
        input_row.pack(fill="x", padx=12, pady=(8, 2))

        ctk.CTkLabel(input_row, text="항목 (쉼표구분):", font=get_font(10, "bold"), text_color=palette["text_main"]).pack(side="left")
        
        self.wheel_entry = ctk.CTkEntry(input_row, height=26, font=get_font(10), fg_color=palette["card_bg"], text_color=palette["text_main"])
        self.wheel_entry.insert(0, ", ".join(self.wheel_items))
        self.wheel_entry.pack(side="left", fill="x", expand=True, padx=4)

        set_btn = ctk.CTkButton(
            input_row,
            text="적용",
            width=42,
            height=26,
            font=get_font(10, "bold"),
            fg_color=palette["sidebar_btn_hover"],
            hover_color=palette["accent_blue"],
            text_color=palette["text_main"],
            command=self._apply_wheel_items
        )
        set_btn.pack(side="left", padx=1)

        load_stu_btn = ctk.CTkButton(
            input_row,
            text="👥 학생불러오기",
            width=80,
            height=26,
            font=get_font(10, "bold"),
            fg_color=palette["accent_green"],
            hover_color="#059669",
            command=self._load_students_into_wheel
        )
        load_stu_btn.pack(side="left", padx=2)
        attach_tooltip(load_stu_btn, "우리 반 학생 명렬표를 돌림판 항목으로 1초 불러오기")

        self.wheel_canvas = tk.Canvas(
            box,
            width=280,
            height=280,
            bg=palette["card_inner_bg"],
            highlightthickness=0
        )
        self.wheel_canvas.pack(pady=2)

        self._draw_wheel(self.wheel_angle)

        self.spin_btn = ctk.CTkButton(
            box,
            text="🚀 돌려돌려 돌림판!",
            width=160,
            height=38,
            font=get_font(13, "bold"),
            corner_radius=12,
            fg_color=palette["accent_orange"],
            hover_color="#c2410c",
            command=self._start_spin_wheel
        )
        self.spin_btn.pack(pady=(2, 4))
        attach_tooltip(self.spin_btn, "돌림판을 힘차게 회전!")

        self.wheel_result_lbl = ctk.CTkLabel(
            box,
            text="돌림판을 돌려 당첨 항목을 뽑아보세요!",
            font=get_font(11, "bold"),
            text_color=palette["accent_blue"]
        )
        self.wheel_result_lbl.pack(pady=(0, 6))

    def _load_students_into_wheel(self):
        names = student_manager.get_student_names()
        if names:
            self.wheel_items = [n.split()[-1] if " " in n else n for n in names[:12]]
            self.wheel_entry.delete(0, "end")
            self.wheel_entry.insert(0, ", ".join(self.wheel_items))
            self._draw_wheel(self.wheel_angle)
            self.wheel_result_lbl.configure(text=f"학생 명단 {len(self.wheel_items)}명을 불러왔습니다.")

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

        self.wheel_canvas.create_oval(cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4, outline="#f59e0b", width=3)

        for i, it in enumerate(self.wheel_items):
            cur_start = start_angle + i * slice_deg
            col = wheel_colors[i % len(wheel_colors)]
            self.wheel_canvas.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=cur_start, extent=slice_deg,
                fill=col, outline="#ffffff", width=2
            )

            mid_rad = math.radians(cur_start + slice_deg / 2.0)
            tx = cx + (r * 0.65) * math.cos(mid_rad)
            ty = cy - (r * 0.65) * math.sin(mid_rad)

            self.wheel_canvas.create_text(
                tx, ty,
                text=it[:6],
                fill="#ffffff",
                font=("Malgun Gothic", 9, "bold")
            )

        self.wheel_canvas.create_oval(cx - 18, cy - 18, cx + 18, cy + 18, fill="#0f172a", outline="#f59e0b", width=3)

        self.wheel_canvas.create_polygon(
            cx, cy - r - 8,
            cx - 10, cy - r + 12,
            cx + 10, cy - r + 12,
            fill="#fbbf24", outline="#b45309", width=2
        )

    def _start_spin_wheel(self):
        if self.wheel_animating or not self.wheel_items:
            return

        self.wheel_animating = True
        self.spin_btn.configure(state="disabled")
        self.wheel_result_lbl.configure(text="🎡 돌림판이 힘차게 회전하는 중...", text_color="#f59e0b")

        step_speed = 36.0
        decel = 0.982

        def _spin_step(speed):
            if speed > 0.4:
                self.wheel_angle = (self.wheel_angle + speed) % 360.0
                self._draw_wheel(self.wheel_angle)
                self.after(16, lambda: _spin_step(speed * decel))
            else:
                self.wheel_animating = False
                self.spin_btn.configure(state="normal")
                
                n = len(self.wheel_items)
                slice_deg = 360.0 / n
                
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

        box = ctk.CTkFrame(self.content_frame, fg_color=palette["card_inner_bg"], corner_radius=14, border_width=1, border_color=palette["card_border"])
        box.pack(fill="both", expand=True, padx=4, pady=4)

        p_row = ctk.CTkFrame(box, fg_color="transparent")
        p_row.pack(fill="x", padx=12, pady=(6, 2))
        ctk.CTkLabel(p_row, text="출발 (위):", font=get_font(10, "bold"), text_color=palette["text_main"]).pack(side="left")
        self.lad_p_entry = ctk.CTkEntry(p_row, height=26, font=get_font(10), fg_color=palette["card_bg"], text_color=palette["text_main"])
        self.lad_p_entry.insert(0, ", ".join(self.ladder_players))
        self.lad_p_entry.pack(side="left", fill="x", expand=True, padx=4)

        load_btn = ctk.CTkButton(
            p_row,
            text="👥 학생불러오기",
            width=80,
            height=26,
            font=get_font(10, "bold"),
            fg_color=palette["accent_green"],
            hover_color="#059669",
            command=self._load_students_into_ladder
        )
        load_btn.pack(side="right")

        g_row = ctk.CTkFrame(box, fg_color="transparent")
        g_row.pack(fill="x", padx=12, pady=(2, 4))
        ctk.CTkLabel(g_row, text="도착 (아래):", font=get_font(10, "bold"), text_color=palette["text_main"]).pack(side="left")
        self.lad_g_entry = ctk.CTkEntry(g_row, height=26, font=get_font(10), fg_color=palette["card_bg"], text_color=palette["text_main"])
        self.lad_g_entry.insert(0, ", ".join(self.ladder_goals))
        self.lad_g_entry.pack(side="left", fill="x", expand=True, padx=4)

        self.lad_canvas = tk.Canvas(
            box,
            width=420,
            height=260,
            bg=palette["card_inner_bg"],
            highlightthickness=0
        )
        self.lad_canvas.pack(pady=2)

        self._generate_and_draw_ladder()

        btn_row = ctk.CTkFrame(box, fg_color="transparent")
        btn_row.pack(pady=4)

        gen_btn = ctk.CTkButton(
            btn_row,
            text="🪜 새 사다리 생성",
            width=120,
            height=34,
            font=get_font(11, "bold"),
            corner_radius=10,
            fg_color=palette["sidebar_btn_hover"],
            hover_color=palette["accent_blue"],
            text_color=palette["text_main"],
            command=self._generate_and_draw_ladder
        )
        gen_btn.pack(side="left", padx=4)

        self.lad_start_btn = ctk.CTkButton(
            btn_row,
            text="▶ 사다리 타기!",
            width=120,
            height=34,
            font=get_font(11, "bold"),
            corner_radius=10,
            fg_color=palette["accent_blue"],
            hover_color="#0369a1",
            command=self._start_ladder_animation
        )
        self.lad_start_btn.pack(side="left", padx=4)

        self.lad_result_lbl = ctk.CTkLabel(
            box,
            text="사다리 타기를 시작해보세요!",
            font=get_font(11, "bold"),
            text_color=palette["accent_blue"]
        )
        self.lad_result_lbl.pack(pady=(0, 4))

    def _load_students_into_ladder(self):
        names = student_manager.get_student_names()
        if names:
            self.ladder_players = [n.split()[-1] if " " in n else n for n in names[:6]]
            self.lad_p_entry.delete(0, "end")
            self.lad_p_entry.insert(0, ", ".join(self.ladder_players))
            self._generate_and_draw_ladder()

    def _generate_and_draw_ladder(self):
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

        w, h = 420, 260
        margin_x = 42
        top_y = 35
        bot_y = 225
        col_gap = (w - margin_x * 2) / (num_col - 1)

        self.ladder_col_x = [margin_x + i * col_gap for i in range(num_col)]
        self.ladder_horiz_lines = []

        for i in range(num_col):
            x = self.ladder_col_x[i]
            self.lad_canvas.create_line(x, top_y, x, bot_y, fill="#64748b", width=3, capstyle=tk.ROUND)
            self.lad_canvas.create_text(x, top_y - 15, text=self.ladder_players[i][:5], fill="#0284c7", font=("Malgun Gothic", 10, "bold"))
            self.lad_canvas.create_text(x, bot_y + 15, text=self.ladder_goals[i][:5], fill="#ea580c", font=("Malgun Gothic", 10, "bold"))

        levels = 6
        step_h = (bot_y - top_y) / (levels + 1)

        for lvl in range(1, levels + 1):
            ly = top_y + lvl * step_h
            for col in range(num_col - 1):
                if random.random() > 0.45:
                    x1 = self.ladder_col_x[col]
                    x2 = self.ladder_col_x[col + 1]
                    self.lad_canvas.create_line(x1, ly, x2, ly, fill="#94a3b8", width=2, capstyle=tk.ROUND)
                    self.ladder_horiz_lines.append((ly, col, col + 1))

    def _start_ladder_animation(self):
        if self.ladder_animating:
            return

        self.ladder_animating = True
        self.lad_start_btn.configure(state="disabled")
        self.lad_result_lbl.configure(text="🪜 사다리를 타고 내려가는 중...", text_color="#f59e0b")

        num_col = len(self.ladder_col_x)
        results = []
        colors = ["#ef4444", "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"]

        for p_idx in range(num_col):
            cur_col = p_idx
            cur_y = 35
            bot_y = 225
            path = [(self.ladder_col_x[cur_col], cur_y)]

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

            for pt_i in range(len(path) - 1):
                x1, y1 = path[pt_i]
                x2, y2 = path[pt_i + 1]
                self.lad_canvas.create_line(x1, y1, x2, y2, fill=colors[p_idx % len(colors)], width=3, capstyle=tk.ROUND, joinstyle=tk.ROUND)

        res_str = " | ".join([f"{p} ➜ {g}" for p, g in results])
        self.lad_result_lbl.configure(text=f"🎉 결과: {res_str}", text_color="#10b981")
        self.ladder_animating = False
        self.lad_start_btn.configure(state="normal")
        try:
            winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass

    # ==========================================
    # 5. ⚾ 아케이드 핀볼(Plinko) 뽑기 뷰
    # ==========================================
    def _render_pinball_view(self):
        palette = theme_manager.get_theme()

        box = ctk.CTkFrame(self.content_frame, fg_color=palette["card_inner_bg"], corner_radius=14, border_width=1, border_color=palette["card_border"])
        box.pack(fill="both", expand=True, padx=4, pady=4)

        s_row = ctk.CTkFrame(box, fg_color="transparent")
        s_row.pack(fill="x", padx=12, pady=(6, 2))
        ctk.CTkLabel(s_row, text="슬롯 항목 (쉼표구분):", font=get_font(10, "bold"), text_color=palette["text_main"]).pack(side="left")
        
        self.pin_slot_entry = ctk.CTkEntry(s_row, height=26, font=get_font(10), fg_color=palette["card_bg"], text_color=palette["text_main"])
        self.pin_slot_entry.insert(0, ", ".join(self.pinball_slots))
        self.pin_slot_entry.pack(side="left", fill="x", expand=True, padx=4)

        set_btn = ctk.CTkButton(
            s_row,
            text="적용",
            width=42,
            height=26,
            font=get_font(10, "bold"),
            fg_color=palette["sidebar_btn_hover"],
            hover_color=palette["accent_blue"],
            text_color=palette["text_main"],
            command=self._apply_pinball_slots
        )
        set_btn.pack(side="left")

        # 핀볼 아케이드 캔버스
        self.pin_canvas = tk.Canvas(
            box,
            width=420,
            height=270,
            bg="#070b12",
            highlightthickness=1,
            highlightbackground="#0284c7"
        )
        self.pin_canvas.pack(pady=2)

        self._draw_pinball_board()

        self.pin_drop_btn = ctk.CTkButton(
            box,
            text="⚾ 핀볼 투하!",
            width=160,
            height=38,
            font=get_font(13, "bold"),
            corner_radius=12,
            fg_color=palette["accent_green"],
            hover_color="#059669",
            command=self._start_pinball_drop
        )
        self.pin_drop_btn.pack(pady=(2, 4))
        attach_tooltip(self.pin_drop_btn, "상단에서 핀볼을 투하하여 슬롯 추첨 시작")

        self.pin_result_lbl = ctk.CTkLabel(
            box,
            text="핀볼을 투하하여 짜릿한 추첨을 즐겨보세요!",
            font=get_font(11, "bold"),
            text_color=palette["accent_blue"]
        )
        self.pin_result_lbl.pack(pady=(0, 4))

    def _apply_pinball_slots(self):
        txt = self.pin_slot_entry.get().strip()
        if txt:
            slots = [x.strip() for x in txt.split(",") if x.strip()]
            if len(slots) >= 2:
                self.pinball_slots = slots
                self._draw_pinball_board()
                self.pin_result_lbl.configure(text=f"{len(self.pinball_slots)}개 슬롯으로 설정되었습니다.")

    def _draw_pinball_board(self, highlight_slot=None):
        self.pin_canvas.delete("all")
        w, h = 420, 270

        self.pinball_pegs.clear()
        rows = 6
        start_y = 45
        gap_y = 30

        for r_idx in range(rows):
            cols = r_idx + 4
            gap_x = 34
            row_w = (cols - 1) * gap_x
            start_x = (w - row_w) / 2.0
            cur_y = start_y + r_idx * gap_y

            for c_idx in range(cols):
                px = start_x + c_idx * gap_x
                py = cur_y
                self.pinball_pegs.append((px, py))
                self.pin_canvas.create_oval(px - 3, py - 3, px + 3, py + 3, fill="#fbbf24", outline="#ffffff", width=1)

        n_slots = len(self.pinball_slots)
        slot_w = w / n_slots
        bot_y = h - 45
        floor_y = h - 6

        slot_colors = ["#ef4444", "#f59e0b", "#10b981", "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899"]

        for i in range(n_slots):
            sx1 = i * slot_w
            sx2 = (i + 1) * slot_w
            scol = slot_colors[i % len(slot_colors)]

            is_win = (highlight_slot == i)
            fill_c = scol if is_win else "#111827"
            
            self.pin_canvas.create_rectangle(sx1 + 2, bot_y, sx2 - 2, floor_y, fill=fill_c, outline=scol, width=2 if is_win else 1)
            self.pin_canvas.create_line(sx1, bot_y - 12, sx1, floor_y, fill="#64748b", width=2)
            if i == n_slots - 1:
                self.pin_canvas.create_line(sx2, bot_y - 12, sx2, floor_y, fill="#64748b", width=2)

            lbl_txt = self.pinball_slots[i][:6]
            self.pin_canvas.create_text(
                (sx1 + sx2) / 2.0, (bot_y + floor_y) / 2.0,
                text=lbl_txt,
                fill="#ffffff",
                font=("Malgun Gothic", 9, "bold")
            )

        self.pin_canvas.create_line(w / 2.0 - 25, 6, w / 2.0 - 10, 26, fill="#38bdf8", width=3)
        self.pin_canvas.create_line(w / 2.0 + 25, 6, w / 2.0 + 10, 26, fill="#38bdf8", width=3)

    def _start_pinball_drop(self):
        if self.pinball_animating:
            return

        self.pinball_animating = True
        self.pin_drop_btn.configure(state="disabled")
        self.pin_result_lbl.configure(text="⚾ 핀볼이 통통 튀며 낙하하는 중...!", text_color="#f59e0b")

        w, h = 420, 270
        self.ball_x = w / 2.0 + random.uniform(-4, 4)
        self.ball_y = 12.0
        self.ball_vx = random.uniform(-1.2, 1.2)
        self.ball_vy = 2.0
        ball_r = 7

        def _physics_step():
            if not self.pinball_animating:
                return

            self.ball_vy += 0.45
            self.ball_vx *= 0.985
            self.ball_x += self.ball_vx
            self.ball_y += self.ball_vy

            if self.ball_x < ball_r + 8:
                self.ball_x = ball_r + 8
                self.ball_vx = abs(self.ball_vx) * 0.75 + 1.0
            elif self.ball_x > w - ball_r - 8:
                self.ball_x = w - ball_r - 8
                self.ball_vx = -abs(self.ball_vx) * 0.75 - 1.0

            for px, py in self.pinball_pegs:
                dx = self.ball_x - px
                dy = self.ball_y - py
                dist = math.hypot(dx, dy)
                min_dist = ball_r + 3

                if dist < min_dist and dist > 0.001:
                    nx = dx / dist
                    ny = dy / dist
                    dot = self.ball_vx * nx + self.ball_vy * ny
                    
                    self.ball_vx = (self.ball_vx - 1.8 * dot * nx) + random.uniform(-0.8, 0.8)
                    self.ball_vy = abs(self.ball_vy - 1.8 * dot * ny) * 0.7 + 1.0

                    self.ball_x = px + nx * min_dist
                    self.ball_y = py + ny * min_dist

            self._draw_pinball_board()
            
            self.pin_canvas.create_oval(
                self.ball_x - ball_r, self.ball_y - ball_r,
                self.ball_x + ball_r, self.ball_y + ball_r,
                fill="#ef4444", outline="#ffffff", width=2
            )

            bot_y = h - 40
            if self.ball_y >= bot_y:
                self.pinball_animating = False
                self.pin_drop_btn.configure(state="normal")

                n_slots = len(self.pinball_slots)
                slot_w = w / n_slots
                win_slot_idx = int(self.ball_x // slot_w)
                win_slot_idx = max(0, min(n_slots - 1, win_slot_idx))

                winner = self.pinball_slots[win_slot_idx]
                self._draw_pinball_board(highlight_slot=win_slot_idx)

                self.pin_canvas.create_oval(
                    self.ball_x - ball_r, bot_y + 10 - ball_r,
                    self.ball_x + ball_r, bot_y + 10 + ball_r,
                    fill="#10b981", outline="#ffffff", width=2
                )

                self.pin_result_lbl.configure(
                    text=f"🎉 핀볼 골인 결과: [ {winner} ] !",
                    text_color="#10b981"
                )
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass
            else:
                self.after(20, _physics_step)

        _physics_step()
