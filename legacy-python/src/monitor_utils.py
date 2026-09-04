"""
Windows 다중 모니터 감지 유틸리티 (Monitor Utils)
- ctypes EnumDisplayMonitors API로 연결된 모든 모니터의 좌표 및 해상도 감지
- 모니터 1, 모니터 2 등 선택 지원
"""
import ctypes
from ctypes import wintypes
from typing import List, Dict, Any

def get_system_monitors() -> List[Dict[str, Any]]:
    monitors = []

    def monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        rect = lprcMonitor.contents
        x = rect.left
        y = rect.top
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        idx = len(monitors)
        is_primary = (x == 0 and y == 0)
        label = f"모니터 {idx + 1}" + (" (주 화면)" if is_primary else " (확장 화면)")
        monitors.append({
            "index": idx,
            "name": label,
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "is_primary": is_primary
        })
        return 1

    try:
        MonitorEnumProc = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            wintypes.HMONITOR,
            wintypes.HDC,
            ctypes.POINTER(wintypes.RECT),
            wintypes.LPARAM
        )
        proc = MonitorEnumProc(monitor_enum_proc)
        ctypes.windll.user32.EnumDisplayMonitors(None, None, proc, 0)
    except Exception as e:
        print(f"[Monitor Detection Error] {e}")

    if not monitors:
        # 폴백: 단일 모니터 1920x1080
        monitors.append({
            "index": 0,
            "name": "모니터 1 (기본)",
            "x": 0,
            "y": 0,
            "width": 1920,
            "height": 1080,
            "is_primary": True
        })

    return monitors

def get_monitor_by_index(idx: int) -> Dict[str, Any]:
    mons = get_system_monitors()
    if 0 <= idx < len(mons):
        return mons[idx]
    return mons[0]
