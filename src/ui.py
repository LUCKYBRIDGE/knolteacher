import os
import sys
import datetime
import winsound
import webbrowser
import threading
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import customtkinter as ctk
from typing import Callable, Optional, Any

from src.font_config import setup_global_fonts, get_font, FONT_FAMILY
from src.scheduler_manager import SchedulerManager
from src.sound_manager import sound_manager
from src.neis_client import neis_client, OFFICE_CODES
from src.timetable_manager import timetable_manager, DAY_KEYS, DAYS_KO
from src.mini_widget import MiniTimetableWidget
from src.mini_ticker import MiniTickerWidget
from src.student_display import StudentDisplayWindow
from src.custom_board_dialog import CustomBoardLaunchDialog
from src.sheet_sync import sheet_sync_manager
from src.autostart_manager import autostart_manager
from src.drawing_overlay import ScreenDrawingOverlay
from src.floating_toolbar import FloatingQuickToolbar
from src.visualizer_window import VisualizerWindow
from src.classroom_tools import ClassroomToolsDialog
from src.system_monitor import system_monitor
from src.site_bookmarks import site_bookmark_manager, SiteBookmarksDialog
from src.theme_manager import theme_manager, THEMES
from src.config_utils import APP_VERSION, self_consolidate_and_clean
from src.github_updater import github_updater
from src.tooltip import attach_tooltip
from src.desktop_cleaner import desktop_cleaner
from src.scrollable_2d_frame import CTk2DScrollableFrame
from src.privacy_dialog import open_privacy_dialog
from src.schedule_dialog import open_schedule_dialog
from src.config_utils import get_config_dir
from src.icon_renderer import get_icon
from src.class_countdown_popup import ClassCountdownPopup
from src.neis_auto_input import (
    ExcelNeisParser, DataValidator, ValidationResult,
    NeisPageType, PAGE_INFO, NeisScriptGenerator, cdp_bridge
)

# 기본 테마: 베이지(Light 기반)
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class SchoolSearchDialog(ctk.CTkToplevel):
    def __init__(self, parent, initial_query: str, initial_office: str, on_select_callback: Callable[[dict[str, str]], None]):
        super().__init__(parent)
        self.on_select_callback = on_select_callback
        self.title("🏫 전국 학교 검색 (17개 시도 교육청 전역)")
        self.geometry("620x520")
        self.minsize(540, 420)
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()

        setup_global_fonts(self)

        parent.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        x, y = px + (pw - 620) // 2, py + (ph - 520) // 2
        self.geometry(f"620x520+{max(0, x)}+{max(0, y)}")

        self._build_ui(initial_query, initial_office)
        self._execute_search()

    def _build_ui(self, initial_query: str, initial_office: str):
        container = ctk.CTkFrame(self, fg_color="#0b0f19", corner_radius=14, border_width=1, border_color="#0a84ff")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # 상단 타이틀바 & 닫기 버튼
        top_bar = ctk.CTkFrame(container, fg_color="transparent")
        top_bar.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            top_bar,
            text="🏫 전국 학교 검색 (17개 시·도 교육청 전역)",
            font=get_font(14, "bold"),
            text_color="#38bdf8"
        ).pack(side="left")

        ctk.CTkButton(
            top_bar,
            text="✕",
            width=28,
            height=28,
            font=get_font(12, "bold"),
            fg_color="#3f1d24",
            hover_color="#dc2626",
            text_color="#fca5a5",
            corner_radius=6,
            command=self.destroy
        ).pack(side="right")

        # 상단 검색 필터 바
        filter_card = ctk.CTkFrame(container, fg_color="#161e31", corner_radius=10)
        filter_card.pack(fill="x", padx=10, pady=(6, 6))

        row1 = ctk.CTkFrame(filter_card, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(row1, text="시·도 교육청:", font=get_font(11, "bold"), text_color="#94a3b8").pack(side="left", padx=(0, 4))
        self.office_combo = ctk.CTkComboBox(
            row1,
            values=list(OFFICE_CODES.keys()),
            font=get_font(11),
            width=150,
            height=28,
            state="readonly"
        )
        self.office_combo.set(initial_office if initial_office in OFFICE_CODES else "전체 (전국)")
        self.office_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row1, text="학교급:", font=get_font(11, "bold"), text_color="#94a3b8").pack(side="left", padx=(0, 4))
        self.type_combo = ctk.CTkComboBox(
            row1,
            values=["전체", "초등학교", "중학교", "고등학교", "특수학교"],
            font=get_font(11),
            width=90,
            height=28,
            state="readonly"
        )
        self.type_combo.set("전체")
        self.type_combo.pack(side="left")

        row2 = ctk.CTkFrame(filter_card, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(4, 8))

        self.search_entry = ctk.CTkEntry(
            row2,
            placeholder_text="학교명을 입력하세요 (예: 포항, 중앙초, 서울초, 신당초)",
            font=get_font(12),
            height=32,
            fg_color="#0b0f19"
        )
        self.search_entry.insert(0, initial_query)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.search_entry.bind("<Return>", lambda e: self._execute_search())

        search_btn = ctk.CTkButton(
            row2,
            text="🔍 다시 검색",
            font=get_font(12, "bold"),
            fg_color="#0a84ff",
            hover_color="#0071e3",
            width=95,
            height=32,
            corner_radius=8,
            command=self._execute_search
        )
        search_btn.pack(side="right")

        # 결과 요약 헤더
        self.result_summary_lbl = ctk.CTkLabel(
            container,
            text="🔍 검색 중...",
            font=get_font(12, "bold"),
            text_color="#38bdf8",
            anchor="w"
        )
        self.result_summary_lbl.pack(fill="x", padx=14, pady=(4, 2))

        # 검색 결과 스크롤 영역
        self.scroll = ctk.CTkScrollableFrame(container, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _execute_search(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        query = self.search_entry.get().strip()
        if not query:
            self.result_summary_lbl.configure(text="검색할 학교명을 입력해주세요.", text_color="#f87171")
            return

        office_name = self.office_combo.get()
        office_code = OFFICE_CODES.get(office_name, "")
        type_filter = self.type_combo.get()

        self.result_summary_lbl.configure(text=f"전국 17개 교육청에서 '{query}' 검색 중...", text_color="#facc15")
        self.update()

        results = neis_client.search_school(query, office_code=office_code, school_type_filter=type_filter)

        if not results:
            self.result_summary_lbl.configure(text=f"'{query}' 검색 결과가 없습니다. (교육청이나 학교명을 확인해주세요)", text_color="#f87171")
            empty_box = ctk.CTkFrame(self.scroll, fg_color="#1e293b", corner_radius=8)
            empty_box.pack(fill="x", pady=20)
            ctk.CTkLabel(
                empty_box,
                text="일치하는 학교를 찾을 수 없습니다.\n• 지역 교육청을 '전체 (전국)'으로 설정해보세요.\n• 학교명에 띄어쓰기 없이 핵심 단어(예: '포항', '중앙')만 입력해보세요.",
                font=get_font(12),
                text_color="#94a3b8",
                justify="center"
            ).pack(pady=20)
            return

        self.result_summary_lbl.configure(text=f"✅ 전국 검색 결과: 총 {len(results)}개 학교 발견 (선택 시 바로 적용됩니다)", text_color="#30d158")

        for item in results:
            card = ctk.CTkFrame(self.scroll, fg_color="#161d2f", corner_radius=8, border_width=1, border_color="#26334d")
            card.pack(fill="x", pady=3)

            left_box = ctk.CTkFrame(card, fg_color="transparent")
            left_box.pack(side="left", fill="both", expand=True, padx=10, pady=6)

            title_row = ctk.CTkFrame(left_box, fg_color="transparent")
            title_row.pack(fill="x")

            # 학교급 뱃지
            stype = item["school_type"]
            badge_bg = "#0284c7" if "초등" in stype else ("#7c3aed" if "중학" in stype else ("#059669" if "고등" in stype else "#ea580c"))
            ctk.CTkLabel(
                title_row,
                text=stype if stype else "학교",
                font=get_font(10, "bold"),
                fg_color=badge_bg,
                text_color="#ffffff",
                corner_radius=4,
                width=48,
                height=20
            ).pack(side="left", padx=(0, 6))

            ctk.CTkLabel(
                title_row,
                text=item["school_name"],
                font=get_font(13, "bold"),
                text_color="#f8fafc"
            ).pack(side="left")

            ctk.CTkLabel(
                title_row,
                text=f"({item['office_name']})",
                font=get_font(11),
                text_color="#94a3b8"
            ).pack(side="left", padx=(6, 0))

            addr_str = item.get("address", "")
            if addr_str:
                ctk.CTkLabel(
                    left_box,
                    text=f"📍 {addr_str}",
                    font=get_font(10),
                    text_color="#64748b",
                    anchor="w"
                ).pack(fill="x", pady=(2, 0))

            select_btn = ctk.CTkButton(
                card, 
                text="선택", 
                font=get_font(11, "bold"),
                fg_color="#0a84ff",
                hover_color="#0071e3",
                width=64,
                height=32,
                corner_radius=6,
                command=lambda it=item: self._on_select(it)
            )
            select_btn.pack(side="right", padx=10, pady=6)

    def _on_select(self, item: dict[str, str]):
        if self.on_select_callback:
            self.on_select_callback(item)
        self.grab_release()
        self.destroy()


class ModernConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, message: str, action_text: str = "확인", is_danger: bool = False):
        super().__init__(parent)
        self.result = False
        self.title(title)
        self.geometry("500x320")
        self.minsize(460, 280)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()

        setup_global_fonts(self)

        parent.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        x, y = px + (pw - 500) // 2, py + (ph - 320) // 2
        self.geometry(f"500x320+{max(0, x)}+{max(0, y)}")

        self._load_icon()

        container = ctk.CTkFrame(self, corner_radius=14, fg_color="#1e2230", border_width=1, border_color="#333b50")
        container.pack(fill="both", expand=True, padx=14, pady=14)

        header_frame = ctk.CTkFrame(container, fg_color="transparent")
        header_frame.pack(fill="x", padx=18, pady=(16, 6))

        icon_char = "⚠️" if is_danger else "⏱️"
        title_label = ctk.CTkLabel(
            header_frame, 
            text=f"{icon_char}  {title}", 
            font=get_font(17, "bold"),
            text_color="#ff5252" if is_danger else "#60a5fa"
        )
        title_label.pack(side="left")

        ctk.CTkButton(
            header_frame,
            text="✕",
            width=28,
            height=28,
            font=get_font(12, "bold"),
            fg_color="#334155",
            hover_color="#ef4444",
            text_color="#cbd5e1",
            corner_radius=6,
            command=self._on_cancel
        ).pack(side="right")

        msg_label = ctk.CTkLabel(
            container, 
            text=message, 
            font=get_font(13),
            wraplength=440,
            justify="center",
            text_color="#f1f5f9"
        )
        msg_label.pack(fill="both", expand=True, padx=18, pady=8)

        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", padx=18, pady=(8, 16))

        cancel_btn = ctk.CTkButton(
            btn_frame, 
            text="취소 (ESC)", 
            font=get_font(13, "bold"),
            fg_color="#374151",
            hover_color="#4b5563",
            text_color="#ffffff",
            width=130,
            height=40,
            corner_radius=8,
            command=self._on_cancel
        )
        cancel_btn.pack(side="left", expand=True, padx=(0, 6))

        confirm_btn = ctk.CTkButton(
            btn_frame, 
            text=f"{action_text} (Enter)", 
            font=get_font(13, "bold"),
            fg_color="#dc2626" if is_danger else "#2563eb",
            hover_color="#b91c1c" if is_danger else "#1d4ed8",
            text_color="#ffffff",
            width=150,
            height=40,
            corner_radius=8,
            command=self._on_confirm
        )
        confirm_btn.pack(side="right", expand=True, padx=(6, 0))

        self.bind("<Return>", lambda e: self._on_confirm())
        self.bind("<KP_Enter>", lambda e: self._on_confirm())
        self.bind("<Escape>", lambda e: self._on_cancel())
        confirm_btn.focus_set()

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def _on_confirm(self):
        self.result = True
        self.grab_release()
        self.destroy()

    def _on_cancel(self):
        self.result = False
        self.grab_release()
        self.destroy()


class AlarmPopupDialog(ctk.CTkToplevel):
    def __init__(self, parent, memo: str, sound_id: str, on_snooze_callback: Callable[[], None]):
        super().__init__(parent)
        self.on_snooze_callback = on_snooze_callback
        self.title("🔔 회의 / 수업 / 연수 알람 알림")
        self.geometry("580x460")
        self.minsize(500, 380)
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()

        setup_global_fonts(self)

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x, y = (sw - 580) // 2, (sh - 460) // 2
        self.geometry(f"580x460+{max(0, x)}+{max(0, y)}")

        self.lift()
        self.focus_force()
        self._load_icon()

        sound_manager.start_loop(sound_id)

        container = ctk.CTkFrame(self, corner_radius=18, fg_color="#181d28", border_width=3, border_color="#f59e0b")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        header = ctk.CTkFrame(container, fg_color="#f59e0b", corner_radius=12, height=54)
        header.pack(fill="x", padx=16, pady=(16, 12))
        header.pack_propagate(False)

        header_label = ctk.CTkLabel(
            header, 
            text="🔔  회의 / 수업 / 연수 알람  🔔", 
            font=get_font(20, "bold"),
            text_color="#111827"
        )
        header_label.pack(side="left", expand=True, padx=(30, 0))

        ctk.CTkButton(
            header,
            text="✕",
            width=32,
            height=32,
            font=get_font(13, "bold"),
            fg_color="#78350f",
            hover_color="#b45309",
            text_color="#ffffff",
            corner_radius=6,
            command=self._on_dismiss
        ).pack(side="right", padx=10)

        now_str = datetime.datetime.now().strftime("%Y년 %m월 %d일 %H:%M:%S")
        time_lbl = ctk.CTkLabel(
            container, 
            text=f"현재 시각: {now_str}", 
            font=get_font(13),
            text_color="#94a3b8"
        )
        time_lbl.pack(pady=(0, 10))

        memo_card = ctk.CTkFrame(container, corner_radius=12, fg_color="#242b3d", border_width=1, border_color="#3b4660")
        memo_card.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        display_memo = memo.strip() if memo.strip() else "설정된 알람 시간입니다."
        
        memo_title = ctk.CTkLabel(
            memo_card, 
            text="📌 알람 내용 / 메모", 
            font=get_font(12, "bold"),
            text_color="#38bdf8"
        )
        memo_title.pack(anchor="w", padx=16, pady=(12, 4))

        memo_scroll = ctk.CTkScrollableFrame(memo_card, fg_color="transparent", height=100)
        memo_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        memo_text = ctk.CTkLabel(
            memo_scroll, 
            text=display_memo, 
            font=get_font(18, "bold"),
            wraplength=460,
            justify="center",
            text_color="#ffffff"
        )
        memo_text.pack(fill="both", expand=True, pady=6)

        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 16))

        snooze_btn = ctk.CTkButton(
            btn_frame, 
            text="⏱️ 5분 뒤 다시 알림 (스누즈)", 
            font=get_font(14, "bold"),
            fg_color="#334155",
            hover_color="#475569",
            text_color="#e2e8f0",
            height=46,
            corner_radius=10,
            command=self._on_snooze
        )
        snooze_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        dismiss_btn = ctk.CTkButton(
            btn_frame, 
            text="🛑 알람 끄기 (확인)", 
            font=get_font(15, "bold"),
            fg_color="#10b981",
            hover_color="#059669",
            text_color="#ffffff",
            height=46,
            corner_radius=10,
            command=self._on_dismiss
        )
        dismiss_btn.pack(side="right", fill="x", expand=True, padx=(8, 0))

        self.bind("<Return>", lambda e: self._on_dismiss())
        self.bind("<Escape>", lambda e: self._on_dismiss())
        dismiss_btn.focus_set()

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def _on_dismiss(self):
        sound_manager.stop_all()
        self.grab_release()
        self.destroy()

    def _on_snooze(self):
        sound_manager.stop_all()
        self.grab_release()
        self.destroy()
        if self.on_snooze_callback:
            self.on_snooze_callback()


class App(ctk.CTk):
    def __init__(self, manager: SchedulerManager):
        super().__init__()
        self.manager = manager
        
        setup_global_fonts(self)

        self.title(f"놀티쳐 (KnolTeacher v{APP_VERSION} - 스마트 교사용 올인원 도구)")
        self.geometry("1180x840")
        self.minsize(860, 600)
        self.resizable(True, True)

        self._load_icon()

        # 브라우저 중복 다운로드 파일((1), (2) 등) 자동 감지 및 단일 파일 유지
        self_consolidate_and_clean()

        # 내부 상태 변수들
        self.pc_action = ctk.StringVar(value="shutdown")
        self.pc_mode = ctk.StringVar(value="quick")
        self.pc_preset_minutes = ctk.IntVar(value=60)
        self.pc_custom_hours = ctk.IntVar(value=1)
        self.pc_custom_minutes = ctk.IntVar(value=0)
        self.pc_target_day = ctk.StringVar(value="today")
        
        self.alarm_mode = ctk.StringVar(value="quick")
        self.alarm_preset_minutes = ctk.IntVar(value=30)
        self.alarm_target_day = ctk.StringVar(value="today")
        self.selected_sound_id = ctk.StringVar(value="chime")

        # 엑셀 나이스 자동입력 상태 변수
        self.excel_parser = ExcelNeisParser()
        self.validation_result: Optional[ValidationResult] = None
        self.input_mode = ctk.StringVar(value="EMPTY_ONLY")
        self.selected_page_type = ctk.StringVar(value=NeisPageType.BEHAVIOR)

        # 서브 위젯들
        self.mini_widget: Optional[MiniTimetableWidget] = None
        self.mini_ticker: Optional[MiniTickerWidget] = None
        self.student_window: Optional[StudentDisplayWindow] = None

        self._build_sidebar_ui()
        self._apply_initial_theme()

        self.manager.on_tick = self._on_manager_tick
        self.manager.on_state_change = self._on_manager_state_change
        self.manager.on_alarm_triggered = self._on_manager_alarm_triggered

        system_monitor.register_listener(self._on_system_metrics_updated)

        # 시스템 트레이 초기화 (작업 표시줄 알림 영역 상주)
        from src.tray_manager import init_tray
        self.tray = init_tray(self)

        # 창 닫기 버튼(X) = 트레이로 최소화 (완전 종료는 트레이 우클릭 > 종료)
        self.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)
        self.bind("<F2>", lambda e: self._open_student_display())

        # 교실 수업 전역 단축키 매니저 (Alt+1 ~ Alt+6) 시작
        try:
            from src.hotkey_manager import hotkey_manager
            hotkey_manager.app = self
            hotkey_manager.start()
        except Exception:
            pass

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def _apply_initial_theme(self):
        theme_name = timetable_manager.settings.get("theme_mode", "Beige")
        theme_manager.set_theme(theme_name)
        palette = theme_manager.get_theme()
        ctk.set_appearance_mode(palette["ctk_mode"])

        alpha_val = timetable_manager.settings.get("window_alpha", 1.0)
        try:
            self.attributes("-alpha", alpha_val)
        except Exception:
            pass

        # 시간표 변경 실시간 감지 리스너 등록
        timetable_manager.add_listener(self._on_timetable_changed)

    # =========================================================================
    # Apple macOS 스타일 사이드바 & 다이내믹 아일랜드 상단 바
    # =========================================================================
    def _build_sidebar_ui(self):
        palette = theme_manager.get_theme()
        self.root_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.root_frame.pack(fill="both", expand=True)

        # 1. 좌측 사이드바 (너비 215px, macOS 사이드바 감성)
        self.sidebar_collapsed = False
        self.sidebar = ctk.CTkFrame(
            self.root_frame,
            width=215,
            corner_radius=0,
            fg_color=palette["sidebar_bg"],
            border_width=1,
            border_color=palette["card_border"]
        )
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar.pack_propagate(False)

        # 사이드바 상단 로고 / 브랜드
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=12, pady=(16, 10))

        title_row = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_row.pack(fill="x")

        # 세련된 앱 아이콘 뱃지
        self.logo_icon_lbl = ctk.CTkLabel(
            title_row,
            text="📅",
            font=get_font(18),
            width=26
        )
        self.logo_icon_lbl.pack(side="left", padx=(0, 6))

        self.logo_title_lbl = ctk.CTkLabel(
            title_row,
            text="놀티쳐",
            font=get_font(17, "bold"),
            text_color=palette["text_main"]
        )
        self.logo_title_lbl.pack(side="left")

        # 사이드바 접기/펼치기 토글 버튼
        self.sidebar_toggle_btn = ctk.CTkButton(
            title_row,
            text="◀",
            width=26, height=26,
            font=get_font(10, "bold"),
            fg_color="transparent",
            hover_color=palette["sidebar_btn_hover"],
            text_color=palette["text_sub"],
            corner_radius=6,
            command=self._toggle_sidebar
        )
        self.sidebar_toggle_btn.pack(side="right")
        attach_tooltip(self.sidebar_toggle_btn, "사이드바 접기 / 펼치기")

        self.logo_sub_lbl = ctk.CTkLabel(
            logo_frame,
            text="KnolTeacher • pinky-ne.com",
            font=get_font(10, "bold"),
            text_color=palette["text_sub"],
            cursor="hand2"
        )
        self.logo_sub_lbl.pack(anchor="w", padx=(32, 0), pady=(2, 0))
        self.logo_sub_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://pinky-ne.com"))
        attach_tooltip(self.logo_sub_lbl, "놀퀴즈(pinky-ne.com) 플랫폼 바로가기")

        # 🌟 최우선 시그니처 퀵 버튼: 📺 놀티쳐 보드 (학생용 대형 화면)
        self.sidebar_board_btn = ctk.CTkButton(
            self.sidebar,
            text="📺  놀티쳐 보드 열기",
            font=get_font(13, "bold"),
            height=40,
            corner_radius=8,
            fg_color=palette["accent"],
            hover_color=palette["accent_hover"],
            text_color="#ffffff",
            command=self._open_student_display
        )
        self.sidebar_board_btn.pack(fill="x", padx=10, pady=(10, 2))
        attach_tooltip(self.sidebar_board_btn, "학생용 대형 스크린 놀티쳐 보드를 즉시 실행합니다 (F2)")

        self.sidebar_custom_board_btn = ctk.CTkButton(
            self.sidebar,
            text="🛠️  커스텀 보드 띄우기",
            font=get_font(11, "bold"),
            height=28,
            corner_radius=6,
            fg_color="transparent",
            hover_color=palette["sidebar_btn_hover"],
            text_color=palette["accent"],
            border_width=1,
            border_color=palette["card_border"],
            command=self._open_custom_board_dialog
        )
        self.sidebar_custom_board_btn.pack(fill="x", padx=10, pady=(0, 6))
        attach_tooltip(self.sidebar_custom_board_btn, "화면 레이아웃, 도구, 표시 항목을 직접 조합하여 커스텀 보드를 띄웁니다")

        # 사이드바 메뉴: 교사용 핵심 탭 (이모지 자간 벌어짐 없는 2D 플랫 벡터 아이콘 장착)
        self.menu_buttons: dict[str, ctk.CTkButton] = {}
        self.menu_items = [
            ("today", "일과 & 급식", "home"),
            ("classroom_tools", "수업 도구 & 화상기", "timer"),
            ("neis_workspace", "나이스 & 시간표", "flat_timetable"),
            ("schedule_hub", "스마트 예약 센터", "flat_timer"),
            ("class_management", "학급 경영 & 모둠", "flat_trophy"),
            ("smart_desk", "스마트 데스크 & 정리", "widget"),
            ("pc_settings", "PC 관리 & 설정", "flat_memo")
        ]

        self.sidebar_scroll = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sidebar_scroll.pack(fill="both", expand=True, padx=6, pady=8)

        for key, name, ico_name in self.menu_items:
            ico = get_icon(ico_name, palette["sidebar_text"], 18)
            btn = ctk.CTkButton(
                self.sidebar_scroll,
                text=f"  {name}",
                image=ico,
                compound="left",
                font=get_font(12, "bold"),
                height=38,
                corner_radius=8,
                anchor="w",
                fg_color="transparent",
                hover_color=palette["sidebar_btn_hover"],
                text_color=palette["sidebar_text"],
                command=lambda k=key: self._switch_view(k)
            )
            btn.pack(fill="x", pady=2, padx=2)
            self.menu_buttons[key] = btn
            attach_tooltip(btn, name)

        # 사이드바 하단 테마 선택기 (🌾 베이지 | 🌙 다크 | ☀️ 라이트)
        self.theme_selector_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.theme_selector_box.pack(fill="x", padx=10, pady=(0, 16))

        ctk.CTkLabel(
            self.theme_selector_box,
            text="🎨 테마 선택:",
            font=get_font(10, "bold"),
            text_color=palette["text_sub"]
        ).pack(anchor="w", padx=2, pady=(0, 6))

        self.theme_seg_btn = ctk.CTkSegmentedButton(
            self.theme_selector_box,
            values=["🌾 베이지", "🌙 다크", "☀️ 라이트"],
            font=get_font(10, "bold"),
            height=28,
            selected_color=palette["accent"],
            selected_hover_color=palette["accent_hover"],
            unselected_color=palette["sidebar_btn_hover"],
            text_color=palette["text_main"],
            command=self._on_sidebar_theme_selected
        )
        curr_th = timetable_manager.settings.get("theme_mode", "Beige")
        th_display_map = {"Beige": "🌾 베이지", "Dark": "🌙 다크", "Light": "☀️ 라이트"}
        self.theme_seg_btn.set(th_display_map.get(curr_th, "🌾 베이지"))
        self.theme_seg_btn.pack(fill="x")

# 사이드바 투명도 조절 바 제거됨

        # 2. 우측 메인 컨텐츠 영역
        self.content_area = ctk.CTkFrame(self.root_frame, fg_color="transparent")
        self.content_area.pack(side="right", fill="both", expand=True, padx=14, pady=10)

        # 컨텐츠 뷰 컨테이너
        self.views_container = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.views_container.pack(fill="both", expand=True, pady=(0, 4))

        self.views: dict[str, ctk.CTkFrame] = {}
        self._init_all_views()

        # 하단 액션 바 & 저작권
        self._create_bottom_actions(self.content_area)

        # 기본 뷰: 오늘의 일과 & 급식
        self._switch_view("today")

    def _toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        palette = theme_manager.get_theme()

        if self.sidebar_collapsed:
            # 사이드바 축소 (너비 64px, 아이콘 모드)
            self.minsize(700, 580)
            self.sidebar.configure(width=64)
            self.sidebar_toggle_btn.configure(text="▶")
            self.logo_title_lbl.pack_forget()
            self.logo_sub_lbl.pack_forget()
            if hasattr(self, "sidebar_board_btn") and self.sidebar_board_btn.winfo_exists():
                self.sidebar_board_btn.configure(text="📺", width=44)
            if hasattr(self, "sidebar_custom_board_btn") and self.sidebar_custom_board_btn.winfo_exists():
                self.sidebar_custom_board_btn.configure(text="🛠️", width=44)

            for key, name, ico_name in self.menu_items:
                btn = self.menu_buttons[key]
                ico = get_icon(ico_name, palette["sidebar_text"], 20)
                btn.configure(text="", image=ico, compound="center", anchor="center")
                attach_tooltip(btn, name)

            self.theme_selector_box.pack_forget()
        else:
            # 사이드바 확장 (너비 215px, 텍스트 모드)
            self.minsize(860, 600)
            self.sidebar.configure(width=215)
            self.sidebar_toggle_btn.configure(text="◀")
            self.logo_title_lbl.pack(side="left")
            self.logo_sub_lbl.pack(anchor="w", padx=(32, 0), pady=(2, 0))
            if hasattr(self, "sidebar_board_btn") and self.sidebar_board_btn.winfo_exists():
                self.sidebar_board_btn.configure(text="📺  놀티쳐 보드 열기", width=190)
            if hasattr(self, "sidebar_custom_board_btn") and self.sidebar_custom_board_btn.winfo_exists():
                self.sidebar_custom_board_btn.configure(text="🛠️  커스텀 보드 띄우기", width=190)

            for key, name, ico_name in self.menu_items:
                btn = self.menu_buttons[key]
                ico = get_icon(ico_name, palette["sidebar_text"], 18)
                btn.configure(text=f"  {name}", image=ico, compound="left", anchor="w", font=get_font(12, "bold"))
                attach_tooltip(btn, name)

            self.theme_selector_box.pack(fill="x", padx=10, pady=(0, 16))

        # 현재 뷰 버튼 상태 동기화
        self._switch_view(self.current_view_key)

    def _on_sidebar_theme_selected(self, choice: str):
        if "베이지" in choice:
            th_key = "Beige"
        elif "다크" in choice:
            th_key = "Dark"
        else:
            th_key = "Light"
        self._apply_theme_mode(th_key)

    def _apply_theme_mode(self, theme_key: str):
        theme_manager.set_theme(theme_key)
        timetable_manager.settings["theme_mode"] = theme_key
        timetable_manager.save_settings()

        palette = theme_manager.get_theme()
        ctk.set_appearance_mode(palette["ctk_mode"])

        # 사이드바 색상 갱신
        self.sidebar.configure(fg_color=palette["sidebar_bg"], border_color=palette["card_border"])
        self.logo_title_lbl.configure(text_color=palette["text_main"])
        self.logo_sub_lbl.configure(text_color=palette["text_sub"])

        # 뷰 프레임 테두리/배경 갱신 및 재구축
        for frame in self.views.values():
            frame.destroy()
        self.views.clear()
        self._init_all_views()

        # 사이드바 버튼 색상 갱신
        self._switch_view(self.current_view_key)

        # 설정 탭 테마 콤보박스 동기화
        if hasattr(self, "theme_combo") and self.theme_combo.winfo_exists():
            th_map = {"Beige": "🌾 따뜻한 베이지 (Warm Beige)", "Dark": "🌙 다크 모드 (Dark Indigo)", "Light": "☀️ 모던 라이트 (Clean Light)"}
            self.theme_combo.set(th_map.get(theme_key, "🌾 따뜻한 베이지 (Warm Beige)"))

        if hasattr(self, "theme_seg_btn") and self.theme_seg_btn.winfo_exists():
            th_display_map = {"Beige": "🌾 베이지", "Dark": "🌙 다크", "Light": "☀️ 라이트"}
            self.theme_seg_btn.set(th_display_map.get(theme_key, "🌾 베이지"))
            self.theme_seg_btn.configure(
                selected_color=palette["accent"],
                selected_hover_color=palette["accent_hover"],
                unselected_color=palette["sidebar_btn_hover"],
                text_color=palette["text_main"]
            )

        if hasattr(self, "sidebar_alpha_lbl") and self.sidebar_alpha_lbl.winfo_exists():
            self.sidebar_alpha_lbl.configure(text_color=palette["accent"])
        if hasattr(self, "sidebar_alpha_slider") and self.sidebar_alpha_slider.winfo_exists():
            self.sidebar_alpha_slider.configure(
                progress_color=palette["accent"],
                button_color=palette["accent"],
                button_hover_color=palette["accent_hover"]
            )

    def _on_timetable_changed(self):
        """시간표 실시간 변경 감지 -> 메인 창의 오늘 일과 뷰 및 시간표 뷰 자동 갱신"""
        if self.winfo_exists():
            self.after(0, self._reload_timetable_views)

    def _reload_timetable_views(self):
        try:
            palette = theme_manager.get_theme()
            if "today" in self.views and self.views["today"].winfo_exists():
                self.views["today"].destroy()
                f_today = ctk.CTkFrame(self.views_container, fg_color=palette["card_bg"], corner_radius=14, border_width=1, border_color=palette["card_border"])
                self._build_today_tab(f_today)
                self.views["today"] = f_today
                if self.current_view_key == "today":
                    f_today.pack(fill="both", expand=True)

            if "neis_workspace" in self.views and self.views["neis_workspace"].winfo_exists():
                self.views["neis_workspace"].destroy()
                f_neis = ctk.CTkFrame(self.views_container, fg_color=palette["card_bg"], corner_radius=14, border_width=1, border_color=palette["card_border"])
                self._build_neis_workspace_tab(f_neis)
                self.views["neis_workspace"] = f_neis
                if self.current_view_key == "neis_workspace":
                    f_neis.pack(fill="both", expand=True)
        except Exception as e:
            print(f"[UI] Error reloading timetable views: {e}")

    def _ensure_view(self, key: str):
        """요청된 뷰가 아직 생성되지 않았으면 그 시점에 최초 1회만 초고속 생성 (지연 로딩)"""
        if key in self.views and self.views[key].winfo_exists():
            return self.views[key]

        palette = theme_manager.get_theme()
        f = ctk.CTkFrame(self.views_container, fg_color=palette["card_bg"], corner_radius=14, border_width=1, border_color=palette["card_border"])
        
        if key == "today":
            self._build_today_tab(f)
        elif key == "classroom_tools":
            self._build_classroom_tools_tab(f)
        elif key == "neis_workspace":
            self._build_neis_workspace_tab(f)
        elif key == "schedule_hub":
            self._build_schedule_hub_tab(f)
        elif key == "class_management":
            self._build_class_management_tab(f)
        elif key == "smart_desk":
            self._build_smart_desk_tab(f)
        elif key == "pc_settings":
            self._build_pc_settings_tab(f)

        self.views[key] = f
        return f

    def _switch_view(self, key: str):
        self.current_view_key = key
        palette = theme_manager.get_theme()

        # 사이드바 버튼 하이라이트 갱신
        for k, btn in self.menu_buttons.items():
            if k == key:
                ico_name = dict([(m[0], m[2]) for m in self.menu_items]).get(k, "home")
                ico = get_icon(ico_name, "#ffffff", 18)
                btn.configure(
                    image=ico,
                    fg_color=palette["sidebar_btn_active"],
                    text_color="#ffffff",
                    hover_color=palette["accent_hover"]
                )
            else:
                ico_name = dict([(m[0], m[2]) for m in self.menu_items]).get(k, "home")
                ico = get_icon(ico_name, palette["sidebar_text"], 18)
                btn.configure(
                    image=ico,
                    fg_color="transparent",
                    text_color=palette["sidebar_text"],
                    hover_color=palette["sidebar_btn_hover"]
                )

        # 1. 이전 활성화된 프레임들을 먼저 숨겨 겹침/깜빡임 완전 제거
        for k, frame in list(self.views.items()):
            if k != key and frame.winfo_exists():
                frame.pack_forget()

        # 2. 목표 뷰 지연 로딩 후 즉시 표시
        target_frame = self._ensure_view(key)
        target_frame.pack(fill="both", expand=True)

    def _init_all_views(self):
        # 시작 시점에는 오늘 탭 1개만 초고속 렌더링 (앱 기동 속도 대폭 향상)
        self._ensure_view("today")

    # =========================================================================
    # 뷰 1: 오늘의 일과 & 급식 (홈 - 직관적 2단 대시보드)
    # =========================================================================
    def _build_today_tab(self, parent):
        palette = theme_manager.get_theme()
        self.today_scroll = CTk2DScrollableFrame(parent, min_content_width=760, fg_color="transparent")
        self.today_scroll.pack(fill="both", expand=True, padx=6, pady=6)
        scroll = self.today_scroll.viewport

        # 1. 상단 일체형 헤더 (오늘 날짜 + 우측 실시간 PC 자원 칩)
        top_bar = ctk.CTkFrame(scroll, fg_color=palette["header_bg"], corner_radius=12, border_width=1, border_color=palette["header_border"])
        top_bar.pack(fill="x", pady=(0, 10))

        tb_inner = ctk.CTkFrame(top_bar, fg_color="transparent")
        tb_inner.pack(fill="x", padx=14, pady=8)

        today = datetime.date.today()
        weekday_str = DAYS_KO[today.weekday()]
        is_hol, hol_name, _ = timetable_manager.get_today_schedule_items()

        title_text = f"📅 {today.year}년 {today.month}월 {today.day}일 ({weekday_str}요일)"
        if is_hol:
            title_text += f" • 🇰🇷 [{hol_name}] 공휴일"

        ctk.CTkLabel(
            tb_inner,
            text=title_text,
            font=get_font(15, "bold"),
            text_color=palette["text_main"] if not is_hol else "#f97316",
            anchor="w"
        ).pack(side="left", fill="x", expand=True)

        # 우측 상단 유틸리티 박스 (투명도 조절 바 + 미니멀 시스템 자원 칩)
        top_right_box = ctk.CTkFrame(tb_inner, fg_color="transparent")
        top_right_box.pack(side="right")

# 상단 투명도 조절 바 제거됨

        # 우측 미니멀 시스템 자원 칩 (CPU / RAM / GPU - 텍스트 잘림 없는 탄력적 너비)
        res_chip_box = ctk.CTkFrame(top_right_box, fg_color=palette["sidebar_bg"], corner_radius=8, border_width=1, border_color=palette["card_border"], height=32)
        res_chip_box.pack(side="left")

        chip_inner = ctk.CTkFrame(res_chip_box, fg_color="transparent")
        chip_inner.pack(padx=(10, 14), pady=3, fill="both", expand=True)

        self.cpu_label = ctk.CTkLabel(chip_inner, text="💻 CPU --%", font=get_font(10, "bold"), text_color=palette["text_sub"])
        self.cpu_label.pack(side="left", padx=4)

        ctk.CTkFrame(chip_inner, width=1, height=14, fg_color=palette["card_border"]).pack(side="left", padx=4)

        self.ram_label = ctk.CTkLabel(chip_inner, text="🧠 RAM --%", font=get_font(10, "bold"), text_color=palette["text_sub"])
        self.ram_label.pack(side="left", padx=4)

        ctk.CTkFrame(chip_inner, width=1, height=14, fg_color=palette["card_border"]).pack(side="left", padx=4)

        self.gpu_label = ctk.CTkLabel(chip_inner, text="🎮 GPU --%", font=get_font(10, "bold"), text_color=palette["text_sub"])
        self.gpu_label.pack(side="left", padx=(4, 4))

        # 1.5. 💡 놀퀴즈 (pinky-ne.com) 소프트 베젤 스마트 연결 유도 배너
        pinky_banner = ctk.CTkFrame(
            scroll,
            fg_color=palette["card_inner_bg"],
            corner_radius=10,
            border_width=1,
            border_color=palette["card_border"],
        )
        pinky_banner.pack(fill="x", pady=(0, 10))

        pb_inner = ctk.CTkFrame(pinky_banner, fg_color="transparent")
        pb_inner.pack(fill="x", padx=14, pady=8)

        ctk.CTkLabel(
            pb_inner,
            text="✨ 지식과 놀이의 배움터: 선생님과 학생이 함께하는 인터랙티브 수업 퀴즈 플랫폼",
            font=get_font(10),
            text_color=palette["text_sub"],
            anchor="w"
        ).pack(side="left", fill="x", expand=True)

        pinky_btn = ctk.CTkButton(
            pb_inner,
            text="💡 놀퀴즈 (pinky-ne.com) ↗",
            font=get_font(10, "bold"),
            fg_color=palette["sidebar_bg"],
            hover_color=palette["sidebar_btn_hover"],
            text_color=palette["accent"],
            border_width=1,
            border_color=palette["card_border"],
            height=28,
            corner_radius=6,
            command=lambda: webbrowser.open("https://pinky-ne.com")
        )
        pinky_btn.pack(side="right", padx=(8, 0))
        attach_tooltip(pinky_btn, "선생님과 아이들이 함께 즐기는 놀퀴즈 (pinky-ne.com) 웹사이트로 이동합니다")

        # 2. 메인 컨텐츠 영역 (좌측: 오늘 시간표 / 우측: 오늘의 급식 식단표)
        content_row = ctk.CTkFrame(scroll, fg_color="transparent")
        content_row.pack(fill="both", expand=True)

        # 좌측: 오늘 시간표 카드
        left_card = ctk.CTkFrame(content_row, fg_color=palette["card_inner_bg"], corner_radius=12, border_width=1, border_color=palette["card_border"])
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 6))

        lc_top = ctk.CTkFrame(left_card, fg_color="transparent")
        lc_top.pack(fill="x", padx=14, pady=(12, 8))

        ctk.CTkLabel(
            lc_top,
            text="📋 오늘의 수업 시간표",
            font=get_font(13, "bold"),
            text_color=palette["text_main"]
        ).pack(side="left", padx=(0, 20))

        lead_min = timetable_manager.settings.get("alarm_lead_minutes", 5)
        
        # 가변 수업 알람 조절 컨트롤러
        alarm_ctrl_box = ctk.CTkFrame(lc_top, fg_color="transparent")
        alarm_ctrl_box.pack(side="right")

        self.batch_alarm_btn = ctk.CTkButton(
            alarm_ctrl_box,
            text=f"🔔  {lead_min}분 전 일괄 알람",
            font=get_font(10, "bold"),
            fg_color=palette["sidebar_bg"],
            hover_color=palette["sidebar_btn_hover"],
            text_color=palette["text_main"],
            border_width=1,
            border_color=palette["card_border"],
            height=28,
            corner_radius=6,
            command=self._batch_schedule_today_classes
        )
        self.batch_alarm_btn.pack(side="right", padx=(4, 0))
        attach_tooltip(self.batch_alarm_btn, f"오늘 등록된 모든 수업의 시작 {lead_min}분 전 알람을 한 번에 일괄 등록합니다.")

        self.top_alarm_lead_combo = ctk.CTkComboBox(
            alarm_ctrl_box,
            values=["1분 전", "2분 전", "3분 전", "5분 전", "10분 전", "15분 전"],
            width=84,
            height=28,
            font=get_font(10, "bold"),
            state="readonly",
            command=self._on_alarm_lead_changed
        )
        self.top_alarm_lead_combo.set(f"{lead_min}분 전")
        self.top_alarm_lead_combo.pack(side="right", padx=(0, 2))
        attach_tooltip(self.top_alarm_lead_combo, "알람 기준 시간을 자유롭게 변경합니다 (1분, 3분, 5분, 10분 등)")

        from src.timetable_quick_editor import open_timetable_quick_editor
        edit_btn = ctk.CTkButton(
            lc_top,
            text="✏️  시간표 수정",
            font=get_font(10, "bold"),
            fg_color=palette["accent"],
            hover_color=palette["accent_hover"],
            text_color="#ffffff",
            height=28,
            corner_radius=6,
            command=lambda: open_timetable_quick_editor(self)
        )
        edit_btn.pack(side="right", padx=(0, 10))
        attach_tooltip(edit_btn, "오늘 또는 주간 시간표의 과목명과 시간을 즉시 수정합니다.")

        self.today_items_container = ctk.CTkFrame(left_card, fg_color="transparent")
        self.today_items_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 우측: 오늘의 급식 식단표 카드
        right_card = ctk.CTkFrame(content_row, fg_color=palette["card_inner_bg"], corner_radius=12, border_width=1, border_color=palette["card_border"])
        right_card.pack(side="right", fill="both", expand=True, padx=(6, 0))

        rc_top = ctk.CTkFrame(right_card, fg_color="transparent")
        rc_top.pack(fill="x", padx=14, pady=(12, 8))

        ctk.CTkLabel(
            rc_top,
            text="🍱 오늘의 급식 식단표",
            font=get_font(13, "bold"),
            text_color=palette["text_main"]
        ).pack(side="left", padx=(0, 20))

        ctk.CTkButton(
            rc_top,
            text="🔄  새로고침",
            font=get_font(10, "bold"),
            fg_color=palette["sidebar_bg"],
            hover_color=palette["sidebar_btn_hover"],
            text_color=palette["text_main"],
            border_width=1,
            border_color=palette["card_border"],
            height=28,
            corner_radius=6,
            command=lambda: self._refresh_today_meal(force=True)
        ).pack(side="right")

        self.meal_container = ctk.CTkFrame(right_card, fg_color="transparent")
        self.meal_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 3. 하단 퀵 액션 런처 바 (판서, 플로팅바, 타이머, 미니위젯, 사이트 바로가기)
        launcher_bar = ctk.CTkFrame(scroll, fg_color=palette["card_inner_bg"], corner_radius=12, border_width=1, border_color=palette["card_border"])
        launcher_bar.pack(fill="x", pady=(12, 6))

        lb_inner = ctk.CTkFrame(launcher_bar, fg_color="transparent")
        lb_inner.pack(fill="x", padx=10, pady=8)

        from src.icon_renderer import get_icon

        # 알록달록 무지개색 제거: 테마 액센트 1개 톤으로 우아하게 통일
        launcher_icon_col = palette["accent"]

        quick_actions = [
            ("pen",     launcher_icon_col, "판서",   self._open_screen_drawing, "어떤 화면 위에서도 자유 판서 (Alt+2)"),
            ("camera",  launcher_icon_col, "화상기", self._open_visualizer, "웹캠/USB 실물화상기 실시간 뷰어"),
            ("timer",   launcher_icon_col, "타이머", lambda: self._open_classroom_tools("timer"), "수업 및 모둠 활동 타이머 (Alt+3)"),
            ("mouse",   launcher_icon_col, "마우스", self._open_mouse_settings, "교실 수업용 마우스 크기/색상 설정"),
            ("dice",    launcher_icon_col, "뽑기",   lambda: self._open_classroom_tools("picker"), "공정한 학생 발표자 무작위 추첨"),
            ("wheel",   launcher_icon_col, "돌림판", lambda: self._open_classroom_tools("wheel"), "모둠/벌칙/보상 돌려돌려 돌림판"),
            ("ladder",  launcher_icon_col, "사다리", lambda: self._open_classroom_tools("ladder"), "짜릿한 학생/모둠 사다리타기 게임"),
            ("pinball", launcher_icon_col, "핀볼",   lambda: self._open_classroom_tools("pinball"), "아케이드 통통 튀는 핀볼 추첨기"),
            ("screen",  launcher_icon_col, "보드",   self._open_student_display, "교실 TV/전자칠판용 대형 놀티쳐 보드"),
            ("widget",  launcher_icon_col, "위젯",   self._open_mini_widget, "바탕화면에 띄워두는 미니 시간표 위젯"),
            ("broom",   launcher_icon_col, "정리",   self._organize_desktop_action, "바탕화면 흩어진 파일 1초 자동 분류 정리"),
            ("globe",   launcher_icon_col, "사이트", self._open_site_bookmarks, "놀퀴즈, 업무포털 등 교사용 필수 사이트 바로가기")
        ]

        # 6개씩 2행 배치
        row1 = ctk.CTkFrame(lb_inner, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 6))
        row2 = ctk.CTkFrame(lb_inner, fg_color="transparent")
        row2.pack(fill="x")

        for i, (a_ico, a_col, a_title, a_cmd, a_tip) in enumerate(quick_actions):
            row = row1 if i < 6 else row2
            btn = ctk.CTkButton(
                row,
                text=f"  {a_title}",
                image=get_icon(a_ico, a_col, 18),
                compound="left",
                font=get_font(10, "bold"),
                height=32,
                corner_radius=8,
                fg_color=palette["sidebar_btn_hover"],
                hover_color=palette["sidebar_bg"],
                text_color=palette["text_main"],
                border_width=1,
                border_color=palette["card_border"],
                command=a_cmd
            )
            btn.pack(side="left", fill="x", expand=True, padx=3)
            attach_tooltip(btn, a_tip)

        self._render_today_items()
        self._refresh_today_meal()
        self.today_scroll.bind_children_mousewheel()

    def _refresh_today_meal(self, force: bool = False):
        if not hasattr(self, "meal_container") or not self.meal_container.winfo_exists():
            return

        palette = theme_manager.get_theme()
        today = datetime.date.today()

        def _do_fetch():
            ok, meal_info, msg = neis_client.get_meal_for_date(today, force_refresh=force)
            if hasattr(self, "after"):
                self.after(0, self._render_meal_ui, ok, meal_info, msg)

        if force:
            for w in self.meal_container.winfo_children():
                w.destroy()
            loading_lbl = ctk.CTkLabel(
                self.meal_container,
                text="⏳ 최신 급식 식단표를 불러오는 중...",
                font=get_font(11),
                text_color=palette["accent"]
            )
            loading_lbl.pack(pady=20)
            threading.Thread(target=_do_fetch, daemon=True).start()
        else:
            ok, meal_info, msg = neis_client.get_meal_for_date(today, force_refresh=False)
            self._render_meal_ui(ok, meal_info, msg)

    def _render_meal_ui(self, ok: bool, meal_info: dict, msg: str):
        if not hasattr(self, "meal_container") or not self.meal_container.winfo_exists():
            return

        palette = theme_manager.get_theme()
        for w in self.meal_container.winfo_children():
            w.destroy()

        school_nm = neis_client.config.get("school_name", "")
        if not school_nm:
            c = ctk.CTkFrame(self.meal_container, fg_color=palette["card_inner_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
            c.pack(fill="x", pady=10)
            ctk.CTkLabel(
                c,
                text="🏫 학교 설정이 필요합니다.\n[시간표 & 나이스 연동] 탭에서\n학교를 검색하여 선택해주세요.",
                font=get_font(12),
                text_color=palette["text_sub"],
                justify="center"
            ).pack(pady=20)
            return

        if not ok or not meal_info.get("dishes"):
            c = ctk.CTkFrame(self.meal_container, fg_color=palette["card_inner_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
            c.pack(fill="x", pady=10)
            ctk.CTkLabel(
                c,
                text=f"🍱 오늘 등록된 급식이 없습니다.\n({school_nm})\n방학 또는 공휴일일 수 있습니다.",
                font=get_font(12, "bold"),
                text_color=palette["text_sub"],
                justify="center"
            ).pack(pady=20)
            return

        # 급식 메뉴 요약 카드
        cal_str = meal_info.get("calorie", "")
        hdr_box = ctk.CTkFrame(self.meal_container, fg_color=palette["card_inner_bg"], corner_radius=8, border_width=1, border_color=palette["card_border"])
        hdr_box.pack(fill="x", pady=(0, 6))

        h_in = ctk.CTkFrame(hdr_box, fg_color="transparent")
        h_in.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(
            h_in,
            text=f"🍽️ 중식 ({school_nm})",
            font=get_font(11, "bold"),
            text_color=palette["text_main"]
        ).pack(side="left")

        if cal_str:
            ctk.CTkLabel(
                h_in,
                text=f"🔥 {cal_str}",
                font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                text_color=palette["accent"]
            ).pack(side="right")

        # 메뉴 리스트
        dishes = meal_info.get("dishes", [])
        menu_box = ctk.CTkFrame(self.meal_container, fg_color=palette["card_bg"], corner_radius=8, border_width=1, border_color=palette["card_border"])
        menu_box.pack(fill="both", expand=True)

        for i, d in enumerate(dishes):
            row_bg = palette["card_inner_bg"] if i % 2 == 0 else palette["card_bg"]
            row = ctk.CTkFrame(menu_box, fg_color=row_bg, corner_radius=0)
            row.pack(fill="x")
            ctk.CTkLabel(
                row,
                text=f"•  {d}",
                font=get_font(11),
                text_color=palette["text_main"],
                anchor="w"
            ).pack(fill="x", padx=12, pady=4)

        # 하단 알레르기 안내 팁
        ctk.CTkLabel(
            self.meal_container,
            text="* 번호는 알레르기 유발물질 표시입니다.",
            font=get_font(9),
            text_color=palette["text_muted"]
        ).pack(anchor="w", padx=4, pady=(6, 2))

    def _render_today_items(self):
        for w in self.today_items_container.winfo_children():
            w.destroy()

        is_hol, hol_name, items = timetable_manager.get_today_schedule_items()
        lead_min = timetable_manager.settings.get("alarm_lead_minutes", 5)
        now_str = datetime.datetime.now().strftime("%H:%M")

        palette = theme_manager.get_theme()

        if is_hol:
            c = ctk.CTkFrame(self.today_items_container, fg_color=palette["card_inner_bg"], corner_radius=12, border_width=1, border_color=palette["accent_orange"])
            c.pack(fill="x", pady=10)
            ctk.CTkLabel(c, text=f"🇰🇷 오늘은 [{hol_name}] 공휴일입니다.\n오늘 설정된 정규 수업은 없습니다.", font=get_font(13, "bold"), text_color=palette["accent_orange"]).pack(pady=20)
            return

        lesson_counter = 0
        for idx, it in enumerate(items):
            is_lunch = it["is_lunch"]
            start_s, end_s = it["start"], it["end"]
            is_current = (start_s <= now_str <= end_s)

            if is_current:
                card_border = palette.get("current_border", palette["accent"])
                card_bg = palette.get("current_bg", palette["card_inner_bg"])
            elif is_lunch:
                card_border = palette.get("lunch_border", palette["card_border"])
                card_bg = palette.get("lunch_bg", palette["card_inner_bg"])
            else:
                card_border = palette["card_border"]
                card_bg = palette["card_bg"]

            c_frame = ctk.CTkFrame(
                self.today_items_container, 
                corner_radius=8, 
                fg_color=card_bg, 
                border_width=2 if is_current else 1, 
                border_color=card_border
            )
            c_frame.pack(fill="x", pady=3)

            badge_bg = palette["accent"] if is_current else palette["sidebar_btn_hover"]
            badge_fg = "#ffffff" if is_current else palette["text_main"]
            badge_text = f"▶ {it['name']}" if is_current else it["name"]

            badge = ctk.CTkLabel(
                c_frame,
                text=badge_text,
                font=get_font(9, "bold"),
                fg_color=badge_bg,
                text_color=badge_fg,
                corner_radius=6,
                width=56,
                height=24
            )
            badge.pack(side="left", padx=(10, 10), pady=4)

            # 시간 텍스트: 일관된 ` ~ ` 띄어쓰기 적용
            ctk.CTkLabel(
                c_frame,
                text=f"{it['start']} ~ {it['end']}",
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                text_color=palette["text_muted"],
                width=88,
                anchor="w"
            ).pack(side="left", padx=(0, 10))

            subj_text = "🍱 점심식사 및 휴식" if is_lunch else it["subject"]
            subj_lbl = ctk.CTkLabel(
                c_frame,
                text=subj_text,
                font=get_font(12, "bold"),
                text_color=palette["text_main"] if not is_lunch else palette.get("lunch_text", palette["text_sub"]),
                anchor="w"
            )
            subj_lbl.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=4)

            tag = it.get("tag", "담임")
            if tag in ["전담", "외강"]:
                tag_bg = palette.get("tag_bg", "#f5efe6")
                tag_fg = palette.get("tag_text", palette["accent"])
                ctk.CTkLabel(
                    c_frame,
                    text=f"[{tag}]",
                    font=get_font(9, "bold"),
                    fg_color=tag_bg,
                    text_color=tag_fg,
                    corner_radius=4,
                    width=40,
                    height=22
                ).pack(side="left", padx=(0, 6))

            if not is_lunch:
                c_frame.configure(cursor="hand2")
                cur_l = lesson_counter
                def _click_edit(e, p_idx=cur_l):
                    open_timetable_quick_editor(self, focus_period=p_idx)
                c_frame.bind("<Button-1>", _click_edit)
                subj_lbl.bind("<Button-1>", _click_edit)
                badge.bind("<Button-1>", _click_edit)
                attach_tooltip(c_frame, f"클릭하여 {it['name']}({it['subject']}) 과목 즉시 수정")
                lesson_counter += 1

                ctk.CTkButton(
                    c_frame,
                    text=f"🔔 {lead_min}분 전",
                    font=get_font(9, "bold"),
                    fg_color=palette["sidebar_bg"],
                    hover_color=palette["sidebar_btn_hover"],
                    text_color=palette["text_sub"],
                    border_width=1,
                    border_color=palette["card_border"],
                    corner_radius=6,
                    width=70,
                    height=24,
                    command=lambda item=it: self._schedule_single_class_alarm(item)
                ).pack(side="right", padx=(0, 8), pady=4)

    def _open_mini_widget(self):
        if self.mini_widget and self.mini_widget.winfo_exists():
            self.mini_widget.lift()
            self.mini_widget.focus_force()
        else:
            self.mini_widget = MiniTimetableWidget(self)

    def _open_mini_ticker(self):
        if self.mini_ticker and self.mini_ticker.winfo_exists():
            self.mini_ticker.lift()
            self.mini_ticker.focus_force()
        else:
            self.mini_ticker = MiniTickerWidget(self.manager, self)

    def _open_student_display(self):
        if self.student_window and self.student_window.winfo_exists():
            self.student_window.lift()
            self.student_window.focus_force()
        else:
            self.student_window = StudentDisplayWindow(self)

    def _open_screen_drawing(self):
        overlay = ScreenDrawingOverlay.get_instance(self)
        overlay.show()

    def _open_visualizer(self):
        VisualizerWindow.get_instance(self)

    def _open_mouse_settings(self):
        import subprocess
        try:
            subprocess.run("start ms-settings:easeofaccess-mousepointer", shell=True, check=True)
        except Exception:
            subprocess.run("main.cpl", shell=True, check=False)

    def _open_floating_quick_toolbar(self):
        FloatingQuickToolbar.get_instance(self)

    def _open_classroom_tools(self, tab="timer"):
        ClassroomToolsDialog.get_instance(self, initial_tab=tab)

    def _render_quick_sites_bar(self):
        if not hasattr(self, "quick_sites_container") or not self.quick_sites_container.winfo_exists():
            return

        for w in self.quick_sites_container.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self.quick_sites_container,
            text="🌐 바로가기:",
            font=get_font(11, "bold"),
            text_color="#cbd5e1"
        ).pack(side="left", padx=(2, 6))

        # 상위 5~6개 사이트 노출
        displayed_sites = site_bookmark_manager.bookmarks[:5]

        for item in displayed_sites:
            ic = item.get("icon", "🌐")
            title = item.get("title", "")
            short_title = title if len(title) <= 8 else title[:7] + "…"
            col = item.get("color", "#0284c7")
            btn = ctk.CTkButton(
                self.quick_sites_container,
                text=f"{ic} {short_title}",
                font=get_font(10, "bold"),
                height=26,
                fg_color="#1e293b",
                hover_color="#334155",
                text_color=col,
                command=lambda u=item["url"]: site_bookmark_manager.open_site(u)
            )
            btn.pack(side="left", fill="x", expand=True, padx=2)

        ctk.CTkButton(
            self.quick_sites_container,
            text="➕ 관리/추가",
            font=get_font(10, "bold"),
            height=26,
            fg_color="#374151",
            hover_color="#4b5563",
            width=78,
            command=self._open_site_bookmarks
        ).pack(side="left", padx=(2, 2))

    def _open_site_bookmarks(self):
        SiteBookmarksDialog(self, on_changed_callback=self._render_quick_sites_bar)

    def _on_system_metrics_updated(self, metrics: dict[str, Any]):
        try:
            self.after(0, self._update_system_metrics_ui, metrics)
        except Exception:
            pass

    def _update_system_metrics_ui(self, m: dict[str, Any]):
        if not hasattr(self, "cpu_label") or not self.cpu_label.winfo_exists():
            return

        cpu_p = m.get("cpu_percent", 0.0)
        ram_p = m.get("ram_percent", 0.0)
        ram_u = m.get("ram_used_gb", 0.0)
        ram_t = m.get("ram_total_gb", 0.0)
        gpu_p = m.get("gpu_percent", 0.0)
        gpu_name = m.get("gpu_name", "GPU")

        palette = theme_manager.get_theme()
        normal_col = palette["text_sub"]

        self.cpu_label.configure(
            text=f"💻 CPU {cpu_p:.0f}%",
            text_color="#ef4444" if cpu_p > 85 else normal_col
        )
        if hasattr(self, "cpu_progress") and self.cpu_progress.winfo_exists():
            self.cpu_progress.set(min(1.0, max(0.0, cpu_p / 100.0)))

        self.ram_label.configure(
            text=f"🧠 RAM {ram_p:.0f}%",
            text_color="#ef4444" if ram_p > 85 else normal_col
        )
        if hasattr(self, "ram_progress") and self.ram_progress.winfo_exists():
            self.ram_progress.set(min(1.0, max(0.0, ram_p / 100.0)))

        self.gpu_label.configure(
            text=f"🎮 GPU {gpu_p:.0f}%",
            text_color="#ef4444" if gpu_p > 85 else normal_col
        )
        if hasattr(self, "gpu_progress") and self.gpu_progress.winfo_exists():
            self.gpu_progress.set(min(1.0, max(0.0, gpu_p / 100.0)))

    def _set_mini_ticker_dock(self, mode: str):
        if not self.mini_ticker or not self.mini_ticker.winfo_exists():
            self.mini_ticker = MiniTickerWidget(self.manager, self)
        self.mini_ticker._apply_dock_position(mode)
        self.mini_ticker.lift()

    def _schedule_single_class_alarm(self, item: dict[str, Any]):
        lead_min = timetable_manager.settings.get("alarm_lead_minutes", 5)
        alarm_dt = timetable_manager.get_next_alarm_time(item, lead_min)
        if not alarm_dt:
            self._show_simple_alert("안내", "해당 교시의 시작 시간이 설정되어 있지 않습니다.")
            return

        now = datetime.datetime.now()
        seconds_diff = int((alarm_dt - now).total_seconds())

        if seconds_diff <= 0:
            self._show_simple_alert("안내", f"이미 지난 교시입니다 ({item['name']} {item['start']}).")
            return

        memo = f"[{item['name']} {item['subject']}] 수업 시작 {lead_min}분 전입니다!"
        sound_id = timetable_manager.settings.get("alarm_sound_id", "chime")

        dialog = ModernConfirmDialog(
            self,
            title="수업 알람 등록",
            message=f"[{item['name']} {item['subject']}]\n수업 시작 {lead_min}분 전({alarm_dt.strftime('%H:%M:%S')}) 알람을 등록하시겠습니까?",
            action_text="등록",
            is_danger=False
        )
        self.wait_window(dialog)

        if dialog.result:
            self.manager.schedule_action("alarm", seconds_diff, memo=memo, sound_id=sound_id)
            self._play_sound("success")
            
            # 사전 카운트다운 팝업 연동 (알람 울리기 1분 전 = 60초 전)
            cd_sec = 60
            if seconds_diff > cd_sec:
                pop_delay_ms = (seconds_diff - cd_sec) * 1000
                self.after(pop_delay_ms, lambda: ClassCountdownPopup.show(item['name'], item['subject'], lead_min, total_seconds=cd_sec, parent=self))
            elif seconds_diff > 0:
                ClassCountdownPopup.show(item['name'], item['subject'], lead_min, total_seconds=seconds_diff, parent=self)

    def _batch_schedule_today_classes(self):
        lead_min = timetable_manager.settings.get("alarm_lead_minutes", 5)
        _, _, items = timetable_manager.get_today_schedule_items()
        now = datetime.datetime.now()

        valid_targets = []
        for it in items:
            if it["is_lunch"]:
                continue
            alarm_dt = timetable_manager.get_next_alarm_time(it, lead_min)
            if alarm_dt and alarm_dt > now:
                diff = int((alarm_dt - now).total_seconds())
                valid_targets.append((it, alarm_dt, diff))

        if not valid_targets:
            self._show_simple_alert("안내", "오늘 남은 수업이 없거나 모든 교시의 알람 시간이 지났습니다.")
            return

        target_item, target_dt, target_sec = valid_targets[0]
        memo = f"[{target_item['name']} {target_item['subject']}] 수업 시작 {lead_min}분 전입니다!"
        sound_id = timetable_manager.settings.get("alarm_sound_id", "chime")

        msg = f"오늘 남은 {len(valid_targets)}개 수업 중 가장 가까운\n[{target_item['name']} {target_item['subject']}] ({target_dt.strftime('%H:%M')} 알람)을 예약하시겠습니까?"

        dialog = ModernConfirmDialog(
            self,
            title="일괄 수업 알람 등록",
            message=msg,
            action_text="알람 예약",
            is_danger=False
        )
        self.wait_window(dialog)

        if dialog.result:
            self.manager.schedule_action("alarm", target_sec, memo=memo, sound_id=sound_id)
            self._play_sound("success")

            # 사전 카운트다운 팝업 연동 (알람 울리기 1분 전 = 60초 전)
            cd_sec = 60
            if target_sec > cd_sec:
                pop_delay_ms = (target_sec - cd_sec) * 1000
                self.after(pop_delay_ms, lambda: ClassCountdownPopup.show(target_item['name'], target_item['subject'], lead_min, total_seconds=cd_sec, parent=self))
            elif target_sec > 0:
                ClassCountdownPopup.show(target_item['name'], target_item['subject'], lead_min, total_seconds=target_sec, parent=self)

    # =========================================================================
    # 뷰 2: ✏️ 수업 도구 & 바로가기 (화면 판서, 플로팅 바, 타이머, 뽑기, 사이트 모음)
    # =========================================================================
    def _build_classroom_tools_tab(self, parent):
        palette = theme_manager.get_theme()
        self.tools_scroll = CTk2DScrollableFrame(parent, min_content_width=740, fg_color="transparent")
        self.tools_scroll.pack(fill="both", expand=True, padx=6, pady=6)
        scroll = self.tools_scroll.viewport

        # 1. 👥 우리 반 학생 명렬표 관리 카드 (로컬 단독 보관)
        roster_card = ctk.CTkFrame(scroll, corner_radius=12, fg_color=palette["card_inner_bg"], border_width=1, border_color=palette["card_border"])
        roster_card.pack(fill="x", pady=(0, 10))

        r_hdr = ctk.CTkFrame(roster_card, fg_color="transparent")
        r_hdr.pack(fill="x", padx=14, pady=(12, 6))

        ctk.CTkLabel(
            r_hdr,
            text="👥 우리 반 학생 명렬표 관리 (발표자 뽑기 & 교실 도구 연동)",
            font=get_font(13, "bold"),
            text_color=palette["text_main"]
        ).pack(side="left")

        from src.student_manager import student_manager
        from src.classroom_tools import StudentRosterEditDialog

        stu_cnt = student_manager.get_count()
        ctk.CTkButton(
            r_hdr,
            text="👥 학생 명단 등록 / 수정",
            font=get_font(11, "bold"),
            fg_color=palette["accent"],
            hover_color=palette["accent_hover"],
            text_color="#ffffff",
            height=28,
            corner_radius=6,
            command=lambda: StudentRosterEditDialog(self, on_saved_callback=lambda: self._switch_view("classroom_tools"))
        ).pack(side="right")

        sec_info = f"• 현재 등록된 학생: 총 {stu_cnt}명 | 발표자 뽑기(🎲)에서 [👦 학생 이름 모드] 또는 [🔢 번호 전용 모드]를 선택하여 사용하실 수 있습니다.\n• 🔒 100% 로컬 영구 보관: 학생 개인정보는 외부 서버로 절대 전송되지 않으며 선생님 PC에만 안전하게 저장됩니다."
        ctk.CTkLabel(roster_card, text=sec_info, font=get_font(10), text_color=palette["text_sub"], justify="left", anchor="w").pack(fill="x", padx=14, pady=(0, 12))

        # 2. ✏️ 교실 수업 진행 도구 6종 카드
        tools_card = ctk.CTkFrame(scroll, corner_radius=12, fg_color=palette["card_inner_bg"], border_width=1, border_color=palette["card_border"])
        tools_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            tools_card,
            text="✏️ 교실 수업 진행 도구 (원클릭 실행)",
            font=get_font(13, "bold"),
            text_color=palette["text_main"]
        ).pack(anchor="w", padx=14, pady=(12, 6))

        t_grid = ctk.CTkFrame(tools_card, fg_color="transparent")
        t_grid.pack(fill="x", padx=10, pady=(0, 10))
        for col_idx in range(3):
            t_grid.grid_columnconfigure(col_idx, weight=1)

        tool_items = [
            ("✏️ 화면 위 자유 판서", "모니터 위 모든 웹/앱 위에 펜으로 직접 판서 및 밑줄", self._open_screen_drawing),
            ("📷 스마트 실물화상기", "웹캠/USB 화상기 90°회전, 반전, 정지, 문서강조, 전체화면", self._open_visualizer),
            ("🛠️ 스마트 플로팅 퀵바", "모니터 구석에 띄워두고 도구를 1초 만에 실행하는 미니바", self._open_floating_quick_toolbar),
            ("⏱️ 교실 활동 타이머", "1분/3분/5분 모둠 활동 카운트다운 및 알람음", lambda: self._open_classroom_tools("timer")),
            ("🎲 발표자 랜덤 뽑기", "학급 학생 이름/번호 롤링 추첨 (중복 제외)", lambda: self._open_classroom_tools("picker")),
            ("🎡 돌려돌려 돌림판", "모둠, 발표자, 벌칙, 보상 돌려돌려 돌림판", lambda: self._open_classroom_tools("wheel")),
            ("🪜 짜릿한 사다리타기", "학생/모둠 사다리타기 게임", lambda: self._open_classroom_tools("ladder")),
            ("⚾ 아케이드 핀볼", "통통 튀는 물리 바운스 핀볼 추첨기", lambda: self._open_classroom_tools("pinball")),
            ("📌 바탕화면 미니 시간표", "모서리 드래그 크기 조절 & 상단 핀 고정 미니 위젯", self._open_mini_widget),
            ("📺 학생용 대형 스크린", "교실 TV/전자칠판용 대형 시간표 및 알림판", self._open_student_display)
        ]

        for idx, (t_title, t_desc, t_cmd) in enumerate(tool_items):
            r = idx // 3
            c = idx % 3

            c_box = ctk.CTkFrame(t_grid, fg_color=palette["card_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
            c_box.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")

            ctk.CTkLabel(c_box, text=t_title, font=get_font(12, "bold"), text_color=palette["text_main"], anchor="w").pack(fill="x", padx=10, pady=(8, 2))
            ctk.CTkLabel(c_box, text=t_desc, font=get_font(10), text_color=palette["text_sub"], anchor="w", justify="left", wraplength=170).pack(fill="x", padx=10, pady=(0, 6))

            ctk.CTkButton(
                c_box,
                text="실행하기",
                font=get_font(11, "bold"),
                height=28,
                corner_radius=6,
                fg_color=palette["accent"],
                hover_color=palette["accent_hover"],
                text_color="#ffffff",
                command=t_cmd
            ).pack(fill="x", padx=10, pady=(0, 8))

        # 2. 🌐 교사용 교육 사이트 바로가기 모음 카드
        site_card = ctk.CTkFrame(scroll, corner_radius=12, fg_color=palette["card_inner_bg"], border_width=1, border_color=palette["card_border"])
        site_card.pack(fill="x", pady=(0, 10))

        s_hdr = ctk.CTkFrame(site_card, fg_color="transparent")
        s_hdr.pack(fill="x", padx=14, pady=(12, 6))

        ctk.CTkLabel(
            s_hdr,
            text="🌐 교사용 추천 교육 사이트 & 내 바로가기",
            font=get_font(13, "bold"),
            text_color=palette["text_main"]
        ).pack(side="left")

        ctk.CTkButton(
            s_hdr,
            text="➕ 사이트 관리 / 추가",
            font=get_font(11, "bold"),
            fg_color=palette["accent"],
            hover_color=palette["accent_hover"],
            text_color="#ffffff",
            height=28,
            corner_radius=6,
            command=self._open_site_bookmarks
        ).pack(side="right")

        self.tools_site_grid = ctk.CTkFrame(site_card, fg_color="transparent")
        self.tools_site_grid.pack(fill="x", padx=10, pady=(0, 10))
        self._render_tools_site_grid()
        self.tools_scroll.bind_children_mousewheel()

    def _render_tools_site_grid(self):
        if not hasattr(self, "tools_site_grid") or not self.tools_site_grid.winfo_exists():
            return

        for w in self.tools_site_grid.winfo_children():
            w.destroy()

        for c_i in range(3):
            self.tools_site_grid.grid_columnconfigure(c_i, weight=1)

        b_list = site_bookmark_manager.bookmarks

        for idx, item in enumerate(b_list):
            r = idx // 3
            c = idx % 3

            s_box = ctk.CTkFrame(self.tools_site_grid, fg_color="#101726", corner_radius=8, border_width=1, border_color="#26334d")
            s_box.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")

            top_r = ctk.CTkFrame(s_box, fg_color="transparent")
            top_r.pack(fill="x", padx=8, pady=(6, 2))

            ctk.CTkLabel(top_r, text=item.get("icon", "🌐"), font=get_font(13)).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(top_r, text=item.get("title", ""), font=get_font(11, "bold"), text_color="#f8fafc", anchor="w").pack(side="left", fill="x", expand=True)

            ctk.CTkButton(
                s_box,
                text="열기",
                font=get_font(10, "bold"),
                height=22,
                fg_color=item.get("color", "#0284c7"),
                hover_color="#0369a1",
                command=lambda u=item["url"]: site_bookmark_manager.open_site(u)
            ).pack(fill="x", padx=8, pady=(0, 6))

    # =========================================================================
    # 뷰 3: 📝 나이스 업무 & 시간표 통합 (주간 시간표 + 나이스 엑셀 입력 서브탭)
    # =========================================================================
    def _build_neis_workspace_tab(self, parent):
        hdr_bar = ctk.CTkFrame(parent, fg_color="#182234", corner_radius=10, border_width=1, border_color="#38bdf8")
        hdr_bar.pack(fill="x", padx=6, pady=(6, 4))

        self.neis_seg_btn = ctk.CTkSegmentedButton(
            hdr_bar,
            values=["📅 주간 시간표 & 나이스 연동", "🚀 4세대 나이스 엑셀 자동입력"],
            font=get_font(12, "bold"),
            command=self._on_neis_sub_tab_changed
        )
        self.neis_seg_btn.set("📅 주간 시간표 & 나이스 연동")
        self.neis_seg_btn.pack(side="left", padx=10, pady=6)

        self.neis_sub_container = ctk.CTkFrame(parent, fg_color="transparent")
        self.neis_sub_container.pack(fill="both", expand=True, padx=2, pady=2)

        self.neis_sub_weekly_frame = ctk.CTkFrame(self.neis_sub_container, fg_color="transparent")
        self._build_weekly_and_neis_tab(self.neis_sub_weekly_frame)

        self.neis_sub_excel_frame = ctk.CTkFrame(self.neis_sub_container, fg_color="transparent")
        self._build_neis_auto_input_tab(self.neis_sub_excel_frame)

        self.neis_sub_weekly_frame.pack(fill="both", expand=True)

    def _on_neis_sub_tab_changed(self, choice: str):
        if "주간 시간표" in choice:
            self.neis_sub_excel_frame.pack_forget()
            self.neis_sub_weekly_frame.pack(fill="both", expand=True)
        else:
            self.neis_sub_weekly_frame.pack_forget()
            self.neis_sub_excel_frame.pack(fill="both", expand=True)

    # =========================================================================
    # 뷰 4: ⚙️ PC 관리 & 설정 (컴퓨터 예약/종료 + 화면 분할 + 환경 설정)
    # =========================================================================


    # =========================================================================
    # 뷰: 스마트 예약 센터 (Schedule Hub)
    # =========================================================================
    def _build_schedule_hub_tab(self, parent):
        palette = theme_manager.get_theme()
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        # 1. 상단 안내 헤더 카드
        hdr_card = ctk.CTkFrame(scroll, fg_color=palette["card_inner_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
        hdr_card.pack(fill="x", pady=(0, 12))

        h_in = ctk.CTkFrame(hdr_card, fg_color="transparent")
        h_in.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(h_in, text="⏰ 스마트 예약 센터", font=get_font(16, "bold"), text_color=palette["accent"]).pack(side="left")
        ctk.CTkLabel(h_in, text="수업 시작 알람(1분 전 카운트다운) 및 PC 전원(종료/절전/부팅) 예약을 한곳에서 관리합니다.", font=get_font(11), text_color=palette["text_sub"]).pack(side="left", padx=14)

        # 2. 메인 2단 그리드: 좌측(수업 알람 예약) + 우측(PC 전원 예약)
        grid_row = ctk.CTkFrame(scroll, fg_color="transparent")
        grid_row.pack(fill="x", pady=(0, 12))

        # ─────────────────────────────────────────────────────────────────────
        # [좌측] 🔔 수업 준비 알람 & 사전 카운트다운 예약 카드
        # ─────────────────────────────────────────────────────────────────────
        alarm_card = ctk.CTkFrame(grid_row, fg_color=palette["card_inner_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
        alarm_card.pack(side="left", fill="both", expand=True, padx=(0, 6))

        ac_hdr = ctk.CTkFrame(alarm_card, fg_color="transparent")
        ac_hdr.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(ac_hdr, text="🔔 수업 준비 알람 & 사전 카운트다운", font=get_font(13, "bold"), text_color=palette["text_main"]).pack(side="left")

        # 가변 알람 기준 선택
        lead_min = timetable_manager.settings.get("alarm_lead_minutes", 5)
        lead_row = ctk.CTkFrame(alarm_card, fg_color="transparent")
        lead_row.pack(fill="x", padx=14, pady=4)

        ctk.CTkLabel(lead_row, text="수업 알람 기준:", font=get_font(11, "bold"), text_color=palette["text_sub"]).pack(side="left", padx=(0, 8))
        self.hub_lead_combo = ctk.CTkComboBox(
            lead_row,
            values=["1분 전", "2분 전", "3분 전", "5분 전", "10분 전", "15분 전"],
            width=90, height=28, font=get_font(11, "bold"), state="readonly",
            command=self._on_alarm_lead_changed
        )
        self.hub_lead_combo.set(f"{lead_min}분 전")
        self.hub_lead_combo.pack(side="left")

        ctk.CTkLabel(
            alarm_card,
            text="* 알람 1분 전(60초 전)에 화면에 카운트다운 플로팅 카드가 떠서\n  0초에 수업 차임벨 종료음이 울립니다.",
            font=get_font(9), text_color=palette["accent"], justify="left"
        ).pack(anchor="w", padx=14, pady=(2, 8))

        # 오늘 수업 일괄 알람 버튼
        self.hub_batch_alarm_btn = ctk.CTkButton(
            alarm_card,
            text=f"🔔 오늘 수업 전체 {lead_min}분 전 일괄 예약",
            font=get_font(12, "bold"), height=36, corner_radius=8,
            fg_color=palette["accent"], hover_color=palette["accent_hover"],
            text_color="#ffffff", command=self._batch_schedule_today_classes
        )
        self.hub_batch_alarm_btn.pack(fill="x", padx=14, pady=(0, 10))

        # 오늘 교시별 바로 예약 칩
        ctk.CTkLabel(alarm_card, text="오늘의 교시별 바로 예약:", font=get_font(10, "bold"), text_color=palette["text_sub"]).pack(anchor="w", padx=14, pady=(4, 2))
        chip_box = ctk.CTkScrollableFrame(alarm_card, fg_color="transparent", height=130)
        chip_box.pack(fill="x", padx=10, pady=(0, 10))

        _, _, today_items = timetable_manager.get_today_schedule_items()
        valid_items = [it for it in today_items if not it["is_lunch"] and it.get("start")]
        if not valid_items:
            ctk.CTkLabel(chip_box, text="오늘 등록된 수업이 없습니다.", font=get_font(10), text_color=palette["text_sub"]).pack(pady=10)
        else:
            for itm in valid_items:
                c_row = ctk.CTkFrame(chip_box, fg_color=palette["card_bg"], corner_radius=6)
                c_row.pack(fill="x", pady=2)
                ctk.CTkLabel(c_row, text=f"{itm['name']} {itm['subject']}", font=get_font(10, "bold"), text_color=palette["text_main"]).pack(side="left", padx=8, pady=4)
                ctk.CTkLabel(c_row, text=itm.get("start", ""), font=ctk.CTkFont(family="Consolas", size=9), text_color=palette["text_sub"]).pack(side="left", padx=4)

                ctk.CTkButton(
                    c_row, text="예약", width=46, height=22, font=get_font(9, "bold"),
                    fg_color=palette["sidebar_btn_hover"], hover_color=palette["accent"],
                    text_color=palette["text_main"], corner_radius=4,
                    command=lambda it=itm: self._schedule_single_class_alarm(it)
                ).pack(side="right", padx=6)

        # ─────────────────────────────────────────────────────────────────────
        # [우측] ⚡ 컴퓨터 전원 스마트 예약 카드 (종료 / 다시시작 / 절전)
        # ─────────────────────────────────────────────────────────────────────
        power_card = ctk.CTkFrame(grid_row, fg_color=palette["card_inner_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
        power_card.pack(side="right", fill="both", expand=True, padx=(6, 0))

        pc_hdr = ctk.CTkFrame(power_card, fg_color="transparent")
        pc_hdr.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(pc_hdr, text="⚡ 컴퓨터 전원 스마트 예약", font=get_font(13, "bold"), text_color=palette["text_main"]).pack(side="left")

        # 전원 동작 선택 세그먼트
        self.hub_power_seg = ctk.CTkSegmentedButton(
            power_card,
            values=["💻 자동 종료", "🔄 다시시작", "🌙 절전 모드"],
            font=get_font(10, "bold"), height=28,
            selected_color=palette["accent"], selected_hover_color=palette["accent_hover"],
            unselected_color=palette["sidebar_btn_hover"], text_color=palette["text_main"]
        )
        self.hub_power_seg.set("💻 자동 종료")
        self.hub_power_seg.pack(fill="x", padx=14, pady=(2, 8))

        # 특정 시각 직접 입력
        t_row = ctk.CTkFrame(power_card, fg_color="transparent")
        t_row.pack(fill="x", padx=14, pady=2)
        ctk.CTkLabel(t_row, text="희망 시각(HH:MM):", font=get_font(11, "bold"), text_color=palette["text_sub"]).pack(side="left", padx=(0, 6))

        self.hub_time_entry = ctk.CTkEntry(t_row, width=80, height=28, font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), justify="center")
        now_dt = datetime.datetime.now()
        def_t = (now_dt + datetime.timedelta(hours=1)).strftime("%H:%M")
        self.hub_time_entry.insert(0, def_t)
        self.hub_time_entry.pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            t_row, text="지정시각 예약", font=get_font(10, "bold"), height=28, width=80,
            fg_color="#0284c7", hover_color="#0369a1", text_color="#ffffff", corner_radius=6,
            command=self._do_hub_schedule_custom_time
        ).pack(side="left")

        # 퀵 프리셋 버튼들
        ctk.CTkLabel(power_card, text="빠른 시간 예약:", font=get_font(10, "bold"), text_color=palette["text_sub"]).pack(anchor="w", padx=14, pady=(8, 2))
        q_row = ctk.CTkFrame(power_card, fg_color="transparent")
        q_row.pack(fill="x", padx=14, pady=(0, 8))

        presets = [
            ("10분 후", 600),
            ("30분 후", 1800),
            ("1시간 후", 3600),
            ("퇴근(16:40)", "16:40")
        ]
        for p_name, p_val in presets:
            ctk.CTkButton(
                q_row, text=p_name, font=get_font(10, "bold"), height=26, corner_radius=6,
                fg_color=palette["card_bg"], hover_color=palette["accent"], text_color=palette["text_main"],
                command=lambda v=p_val: self._do_hub_schedule_preset(v)
            ).pack(side="left", fill="x", expand=True, padx=2)

        # 절전 vs 종료 안내 배너
        info_banner = ctk.CTkFrame(power_card, fg_color=palette["card_bg"], corner_radius=8, border_width=1, border_color=palette["card_border"])
        info_banner.pack(fill="x", padx=14, pady=(4, 10))
        ctk.CTkLabel(
            info_banner,
            text="💡 [절전 vs 종료]\n• 절전: 작업 중이던 창과 프로그램이 그대로 유지되어 1초 만에 켜짐.\n• 종료: 전원이 완전히 차단되어 PC 부품 수명 및 보안에 최적.",
            font=get_font(9), text_color=palette["text_sub"], justify="left"
        ).pack(fill="x", padx=8, pady=6)

        # ─────────────────────────────────────────────────────────────────────
        # 3. 📋 현재 실행 중인 실시간 예약 모니터링 카드 (Live Monitor)
        # ─────────────────────────────────────────────────────────────────────
        monitor_card = ctk.CTkFrame(scroll, fg_color=palette["card_inner_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
        monitor_card.pack(fill="x", pady=(0, 12))

        m_hdr = ctk.CTkFrame(monitor_card, fg_color="transparent")
        m_hdr.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(m_hdr, text="📋 현재 활성화된 예약 목록 (실시간 카운트다운)", font=get_font(13, "bold"), text_color=palette["text_main"]).pack(side="left")

        ctk.CTkButton(
            m_hdr, text="전체 예약 취소", font=get_font(10, "bold"), height=26, width=90,
            fg_color="#dc2626", hover_color="#b91c1c", text_color="#ffffff", corner_radius=6,
            command=self._cancel_all_schedules_from_hub
        ).pack(side="right")

        self.hub_active_list_container = ctk.CTkFrame(monitor_card, fg_color="transparent")
        self.hub_active_list_container.pack(fill="x", padx=14, pady=(0, 12))

        self._render_hub_active_schedules()
        self._start_hub_monitor_loop()

    def _start_hub_monitor_loop(self):
        def _tick():
            if self.winfo_exists() and getattr(self, "current_view_key", "") == "schedule_hub":
                self._render_hub_active_schedules()
                self.after(1000, _tick)
        self.after(1000, _tick)

    def _render_hub_active_schedules(self):
        if not hasattr(self, "hub_active_list_container") or not self.hub_active_list_container.winfo_exists():
            return

        for w in self.hub_active_list_container.winfo_children():
            w.destroy()

        palette = theme_manager.get_theme()
        schedules = list(self.manager.schedules.values())

        if not schedules:
            empty_box = ctk.CTkFrame(self.hub_active_list_container, fg_color=palette["card_bg"], corner_radius=8)
            empty_box.pack(fill="x", pady=4)
            ctk.CTkLabel(empty_box, text="현재 진행 중인 예약(수업 알람, 전원 제어)이 없습니다.", font=get_font(11), text_color=palette["text_sub"]).pack(pady=12)
            return

        for itm in schedules:
            row = ctk.CTkFrame(self.hub_active_list_container, fg_color=palette["card_bg"], corner_radius=8, border_width=1, border_color=palette["card_border"])
            row.pack(fill="x", pady=2)

            act_type = itm.get("action_type", "")
            act_name = self.manager._get_action_name(act_type)
            tgt_dt = itm.get("target_time")
            tgt_str = tgt_dt.strftime("%H:%M:%S") if tgt_dt else "--:--"
            rem_sec = itm.get("remaining_seconds", 0)

            # 남은 시간 포맷
            h = rem_sec // 3600
            m = (rem_sec % 3600) // 60
            s = rem_sec % 60
            rem_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

            badge_col = "#dc2626" if act_type in ("shutdown", "restart") else ("#ea580c" if act_type == "sleep" else "#0284c7")
            ctk.CTkLabel(row, text=act_name, font=get_font(10, "bold"), fg_color=badge_col, text_color="#ffffff", corner_radius=4, width=54, height=22).pack(side="left", padx=(8, 8), pady=6)

            memo_txt = itm.get("memo", f"{act_name} 예약")
            ctk.CTkLabel(row, text=memo_txt, font=get_font(11, "bold"), text_color=palette["text_main"]).pack(side="left", padx=4)

            ctk.CTkLabel(row, text=f"목표: {tgt_str}", font=ctk.CTkFont(family="Consolas", size=10), text_color=palette["text_sub"]).pack(side="left", padx=8)

            ctk.CTkLabel(row, text=f"남은 시간: {rem_str}", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color="#f59e0b").pack(side="right", padx=(8, 12))

            sch_id = itm.get("id")
            ctk.CTkButton(
                row, text="취소", width=44, height=22, font=get_font(9, "bold"),
                fg_color="#dc2626", hover_color="#b91c1c", text_color="#ffffff", corner_radius=4,
                command=lambda sid=sch_id: self._cancel_single_schedule_from_hub(sid)
            ).pack(side="right", padx=4)

    def _cancel_single_schedule_from_hub(self, sch_id: str):
        ok, msg = self.manager.cancel_schedule_by_id(sch_id)
        self._render_hub_active_schedules()
        self._show_simple_alert("예약 취소", msg)

    def _cancel_all_schedules_from_hub(self):
        ok, msg = self.manager.cancel_schedule()
        self._render_hub_active_schedules()
        self._show_simple_alert("전체 취소", msg)

    def _do_hub_schedule_custom_time(self):
        val = self.hub_time_entry.get().strip()
        try:
            h, m = map(int, val.split(":"))
            now = datetime.datetime.now()
            tgt = datetime.datetime(now.year, now.month, now.day, h, m, 0)
            if tgt <= now:
                tgt += datetime.timedelta(days=1)
            diff = int((tgt - now).total_seconds())
        except Exception:
            self._show_simple_alert("오류", "올바른 시각(HH:MM 형식)을 입력해주세요. (예: 16:40)")
            return

        choice = self.hub_power_seg.get()
        act_type = "shutdown"
        if "다시시작" in choice: act_type = "restart"
        elif "절전" in choice: act_type = "sleep"

        ok, msg = self.manager.schedule_action(act_type, diff, memo=f"{choice} 예약 ({val})")
        if not ok and "CONFLICT" in msg:
            if messagebox.askyesno("예약 충돌", "이미 비슷한 시각에 다른 전원 제어 예약이 있습니다.\n기존 예약을 대체하고 새로 등록하시겠습니까?"):
                self.manager.schedule_action(act_type, diff, memo=f"{choice} 예약 ({val})", force=True)
                self._show_simple_alert("예약 완료", f"{val}에 {choice}이(가) 등록되었습니다.")
        elif ok:
            self._show_simple_alert("예약 완료", msg)
        self._render_hub_active_schedules()

    def _do_hub_schedule_preset(self, val):
        now = datetime.datetime.now()
        if isinstance(val, str) and ":" in val:
            h, m = map(int, val.split(":"))
            tgt = datetime.datetime(now.year, now.month, now.day, h, m, 0)
            if tgt <= now:
                tgt += datetime.timedelta(days=1)
            diff = int((tgt - now).total_seconds())
        else:
            diff = int(val)

        choice = self.hub_power_seg.get()
        act_type = "shutdown"
        if "다시시작" in choice: act_type = "restart"
        elif "절전" in choice: act_type = "sleep"

        ok, msg = self.manager.schedule_action(act_type, diff, memo=f"{choice} 퀵 예약")
        if not ok and "CONFLICT" in msg:
            if messagebox.askyesno("예약 충돌", "이미 비슷한 시각에 다른 전원 제어 예약이 있습니다.\n기존 예약을 대체하고 새로 등록하시겠습니까?"):
                self.manager.schedule_action(act_type, diff, memo=f"{choice} 퀵 예약", force=True)
                self._show_simple_alert("예약 완료", f"{choice} 예약이 등록되었습니다.")
        elif ok:
            self._show_simple_alert("예약 완료", msg)
        self._render_hub_active_schedules()

    # =========================================================================
    # 뷰: 학급 경영 & 모둠 (Class Management)
    # =========================================================================
    def _build_class_management_tab(self, parent):
        palette = theme_manager.get_theme()
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        # 1. 헤더 카드
        hdr_card = ctk.CTkFrame(scroll, fg_color=palette["card_inner_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
        hdr_card.pack(fill="x", pady=(0, 12))
        
        h_in = ctk.CTkFrame(hdr_card, fg_color="transparent")
        h_in.pack(fill="x", padx=16, pady=12)
        
        ctk.CTkLabel(h_in, text="🏆 학급 경영 & 모둠 활동 센터", font=get_font(15, "bold"), text_color=palette["text_main"]).pack(side="left")
        ctk.CTkLabel(h_in, text="학생 자리 배치, 모둠 점수판, 소음 측정, 알림장을 한곳에서 관리합니다.", font=get_font(11), text_color=palette["text_sub"]).pack(side="left", padx=14)

        # 2. 4대 핵심 학급 경영 카드 그리드
        grid_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)

        cards = [
            ("🪑 학생 자리 배치 & 모둠 편성", "남녀 짝꿍, 모둠별 자리 배치 시각화 및 랜덤 자리 섞기", "자리 배치표 열기", self._open_student_display),
            ("🏆 모둠 점수판 & 칭찬 트로피", "모둠별 점수 부여, 실시간 랭킹 순위 및 보상 효과음", "모둠 점수판 열기", self._open_student_display),
            ("📢 교실 소음 측정기 & 정숙 데시벨", "마이크를 통한 실시간 교실 소음 측정 및 정숙 모드 경고", "소음 측정기 실행", lambda: self._show_simple_alert("소음 측정기", "놀티쳐 보드 상단 도구 메뉴에서 소음측정기를 바로 실행하실 수 있습니다.")),
            ("📌 학급 알림장 & 과제 메모장", "내일 준비물, 숙제, 가정통신문 안내사항 보드 상시 게시", "알림장 메모 열기", self._open_student_display)
        ]

        for idx, (title, desc, btn_txt, cmd) in enumerate(cards):
            r = idx // 2
            c = idx % 2
            card = ctk.CTkFrame(grid_frame, fg_color=palette["card_inner_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
            card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

            c_in = ctk.CTkFrame(card, fg_color="transparent")
            c_in.pack(fill="both", expand=True, padx=14, pady=12)

            ctk.CTkLabel(c_in, text=title, font=get_font(13, "bold"), text_color=palette["accent"]).pack(anchor="w")
            ctk.CTkLabel(c_in, text=desc, font=get_font(10), text_color=palette["text_sub"], wraplength=280, justify="left").pack(anchor="w", pady=(6, 12))

            ctk.CTkButton(
                c_in, text=btn_txt, font=get_font(11, "bold"), height=32, corner_radius=6,
                fg_color=palette["accent"], hover_color=palette["accent_hover"],
                text_color="#ffffff", command=cmd
            ).pack(anchor="w")

    # =========================================================================
    # 뷰: 스마트 데스크 & 정리 (Smart Desk)
    # =========================================================================
    def _build_smart_desk_tab(self, parent):
        palette = theme_manager.get_theme()
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        # 1. 헤더 카드
        hdr_card = ctk.CTkFrame(scroll, fg_color=palette["card_inner_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
        hdr_card.pack(fill="x", pady=(0, 12))
        
        h_in = ctk.CTkFrame(hdr_card, fg_color="transparent")
        h_in.pack(fill="x", padx=16, pady=12)
        
        ctk.CTkLabel(h_in, text="🖥️ 스마트 데스크 & 바탕화면 정리 센터", font=get_font(15, "bold"), text_color=palette["text_main"]).pack(side="left")
        ctk.CTkLabel(h_in, text="복잡한 교사 컴퓨터를 1초 만에 깔끔하게 정돈하고 필수 사이트를 즉시 연결합니다.", font=get_font(11), text_color=palette["text_sub"]).pack(side="left", padx=14)

        # 2. 기능 카드 그리드
        grid_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)

        cards = [
            ("🧹 바탕화면 1초 스마트 자동 정리", "어질러진 문서, 이미지, 압축파일을 종류별/날짜별 폴더로 1초 자동 분류", "바탕화면 1초 정리 실행", self._organize_desktop_action),
            ("↩️ 바탕화면 정리 직전 상태 되돌리기", "방금 자동 정리한 파일들을 원래 위치로 100% 안전 복원", "정리 되돌리기 실행", self._undo_desktop_action),
            ("🌐 교사용 필수 교육 사이트 모음", "나이스 업무포털, K-에듀파인, pinky-ne.com 놀퀴즈 등 원클릭 접속", "교육 사이트 모음 열기", self._open_site_bookmarks),
            ("📌 미니 시간표 위젯 & 스마트 플로팅바", "바탕화면에 상시 띄워두고 수업 일정과 도구를 바로 쓰는 미니바", "미니 위젯 띄우기", self._open_mini_widget)
        ]

        for idx, (title, desc, btn_txt, cmd) in enumerate(cards):
            r = idx // 2
            c = idx % 2
            card = ctk.CTkFrame(grid_frame, fg_color=palette["card_inner_bg"], corner_radius=10, border_width=1, border_color=palette["card_border"])
            card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

            c_in = ctk.CTkFrame(card, fg_color="transparent")
            c_in.pack(fill="both", expand=True, padx=14, pady=12)

            ctk.CTkLabel(c_in, text=title, font=get_font(13, "bold"), text_color=palette["accent_green"]).pack(anchor="w")
            ctk.CTkLabel(c_in, text=desc, font=get_font(10), text_color=palette["text_sub"], wraplength=280, justify="left").pack(anchor="w", pady=(6, 12))

            ctk.CTkButton(
                c_in, text=btn_txt, font=get_font(11, "bold"), height=32, corner_radius=6,
                fg_color=palette["accent_green"], hover_color="#059669",
                text_color="#ffffff", command=cmd
            ).pack(anchor="w")

    def _build_pc_settings_tab(self, parent):
        self._build_tools_and_settings_tab(parent)

    # =========================================================================
    # 서브 컴포넌트: 주간 시간표 & 나이스 연동
    # =========================================================================
    def _build_weekly_and_neis_tab(self, parent):
        palette = theme_manager.get_theme()
        self.weekly_scroll = CTk2DScrollableFrame(parent, min_content_width=840, fg_color="transparent")
        self.weekly_scroll.pack(fill="both", expand=True, padx=6, pady=6)
        scroll = self.weekly_scroll.viewport

        # 1. 나이스 학교 및 학년/반 설정 카드
        cfg_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#222a3a", border_width=1, border_color="#38bdf8")
        cfg_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(cfg_card, text="🏫 나이스 학교 및 학년·반 설정 (전국 17개 교육청 Open API)", font=get_font(13, "bold"), text_color="#38bdf8").pack(anchor="w", padx=12, pady=(10, 4))

        row1 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(row1, text="교육청:", font=get_font(11, "bold"), width=50, anchor="w").pack(side="left")
        self.neis_office_combo = ctk.CTkComboBox(
            row1,
            values=list(OFFICE_CODES.keys()),
            font=get_font(11),
            width=130,
            height=30,
            state="readonly"
        )
        curr_office = neis_client.config.get("office_name", "전체 (전국)")
        self.neis_office_combo.set(curr_office if curr_office in OFFICE_CODES else "전체 (전국)")
        self.neis_office_combo.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(row1, text="학교명:", font=get_font(11, "bold"), width=48, anchor="w").pack(side="left")
        self.neis_school_search_entry = ctk.CTkEntry(row1, placeholder_text="예: 포항, 서울초, 신당초", font=get_font(12), height=30)
        self.neis_school_search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.neis_school_search_entry.bind("<Return>", lambda e: self._search_neis_school())

        ctk.CTkButton(
            row1, 
            text="🔍 학교 검색", 
            font=get_font(12, "bold"), 
            fg_color="#0a84ff",
            hover_color="#0071e3",
            width=90, 
            height=30, 
            command=self._search_neis_school
        ).pack(side="right")

        row2 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(4, 10))

        self.neis_school_info_lbl = ctk.CTkLabel(
            row2,
            text=f"현재: {neis_client.config.get('school_name', '학교 미설정')} ({neis_client.config.get('office_name', '전국')})",
            font=get_font(12, "bold"),
            text_color="#4ade80"
        )
        self.neis_school_info_lbl.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(row2, text="학년:", font=get_font(11, "bold")).pack(side="left", padx=(0, 2))
        self.neis_grade_combo = ctk.CTkComboBox(row2, values=[str(i) for i in range(1, 7)], width=54, font=get_font(11), state="readonly")
        self.neis_grade_combo.set(str(neis_client.config.get("grade", "5")))
        self.neis_grade_combo.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(row2, text="반:", font=get_font(11, "bold")).pack(side="left", padx=(0, 2))
        self.neis_class_combo = ctk.CTkComboBox(row2, values=[str(i) for i in range(1, 16)], width=58, font=get_font(11), state="readonly")
        self.neis_class_combo.set(str(neis_client.config.get("class_nm", "1")))
        self.neis_class_combo.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            row2,
            text="💾 저장",
            font=get_font(11, "bold"),
            fg_color="#10b981",
            hover_color="#059669",
            width=54,
            height=28,
            command=self._save_neis_grade_class
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            row2,
            text="🔄 나이스 시간표 조회 & 내 시간표로 복사",
            font=get_font(11, "bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=28,
            command=self._fetch_and_display_neis_timetable
        ).pack(side="right")

        # 2. 일과표 도구 & 시차 조정 바
        period_box = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#1e2230", border_width=1, border_color="#374151")
        period_box.pack(fill="x", pady=(0, 8))

        pb_top = ctk.CTkFrame(period_box, fg_color="transparent")
        pb_top.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(pb_top, text="⏰ 일과표 시차 조정 & 점심시간 위치:", font=get_font(12, "bold"), text_color="#60a5fa").pack(side="left", padx=(0, 6))

        ctk.CTkButton(pb_top, text="⏪ 5분 당기기", font=get_font(10), width=68, height=24, fg_color="#334155", hover_color="#475569", command=lambda: self._shift_periods(-5)).pack(side="left", padx=2)
        ctk.CTkButton(pb_top, text="⏩ 5분 미루기", font=get_font(10), width=68, height=24, fg_color="#334155", hover_color="#475569", command=lambda: self._shift_periods(5)).pack(side="left", padx=2)

        self.lunch_pos_combo = ctk.CTkComboBox(
            pb_top,
            values=["3교시 후 점심", "4교시 후 점심 (기본)", "5교시 후 점심"],
            font=get_font(11),
            width=130,
            height=24,
            state="readonly",
            command=self._on_lunch_pos_changed
        )
        curr_lunch_p = timetable_manager.settings.get("lunch_after_period", 4)
        pos_str_map = {3: "3교시 후 점심", 4: "4교시 후 점심 (기본)", 5: "5교시 후 점심"}
        self.lunch_pos_combo.set(pos_str_map.get(curr_lunch_p, "4교시 후 점심 (기본)"))
        self.lunch_pos_combo.pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            pb_top,
            text="🔄 기본값 복구",
            font=get_font(10),
            fg_color="#475569",
            hover_color="#334155",
            width=70,
            height=24,
            command=self._reset_all_defaults
        ).pack(side="right")

        # 3. 주간 시간표 그리드
        tt_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#1e2230", border_width=1, border_color="#374151")
        tt_card.pack(fill="both", expand=True, pady=(0, 8))

        tt_hdr = ctk.CTkFrame(tt_card, fg_color="transparent")
        tt_hdr.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(tt_hdr, text="📝 주간 시간표 (월~금 6교시, 수요일 5교시 기본):", font=get_font(12, "bold"), text_color="#38bdf8").pack(side="left")

        ctk.CTkButton(
            tt_hdr,
            text="💾 주간 시간표 저장",
            font=get_font(11, "bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=26,
            command=self._save_weekly_timetable_inputs
        ).pack(side="right")

        self.weekly_grid_container = ctk.CTkFrame(tt_card, fg_color="transparent")
        self.weekly_grid_container.pack(fill="both", expand=True, padx=8, pady=4)

        self._render_weekly_grid()

        # 4. 나이스 실시간 조회 결과 영역 (접이식)
        res_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#161d2f", border_width=1, border_color="#26334d")
        res_card.pack(fill="x", pady=(0, 8))

        rc_hdr = ctk.CTkFrame(res_card, fg_color="transparent")
        rc_hdr.pack(fill="x", padx=12, pady=(6, 4))

        self.neis_res_title = ctk.CTkLabel(rc_hdr, text="📋 나이스 실시간 시간표 조회 결과", font=get_font(12, "bold"), text_color="#60a5fa")
        self.neis_res_title.pack(side="left")

        ctk.CTkButton(
            rc_hdr,
            text="📥 오늘 내 시간표로 즉시 복사",
            font=get_font(10, "bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=24,
            command=self._copy_neis_to_my_timetable
        ).pack(side="right")

        self.neis_timetable_container = ctk.CTkFrame(res_card, fg_color="transparent")
        self.neis_timetable_container.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.last_fetched_neis_list = []
        self._fetch_and_display_neis_timetable()
        self.weekly_scroll.bind_children_mousewheel()

    # =========================================================================
    # 뷰 4: PC 전원 & 도구 설정 통합 (컴퓨터 예약 + 화면 분할 + 테마/설정)
    # =========================================================================
    def _build_tools_and_settings_tab(self, parent):
        palette = theme_manager.get_theme()
        self.settings_scroll = CTk2DScrollableFrame(parent, min_content_width=720, fg_color="transparent")
        self.settings_scroll.pack(fill="both", expand=True, padx=6, pady=6)
        scroll = self.settings_scroll.viewport

        # 1. 컴퓨터 예약/종료 카드
        pc_card = ctk.CTkFrame(scroll, corner_radius=12, fg_color=palette["card_inner_bg"], border_width=1, border_color=palette["card_border"])
        pc_card.pack(fill="x", pady=(0, 10))

        pc_hdr_r = ctk.CTkFrame(pc_card, fg_color="transparent")
        pc_hdr_r.pack(fill="x", padx=14, pady=(12, 6))

        ctk.CTkLabel(
            pc_hdr_r,
            text="⏰ 컴퓨터 예약 / 종료 / 회의 알람 설정",
            font=get_font(13, "bold"),
            text_color=palette["text_main"]
        ).pack(side="left")

        sch_mgr_btn = ctk.CTkButton(
            pc_hdr_r,
            text="📅  예약 & 알람 관리 센터",
            font=get_font(10, "bold"),
            fg_color=palette["accent"],
            hover_color=palette["accent_hover"],
            text_color="#ffffff",
            height=28,
            corner_radius=6,
            command=lambda: open_schedule_dialog(self, self.manager)
        )
        sch_mgr_btn.pack(side="right")
        attach_tooltip(sch_mgr_btn, "현재 등록된 모든 예약과 알람을 모아보고 개별 취소 또는 일괄 취소합니다.")

        # 2개월 제한 안내 칩
        limit_chip = ctk.CTkFrame(pc_card, fg_color=palette["card_bg"], corner_radius=6, border_width=1, border_color=palette["card_border"])
        limit_chip.pack(fill="x", padx=14, pady=(0, 6))
        ctk.CTkLabel(
            limit_chip,
            text="💡 컴퓨터 전원 예약은 시스템 안정성을 위해 최대 2개월(60일)까지만 지원됩니다.",
            font=get_font(9, "bold"),
            text_color=palette["accent"]
        ).pack(side="left", padx=10, pady=4)

        # 1-1. 동작 선택 행 (깔끔한 세그먼트 버튼 & 라벨)
        pc_row1 = ctk.CTkFrame(pc_card, fg_color="transparent")
        pc_row1.pack(fill="x", padx=14, pady=4)

        ctk.CTkLabel(
            pc_row1,
            text="동작 선택:",
            font=get_font(11, "bold"),
            text_color=palette["text_main"],
            width=70,
            anchor="w"
        ).pack(side="left")

        act_map = {"종료": "shutdown", "다시 시작": "restart", "절전": "sleep", "알람(소리)": "alarm"}
        inv_act_map = {v: k for k, v in act_map.items()}

        def _on_action_seg(choice):
            self.pc_action.set(act_map.get(choice, "shutdown"))

        act_seg = ctk.CTkSegmentedButton(
            pc_row1,
            values=["종료", "다시 시작", "절전", "알람(소리)"],
            font=get_font(11, "bold"),
            selected_color=palette["accent"],
            selected_hover_color=palette["accent_hover"],
            unselected_color=palette["sidebar_btn_hover"],
            unselected_hover_color=palette["sidebar_bg"],
            text_color="#ffffff",
            command=_on_action_seg
        )
        act_seg.set(inv_act_map.get(self.pc_action.get(), "종료"))
        act_seg.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # 1-2. 시간 선택 행 (빠른 프리셋 + 수동 시간 자유 입력 지원)
        time_container = ctk.CTkFrame(pc_card, fg_color="transparent")
        time_container.pack(fill="x", padx=14, pady=(6, 12))

        # 상단 서브 행: 방식 전환 세그먼트 + 전체 취소 버튼
        tc_top = ctk.CTkFrame(time_container, fg_color="transparent")
        tc_top.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            tc_top,
            text="예약 방식:",
            font=get_font(11, "bold"),
            text_color=palette["text_main"],
            width=70,
            anchor="w"
        ).pack(side="left")

        def _on_time_mode_toggle(choice):
            if "프리셋" in choice:
                custom_box.pack_forget()
                preset_box.pack(fill="x")
            else:
                preset_box.pack_forget()
                custom_box.pack(fill="x")

        time_mode_seg = ctk.CTkSegmentedButton(
            tc_top,
            values=["⚡ 빠른 프리셋 (추천)", "⏰ 수동 시간 직접 입력"],
            font=get_font(10, "bold"),
            selected_color=palette["accent"],
            selected_hover_color=palette["accent_hover"],
            unselected_color=palette["sidebar_btn_hover"],
            unselected_hover_color=palette["sidebar_bg"],
            text_color="#ffffff",
            command=_on_time_mode_toggle
        )
        time_mode_seg.set("⚡ 빠른 프리셋 (추천)")
        time_mode_seg.pack(side="left", padx=(0, 8))

        cancel_all_btn = ctk.CTkButton(
            tc_top,
            text="🛑 전체 예약 취소",
            font=get_font(10, "bold"),
            fg_color="#3f1d24",
            hover_color="#dc2626",
            text_color="#fca5a5",
            width=95,
            height=28,
            corner_radius=6,
            command=self._cancel_schedule
        )
        cancel_all_btn.pack(side="right")

        # 1-2-A. 빠른 프리셋 박스
        preset_box = ctk.CTkFrame(time_container, fg_color="transparent")
        preset_box.pack(fill="x")

        for col_idx in range(4):
            preset_box.grid_columnconfigure(col_idx, weight=1)

        presets = [(30, "30분 뒤"), (60, "1시간 뒤"), (90, "1.5시간 뒤"), (120, "2시간 뒤")]
        for idx, (m, lbl) in enumerate(presets):
            btn = ctk.CTkButton(
                preset_box,
                text=lbl,
                font=get_font(11, "bold"),
                height=30,
                corner_radius=8,
                fg_color=palette["sidebar_btn_hover"],
                hover_color=palette["accent_hover"],
                text_color=palette["text_main"],
                command=lambda mins=m: self._quick_schedule_pc(mins)
            )
            btn.grid(row=0, column=idx, padx=2, sticky="nsew")

        # 1-2-B. 수동 시간 직접 입력 박스 (자유로운 시간/분 입력)
        custom_box = ctk.CTkFrame(time_container, fg_color=palette["card_bg"], corner_radius=8, border_width=1, border_color=palette["card_border"])
        # 기본 상태는 숨김 (프리셋이 우선 표시)

        cb_in = ctk.CTkFrame(custom_box, fg_color="transparent")
        cb_in.pack(fill="x", padx=10, pady=8)

        ctk.CTkLabel(cb_in, text="⏳ 실행 시각:", font=get_font(11, "bold"), text_color=palette["text_main"]).pack(side="left", padx=(0, 6))

        self.custom_hour_entry = ctk.CTkEntry(cb_in, width=44, height=28, font=get_font(11, "bold"), justify="center")
        self.custom_hour_entry.insert(0, "1")
        self.custom_hour_entry.pack(side="left")
        ctk.CTkLabel(cb_in, text="시간", font=get_font(11), text_color=palette["text_main"]).pack(side="left", padx=(4, 8))

        self.custom_min_entry = ctk.CTkEntry(cb_in, width=44, height=28, font=get_font(11, "bold"), justify="center")
        self.custom_min_entry.insert(0, "30")
        self.custom_min_entry.pack(side="left")
        ctk.CTkLabel(cb_in, text="분 뒤 실행", font=get_font(11), text_color=palette["text_main"]).pack(side="left", padx=(4, 12))

        self.custom_memo_entry = ctk.CTkEntry(cb_in, placeholder_text="예약 메모 (선택)", width=140, height=28, font=get_font(10))
        self.custom_memo_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            cb_in,
            text="➕ 예약 등록",
            font=get_font(11, "bold"),
            fg_color=palette["accent"],
            hover_color=palette["accent_hover"],
            text_color="#ffffff",
            width=90,
            height=28,
            corner_radius=6,
            command=self._on_custom_time_schedule_submit
        ).pack(side="right")

        # 2. 화면 분할 & 위젯 도구
        screen_card = ctk.CTkFrame(scroll, corner_radius=12, fg_color=palette["card_inner_bg"], border_width=1, border_color=palette["card_border"])
        screen_card.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(screen_card, text="🖥️ 화면 분할 최적화 & 창 위치 스냅", font=get_font(13, "bold"), text_color=palette["accent"]).pack(anchor="w", padx=14, pady=(10, 6))

        sc_row = ctk.CTkFrame(screen_card, fg_color="transparent")
        sc_row.pack(fill="x", padx=14, pady=(2, 10))

        snap_map = {
            "좌측 반": "left_half",
            "우측 반": "right_half",
            "좌측 1/3": "left_third",
            "중앙 표준": "center_opt",
            "전체 화면": "maximize"
        }

        def _on_snap_select(choice: str):
            mode = snap_map.get(choice, "center_opt")
            self._snap_window(mode)

        self.snap_seg_btn = ctk.CTkSegmentedButton(
            sc_row,
            values=["좌측 반", "우측 반", "좌측 1/3", "중앙 표준", "전체 화면"],
            font=get_font(11, "bold"),
            selected_color=palette["accent"],
            selected_hover_color=palette["accent_hover"],
            unselected_color=palette["sidebar_btn_hover"],
            unselected_hover_color=palette["sidebar_bg"],
            text_color="#ffffff",
            command=_on_snap_select
        )
        self.snap_seg_btn.set("중앙 표준")
        self.snap_seg_btn.pack(fill="x", expand=True)

        # 2-1. ✏️ 화면 위 판서 & 교사용 플로팅 퀵 도구 카드
        tools_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#1e2230", border_width=1, border_color="#38bdf8")
        tools_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(tools_card, text="✏️ 화면 위 자유 판서 & 플로팅 퀵 툴바 (수업/수행평가/화상회의)", font=get_font(13, "bold"), text_color="#38bdf8").pack(anchor="w", padx=12, pady=(10, 6))

        t_row1 = ctk.CTkFrame(tools_card, fg_color="transparent")
        t_row1.pack(fill="x", padx=12, pady=4)

        ctk.CTkButton(
            t_row1,
            text="✏️ 화면 위 자유 판서 시작",
            font=get_font(12, "bold"),
            fg_color="#ea580c",
            hover_color="#c2410c",
            height=34,
            command=self._open_screen_drawing
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(
            t_row1,
            text="🛠️ 스마트 플로팅 퀵 바",
            font=get_font(12, "bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=34,
            command=self._open_floating_quick_toolbar
        ).pack(side="left", fill="x", expand=True, padx=4)

        ctk.CTkButton(
            t_row1,
            text="⏱️ 활동 타이머 & 🎲 뽑기",
            font=get_font(12, "bold"),
            fg_color="#059669",
            hover_color="#047857",
            height=34,
            command=self._open_classroom_tools
        ).pack(side="right", fill="x", expand=True, padx=(4, 0))

        t_info = "• 화면 판서: 어떤 웹/앱(나이스, 유튜브, PPT 등)이 띄워져 있어도 화면 전체 위에 펜/형광펜/도형으로 판서합니다.\n• 스마트 퀵 바: 모니터 구석에 둥둥 띄워두고 판서, 시간표, 타이머, 발표자 뽑기를 원클릭으로 실행합니다."
        ctk.CTkLabel(tools_card, text=t_info, font=get_font(11), text_color="#cbd5e1", justify="left", anchor="w").pack(fill="x", padx=12, pady=(4, 10))

        # 3. 환경 설정 & 테마 & 시작프로그램
        self._build_settings_tab(scroll)

    def _search_neis_school(self):
        query = self.neis_school_search_entry.get().strip()
        office_name = self.neis_office_combo.get()

        def on_selected(school_info: dict[str, str]):
            neis_client.save_config({
                "office_code": school_info.get("office_code", ""),
                "office_name": school_info.get("office_name", ""),
                "school_code": school_info.get("school_code", ""),
                "school_name": school_info.get("school_name", "")
            })
            self.neis_school_info_lbl.configure(
                text=f"현재: {school_info.get('school_name', '')} ({school_info.get('office_name', '')})"
            )
            self._play_sound("success")
            self._fetch_and_display_neis_timetable()
            self._refresh_today_meal()

        SchoolSearchDialog(self, initial_query=query, initial_office=office_name, on_select_callback=on_selected)

    def _save_neis_grade_class(self):
        g = self.neis_grade_combo.get()
        c = self.neis_class_combo.get()
        neis_client.save_config({"grade": g, "class_nm": c})
        self._play_sound("success")
        self._show_simple_alert("설정 저장", f"{g}학년 {c}반으로 저장되었습니다!")
        self._fetch_and_display_neis_timetable()

    def _fetch_and_display_neis_timetable(self):
        today = datetime.date.today()
        cfg = neis_client.config
        s_name = cfg.get("school_name", "학교 미설정")
        g = cfg.get("grade", "5")
        c = cfg.get("class_nm", "1")
        weekday_str = DAYS_KO[today.weekday()]

        if hasattr(self, "neis_res_title"):
            self.neis_res_title.configure(
                text=f"📋 나이스 실시간 시간표: {s_name} {g}학년 {c}반 ({today.strftime('%m/%d')} {weekday_str})"
            )

        ok, tt_list, msg = neis_client.get_timetable_for_date(today)
        if ok and tt_list:
            self.last_fetched_neis_list = tt_list
            self._render_neis_timetable_items(tt_list)
        else:
            self.last_fetched_neis_list = []
            self._render_neis_timetable_items([])

    def _render_neis_timetable_items(self, tt_list: list):
        for w in self.neis_timetable_container.winfo_children():
            w.destroy()

        if not tt_list:
            lbl = ctk.CTkLabel(
                self.neis_timetable_container,
                text="조회된 나이스 시간표가 없습니다 (학교/학년/반 또는 날짜를 확인해주세요).",
                font=get_font(11),
                text_color="#94a3b8"
            )
            lbl.pack(pady=8)
            return

        lesson_periods_map = {}
        for p in timetable_manager.periods:
            if not p.get("is_lunch", False) and "교시" in p.get("name", ""):
                try:
                    num = int(p["name"].replace("교시", "").strip())
                    lesson_periods_map[num] = p
                except Exception:
                    pass

        for it in tt_list:
            p_num = int(it.get("period", 1))
            p_time_info = lesson_periods_map.get(p_num, {"start": "--:--", "end": "--:--"})
            t_str = f"{p_time_info.get('start', '--:--')} ~ {p_time_info.get('end', '--:--')}"

            row = ctk.CTkFrame(self.neis_timetable_container, fg_color="#161d2f", corner_radius=8, border_width=1, border_color="#26334d")
            row.pack(fill="x", pady=3)

            # 교시 뱃지
            ctk.CTkLabel(
                row, 
                text=f"{it['period']}교시", 
                font=get_font(11, "bold"), 
                fg_color="#0284c7",
                text_color="#ffffff",
                corner_radius=6,
                width=54,
                height=26
            ).pack(side="left", padx=(8, 8), pady=4)

            # 시간 범위
            ctk.CTkLabel(
                row,
                text=t_str,
                font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                text_color="#94a3b8",
                width=95
            ).pack(side="left", padx=(0, 10))

            # 과목명
            ctk.CTkLabel(
                row, 
                text=it["subject"], 
                font=get_font(13, "bold"), 
                text_color="#ffffff",
                anchor="w"
            ).pack(side="left", fill="x", expand=True, padx=4, pady=4)

    def _copy_neis_to_my_timetable(self):
        if not self.last_fetched_neis_list:
            self._show_simple_alert("안내", "복사할 나이스 시간표 데이터가 없습니다.")
            return

        today = datetime.date.today()
        weekday_idx = today.weekday()
        if weekday_idx >= 5:
            self._show_simple_alert("안내", "주말에는 시간표를 복사할 수 없습니다.")
            return

        day_key = DAY_KEYS[weekday_idx]
        current_list = timetable_manager.weekly_timetable.get(day_key, [])

        for idx, item in enumerate(self.last_fetched_neis_list):
            if idx < len(current_list):
                current_list[idx]["subject"] = item["subject"]
            else:
                current_list.append({"subject": item["subject"], "tag": "담임"})

        timetable_manager.weekly_timetable[day_key] = current_list
        timetable_manager.save_weekly_timetable(timetable_manager.weekly_timetable)
        self._render_today_items()
        self._render_weekly_grid()
        self._play_sound("success")
        self._show_simple_alert("복사 완료", f"오늘({DAYS_KO[weekday_idx]}요일) 나이스 시간표가 내 시간표로 복사되었습니다!")

    def _render_weekly_grid(self):
        for w in self.weekly_grid_container.winfo_children():
            w.destroy()

        self.weekly_grid_entries = {}
        tt = timetable_manager.weekly_timetable

        # 헤더: 요일 (월, 화, 수, 목, 금)
        hdr_row = ctk.CTkFrame(self.weekly_grid_container, fg_color="transparent")
        hdr_row.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(hdr_row, text="교시", font=get_font(11, "bold"), width=50, text_color="#94a3b8").pack(side="left", padx=2)
        for d_key, d_name in zip(DAY_KEYS, DAYS_KO[:5]):
            lbl = ctk.CTkLabel(hdr_row, text=f"{d_name}요일", font=get_font(12, "bold"), text_color="#38bdf8")
            lbl.pack(side="left", fill="x", expand=True, padx=2)

        # 1~6교시 행
        for p_idx in range(6):
            row_f = ctk.CTkFrame(self.weekly_grid_container, fg_color="transparent")
            row_f.pack(fill="x", pady=2)

            ctk.CTkLabel(row_f, text=f"{p_idx + 1}교시", font=get_font(11, "bold"), width=50, text_color="#64748b").pack(side="left", padx=2)

            for d_key in DAY_KEYS:
                cell_f = ctk.CTkFrame(row_f, fg_color="#181d28", corner_radius=6, border_width=1, border_color="#2d3748")
                cell_f.pack(side="left", fill="x", expand=True, padx=2)

                day_items = tt.get(d_key, [])
                item = day_items[p_idx] if p_idx < len(day_items) else {"subject": "", "tag": "담임"}
                subj_val = item.get("subject", "")
                tag_val = item.get("tag", "담임")

                entry = ctk.CTkEntry(cell_f, font=get_font(11), height=26, fg_color="transparent", border_width=0)
                entry.insert(0, subj_val)
                entry.pack(side="left", fill="x", expand=True, padx=(4, 2))

                tag_var = ctk.StringVar(value=tag_val)
                tag_btn = ctk.CTkButton(
                    cell_f,
                    text=tag_val,
                    font=get_font(9, "bold"),
                    width=32,
                    height=20,
                    fg_color="#5e5ce6" if tag_val == "전담" else "#334155",
                    hover_color="#4338ca"
                )
                tag_btn.configure(command=lambda tv=tag_var, btn=tag_btn: self._toggle_cell_tag(tv, btn))
                tag_btn.pack(side="right", padx=2)

                self.weekly_grid_entries[(d_key, p_idx)] = (entry, tag_var)

    def _toggle_cell_tag(self, tag_var: ctk.StringVar, btn: ctk.CTkButton):
        cur = tag_var.get()
        nxt = "전담" if cur == "담임" else "담임"
        tag_var.set(nxt)
        btn.configure(
            text=nxt,
            fg_color="#5e5ce6" if nxt == "전담" else "#334155"
        )

    def _save_weekly_timetable_inputs(self):
        new_tt = {}
        for d_key in DAY_KEYS:
            new_tt[d_key] = []
            for p_idx in range(6):
                entry, tag_var = self.weekly_grid_entries.get((d_key, p_idx), (None, None))
                subj = entry.get().strip() if entry else ""
                tag = tag_var.get() if tag_var else "담임"
                new_tt[d_key].append({"subject": subj, "tag": tag})

        timetable_manager.save_weekly_timetable(new_tt)
        self._render_today_items()
        self._play_sound("success")
        self._show_simple_alert("저장 완료", "주간 시간표가 성공적으로 저장되었습니다!")

    def _on_lunch_pos_changed(self, choice: str):
        p_num = 3 if "3교시" in choice else (5 if "5교시" in choice else 4)
        timetable_manager.update_lunch_position(p_num)
        self._render_today_items()
        self._render_weekly_grid()

    def _shift_periods(self, minutes: int):
        timetable_manager.shift_all_periods(minutes)
        self._render_today_items()
        self._render_weekly_grid()
        self._play_sound("success")

    def _reset_all_defaults(self):
        timetable_manager.reset_to_default_periods()
        if hasattr(self, "lunch_pos_combo"):
            self.lunch_pos_combo.set("4교시 후 점심 (기본)")
        self._render_today_items()
        self._render_weekly_grid()
        self._play_sound("success")
        self._show_simple_alert("초기화 완료", "일과표 및 점심시간이 기본 표준 시간표로 초기화되었습니다.")

    # =========================================================================
    # 뷰 4: 나이스 엑셀 자동입력 (최우선 핵심)
    # =========================================================================
    def _build_neis_auto_input_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=6)

        file_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#222a3a", border_width=1, border_color="#38bdf8")
        file_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(file_card, text="1️⃣ Excel 파일 및 시트 선택 (.xlsx)", font=get_font(13, "bold"), text_color="#38bdf8").pack(anchor="w", padx=12, pady=(10, 6))

        fc_row1 = ctk.CTkFrame(file_card, fg_color="transparent")
        fc_row1.pack(fill="x", padx=12, pady=4)

        self.excel_path_entry = ctk.CTkEntry(fc_row1, placeholder_text="Excel 파일을 선택해주세요 (.xlsx)", font=get_font(12), height=32)
        self.excel_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            fc_row1,
            text="📂 파일 찾기",
            font=get_font(12, "bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            width=95,
            height=32,
            command=self._select_excel_file
        ).pack(side="right")

        fc_row2a = ctk.CTkFrame(file_card, fg_color="transparent")
        fc_row2a.pack(fill="x", padx=12, pady=(4, 2))

        ctk.CTkLabel(fc_row2a, text="작업 시트:", font=get_font(12, "bold")).pack(side="left", padx=(0, 6))
        self.sheet_combo = ctk.CTkComboBox(fc_row2a, values=["선택 대기"], font=get_font(12), height=30, state="readonly", command=self._on_sheet_selected)
        self.sheet_combo.pack(side="left", fill="x", expand=True, padx=(0, 6))

        fc_row2b = ctk.CTkFrame(file_card, fg_color="transparent")
        fc_row2b.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(fc_row2b, text="대상 화면:", font=get_font(12, "bold")).pack(side="left", padx=(0, 6))
        self.page_type_combo = ctk.CTkComboBox(
            fc_row2b,
            values=["행동특성 및 종합의견", "교과 학기말 종합의견"],
            font=get_font(12),
            height=30,
            state="readonly"
        )
        self.page_type_combo.set("행동특성 및 종합의견")
        self.page_type_combo.pack(side="left", fill="x", expand=True)

        col_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#222a3a", border_width=1, border_color="#374151")
        col_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(col_card, text="2️⃣ 열 매핑 (자동 감지됨) & 입력 모드 설정", font=get_font(13, "bold"), text_color="#60a5fa").pack(anchor="w", padx=12, pady=(10, 6))

        cm_row = ctk.CTkFrame(col_card, fg_color="transparent")
        cm_row.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(cm_row, text="번호 열:", font=get_font(11, "bold"), text_color="#38bdf8").pack(side="left", padx=(0, 4))
        self.col_num_combo = ctk.CTkComboBox(cm_row, values=["선택"], width=90, font=get_font(11), state="readonly", command=self._refresh_parsed_preview)
        self.col_num_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(cm_row, text="이름 열:", font=get_font(11, "bold"), text_color="#94a3b8").pack(side="left", padx=(0, 4))
        self.col_name_combo = ctk.CTkComboBox(cm_row, values=["선택"], width=90, font=get_font(11), state="readonly", command=self._refresh_parsed_preview)
        self.col_name_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(cm_row, text="내용 열:", font=get_font(11, "bold"), text_color="#4ade80").pack(side="left", padx=(0, 4))
        self.col_content_combo = ctk.CTkComboBox(cm_row, values=["선택"], width=130, font=get_font(11), state="readonly", command=self._refresh_parsed_preview)
        self.col_content_combo.pack(side="left", padx=(0, 10))

        mode_row = ctk.CTkFrame(col_card, fg_color="#181d28", corner_radius=8)
        mode_row.pack(fill="x", padx=12, pady=(4, 10))

        ctk.CTkLabel(mode_row, text="기존 내용 처리:", font=get_font(11, "bold")).pack(side="left", padx=8, pady=6)
        ctk.CTkRadioButton(mode_row, text="빈 칸에만 입력 (기본·안전)", value="EMPTY_ONLY", variable=self.input_mode, font=get_font(11, "bold")).pack(side="left", padx=6)
        ctk.CTkRadioButton(mode_row, text="기존 내용 뒤에 이어쓰기", value="APPEND", variable=self.input_mode, font=get_font(11)).pack(side="left", padx=6)
        ctk.CTkRadioButton(mode_row, text="기존 내용 덮어쓰기 (교체)", value="OVERWRITE", variable=self.input_mode, font=get_font(11)).pack(side="left", padx=6)

        preview_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#1e2230", border_width=1, border_color="#374151")
        preview_card.pack(fill="both", expand=True, pady=(0, 8))

        pc_hdr = ctk.CTkFrame(preview_card, fg_color="transparent")
        pc_hdr.pack(fill="x", padx=12, pady=(10, 6))

        self.preview_summary_lbl = ctk.CTkLabel(
            pc_hdr,
            text="📋 3️⃣ 입력 데이터 사전 검증 및 학생별 미리보기 (파일을 열어주세요)",
            font=get_font(13, "bold"),
            text_color="#f1f5f9"
        )
        self.preview_summary_lbl.pack(side="left")

        self.preview_scroll = ctk.CTkScrollableFrame(preview_card, fg_color="#181d28", height=180)
        self.preview_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        exec_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#0f291e", border_width=2, border_color="#10b981")
        exec_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            exec_card,
            text="🚀 4️⃣ 4세대 나이스 학생번호 기준 안전 자동입력 실행",
            font=get_font(14, "bold"),
            text_color="#6ee7b7"
        ).pack(anchor="w", padx=12, pady=(10, 4))

        exec_btn_row = ctk.CTkFrame(exec_card, fg_color="transparent")
        exec_btn_row.pack(fill="x", padx=12, pady=6)

        self.btn_copy_script = ctk.CTkButton(
            exec_btn_row,
            text="📋 [원클릭] 나이스 자동입력 스크립트 복사 (추천: F12 콘솔창 붙여넣기)",
            font=get_font(12, "bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=38,
            command=self._copy_auto_input_script
        )
        self.btn_copy_script.pack(side="left", fill="x", expand=True, padx=(0, 6))

        rule_box = ctk.CTkFrame(exec_card, fg_color="#181d28", corner_radius=6)
        rule_box.pack(fill="x", padx=12, pady=(4, 10))

        rule_text = (
            "🛡️ [철저한 안전장치 및 사용 안내]\n"
            "1. 학생 매칭은 '학생번호(값 자체)'를 기준으로 1:1 매칭됩니다 (중간 번호가 빠져도 절대 밀리지 않음).\n"
            "2. Excel에 동일 학생번호가 중복되어 있으면 안전을 위해 입력을 시작하지 않습니다.\n"
            "3. [스크립트 복사] 후 나이스 화면에서 F12(개발자도구 콘솔)를 열고 붙여넣으면 즉시 초고속 자동입력 및 검증이 완료됩니다.\n"
            "4. ★ 프로그램은 [저장] 버튼을 절대 누르지 않습니다. 화면의 내용을 직접 확인 후 [저장]을 눌러주세요!"
        )
        ctk.CTkLabel(rule_box, text=rule_text, font=get_font(11), text_color="#cbd5e1", justify="left").pack(padx=10, pady=8)

    def _select_excel_file(self):
        fp = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
        if not fp:
            return

        self.excel_path_entry.delete(0, "end")
        self.excel_path_entry.insert(0, fp)

        ok, msg, sheets = self.excel_parser.load_file(fp)
        if not ok:
            self._show_simple_alert("오류", msg)
            return

        self.sheet_combo.configure(values=sheets)
        self.sheet_combo.set(sheets[0])
        self._on_sheet_selected(sheets[0])

    def _on_sheet_selected(self, sheet_name: str):
        ok, msg, headers, detected = self.excel_parser.select_sheet(sheet_name)
        if not ok:
            self._show_simple_alert("오류", msg)
            return

        header_display = [f"{i}: {h}" for i, h in enumerate(headers)]
        self.col_num_combo.configure(values=header_display)
        self.col_name_combo.configure(values=header_display)
        self.col_content_combo.configure(values=header_display)

        if 0 <= detected["num_col"] < len(header_display):
            self.col_num_combo.set(header_display[detected["num_col"]])
        if 0 <= detected["name_col"] < len(header_display):
            self.col_name_combo.set(header_display[detected["name_col"]])
        if 0 <= detected["content_col"] < len(header_display):
            self.col_content_combo.set(header_display[detected["content_col"]])

        self._refresh_parsed_preview()

    def _refresh_parsed_preview(self, _=None):
        for w in self.preview_scroll.winfo_children():
            w.destroy()

        num_str = self.col_num_combo.get()
        name_str = self.col_name_combo.get()
        content_str = self.col_content_combo.get()

        if ":" not in num_str or ":" not in content_str:
            return

        try:
            num_idx = int(num_str.split(":")[0])
            name_idx = int(name_str.split(":")[0]) if ":" in name_str else -1
            content_idx = int(content_str.split(":")[0])
        except Exception:
            return

        raw_records = self.excel_parser.parse_data(num_idx, name_idx, content_idx)
        self.validation_result = DataValidator.validate(raw_records)

        if not self.validation_result.is_valid:
            self.preview_summary_lbl.configure(
                text=f"❌ 검증 실패: 치명적인 오류 {len(self.validation_result.fatal_errors)}건 발견 (입력 차단됨)",
                text_color="#f87171"
            )
            err_box = ctk.CTkFrame(self.preview_scroll, fg_color="#3b1d11", corner_radius=8, border_width=1, border_color="#ef4444")
            err_box.pack(fill="x", pady=6)
            for err in self.validation_result.fatal_errors:
                ctk.CTkLabel(err_box, text=err, font=get_font(12, "bold"), text_color="#fca5a5", justify="left").pack(anchor="w", padx=10, pady=2)
            self.btn_copy_script.configure(state="disabled", fg_color="#374151")
            return

        self.btn_copy_script.configure(state="normal", fg_color="#10b981")
        valid_cnt = self.validation_result.valid_students_count
        skip_cnt = self.validation_result.skipped_students_count

        self.preview_summary_lbl.configure(
            text=f"✅ 검증 완료: 총 {len(self.validation_result.students_to_input)}명 (입력 대상: {valid_cnt}명, 내용없음 건너뜀: {skip_cnt}명)",
            text_color="#4ade80"
        )

        if self.validation_result.warnings:
            warn_box = ctk.CTkFrame(self.preview_scroll, fg_color="#2e2410", corner_radius=6)
            warn_box.pack(fill="x", pady=(0, 6))
            for w in self.validation_result.warnings:
                ctk.CTkLabel(warn_box, text=w, font=get_font(11), text_color="#fde047").pack(anchor="w", padx=8, pady=1)

        for st in self.validation_result.students_to_input:
            row_frame = ctk.CTkFrame(self.preview_scroll, fg_color="#222a3a", corner_radius=6)
            row_frame.pack(fill="x", pady=2)

            is_ready = st.get("status") == "READY"
            status_bg = "#059669" if is_ready else "#475569"
            status_txt = "✓ 입력 예정" if is_ready else "건너뜀"

            ctk.CTkLabel(
                row_frame,
                text=f"{st['student_number']}번 {st['name']}",
                font=get_font(12, "bold"),
                text_color="#38bdf8",
                width=110,
                anchor="w"
            ).pack(side="left", padx=8, pady=4)

            preview_snippet = st['content'][:45] + ("..." if len(st['content']) > 45 else "")
            ctk.CTkLabel(
                row_frame,
                text=preview_snippet if preview_snippet else "(내용 없음)",
                font=get_font(11),
                text_color="#f1f5f9" if preview_snippet else "#64748b",
                anchor="w"
            ).pack(side="left", fill="x", expand=True, padx=4)

            ctk.CTkLabel(
                row_frame,
                text=status_txt,
                font=get_font(11, "bold"),
                fg_color=status_bg,
                text_color="#ffffff",
                corner_radius=4,
                width=76,
                height=22
            ).pack(side="right", padx=8)

    def _copy_auto_input_script(self):
        if not self.validation_result or not self.validation_result.is_valid:
            self._show_simple_alert("오류", "유효한 Excel 데이터를 먼저 불러와 검증을 통과해야 합니다.")
            return

        page_choice = self.page_type_combo.get()
        p_type = NeisPageType.BEHAVIOR if "행동특성" in page_choice else NeisPageType.SUBJECT_TERM
        mode_val = self.input_mode.get()

        js_script = NeisScriptGenerator.generate_input_and_verify_script(
            students_data=self.validation_result.students_to_input,
            input_mode=mode_val,
            page_type=p_type
        )

        self.clipboard_clear()
        self.clipboard_append(js_script)
        self.update()

        self._play_sound("success")

        guide_msg = (
            "🎉 나이스 자동입력 스크립트가 클립보드에 복사되었습니다!\n\n"
            "1. 웹 브라우저(Chrome/Edge)에서 [나이스 입력 화면]을 엽니다.\n"
            "2. 키보드의 [F12]를 눌러 개발자 도구를 열고 상단 [Console(콘솔)] 탭을 클릭합니다.\n"
            "3. [Ctrl + V]로 붙여넣고 [Enter]를 누르면 학생번호를 1:1 매칭하여 초고속으로 자동입력됩니다!\n\n"
            "※ 작업 완료 후 화면의 입력값을 확인하시고 [저장] 버튼을 눌러주세요."
        )
        self._show_simple_alert("스크립트 복사 완료", guide_msg)

    # =========================================================================
    # 뷰 5: 컴퓨터 예약/종료
    # =========================================================================
    def _build_pc_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=6)

        action_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#222a3a", border_width=1, border_color="#374151")
        action_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            action_card, 
            text="1️⃣ 실행할 동작을 선택하세요:", 
            font=get_font(13, "bold"),
            text_color="#60a5fa"
        ).pack(anchor="w", padx=12, pady=(10, 6))

        r_frame = ctk.CTkFrame(action_card, fg_color="transparent")
        r_frame.pack(fill="x", padx=12, pady=(0, 10))

        for text, val in [("종료", "shutdown"), ("다시 시작", "restart"), ("절전 모드", "sleep")]:
            ctk.CTkRadioButton(
                r_frame, 
                text=text, 
                value=val, 
                variable=self.pc_action,
                font=get_font(13, "bold")
            ).pack(side="left", padx=8)

        time_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#222a3a", border_width=1, border_color="#374151")
        time_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            time_card, 
            text="2️⃣ 1회성 예약 시간을 설정하세요:", 
            font=get_font(13, "bold"),
            text_color="#60a5fa"
        ).pack(anchor="w", padx=12, pady=(10, 6))

        self.pc_mode_seg = ctk.CTkSegmentedButton(
            time_card,
            values=["빠른 시간", "직접 시간 설정", "특정 시각 지정"],
            font=get_font(12, "bold"),
            command=self._on_pc_mode_changed
        )
        self.pc_mode_seg.set("빠른 시간")
        self.pc_mode_seg.pack(fill="x", padx=12, pady=(0, 10))

        self.pc_time_content = ctk.CTkFrame(time_card, fg_color="transparent")
        self.pc_time_content.pack(fill="x", padx=12, pady=(0, 12))

        self._render_pc_quick_view()

        auto_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#1e293b", border_width=1, border_color="#38bdf8")
        auto_card.pack(fill="x", pady=(4, 8))

        ctk.CTkLabel(
            auto_card,
            text="🏢 월~금 주간 반복 자동 전원 관리 (공휴일 자동 제외):",
            font=get_font(13, "bold"),
            text_color="#38bdf8"
        ).pack(anchor="w", padx=12, pady=(10, 6))

        auto_row1 = ctk.CTkFrame(auto_card, fg_color="transparent")
        auto_row1.pack(fill="x", padx=12, pady=4)

        self.auto_shut_switch = ctk.CTkSwitch(
            auto_row1,
            text="월~금 퇴근 시각 자동 종료 활성화",
            font=get_font(12, "bold")
        )
        if self.manager.auto_power_config.get("auto_shutdown_enabled", False):
            self.auto_shut_switch.select()
        self.auto_shut_switch.pack(side="left")

        self.auto_shut_time_combo = ctk.CTkComboBox(
            auto_row1,
            values=["16:30", "16:40", "17:00", "17:30", "18:00"],
            font=get_font(12),
            width=90,
            height=28,
            state="readonly"
        )
        self.auto_shut_time_combo.set(self.manager.auto_power_config.get("auto_shutdown_time", "16:40"))
        self.auto_shut_time_combo.pack(side="left", padx=10)

        save_auto_btn = ctk.CTkButton(
            auto_row1,
            text="💾 스케줄 저장",
            font=get_font(11, "bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=28,
            command=self._save_auto_power_schedule
        )
        save_auto_btn.pack(side="right")

        auto_info = "• 토/일요일 및 법정 공휴일/대체공휴일은 자동으로 종료되지 않고 건너뜁니다.\n• 아침 자동 켜짐: 절전 모드 시 Windows 스케줄러로 자동 깨우기를 지원합니다."
        ctk.CTkLabel(auto_card, text=auto_info, font=get_font(11), text_color="#cbd5e1", justify="left", anchor="w").pack(fill="x", padx=12, pady=(4, 10))

    def _save_auto_power_schedule(self):
        is_on = self.auto_shut_switch.get() == 1
        t_val = self.auto_shut_time_combo.get()
        self.manager.save_auto_power_config({
            "auto_shutdown_enabled": is_on,
            "auto_shutdown_time": t_val,
            "skip_holidays": True
        })
        self._play_sound("success")
        status_txt = f"월~금 {t_val} 자동 종료 활성화 (공휴일 제외)" if is_on else "주간 자동 종료 비활성화"
        self._show_simple_alert("스케줄 저장 완료", f"{status_txt} 설정이 저장되었습니다!")

    def _on_pc_mode_changed(self, mode_str: str):
        for widget in self.pc_time_content.winfo_children():
            widget.destroy()

        if mode_str == "빠른 시간":
            self.pc_mode.set("quick")
            self._render_pc_quick_view()
        elif mode_str == "직접 시간 설정":
            self.pc_mode.set("custom")
            self._render_pc_custom_view()
        elif mode_str == "특정 시각 지정":
            self.pc_mode.set("clock")
            self._render_pc_clock_view()

    def _render_pc_quick_view(self):
        presets = [
            ("15분 후", 15), ("30분 후", 30), ("45분 후", 45), ("1시간 후", 60),
            ("1시간 30분 후", 90), ("2시간 후", 120), ("3시간 후", 180), ("4시간 후", 240)
        ]
        grid = ctk.CTkFrame(self.pc_time_content, fg_color="transparent")
        grid.pack(fill="x")

        self.pc_preset_btns = []
        for i, (label, mins) in enumerate(presets):
            row, col = i // 2, i % 2
            btn = ctk.CTkButton(
                grid,
                text=label,
                font=get_font(13, "bold"),
                height=38,
                corner_radius=8,
                fg_color="#2563eb" if mins == self.pc_preset_minutes.get() else "#374151",
                hover_color="#1d4ed8",
                text_color="#ffffff",
                command=lambda m=mins: self._select_pc_preset(m)
            )
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            self.pc_preset_btns.append((btn, mins))
            grid.grid_columnconfigure(col, weight=1)

    def _select_pc_preset(self, mins: int):
        self.pc_preset_minutes.set(mins)
        for btn, m in self.pc_preset_btns:
            if m == mins:
                btn.configure(fg_color="#2563eb", border_width=2, border_color="#93c5fd")
            else:
                btn.configure(fg_color="#374151", border_width=0)

    def _render_pc_custom_view(self):
        box = ctk.CTkFrame(self.pc_time_content, fg_color="transparent")
        box.pack(fill="x")

        h_row = ctk.CTkFrame(box, fg_color="transparent")
        h_row.pack(fill="x", pady=4)
        self.pc_h_label = ctk.CTkLabel(h_row, text=f"시간: {self.pc_custom_hours.get()} 시간", font=get_font(13, "bold"), width=100, anchor="w")
        self.pc_h_label.pack(side="left")
        ctk.CTkSlider(h_row, from_=0, to=24, number_of_steps=24, variable=self.pc_custom_hours, command=self._update_pc_custom_labels).pack(side="left", fill="x", expand=True, padx=8)

        m_row = ctk.CTkFrame(box, fg_color="transparent")
        m_row.pack(fill="x", pady=4)
        self.pc_m_label = ctk.CTkLabel(m_row, text=f"분: {self.pc_custom_minutes.get()} 분", font=get_font(13, "bold"), width=100, anchor="w")
        self.pc_m_label.pack(side="left")
        ctk.CTkSlider(m_row, from_=0, to=59, number_of_steps=59, variable=self.pc_custom_minutes, command=self._update_pc_custom_labels).pack(side="left", fill="x", expand=True, padx=8)

        self.pc_summary_lbl = ctk.CTkLabel(box, text="총 1시간 0분 후 실행됩니다.", font=get_font(14, "bold"), text_color="#60a5fa")
        self.pc_summary_lbl.pack(pady=(10, 0))
        self._update_pc_custom_labels()

    def _update_pc_custom_labels(self, _=None):
        h = self.pc_custom_hours.get()
        m = self.pc_custom_minutes.get()
        if hasattr(self, 'pc_h_label'):
            self.pc_h_label.configure(text=f"시간: {h} 시간")
            self.pc_m_label.configure(text=f"분: {m} 분")
            if h == 0 and m == 0:
                self.pc_summary_lbl.configure(text="0분은 예약할 수 없습니다 (최소 1분 이상).", text_color="#f87171")
            else:
                parts = []
                if h > 0: parts.append(f"{h}시간")
                if m > 0: parts.append(f"{m}분")
                self.pc_summary_lbl.configure(text=f"총 {' '.join(parts)} 후 실행됩니다.", text_color="#60a5fa")

    def _render_pc_clock_view(self):
        box = ctk.CTkFrame(self.pc_time_content, fg_color="transparent")
        box.pack(fill="x")

        day_row = ctk.CTkFrame(box, fg_color="transparent")
        day_row.pack(fill="x", pady=4)
        ctk.CTkLabel(day_row, text="날짜:", font=get_font(13, "bold"), width=60, anchor="w").pack(side="left")
        ctk.CTkRadioButton(day_row, text="오늘", value="today", variable=self.pc_target_day, font=get_font(13)).pack(side="left", padx=8)
        ctk.CTkRadioButton(day_row, text="내일", value="tomorrow", variable=self.pc_target_day, font=get_font(13)).pack(side="left", padx=8)

        time_row = ctk.CTkFrame(box, fg_color="transparent")
        time_row.pack(fill="x", pady=6)
        ctk.CTkLabel(time_row, text="시각:", font=get_font(13, "bold"), width=60, anchor="w").pack(side="left")

        now = datetime.datetime.now()
        hour_vals = [f"{i:02d}" for i in range(24)]
        min_vals = [f"{i:02d}" for i in range(0, 60, 5)]

        self.pc_hour_combo = ctk.CTkComboBox(time_row, values=hour_vals, width=80, font=get_font(13), state="readonly")
        self.pc_hour_combo.set(f"{(now.hour + 1) % 24:02d}")
        self.pc_hour_combo.pack(side="left", padx=(0, 6))
        ctk.CTkLabel(time_row, text="시", font=get_font(13)).pack(side="left", padx=(0, 10))

        self.pc_min_combo = ctk.CTkComboBox(time_row, values=min_vals, width=80, font=get_font(13), state="readonly")
        self.pc_min_combo.set("00")
        self.pc_min_combo.pack(side="left", padx=(0, 6))
        ctk.CTkLabel(time_row, text="분", font=get_font(13)).pack(side="left")

    # =========================================================================
    # 뷰 6: 회의/연수 알람
    # =========================================================================
    def _build_alarm_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=6)

        memo_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#222a3a", border_width=1, border_color="#0284c7")
        memo_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            memo_card, 
            text="📝 알람 메모 (회의명, 연수 내용 등):", 
            font=get_font(13, "bold"),
            text_color="#38bdf8"
        ).pack(anchor="w", padx=12, pady=(10, 6))

        self.alarm_memo_entry = ctk.CTkEntry(
            memo_card,
            placeholder_text="예: 3시 팀 주간 화상 회의 참석, 교원 직무 연수",
            font=get_font(13),
            height=38,
            corner_radius=8,
            fg_color="#0f172a",
            text_color="#ffffff"
        )
        self.alarm_memo_entry.pack(fill="x", padx=12, pady=(0, 12))

        sound_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#222a3a", border_width=1, border_color="#374151")
        sound_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            sound_card, 
            text="🎵 알람음 선택 & 미리듣기:", 
            font=get_font(13, "bold"),
            text_color="#38bdf8"
        ).pack(anchor="w", padx=12, pady=(10, 6))

        sound_row = ctk.CTkFrame(sound_card, fg_color="transparent")
        sound_row.pack(fill="x", padx=12, pady=(0, 12))

        sound_items = sound_manager.get_sound_list()
        self.alarm_sound_map = {name: sid for sid, name in sound_items}
        sound_names = [name for _, name in sound_items]

        self.alarm_sound_combo = ctk.CTkComboBox(
            sound_row,
            values=sound_names,
            font=get_font(12),
            height=36,
            state="readonly",
            command=self._on_alarm_sound_changed
        )
        self.alarm_sound_combo.set(sound_names[0])
        self.alarm_sound_combo.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            sound_row,
            text="🔊 미리듣기",
            font=get_font(12, "bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color="#ffffff",
            width=90,
            height=36,
            corner_radius=8,
            command=self._preview_alarm_sound
        ).pack(side="right")

        time_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#222a3a", border_width=1, border_color="#374151")
        time_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            time_card, 
            text="⏰ 알람 시간 설정:", 
            font=get_font(13, "bold"),
            text_color="#38bdf8"
        ).pack(anchor="w", padx=12, pady=(10, 6))

        self.alarm_mode_seg = ctk.CTkSegmentedButton(
            time_card,
            values=["빠른 시간", "특정 시각 지정"],
            font=get_font(12, "bold"),
            command=self._on_alarm_mode_changed
        )
        self.alarm_mode_seg.set("빠른 시간")
        self.alarm_mode_seg.pack(fill="x", padx=12, pady=(0, 10))

        self.alarm_time_content = ctk.CTkFrame(time_card, fg_color="transparent")
        self.alarm_time_content.pack(fill="x", padx=12, pady=(0, 12))

        self._render_alarm_quick_view()

    def _on_alarm_sound_changed(self, choice: str):
        sid = self.alarm_sound_map.get(choice, "chime")
        self.selected_sound_id.set(sid)

    def _preview_alarm_sound(self):
        choice = self.alarm_sound_combo.get()
        sid = self.alarm_sound_map.get(choice, "chime")
        sound_manager.preview_sound(sid)

    def _on_alarm_mode_changed(self, mode_str: str):
        for w in self.alarm_time_content.winfo_children():
            w.destroy()
        if mode_str == "빠른 시간":
            self.alarm_mode.set("quick")
            self._render_alarm_quick_view()
        elif mode_str == "특정 시각 지정":
            self.alarm_mode.set("clock")
            self._render_alarm_clock_view()

    def _render_alarm_quick_view(self):
        presets = [
            ("5분 후", 5), ("10분 후", 10), ("15분 후", 15), ("20분 후", 20),
            ("30분 후", 30), ("45분 후", 45), ("1시간 후", 60), ("2시간 후", 120)
        ]
        grid = ctk.CTkFrame(self.alarm_time_content, fg_color="transparent")
        grid.pack(fill="x")

        self.alarm_preset_btns = []
        for i, (label, mins) in enumerate(presets):
            row, col = i // 2, i % 2
            btn = ctk.CTkButton(
                grid,
                text=label,
                font=get_font(13, "bold"),
                height=38,
                corner_radius=8,
                fg_color="#0284c7" if mins == self.alarm_preset_minutes.get() else "#374151",
                hover_color="#0369a1",
                text_color="#ffffff",
                command=lambda m=mins: self._select_alarm_preset(m)
            )
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            self.alarm_preset_btns.append((btn, mins))
            grid.grid_columnconfigure(col, weight=1)

    def _select_alarm_preset(self, mins: int):
        self.alarm_preset_minutes.set(mins)
        for btn, m in self.alarm_preset_btns:
            if m == mins:
                btn.configure(fg_color="#0284c7", border_width=2, border_color="#38bdf8")
            else:
                btn.configure(fg_color="#374151", border_width=0)

    def _render_alarm_clock_view(self):
        box = ctk.CTkFrame(self.alarm_time_content, fg_color="transparent")
        box.pack(fill="x")

        day_row = ctk.CTkFrame(box, fg_color="transparent")
        day_row.pack(fill="x", pady=4)
        ctk.CTkLabel(day_row, text="날짜:", font=get_font(13, "bold"), width=60, anchor="w").pack(side="left")
        ctk.CTkRadioButton(day_row, text="오늘", value="today", variable=self.alarm_target_day, font=get_font(13)).pack(side="left", padx=8)
        ctk.CTkRadioButton(day_row, text="내일", value="tomorrow", variable=self.alarm_target_day, font=get_font(13)).pack(side="left", padx=8)

        time_row = ctk.CTkFrame(box, fg_color="transparent")
        time_row.pack(fill="x", pady=6)
        ctk.CTkLabel(time_row, text="시각:", font=get_font(13, "bold"), width=60, anchor="w").pack(side="left")

        now = datetime.datetime.now()
        hour_vals = [f"{i:02d}" for i in range(24)]
        min_vals = [f"{i:02d}" for i in range(0, 60, 5)]

        self.alarm_hour_combo = ctk.CTkComboBox(time_row, values=hour_vals, width=80, font=get_font(13), state="readonly")
        self.alarm_hour_combo.set(f"{(now.hour + 1) % 24:02d}")
        self.alarm_hour_combo.pack(side="left", padx=(0, 6))
        ctk.CTkLabel(time_row, text="시", font=get_font(13)).pack(side="left", padx=(0, 10))

        self.alarm_min_combo = ctk.CTkComboBox(time_row, values=min_vals, width=80, font=get_font(13), state="readonly")
        self.alarm_min_combo.set("00")
        self.alarm_min_combo.pack(side="left", padx=(0, 6))
        ctk.CTkLabel(time_row, text="분", font=get_font(13)).pack(side="left")

    # =========================================================================
    # 뷰 7: 엑셀 / 구글 시트 연동
    # =========================================================================
    def _build_sheet_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=6)

        excel_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#222a3a", border_width=1, border_color="#374151")
        excel_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(excel_card, text="📊 엑셀(.xlsx / .csv) 시간표 가져오기 / 내보내기", font=get_font(13, "bold"), text_color="#60a5fa").pack(anchor="w", padx=12, pady=(10, 6))

        ex_btns = ctk.CTkFrame(excel_card, fg_color="transparent")
        ex_btns.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            ex_btns,
            text="📤 내 시간표 엑셀로 내보내기 (.xlsx)",
            font=get_font(12, "bold"),
            fg_color="#059669",
            hover_color="#047857",
            height=34,
            command=self._export_excel_file
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            ex_btns,
            text="📥 엑셀/CSV 파일에서 불러오기",
            font=get_font(12, "bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=34,
            command=self._import_excel_file
        ).pack(side="left")

        gs_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#1e293b", border_width=1, border_color="#38bdf8")
        gs_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(gs_card, text="🌐 구글 스프레드시트 실시간 동기화", font=get_font(13, "bold"), text_color="#38bdf8").pack(anchor="w", padx=12, pady=(10, 6))

        gs_row = ctk.CTkFrame(gs_card, fg_color="transparent")
        gs_row.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(gs_row, text="웹 게시 CSV URL:", font=get_font(12, "bold"), width=110, anchor="w").pack(side="left")
        self.gs_url_entry = ctk.CTkEntry(
            gs_row,
            placeholder_text="https://docs.google.com/spreadsheets/.../pub?output=csv",
            font=get_font(12),
            height=32,
            fg_color="#0f172a"
        )
        saved_url = timetable_manager.settings.get("google_sheet_url", "")
        if saved_url:
            self.gs_url_entry.insert(0, saved_url)
        self.gs_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            gs_row,
            text="🔄 시트 동기화",
            font=get_font(12, "bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            width=90,
            height=32,
            command=self._sync_google_sheet
        ).pack(side="right")

        guide_box = ctk.CTkFrame(gs_card, fg_color="#0f172a", corner_radius=6)
        guide_box.pack(fill="x", padx=12, pady=(6, 12))
        ctk.CTkLabel(guide_box, text=sheet_sync_manager.GOOGLE_SHEET_GUIDE_TEXT, font=get_font(11), text_color="#cbd5e1", justify="left").pack(padx=10, pady=8)

    def _export_excel_file(self):
        default_name = f"학급시간표_{datetime.date.today().strftime('%Y%m%d')}.xlsx"
        fp = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")], initialfile=default_name)
        if fp:
            if sheet_sync_manager.export_to_excel(fp, timetable_manager.weekly_timetable, timetable_manager.periods):
                self._play_sound("success")
                self._show_simple_alert("내보내기 완료", f"시간표가 엑셀 파일로 저장되었습니다!\n경로: {fp}")
            else:
                self._show_simple_alert("오류", "엑셀 내보내기 실패")

    def _import_excel_file(self):
        fp = filedialog.askopenfilename(filetypes=[("Spreadsheet Files", "*.xlsx;*.csv")])
        if fp:
            ok, data, msg = sheet_sync_manager.import_from_excel_or_csv(fp)
            if ok and data:
                timetable_manager.save_weekly_timetable(data)
                self._play_sound("success")
                self._render_weekly_grid()
                self._render_today_items()
                self._show_simple_alert("가져오기 완료", "파일에서 시간표를 성공적으로 불러왔습니다!")
            else:
                self._show_simple_alert("가져오기 실패", msg)

    def _sync_google_sheet(self):
        url = self.gs_url_entry.get().strip()
        if not url:
            self._show_simple_alert("안내", "구글 시트 웹 게시 CSV 링크를 입력해주세요.")
            return

        timetable_manager.save_settings({"google_sheet_url": url})
        ok, data, msg = sheet_sync_manager.sync_from_google_sheet_csv(url)
        if ok and data:
            timetable_manager.save_weekly_timetable(data)
            self._play_sound("success")
            self._render_weekly_grid()
            self._render_today_items()
            self._show_simple_alert("동기화 성공", msg)
        else:
            self._show_simple_alert("동기화 실패", msg)

    # =========================================================================
    # 뷰 8: 화면 분할 도킹 & 위젯 모음
    # =========================================================================
    def _build_screen_layout_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=6)

        dock_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#222a3a", border_width=1, border_color="#38bdf8")
        dock_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(dock_card, text="🔲 원클릭 화면 분할 및 위치 도킹 (멀티태스킹 최적화)", font=get_font(13, "bold"), text_color="#38bdf8").pack(anchor="w", padx=12, pady=(10, 6))

        dock_row1 = ctk.CTkFrame(dock_card, fg_color="transparent")
        dock_row1.pack(fill="x", padx=12, pady=4)

        ctk.CTkButton(dock_row1, text="⬅️ 화면 좌측 50% 분할", font=get_font(12, "bold"), fg_color="#0284c7", hover_color="#0369a1", height=34, command=self._dock_left).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(dock_row1, text="➡️ 화면 우측 50% 분할", font=get_font(12, "bold"), fg_color="#0284c7", hover_color="#0369a1", height=34, command=self._dock_right).pack(side="right", fill="x", expand=True, padx=(4, 0))

        size_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#222a3a", border_width=1, border_color="#374151")
        size_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(size_card, text="📐 최적화 창 크기 프리셋", font=get_font(13, "bold"), text_color="#60a5fa").pack(anchor="w", padx=12, pady=(10, 6))

        sz_row = ctk.CTkFrame(size_card, fg_color="transparent")
        sz_row.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(sz_row, text="💻 표준 모드 (960x820)", font=get_font(11, "bold"), fg_color="#374151", hover_color="#4b5563", height=32, command=lambda: self._set_window_size(960, 820)).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(sz_row, text="📱 컴팩트 모드 (780x680)", font=get_font(11, "bold"), fg_color="#374151", hover_color="#4b5563", height=32, command=lambda: self._set_window_size(780, 680)).pack(side="left", fill="x", expand=True, padx=2)
        ctk.CTkButton(sz_row, text="🖥️ 와이드 모드 (1180x840)", font=get_font(11, "bold"), fg_color="#374151", hover_color="#4b5563", height=32, command=lambda: self._set_window_size(1180, 840)).pack(side="right", fill="x", expand=True, padx=(4, 0))

        # 미니 위젯 모음 카드
        widget_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#1e2230", border_width=1, border_color="#10b981")
        widget_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(widget_card, text="📌 편리한 상시 플로팅 미니 위젯 & 다양한 고정 위치", font=get_font(13, "bold"), text_color="#4ade80").pack(anchor="w", padx=12, pady=(10, 6))

        w_row = ctk.CTkFrame(widget_card, fg_color="transparent")
        w_row.pack(fill="x", padx=12, pady=(0, 6))

        ctk.CTkButton(w_row, text="📊 미니 정보바 열기", font=get_font(12, "bold"), fg_color="#10b981", hover_color="#059669", height=36, command=self._open_mini_ticker).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(w_row, text="📌 바탕화면 미니 시간표 위젯", font=get_font(12, "bold"), fg_color="#0284c7", hover_color="#0369a1", height=36, command=self._open_mini_widget).pack(side="right", fill="x", expand=True, padx=(4, 0))

        # 미니바 고정 위치 원클릭 설정 그리드
        dock_pos_frame = ctk.CTkFrame(widget_card, fg_color="#111827", corner_radius=8)
        dock_pos_frame.pack(fill="x", padx=12, pady=(4, 10))

        ctk.CTkLabel(dock_pos_frame, text="📍 미니바 원클릭 위치 고정:", font=get_font(11, "bold"), text_color="#38bdf8").pack(anchor="w", padx=8, pady=(6, 2))

        d_btns_1 = ctk.CTkFrame(dock_pos_frame, fg_color="transparent")
        d_btns_1.pack(fill="x", padx=8, pady=2)
        ctk.CTkButton(d_btns_1, text="⬇️ 작업표시줄 약간 위", font=get_font(11), height=26, fg_color="#334155", hover_color="#475569", command=lambda: self._set_mini_ticker_dock("bottom_dock")).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ctk.CTkButton(d_btns_1, text="⬆️ 화면 상단 중앙 (노치)", font=get_font(11), height=26, fg_color="#334155", hover_color="#475569", command=lambda: self._set_mini_ticker_dock("top_dock")).pack(side="right", fill="x", expand=True, padx=(2, 0))

        d_btns_2 = ctk.CTkFrame(dock_pos_frame, fg_color="transparent")
        d_btns_2.pack(fill="x", padx=8, pady=(2, 6))
        ctk.CTkButton(d_btns_2, text="⬅️ 모니터 좌측 사이드", font=get_font(11), height=26, fg_color="#334155", hover_color="#475569", command=lambda: self._set_mini_ticker_dock("left_side")).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ctk.CTkButton(d_btns_2, text="➡️ 모니터 우측 사이드", font=get_font(11), height=26, fg_color="#334155", hover_color="#475569", command=lambda: self._set_mini_ticker_dock("right_side")).pack(side="left", fill="x", expand=True, padx=2)
        ctk.CTkButton(d_btns_2, text="↘️ 우측 하단 트레이", font=get_font(11), height=26, fg_color="#334155", hover_color="#475569", command=lambda: self._set_mini_ticker_dock("bottom_right")).pack(side="right", fill="x", expand=True, padx=(2, 0))

        # 듀얼모니터 학생용 뷰어 카드
        dual_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#222a3a", border_width=1, border_color="#38bdf8")
        dual_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(dual_card, text="📺 듀얼 모니터 (학생용 화면2 / 교실 TV) 대형 스크린", font=get_font(13, "bold"), text_color="#38bdf8").pack(anchor="w", padx=12, pady=(10, 6))

        ctk.CTkButton(
            dual_card,
            text="🚀 학생용 대형 시간표/알림판 화면 열기 (화면2로 이동 가능)",
            font=get_font(13, "bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=36,
            command=self._open_student_display
        ).pack(fill="x", padx=12, pady=(0, 10))

    def _dock_left(self):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = sw // 2
        h = sh - 70
        self.geometry(f"{w}x{h}+0+0")

    def _dock_right(self):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = sw // 2
        h = sh - 70
        self.geometry(f"{w}x{h}+{w}+0")

    def _set_window_size(self, w: int, h: int):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = max(10, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    # =========================================================================
    # 뷰 9: 설정 & 테마 (카테고리별 체계적 관리)
    # =========================================================================
    # 뷰 9: 설정 & 테마 (카테고리별 체계적 관리)
    # =========================================================================
    def _build_settings_tab(self, parent):
        palette = theme_manager.get_theme()
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=6)

        # 1. 🚀 시작 프로그램 및 부팅 설정 카드
        boot_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color=palette["card_inner_bg"], border_width=1, border_color=palette["card_border"])
        boot_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(boot_card, text="🚀 1. Windows 시작 프로그램 & 부팅 설정", font=get_font(13, "bold"), text_color=palette["accent_blue"]).pack(anchor="w", padx=12, pady=(10, 6))

        bc_row1 = ctk.CTkFrame(boot_card, fg_color="transparent")
        bc_row1.pack(fill="x", padx=12, pady=4)

        self.autostart_switch = ctk.CTkSwitch(
            bc_row1,
            text="Windows 부팅 시 프로그램 자동 시작",
            font=get_font(12, "bold"),
            text_color=palette["text_main"],
            command=self._on_toggle_autostart
        )
        if autostart_manager.is_autostart_enabled():
            self.autostart_switch.select()
        self.autostart_switch.pack(side="left")

        bc_row2 = ctk.CTkFrame(boot_card, fg_color="transparent")
        bc_row2.pack(fill="x", padx=12, pady=(4, 10))

        self.auto_mini_switch = ctk.CTkSwitch(
            bc_row2,
            text="프로그램 실행 시 미니 정보 바 위젯 자동 띄우기",
            font=get_font(12),
            text_color=palette["text_main"],
            command=self._on_toggle_auto_mini_ticker
        )
        if timetable_manager.settings.get("auto_open_mini_ticker", True):
            self.auto_mini_switch.select()
        self.auto_mini_switch.pack(side="left")

        # 2. 📌 미니 정보 바 & 위젯 기본 위치 설정 카드
        dock_cfg_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color=palette["card_inner_bg"], border_width=1, border_color=palette["card_border"])
        dock_cfg_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(dock_cfg_card, text="📌 2. 미니 정보 바 & 위젯 화면 고정 위치 관리", font=get_font(13, "bold"), text_color=palette["accent_green"]).pack(anchor="w", padx=12, pady=(10, 6))

        dc_row1 = ctk.CTkFrame(dock_cfg_card, fg_color="transparent")
        dc_row1.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(dc_row1, text="기본 고정 위치:", font=get_font(12, "bold"), text_color=palette["text_main"], width=95, anchor="w").pack(side="left")
        self.dock_preset_combo = ctk.CTkComboBox(
            dc_row1,
            values=[
                "⬇️ 작업표시줄 약간 위 (Bottom Dock)",
                "⬆️ 화면 상단 중앙 (Top Notch)",
                "⬅️ 모니터 좌측 사이드 (Left Side)",
                "➡️ 모니터 우측 사이드 (Right Side)",
                "↘️ 우측 하단 트레이 위 (Bottom Right)"
            ],
            font=get_font(12),
            width=230,
            state="readonly",
            fg_color=palette["card_bg"],
            text_color=palette["text_main"],
            command=self._on_settings_dock_changed
        )
        self.dock_preset_combo.set("⬇️ 작업표시줄 약간 위 (Bottom Dock)")
        self.dock_preset_combo.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            dc_row1,
            text="📊 미니바 열기/위치 적용",
            font=get_font(11, "bold"),
            fg_color=palette["accent_green"],
            hover_color="#059669",
            height=28,
            command=lambda: self._set_mini_ticker_dock(self._get_selected_dock_key())
        ).pack(side="left")

        # 3. 🔔 수업 및 회의 알람 기본값 설정 카드
        alarm_cfg_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color=palette["card_inner_bg"], border_width=1, border_color=palette["card_border"])
        alarm_cfg_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(alarm_cfg_card, text="🔔 3. 수업 및 회의 알람 기본 설정", font=get_font(13, "bold"), text_color=palette["accent_blue"]).pack(anchor="w", padx=12, pady=(10, 6))

        ac_row1 = ctk.CTkFrame(alarm_cfg_card, fg_color="transparent")
        ac_row1.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(ac_row1, text="수업 시작 전 알람:", font=get_font(12, "bold"), text_color=palette["text_main"], width=110, anchor="w").pack(side="left")
        self.alarm_lead_combo = ctk.CTkComboBox(
            ac_row1,
            values=["3분 전", "5분 전 (기본)", "10분 전", "15분 전"],
            font=get_font(12),
            width=120,
            state="readonly",
            fg_color=palette["card_bg"],
            text_color=palette["text_main"],
            command=self._on_alarm_lead_changed
        )
        curr_lead = timetable_manager.settings.get("alarm_lead_minutes", 5)
        lead_map = {3: "3분 전", 5: "5분 전 (기본)", 10: "10분 전", 15: "15분 전"}
        self.alarm_lead_combo.set(lead_map.get(curr_lead, "5분 전 (기본)"))
        self.alarm_lead_combo.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(ac_row1, text="기본 알람음:", font=get_font(12, "bold"), text_color=palette["text_main"], width=75, anchor="w").pack(side="left")
        sound_items = sound_manager.get_sound_list()
        self.settings_sound_names = [name for _, name in sound_items]
        self.settings_sound_map = {name: sid for sid, name in sound_items}
        self.settings_sound_combo = ctk.CTkComboBox(
            ac_row1,
            values=self.settings_sound_names,
            font=get_font(12),
            width=130,
            state="readonly",
            fg_color=palette["card_bg"],
            text_color=palette["text_main"],
            command=self._on_settings_sound_changed
        )
        saved_sound_id = timetable_manager.settings.get("alarm_sound_id", "chime")
        inv_s_map = {sid: name for sid, name in sound_items}
        self.settings_sound_combo.set(inv_s_map.get(saved_sound_id, self.settings_sound_names[0]))
        self.settings_sound_combo.pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            ac_row1,
            text="🔊",
            width=30,
            height=28,
            font=get_font(12),
            fg_color=palette["sidebar_btn_hover"],
            hover_color=palette["accent_blue"],
            text_color=palette["text_main"],
            command=lambda: sound_manager.preview_sound(self.settings_sound_map.get(self.settings_sound_combo.get(), "chime"))
        ).pack(side="left")

        # 4. 🎨 화면 테마 및 창 투명도 설정 카드
        theme_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color=palette["card_inner_bg"], border_width=1, border_color=palette["card_border"])
        theme_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(theme_card, text="🎨 4. 화면 테마 및 창 투명도 설정", font=get_font(13, "bold"), text_color=palette["accent_purple"]).pack(anchor="w", padx=12, pady=(10, 6))

        t_row = ctk.CTkFrame(theme_card, fg_color="transparent")
        t_row.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(t_row, text="화면 테마:", font=get_font(12, "bold"), text_color=palette["text_main"], width=70, anchor="w").pack(side="left")
        self.theme_combo = ctk.CTkComboBox(
            t_row,
            values=["🌾 따뜻한 베이지 (Warm Beige)", "🌙 다크 모드 (Dark Indigo)", "☀️ 모던 라이트 (Clean Light)"],
            font=get_font(12),
            width=210,
            height=28,
            state="readonly",
            fg_color=palette["card_bg"],
            text_color=palette["text_main"],
            command=self._on_theme_changed
        )
        curr_th = timetable_manager.settings.get("theme_mode", "Beige")
        th_map = {"Beige": "🌾 따뜻한 베이지 (Warm Beige)", "Dark": "🌙 다크 모드 (Dark Indigo)", "Light": "☀️ 모던 라이트 (Clean Light)"}
        self.theme_combo.set(th_map.get(curr_th, "🌾 따뜻한 베이지 (Warm Beige)"))
        self.theme_combo.pack(side="left", padx=(0, 16))

        alpha_row = ctk.CTkFrame(theme_card, fg_color="transparent")
        alpha_row.pack(fill="x", padx=12, pady=(4, 12))

        ctk.CTkLabel(alpha_row, text="창 투명도:", font=get_font(12, "bold"), text_color=palette["text_main"], width=70, anchor="w").pack(side="left")
        self.alpha_slider = ctk.CTkSlider(alpha_row, from_=0.6, to=1.0, number_of_steps=40, command=self._on_alpha_changed)
        self.alpha_slider.set(timetable_manager.settings.get("window_alpha", 1.0))
        self.alpha_slider.pack(side="left", fill="x", expand=True, padx=8)

        # 5. 🏫 나이스 Open API 키 및 계정 설정 카드 (선택사항)
        neis_key_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color=palette["card_inner_bg"], border_width=1, border_color=palette["card_border"])
        neis_key_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(neis_key_card, text="🏫 5. 나이스 Open API 인증키 설정 (선택사항)", font=get_font(13, "bold"), text_color=palette["accent_blue"]).pack(anchor="w", padx=12, pady=(10, 6))

        nk_row = ctk.CTkFrame(neis_key_card, fg_color="transparent")
        nk_row.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(nk_row, text="개인 인증키(KEY):", font=get_font(11, "bold"), text_color=palette["text_main"], width=110, anchor="w").pack(side="left")
        self.neis_api_key_entry = ctk.CTkEntry(
            nk_row,
            placeholder_text="기본 샘플키 사용 중 (대용량 조회 시 교육부 개방포털 무료 인증키 입력)",
            font=get_font(11),
            height=30,
            fg_color=palette["card_bg"],
            text_color=palette["text_main"]
        )
        saved_key = neis_client.config.get("api_key", "")
        if saved_key:
            self.neis_api_key_entry.insert(0, saved_key)
        self.neis_api_key_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            nk_row,
            text="💾 키 저장",
            font=get_font(11, "bold"),
            fg_color=palette["accent_green"],
            hover_color="#059669",
            width=70,
            height=30,
            command=self._save_neis_api_key
        ).pack(side="right")

        nk_info = "• 인증키를 비워두셔도 전국 17개 교육청의 모든 학교 및 시간표 조회가 기본 작동합니다.\n• 공식 교육부 Open API 포털(open.neis.go.kr)에서 발급받은 개인 키가 있으시면 입력 후 저장하세요."
        ctk.CTkLabel(neis_key_card, text=nk_info, font=get_font(10), text_color=palette["text_sub"], justify="left", anchor="w").pack(fill="x", padx=12, pady=(2, 10))

        # 6. 🧹 쾌적한 PC & 바탕화면 스마트 정리 센터 카드
        cleaner_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color=palette["card_inner_bg"], border_width=1, border_color=palette["card_border"])
        cleaner_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(cleaner_card, text="🧹 6. 쾌적한 PC & 바탕화면 스마트 정리 센터", font=get_font(13, "bold"), text_color=palette["accent_green"]).pack(anchor="w", padx=12, pady=(10, 4))
        
        # 1행: 바탕화면 정리 & 되돌리기
        cl_row1 = ctk.CTkFrame(cleaner_card, fg_color="transparent")
        cl_row1.pack(fill="x", padx=12, pady=3)

        ctk.CTkButton(
            cl_row1,
            text="🧹 바탕화면 1초 자동 분류 정리",
            font=get_font(11, "bold"),
            fg_color=palette["accent_blue"],
            hover_color="#0369a1",
            height=32,
            command=self._organize_desktop_action
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            cl_row1,
            text="↩ 직전 정리 되돌리기 (Undo)",
            font=get_font(11, "bold"),
            fg_color=palette["sidebar_btn_hover"],
            hover_color=palette["accent_blue"],
            text_color=palette["text_main"],
            height=32,
            command=self._undo_desktop_action
        ).pack(side="left", padx=(0, 6))

        # 2행: 수업용 아이콘 숨기기 & 학급 폴더 생성 & 임시파일 다이어트
        cl_row2 = ctk.CTkFrame(cleaner_card, fg_color="transparent")
        cl_row2.pack(fill="x", padx=12, pady=3)

        ctk.CTkButton(
            cl_row2,
            text="🙈 수업용 아이콘 숨김/표시 (Zen)",
            font=get_font(11, "bold"),
            fg_color=palette["accent_purple"],
            hover_color="#7c3aed",
            height=32,
            command=self._toggle_desktop_icons_action
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            cl_row2,
            text="🗂️ 새 학기 학급 폴더 6종 자동생성",
            font=get_font(11, "bold"),
            fg_color=palette["accent_green"],
            hover_color="#059669",
            height=32,
            command=self._create_class_folder_action
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            cl_row2,
            text="🗑️ 임시파일(Temp) 청소",
            font=get_font(11, "bold"),
            fg_color=palette["sidebar_btn_hover"],
            hover_color=palette["accent_blue"],
            text_color=palette["text_main"],
            height=32,
            command=self._clean_temp_files_action
        ).pack(side="left")

        self.cleaner_status_lbl = ctk.CTkLabel(
            cleaner_card,
            text="• 흩어진 문서/사진/동영상/압축파일을 성격별 폴더로 자동 분류하여 교실 TV 및 모니터를 쾌적하게 유지합니다.",
            font=get_font(10),
            text_color=palette["text_sub"],
            justify="left",
            anchor="w"
        )
        self.cleaner_status_lbl.pack(fill="x", padx=12, pady=(4, 10))

        # 7. 🚀 놀티쳐 최신 버전 & 1초 스마트 자동 업데이트 카드
        updater_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color=palette["card_inner_bg"], border_width=1, border_color=palette["card_border"])
        updater_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(updater_card, text="🚀 7. 놀티쳐 최신 버전 & 1초 스마트 자동 업데이트", font=get_font(13, "bold"), text_color=palette["accent_blue"]).pack(anchor="w", padx=12, pady=(10, 4))

        up_row = ctk.CTkFrame(updater_card, fg_color="transparent")
        up_row.pack(fill="x", padx=12, pady=4)

        self.updater_status_lbl = ctk.CTkLabel(
            up_row,
            text=f"현재 버전: v{APP_VERSION} (최신 공식 릴리스)",
            font=get_font(12, "bold"),
            text_color=palette["accent_green"]
        )
        self.updater_status_lbl.pack(side="left")

        btns_box = ctk.CTkFrame(up_row, fg_color="transparent")
        btns_box.pack(side="right")

        ctk.CTkButton(
            btns_box,
            text="🌐 GitHub 저장소",
            font=get_font(10, "bold"),
            fg_color=palette["sidebar_btn_hover"],
            hover_color=palette["accent_blue"],
            text_color=palette["text_main"],
            height=30,
            command=lambda: webbrowser.open("https://github.com/LUCKYBRIDGE/knolteacher")
        ).pack(side="left", padx=(0, 6))

        self.update_check_btn = ctk.CTkButton(
            btns_box,
            text="🔄 최신 업데이트 확인",
            font=get_font(11, "bold"),
            fg_color=palette["accent_blue"],
            hover_color="#0369a1",
            text_color="#ffffff",
            height=30,
            command=self._check_and_run_github_update
        )
        self.update_check_btn.pack(side="left")

        up_info = "• GitHub(LUCKYBRIDGE/knol-teacher-desk) 릴리스와 연동되어 웹 브라우저 다운로드 없이 앱 내부에서 1초 만에 최신 버전으로 직접 덮어쓰기 업데이트됩니다.\n• 새 버전을 받더라도 선생님께서 설정하신 모든 시간표, 학교, 바로가기, 테마는 영구 보존됩니다."
        ctk.CTkLabel(updater_card, text=up_info, font=get_font(10), text_color=palette["text_sub"], justify="left", anchor="w").pack(fill="x", padx=12, pady=(2, 10))

        # 8. 📁 로컬 데이터 보관 & 다른 PC 이전(백업) 안내
        data_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color=palette["card_inner_bg"], border_width=1, border_color=palette["card_border"])
        data_card.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(data_card, text="📁 8. 로컬 데이터 보관 & 다른 PC 이전(백업) 안내", font=get_font(13, "bold"), text_color=palette["accent"]).pack(anchor="w", padx=12, pady=(10, 4))

        cfg_dir = get_config_dir()
        d_row1 = ctk.CTkFrame(data_card, fg_color="transparent")
        d_row1.pack(fill="x", padx=12, pady=(2, 4))

        ctk.CTkLabel(d_row1, text="• 실제 데이터 저장 폴더:", font=get_font(11, "bold"), text_color=palette["text_main"]).pack(side="left", padx=(0, 6))

        path_box = ctk.CTkEntry(d_row1, font=ctk.CTkFont(family="Consolas", size=10), height=26)
        path_box.insert(0, cfg_dir)
        path_box.configure(state="readonly")
        path_box.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            d_row1,
            text="📂 저장 폴더 열기",
            font=get_font(10, "bold"),
            fg_color=palette["accent"],
            hover_color=palette["accent_hover"],
            text_color="#ffffff",
            height=26,
            command=self._open_data_folder
        ).pack(side="right")

        d_info = (
            "• 100% 캐시 정리 안전: 본 폴더는 윈도우 사용자 영구 프로필 루트에 위치하므로, "
            "알약/V3/고클린/윈도우 디스크 정리 등 PC 최적화 도구를 실행해도 절대 삭제되지 않습니다.\n"
            "• 다른 컴퓨터에서 그대로 쓰고 싶을 때: 위 폴더를 USB에 복사하여 새 컴퓨터의 사용자 폴더(C:\\Users\\선생님계정\\)에 그대로 붙여넣으시면, "
            "선생님께서 입력하신 시간표·나이스 학교 설정·학생 명렬표·사이트 북마크가 1초 만에 100% 완벽 복원됩니다."
        )
        ctk.CTkLabel(data_card, text=d_info, font=get_font(10), text_color=palette["text_sub"], justify="left", anchor="w").pack(fill="x", padx=12, pady=(2, 10))

        # 9. ℹ️ 프로그램 정보 & 저작권
        info_card = ctk.CTkFrame(scroll, corner_radius=10, fg_color=palette["card_inner_bg"], border_width=1, border_color=palette["card_border"])
        info_card.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(info_card, text="ℹ️ 9. 프로그램 정보 & 저작권", font=get_font(13, "bold"), text_color=palette["text_main"]).pack(anchor="w", padx=12, pady=(10, 4))
        info_str = (
            f"• 프로그램명: 놀티쳐 (KnolTeacher v{APP_VERSION})\n"
            "• 개발 및 저작권: Copyright 2026. 교사 서정완. All rights reserved.\n"
            "• 브랜드: Knol (Knowledge & Play - 즐거운 배움과 스마트 교실 생태계)\n"
            "• 기능: 4세대 나이스 학생번호 기준 안전 자동입력, 전국 17개 교육청 전역 학교 시간표 연동,\n"
            "        놀티쳐 보드(교실 TV), 판서 & 플로팅 퀵바, 올웨이즈온 미니바/급식 위젯, 수업 알람, PC 전원 예약."
        )
        ctk.CTkLabel(info_card, text=info_str, font=get_font(11), text_color="#cbd5e1", justify="left", anchor="w").pack(fill="x", padx=12, pady=(2, 10))

    def _organize_desktop_action(self):
        ans = messagebox.askyesno(
            "바탕화면 자동 분류 정리",
            "바탕화면에 흩어진 파일들을 [문서·수업자료], [사진·이미지], [동영상], [압축·설치] 폴더로 자동 분류하시겠습니까?\n\n(실행 파일 및 바로가기는 안전하게 제외되며, 원클릭으로 되돌릴 수 있습니다.)"
        )
        if ans:
            ok, msg, count = desktop_cleaner.organize_desktop()
            if ok:
                self.cleaner_status_lbl.configure(text=f"✓ {msg}", text_color="#4ade80")
                messagebox.showinfo("정리 완료", msg)
            else:
                self.cleaner_status_lbl.configure(text=f"✗ {msg}", text_color="#f87171")
                messagebox.showerror("오류", msg)

    def _undo_desktop_action(self):
        ok, msg, count = desktop_cleaner.undo_organize()
        if ok:
            self.cleaner_status_lbl.configure(text=f"✓ {msg}", text_color="#4ade80")
            messagebox.showinfo("되돌리기 완료", msg)
        else:
            self.cleaner_status_lbl.configure(text=f"ℹ {msg}", text_color="#f59e0b")
            messagebox.showinfo("되돌리기 안내", msg)

    def _open_data_folder(self):
        import os, subprocess
        from tkinter import messagebox
        from src.config_utils import get_config_dir
        cfg_dir = get_config_dir()
        if os.path.exists(cfg_dir):
            try:
                if os.name == "nt":
                    os.startfile(cfg_dir)
                else:
                    subprocess.run(["xdg-open", cfg_dir])
            except Exception:
                messagebox.showinfo("데이터 저장 폴더", f"실제 저장 폴더 경로:\n{cfg_dir}")
        else:
            messagebox.showinfo("데이터 저장 폴더", f"실제 저장 폴더 경로:\n{cfg_dir}")

    def _toggle_desktop_icons_action(self):
        ok, is_vis, msg = desktop_cleaner.toggle_desktop_icons()
        if ok:
            st_text = "바탕화면 아이콘이 표시 중입니다." if is_vis else "수업 모드: 바탕화면 아이콘이 깔끔하게 숨겨졌습니다."
            self.cleaner_status_lbl.configure(text=f"✓ {st_text}", text_color="#a78bfa")
            messagebox.showinfo("수업용 아이콘 제어", msg)
        else:
            messagebox.showerror("오류", msg)

    def _create_class_folder_action(self):
        ans = messagebox.askyesno(
            "새 학기 표준 폴더 생성",
            "바탕화면에 새 학기 교사용 표준 폴더 6개\n(학급경영, 수업자료, 평가및나이스, 상담, 공문, 사진영상)를 생성하시겠습니까?"
        )
        if ans:
            ok, msg = desktop_cleaner.create_class_folder_kit()
            if ok:
                self.cleaner_status_lbl.configure(text=f"✓ {msg}", text_color="#4ade80")
                messagebox.showinfo("생성 완료", msg)
            else:
                messagebox.showerror("오류", msg)

    def _clean_temp_files_action(self):
        ans = messagebox.askyesno(
            "임시파일 청소",
            "오래된 시스템 임시파일(Temp)을 삭제하여 PC 저장 공간을 확보하시겠습니까?"
        )
        if ans:
            ok, msg, count, freed_mb = desktop_cleaner.clean_temp_and_downloads()
            self.cleaner_status_lbl.configure(text=f"✓ {msg}", text_color="#4ade80")
            messagebox.showinfo("청소 완료", msg)

    def _check_and_run_github_update(self):
        self.update_check_btn.configure(state="disabled", text="⏳ 확인 중...")
        self.updater_status_lbl.configure(text="GitHub 최신 릴리스 확인 중...", text_color="#38bdf8")

        def _bg_check():
            has_update, latest_ver, download_url, notes, html_url = github_updater.check_latest_release()
            
            def _ui_update():
                self.update_check_btn.configure(state="normal", text="🔄 최신 업데이트 확인")
                if has_update and download_url:
                    self.updater_status_lbl.configure(text=f"🎉 새 버전 발견: v{latest_ver}", text_color="#f59e0b")
                    ans = messagebox.askyesno(
                        "놀티쳐 새 버전 업데이트",
                        f"새로운 버전(v{latest_ver})이 출시되었습니다!\n\n"
                        f"[업데이트 주요 내용]\n{notes[:200]}\n\n"
                        f"지금 바로 1초 자동 업데이트를 적용하시겠습니까?\n"
                        f"(기존 설정은 100% 안전하게 유지됩니다)"
                    )
                    if ans:
                        self._start_in_app_update(download_url)
                else:
                    self.updater_status_lbl.configure(text=f"현재 버전: v{APP_VERSION} (최신 상태)", text_color="#4ade80")
                    self._show_simple_alert("업데이트 확인", f"현재 최신 버전(v{APP_VERSION})을 사용하고 계십니다.\n추가 업데이트가 없습니다.")

            self.after(0, _ui_update)

        threading.Thread(target=_bg_check, daemon=True).start()

    def _start_in_app_update(self, download_url: str):
        self.update_check_btn.configure(state="disabled", text="⬇️ 다운로드 중...")
        
        def _on_prog(prog: float, msg: str):
            def _set_prog():
                self.updater_status_lbl.configure(text=msg, text_color="#38bdf8")
            self.after(0, _set_prog)

        def _on_fin(ok: bool, msg: str):
            def _set_fin():
                self.update_check_btn.configure(state="normal", text="🔄 최신 업데이트 확인")
                if not ok:
                    self._show_simple_alert("업데이트 안내", msg)
            self.after(0, _set_fin)

        github_updater.apply_update_in_background(download_url, on_progress=_on_prog, on_finish=_on_fin)

    def _save_neis_api_key(self):
        k = self.neis_api_key_entry.get().strip()
        neis_client.save_config({"api_key": k})
        self._play_sound("success")
        msg = "개인 나이스 Open API 인증키가 저장되었습니다!" if k else "기본 샘플키 모드로 설정되었습니다."
        self._show_simple_alert("키 저장 완료", msg)

    def _on_toggle_autostart(self):
        is_enable = self.autostart_switch.get() == 1
        ok, msg = autostart_manager.set_autostart(is_enable)
        self._play_sound("success" if ok else "warning")
        self._show_simple_alert("시작 프로그램 설정", msg)

    def _on_toggle_auto_mini_ticker(self):
        is_on = self.auto_mini_switch.get() == 1
        timetable_manager.save_settings({"auto_open_mini_ticker": is_on})

    def _get_selected_dock_key(self) -> str:
        val = self.dock_preset_combo.get()
        if "Top Notch" in val or "상단" in val: return "top_dock"
        elif "좌측" in val or "Left" in val: return "left_side"
        elif "우측 사이드" in val or "Right Side" in val: return "right_side"
        elif "트레이" in val or "Bottom Right" in val: return "bottom_right"
        return "bottom_dock"

    def _on_settings_dock_changed(self, choice: str):
        key = self._get_selected_dock_key()
        self._set_mini_ticker_dock(key)

    def _on_alarm_lead_changed(self, choice: str):
        import re
        m = re.search(r'(\d+)', choice)
        mins = int(m.group(1)) if m else 5
        timetable_manager.save_settings({"alarm_lead_minutes": mins})
        
        if hasattr(self, "batch_alarm_btn") and self.batch_alarm_btn.winfo_exists():
            self.batch_alarm_btn.configure(text=f"🔔  {mins}분 전 일괄 알람")
        if hasattr(self, "alarm_lead_combo") and self.alarm_lead_combo.winfo_exists():
            self.alarm_lead_combo.set(f"{mins}분 전")
        if hasattr(self, "top_alarm_lead_combo") and self.top_alarm_lead_combo.winfo_exists():
            self.top_alarm_lead_combo.set(f"{mins}분 전")
        
        if hasattr(self, "_render_today_items"):
            self._render_today_items()

    def _on_settings_sound_changed(self, choice: str):
        sid = self.settings_sound_map.get(choice, "chime")
        timetable_manager.save_settings({"alarm_sound_id": sid})

    def _open_student_display(self):
        if self.student_window and self.student_window.winfo_exists():
            self.student_window.lift()
            self.student_window.focus_force()
        else:
            self.student_window = StudentDisplayWindow(self)

    def _on_theme_changed(self, choice: str):
        if "베이지" in choice or "Beige" in choice:
            mode_val = "Beige"
        elif "다크" in choice or "Dark" in choice:
            mode_val = "Dark"
        else:
            mode_val = "Light"
        self._apply_theme_mode(mode_val)

    def _on_alpha_changed(self, val: float):
        try:
            self.attributes("-alpha", val)
            timetable_manager.save_settings({"window_alpha": val})
            pct_str = f"{int(val * 100)}%"

            if hasattr(self, "top_alpha_lbl") and self.top_alpha_lbl.winfo_exists():
                self.top_alpha_lbl.configure(text=f"👁️ 투명도 {pct_str}")
            if hasattr(self, "top_alpha_slider") and self.top_alpha_slider.winfo_exists() and abs(self.top_alpha_slider.get() - val) > 0.01:
                self.top_alpha_slider.set(val)

            if hasattr(self, "sidebar_alpha_lbl") and self.sidebar_alpha_lbl.winfo_exists():
                self.sidebar_alpha_lbl.configure(text=pct_str)
            if hasattr(self, "sidebar_alpha_slider") and self.sidebar_alpha_slider.winfo_exists() and abs(self.sidebar_alpha_slider.get() - val) > 0.01:
                self.sidebar_alpha_slider.set(val)

            if hasattr(self, "alpha_slider") and self.alpha_slider.winfo_exists() and abs(self.alpha_slider.get() - val) > 0.01:
                self.alpha_slider.set(val)
        except Exception:
            pass

    # =========================================================================
    # 뷰 10: 즉시 실행
    # =========================================================================
    def _build_instant_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=6, pady=6)

        card = ctk.CTkFrame(scroll, corner_radius=10, fg_color="#222a3a", border_width=1, border_color="#ef4444")
        card.pack(fill="x", pady=6)

        ctk.CTkLabel(
            card, 
            text="⚠️ 즉시 실행 작업 (클릭 시 확인 팝업 후 즉시 작동):", 
            font=get_font(13, "bold"),
            text_color="#fca5a5"
        ).pack(anchor="w", padx=12, pady=(12, 10))

        ctk.CTkButton(
            card,
            text="🛑 지금 즉시 컴퓨터 종료",
            font=get_font(14, "bold"),
            height=44,
            corner_radius=8,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            text_color="#ffffff",
            command=lambda: self._confirm_immediate_action("shutdown")
        ).pack(fill="x", padx=12, pady=5)

        ctk.CTkButton(
            card,
            text="🔄 지금 즉시 다시 시작 (재부팅)",
            font=get_font(14, "bold"),
            height=44,
            corner_radius=8,
            fg_color="#d97706",
            hover_color="#b45309",
            text_color="#ffffff",
            command=lambda: self._confirm_immediate_action("restart")
        ).pack(fill="x", padx=12, pady=5)

        ctk.CTkButton(
            card,
            text="🌙 지금 즉시 절전 모드",
            font=get_font(14, "bold"),
            height=44,
            corner_radius=8,
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            text_color="#ffffff",
            command=lambda: self._confirm_immediate_action("sleep")
        ).pack(fill="x", padx=12, pady=(5, 14))

    def _execute_schedule_with_conflict_check(
        self,
        action_type: str,
        seconds: int = 0,
        target_dt: Optional[datetime.datetime] = None,
        memo: str = ""
    ):
        ok, msg = self.manager.schedule_action(
            action_type=action_type,
            seconds=seconds,
            target_datetime=target_dt,
            memo=memo
        )
        if not ok and msg.startswith("CONFLICT:"):
            parts = msg.split(":")
            c_id = parts[1]
            c_name = parts[2]
            c_time = parts[3]
            act_name = SchedulerManager._get_action_name(action_type)

            from tkinter import messagebox
            ans = messagebox.askyesno(
                "⚠️ 예약 일정 충돌 감지",
                f"이미 [{c_time}]에 [{c_name}] 예약이 등록되어 있습니다.\n\n"
                f"새로 등록하려는 [{act_name}] 작업과 동시에 실행할 수 없습니다.\n\n"
                f"기존 충돌 예약을 취소하고 새로운 [{act_name}] 예약으로 교체하시겠습니까?"
            )
            if ans:
                self.manager.cancel_schedule_by_id(c_id)
                ok2, msg2 = self.manager.schedule_action(
                    action_type=action_type,
                    seconds=seconds,
                    target_datetime=target_dt,
                    memo=memo,
                    force=True
                )
                if ok2:
                    self._play_sound("success")
                    messagebox.showinfo("예약 교체 완료", msg2)
            return

        from tkinter import messagebox
        if ok:
            self._play_sound("success")
            messagebox.showinfo("예약 등록 완료", msg)
        else:
            messagebox.showwarning("예약 알림", msg)

    def _quick_schedule_pc(self, mins: int):
        action_type = self.pc_action.get()
        action_name = SchedulerManager._get_action_name(action_type)
        target_sec = mins * 60
        target_dt = datetime.datetime.now() + datetime.timedelta(seconds=target_sec)

        dialog = ModernConfirmDialog(
            self,
            title="빠른 예약 확인",
            message=f"[{action_name}] 작업을 {mins}분 후 ({target_dt.strftime('%H:%M:%S')})에 실행하시겠습니까?",
            action_text="예약 실행",
            is_danger=False
        )
        self.wait_window(dialog)

        if dialog.result:
            self._execute_schedule_with_conflict_check(action_type=action_type, seconds=target_sec)

    def _on_custom_time_schedule_submit(self):
        from tkinter import messagebox
        try:
            h_text = self.custom_hour_entry.get().strip() or "0"
            m_text = self.custom_min_entry.get().strip() or "0"
            h = int(h_text)
            m = int(m_text)
            total_sec = (h * 3600) + (m * 60)
            if total_sec <= 0:
                messagebox.showwarning("입력 오류", "예약 시간은 최소 1분 이상이어야 합니다.")
                return

            action_type = self.pc_action.get()
            memo = self.custom_memo_entry.get().strip()
            self._execute_schedule_with_conflict_check(action_type=action_type, seconds=total_sec, memo=memo)
        except ValueError:
            messagebox.showerror("입력 오류", "시간과 분은 숫자만 입력해주세요.")

    def _snap_window(self, mode: str):
        """화면 분할 최적화 및 창 위치 스냅 실제 작동 로직"""
        try:
            if self.state() == "zoomed":
                self.state("normal")
                self.update_idletasks()

            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            work_h = screen_h - 48  # 작업표시줄 높이 보정

            if mode == "left_half":
                w = screen_w // 2
                h = work_h
                x = 0
                y = 0
            elif mode == "right_half":
                w = screen_w // 2
                h = work_h
                x = screen_w // 2
                y = 0
            elif mode == "left_third":
                w = max(860, screen_w // 3)
                h = work_h
                x = 0
                y = 0
            elif mode == "center_opt":
                w = min(1180, screen_w - 40)
                h = min(840, work_h - 20)
                x = (screen_w - w) // 2
                y = (work_h - h) // 2
            elif mode == "maximize":
                self.state("zoomed")
                return
            else:
                return

            self.geometry(f"{w}x{h}+{x}+{y}")
            self.lift()
            self.focus_force()
        except Exception as e:
            print(f"[UI] Error snapping window: {e}")

    def _cancel_schedule(self):
        if not self.manager.is_scheduled and not self.manager.schedules:
            self._show_simple_alert("안내", "현재 진행 중인 예약이 없습니다.")
            return
        self._confirm_cancel_schedule()

    def _on_schedule_clicked(self):
        current_tab = getattr(self, "current_view_key", "today")

        if current_tab == "instant":
            self._show_simple_alert("안내", "'즉시 실행' 화면 내의 개별 버튼을 눌러주세요.")
            return

        if current_tab not in ["pc_power", "alarm_memo"]:
            self._show_simple_alert("안내", "[컴퓨터 예약/종료] 또는 [회의/연수 알람] 메뉴에서 시간을 설정한 후 예약해주세요.")
            return

        target_seconds = 0
        desc_str = ""
        action_type = "shutdown"
        memo_text = ""
        sound_id = "chime"
        sound_choice = ""

        if current_tab == "pc_power":
            action_type = self.pc_action.get()
            mode = self.pc_mode.get()

            if mode == "quick":
                mins = self.pc_preset_minutes.get()
                target_seconds = mins * 60
                desc_str = f"{mins}분 후"
            elif mode == "custom":
                h = self.pc_custom_hours.get()
                m = self.pc_custom_minutes.get()
                target_seconds = (h * 3600) + (m * 60)
                if target_seconds <= 0:
                    self._show_simple_alert("오류", "시간을 1분 이상으로 설정해주세요.")
                    return
                parts = []
                if h > 0: parts.append(f"{h}시간")
                if m > 0: parts.append(f"{m}분")
                desc_str = f"{' '.join(parts)} 후"
            elif mode == "clock":
                target_h = int(self.pc_hour_combo.get())
                target_m = int(self.pc_min_combo.get())
                is_tomorrow = self.pc_target_day.get() == "tomorrow"
                now = datetime.datetime.now()
                target_dt = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
                if is_tomorrow or target_dt <= now:
                    target_dt += datetime.timedelta(days=1)
                target_seconds = int((target_dt - now).total_seconds())
                desc_str = f"{target_dt.strftime('%m월 %d일 %H:%M')}"

        elif current_tab == "alarm_memo":
            action_type = "alarm"
            memo_text = self.alarm_memo_entry.get().strip()
            sound_choice = self.alarm_sound_combo.get()
            sound_id = self.alarm_sound_map.get(sound_choice, "chime")
            mode = self.alarm_mode.get()

            if mode == "quick":
                mins = self.alarm_preset_minutes.get()
                target_seconds = mins * 60
                desc_str = f"{mins}분 후"
            elif mode == "clock":
                target_h = int(self.alarm_hour_combo.get())
                target_m = int(self.alarm_min_combo.get())
                is_tomorrow = self.alarm_target_day.get() == "tomorrow"
                now = datetime.datetime.now()
                target_dt = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
                if is_tomorrow or target_dt <= now:
                    target_dt += datetime.timedelta(days=1)
                target_seconds = int((target_dt - now).total_seconds())
                desc_str = f"{target_dt.strftime('%m월 %d일 %H:%M')}"

        action_name = SchedulerManager._get_action_name(action_type)
        target_time_preview = (datetime.datetime.now() + datetime.timedelta(seconds=target_seconds)).strftime("%Y-%m-%d %H:%M:%S")

        msg = f"[{action_name}] 예약을 진행하시겠습니까?\n\n"
        msg += f"• 설정 시간: {desc_str}\n"
        msg += f"• 예정 시각: {target_time_preview}\n"
        if action_type == "alarm":
            msg += f"• 알람 메모: \"{memo_text if memo_text else '없음'}\"\n"
            msg += f"• 알람음: {sound_choice}\n"
        msg += "\n"
        if self.manager.is_scheduled:
            msg += "※ 새 예약을 진행하면 기존 예약은 자동으로 취소됩니다."

        self._play_sound("question")

        dialog = ModernConfirmDialog(
            self,
            title="예약 확인",
            message=msg,
            action_text="예약 확정",
            is_danger=False
        )
        self.wait_window(dialog)

        if dialog.result:
            success, res_msg = self.manager.schedule_action(
                action_type=action_type,
                seconds=target_seconds,
                memo=memo_text,
                sound_id=sound_id
            )
            if success:
                self._play_sound("success")
            else:
                self._show_simple_alert("실패", res_msg)

    def _confirm_immediate_action(self, action_type: str):
        action_name = SchedulerManager._get_action_name(action_type)
        msg = f"⚠️ 정말로 지금 즉시 [{action_name}]을(를) 실행하시겠습니까?\n\n저장되지 않은 모든 작업이 손실될 수 있습니다!"
        
        self._play_sound("warning")

        dialog = ModernConfirmDialog(
            self, 
            title=f"즉시 {action_name} 확인", 
            message=msg, 
            action_text="지금 즉시 실행",
            is_danger=True
        )
        self.wait_window(dialog)

        if dialog.result:
            self.manager.execute_immediate(action_type)

    def _confirm_cancel_schedule(self):
        if not self.manager.is_scheduled:
            return

        dialog = ModernConfirmDialog(
            self, 
            title="예약 취소 확인", 
            message="현재 진행 중인 예약을 취소하시겠습니까?", 
            action_text="예약 취소",
            is_danger=False
        )
        self.wait_window(dialog)

        if dialog.result:
            self.manager.cancel_schedule(notify=True)
            self._play_sound("cancel")

    def _show_simple_alert(self, title: str, message: str):
        dialog = ModernConfirmDialog(self, title=title, message=message, action_text="확인", is_danger=False)
        self.wait_window(dialog)

    def _play_sound(self, sound_type: str):
        try:
            if sound_type == "success":
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            elif sound_type == "warning":
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            elif sound_type == "cancel":
                winsound.MessageBeep(winsound.MB_OK)
            elif sound_type == "question":
                winsound.MessageBeep(winsound.MB_ICONQUESTION)
        except Exception:
            pass

    def _on_manager_tick(self, remaining_seconds: int, target_time_str: str):
        self.after(0, self._update_timer_display, remaining_seconds, target_time_str)

    def _update_timer_display(self, remaining_sec: int, target_time_str: str):
        hours = remaining_sec // 3600
        mins = (remaining_sec % 3600) // 60
        secs = remaining_sec % 60
        time_formatted = f"{hours:02d}:{mins:02d}:{secs:02d}"
        
        act = self.manager.action_type
        act_name = SchedulerManager._get_action_name(act or "shutdown")

        if hasattr(self, "timer_label") and self.timer_label.winfo_exists():
            self.timer_label.configure(
                text=time_formatted,
                text_color="#4ade80"
            )

        if hasattr(self, "target_time_label") and self.target_time_label.winfo_exists():
            if act == "alarm" and self.manager.memo:
                self.target_time_label.configure(
                    text=f"알람 예정: {target_time_str} | 📌 {self.manager.memo}",
                    text_color="#93c5fd"
                )
            else:
                self.target_time_label.configure(
                    text=f"실행 예정 시각: {target_time_str}",
                    text_color="#93c5fd"
                )

        if hasattr(self, "active_schedule_lbl") and self.active_schedule_lbl.winfo_exists():
            palette = theme_manager.get_theme()
            if act == "alarm" and self.manager.memo:
                self.active_schedule_lbl.configure(
                    text=f"🔔 [회의/연수 알람] {target_time_str} ({time_formatted} 남음) | 📌 {self.manager.memo}",
                    text_color=palette["accent_blue"]
                )
            else:
                self.active_schedule_lbl.configure(
                    text=f"⏰ [컴퓨터 {act_name} 예약] {target_time_str} 실행 예정 (남은 시간: {time_formatted})",
                    text_color=palette["accent_green"]
                )

    # =========================================================================
    # Apple 스타일 하단 액션 바 & 저작권 표기
    # =========================================================================
    # =========================================================================
    # 하단 스마트 상태 바 & 저작권 표기
    # =========================================================================
    def _create_bottom_actions(self, parent):
        palette = theme_manager.get_theme()

        # 평상시 숨겨져 있다가, PC 예약/알람이 가동 중일 때만 부드럽게 나타나는 스마트 상태 바
        self.active_schedule_bar = ctk.CTkFrame(
            parent,
            fg_color=palette["card_inner_bg"],
            corner_radius=10,
            border_width=1,
            border_color=palette["accent_blue"]
        )
        # 기본 상태는 숨김 (예약 가동 시 pack)

        asb_inner = ctk.CTkFrame(self.active_schedule_bar, fg_color="transparent")
        asb_inner.pack(fill="x", padx=12, pady=6)

        self.active_schedule_lbl = ctk.CTkLabel(
            asb_inner,
            text="⏰ 컴퓨터 예약 가동 중",
            font=get_font(12, "bold"),
            text_color=palette["accent_blue"],
            anchor="w"
        )
        self.active_schedule_lbl.pack(side="left", fill="x", expand=True)

        self.active_cancel_btn = ctk.CTkButton(
            asb_inner,
            text="🛑 컴퓨터 예약 취소",
            font=get_font(11, "bold"),
            fg_color="#3f1d24",
            hover_color="#dc2626",
            text_color="#fca5a5",
            width=130,
            height=28,
            corner_radius=8,
            command=self._confirm_cancel_schedule
        )
        self.active_cancel_btn.pack(side="right")

        # 하단 푸터: 저작권 표기 + 개인정보 처리방침 + 통합 예약 센터
        footer_frame = ctk.CTkFrame(parent, fg_color="transparent")
        footer_frame.pack(fill="x", pady=(6, 6))

        self.copyright_lbl = ctk.CTkLabel(
            footer_frame,
            text="Copyright 2026. 교사 서정완. All rights reserved.",
            font=get_font(10),
            text_color=palette["text_muted"]
        )
        self.copyright_lbl.pack(side="left")

        privacy_btn = ctk.CTkButton(
            footer_frame,
            text="🔒 개인정보 처리방침",
            font=get_font(9, "bold"),
            fg_color="transparent",
            hover_color=palette["sidebar_btn_hover"],
            text_color=palette["accent"],
            height=20,
            command=lambda: open_privacy_dialog(self)
        )
        privacy_btn.pack(side="right")
        attach_tooltip(privacy_btn, "100% 로컬 데이터 저장 원칙 및 제작자 공식 문의(lucky20220528@gmail.com) 안내를 확인합니다.")

        schedule_center_btn = ctk.CTkButton(
            footer_frame,
            text="📅 통합 예약·알람 관리",
            font=get_font(9, "bold"),
            fg_color="transparent",
            hover_color=palette["sidebar_btn_hover"],
            text_color=palette["accent"],
            height=20,
            command=lambda: open_schedule_dialog(self, self.manager)
        )
        schedule_center_btn.pack(side="right", padx=(0, 6))
        attach_tooltip(schedule_center_btn, "현재 등록된 모든 컴퓨터 예약 및 수업 알람을 한눈에 모아보고 관리합니다.")

    def _on_manager_state_change(self, is_scheduled: bool, action_type: Optional[str], message: str):
        self.after(0, self._update_state_ui, is_scheduled, action_type, message)

    def _update_state_ui(self, is_scheduled: bool, action_type: Optional[str], message: str):
        palette = theme_manager.get_theme()
        if not hasattr(self, "active_schedule_bar") or not self.active_schedule_bar.winfo_exists():
            return

        if is_scheduled:
            action_name = SchedulerManager._get_action_name(action_type or "shutdown")
            self.active_schedule_lbl.configure(
                text=f"⏰ [컴퓨터 {action_name} 예약 가동 중]  {message}",
                text_color=palette["accent_green"]
            )
            self.active_schedule_bar.pack(fill="x", pady=(4, 2), before=self.copyright_lbl)
        else:
            self.active_schedule_bar.pack_forget()

        # 트레이 메뉴 동적 갱신 (예약 상태 반영)
        if hasattr(self, "tray") and self.tray:
            try:
                self.tray.update_menu()
            except Exception:
                pass

    def _on_manager_alarm_triggered(self, memo: str, sound_id: str):
        self.after(0, self._open_alarm_popup, memo, sound_id)

    def _open_alarm_popup(self, memo: str, sound_id: str):
        self.deiconify()
        self.lift()
        self.focus_force()

        dialog = AlarmPopupDialog(
            self,
            memo=memo,
            sound_id=sound_id,
            on_snooze_callback=lambda: self.manager.snooze_alarm(minutes=5)
        )
        self.wait_window(dialog)

    def _minimize_to_tray(self):
        """창 X 버튼 → 트레이로 최소화 (앱은 백그라운드에서 계속 실행됨)"""
        self.withdraw()  # 창 숨기기 (종료 아님)
        if hasattr(self, "tray") and self.tray:
            self.tray.update_menu()
        # Windows 풍선 알림 한 번만 표시
        if not getattr(self, "_tray_hint_shown", False):
            self._tray_hint_shown = True
            self._show_tray_balloon()

    def _show_tray_balloon(self):
        """트레이 풍선 안내 — 오른쪽 하단 알림 영역 클릭 안내"""
        try:
            if hasattr(self, "tray") and self.tray and self.tray.tray_icon:
                self.tray.tray_icon.notify(
                    "놀티쳐가 트레이에 상주 중입니다.\n트레이 아이콘을 더블클릭하거나 우클릭하여 기능을 사용하세요.",
                    "놀티쳐 — 백그라운드 실행 중"
                )
        except Exception:
            pass

    def _on_closing(self):
        if self.manager.is_scheduled:
            dialog = ModernConfirmDialog(
                self,
                title="프로그램 종료 안내",
                message="프로그램을 닫으면 진행 중인 알람 및 예약 카운트다운이 중단됩니다.\n(단, 시스템 종료/재부팅 명령은 Windows에 등록되어 있습니다.)\n\n프로그램을 종료하시겠습니까?",
                action_text="종료",
                is_danger=False
            )
            self.wait_window(dialog)
            if not dialog.result:
                return
        if self.mini_widget and self.mini_widget.winfo_exists():
            try:
                self.mini_widget.destroy()
            except Exception:
                pass
        if self.mini_ticker and self.mini_ticker.winfo_exists():
            try:
                self.mini_ticker.destroy()
            except Exception:
                pass
        if self.student_window and self.student_window.winfo_exists():
            try:
                self.student_window.destroy()
            except Exception:
                pass
        # 트레이 아이콘 제거
        if hasattr(self, "tray") and self.tray:
            try:
                self.tray.stop()
            except Exception:
                pass
        sound_manager.stop_all()
        self.destroy()



    def _open_custom_board_dialog(self):
        CustomBoardLaunchDialog(self, self._open_student_display_with_config)

    def _open_student_display_with_config(self, config: dict):
        StudentDisplayWindow.get_instance(self, custom_config=config)
