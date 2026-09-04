import os
import json
import re
from typing import List, Dict, Any, Tuple, Optional
from src.config_utils import get_config_dir

class StudentRosterManager:
    """
    놀티쳐 데스크 - 학급 학생 명렬표 관리자 (Student Roster Manager)
    - 학생 번호, 이름, 성별(남/여) 로컬 영구 저장 (~/.knol_teacher_desk/student_roster.json)
    - 🔒 100% 로컬 단독 보관: 외부 서버 전송 일절 없음
    - 번호 모드 / 이름 모드 / 성별 필터(남학생/여학생) 추첨 지원
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
                    raw_list = data.get("students", [])
                    for s in raw_list:
                        if "gender" not in s:
                            s["gender"] = ""
                    return raw_list
            except Exception:
                pass
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
        한 줄에 한 명씩 적힌 텍스트(또는 '1번 김민수 남', '1 김민수(여)', '김민수 남' 등)로부터 학생 명단 파싱
        """
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        new_students = []

        for idx, line in enumerate(lines, start=1):
            gender = ""
            if re.search(r"[\(\[\s]남[\)\]\s]*$", line):
                gender = "남"
                line = re.sub(r"[\(\[\s]남[\)\]\s]*$", "", line).strip()
            elif re.search(r"[\(\[\s]여[\)\]\s]*$", line):
                gender = "여"
                line = re.sub(r"[\(\[\s]여[\)\]\s]*$", "", line).strip()

            parts = line.split()
            if len(parts) >= 2 and (parts[0].isdigit() or parts[0].endswith("번")):
                num_str = parts[0].replace("번", "")
                try:
                    num = int(num_str)
                except Exception:
                    num = idx
                name = " ".join(parts[1:])
            else:
                num = idx
                name = line

            if name.endswith(" 남") or name.endswith("(남)"):
                gender = "남"
                name = name[:-2].strip() if name.endswith(" 남") else name[:-3].strip()
            elif name.endswith(" 여") or name.endswith("(여)"):
                gender = "여"
                name = name[:-2].strip() if name.endswith(" 여") else name[:-3].strip()

            new_students.append({"number": num, "name": name, "gender": gender})

        new_students.sort(key=lambda x: x["number"])
        self.save_roster(new_students, self.use_names_in_picker)
        return len(new_students)

    def get_student_list(self, gender: Optional[str] = None) -> List[Dict[str, Any]]:
        if not gender or gender == "전체":
            return self.students
        return [s for s in self.students if s.get("gender") == gender]

    def get_student_names(self, gender: Optional[str] = None) -> List[str]:
        target = self.get_student_list(gender)
        if not target:
            if not self.students:
                return [f"{i}번" for i in range(1, 26)]
            return []
        res = []
        for s in target:
            num = s['number']
            nm = s.get('name', '')
            gen = s.get('gender', '')
            g_mark = f" ({gen})" if gen else ""
            if nm:
                res.append(f"{num}번 {nm}{g_mark}")
            else:
                res.append(f"{num}번{g_mark}")
        return res

    def get_count(self, gender: Optional[str] = None) -> int:
        target = self.get_student_list(gender)
        return len(target) if target else (25 if not self.students else 0)

    def get_gender_stats(self) -> Dict[str, int]:
        male_cnt = sum(1 for s in self.students if s.get("gender") == "남")
        female_cnt = sum(1 for s in self.students if s.get("gender") == "여")
        none_cnt = len(self.students) - male_cnt - female_cnt
        return {
            "total": len(self.students),
            "male": male_cnt,
            "female": female_cnt,
            "none": none_cnt
        }

student_manager = StudentRosterManager.get_instance()
