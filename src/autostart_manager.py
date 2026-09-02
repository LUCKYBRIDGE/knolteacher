import os
import sys
import winreg
from typing import Tuple

APP_REG_NAME = "KnolTeacherDesk"
LEGACY_REG_NAMES = ["TeacherAssistantScheduler", "TeacherMate", "Teachermate"]

class AutoStartManager:
    """
    Windows 시작 프로그램 등록 및 해제 관리자 (HKCU Registry 기반)
    - 레거시 레지스트리 키 자동 정리 및 KnolTeacherDesk 단일화
    """
    REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

    @classmethod
    def get_executable_path(cls) -> str:
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 단일 EXE 파일 경로
            return f'"{sys.executable}"'
        else:
            # 파이썬 스크립트 실행 시
            main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
            return f'"{sys.executable}" "{main_py}"'

    @classmethod
    def is_autostart_enabled(cls) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_KEY, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, APP_REG_NAME)
                return bool(val)
        except Exception:
            return False

    @classmethod
    def set_autostart(cls, enable: bool) -> Tuple[bool, str]:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                # 과거 레거시 키 정리
                for old_k in LEGACY_REG_NAMES:
                    try:
                        winreg.DeleteValue(key, old_k)
                    except Exception:
                        pass

                if enable:
                    exe_cmd = cls.get_executable_path()
                    winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, exe_cmd)
                    return True, "Windows 시작 프로그램에 등록되었습니다."
                else:
                    try:
                        winreg.DeleteValue(key, APP_REG_NAME)
                        return True, "Windows 시작 프로그램에서 해제되었습니다."
                    except FileNotFoundError:
                        return True, "이미 해제되어 있습니다."
        except Exception as e:
            return False, f"레지스트리 설정 중 오류 발생: {str(e)}"

autostart_manager = AutoStartManager()
