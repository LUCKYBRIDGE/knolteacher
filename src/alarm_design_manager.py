"""
알람 화면 커스텀 디자인 관리자 (AlarmDesignManager)
- 알람 팝업 창의 크기, 테마, 위치, 각 요소(제목, 타이머, 안내 메시지, 스티커)의 좌표/크기/색상 저장
- alarm_design_config.json 영구 저장 및 기본값 복원
"""
import os
import json
from typing import Dict, Any
from src.config_utils import get_config_dir

DEFAULT_ALARM_DESIGN = {
    "window_width": 380,
    "window_height": 210,
    "theme_bg": "#0f172a",
    "theme_border": "#38bdf8",
    "theme_accent": "#38bdf8",
    "theme_text": "#ffffff",
    "theme_sub": "#94a3b8",
    "position_mode": "top_right",  # top_right, center, bottom_center
    "monitor_index": 0,
    "custom_x": 0,
    "custom_y": 0,
    "elements": {
        "title": {
            "visible": True,
            "text": "🔔 [수업 교시명]",
            "font_size": 13,
            "color": "#38bdf8",
            "x": 20,
            "y": 16
        },
        "timer": {
            "visible": True,
            "font_size": 52,
            "color": "#f59e0b",
            "x": 190,
            "y": 80
        },
        "message": {
            "visible": True,
            "text": "책상 위를 정리하고 교과서를 바르게 펴두세요!",
            "font_size": 11,
            "color": "#cbd5e1",
            "x": 190,
            "y": 145
        },
        "sub_notice": {
            "visible": True,
            "text": "수업 시작 알람 카운트다운",
            "font_size": 9,
            "color": "#64748b",
            "x": 190,
            "y": 178
        },
        "sticker": {
            "visible": True,
            "sticker_type": "📚",
            "image_path": "",
            "size": 32,
            "x": 330,
            "y": 20
        }
    }
}


class AlarmDesignManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.file_path = os.path.join(get_config_dir(), "alarm_design_config.json")
        self.config: Dict[str, Any] = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cfg = dict(DEFAULT_ALARM_DESIGN)
                    cfg.update(data)
                    cfg["elements"] = dict(DEFAULT_ALARM_DESIGN["elements"])
                    if "elements" in data:
                        for k, v in data["elements"].items():
                            if k in cfg["elements"]:
                                cfg["elements"][k].update(v)
                            else:
                                cfg["elements"][k] = v
                    return cfg
            except Exception as e:
                print(f"[Alarm Design Load Error] {e}")
        return json.loads(json.dumps(DEFAULT_ALARM_DESIGN))

    def save_config(self, cfg: Dict[str, Any]):
        self.config = cfg
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Alarm Design Save Error] {e}")

    def reset_to_defaults(self):
        self.config = json.loads(json.dumps(DEFAULT_ALARM_DESIGN))
        self.save_config(self.config)


alarm_design_manager = AlarmDesignManager.get_instance()
