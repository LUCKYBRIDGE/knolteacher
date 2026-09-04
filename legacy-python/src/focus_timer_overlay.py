import os
import sys
import threading
import winsound
import tkinter as tk
import customtkinter as ctk
from src.font_config import setup_global_fonts, get_font


class FocusTimerOverlayWindow(tk.Toplevel):
    """
    Alt+3: 흰 화면 위 검정 타이머 (교실 집중 타이머)
    - 흰 배경 위에 크고 또렷한 검은색 숫자
    - 마우스 스크롤(휠)로 시간 초간편 조절 (+/- 30초, Shift 시 5분)
    - 클릭 시 시작/일시정지
    - 자그마한 옵션: 종료 10초 전 시계음(째깍째깍), 종료 시 알람음(폭발음)
    - ESC 또는 Alt+3으로 종료
    """
    _instance = None

    @classmethod
    def toggle(cls):
        if cls._instance and cls._instance.winfo_exists():
            cls._instance.close()
        else:
            cls._instance = cls()

    def __init__(self):
        super().__init__()
        self.title("교실 화이트 타이머")
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.configure(bg="#ffffff")

        self.sw = self.winfo_screenwidth()
        self.sh = self.winfo_screenheight()

        self.seconds = 300  # 기본 5분
        self.is_running = False
        self.timer_job = None

        # 옵션
        self.sound_10s = tk.BooleanVar(value=True)
        self.sound_end = tk.BooleanVar(value=True)

        self._build_ui()
        self.bind("<Escape>", lambda e: self.close())
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<space>", lambda e: self._toggle_timer())

    def _build_ui(self):
        # 상단 자그마한 옵션 바
        opt_bar = tk.Frame(self, bg="#ffffff")
        opt_bar.pack(side="top", fill="x", pady=(24, 0))

        opt_inner = tk.Frame(opt_bar, bg="#ffffff")
        opt_inner.pack(anchor="center")

        chk_10s = tk.Checkbutton(
            opt_inner, text="⏰ 종료 10초 전 시계음(째깍째깍)",
            variable=self.sound_10s, font=("Malgun Gothic", 11, "bold"),
            fg="#475569", bg="#ffffff", activebackground="#ffffff",
            selectcolor="#f1f5f9"
        )
        chk_10s.pack(side="left", padx=16)

        chk_end = tk.Checkbutton(
            opt_inner, text="💥 종료 시 알람음(폭발음)",
            variable=self.sound_end, font=("Malgun Gothic", 11, "bold"),
            fg="#475569", bg="#ffffff", activebackground="#ffffff",
            selectcolor="#f1f5f9"
        )
        chk_end.pack(side="left", padx=16)

        # 중앙 캔버스 (대형 숫자 타이머)
        self.canvas = tk.Canvas(self, bg="#ffffff", highlightthickness=0, cursor="hand2")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Button-1>", lambda e: self._toggle_timer())
        self.canvas.bind("<MouseWheel>", self._on_wheel)

        # 하단 힌트 바
        hint_bar = tk.Frame(self, bg="#ffffff")
        hint_bar.pack(side="bottom", fill="x", pady=(0, 24))

        tk.Label(
            hint_bar,
            text="[마우스 휠] 시간 조절  |  [클릭/스페이스] 시작/일시정지  |  [ESC] 나가기",
            font=("Malgun Gothic", 12, "bold"), fg="#94a3b8", bg="#ffffff"
        ).pack(anchor="center")

        self._render_display()

    def _render_display(self):
        self.canvas.delete("all")
        cx = self.sw // 2
        cy = self.sh // 2 - 20

        m, s = divmod(self.seconds, 60)
        time_str = f"{m:02d}:{s:02d}"

        # 10초 이하일 때는 빨강, 그 외엔 선명한 검정
        col = "#dc2626" if self.seconds <= 10 and self.seconds > 0 else "#0f172a"

        # 대형 시간 텍스트
        self.canvas.create_text(
            cx, cy, text=time_str,
            font=("Consolas", int(self.sh * 0.22), "bold"),
            fill=col, anchor="center"
        )

        # 재생 상태 뱃지
        status_text = "▶ 클릭하여 시작" if not self.is_running else "⏸ 일시정지 (클릭)"
        status_col = "#059669" if not self.is_running else "#ea580c"
        self.canvas.create_text(
            cx, cy + int(self.sh * 0.16),
            text=status_text,
            font=("Malgun Gothic", 16, "bold"),
            fill=status_col, anchor="center"
        )

    def _on_wheel(self, event):
        """마우스 휠로 시간 편하게 조절"""
        if self.is_running:
            return  # 작동 중일 땐 오작동 방지
        step = 60 if (event.state & 0x0001) else 30  # Shift 누르면 1분, 기본 30초
        if event.delta > 0:
            self.seconds = min(3600 * 3, self.seconds + step)
        else:
            self.seconds = max(10, self.seconds - step)
        self._render_display()

    def _toggle_timer(self):
        if self.is_running:
            self.is_running = False
            if self.timer_job:
                self.after_cancel(self.timer_job)
                self.timer_job = None
        else:
            if self.seconds <= 0:
                self.seconds = 300
            self.is_running = True
            self._tick()
        self._render_display()

    def _tick(self):
        if not self.is_running:
            return
        if self.seconds <= 0:
            self.is_running = False
            self._render_display()
            if self.sound_end.get():
                threading.Thread(target=self._play_explosion_sound, daemon=True).start()
            return

        # 10초 전 시계음
        if self.seconds <= 10 and self.sound_10s.get():
            threading.Thread(target=lambda: winsound.Beep(1400, 60), daemon=True).start()

        self.seconds -= 1
        self._render_display()
        self.timer_job = self.after(1000, self._tick)

    def _play_explosion_sound(self):
        """종료 시 알람 폭발음"""
        try:
            for freq, dur in [(600, 80), (450, 100), (320, 150), (220, 200), (140, 500)]:
                winsound.Beep(freq, dur)
        except Exception:
            pass

    def close(self):
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass
        FocusTimerOverlayWindow._instance = None
