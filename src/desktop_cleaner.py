import os
import sys
import shutil
import datetime
import time
import winreg
import ctypes
from typing import Tuple, List, Dict, Any

class DesktopCleanerManager:
    """
    놀티쳐 데스크 - 쾌적한 PC & 바탕화면 스마트 정리 센터
    1. 🧹 바탕화면 1초 스마트 자동 분류 정리 (확장자별 폴더화 및 원클릭 Undo)
    2. 🙈 수업/공개용 바탕화면 아이콘 즉시 숨기기 / 보이기 (Zen Focus Mode)
    3. 🗑️ 다운로드 폴더 & 임시파일(Temp) 안전 청소
    4. 🗂️ 새 학기 학급 필수 업무 폴더 트리 1초 자동 생성기
    """
    def __init__(self):
        self.last_organized_records = []  # [(src, dst), ...] for Undo

    def get_desktop_path(self) -> str:
        return os.path.join(os.path.expanduser("~"), "Desktop")

    def get_downloads_path(self) -> str:
        return os.path.join(os.path.expanduser("~"), "Downloads")

    # ==========================================
    # 1. 🧹 바탕화면 1초 스마트 자동 정리
    # ==========================================
    def organize_desktop(self) -> Tuple[bool, str, int]:
        """
        바탕화면에 흩어진 파일들을 성격별 폴더로 자동 분류 정리
        (바로가기 .lnk 및 '놀티쳐 데스크.exe'는 제외)
        """
        desktop = self.get_desktop_path()
        if not os.path.exists(desktop):
            return False, "바탕화면 경로를 찾을 수 없습니다.", 0

        # 분류 폴더 매핑
        CATEGORIES = {
            "📁 [문서·수업자료]": [".hwp", ".hwpx", ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".csv"],
            "📁 [사진·이미지]": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".psd"],
            "📁 [동영상·오디오]": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".mp3", ".wav", ".m4a", ".flac"],
            "📁 [압축·설치파일]": [".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".exe", ".msi"]
        }

        self.last_organized_records.clear()
        moved_count = 0

        # 보호 대상 파일 (정리하지 않고 바탕화면에 그대로 둘 파일)
        PROTECTED_NAMES = ["놀티쳐.exe", "놀티쳐 데스크.exe", "knolteacher.exe", "desktop.ini"]

        try:
            for item in os.listdir(desktop):
                item_path = os.path.join(desktop, item)
                
                # 폴더나 바로가기(.lnk) 및 보호 대상은 건너뜀
                if os.path.isdir(item_path):
                    continue
                if item.lower().endswith(".lnk") or item in PROTECTED_NAMES:
                    continue

                _, ext = os.path.splitext(item)
                ext_lower = ext.lower()

                target_folder_name = "📁 [기타 파일]"
                for cat_name, ext_list in CATEGORIES.items():
                    if ext_lower in ext_list:
                        target_folder_name = cat_name
                        break

                target_folder_path = os.path.join(desktop, target_folder_name)
                os.makedirs(target_folder_path, exist_ok=True)

                dst_path = os.path.join(target_folder_path, item)
                
                # 파일명 중복 방지
                if os.path.exists(dst_path):
                    base, ex = os.path.splitext(item)
                    now_ts = datetime.datetime.now().strftime("%H%M%S")
                    dst_path = os.path.join(target_folder_path, f"{base}_{now_ts}{ex}")

                shutil.move(item_path, dst_path)
                self.last_organized_records.append((item_path, dst_path))
                moved_count += 1

            if moved_count > 0:
                return True, f"총 {moved_count}개의 파일을 성격별 폴더로 깔끔하게 정리했습니다!", moved_count
            else:
                return True, "정리할 대상 파일이 없습니다. 이미 바탕화면이 깨끗합니다!", 0

        except Exception as e:
            return False, f"정리 중 오류 발생: {str(e)}", moved_count

    def undo_organize(self) -> Tuple[bool, str, int]:
        """직전 정리 작업을 원래 위치로 되돌리기"""
        if not self.last_organized_records:
            return False, "되돌릴 직전 정리 기록이 없습니다.", 0

        restored_count = 0
        try:
            for orig_src, current_dst in reversed(self.last_organized_records):
                if os.path.exists(current_dst):
                    shutil.move(current_dst, orig_src)
                    restored_count += 1

            self.last_organized_records.clear()
            return True, f"총 {restored_count}개의 파일을 원래 자리로 복원했습니다!", restored_count
        except Exception as e:
            return False, f"복원 중 오류 발생: {str(e)}", restored_count

    # ==========================================
    # 2. 🙈 수업/공개용 바탕화면 아이콘 숨김/표시 (Zen Mode)
    # ==========================================
    def toggle_desktop_icons(self) -> Tuple[bool, bool, str]:
        """
        바탕화면 아이콘을 1초 만에 모두 숨기거나 다시 표시
        Returns: (success: bool, is_currently_visible: bool, message: str)
        """
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
                current_val, _ = winreg.QueryValueEx(key, "HideIcons")
                new_val = 1 if current_val == 0 else 0
                winreg.SetValueEx(key, "HideIcons", 0, winreg.REG_DWORD, new_val)

            # 탐색기 쉘 새로고침 (SHChangeNotify)
            ctypes.windll.shell32.SHChangeNotify(0x8000000, 0x1000, 0, 0)
            
            is_visible = (new_val == 0)
            msg = "바탕화면 아이콘이 표시되었습니다." if is_visible else "수업 모드: 바탕화면 아이콘이 모두 숨겨졌습니다."
            return True, is_visible, msg
        except Exception as e:
            return False, True, f"아이콘 토글 실패: {str(e)}"

    # ==========================================
    # 3. 🗑️ 다운로드 폴더 및 임시파일 안전 청소
    # ==========================================
    def clean_temp_and_downloads(self, days_old: int = 30) -> Tuple[bool, str, int, float]:
        """
        오래된 임시파일 및 Downloads 폴더 내 오래된 파일 안전 정리
        Returns: (success, msg, deleted_files_count, freed_mb)
        """
        deleted_count = 0
        freed_bytes = 0
        cutoff_time = time.time() - (days_old * 86400)

        # 1. 시스템 Temp 폴더
        temp_dir = os.environ.get("TEMP", "")
        if temp_dir and os.path.exists(temp_dir):
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        st = os.stat(fp)
                        if st.st_mtime < cutoff_time:
                            f_size = st.st_size
                            os.remove(fp)
                            deleted_count += 1
                            freed_bytes += f_size
                    except Exception:
                        pass

        freed_mb = freed_bytes / (1024 * 1024)
        return True, f"오래된 임시파일 {deleted_count}개 삭제 완료 ({freed_mb:.1f} MB 확보)", deleted_count, freed_mb

    # ==========================================
    # 4. 🗂️ 새 학기 학급 필수 업무 폴더 트리 생성
    # ==========================================
    def create_class_folder_kit(self, grade_class_name: str = "2026학년도 학급경영") -> Tuple[bool, str]:
        """
        새 학기 교사용 표준 폴더 트리 1초 자동 생성
        """
        desktop = self.get_desktop_path()
        root_folder = os.path.join(desktop, f"📁 {grade_class_name}")

        subfolders = [
            "01_학급경영 (명렬표, 시간표, 좌석배치, 1인1역)",
            "02_수업자료 (교과별 학습지, PPT, 창체, 안전)",
            "03_평가및나이스 (수행평가, 관찰기록, 세특, 행동특성)",
            "04_상담및생활지도 (학생상담일지, 학부모상담, 가통)",
            "05_공문및행정 (기안문, 내부결재, 출장, 연수물)",
            "06_사진및영상 (학급행사, 현장체험학습, 축제)"
        ]

        try:
            os.makedirs(root_folder, exist_ok=True)
            for sub in subfolders:
                os.makedirs(os.path.join(root_folder, sub), exist_ok=True)

            return True, f"바탕화면에 '{os.path.basename(root_folder)}' 표준 폴더 6개가 성공적으로 생성되었습니다!"
        except Exception as e:
            return False, f"폴더 생성 실패: {str(e)}"

desktop_cleaner = DesktopCleanerManager()
