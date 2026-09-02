from typing import Any

class ValidationResult:
    def __init__(self):
        self.is_valid: bool = True
        self.fatal_errors: list[str] = []
        self.warnings: list[str] = []
        self.total_rows: int = 0
        self.valid_students_count: int = 0
        self.skipped_students_count: int = 0
        self.students_to_input: list[dict[str, Any]] = []

class DataValidator:
    """
    Excel 데이터 검증 및 안전장치 규칙 엔진
    - 학생번호 중복: 즉시 전체 입력 차단 (Fatal Error)
    - 학생번호 누락/빈값: 해당 학생 건너뜀 (밀림 방지)
    - 내용 빈칸: 건너뜀
    """
    @staticmethod
    def validate(raw_records: list[dict[str, Any]]) -> ValidationResult:
        res = ValidationResult()
        res.total_rows = len(raw_records)

        number_map: dict[int, list[dict[str, Any]]] = {}
        invalid_rows = []

        for r in raw_records:
            raw_num = r.get("raw_number")
            name = r.get("name", "")
            content = r.get("content", "")
            row_idx = r.get("row_index", 0)

            # 1. 번호 파싱
            student_num = None
            if raw_num is not None:
                s_str = str(raw_num).strip()
                # 1.0 같은 float 형태 처리
                try:
                    student_num = int(float(s_str))
                except Exception:
                    student_num = None

            if student_num is None or student_num <= 0:
                invalid_rows.append(f"{row_idx}행: 유효하지 않은 학생번호 '{raw_num}' (건너뜀)")
                continue

            if student_num not in number_map:
                number_map[student_num] = []
            
            number_map[student_num].append({
                "student_number": student_num,
                "name": name,
                "content": content,
                "row_index": row_idx
            })

        # 2. 학생번호 중복 검사 (최우선 Fatal Error)
        duplicates = []
        for s_num, items in number_map.items():
            if len(items) > 1:
                rows_str = ", ".join(f"{it['row_index']}행({it['name']})" for it in items)
                duplicates.append(f"• 학생번호 [{s_num}번]이 {len(items)}회 중복되었습니다: {rows_str}")

        if duplicates:
            res.is_valid = False
            res.fatal_errors.append("⚠️ [안전장치] Excel 파일에 중복된 학생번호가 존재하여 자동입력을 시작할 수 없습니다.")
            res.fatal_errors.extend(duplicates)
            res.fatal_errors.append("👉 Excel 파일에서 중복 번호를 수정한 후 다시 시도해주세요.")
            return res

        # 3. 유효 학생 리스트 정렬 구성 및 빈 내용 체크
        sorted_numbers = sorted(number_map.keys())
        if not sorted_numbers:
            res.is_valid = False
            res.fatal_errors.append("입력할 유효한 학생 데이터가 없습니다.")
            return res

        # 번호 누락(중간 번호 건너뜀) 안내
        min_n, max_n = sorted_numbers[0], sorted_numbers[-1]
        missing_numbers = [n for n in range(min_n, max_n + 1) if n not in number_map]
        if missing_numbers:
            missing_str = ", ".join(map(str, missing_numbers))
            res.warnings.append(f"ℹ️ {missing_str}번 학생 데이터가 Excel에 없어 해당 번호는 건너뜁니다 (이후 번호는 밀리지 않고 정확히 입력됨).")

        for s_num in sorted_numbers:
            item = number_map[s_num][0]
            content = item["content"].strip()
            if not content:
                item["status"] = "SKIPPED_EMPTY"
                item["status_text"] = "내용 없음 (건너뜀)"
                res.skipped_students_count += 1
            else:
                item["status"] = "READY"
                item["status_text"] = "입력 대기"
                res.valid_students_count += 1

            res.students_to_input.append(item)

        if invalid_rows:
            res.warnings.extend(invalid_rows)

        return res
