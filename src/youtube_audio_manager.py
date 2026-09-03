"""
놀티쳐 (KnolTeacher) - 유튜브 백그라운드 교실 BGM 오디오 매니저
- 유튜브 링크에서 화면 없이 오직 소리만 백그라운드로 재생
- oEmbed API 기반 동영상 제목/채널 자동 추출
- 사전 등록 플레이리스트 관리 (집중 음악, 활동 BGM, 명상, 정리정돈 등)
- 재생, 일시정지, 정지, 볼륨 조절, 반복 재생 제어
"""

import os
import sys
import re
import json
import time
import urllib.request
import urllib.parse
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from src.config_utils import get_config_dir
from src.font_config import get_font
from src.tooltip import attach_tooltip

WORKER_PORT = 28888
WORKER_URL = f"http://127.0.0.1:{WORKER_PORT}"


def extract_youtube_id(url_or_id: str) -> str:
    """다양한 형태의 유튜브 링크에서 11자리 비디오 ID 추출"""
    text = url_or_id.strip()
    if re.match(r'^[a-zA-Z0-9_-]{11}$', text):
        return text

    patterns = [
        r'(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/live\/|\/shorts\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
        r'music\.youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1)
    return ""


def fetch_youtube_meta(video_id: str) -> dict:
    """YouTube oEmbed API로 비디오 제목, 채널명 초고속 조회 (인증 불필요)"""
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return {
                "title": data.get("title", f"유튜브 음악 ({video_id})"),
                "author": data.get("author_name", "YouTube"),
                "thumbnail": data.get("thumbnail_url", "")
            }
    except Exception:
        return {
            "title": f"유튜브 음악 ({video_id})",
            "author": "YouTube",
            "thumbnail": ""
        }


class YouTubeAudioManager:
    _instance = None
    CONFIG_FILE = os.path.join(get_config_dir(), "classroom_bgm_playlist.json")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.worker_proc = None
        self.playlist = []
        self.current_track = None
        self.is_playing = False
        self.volume = 80
        self._load_playlist()
        self._ensure_worker_async()

    def _get_default_presets(self):
        return [
            {
                "id": "5qap5aO4i9A",
                "name": "🌿 [집중/자습] 편안하고 차분한 로파이 피아노 BGM",
                "emoji": "🌿",
                "category": "집중",
                "video_id": "5qap5aO4i9A"
            },
            {
                "id": "DWcJFNfaw9c",
                "name": "☕ [독서/아침] 따뜻한 휴식 칠 비트 음악",
                "emoji": "☕",
                "category": "휴식",
                "video_id": "DWcJFNfaw9c"
            },
            {
                "id": "_tV5LEBDs7w",
                "name": "🎨 [활동/미술] 포근한 감성 힐링 BGM",
                "emoji": "🎨",
                "category": "활동",
                "video_id": "_tV5LEBDs7w"
            },
            {
                "id": "WPni755-Krg",
                "name": "🧠 [집중/공부] 알파파 두뇌 집중 클래스 음악",
                "emoji": "🧠",
                "category": "집중",
                "video_id": "WPni755-Krg"
            },
            {
                "id": "2OEL4P1Rz04",
                "name": "🧘 [명상/힐링] 맑은 자연과 마음 챙김 힐링 BGM",
                "emoji": "🧘",
                "category": "명상",
                "video_id": "2OEL4P1Rz04"
            }
        ]

    def _load_playlist(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.playlist = json.load(f)
                    if isinstance(self.playlist, list) and len(self.playlist) > 0:
                        return
            except Exception:
                pass
        self.playlist = self._get_default_presets()
        self._save_playlist()

    def _save_playlist(self):
        try:
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.playlist, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_playlist(self):
        return list(self.playlist)

    def add_track(self, url_or_id: str, custom_name: str = "", emoji: str = "🎵", category: str = "수업"):
        vid = extract_youtube_id(url_or_id)
        if not vid:
            return None

        meta = fetch_youtube_meta(vid)
        name = custom_name.strip() or meta["title"]

        track = {
            "id": vid,
            "name": name,
            "emoji": emoji.strip() or "🎵",
            "category": category.strip() or "수업",
            "video_id": vid,
            "author": meta.get("author", "")
        }

        # 중복 검사
        self.playlist = [t for t in self.playlist if t.get("video_id") != vid]
        self.playlist.append(track)
        self._save_playlist()
        return track

    def remove_track(self, video_id: str):
        if self.current_track and self.current_track.get("video_id") == video_id:
            self.stop()
        self.playlist = [t for t in self.playlist if t.get("video_id") != video_id]
        self._save_playlist()

    # ── 워커 프로세스 통신 ──────────────────────────────────────────────────
    def _is_worker_running(self) -> bool:
        try:
            req = urllib.request.Request(f"{WORKER_URL}/ping")
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _ensure_worker_async(self):
        def _task():
            if not self._is_worker_running():
                self._spawn_worker()
        threading.Thread(target=_task, daemon=True).start()

    def _spawn_worker(self):
        try:
            py_exe = sys.executable
            # Windows 콘솔 창 없이 조용히 실행
            creationflags = 0x08000000 if os.name == 'nt' else 0  # CREATE_NO_WINDOW
            worker_script = os.path.join(os.path.dirname(__file__), "youtube_audio_worker.py")

            self.worker_proc = subprocess.Popen(
                [py_exe, worker_script],
                creationflags=creationflags,
                close_fds=True
            )
            # 최대 4초간 시작 대기
            for _ in range(8):
                time.sleep(0.5)
                if self._is_worker_running():
                    break
        except Exception:
            pass

    def _send_cmd(self, endpoint: str) -> bool:
        if not self._is_worker_running():
            self._spawn_worker()
            time.sleep(1.0)

        try:
            req = urllib.request.Request(f"{WORKER_URL}{endpoint}")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    # ── 재생 제어 ────────────────────────────────────────────────────────
    def play(self, track: dict):
        vid = track.get("video_id")
        if not vid:
            return

        self.current_track = track
        self.is_playing = True

        def _do_play():
            stream_url = None
            try:
                # 1차 방어: yt-dlp로 광고 없는 순수 다이렉트 오디오 스트림 URL 추출
                import yt_dlp
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                    'no_warnings': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
                    stream_url = info.get('url')
            except Exception:
                stream_url = None

            if stream_url:
                # 다이렉트 스트림 재생 (광고 0% 원천 차단)
                enc_url = urllib.parse.quote(stream_url)
                self._send_cmd(f"/play_direct?url={enc_url}")
            else:
                # 2차 방어: Iframe Fallback (50ms 광고 스키퍼 & 16배속 음소거 가동)
                self._send_cmd(f"/play_iframe?id={vid}")

            self._send_cmd(f"/volume?val={self.volume}")

        threading.Thread(target=_do_play, daemon=True).start()

    def pause(self):
        self.is_playing = False
        threading.Thread(target=lambda: self._send_cmd("/pause"), daemon=True).start()

    def resume(self):
        if self.current_track:
            self.is_playing = True
            threading.Thread(target=lambda: self._send_cmd("/resume"), daemon=True).start()

    def stop(self):
        self.is_playing = False
        self.current_track = None
        threading.Thread(target=lambda: self._send_cmd("/stop"), daemon=True).start()

    def set_volume(self, val: int):
        self.volume = max(0, min(100, val))
        threading.Thread(target=lambda: self._send_cmd(f"/volume?val={self.volume}"), daemon=True).start()

    # ── 추가 다이얼로그 ──────────────────────────────────────────────────
    def open_add_dialog(self, parent=None, on_success=None):
        dlg = ctk.CTkToplevel(parent)
        dlg.title("유튜브 배경음악(BGM) 등록")
        dlg.geometry("460x340")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.grab_set()

        ctk.CTkLabel(
            dlg, text="🎵 유튜브 배경음악 (오디오 전용) 등록",
            font=get_font(13, "bold"), text_color="#0284c7"
        ).pack(pady=(16, 8))

        form = ctk.CTkFrame(dlg, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20, pady=4)

        # 1. 유튜브 링크 입력란
        ctk.CTkLabel(form, text="유튜브 영상 링크 또는 ID:", font=get_font(10, "bold"), anchor="w").pack(fill="x", pady=(4, 1))
        url_box = ctk.CTkFrame(form, fg_color="transparent")
        url_box.pack(fill="x", pady=(0, 6))

        url_entry = ctk.CTkEntry(url_box, placeholder_text="예: https://www.youtube.com/watch?v=...", font=get_font(11))
        url_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        # 2. 곡 이름 입력란
        ctk.CTkLabel(form, text="표시할 곡 제목:", font=get_font(10, "bold"), anchor="w").pack(fill="x", pady=(4, 1))
        name_entry = ctk.CTkEntry(form, placeholder_text="링크를 넣고 [제목 가져오기]를 누르면 자동 입력됩니다", font=get_font(11))
        name_entry.pack(fill="x", pady=(0, 8))

        def _fetch_title():
            raw = url_entry.get().strip()
            vid = extract_youtube_id(raw)
            if not vid:
                messagebox.showwarning("오류", "올바른 유튜브 영상 링크가 아닙니다.", parent=dlg)
                return
            status_lbl.configure(text="⏳ 유튜브 정보 조회 중...")

            def _worker():
                meta = fetch_youtube_meta(vid)
                t = meta.get("title", "")
                if t:
                    name_entry.delete(0, "end")
                    name_entry.insert(0, t)
                    status_lbl.configure(text=f"✔️ 조회 완료: {meta.get('author', '')}")
                else:
                    status_lbl.configure(text="⚠️ 제목을 찾지 못했습니다. 직접 입력해주세요.")

            threading.Thread(target=_worker, daemon=True).start()

        fetch_btn = ctk.CTkButton(
            url_box, text="제목 가져오기", width=96, font=get_font(10, "bold"),
            fg_color="#0284c7", hover_color="#0369a1", command=_fetch_title
        )
        fetch_btn.pack(side="left")

        # 3. 이모지 및 카테고리
        sub_box = ctk.CTkFrame(form, fg_color="transparent")
        sub_box.pack(fill="x", pady=2)

        ctk.CTkLabel(sub_box, text="이모지:", font=get_font(10, "bold")).pack(side="left", padx=(0, 4))
        emoji_entry = ctk.CTkEntry(sub_box, width=60, placeholder_text="🎵", font=get_font(11))
        emoji_entry.insert(0, "🎵")
        emoji_entry.pack(side="left", padx=(0, 14))

        ctk.CTkLabel(sub_box, text="분류:", font=get_font(10, "bold")).pack(side="left", padx=(0, 4))
        cat_combo = ctk.CTkComboBox(sub_box, values=["집중", "휴식", "활동", "정리", "명상", "기타"], width=100, font=get_font(10))
        cat_combo.set("집중")
        cat_combo.pack(side="left")

        # 상태 메시지
        status_lbl = ctk.CTkLabel(form, text="💡 화면에 영상 창이 일절 뜨지 않고 오직 소리만 깨끗하게 나옵니다.", font=get_font(9), text_color="#64748b")
        status_lbl.pack(pady=4)

        # 4. 저장 버튼
        btn_box = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(6, 16))

        def _save():
            u = url_entry.get().strip()
            vid = extract_youtube_id(u)
            if not vid:
                messagebox.showwarning("입력 필요", "유튜브 링크를 입력해주세요.", parent=dlg)
                return
            n = name_entry.get().strip()
            em = emoji_entry.get().strip() or "🎵"
            cat = cat_combo.get()

            self.add_track(vid, custom_name=n, emoji=em, category=cat)
            dlg.destroy()
            if on_success:
                on_success()

        ctk.CTkButton(
            btn_box, text="등록 완료 ✔️", font=get_font(11, "bold"),
            fg_color="#059669", hover_color="#047857", height=36,
            command=_save
        ).pack(side="left", fill="x", expand=True, padx=4)

        ctk.CTkButton(
            btn_box, text="취소", font=get_font(10),
            fg_color="#64748b", hover_color="#475569", height=36, width=70,
            command=dlg.destroy
        ).pack(side="left", padx=4)


youtube_audio = YouTubeAudioManager.get_instance()
