import os
import sys
import shutil
import glob

APP_VERSION = "5.7"

def get_config_dir() -> str:
    """
    놀티쳐 데스크의 글로벌 영구 설정 디렉터리 (~/.knol_teacher_desk)
    - 버전 업데이트나 파일 위치 변경 시에도 사용자 설정(시간표, 학교, 바로가기, 테마) 영구 보존
    - 과거 레거시 디렉터리(~/.teacher_mate 및 local config/) 자동 마이그레이션 지원
    """
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".knol_teacher_desk")
    
    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir, exist_ok=True)
        except Exception:
            # Fallback to local config if home directory access fails
            config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config"))
            os.makedirs(config_dir, exist_ok=True)
            return config_dir

    # 기존 레거시 설정 파일 자동 이전 (무손실 마이그레이션)
    _migrate_legacy_configs(config_dir)

    return config_dir

def _migrate_legacy_configs(target_dir: str):
    """
    과거 설정 디렉터리(~/.teacher_mate 및 프로젝트 local config/)에서
    새로운 ~/.knol_teacher_desk 디렉터리로 설정 파일들을 안전하게 자동 복사
    """
    legacy_dirs = [
        os.path.join(os.path.expanduser("~"), ".teacher_mate"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config"))
    ]

    target_files = [
        "schedule_config.json",
        "timetable_config.json",
        "neis_config.json",
        "bookmarks_config.json",
        "mini_ticker_config.json",
        "updater_config.json",
        "theme_config.json"
    ]

    for leg_dir in legacy_dirs:
        if os.path.exists(leg_dir) and os.path.abspath(leg_dir) != os.path.abspath(target_dir):
            for fname in target_files:
                src_f = os.path.join(leg_dir, fname)
                dst_f = os.path.join(target_dir, fname)
                if os.path.exists(src_f) and not os.path.exists(dst_f):
                    try:
                        shutil.copy2(src_f, dst_f)
                    except Exception:
                        pass

def self_consolidate_and_clean():
    """
    스마트 단일 파일 유지 시스템 (Self-Consolidation & Duplicate Cleaner)
    1) 현재 실행된 파일이 '놀티쳐 데스크 (1).exe' 등 중복 복사본인 경우:
       -> 바탕화면의 메인 '놀티쳐 데스크.exe'를 최신인 자기 자신으로 자동 갱신
    2) 바탕화면 및 실행 폴더 주변에 남아있는 과거 파일(티처메이트, TeacherMate 등)과
       모든 중복/잉여 다운로드 파일들을 자동으로 감지하여 깔끔하게 삭제 정리
    => 결과: 언제나 오직 단 1개의 '놀티쳐 데스크.exe'만 바탕화면에 영구 유지됩니다!
    """
    if not getattr(sys, 'frozen', False):
        return

    try:
        current_exe = os.path.abspath(sys.executable)
        current_dir = os.path.dirname(current_exe)
        current_name = os.path.basename(current_exe)
        
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        main_desktop_exe = os.path.join(desktop_dir, "놀티쳐 데스크.exe")

        # 1. 만약 현재 실행 파일이 바탕화면의 '놀티쳐 데스크.exe'가 아닌 복사본(예: 다운로드 폴더나 놀티쳐 데스크 (1).exe)이라면
        #    바탕화면의 메인 놀티쳐 데스크.exe를 최신 버전인 현재 파일로 덮어쓰기 갱신
        if os.path.abspath(current_exe) != os.path.abspath(main_desktop_exe):
            try:
                shutil.copy2(current_exe, main_desktop_exe)
                print(f"[Auto-Updater] Main desktop executable updated to latest version from {current_name}")
            except Exception as e:
                print(f"[Auto-Updater Note] {e}")

        # 2. 바탕화면 및 현재 폴더에서 중복/과거 파일 패턴 검색 및 자동 삭제
        search_dirs = [desktop_dir]
        if os.path.abspath(current_dir) != os.path.abspath(desktop_dir):
            search_dirs.append(current_dir)

        patterns = [
            "놀티쳐 데스크 (*).exe",
            "놀티쳐데스크 (*).exe",
            "KnolTeacherDesk (*).exe",
            "놀퀴즈*.exe",
            "티처메이트*.exe",
            "TeacherMate*.exe",
            "TeacherDesk*.exe",
            "컴퓨터종료*.exe",
            "컴퓨터예약*.exe"
        ]

        for sdir in search_dirs:
            for pat in patterns:
                for dup_path in glob.glob(os.path.join(sdir, pat)):
                    if os.path.abspath(dup_path) == os.path.abspath(current_exe):
                        continue
                    try:
                        os.remove(dup_path)
                        print(f"[Cleaner] Removed redundant file: {dup_path}")
                    except Exception:
                        pass
    except Exception as e:
        print(f"[Self-Consolidate Error] {e}")
