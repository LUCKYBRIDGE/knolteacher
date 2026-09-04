import time
import winsound
import threading
from typing import Optional

class SoundManager:
    """
    외부 파일 종속성 없이 100% 동작하는 풍부하고 반복적인 알람 사운드 엔진
    """
    SOUNDS = {
        "chime": {
            "name": "🔔 맑은 학교 차임벨 (딩동댕동 딩동댕동)",
            # 미솔라도 도라솔미 2회 반복 패턴 (풍부한 차임벨)
            "pattern": [
                (659, 220), (784, 220), (880, 220), (1046, 380),
                (0, 100),
                (1046, 220), (880, 220), (784, 220), (659, 450)
            ],
            "pause": 0.04
        },
        "digital": {
            "name": "⏰ 연속 디지털 알람 (삐삐삐삐 삐삐삐삐)",
            # 삐삐삐삐 4연타 2세트
            "pattern": [
                (988, 80), (0, 40), (988, 80), (0, 40), (988, 80), (0, 40), (988, 160),
                (0, 120),
                (988, 80), (0, 40), (988, 80), (0, 40), (988, 80), (0, 40), (988, 250)
            ],
            "pause": 0.03
        },
        "melody": {
            "name": "🎶 밝은 교실 멜로디 (도미솔도 솔미도)",
            # 경쾌한 클래식/동요 멜로디
            "pattern": [
                (523, 160), (659, 160), (784, 180), (1046, 280),
                (0, 80),
                (784, 160), (659, 160), (523, 350),
                (0, 80),
                (587, 160), (659, 160), (784, 160), (1046, 400)
            ],
            "pause": 0.04
        },
        "siren": {
            "name": "🚨 집중 경보 싸이렌 (위잉-위잉)",
            # 4회 연속 상승/하강 싸이렌
            "pattern": [
                (600, 160), (950, 180), (600, 160), (950, 180),
                (600, 160), (950, 180), (600, 160), (950, 300)
            ],
            "pause": 0.03
        },
        "bell": {
            "name": "📢 청량한 핑퐁 알람 (핑퐁핑퐁)",
            # 핑퐁 3회 반복
            "pattern": [
                (784, 180), (1046, 280),
                (0, 80),
                (784, 180), (1046, 280),
                (0, 80),
                (784, 180), (1046, 450)
            ],
            "pause": 0.04
        }
    }

    def __init__(self):
        self._loop_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._preview_thread: Optional[threading.Thread] = None

    def get_sound_list(self) -> list[tuple[str, str]]:
        """(sound_id, display_name) 목록 반환"""
        return [(k, v["name"]) for k, v in self.SOUNDS.items()]

    def preview_sound(self, sound_id: str, repeat_count: int = 2):
        """미리듣기 (2회 반복 연주로 충분히 들리게)"""
        self.stop_all()
        self._stop_event.clear()
        self._preview_thread = threading.Thread(
            target=self._play_pattern_n_times, 
            args=(sound_id, repeat_count), 
            daemon=True
        )
        self._preview_thread.start()

    def start_loop(self, sound_id: str):
        """알람이 꺼질 때까지 리드미컬하게 무한 반복 재생"""
        self.stop_all()
        self._stop_event.clear()
        self._loop_thread = threading.Thread(
            target=self._loop_worker, 
            args=(sound_id,), 
            daemon=True
        )
        self._loop_thread.start()

    def stop_all(self):
        """재생 중인 모든 사운드 정지"""
        self._stop_event.set()
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=0.2)
        if self._preview_thread and self._preview_thread.is_alive():
            self._preview_thread.join(timeout=0.2)
        self._loop_thread = None
        self._preview_thread = None

    def _play_pattern_n_times(self, sound_id: str, n: int):
        sound_data = self.SOUNDS.get(sound_id, self.SOUNDS["chime"])
        pattern = sound_data["pattern"]
        pause = sound_data["pause"]

        for rep in range(n):
            if self._stop_event.is_set():
                return
            for freq, dur in pattern:
                if self._stop_event.is_set():
                    return
                if freq > 0:
                    try:
                        winsound.Beep(freq, dur)
                    except Exception:
                        time.sleep(dur / 1000.0)
                else:
                    time.sleep(dur / 1000.0)
                time.sleep(pause)
            
            # 반복 간 짧은 휴식 (0.3초)
            if rep < n - 1:
                for _ in range(3):
                    if self._stop_event.is_set():
                        return
                    time.sleep(0.1)

    def _loop_worker(self, sound_id: str):
        sound_data = self.SOUNDS.get(sound_id, self.SOUNDS["chime"])
        pattern = sound_data["pattern"]
        pause = sound_data["pause"]

        while not self._stop_event.is_set():
            for freq, dur in pattern:
                if self._stop_event.is_set():
                    return
                if freq > 0:
                    try:
                        winsound.Beep(freq, dur)
                    except Exception:
                        time.sleep(dur / 1000.0)
                else:
                    time.sleep(dur / 1000.0)
                time.sleep(pause)
            
            # 한 번 연주 후 0.4초만 쉬고 계속해서 반복 재생 (알람을 놓치지 않도록)
            for _ in range(4):
                if self._stop_event.is_set():
                    return
                time.sleep(0.1)

sound_manager = SoundManager()
