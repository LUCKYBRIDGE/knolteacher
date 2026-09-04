"""
놀티쳐 보드 - 자유 배치 및 크기조절 스마트 위젯 시스템 (Board Widgets)
- 마우스 드래그 이동 타이틀바
- 우하단 리사이즈 핸들 (크기 조절)
- 주사위: 면 수 조절(D4~D20, N면), 2개 주사위, 비/비율/백분율 실시간 통계 표
- 발표자 뽑기: 이름 모드, 번호 모드, 성별 필터(남/여)
- 타이머, 돌림판, 점수판, 시간표, 급식, 메모 위젯
"""
import random
import datetime
import winsound
import tkinter as tk
import customtkinter as ctk
from typing import Dict, Any, Optional, List, Callable
from src.font_config import get_font
from src.theme_manager import theme_manager
from src.student_manager import student_manager
from src.timetable_manager import timetable_manager
from src.neis_client import neis_client


class FloatingBoardWidget(ctk.CTkFrame):
    """
    보드 캔버스 위에서 드래그 이동 및 크기 조절이 가능한 플로팅 위젯 베이스 프레임
    """
    MIN_WIDTH = 220
    MIN_HEIGHT = 160

    def __init__(
        self,
        parent_canvas,
        widget_id: str,
        widget_type: str,
        title: str,
        x: int = 50,
        y: int = 50,
        width: int = 340,
        height: int = 280,
        on_change_callback: Optional[Callable] = None,
        on_close_callback: Optional[Callable] = None
    ):
        raw_t = theme_manager.get_theme()
        self.t = {
            "bg": raw_t.get("app_bg", "#0b0f19"),
            "card": raw_t.get("card_bg", "#161d2f"),
            "card_inner": raw_t.get("card_inner_bg", "#111622"),
            "border": raw_t.get("card_border", "#26334d"),
            "accent": raw_t.get("accent", "#38bdf8"),
            "accent_hover": raw_t.get("accent_hover", "#0284c7"),
            "text_main": raw_t.get("text_main", "#f8fafc"),
            "text_sub": raw_t.get("text_sub", "#94a3b8")
        }
        self.cur_x = x
        self.cur_y = y
        self.cur_w = max(self.MIN_WIDTH, width)
        self.cur_h = max(self.MIN_HEIGHT, height)
        super().__init__(
            parent_canvas,
            width=self.cur_w,
            height=self.cur_h,
            fg_color=self.t["card"],
            corner_radius=12,
            border_width=1,
            border_color=self.t["border"]
        )
        self.parent_canvas = parent_canvas
        self.widget_id = widget_id
        self.widget_type = widget_type
        self.title_text = title
        self.on_change = on_change_callback
        self.on_close = on_close_callback

        self._drag_start_x = 0
        self._drag_start_y = 0
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_orig_w = 0
        self._resize_orig_h = 0

        self._build_container()
        self.update_geometry()

    def update_geometry(self):
        self.configure(width=self.cur_w, height=self.cur_h)
        self.place(x=self.cur_x, y=self.cur_y)

    def _build_container(self):
        # 1. 상단 드래그 타이틀바
        self.titlebar = ctk.CTkFrame(self, fg_color=self.t["card_inner"], corner_radius=8, height=32)
        self.titlebar.pack(fill="x", padx=4, pady=4)
        self.titlebar.pack_propagate(False)

        # 타이틀 라벨 (드래그 핸들)
        self.title_lbl = ctk.CTkLabel(
            self.titlebar,
            text=f"  {self.title_text}",
            font=get_font(11, "bold"),
            text_color=self.t["text_main"],
            anchor="w",
            cursor="fleur"
        )
        self.title_lbl.pack(side="left", fill="x", expand=True, padx=4)

        # 닫기 버튼
        close_btn = ctk.CTkButton(
            self.titlebar,
            text="✕",
            width=22,
            height=22,
            font=get_font(10, "bold"),
            fg_color="transparent",
            hover_color="#ef4444",
            text_color=self.t["text_sub"],
            command=self.close
        )
        close_btn.pack(side="right", padx=3)

        # 타이틀바 드래그 바인딩
        for target in (self.titlebar, self.title_lbl):
            target.bind("<Button-1>", self._on_drag_start)
            target.bind("<B1-Motion>", self._on_drag_motion)
            target.bind("<ButtonRelease-1>", self._on_drag_end)

        # 2. 메인 컨텐츠 영역
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.pack(fill="both", expand=True, padx=6, pady=(0, 4))

        # 3. 우하단 리사이즈 핸들 바
        bottom_bar = ctk.CTkFrame(self, fg_color="transparent", height=14)
        bottom_bar.pack(fill="x", side="bottom")

        self.resize_grip = ctk.CTkLabel(
            bottom_bar,
            text="◢ ",
            font=ctk.CTkFont(size=9),
            text_color=self.t["text_sub"],
            cursor="size_nw_se"
        )
        self.resize_grip.pack(side="right", padx=2)
        self.resize_grip.bind("<Button-1>", self._on_resize_start)
        self.resize_grip.bind("<B1-Motion>", self._on_resize_motion)
        self.resize_grip.bind("<ButtonRelease-1>", self._on_resize_end)

    def _on_drag_start(self, event):
        self.lift()
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root

    def _on_drag_motion(self, event):
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        self.cur_x = max(0, self.cur_x + dx)
        self.cur_y = max(0, self.cur_y + dy)
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        self.update_geometry()

    def _on_drag_end(self, event):
        if self.on_change:
            self.on_change()

    def _on_resize_start(self, event):
        self.lift()
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._resize_orig_w = self.cur_w
        self._resize_orig_h = self.cur_h

    def _on_resize_motion(self, event):
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        self.cur_w = max(self.MIN_WIDTH, self._resize_orig_w + dx)
        self.cur_h = max(self.MIN_HEIGHT, self._resize_orig_h + dy)
        self.update_geometry()

    def _on_resize_end(self, event):
        if self.on_change:
            self.on_change()

    def close(self):
        if self.on_close:
            self.on_close(self.widget_id)
        self.destroy()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.widget_id,
            "type": self.widget_type,
            "title": self.title_text,
            "x": self.cur_x,
            "y": self.cur_y,
            "w": self.cur_w,
            "h": self.cur_h
        }


# =============================================================================
# 1. 타이머 위젯
# =============================================================================
class TimerWidget(FloatingBoardWidget):
    def __init__(self, parent, widget_id, x=60, y=60, w=320, h=250, **kwargs):
        super().__init__(parent, widget_id, "timer", "⏱️ 수업 타이머", x, y, w, h, **kwargs)
        self.total_seconds = 300
        self.remaining_seconds = 300
        self.is_running = False
        self._job = None
        self._build_content()

    def _build_content(self):
        t = self.t
        # 시간 표시
        self.disp_lbl = ctk.CTkLabel(
            self.content_area,
            text="05:00",
            font=ctk.CTkFont(family="Consolas", size=48, weight="bold"),
            text_color=t["accent"]
        )
        self.disp_lbl.pack(expand=True, pady=4)

        # 프리셋 버튼들
        preset_row = ctk.CTkFrame(self.content_area, fg_color="transparent")
        preset_row.pack(fill="x", pady=2)
        for s, lbl in [(60, "1분"), (180, "3분"), (300, "5분"), (600, "10분")]:
            ctk.CTkButton(
                preset_row, text=lbl, width=44, height=24, font=get_font(9, "bold"),
                fg_color=t["card_inner"], hover_color=t["accent"], text_color=t["text_main"],
                command=lambda sec=s: self.set_time(sec)
            ).pack(side="left", padx=2, expand=True)

        # 제어 버튼
        ctrl_row = ctk.CTkFrame(self.content_area, fg_color="transparent")
        ctrl_row.pack(fill="x", pady=(6, 2))

        self.btn_run = ctk.CTkButton(
            ctrl_row, text="▶ 시작", height=32, font=get_font(11, "bold"),
            fg_color=t["accent"], hover_color=t["accent_hover"],
            command=self.toggle_run
        )
        self.btn_run.pack(side="left", fill="x", expand=True, padx=2)

        ctk.CTkButton(
            ctrl_row, text="↺ 리셋", width=60, height=32, font=get_font(10, "bold"),
            fg_color=t["card_inner"], hover_color=t["border"], text_color=t["text_main"],
            command=self.reset_timer
        ) .pack(side="left", padx=2)

    def set_time(self, sec):
        self.reset_timer()
        self.total_seconds = sec
        self.remaining_seconds = sec
        self._update_disp()

    def toggle_run(self):
        if self.is_running:
            self.is_running = False
            if self._job:
                self.after_cancel(self._job)
                self._job = None
            self.btn_run.configure(text="▶ 재개", fg_color=self.t["accent"])
        else:
            self.is_running = True
            self.btn_run.configure(text="⏸ 정지", fg_color="#ea580c")
            self._tick()

    def _tick(self):
        if not self.is_running:
            return
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self._update_disp()
            self._job = self.after(1000, self._tick)
        else:
            self.is_running = False
            self.btn_run.configure(text="▶ 시작", fg_color=self.t["accent"])
            self.disp_lbl.configure(text="시간 종료!", text_color="#ef4444")
            try: winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception: pass

    def reset_timer(self):
        self.is_running = False
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        self.remaining_seconds = self.total_seconds
        self.btn_run.configure(text="▶ 시작", fg_color=self.t["accent"])
        self._update_disp()

    def _update_disp(self):
        m = self.remaining_seconds // 60
        s = self.remaining_seconds % 60
        self.disp_lbl.configure(text=f"{m:02d}:{s:02d}", text_color=self.t["accent"])


# =============================================================================
# 2. 발표자 뽑기 위젯 (학생 이름 모드, 번호 모드, 성별 필터)
# =============================================================================
class PickerWidget(FloatingBoardWidget):
    def __init__(self, parent, widget_id, x=400, y=60, w=340, h=300, **kwargs):
        super().__init__(parent, widget_id, "picker", "🎯 발표자 추첨", x, y, w, h, **kwargs)
        self.picked_history = []
        self._is_picking = False
        self._build_content()

    def _build_content(self):
        t = self.t
        # 상단 모드 및 성별 필터
        top_bar = ctk.CTkFrame(self.content_area, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 4))

        self.mode_seg = ctk.CTkSegmentedButton(
            top_bar, values=["이름", "번호"], font=get_font(9, "bold"), height=24,
            command=lambda v: self.reset_history()
        )
        self.mode_seg.set("이름")
        self.mode_seg.pack(side="left")

        self.gender_seg = ctk.CTkSegmentedButton(
            top_bar, values=["전체", "👦남", "👧여"], font=get_font(9, "bold"), height=24,
            command=lambda v: self.reset_history()
        )
        self.gender_seg.set("전체")
        self.gender_seg.pack(side="right")

        # 전광판
        disp_card = ctk.CTkFrame(self.content_area, fg_color=t["card_inner"], corner_radius=10, border_width=1, border_color=t["border"])
        disp_card.pack(fill="both", expand=True, pady=4)

        self.winner_lbl = ctk.CTkLabel(
            disp_card,
            text="?",
            font=ctk.CTkFont(family="Malgun Gothic", size=42, weight="bold"),
            text_color=t["accent"]
        )
        self.winner_lbl.pack(expand=True)

        # 뽑기 버튼
        self.pick_btn = ctk.CTkButton(
            self.content_area, text="🎲 추첨하기", font=get_font(12, "bold"), height=34,
            fg_color=t["accent"], hover_color=t["accent_hover"],
            command=self.start_pick
        )
        self.pick_btn.pack(fill="x", pady=2)

        # 히스토리 텍스트
        self.hist_lbl = ctk.CTkLabel(
            self.content_area, text="뽑힌 기록: 없음", font=get_font(9),
            text_color=t["text_sub"], wraplength=300
        )
        self.hist_lbl.pack(fill="x", pady=(2, 0))

    def start_pick(self):
        if self._is_picking:
            return

        is_name = (self.mode_seg.get() == "이름")
        g_val = self.gender_seg.get()
        gender = "남" if "남" in g_val else ("여" if "여" in g_val else None)

        students = student_manager.get_student_list(gender)
        if is_name and students:
            candidates = []
            for s in students:
                nm = s.get("name", "")
                gen = s.get("gender", "")
                tag = " 👦" if gen == "남" else (" 👧" if gen == "여" else "")
                candidates.append(f"{s['number']}번 {nm}{tag}" if nm else f"{s['number']}번{tag}")
        else:
            candidates = [f"{i}번" for i in range(1, 26)]

        available = [c for c in candidates if c not in self.picked_history]
        if not available:
            self.winner_lbl.configure(text="완료!", text_color="#10b981")
            self.hist_lbl.configure(text="모든 학생이 다 뽑혔습니다!")
            return

        self._is_picking = True
        self.pick_btn.configure(state="disabled")

        def _rolling(step=0):
            if step < 14:
                temp = random.choice(candidates)
                self.winner_lbl.configure(text=temp, text_color=self.t["text_main"])
                self.after(50 + step * 10, lambda: _rolling(step + 1))
            else:
                winner = random.choice(available)
                self.picked_history.append(winner)
                self.winner_lbl.configure(text=winner, text_color="#10b981")
                self.hist_lbl.configure(text=f"기록 ({len(self.picked_history)}명): {', '.join(self.picked_history)}")
                self._is_picking = False
                self.pick_btn.configure(state="normal")
                try: winsound.MessageBeep(winsound.MB_OK)
                except Exception: pass

        _rolling()

    def reset_history(self):
        self.picked_history.clear()
        self.winner_lbl.configure(text="?", text_color=self.t["accent"])
        self.hist_lbl.configure(text="뽑힌 기록: 없음")


# =============================================================================
# 3. 주사위 위젯 (D4~D20, 2개 주사위, 비, 비율, 백분율 실시간 통계 표)
# =============================================================================
class DiceWidget(FloatingBoardWidget):
    DICE_CHARS = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}

    def __init__(self, parent, widget_id, x=60, y=330, w=440, h=340, **kwargs):
        super().__init__(parent, widget_id, "dice", "🎲 스마트 주사위 & 통계", x, y, w, h, **kwargs)
        self.dice_count = 1  # 1 or 2
        self.max_face = 6    # 면 수
        self.roll_history = []  # [{roll, d1, d2, sum}]
        self.face_counts = {}   # {val: count}
        self._is_rolling = False
        self._build_content()

    def _build_content(self):
        t = self.t
        # 상단 설정 바: 주사위 개수 & 면 수 선택
        cfg_bar = ctk.CTkFrame(self.content_area, fg_color="transparent")
        cfg_bar.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(cfg_bar, text="개수:", font=get_font(9, "bold"), text_color=t["text_sub"]).pack(side="left")
        self.dice_cnt_seg = ctk.CTkSegmentedButton(
            cfg_bar, values=["1개", "2개"], font=get_font(9, "bold"), height=24,
            command=self._on_cnt_changed
        )
        self.dice_cnt_seg.set("1개")
        self.dice_cnt_seg.pack(side="left", padx=(2, 8))

        ctk.CTkLabel(cfg_bar, text="면수:", font=get_font(9, "bold"), text_color=t["text_sub"]).pack(side="left")
        self.face_combo = ctk.CTkComboBox(
            cfg_bar, values=["D6 (6면)", "D4 (4면)", "D8 (8면)", "D10 (10면)", "D12 (12면)", "D20 (20면)", "D100 (100면)"],
            width=100, height=24, font=get_font(9, "bold"), state="readonly", command=self._on_face_changed
        )
        self.face_combo.set("D6 (6면)")
        self.face_combo.pack(side="left", padx=2)

        # 메인 주사위 전광판 + 통계 표 분할 컨테이너
        self.split_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.split_frame.pack(fill="both", expand=True, pady=2)

        # 좌측: 대형 주사위 디스플레이
        self.left_box = ctk.CTkFrame(self.split_frame, fg_color=t["card_inner"], corner_radius=10)
        self.left_box.pack(side="left", fill="both", expand=True, padx=(0, 4))

        self.dice_disp_lbl = ctk.CTkLabel(
            self.left_box, text="⚅", font=ctk.CTkFont(family="Segoe UI Symbol", size=60),
            text_color=t["accent"]
        )
        self.dice_disp_lbl.pack(expand=True)

        self.sub_val_lbl = ctk.CTkLabel(self.left_box, text="결과: 6", font=get_font(12, "bold"), text_color=t["text_main"])
        self.sub_val_lbl.pack(pady=(0, 6))

        # 우측: 비 / 비율 / 백분율 통계 스크롤 표
        self.right_table_box = ctk.CTkFrame(self.split_frame, fg_color=t["card_inner"], corner_radius=10)
        self.right_table_box.pack(side="right", fill="both", expand=True, padx=(4, 0))

        tbl_hdr = ctk.CTkFrame(self.right_table_box, fg_color="transparent", height=20)
        tbl_hdr.pack(fill="x", padx=6, pady=2)
        ctk.CTkLabel(tbl_hdr, text="📊 비 / 비율 / 백분율 통계", font=get_font(9, "bold"), text_color=t["accent"]).pack(side="left")

        self.table_scroll = ctk.CTkScrollableFrame(self.right_table_box, fg_color="transparent", height=130)
        self.table_scroll.pack(fill="both", expand=True, padx=4, pady=2)
        self._render_stats_table()

        # 하단 굴리기 버튼 바
        b_bar = ctk.CTkFrame(self.content_area, fg_color="transparent")
        b_bar.pack(fill="x", pady=(4, 0))

        self.roll_btn = ctk.CTkButton(
            b_bar, text="🎲 주사위 굴리기!", font=get_font(11, "bold"), height=32,
            fg_color=t["accent"], hover_color=t["accent_hover"], command=self.roll
        )
        self.roll_btn.pack(side="left", fill="x", expand=True, padx=2)

        ctk.CTkButton(
            b_bar, text="통계 초기화", width=70, height=32, font=get_font(9, "bold"),
            fg_color=t["card_inner"], hover_color="#dc2626", text_color=t["text_main"],
            command=self.reset_stats
        ).pack(side="left", padx=2)

    def _on_cnt_changed(self, choice):
        self.dice_count = 2 if choice == "2개" else 1
        self._update_dice_display(6, 6 if self.dice_count == 2 else None)

    def _on_face_changed(self, choice):
        num_str = choice.split("(")[1].replace("면)", "")
        self.max_face = int(num_str)
        self._update_dice_display(self.max_face, self.max_face if self.dice_count == 2 else None)

    def roll(self):
        if self._is_rolling:
            return
        self._is_rolling = True
        self.roll_btn.configure(state="disabled")

        def _anim(step=0):
            if step < 12:
                r1 = random.randint(1, self.max_face)
                r2 = random.randint(1, self.max_face) if self.dice_count == 2 else None
                self._update_dice_display(r1, r2)
                self.after(50 + step * 8, lambda: _anim(step + 1))
            else:
                final1 = random.randint(1, self.max_face)
                final2 = random.randint(1, self.max_face) if self.dice_count == 2 else None
                self._update_dice_display(final1, final2)

                # 기록 및 통계 집계
                total = final1 + (final2 or 0)
                self.roll_history.append({"roll": len(self.roll_history)+1, "d1": final1, "d2": final2, "sum": total})
                self.face_counts[final1] = self.face_counts.get(final1, 0) + 1
                if final2 is not None:
                    self.face_counts[final2] = self.face_counts.get(final2, 0) + 1

                self._render_stats_table()
                self._is_rolling = False
                self.roll_btn.configure(state="normal")
                try: winsound.MessageBeep(winsound.MB_OK)
                except Exception: pass

        _anim()

    def _update_dice_display(self, v1, v2=None):
        if self.max_face == 6 and v1 in self.DICE_CHARS and (v2 is None or v2 in self.DICE_CHARS):
            if v2 is None:
                self.dice_disp_lbl.configure(text=self.DICE_CHARS[v1], font=ctk.CTkFont(family="Segoe UI Symbol", size=60))
                self.sub_val_lbl.configure(text=f"눈: {v1}")
            else:
                self.dice_disp_lbl.configure(text=f"{self.DICE_CHARS[v1]} {self.DICE_CHARS[v2]}", font=ctk.CTkFont(family="Segoe UI Symbol", size=48))
                self.sub_val_lbl.configure(text=f"A={v1}, B={v2} (합={v1+v2})")
        else:
            if v2 is None:
                self.dice_disp_lbl.configure(text=str(v1), font=ctk.CTkFont(family="Consolas", size=54, weight="bold"))
                self.sub_val_lbl.configure(text=f"숫자: {v1} (D{self.max_face})")
            else:
                self.dice_disp_lbl.configure(text=f"{v1} + {v2}", font=ctk.CTkFont(family="Consolas", size=42, weight="bold"))
                self.sub_val_lbl.configure(text=f"A={v1}, B={v2} (합={v1+v2})")

    def _render_stats_table(self):
        for w in self.table_scroll.winfo_children():
            w.destroy()

        t = self.t
        total_rolls = len(self.roll_history)
        if total_rolls == 0:
            ctk.CTkLabel(self.table_scroll, text="주사위를 굴리면\n비·비율·백분율이 집계됩니다.", font=get_font(9), text_color=t["text_sub"]).pack(pady=20)
            return

        # 테이블 헤더
        h_row = ctk.CTkFrame(self.table_scroll, fg_color=t["card_inner"], corner_radius=4)
        h_row.pack(fill="x", pady=1)
        ctk.CTkLabel(h_row, text="눈", width=26, font=get_font(9, "bold"), text_color=t["accent"]).pack(side="left")
        ctk.CTkLabel(h_row, text="빈도", width=34, font=get_font(9, "bold"), text_color=t["text_main"]).pack(side="left")
        ctk.CTkLabel(h_row, text="비(比)", width=48, font=get_font(9, "bold"), text_color=t["text_sub"]).pack(side="left")
        ctk.CTkLabel(h_row, text="비율", width=42, font=get_font(9, "bold"), text_color=t["text_sub"]).pack(side="left")
        ctk.CTkLabel(h_row, text="백분율(%)", width=54, font=get_font(9, "bold"), text_color="#10b981").pack(side="left")

        # 총 주사위 나온 횟수
        total_dice_throws = sum(self.face_counts.values())

        for face in range(1, min(self.max_face + 1, 21)):
            cnt = self.face_counts.get(face, 0)
            ratio = (cnt / total_dice_throws) if total_dice_throws > 0 else 0.0
            pct = ratio * 100

            row = ctk.CTkFrame(self.table_scroll, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=str(face), width=26, font=ctk.CTkFont(family="Consolas", size=9, weight="bold"), text_color=t["text_main"]).pack(side="left")
            ctk.CTkLabel(row, text=f"{cnt}회", width=34, font=get_font(8), text_color=t["text_sub"]).pack(side="left")
            ctk.CTkLabel(row, text=f"{cnt}:{total_dice_throws}", width=48, font=ctk.CTkFont(family="Consolas", size=8), text_color=t["text_sub"]).pack(side="left")
            ctk.CTkLabel(row, text=f"{ratio:.3f}", width=42, font=ctk.CTkFont(family="Consolas", size=8), text_color=t["text_sub"]).pack(side="left")
            ctk.CTkLabel(row, text=f"{pct:.1f}%", width=54, font=ctk.CTkFont(family="Consolas", size=9, weight="bold"), text_color="#10b981").pack(side="left")

    def reset_stats(self):
        self.roll_history.clear()
        self.face_counts.clear()
        self._render_stats_table()
        self._update_dice_display(6, 6 if self.dice_count == 2 else None)


# =============================================================================
# 4. 돌림판 위젯
# =============================================================================
class WheelWidget(FloatingBoardWidget):
    def __init__(self, parent, widget_id, x=450, y=330, w=340, h=300, **kwargs):
        super().__init__(parent, widget_id, "wheel", "🎡 돌려돌려 돌림판", x, y, w, h, **kwargs)
        self.items = ["1모둠", "2모둠", "3모둠", "4모둠", "5모둠", "6모둠"]
        self._is_spinning = False
        self._build_content()

    def _build_content(self):
        t = self.t
        self.wheel_lbl = ctk.CTkLabel(
            self.content_area, text="🎡", font=ctk.CTkFont(size=56)
        )
        self.wheel_lbl.pack(pady=4)

        self.res_lbl = ctk.CTkLabel(
            self.content_area, text="행운의 돌림판을 돌려보세요!",
            font=get_font(12, "bold"), text_color=t["text_main"]
        )
        self.res_lbl.pack(pady=4)

        spin_btn = ctk.CTkButton(
            self.content_area, text="🎡 돌리기!", font=get_font(11, "bold"), height=34,
            fg_color=t["accent"], hover_color=t["accent_hover"], command=self.spin
        )
        spin_btn.pack(fill="x", pady=4)

    def spin(self):
        if self._is_spinning:
            return
        self._is_spinning = True

        def _step(cnt=0):
            if cnt < 16:
                cur = random.choice(self.items)
                self.res_lbl.configure(text=f"▶ {cur}", text_color=self.t["accent"])
                self.after(50 + cnt * 15, lambda: _step(cnt + 1))
            else:
                winner = random.choice(self.items)
                self.res_lbl.configure(text=f"🎉 당첨: {winner}!", text_color="#10b981")
                self._is_spinning = False
                try: winsound.MessageBeep(winsound.MB_OK)
                except Exception: pass

        _step()


# =============================================================================
# 5. 점수판 위젯
# =============================================================================
class ScoreboardWidget(FloatingBoardWidget):
    def __init__(self, parent, widget_id, x=800, y=60, w=320, h=300, **kwargs):
        super().__init__(parent, widget_id, "scoreboard", "🏆 모둠 점수판", x, y, w, h, **kwargs)
        self.scores = {f"{i}모둠": 0 for i in range(1, 7)}
        self._build_content()

    def _build_content(self):
        t = self.t
        grid = ctk.CTkFrame(self.content_area, fg_color="transparent")
        grid.pack(fill="both", expand=True)

        self.score_lbls = {}
        for idx, (grp, sc) in enumerate(self.scores.items()):
            r = idx // 3
            c = idx % 3

            card = ctk.CTkFrame(grid, fg_color=t["card_inner"], corner_radius=8)
            card.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")
            grid.grid_columnconfigure(c, weight=1)

            ctk.CTkLabel(card, text=grp, font=get_font(9, "bold"), text_color=t["text_sub"]).pack(pady=(2, 0))
            lbl = ctk.CTkLabel(card, text=str(sc), font=ctk.CTkFont(family="Consolas", size=18, weight="bold"), text_color=t["accent"])
            lbl.pack()
            self.score_lbls[grp] = lbl

            btn_row = ctk.CTkFrame(card, fg_color="transparent")
            btn_row.pack(pady=(0, 2))
            ctk.CTkButton(btn_row, text="+", width=22, height=18, font=get_font(9, "bold"), command=lambda g=grp: self.add(g, 1)).pack(side="left", padx=1)
            ctk.CTkButton(btn_row, text="-", width=22, height=18, font=get_font(9, "bold"), fg_color="#334155", command=lambda g=grp: self.add(g, -1)).pack(side="left", padx=1)

    def add(self, grp, delta):
        self.scores[grp] = max(0, self.scores[grp] + delta)
        self.score_lbls[grp].configure(text=str(self.scores[grp]))


# =============================================================================
# 6. 시간표 위젯
# =============================================================================
class TimetableWidget(FloatingBoardWidget):
    def __init__(self, parent, widget_id, x=800, y=380, w=300, h=280, **kwargs):
        super().__init__(parent, widget_id, "timetable", "📅 오늘의 시간표", x, y, w, h, **kwargs)
        self._build_content()

    def _build_content(self):
        t = self.t
        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        _, _, items = timetable_manager.get_today_schedule_items()
        now_s = datetime.datetime.now().strftime("%H:%M")

        for it in items:
            is_l = it["is_lunch"]
            start_s, end_s = it["start"], it["end"]
            is_cur = (start_s <= now_s <= end_s)

            row = ctk.CTkFrame(scroll, fg_color=t["accent"] if is_cur else t["card_inner"], corner_radius=6)
            row.pack(fill="x", pady=2)

            txt = f"{it['name']} ({it['start']})"
            ctk.CTkLabel(row, text=txt, font=get_font(9, "bold"), text_color="#ffffff" if is_cur else t["text_sub"]).pack(side="left", padx=6, pady=3)
            sub = "점심시간" if is_l else it["subject"]
            ctk.CTkLabel(row, text=sub, font=get_font(10, "bold"), text_color="#ffffff" if is_cur else t["text_main"]).pack(side="right", padx=6)


# =============================================================================
# 7. 급식 식단 위젯
# =============================================================================
class MealWidget(FloatingBoardWidget):
    def __init__(self, parent, widget_id, x=100, y=100, w=280, h=260, **kwargs):
        super().__init__(parent, widget_id, "meal", "🍱 오늘의 급식", x, y, w, h, **kwargs)
        self._build_content()

    def _build_content(self):
        t = self.t
        today = datetime.date.today()
        ok, meal_info, _ = neis_client.get_meal_for_date(today)

        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        if not ok or not meal_info.get("dishes"):
            ctk.CTkLabel(scroll, text="오늘 등록된 급식이 없습니다.", font=get_font(10), text_color=t["text_sub"]).pack(pady=20)
            return

        for d in meal_info.get("dishes", []):
            ctk.CTkLabel(scroll, text=f"• {d}", font=get_font(10), text_color=t["text_main"], anchor="w").pack(fill="x", pady=2, padx=4)


# =============================================================================
# 8. 메모 / 알림장 위젯
# =============================================================================
class MemoWidget(FloatingBoardWidget):
    def __init__(self, parent, widget_id, x=100, y=360, w=300, h=240, **kwargs):
        super().__init__(parent, widget_id, "memo", "📝 학급 알림장 / 메모", x, y, w, h, **kwargs)
        self._build_content()

    def _build_content(self):
        self.txt = ctk.CTkTextbox(self.content_area, font=get_font(11), fg_color=self.t["card_inner"], text_color=self.t["text_main"])
        self.txt.pack(fill="both", expand=True, pady=2)
        self.txt.insert("1.0", "• 1교시 준비물: 수학익힘책\n• 5교시 체육복 착용\n• 하교 후 손 씻기!")


# =============================================================================
# 위젯 팩토리 (Widget Factory)
# =============================================================================
WIDGET_CLASSES = {
    "timer": TimerWidget,
    "picker": PickerWidget,
    "dice": DiceWidget,
    "wheel": WheelWidget,
    "scoreboard": ScoreboardWidget,
    "timetable": TimetableWidget,
    "meal": MealWidget,
    "memo": MemoWidget,
}

def create_board_widget(parent_canvas, w_type: str, w_id: str, x=50, y=50, w=320, h=260, **kwargs):
    cls = WIDGET_CLASSES.get(w_type, TimerWidget)
    return cls(parent_canvas, w_id, x=x, y=y, w=w, h=h, **kwargs)
