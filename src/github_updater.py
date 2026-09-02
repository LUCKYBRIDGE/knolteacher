import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
import threading
from typing import Optional, Tuple, Dict, Any, Callable

from src.config_utils import get_config_dir, APP_VERSION

DEFAULT_GITHUB_REPO = "LUCKYBRIDGE/teachermate"

class GitHubUpdater:
    """
    GitHub Releases 기반 원클릭 인앱 스마트 자동 업데이트 시스템
    - GitHub Releases API를 통해 최신 릴리스 버전 체크
    - 웹 브라우저를 열지 않고도 앱 내부에서 최신 티처메이트.exe 다운로드
    - 기존 실행 파일을 안전하게 교체(Replace)하고 자동 재실행
    - 중복 파일((1), (2) 등) 발생 원천 차단
    """
    def __init__(self):
        self.config_file = os.path.join(get_config_dir(), "updater_config.json")
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "github_repo": DEFAULT_GITHUB_REPO,
            "auto_check_on_startup": True
        }

    def save_settings(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def check_latest_release(self) -> Tuple[bool, str, str, str, str]:
        """
        GitHub Releases API를 호출하여 최신 버전 정보 확인
        반환: (has_update, latest_version, download_url, release_notes, html_url)
        """
        repo = self.settings.get("github_repo", DEFAULT_GITHUB_REPO).strip()
        if not repo or "/" not in repo:
            return False, APP_VERSION, "", "GitHub 저장소 정보가 올바르지 않습니다.", ""

        api_url = f"https://api.github.com/repos/{repo}/releases/latest"
        headers = {
            "User-Agent": "TeacherMate-AutoUpdater",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))

            tag_name = data.get("tag_name", "").strip().lstrip("vV")
            release_notes = data.get("body", "최신 기능 개선 및 안정성 향상")
            html_url = data.get("html_url", f"https://github.com/{repo}/releases")

            # assets 중 .exe 파일 찾기
            download_url = ""
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if name.lower().endswith(".exe"):
                    download_url = asset.get("browser_download_url", "")
                    break

            if not download_url and data.get("assets"):
                download_url = data["assets"][0].get("browser_download_url", "")

            # 버전 비교 (단순 문자열 비교 및 숫자 비교)
            has_update = self._is_newer_version(tag_name, APP_VERSION)
            return has_update, tag_name, download_url, release_notes, html_url

        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False, APP_VERSION, "", "아직 등록된 GitHub Release가 없습니다.", f"https://github.com/{repo}"
            return False, APP_VERSION, "", f"GitHub API 오류: {e.code}", ""
        except Exception as e:
            return False, APP_VERSION, "", f"네트워크 연결 확인 필요: {e}", ""

    def _is_newer_version(self, latest: str, current: str) -> bool:
        if not latest:
            return False
        try:
            latest_parts = [int(p) for p in latest.split(".") if p.isdigit()]
            current_parts = [int(p) for p in current.split(".") if p.isdigit()]
            return latest_parts > current_parts
        except Exception:
            return latest != current

    def apply_update_in_background(self, download_url: str, on_progress: Optional[Callable[[float, str], None]] = None, on_finish: Optional[Callable[[bool, str], None]] = None):
        """
        백그라운드에서 최신 EXE를 다운로드하고 안전하게 교체 재실행
        """
        def _task():
            try:
                if on_progress:
                    on_progress(0.1, "최신 업데이트 파일 다운로드 준비 중...")

                # 1. 임시 파일 다운로드
                temp_exe = os.path.join(get_config_dir(), "teachermate_update_temp.exe")
                if os.path.exists(temp_exe):
                    try:
                        os.remove(temp_exe)
                    except Exception:
                        pass

                headers = {"User-Agent": "TeacherMate-AutoUpdater"}
                req = urllib.request.Request(download_url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=30) as resp, open(temp_exe, "wb") as out_f:
                    total_size = int(resp.headers.get("content-length", 0))
                    downloaded = 0
                    block_size = 65536

                    while True:
                        chunk = resp.read(block_size)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and on_progress:
                            prog = min(0.9, downloaded / total_size)
                            on_progress(prog, f"다운로드 중... ({downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB)")

                if on_progress:
                    on_progress(0.95, "업데이트 적용 스크립트 실행 중...")

                # 2. 대상 실행 파일 경로 결정
                current_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.join(os.path.expanduser("~"), "Desktop", "티처메이트.exe")
                
                # 3. 안전한 교체 배치 스크립트 작성 (update_helper.bat)
                bat_path = os.path.join(get_config_dir(), "apply_update.bat")
                bat_content = f"""@echo off
chcp 65001 > nul
echo [티처메이트] 최신 버전으로 업데이트 중입니다...
timeout /t 2 /nobreak > nul
:loop
taskkill /f /im "{os.path.basename(current_exe)}" > nul 2>&1
timeout /t 1 /nobreak > nul
copy /y "{temp_exe}" "{current_exe}" > nul
if errorlevel 1 (
    echo [재시도] 파일 교체 대기 중...
    timeout /t 1 /nobreak > nul
    goto loop
)
del /f /q "{temp_exe}" > nul 2>&1
echo [완료] 최신 버전을 실행합니다.
start "" "{current_exe}"
del /f /q "%~f0" > nul 2>&1
exit
"""
                with open(bat_path, "w", encoding="utf-8") as f:
                    f.write(bat_content)

                if on_finish:
                    on_finish(True, "다운로드 완료! 2초 후 앱이 자동으로 재실행됩니다.")

                # 4. 배치 파일 실행 후 현재 프로세스 종료
                subprocess.Popen(["cmd.exe", "/c", bat_path], shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
                sys.exit(0)

            except Exception as e:
                if on_finish:
                    on_finish(False, f"업데이트 실패: {e}")

        threading.Thread(target=_task, daemon=True).start()

github_updater = GitHubUpdater()
