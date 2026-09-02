import os
import sys
import glob
import shutil
import subprocess
import time

APP_VERSION = "5.7"

def get_config_dir() -> str:
    """
    티처메이트의 글로벌 영구 설정 디렉터리 (~/.teacher_mate)
    - 새로운 버전의 exe를 다운로드받거나 경로를 변경하더라도
      사용자가 저장한 모든 설정(시간표, 학교, 나이스 키, 바로가기, 테마 등)이 100% 영구 보존됩니다.
    """
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".teacher_mate")
    os.makedirs(config_dir, exist_ok=True)

    # 기존 구버전 로컬 config/ 디렉터리가 있을 경우 자동 마이그레이션
    _migrate_legacy_configs(config_dir)

    return config_dir

def _migrate_legacy_configs(target_dir: str):
    """
    과거 로컬 config/ 폴더에 저장되어 있던 설정 파일들을 새 영구 폴더로 자동 복사
    """
    candidate_legacy_dirs = []
    
    if getattr(sys, 'frozen', False):
        candidate_legacy_dirs.append(os.path.join(os.path.dirname(sys.executable), "config"))
    
    source_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    candidate_legacy_dirs.append(os.path.join(source_root, "config"))

    config_files = [
        "custom_timetable.json",
        "schedule_periods.json",
        "timetable_settings.json",
        "neis_settings.json",
        "weekly_schedule.json",
        "site_bookmarks.json",
        "scheduler_history.json"
    ]

    for leg_dir in candidate_legacy_dirs:
        if os.path.exists(leg_dir) and os.path.abspath(leg_dir) != os.path.abspath(target_dir):
            for fname in config_files:
                src_file = os.path.join(leg_dir, fname)
                dst_file = os.path.join(target_dir, fname)
                if os.path.exists(src_file) and not os.path.exists(dst_file):
                    try:
                        shutil.copy2(src_file, dst_file)
                        print(f"[Migration] Copied {fname} to persistent config directory.")
                    except Exception as e:
                        print(f"[Migration Warning] Could not copy {fname}: {e}")

def self_consolidate_and_clean():
    """
    스마트 단일 파일 유지 시스템 (Self-Consolidation & Duplicate Cleaner)
    1) 현재 실행된 파일이 '티처메이트 (1).exe' 등 중복 복사본인 경우:
       -> 바탕화면의 메인 '티처메이트.exe'를 최신인 자기 자신으로 자동 갱신
    2) 바탕화면 및 실행 폴더 주변에 남아있는 '티처메이트 (1).exe', '티처메이트 (2).exe' 등
       모든 중복/잉여 다운로드 파일들을 자동으로 감지하여 깔끔하게 삭제 정리
    => 결과: 언제나 오직 단 1개의 '티처메이트.exe'만 바탕화면에 영구 유지됩니다!
    """
    if not getattr(sys, 'frozen', False):
        return

    try:
        current_exe = os.path.abspath(sys.executable)
        current_dir = os.path.dirname(current_exe)
        current_name = os.path.basename(current_exe)
        
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        main_desktop_exe = os.path.join(desktop_dir, "티처메이트.exe")

        # 1. 만약 현재 실행 파일이 바탕화면의 '티처메이트.exe'가 아닌 복사본(예: 다운로드 폴더나 티처메이트 (1).exe)이라면
        #    바탕화면의 메인 티처메이트.exe를 최신 버전인 현재 파일로 덮어쓰기 갱신
        if os.path.abspath(current_exe) != os.path.abspath(main_desktop_exe):
            try:
                shutil.copy2(current_exe, main_desktop_exe)
                print(f"[Auto-Updater] Main desktop executable updated to latest version from {current_name}")
            except Exception as e:
                print(f"[Auto-Updater Note] {e}")

        # 2. 바탕화면 및 현재 폴더에서 중복 파일 패턴 검색 및 자동 삭제
        search_dirs = [desktop_dir]
        if os.path.abspath(current_dir) != os.path.abspath(desktop_dir):
            search_dirs.append(current_dir)

        patterns = [
            "티처메이트 (*).exe",
            "TeacherMate (*).exe",
            "티처메이트(TeacherMate).exe",
            "티처메이트 - 복사본*.exe",
            "TeacherMate - Copy*.exe"
        ]

        for sdir in search_dirs:
            for pat in patterns:
                for dup_path in glob.glob(os.path.join(sdir, pat)):
                    # 현재 실행 중인 파일 자체는 프로세스가 락을 잡고 있으므로 제외
                    if os.path.abspath(dup_path) == os.path.abspath(current_exe):
                        continue
                    try:
                        os.remove(dup_path)
                        print(f"[Cleaner] Removed duplicate file: {dup_path}")
                    except Exception:
                        pass
    except Exception as e:
        print(f"[Self-Consolidate Error] {e}")
