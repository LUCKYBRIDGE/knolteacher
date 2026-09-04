using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using KnolTeacher.Desktop.Models;
using MiniExcelLibs;

namespace KnolTeacher.Desktop.Services;

public interface INeisCommentBatchService
{
    void GenerateExcelTemplate(string filePath);
    List<NeisStudentComment> ParseExcelFile(string filePath);
    List<NeisStudentComment> ParseClipboardText(string text);
    string GenerateNeisConsoleScript(List<NeisStudentComment> comments, string pageType);
}

public class NeisCommentBatchService : INeisCommentBatchService
{
    public void GenerateExcelTemplate(string filePath)
    {
        var sampleRows = new List<Dictionary<string, object>>
        {
            new() { { "번호", 1 }, { "성명", "김도윤" }, { "평어내용", "지적 호기심이 매우 높고 자신의 생각을 논리적으로 표현하는 능력이 뛰어나며 모든 교과에서 우수한 성취를 보임." } },
            new() { { "번호", 2 }, { "성명", "김도현" }, { "평어내용", "자신의 생각을 논리적으로 표현하는 능력이 뛰어나며 재치 있는 말로 주변 친구들에게 즐거움을 주는 등 의사소통을 원활하게 잘함." } },
            new() { { "번호", 3 }, { "성명", "김리나" }, { "평어내용", "자신의 생각을 친구들에게 조리 있게 전달하며 교우 관계가 매우 원만하여 무리에 잘 어우러지는 학생임." } },
            new() { { "번호", 4 }, { "성명", "김승권" }, { "평어내용", "스스로 학습 목표를 세우고 실천하는 자기 주도적인 태도가 돋보이며 어떤 일이든 끝까지 스스로 해내려는 책임감이 강함." } },
            new() { { "번호", 5 }, { "성명", "김서연" }, { "평어내용", "자신의 생각을 논리적으로 정리하여 차분하게 발표하며 매 수업 시간마다 집중하여 참여함." } }
        };

        MiniExcel.SaveAs(filePath, sampleRows, overwriteFile: true);
    }

    public List<NeisStudentComment> ParseExcelFile(string filePath)
    {
        var result = new List<NeisStudentComment>();
        if (!File.Exists(filePath)) return result;

        try
        {
            var rows = MiniExcel.Query(filePath).ToList();
            if (rows.Count == 0) return result;

            int numCol = -1;
            int nameCol = -1;
            int contentCol = -1;
            int headerRowIdx = -1;

            for (int r = 0; r < Math.Min(5, rows.Count); r++)
            {
                var rowDict = (IDictionary<string, object>)rows[r];
                var values = rowDict.Values.Select(v => v?.ToString()?.Trim() ?? "").ToList();

                for (int c = 0; c < values.Count; c++)
                {
                    string header = values[c];
                    if (header.Contains("번호") || header.Equals("No", StringComparison.OrdinalIgnoreCase) || header.Equals("순번"))
                        numCol = c;
                    else if (header.Contains("성명") || header.Contains("이름") || header.Equals("학생명"))
                        nameCol = c;
                    else if (header.Contains("평어") || header.Contains("종합의견") || header.Contains("행동특성") || header.Contains("내용") || header.Contains("의견"))
                        contentCol = c;
                }

                if (numCol >= 0 && (nameCol >= 0 || contentCol >= 0))
                {
                    headerRowIdx = r;
                    break;
                }
            }

            if (numCol < 0) numCol = 0;
            if (nameCol < 0) nameCol = 1;
            if (contentCol < 0) contentCol = 2;

            int startRow = (headerRowIdx >= 0) ? headerRowIdx + 1 : 1;

            for (int r = startRow; r < rows.Count; r++)
            {
                var rowDict = (IDictionary<string, object>)rows[r];
                var values = rowDict.Values.Select(v => v?.ToString()?.Trim() ?? "").ToList();

                if (values.Count <= numCol) continue;

                string rawNum = values[numCol];
                if (!int.TryParse(rawNum, out int number))
                {
                    if (double.TryParse(rawNum, out double dNum)) number = (int)dNum;
                    else continue;
                }

                if (number <= 0) continue;

                string name = (nameCol >= 0 && nameCol < values.Count) ? values[nameCol] : "";
                string content = (contentCol >= 0 && contentCol < values.Count) ? values[contentCol] : "";

                result.Add(new NeisStudentComment
                {
                    StudentNumber = number,
                    StudentName = name,
                    CommentText = content
                });
            }
        }
        catch { }

        return result.OrderBy(x => x.StudentNumber).ToList();
    }

    public List<NeisStudentComment> ParseClipboardText(string text)
    {
        var result = new List<NeisStudentComment>();
        if (string.IsNullOrWhiteSpace(text)) return result;

        var lines = text.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.RemoveEmptyEntries);
        if (lines.Length == 0) return result;

        int numCol = -1;
        int nameCol = -1;
        int contentCol = -1;
        int startRow = 0;

        var firstCols = lines[0].Split('\t').Select(c => c.Trim()).ToList();
        for (int c = 0; c < firstCols.Count; c++)
        {
            string h = firstCols[c];
            if (h.Contains("번호") || h.Equals("No", StringComparison.OrdinalIgnoreCase) || h.Equals("순번")) numCol = c;
            else if (h.Contains("성명") || h.Contains("이름") || h.Equals("학생명")) nameCol = c;
            else if (h.Contains("평어") || h.Contains("종합의견") || h.Contains("행동특성") || h.Contains("내용") || h.Contains("의견")) contentCol = c;
        }

        if (numCol >= 0 && (nameCol >= 0 || contentCol >= 0))
        {
            startRow = 1;
        }
        else
        {
            numCol = 0;
            if (firstCols.Count >= 3)
            {
                nameCol = 1;
                contentCol = 2;
            }
            else if (firstCols.Count == 2)
            {
                contentCol = 1;
            }
        }

        for (int r = startRow; r < lines.Length; r++)
        {
            var cols = lines[r].Split('\t');
            if (cols.Length <= numCol) continue;

            string rawNum = cols[numCol].Trim();
            if (!int.TryParse(rawNum, out int number))
            {
                if (double.TryParse(rawNum, out double d)) number = (int)d;
                else continue;
            }

            if (number <= 0) continue;

            string name = (nameCol >= 0 && nameCol < cols.Length) ? cols[nameCol].Trim() : "";
            string content = (contentCol >= 0 && contentCol < cols.Length) ? cols[contentCol].Trim() : "";

            result.Add(new NeisStudentComment
            {
                StudentNumber = number,
                StudentName = name,
                CommentText = content
            });
        }

        return result.OrderBy(x => x.StudentNumber).ToList();
    }

    public string GenerateNeisConsoleScript(List<NeisStudentComment> comments, string pageType)
    {
        var dict = new Dictionary<string, object>();
        foreach (var c in comments)
        {
            if (c.StudentNumber > 0 && !string.IsNullOrWhiteSpace(c.CommentText))
            {
                dict[c.StudentNumber.ToString()] = new
                {
                    name = c.StudentName,
                    content = c.CommentText
                };
            }
        }

        string payloadJson = JsonSerializer.Serialize(dict, new JsonSerializerOptions { WriteIndented = false });

        return $@"(function() {{
    const STUDENTS = {payloadJson};
    console.log('%c[놀티쳐 나이스 일괄입력] 시작 (대상 학생: ' + Object.keys(STUDENTS).length + '명)', 'color:#0284C7; font-size:14px; font-weight:bold;');

    let successCount = 0;
    let skippedCount = 0;

    let allRows = Array.from(document.querySelectorAll('tr, div[role=""row""], .grid-row, .w2grid_row'));
    let matchedRows = [];

    for (let row of allRows) {{
        let hasInput = row.querySelector('textarea, input[type=""text""], div[contenteditable=""true""]');
        if (hasInput) matchedRows.push(row);
    }}

    console.log('발견된 나이스 입력 행 수: ' + matchedRows.length);

    for (let row of matchedRows) {{
        let num = null;
        let cells = Array.from(row.querySelectorAll('td, div[role=""gridcell""], .w2grid_cell, .cell'));
        for (let cell of cells) {{
            let txt = cell.innerText ? cell.innerText.trim() : '';
            if (/^\d+$/.test(txt)) {{
                let n = parseInt(txt, 10);
                if (n > 0 && n <= 100) {{ num = n; break; }}
            }}
        }}

        if (!num) {{
            let rowText = row.innerText || '';
            let match = rowText.match(/(\d+)/);
            if (match) {{
                let n = parseInt(match[1], 10);
                if (n > 0 && n <= 100) num = n;
            }}
        }}

        if (!num || !STUDENTS[String(num)]) continue;

        let studentData = STUDENTS[String(num)];
        let targetTextarea = row.querySelector('textarea');
        if (!targetTextarea) targetTextarea = row.querySelector('input[type=""text""]');
        if (!targetTextarea) targetTextarea = row.querySelector('div[contenteditable=""true""]');

        if (targetTextarea) {{
            let textToSet = studentData.content;
            if (targetTextarea.tagName.toLowerCase() === 'textarea' || targetTextarea.tagName.toLowerCase() === 'input') {{
                targetTextarea.value = textToSet;
                targetTextarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                targetTextarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                targetTextarea.dispatchEvent(new Event('blur', {{ bubbles: true }}));
            }} else {{
                targetTextarea.innerText = textToSet;
                targetTextarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
            successCount++;
            console.log('✅ [' + num + '번 ' + studentData.name + '] 입력 완료 (' + textToSet.length + '자)');
        }} else {{
            skippedCount++;
        }}
    }}

    alert('🎉 [놀티쳐 나이스 일괄입력 완료]\n\n' + successCount + '명의 평어가 정상 입력되었습니다.\n내용을 확인하신 후 나이스 상단의 [저장] 버튼을 클릭해 주세요!');
}})();";
    }
}
