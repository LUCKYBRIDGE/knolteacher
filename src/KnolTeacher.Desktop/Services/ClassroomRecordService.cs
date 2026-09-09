using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Unicode;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Services;

public interface IClassroomRecordService
{
    List<ChecklistGroup> Checklists { get; }
    List<CumulativeRecordItem> CumulativeRecords { get; }

    event Action? OnChecklistsChanged;
    event Action? OnCumulativeRecordsChanged;

    void LoadAll();
    void SaveAll();
    void SaveChecklists();
    void SaveCumulativeRecords();

    // Checklist
    ChecklistGroup CreateChecklist(string title, string category, IEnumerable<StudentItem> students, string? targetDate = null);
    void DeleteChecklist(string id);
    void ToggleChecklistItemStatus(string checklistId, int studentNumber);
    void SetChecklistItemStatus(string checklistId, int studentNumber, string status, string? note = null);

    // Cumulative Records
    void AddCumulativeRecord(int studentNumber, string studentName, DateTime date, string category, string content, string tag);
    void DeleteCumulativeRecord(string id);
    string GenerateNeisSynthesisText(int studentNumber);

    // Templates & CSV Export
    string GetRosterCsvTemplate();
    string GetChecklistCsvTemplate(ChecklistGroup? group = null);
    string GetCumulativeRecordCsvTemplate(int? studentNumber = null);
    void ExportCsvFile(string filePath, string csvContent);
    List<StudentItem> ParsePastedRosterText(string pastedText);
}

public class ClassroomRecordService : IClassroomRecordService
{
    private readonly IConfigService _configService;
    private readonly string _checklistFilePath;
    private readonly string _cumulativeFilePath;

    private readonly JsonSerializerOptions _jsonOptions = new()
    {
        WriteIndented = true,
        Encoder = JavaScriptEncoder.Create(UnicodeRanges.All)
    };

    public List<ChecklistGroup> Checklists { get; private set; } = new();
    public List<CumulativeRecordItem> CumulativeRecords { get; private set; } = new();

    public event Action? OnChecklistsChanged;
    public event Action? OnCumulativeRecordsChanged;

    public ClassroomRecordService(IConfigService configService)
    {
        _configService = configService;
        _checklistFilePath = Path.Combine(_configService.ConfigDir, "student_checklists.json");
        _cumulativeFilePath = Path.Combine(_configService.ConfigDir, "student_cumulative_records.json");

        LoadAll();
    }

    public void LoadAll()
    {
        LoadChecklists();
        LoadCumulativeRecords();
    }

    public void SaveAll()
    {
        SaveChecklists();
        SaveCumulativeRecords();
    }

    private void LoadChecklists()
    {
        try
        {
            if (File.Exists(_checklistFilePath))
            {
                string json = File.ReadAllText(_checklistFilePath);
                var loaded = JsonSerializer.Deserialize<List<ChecklistGroup>>(json, _jsonOptions);
                if (loaded != null)
                {
                    Checklists = loaded;
                    return;
                }
            }
        }
        catch { }

        // Sample default checklists for teachers
        Checklists = new List<ChecklistGroup>();
    }

    public void SaveChecklists()
    {
        try
        {
            Directory.CreateDirectory(_configService.ConfigDir);
            string json = JsonSerializer.Serialize(Checklists, _jsonOptions);
            File.WriteAllText(_checklistFilePath, json);
        }
        catch { }

        OnChecklistsChanged?.Invoke();
    }

    private void LoadCumulativeRecords()
    {
        try
        {
            if (File.Exists(_cumulativeFilePath))
            {
                string json = File.ReadAllText(_cumulativeFilePath);
                var loaded = JsonSerializer.Deserialize<List<CumulativeRecordItem>>(json, _jsonOptions);
                if (loaded != null)
                {
                    CumulativeRecords = loaded;
                    return;
                }
            }
        }
        catch { }

        CumulativeRecords = new List<CumulativeRecordItem>();
    }

    public void SaveCumulativeRecords()
    {
        try
        {
            Directory.CreateDirectory(_configService.ConfigDir);
            string json = JsonSerializer.Serialize(CumulativeRecords, _jsonOptions);
            File.WriteAllText(_cumulativeFilePath, json);
        }
        catch { }

        OnCumulativeRecordsChanged?.Invoke();
    }

    public ChecklistGroup CreateChecklist(string title, string category, IEnumerable<StudentItem> students, string? targetDate = null)
    {
        var group = new ChecklistGroup
        {
            Title = string.IsNullOrWhiteSpace(title) ? "새 과제 점검" : title.Trim(),
            Category = string.IsNullOrWhiteSpace(category) ? "과제" : category.Trim(),
            TargetDate = string.IsNullOrWhiteSpace(targetDate) ? DateTime.Today.ToString("yyyy-MM-dd") : targetDate.Trim(),
            Items = students.OrderBy(s => s.Number).Select(s => new ChecklistItem
            {
                StudentNumber = s.Number,
                StudentName = s.Name,
                Status = "Incomplete",
                Note = string.Empty
            }).ToList()
        };

        Checklists.Insert(0, group);
        SaveChecklists();
        return group;
    }

    public void DeleteChecklist(string id)
    {
        var found = Checklists.FirstOrDefault(c => c.Id == id);
        if (found != null)
        {
            Checklists.Remove(found);
            SaveChecklists();
        }
    }

    public void ToggleChecklistItemStatus(string checklistId, int studentNumber)
    {
        var checklist = Checklists.FirstOrDefault(c => c.Id == checklistId);
        if (checklist == null) return;

        var item = checklist.Items.FirstOrDefault(i => i.StudentNumber == studentNumber);
        if (item == null) return;

        // Cycle: Incomplete (X) -> Completed (O) -> Pending (△) -> Incomplete (X)
        item.Status = item.Status switch
        {
            "Incomplete" => "Completed",
            "Completed" => "Pending",
            _ => "Incomplete"
        };

        SaveChecklists();
    }

    public void SetChecklistItemStatus(string checklistId, int studentNumber, string status, string? note = null)
    {
        var checklist = Checklists.FirstOrDefault(c => c.Id == checklistId);
        if (checklist == null) return;

        var item = checklist.Items.FirstOrDefault(i => i.StudentNumber == studentNumber);
        if (item == null) return;

        item.Status = status;
        if (note != null) item.Note = note;

        SaveChecklists();
    }

    public void AddCumulativeRecord(int studentNumber, string studentName, DateTime date, string category, string content, string tag)
    {
        if (string.IsNullOrWhiteSpace(content)) return;

        var record = new CumulativeRecordItem
        {
            StudentNumber = studentNumber,
            StudentName = studentName,
            Date = date,
            Category = category,
            Content = content.Trim(),
            Tag = tag
        };

        CumulativeRecords.Insert(0, record);
        SaveCumulativeRecords();
    }

    public void DeleteCumulativeRecord(string id)
    {
        var found = CumulativeRecords.FirstOrDefault(r => r.Id == id);
        if (found != null)
        {
            CumulativeRecords.Remove(found);
            SaveCumulativeRecords();
        }
    }

    public string GenerateNeisSynthesisText(int studentNumber)
    {
        var records = CumulativeRecords
            .Where(r => r.StudentNumber == studentNumber)
            .OrderBy(r => r.Date)
            .ToList();

        if (records.Count == 0)
        {
            return "등록된 누가기록 관찰 내용이 없습니다.";
        }

        var sb = new StringBuilder();
        var studentName = records.First().StudentName;
        sb.AppendLine($"[나이스 행동특성 및 종합의견 참고자료 - {studentNumber}번 {studentName}]");

        var grouped = records.GroupBy(r => r.Category);
        foreach (var grp in grouped)
        {
            sb.AppendLine($"\n■ {grp.Key}:");
            foreach (var item in grp)
            {
                sb.AppendLine($"- ({item.Date:MM/dd}) {item.Content}");
            }
        }

        sb.AppendLine("\n■ 요약 평어 초안:");
        var keyObservations = records.TakeLast(3).Select(r => r.Content);
        sb.AppendLine(string.Join(" 또한, ", keyObservations));

        return sb.ToString();
    }

    public string GetRosterCsvTemplate()
    {
        var sb = new StringBuilder();
        sb.AppendLine("번호,이름,성별,1인1역,생년월일,보호자연락처,특이사항메모");
        sb.AppendLine("1,김하늘,여,칠판도우미,2014-03-12,010-1234-5678,우유 알레르기 있음");
        sb.AppendLine("2,이바다,남,체육부장,2014-05-24,010-9876-5432,시력 안경 착용");
        sb.AppendLine("3,박민준,남,청소반장,2014-07-09,010-3333-7777,");
        sb.AppendLine("4,정서연,여,도서도우미,2014-11-18,010-5555-8888,손목 약함");
        return sb.ToString();
    }

    public string GetChecklistCsvTemplate(ChecklistGroup? group = null)
    {
        var sb = new StringBuilder();
        sb.AppendLine("번호,이름,확인상태(O:완료/X:미제출/△:보완),비고");

        if (group != null && group.Items.Count > 0)
        {
            foreach (var item in group.Items.OrderBy(i => i.StudentNumber))
            {
                sb.AppendLine($"{item.StudentNumber},{item.StudentName},{item.StatusSymbol},{item.Note}");
            }
        }
        else
        {
            sb.AppendLine("1,김하늘,O,제출완료");
            sb.AppendLine("2,이바다,X,내일 아침 제출 예정");
            sb.AppendLine("3,박민준,△,수학익힘 35쪽 2번 미해결");
        }

        return sb.ToString();
    }

    public string GetCumulativeRecordCsvTemplate(int? studentNumber = null)
    {
        var sb = new StringBuilder();
        sb.AppendLine("날짜,번호,이름,영역,관찰내용,태그(일반/칭찬/지도필요/상담완료)");

        var filtered = CumulativeRecords.AsEnumerable();
        if (studentNumber.HasValue)
        {
            filtered = filtered.Where(r => r.StudentNumber == studentNumber.Value);
        }

        var list = filtered.OrderBy(r => r.Date).ToList();
        if (list.Count > 0)
        {
            foreach (var r in list)
            {
                sb.AppendLine($"{r.Date:yyyy-MM-dd},{r.StudentNumber},{r.StudentName},{r.Category},\"{r.Content.Replace("\"", "\"\"")}\",{r.Tag}");
            }
        }
        else
        {
            sb.AppendLine($"{DateTime.Today:yyyy-MM-dd},1,김하늘,행동특성,\"학급 칠판도우미 역할을 성실히 수행하며 친구들을 솔선수범하여 도움.\",칭찬/우수");
            sb.AppendLine($"{DateTime.Today:yyyy-MM-dd},2,이바다,수업태도,\"수학 분수의 나눗셈 단원에서 뛰어난 문제해결력을 보이며 모둠원들에게 설명해줌.\",칭찬/우수");
            sb.AppendLine($"{DateTime.Today:yyyy-MM-dd},3,박민준,생활지도,\"쉬는 시간 복도에서 뛰지 않도록 안전 수칙을 상기시키고 지도함.\",지도필요");
        }

        return sb.ToString();
    }

    public void ExportCsvFile(string filePath, string csvContent)
    {
        // Save with UTF-8 BOM so Excel opens Korean text cleanly without garbled characters
        var encoding = new UTF8Encoding(true);
        File.WriteAllText(filePath, csvContent, encoding);
    }

    public List<StudentItem> ParsePastedRosterText(string pastedText)
    {
        var result = new List<StudentItem>();
        if (string.IsNullOrWhiteSpace(pastedText)) return result;

        var lines = pastedText.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
        int autoNum = 1;

        foreach (var rawLine in lines)
        {
            var line = rawLine.Trim();
            if (string.IsNullOrWhiteSpace(line)) continue;

            // Split by tab, comma, or multiple spaces
            var parts = line.Split(new[] { '\t', ',' }, StringSplitOptions.TrimEntries);
            if (parts.Length == 1)
            {
                // Single column: could be "1 김철수" or just "김철수"
                var subParts = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                if (subParts.Length >= 2 && int.TryParse(subParts[0], out int num))
                {
                    result.Add(new StudentItem
                    {
                        Number = num,
                        Name = subParts[1].Trim(),
                        Gender = subParts.Length > 2 ? subParts[2] : string.Empty
                    });
                }
                else
                {
                    result.Add(new StudentItem
                    {
                        Number = autoNum++,
                        Name = line
                    });
                }
            }
            else
            {
                // Multi-column (e.g. from Excel: 번호, 이름, 성별, 역할...)
                int number = autoNum;
                string name = parts[0];
                string gender = string.Empty;
                string role = string.Empty;

                if (int.TryParse(parts[0], out int parsedNum))
                {
                    number = parsedNum;
                    name = parts.Length > 1 ? parts[1] : $"학생 {number}";
                    gender = parts.Length > 2 ? parts[2] : string.Empty;
                    role = parts.Length > 3 ? parts[3] : string.Empty;
                }
                else
                {
                    name = parts[0];
                    gender = parts.Length > 1 ? parts[1] : string.Empty;
                    role = parts.Length > 2 ? parts[2] : string.Empty;
                    number = autoNum++;
                }

                result.Add(new StudentItem
                {
                    Number = number,
                    Name = name,
                    Gender = gender,
                    Role = role
                });
            }
        }

        return result.OrderBy(s => s.Number).ToList();
    }
}
