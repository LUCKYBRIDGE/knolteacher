"""
놀티쳐 보드 다중 프리셋 프로필 관리자 (Board Preset Manager)
- 보드 실행 시 시작 도구(타이머, 추첨, 주사위, 돌림판, 점수판, 판서) 및 테마 사전 설정
- 교사가 원하는 이름으로 무제한 프로필 저장 및 0.1초 원클릭 실시간 전환
"""

import os
import json
from typing import Dict, Any, List
from src.config_utils import get_config_dir

DEFAULT_PRESETS = {
    "기본 수업 모드": {
        "active_tool": "timer",
        "theme_key": "slate_dark",
        "is_fullscreen": False,
        "desc": "대형 수업 타이머와 슬레이트 다크 테마"
    },
    "모둠 활동 모드": {
        "active_tool": "wheel",
        "theme_key": "chalkboard",
        "is_fullscreen": False,
        "desc": "모둠 돌림판 및 칠판 딥그린 테마"
    },
    "발표 추첨 모드": {
        "active_tool": "picker",
        "theme_key": "indigo_night",
        "is_fullscreen": False,
        "desc": "학생 발표자 랜덤 추첨 및 오션 인디고 테마"
    },
    "학급 판서 모드": {
        "active_tool": "drawing",
        "theme_key": "warm_beige",
        "is_fullscreen": False,
        "desc": "학급 판서 칠판 및 웜베이지 테마"
    },
    "모둠 점수판 모드": {
        "active_tool": "scoreboard",
        "theme_key": "slate_dark",
        "is_fullscreen": False,
        "desc": "모둠별 점수판 및 다크 테마"
    }
}

class BoardPresetManager:
    def __init__(self):
        self.config_file = os.path.join(get_config_dir(), "board_presets.json")
        self.data = {
            "active_preset": "기본 수업 모드",
            "presets": dict(DEFAULT_PRESETS)
        }
        self.load()

    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if "presets" in loaded and isinstance(loaded["presets"], dict):
                        self.data["presets"] = loaded["presets"]
                    if "active_preset" in loaded and loaded["active_preset"] in self.data["presets"]:
                        self.data["active_preset"] = loaded["active_preset"]
            except Exception as e:
                print(f"[BoardPresetManager] 로드 오류: {e}")

    def save(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[BoardPresetManager] 저장 오류: {e}")
            return False

    def get_preset_names(self) -> List[str]:
        return list(self.data["presets"].keys())

    def get_active_preset_name(self) -> str:
        name = self.data.get("active_preset", "기본 수업 모드")
        if name not in self.data["presets"]:
            names = self.get_preset_names()
            name = names[0] if names else "기본 수업 모드"
        return name

    def get_active_preset(self) -> Dict[str, Any]:
        name = self.get_active_preset_name()
        return self.data["presets"].get(name, DEFAULT_PRESETS["기본 수업 모드"])

    def set_active_preset(self, name: str) -> bool:
        if name in self.data["presets"]:
            self.data["active_preset"] = name
            self.save()
            return True
        return False

    def save_preset(self, name: str, config: Dict[str, Any]) -> bool:
        if not name.strip():
            return False
        self.data["presets"][name.strip()] = config
        self.data["active_preset"] = name.strip()
        return self.save()

    def delete_preset(self, name: str) -> bool:
        if name in self.data["presets"] and len(self.data["presets"]) > 1:
            del self.data["presets"][name]
            if self.data.get("active_preset") == name:
                self.data["active_preset"] = list(self.data["presets"].keys())[0]
            return self.save()
        return False

    def rename_preset(self, old_name: str, new_name: str) -> bool:
        if old_name in self.data["presets"] and new_name.strip() and new_name.strip() not in self.data["presets"]:
            cfg = self.data["presets"].pop(old_name)
            self.data["presets"][new_name.strip()] = cfg
            if self.data.get("active_preset") == old_name:
                self.data["active_preset"] = new_name.strip()
            return self.save()
        return False

board_preset_manager = BoardPresetManager()
