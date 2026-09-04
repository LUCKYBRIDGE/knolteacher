import os
import sys
import json
import datetime
import customtkinter as ctk
from typing import Optional
from src.font_config import setup_global_fonts, get_font
from src.timetable_manager import timetable_manager, DAYS_KO
from src.config_utils import get_config_dir
from src.system_monitor import system_monitor

class MiniTickerWidget(ctk.CTkToplevel):
    """
    Apple Dynamic Island 감성의 세련된 올웨이즈온 미니 정보 바 위젯
    """
    POS_FILE = os.path.join(get_config_dir(), "widget_dock_config.json")

    def __init__(self, scheduler_manager, parent=None):
        super().__init__(parent)
        self.scheduler_manager = scheduler_manager
        self.title("미니 상태 도크")
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        setup_global_fonts(self)

        self.dock_mode = "bottom_dock"
        self.opacity = 0.95
        self.load_dock_config()

        self._drag_start_x = 0
        self._drag_start_y = 0

        self._build_ui()
        self._apply_dock_position(self.dock_mode, save=False)
        self._update_loop()
        system_monitor.register_listener(self._on_metrics_updated)

    def load_dock_config(self):
        if os.path.exists(self.POS_FILE):
            try:
                with open(self.POS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.dock_mode = data.get("dock_mode", "bottom_dock")
                    self.opacity = data.get("opacity", 0.95)
            except Exception as e:
                print(f"Error loading dock config: {e}")

    def save_dock_config(self):
        try:
            with open(self.POS_FILE, "w", encoding="utf-8") as f:
                json.dump({"dock_mode": self.dock_mode, "opacity": self.opacity}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving dock config: {e}")

    def _build_ui(self):
        try:
            self.attributes("-alpha", self.opacity)
        except Exception:
            pass

        self.container = ctk.CTkFrame(
            self, 
            fg_color="#0b0f19", 
            corner_radius=14, 
            border_width=1, 
            border_color="#0a84ff"
        )
        self.container.pack(fill="both", expand=True)

        self.container.bind("<Button-1>", self._start_drag)
        self.container.bind("<B1-Motion>", self._on_drag)

        self.main_layout = ctk.CTkFrame(self.container, fg_color="transparent")
        self.main_layout.pack(fill="both", expand=True, padx=8, pady=4)

        # 1. 드래그 핸들 (macOS 그립 스타일)
        self.handle_lbl = ctk.CTkLabel(self.main_layout, text="⠿", font=get_font(13, "bold"), text_color="#475569", width=16)
        self.handle_lbl.pack(side="left", padx=(2, 2))
        self.handle_lbl.bind("<Button-1>", self._start_drag)
        self.handle_lbl.bind("<B1-Motion>", self._on_drag)

        # 2. 디지털 시계 (Apple Watch Monospace 스타일)
        self.clock_lbl = ctk.CTkLabel(
            self.main_layout,
            text="00:00:00",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color="#30d158",
            width=70
        )
        self.clock_lbl.pack(side="left", padx=4)

        # 구분선
        self.div_lbl = ctk.CTkLabel(self.main_layout, text="|", font=get_font(11), text_color="#1e293b")
        self.div_lbl.pack(side="left", padx=2)

        # 3. 실시간 수업/일과 정보 (직관적인 텍스트)
        self.status_lbl = ctk.CTkLabel(
            self.main_layout,
            text="시간표 확인 중...",
            font=get_font(12, "bold"),
            text_color="#f8fafc",
            anchor="w"
        )
        self.status_lbl.pack(side="left", fill="x", expand=True, padx=6)
        self.status_lbl.bind("<Button-1>", self._start_drag)
        self.status_lbl.bind("<B1-Motion>", self._on_drag)

        # 4. 전원/예약 뱃지 (Pill Badge)
        self.power_badge = ctk.CTkLabel(
            self.main_layout,
            text="🏢 자동종료 대기",
            font=get_font(10, "bold"),
            fg_color="#161e31",
            text_color="#94a3b8",
            corner_radius=8,
            height=26,
            width=92
        )
        self.power_badge.pack(side="right", padx=(0, 4))

        # 4-1. 실시간 PC 자원 뱃지
        self.res_badge = ctk.CTkLabel(
            self.main_layout,
            text="💻--%",
            font=get_font(9, "bold"),
            fg_color="#111827",
            text_color="#38bdf8",
            corner_radius=6,
            height=24,
            width=48
        )
        self.res_badge.pack(side="right", padx=(0, 4))

        # 5. 위치 선택 팝업 버튼
        self.dock_menu_btn = ctk.CTkButton(
            self.main_layout,
            text="📍",
            font=get_font(11),
            width=26,
            height=26,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#cbd5e1",
            corner_radius=7,
            command=self._show_dock_popup_menu
        )
        self.dock_menu_btn.pack(side="right", padx=2)

        # 6. 최소화 버튼
        min_btn = ctk.CTkButton(
            self.main_layout,
            text="—",
            font=get_font(10, "bold"),
            width=24,
            height=24,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#cbd5e1",
            corner_radius=6,
            command=self.iconify
        )
        min_btn.pack(side="right", padx=2)

        # 7. 닫기 버튼
        close_btn = ctk.CTkButton(
            self.main_layout,
            text="✕",
            font=get_font(10, "bold"),
            width=24,
            height=24,
            fg_color="#3f1d24",
            hover_color="#dc2626",
            text_color="#fca5a5",
            corner_radius=6,
            command=self.destroy
        )
        close_btn.pack(side="right", padx=(2, 2))

    def _show_dock_popup_menu(self):
        menu_win = ctk.CTkToplevel(self)
        menu_win.title("고정 위치 선택")
        menu_win.geometry("250x270")
        menu_win.resizable(False, False)
        menu_win.attributes("-topmost", True)
        setup_global_fonts(menu_win)

        bx = self.winfo_x() + max(0, self.winfo_width() - 260)
        by = max(10, self.winfo_y() - 280 if self.winfo_y() > 300 else self.winfo_y() + 50)
        menu_win.geometry(f"250x270+{bx}+{by}")

        container = ctk.CTkFrame(menu_win, fg_color="#0b0f19", corner_radius=12, border_width=1, border_color="#1e293b")
        container.pack(fill="both", expand=True, padx=6, pady=6)

        ctk.CTkLabel(container, text="📌 미니바 고정 위치 선택", font=get_font(12, "bold"), text_color="#0a84ff").pack(pady=(6, 4))

        presets = [
            ("bottom_dock", "⬇️ 작업표시줄 약간 위"),
            ("top_dock", "⬆️ 화면 상단 중앙 (노치)"),
            ("left_side", "⬅️ 모니터 좌측 사이드"),
            ("right_side", "➡️ 모니터 우측 사이드"),
            ("bottom_right", "↘️ 우측 하단 트레이 위"),
            ("free", "✋ 자유 위치 이동 (드래그)")
        ]

        for p_key, p_name in presets:
            btn = ctk.CTkButton(
                container,
                text=p_name,
                font=get_font(11, "bold" if self.dock_mode == p_key else "normal"),
                height=30,
                corner_radius=8,
                fg_color="#0a84ff" if self.dock_mode == p_key else "transparent",
                hover_color="#0071e3" if self.dock_mode == p_key else "#1e293b",
                text_color="#ffffff" if self.dock_mode == p_key else "#cbd5e1",
                anchor="w",
                command=lambda k=p_key, w=menu_win: [self._apply_dock_position(k), w.destroy()]
            )
            btn.pack(fill="x", padx=6, pady=2)

    def _apply_dock_position(self, mode: str, save: bool = True):
        self.dock_mode = mode
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        if mode == "bottom_dock":
            w, h = 600, 44
            x = (sw - w) // 2
            y = max(10, sh - 95)
            self.geometry(f"{w}x{h}+{x}+{y}")
        elif mode == "top_dock":
            w, h = 600, 44
            x = (sw - w) // 2
            y = 10
            self.geometry(f"{w}x{h}+{x}+{y}")
        elif mode == "left_side":
            w, h = 480, 44
            x = 15
            y = (sh - h) // 2
            self.geometry(f"{w}x{h}+{x}+{y}")
        elif mode == "right_side":
            w, h = 480, 44
            x = max(10, sw - w - 15)
            y = (sh - h) // 2
            self.geometry(f"{w}x{h}+{x}+{y}")
        elif mode == "bottom_right":
            w, h = 460, 44
            x = max(10, sw - w - 20)
            y = max(10, sh - 95)
            self.geometry(f"{w}x{h}+{x}+{y}")

        if save:
            self.save_dock_config()

    def _start_drag(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag(self, event):
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")
        self.dock_mode = "free"

    def _update_loop(self):
        now = datetime.datetime.now()
        self.clock_lbl.configure(text=now.strftime("%H:%M:%S"))

        is_hol, hol_name, items = timetable_manager.get_today_schedule_items()
        now_str = now.strftime("%H:%M")

        if is_hol:
            self.status_lbl.configure(text=f"🇰🇷 오늘은 [{hol_name}] 공휴일입니다.", text_color="#ff9f0a")
        else:
            current_period = None
            next_period = None

            for it in items:
                start_s, end_s = it["start"], it["end"]
                if start_s <= now_str <= end_s:
                    current_period = it
                elif now_str < start_s and not next_period and not it["is_lunch"]:
                    next_period = it

            if current_period:
                p_name = current_period["name"]
                p_subj = current_period["subject"]
                is_lunch = current_period.get("is_lunch", False)
                if is_lunch:
                    try:
                        from src.neis_client import neis_client
                        ok, m_info, _ = neis_client.get_meal_for_date(now.date())
                        if ok and m_info.get("dishes"):
                            short_menu = ", ".join([d.split("(")[0].strip() for d in m_info["dishes"][:3]])
                            self.status_lbl.configure(
                                text=f"🍱 [점심시간] 오늘 메뉴: {short_menu}",
                                text_color="#fb923c"
                            )
                        else:
                            self.status_lbl.configure(text="🍱 [점심시간] 맛있는 점심 식사 시간입니다.", text_color="#fb923c")
                    except Exception:
                        self.status_lbl.configure(text="🍱 [점심시간] 맛있는 점심 식사 시간입니다.", text_color="#fb923c")
                else:
                    self.status_lbl.configure(
                        text=f"▶ 진행 중: [{p_name} {p_subj}] ({current_period['start']}~{current_period['end']})",
                        text_color="#30d158"
                    )
            elif next_period:
                p_name = next_period["name"]
                p_subj = next_period["subject"]
                self.status_lbl.configure(
                    text=f"⏳ 다음 수업: [{p_name} {p_subj}] ({next_period['start']} 시작)",
                    text_color="#0a84ff"
                )
            else:
                self.status_lbl.configure(text="✨ 오늘의 모든 정규 수업이 종료되었습니다.", text_color="#94a3b8")

        # 전원/예약 상태 뱃지
        if self.scheduler_manager.is_scheduled:
            rem = self.scheduler_manager.remaining_seconds
            m, s = rem // 60, rem % 60
            self.power_badge.configure(
                text=f"⏱️ {m:02d}:{s:02d} 예약",
                fg_color="#059669",
                text_color="#ffffff"
            )
        elif self.scheduler_manager.auto_power_config.get("auto_shutdown_enabled", False):
            t_str = self.scheduler_manager.auto_power_config.get("auto_shutdown_time", "16:40")
            self.power_badge.configure(
                text=f"🏢 {t_str} 퇴근종료",
                fg_color="#1e3a8a",
                text_color="#93c5fd"
            )
        else:
            self.power_badge.configure(
                text="대기 중",
                fg_color="#161e31",
                text_color="#94a3b8"
            )

        self.after(1000, self._update_loop)

    def _on_metrics_updated(self, m: dict):
        if not self.winfo_exists():
            return
        try:
            self.after(0, self._update_res_badge, m)
        except Exception:
            pass

    def _update_res_badge(self, m: dict):
        if hasattr(self, "res_badge") and self.res_badge.winfo_exists():
            c_p = int(m.get("cpu_percent", 0))
            self.res_badge.configure(
                text=f"💻{c_p}%",
                text_color="#ef4444" if c_p > 85 else ("#f59e0b" if c_p > 60 else "#38bdf8")
            )
