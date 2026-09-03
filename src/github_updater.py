import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
import threading
from typing import Optional, Tuple, Dict, Any, Callable

from src.config_utils import get_config_dir, APP_VERSION

DEFAULT_GITHUB_REPO = "LUCKYBRIDGE/knolteacher"

class GitHubUpdater:
    """
    GitHub Releases 기반 원클릭 인앱 스마트 자동 업데이트 시스템
    - GitHub Releases API를 통해 최신 릴리스 버전 체크
    - 웹 브라우저를 열지 않고도 앱 내부에서 최신 놀티쳐 데스크.exe 다운로드
    - 기존 실행 파일을 안전하게 교체(Replace)하고 자동 재실행
    - 중복 파일((1), (2) 등) 발생 원천 차단
    """
    def __init__(self):
        self.config_file = os.path.join(get_config_dir(), "updater_config.json")
        self.settings = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        default = {
            "github_repo": DEFAULT_GITHUB_REPO,
            "auto_check_on_startup": True
        }
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default.update(data)
            except Exception:
                pass
        return default

    def save_settings(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def check_latest_release(self) -> Tuple[bool, str, Optional[str], str, str]:
        """
        GitHub Releases API를 호출하여 새 버전 여부 확인
        Returns:
            (has_update: bool, latest_version: str, download_url: Optional[str], release_notes: str, html_url: str)
        """
        repo = self.settings.get("github_repo", DEFAULT_GITHUB_REPO).strip()
        api_url = f"https://api.github.com/repos/{repo}/releases/latest"

        try:
            req = urllib.request.Request(
                api_url,
                headers={
                    "User-Agent": "KnolTeacherDesk-AutoUpdater",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    tag_name = data.get("tag_name", "").strip().lstrip("vV")
                    body = data.get("body", "최신 기능 개선 및 버그 수정이 적용되었습니다.")
                    html_url = data.get("html_url", f"https://github.com/{repo}/releases")

                    # 에셋 중 .exe 파일 다운로드 URL 탐색
                    exe_download_url = None
                    for asset in data.get("assets", []):
                        aname = asset.get("name", "").lower()
                        if aname.endswith(".exe"):
                            exe_download_url = asset.get("browser_download_url")
                            break

                    has_update = self._is_newer_version(tag_name, APP_VERSION)
                    return has_update, tag_name, exe_download_url, body, html_url
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False, APP_VERSION, None, "아직 등록된 공식 릴리스가 없습니다.", f"https://github.com/{repo}/releases"
        except Exception as e:
            print(f"[Updater Error] {e}")

        return False, APP_VERSION, None, "최신 버전을 확인하지 못했습니다.", f"https://github.com/{repo}/releases"

    def _is_newer_version(self, latest: str, current: str) -> bool:
        """버전 문자열 비교 (예: 5.8 > 5.7)"""
        try:
            l_parts = [int(p) for p in latest.split(".") if p.isdigit()]
            c_parts = [int(p) for p in current.split(".") if p.isdigit()]
            while len(l_parts) < 3:
                l_parts.append(0)
            while len(c_parts) < 3:
                c_parts.append(0)
            return l_parts > c_parts
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
                temp_exe = os.path.join(get_config_dir(), "knolteacherdesk_update_temp.exe")
                if os.path.exists(temp_exe):
                    try:
                        os.remove(temp_exe)
                    except Exception:
                        pass

                headers = {"User-Agent": "KnolTeacherDesk-AutoUpdater"}
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
                current_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.join(os.path.expanduser("~"), "Desktop", "놀티쳐 데스크.exe")
                
                # 3. 안전한 교체 배치 스크립트 작성 (update_helper.bat)
                bat_path = os.path.join(get_config_dir(), "apply_update.bat")
                bat_content = f"""@echo off
chcp 65001 > nul
echo [놀티쳐 데스크] 최신 버전으로 업데이트 중입니다...
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
del "{temp_exe}" > nul 2>&1
start "" "{current_exe}"
del "%~f0" > nul 2>&1
"""
                with open(bat_path, "w", encoding="utf-8") as bf:
                    bf.write(bat_content)

                if on_progress:
                    on_progress(1.0, "업데이트 준비 완료! 앱을 재실행합니다.")

                if on_finish:
                    on_finish(True, "성공적으로 업데이트가 적용되었습니다.")

                # 4. 배치 스크립트 실행 및 현재 프로세스 종료
                subprocess.Popen(["cmd.exe", "/c", bat_path], shell=True, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                sys.exit(0)

            except Exception as e:
                print(f"[Update Apply Failed] {e}")
                if on_finish:
                    on_finish(False, f"업데이트 실패: {str(e)}")

        th = threading.Thread(target=_task, daemon=True)
        th.start()

github_updater = GitHubUpdater()
