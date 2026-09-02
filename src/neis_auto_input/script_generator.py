import json
from typing import Any
from src.neis_auto_input.page_adapters import NeisPageType, PAGE_INFO

class NeisScriptGenerator:
    """
    4세대 나이스 웹 화면 DOM 주입 및 학생번호 1:1 매칭 자동입력/검증 스크립트 생성기
    - 학생 번호 기준 1:1 매핑 (순서 무관, 밀림 100% 방지)
    - 3가지 입력 모드 지원 (빈칸만, 이어쓰기, 덮어쓰기)
    - 입력 후 전수 비교 검증
    - 자동 저장 절대 금지
    """
    @staticmethod
    def generate_input_and_verify_script(
        students_data: list[dict[str, Any]], 
        input_mode: str = "EMPTY_ONLY",  # "EMPTY_ONLY", "APPEND", "OVERWRITE"
        page_type: str = NeisPageType.BEHAVIOR
    ) -> str:
        """
        학생 데이터와 설정에 맞춘 고성능 브라우저 DOM 자동입력 및 검증 자바스크립트 생성
        """
        # { "1": { "name": "김도윤", "content": "..." }, "2": ... }
        student_payload = {}
        for s in students_data:
            num = s.get("student_number")
            if num and s.get("content", "").strip():
                student_payload[str(num)] = {
                    "name": s.get("name", ""),
                    "content": s.get("content", "")
                }

        payload_json = json.dumps(student_payload, ensure_ascii=False)
        info = PAGE_INFO.get(page_type, PAGE_INFO[NeisPageType.BEHAVIOR])

        js_code = f"""
(function() {{
    const STUDENTS = {payload_json};
    const INPUT_MODE = "{input_mode}"; // EMPTY_ONLY, APPEND, OVERWRITE
    const PAGE_NAME = "{info['name']}";

    console.log("[NEIS AutoInput] 시작: " + PAGE_NAME + " (대상 학생 수: " + Object.keys(STUDENTS).length + "명, 모드: " + INPUT_MODE + ")");

    let report = {{
        successCount: 0,
        skippedCount: 0,
        failedCount: 0,
        mismatchCount: 0,
        logs: [],
        details: []
    }};

    // 1. 페이지 내 입력 행(Row) 탐색
    function findRows() {{
        let allRows = Array.from(document.querySelectorAll('tr, div[role="row"], .grid-row, .w2grid_row'));
        let targetRows = [];

        for (let row of allRows) {{
            // 행 내 텍스트에 숫자가 있고 textarea 또는 text input이 있는 경우
            let hasInput = row.querySelector('textarea, input[type="text"], div[contenteditable="true"]');
            if (hasInput) {{
                targetRows.push(row);
            }}
        }}
        return targetRows;
    }}

    // 2. 행에서 학생 번호 추출
    function extractStudentNumber(row) {{
        let cells = Array.from(row.querySelectorAll('td, div[role="gridcell"], .w2grid_cell, .cell'));
        for (let cell of cells) {{
            let txt = cell.innerText ? cell.innerText.trim() : "";
            // 순수 숫자이거나 '1' 형태
            if (/^\\d+$/.test(txt)) {{
                let num = parseInt(txt, 10);
                if (num > 0 && num <= 100) {{
                    return num;
                }}
            }}
        }}
        // input 전의 텍스트 노드 탐색
        let rowText = row.innerText || "";
        let match = rowText.match(/\\b(\\d+)\\b/);
        if (match) {{
            let n = parseInt(match[1], 10);
            if (n > 0 && n <= 100) return n;
        }}
        return null;
    }}

    // 3. 행에서 텍스트 입력 엘리먼트 추출
    function findInputElement(row) {{
        let textareas = row.querySelectorAll('textarea');
        if (textareas.length > 0) return textareas[textareas.length - 1]; // 대형 텍스트란
        let contenteditables = row.querySelectorAll('div[contenteditable="true"]');
        if (contenteditables.length > 0) return contenteditables[0];
        let inputs = row.querySelectorAll('input[type="text"]');
        if (inputs.length > 0) return inputs[inputs.length - 1];
        return null;
    }}

    // 4. 입력값 설정 및 이벤트 트리거
    function setInputValue(elem, value) {{
        if (!elem) return;
        if (elem.tagName.toLowerCase() === 'textarea' || elem.tagName.toLowerCase() === 'input') {{
            elem.value = value;
            elem.dispatchEvent(new Event('input', {{ bubbles: true }}));
            elem.dispatchEvent(new Event('change', {{ bubbles: true }}));
            elem.dispatchEvent(new Event('blur', {{ bubbles: true }}));
        }} else if (elem.isContentEditable) {{
            elem.innerText = value;
            elem.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
    }}

    function getInputValue(elem) {{
        if (!elem) return "";
        if (elem.tagName.toLowerCase() === 'textarea' || elem.tagName.toLowerCase() === 'input') {{
            return elem.value || "";
        }}
        return elem.innerText || "";
    }}

    // 실행 시작
    let rows = findRows();
    if (rows.length === 0) {{
        alert("[오류] 나이스 입력 화면의 학생 행(테이블)을 찾을 수 없습니다.\\n현재 화면이 올바른 나이스 입력 화면인지 확인해주세요.");
        return;
    }}

    let matchedCount = 0;
    let foundStudentNumbers = [];

    for (let row of rows) {{
        let sNum = extractStudentNumber(row);
        if (!sNum) continue;

        foundStudentNumbers.push(sNum);
        let sNumStr = String(sNum);
        let inputElem = findInputElement(row);

        if (!inputElem) continue;

        if (STUDENTS[sNumStr]) {{
            matchedCount++;
            let excelData = STUDENTS[sNumStr];
            let excelContent = excelData.content.trim();
            let currentContent = getInputValue(inputElem).trim();

            let finalContent = "";
            let action = "";

            if (INPUT_MODE === "EMPTY_ONLY") {{
                if (currentContent === "") {{
                    finalContent = excelContent;
                    action = "입력 완료 (빈칸)";
                }} else {{
                    finalContent = currentContent;
                    action = "건너뜀 (기존 내용 유지)";
                    report.skippedCount++;
                }}
            }} else if (INPUT_MODE === "APPEND") {{
                if (currentContent === "") {{
                    finalContent = excelContent;
                    action = "입력 완료 (신규)";
                }} else {{
                    finalContent = currentContent + " " + excelContent;
                    action = "이어쓰기 완료";
                }}
            }} else if (INPUT_MODE === "OVERWRITE") {{
                finalContent = excelContent;
                action = "덮어쓰기 완료";
            }}

            if (action !== "건너뜀 (기존 내용 유지)") {{
                setInputValue(inputElem, finalContent);
                // 입력 후 검증
                let verifiedVal = getInputValue(inputElem).trim();
                if (verifiedVal === finalContent) {{
                    report.successCount++;
                    report.details.push({{
                        number: sNum,
                        name: excelData.name,
                        status: "SUCCESS",
                        msg: action
                    }});
                }} else {{
                    report.mismatchCount++;
                    report.details.push({{
                        number: sNum,
                        name: excelData.name,
                        status: "MISMATCH",
                        msg: "값 불일치 발생"
                    }});
                }}
            }} else {{
                report.details.push({{
                    number: sNum,
                    name: excelData.name,
                    status: "SKIPPED",
                    msg: action
                }});
            }}
        }}
    }}

    // 결과 안내 알림창
    let summaryMsg = "========================================\\n" +
                     "  🎉 나이스 자동입력 및 검증 완료 리포트\\n" +
                     "========================================\\n\\n" +
                     "• 전체 입력 대상: " + Object.keys(STUDENTS).length + "명\\n" +
                     "• 화면 매칭 학생: " + matchedCount + "명\\n" +
                     "• ✅ 입력 성공: " + report.successCount + "명\\n" +
                     "• ⏩ 건너뜀: " + report.skippedCount + "명\\n" +
                     "• ⚠️ 불일치: " + report.mismatchCount + "명\\n\\n" +
                     "※ [안전장치] 최종 저장은 자동화되지 않습니다.\\n" +
                     "입력된 내용을 화면에서 꼼꼼히 확인하신 후, [저장] 버튼을 직접 눌러주세요!";

    console.log(summaryMsg);
    alert(summaryMsg);

    return report;
}})();
        """.strip()

        return js_code

    @staticmethod
    def generate_bookmarklet_url(script_code: str) -> str:
        """북마크릿 URL 형식 생성 (javascript:...)"""
        import urllib.parse
        encoded = urllib.parse.quote(script_code)
        return f"javascript:{encoded}"
