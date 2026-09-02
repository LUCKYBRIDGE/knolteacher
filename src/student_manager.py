import os
import json
from typing import List, Dict, Any, Tuple
from src.config_utils import get_config_dir

class StudentRosterManager:
    """
    놀티쳐 데스크 - 학급 학생 명렬표 관리자 (Student Roster Manager)
    - 학생 번호 및 이름 로컬 영구 저장 (~/.knol_teacher_desk/student_roster.json)
    - 🔒 100% 로컬 단독 보관: 외부 서버 전송 일절 없음
    - 번호 모드 / 이름 모드 추첨 지원
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.config_file = os.path.join(get_config_dir(), "student_roster.json")
        self.students: List[Dict[str, Any]] = self._load_roster()
        self.use_names_in_picker: bool = self._load_preference()

    def _load_roster(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("students", [])
            except Exception:
                pass
        # 기본 25명 샘플
        return []

    def _load_preference(self) -> bool:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("use_names_in_picker", True)
            except Exception:
                pass
        return True

    def save_roster(self, students: List[Dict[str, Any]], use_names: bool = True):
        self.students = students
        self.use_names_in_picker = use_names
        try:
            payload = {
                "_info": "이 데이터는 선생님의 로컬 컴퓨터에만 안전하게 영구 보관되며 외부 서버로 절대 전송되지 않습니다.",
                "use_names_in_picker": self.use_names_in_picker,
                "students": self.students
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Roster Save Error] {e}")

    def import_from_text(self, text: str) -> int:
        """
        한 줄에 한 명씩 적힌 텍스트(또는 '1번 김민수', '김민수' 등)로부터 학생 명단 파싱
        """
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        new_students = []

        for idx, line in enumerate(lines, start=1):
            parts = line.split()
            if len(parts) >= 2 and (parts[0].isdigit() or parts[0].endswith("번")):
                # 예: "1 김민수" 또는 "1번 김민수"
                num_str = parts[0].replace("번", "")
                try:
                    num = int(num_str)
                except Exception:
                    num = idx
                name = " ".join(parts[1:])
            else:
                num = idx
                name = line

            new_students.append({"number": num, "name": name})

        # 번호순 정렬
        new_students.sort(key=lambda x: x["number"])
        self.save_roster(new_students, self.use_names_in_picker)
        return len(new_students)

    def get_student_list(self) -> List[Dict[str, Any]]:
        return self.students

    def get_student_names(self) -> List[str]:
        if not self.students:
            return [f"{i}번" for i in range(1, 26)]
        return [f"{s['number']}번 {s['name']}" if s.get('name') else f"{s['number']}번" for s in self.students]

    def get_count(self) -> int:
        return len(self.students) if self.students else 25

student_manager = StudentRosterManager.get_instance()
