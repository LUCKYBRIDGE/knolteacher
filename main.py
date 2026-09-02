import os
import sys
import ctypes

# Windows 고해상도(DPI) 선명도 최적화
if sys.platform == "win32":
    try:
        # Per-Monitor DPI Aware v2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from src.font_config import setup_global_fonts
from src.scheduler_manager import SchedulerManager
from src.ui import App

def main():
    manager = SchedulerManager()
    app = App(manager)
    setup_global_fonts(app)
    app.mainloop()

if __name__ == "__main__":
    main()
