"""
놀티쳐 데스크 - 시스템 트레이 관리자
Windows 작업 표시줄 알림 영역(트레이)에 앱 아이콘을 상주시키고
우클릭 컨텍스트 메뉴를 통해 주요 기능을 빠르게 실행할 수 있도록 지원합니다.

[우클릭 메뉴 항목]
  ✅ 놀티쳐 데스크 열기 / 숨기기
  ─────────────────────────────
  ✏️ 화면 판서 시작
  🛠️ 플로팅 퀵바 열기
  ⏱️ 교실 타이머 & 뽑기
  🎡 돌림판 열기
  📌 미니 시간표 위젯
  ─────────────────────────────
  🖥️ PC 예약 상태 (동적 표시)
  🔔 알람 예약 상태 (동적 표시)
  ─────────────────────────────
  ❌ 완전히 종료
"""

import os
import sys
import threading
from typing import Optional, Callable


class TrayManager:
    """
    pystray 기반 시스템 트레이 아이콘 관리자.
    앱 메인 윈도우(App)와 분리된 백그라운드 스레드에서 실행됩니다.
    """

    def __init__(self, app):
        self.app = app        # App (CTk 메인 윈도우)
        self.tray_icon = None
        self._thread: Optional[threading.Thread] = None

    # ─── 트레이 초기화 & 시작 ────────────────────────────────────────────────
    def start(self):
        """백그라운드 스레드에서 트레이 아이콘을 실행합니다."""
        try:
            import pystray
            from PIL import Image
        except ImportError:
            print("[Tray] pystray 또는 Pillow 미설치 — 트레이 기능 비활성화")
            return

        icon_img = self._load_icon_image()

        menu = self._build_menu()
        self.tray_icon = pystray.Icon(
            name="knol_teacher_desk",
            icon=icon_img,
            title="놀티쳐 데스크",
            menu=menu
        )

        self._thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self._thread.start()

    def stop(self):
        """트레이 아이콘을 완전히 제거합니다."""
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None

    def update_menu(self):
        """예약 상태가 변경되었을 때 트레이 메뉴를 동적으로 갱신합니다."""
        if self.tray_icon:
            try:
                self.tray_icon.menu = self._build_menu()
                self.tray_icon.update_menu()
            except Exception:
                pass

    # ─── 아이콘 이미지 로드 ─────────────────────────────────────────────────
    def _load_icon_image(self):
        from PIL import Image
        try:
            base_dir = getattr(sys, "_MEIPASS", os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..")))
            icon_path = os.path.join(base_dir, "assets", "app_icon.png")
            if os.path.exists(icon_path):
                img = Image.open(icon_path).convert("RGBA")
                img = img.resize((64, 64), Image.LANCZOS)
                return img
        except Exception:
            pass
        # 폴백: 간단한 색상 아이콘 생성
        img = Image.new("RGBA", (64, 64), (59, 130, 246, 255))
        return img

    # ─── 우클릭 메뉴 구성 ───────────────────────────────────────────────────
    def _build_menu(self):
        import pystray

        is_visible = self.app.winfo_viewable() if self.app.winfo_exists() else False
        is_scheduled = self.app.manager.is_scheduled if hasattr(self.app, "manager") else False
        action_type = self.app.manager.action_type if is_scheduled else None

        # 예약 상태 표시 아이템
        sched_label = "● 예약 없음"
        sched_enabled = False
        if is_scheduled and action_type == "alarm":
            memo = self.app.manager.memo or ""
            sched_label = f"🔔 알람 가동 중  [{memo}]" if memo else "🔔 알람 가동 중"
            sched_enabled = True
        elif is_scheduled:
            from src.scheduler_manager import SchedulerManager
            act_name = SchedulerManager._get_action_name(action_type or "shutdown")
            rem = self.app.manager.remaining_seconds
            h = rem // 3600; m = (rem % 3600) // 60; s = rem % 60
            sched_label = f"⏰ {act_name} 예약 가동 중  ({h:02d}:{m:02d}:{s:02d} 남음)"
            sched_enabled = True

        def _show_or_hide(icon, item):
            self.app.after(0, self._toggle_window)

        def _open_drawing(icon, item):
            self.app.after(0, self.app._open_screen_drawing)

        def _open_visualizer(icon, item):
            self.app.after(0, self.app._open_visualizer)

        def _open_quickbar(icon, item):
            self.app.after(0, self.app._open_floating_quick_toolbar)

        def _open_tools_timer(icon, item):
            self.app.after(0, lambda: self.app._open_classroom_tools("timer"))

        def _open_wheel(icon, item):
            self.app.after(0, lambda: self.app._open_classroom_tools("wheel"))

        def _open_picker(icon, item):
            self.app.after(0, lambda: self.app._open_classroom_tools("picker"))

        def _open_mini_widget(icon, item):
            self.app.after(0, self.app._open_mini_widget)

        def _cancel_schedule(icon, item):
            self.app.after(0, self.app._confirm_cancel_schedule)

        def _switch_today(icon, item):
            self.app.after(0, lambda: self._show_and_navigate("today"))

        def _switch_tools(icon, item):
            self.app.after(0, lambda: self._show_and_navigate("classroom_tools"))

        def _quit_app(icon, item):
            self.app.after(0, self.app._on_closing)

        toggle_label = "✅ 놀티쳐 데스크 숨기기" if is_visible else "📂 놀티쳐 데스크 열기"

        menu = pystray.Menu(
            pystray.MenuItem(toggle_label, _show_or_hide, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("📋 오늘 시간표 & 급식 보기", _switch_today),
            pystray.MenuItem("✏️ 화면 위 자유 판서 시작", _open_drawing),
            pystray.MenuItem("📷 실물화상기 열기", _open_visualizer),
            pystray.MenuItem("🛠️ 플로팅 퀵바 열기", _open_quickbar),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⏱️ 교실 타이머 열기", _open_tools_timer),
            pystray.MenuItem("🎲 발표자 랜덤 뽑기", _open_picker),
            pystray.MenuItem("🎡 돌림판 열기", _open_wheel),
            pystray.MenuItem("📌 미니 시간표 위젯", _open_mini_widget),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(sched_label, _cancel_schedule, enabled=sched_enabled),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ 완전히 종료", _quit_app),
        )
        return menu

    # ─── 헬퍼 메서드 ────────────────────────────────────────────────────────
    def _toggle_window(self):
        """앱 창을 표시하거나 숨깁니다 (최소화/복원)."""
        try:
            if self.app.winfo_viewable():
                self.app.withdraw()
            else:
                self.app.deiconify()
                self.app.lift()
                self.app.focus_force()
        except Exception:
            pass
        self.update_menu()

    def _show_and_navigate(self, view_key: str):
        """창을 표시하고 특정 탭으로 이동합니다."""
        try:
            self.app.deiconify()
            self.app.lift()
            self.app.focus_force()
            self.app._switch_view(view_key)
        except Exception:
            pass
        self.update_menu()


# ─── 싱글턴 인스턴스 ────────────────────────────────────────────────────────
_tray_manager: Optional[TrayManager] = None


def init_tray(app) -> TrayManager:
    global _tray_manager
    _tray_manager = TrayManager(app)
    _tray_manager.start()
    return _tray_manager


def get_tray() -> Optional[TrayManager]:
    return _tray_manager
