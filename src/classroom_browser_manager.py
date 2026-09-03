"""
놀티쳐 (KnolTeacher) - 교실 클린 브라우저 매니저 (Classroom Browser Manager)
- 교실 TV(학생 화면) 연동: 무광고 클린 웹 브라우저 실행 및 수업 북마크 관리
"""

import os
import sys
import json
import subprocess
import threading
from src.config_utils import get_config_dir


class ClassroomBrowserManager:
    _instance = None
    CONFIG_FILE = os.path.join(get_config_dir(), "classroom_browser_bookmarks.json")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.bookmarks = []
        self._load_bookmarks()

    def _get_default_presets(self):
        return [
            {
                "id": "iscream",
                "name": "아이스크림 초등 (교수학습지원)",
                "url": "https://www.i-scream.co.kr",
                "emoji": "🍦",
                "category": "수업"
            },
            {
                "id": "tselpa",
                "name": "티셀파 초등 (천재교과서)",
                "url": "https://elem.tselpa.co.kr",
                "emoji": "🔵",
                "category": "수업"
            },
            {
                "id": "douclass",
                "name": "두클래스 초등 (동아출판)",
                "url": "https://elem.douclass.com",
                "emoji": "🟢",
                "category": "수업"
            },
            {
                "id": "vivasam",
                "name": "비바쌤 초등 (비상교육)",
                "url": "https://e.vivasam.com",
                "emoji": "🟣",
                "category": "수업"
            },
            {
                "id": "indischool",
                "name": "인디스쿨 (초등교사 커뮤니티)",
                "url": "https://www.indischool.com",
                "emoji": "🏫",
                "category": "교사"
            },
            {
                "id": "cls_edunet",
                "name": "e학습터 (학급 학습터)",
                "url": "https://cls.edunet.net",
                "emoji": "🏫",
                "category": "수업"
            },
            {
                "id": "edunet",
                "name": "에듀넷·티-클리어 (교육 포털)",
                "url": "https://www.edunet.net",
                "emoji": "📚",
                "category": "수업"
            },
            {
                "id": "naver",
                "name": "네이버 (포털/검색)",
                "url": "https://www.naver.com",
                "emoji": "🟢",
                "category": "포털"
            },
            {
                "id": "google",
                "name": "구글 (자료 검색)",
                "url": "https://www.google.com",
                "emoji": "🔍",
                "category": "포털"
            },
            {
                "id": "wiki",
                "name": "위키백과 (백과사전)",
                "url": "https://ko.wikipedia.org",
                "emoji": "📖",
                "category": "사전"
            },
            {
                "id": "naver_terms",
                "name": "네이버 지식백과",
                "url": "https://terms.naver.com",
                "emoji": "💡",
                "category": "사전"
            },
            {
                "id": "naver_map",
                "name": "네이버 지도 (사회/지리)",
                "url": "https://map.naver.com",
                "emoji": "🗺️",
                "category": "사회"
            },
            {
                "id": "kma",
                "name": "기상청 날씨누리 (과학/날씨)",
                "url": "https://www.kma.go.kr",
                "emoji": "☀️",
                "category": "과학"
            },
            {
                "id": "museum",
                "name": "국립중앙박물관 (역사/문화)",
                "url": "https://www.museum.go.kr",
                "emoji": "🏛️",
                "category": "역사"
            }
        ]

    def _load_bookmarks(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.bookmarks = json.load(f)
                    if isinstance(self.bookmarks, list) and len(self.bookmarks) > 0:
                        return
            except Exception:
                pass
        self.bookmarks = self._get_default_presets()
        self._save_bookmarks()

    def _save_bookmarks(self):
        try:
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.bookmarks, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_bookmarks(self):
        return list(self.bookmarks)

    def add_bookmark(self, name: str, url: str, emoji: str = "🌐", category: str = "수업"):
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        import uuid
        bm_id = str(uuid.uuid4())[:8]
        item = {
            "id": bm_id,
            "name": name.strip() or url,
            "url": url.strip(),
            "emoji": emoji.strip() or "🌐",
            "category": category.strip() or "수업"
        }
        self.bookmarks.append(item)
        self._save_bookmarks()
        return item

    def remove_bookmark(self, bm_id: str):
        self.bookmarks = [b for b in self.bookmarks if b.get("id") != bm_id]
        self._save_bookmarks()

    def launch_browser(self, target_url: str = "https://www.naver.com"):
        """교실 전용 무광고 클린 브라우저를 독립 창으로 실행"""
        def _runner():
            py_exe = sys.executable
            browser_script = os.path.join(os.path.dirname(__file__), "classroom_browser.py")
            cmd = [py_exe, browser_script, f"--url={target_url}"]
            creationflags = 0x08000000 if os.name == 'nt' else 0
            subprocess.Popen(cmd, creationflags=creationflags, close_fds=True)

        threading.Thread(target=_runner, daemon=True).start()


classroom_browser = ClassroomBrowserManager.get_instance()
