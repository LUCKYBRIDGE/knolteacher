"""
놀티쳐 보드 탭 & 위젯 레이아웃 관리자 (Board Tab Manager)
- 사전설정 표준 탭 (종료 후 재실행 시 원래 기본 배치로 복구)
- 사용자 커스텀 탭 (마지막에 사용한 위젯 배치 및 크기 그대로 영구 보존)
- 탭 이름 자유 설정 및 추가/삭제
"""
import os
import json
import uuid
from typing import List, Dict, Any, Optional
from src.config_utils import get_config_dir

class BoardTabManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.config_file = os.path.join(get_config_dir(), "board_tabs_config.json")
        self.active_tab_id = "std_tools"
        self.custom_tabs: List[Dict[str, Any]] = []
        self._load_config()

    def get_standard_tabs(self) -> List[Dict[str, Any]]:
        """사전 설정된 표준 모드 탭 목록 (재시작 시 항상 원본 상태로 복구)"""
        return [
            {
                "id": "std_tools",
                "name": "🎯 수업 도구 모드",
                "is_custom": False,
                "widgets": [
                    {"id": "w_timer", "type": "timer", "title": "⏱️ 수업 타이머", "x": 40, "y": 40, "w": 360, "h": 270},
                    {"id": "w_picker", "type": "picker", "title": "🎯 발표자 추첨", "x": 430, "y": 40, "w": 380, "h": 320},
                    {"id": "w_dice", "type": "dice", "title": "🎲 스마트 주사위 & 통계", "x": 40, "y": 330, "w": 500, "h": 320},
                ]
            },
            {
                "id": "std_board",
                "name": "📋 학급 게시판 모드",
                "is_custom": False,
                "widgets": [
                    {"id": "w_tt", "type": "timetable", "title": "📅 오늘의 시간표", "x": 40, "y": 40, "w": 340, "h": 580},
                    {"id": "w_meal", "type": "meal", "title": "🍱 오늘의 급식", "x": 410, "y": 40, "w": 340, "h": 580},
                    {"id": "w_memo", "type": "memo", "title": "📝 학급 알림장", "x": 780, "y": 40, "w": 360, "h": 580},
                ]
            },
            {
                "id": "std_split",
                "name": "⚖️ 올인원 분할 모드",
                "is_custom": False,
                "widgets": [
                    {"id": "w_timer", "type": "timer", "title": "⏱️ 수업 타이머", "x": 40, "y": 40, "w": 340, "h": 280},
                    {"id": "w_picker", "type": "picker", "title": "🎯 발표자 추첨", "x": 40, "y": 340, "w": 340, "h": 280},
                    {"id": "w_tt", "type": "timetable", "title": "📅 오늘의 시간표", "x": 410, "y": 40, "w": 320, "h": 580},
                    {"id": "w_meal", "type": "meal", "title": "🍱 오늘의 급식", "x": 750, "y": 40, "w": 320, "h": 580},
                ]
            }
        ]

    def _load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.active_tab_id = data.get("active_tab_id", "std_tools")
                    self.custom_tabs = data.get("custom_tabs", [])
            except Exception as e:
                print(f"[BoardTabManager] load error: {e}")
                self.custom_tabs = []
        else:
            # 기본 커스텀 탭 1개 생성
            self.custom_tabs = [
                {
                    "id": f"custom_{uuid.uuid4().hex[:6]}",
                    "name": "내 맞춤 보드 1",
                    "is_custom": True,
                    "widgets": [
                        {"id": "w_c1", "type": "timer", "title": "⏱️ 수업 타이머", "x": 50, "y": 50, "w": 340, "h": 260},
                        {"id": "w_c2", "type": "picker", "title": "🎯 발표자 추첨", "x": 420, "y": 50, "w": 360, "h": 280},
                        {"id": "w_c3", "type": "dice", "title": "🎲 스마트 주사위 & 통계", "x": 50, "y": 330, "w": 480, "h": 310}
                    ]
                }
            ]
            self._save_config()

    def _save_config(self):
        try:
            payload = {
                "active_tab_id": self.active_tab_id,
                "custom_tabs": self.custom_tabs
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[BoardTabManager] save error: {e}")

    def get_all_tabs(self) -> List[Dict[str, Any]]:
        return self.get_standard_tabs() + self.custom_tabs

    def get_tab_by_id(self, tab_id: str) -> Optional[Dict[str, Any]]:
        for t in self.get_all_tabs():
            if t["id"] == tab_id:
                return t
        return None

    def add_custom_tab(self, name: str = "") -> Dict[str, Any]:
        cnt = len(self.custom_tabs) + 1
        new_name = name.strip() or f"내 맞춤 보드 {cnt}"
        new_tab = {
            "id": f"custom_{uuid.uuid4().hex[:6]}",
            "name": new_name,
            "is_custom": True,
            "widgets": [
                {"id": f"w_{uuid.uuid4().hex[:4]}", "type": "timer", "title": "⏱️ 수업 타이머", "x": 60, "y": 60, "w": 340, "h": 260}
            ]
        }
        self.custom_tabs.append(new_tab)
        self.active_tab_id = new_tab["id"]
        self._save_config()
        return new_tab

    def rename_tab(self, tab_id: str, new_name: str) -> bool:
        for t in self.custom_tabs:
            if t["id"] == tab_id:
                t["name"] = new_name.strip() or t["name"]
                self._save_config()
                return True
        return False

    def delete_tab(self, tab_id: str) -> bool:
        for idx, t in enumerate(self.custom_tabs):
            if t["id"] == tab_id:
                self.custom_tabs.pop(idx)
                if self.active_tab_id == tab_id:
                    self.active_tab_id = "std_tools"
                self._save_config()
                return True
        return False

    def update_tab_widgets(self, tab_id: str, widgets_data: List[Dict[str, Any]]):
        """커스텀 탭인 경우에만 실시간 배치(X, Y, W, H)를 영구 저장"""
        for t in self.custom_tabs:
            if t["id"] == tab_id:
                t["widgets"] = widgets_data
                self._save_config()
                return

board_tab_manager = BoardTabManager.get_instance()
