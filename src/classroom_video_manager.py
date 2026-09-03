"""
놀티쳐 (KnolTeacher) - 교실 수업 영상 매니저 (Classroom Video Manager)
- 학생 공유 화면 연동: 무광고 고화질 수업 영상 실행 및 관리
- 유튜브 링크로 신규 수업 영상 등록
- 기본 과목별(과학, 안전, 사회, 체육, 미술) 추천 수업 영상 프리셋 제공
"""

import os
import sys
import json
import subprocess
import threading
from src.config_utils import get_config_dir
from src.youtube_audio_manager import extract_youtube_id, fetch_youtube_meta


class ClassroomVideoManager:
    _instance = None
    CONFIG_FILE = os.path.join(get_config_dir(), "classroom_videos.json")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.videos = []
        self._load_videos()

    def _get_default_presets(self):
        return [
            {
                "id": "7rXl3aD8_bQ",
                "name": "🌍 [과학] 신비로운 우주와 태양계 행성들",
                "emoji": "🌍",
                "category": "과학",
                "video_id": "7rXl3aD8_bQ"
            },
            {
                "id": "lTRiuFIWV54",
                "name": "🔥 [안전] 알기 쉬운 화재 대피 및 소화기 사용법",
                "emoji": "🔥",
                "category": "안전",
                "video_id": "lTRiuFIWV54"
            },
            {
                "id": "2OEL4P1Rz04",
                "name": "📜 [사회] 아름다운 우리의 섬 독도 이야기",
                "emoji": "📜",
                "category": "사회",
                "video_id": "2OEL4P1Rz04"
            },
            {
                "id": "DWcJFNfaw9c",
                "name": "🤸 [체육] 다 함께 신나는 어린이 키 성장 체조",
                "emoji": "🤸",
                "category": "체육",
                "video_id": "DWcJFNfaw9c"
            },
            {
                "id": "_tV5LEBDs7w",
                "name": "🎨 [미술] 쉽게 완성하는 신기한 종이접기 교실",
                "emoji": "🎨",
                "category": "미술",
                "video_id": "_tV5LEBDs7w"
            }
        ]

    def _load_videos(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.videos = json.load(f)
                    if isinstance(self.videos, list) and len(self.videos) > 0:
                        return
            except Exception:
                pass
        self.videos = self._get_default_presets()
        self._save_videos()

    def _save_videos(self):
        try:
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.videos, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_videos(self):
        return list(self.videos)

    def add_video(self, url_or_id: str, custom_name: str = "", emoji: str = "🎬", category: str = "수업"):
        vid = extract_youtube_id(url_or_id)
        if not vid:
            return None

        meta = fetch_youtube_meta(vid)
        name = custom_name.strip() or meta["title"]

        item = {
            "id": vid,
            "name": name,
            "emoji": emoji.strip() or "🎬",
            "category": category.strip() or "수업",
            "video_id": vid,
            "author": meta.get("author", "")
        }

        self.videos = [v for v in self.videos if v.get("video_id") != vid]
        self.videos.append(item)
        self._save_videos()
        return item

    def remove_video(self, video_id: str):
        self.videos = [v for v in self.videos if v.get("video_id") != video_id]
        self._save_videos()

    def launch_video(self, video_id: str, title: str = "수업 영상"):
        """무광고 비디오 플레이어를 독립 창으로 실행"""
        def _runner():
            py_exe = sys.executable
            player_script = os.path.join(os.path.dirname(__file__), "youtube_video_player.py")
            cmd = [py_exe, player_script, f"--id={video_id}", f"--title={title}"]
            creationflags = 0x08000000 if os.name == 'nt' else 0
            subprocess.Popen(cmd, creationflags=creationflags, close_fds=True)

        threading.Thread(target=_runner, daemon=True).start()


classroom_video = ClassroomVideoManager.get_instance()
