from typing import Optional

class NeisPageType:
    BEHAVIOR = "BEHAVIOR"           # 행동특성 및 종합의견
    SUBJECT_TERM = "SUBJECT_TERM"   # 교과 학기말종합의견
    CREATIVE_EXP = "CREATIVE_EXP"   # 창의적 체험활동 / 기타 학생별 텍스트

PAGE_INFO = {
    NeisPageType.BEHAVIOR: {
        "name": "행동특성 및 종합의견",
        "desc": "담임 교사의 학생별 행동발달특성 및 종합의견 입력 화면",
        "table_keywords": ["행동특성 및 종합의견", "행동특성및종합의견"],
        "num_col_header": ["번호", "반/번호", "순번"],
        "name_col_header": ["성명", "이름"],
        "content_col_header": ["행동특성 및 종합의견", "종합의견", "행동특성"]
    },
    NeisPageType.SUBJECT_TERM: {
        "name": "교과 학기말 종합의견 (교과평어)",
        "desc": "교과별 학기말 종합의견 및 평가 결과 입력 화면",
        "table_keywords": ["학기말종합의견", "교과평가", "학기말 종합의견"],
        "num_col_header": ["반/번호", "번호"],
        "name_col_header": ["성명", "이름"],
        "content_col_header": ["학기말 종합의견", "종합의견", "의견"]
    }
}
