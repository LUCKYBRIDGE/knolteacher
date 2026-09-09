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

public interface IDataShareService
{
    void ExportStudentRosterTemplate(string filePath);
    TemplateImportResult ImportStudentRosterCsv(string filePath);

    void ExportAcademicScheduleTemplate(string filePath);
    TemplateImportResult ImportAcademicScheduleCsv(string filePath);

    void ExportTimetableTemplate(string filePath);
    TemplateImportResult ImportTimetableCsv(string filePath);

    void ExportFullConfigPackage(string filePath);
    TemplateImportResult ImportFullConfigPackage(string filePath);
}

public class DataShareService : IDataShareService
{
    private readonly IConfigService _configService;
    private readonly IStudentManagerService _studentManagerService;
    private readonly ITimetableService _timetableService;
    private readonly IAcademicCalendarService _calendarService;

    private static readonly UTF8Encoding Utf8Bom = new(true);
    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
        Encoder = JavaScriptEncoder.Create(UnicodeRanges.All),
        PropertyNameCaseInsensitive = true
    };

    public DataShareService(
        IConfigService configService,
        IStudentManagerService studentManagerService,
        ITimetableService timetableService,
        IAcademicCalendarService calendarService)
    {
        _configService = configService;
        _studentManagerService = studentManagerService;
        _timetableService = timetableService;
        _calendarService = calendarService;
    }

    #region 1. 학생 명렬표 (Student Roster)
    public void ExportStudentRosterTemplate(string filePath)
    {
        var sb = new StringBuilder();
        sb.AppendLine("번호,이름,성별,아바타");

        if (_studentManagerService.Students != null && _studentManagerService.Students.Count > 0)
        {
            foreach (var s in _studentManagerService.Students)
            {
                sb.AppendLine($"{s.Number},{EscapeCsv(s.Name)},{EscapeCsv(s.Gender)},{EscapeCsv(s.AvatarId)}");
            }
        }
        else
        {
            sb.AppendLine("1,김하늘,남,avatar_01");
            sb.AppendLine("2,박바다,여,avatar_02");
            sb.AppendLine("3,이구름,남,avatar_03");
            sb.AppendLine("4,최샛별,여,avatar_04");
            sb.AppendLine("5,정햇살,남,avatar_05");
        }

        File.WriteAllText(filePath, sb.ToString(), Utf8Bom);
    }

    public TemplateImportResult ImportStudentRosterCsv(string filePath)
    {
        try
        {
            var lines = ReadLinesWithEncoding(filePath);
            if (lines.Count < 2)
            {
                return new TemplateImportResult { Success = false, Message = "파일에 데이터가 없거나 형식이 올바르지 않습니다." };
            }

            var imported = new List<StudentItem>();
            int autoNum = 1;

            for (int i = 1; i < lines.Count; i++)
            {
                var line = lines[i].Trim();
                if (string.IsNullOrWhiteSpace(line)) continue;

                var cols = SplitCsvRow(line);
                if (cols.Count < 2) continue;

                int num = autoNum;
                if (int.TryParse(cols[0].Trim(), out int parsedNum))
                {
                    num = parsedNum;
                }

                string name = cols[1].Trim();
                if (string.IsNullOrWhiteSpace(name)) continue;

                string gender = cols.Count > 2 ? cols[2].Trim() : "";
                string avatar = cols.Count > 3 ? cols[3].Trim() : "";

                imported.Add(new StudentItem
                {
                    Number = num,
                    Name = name,
                    Gender = gender,
                    AvatarId = avatar
                });

                autoNum = num + 1;
            }

            if (imported.Count == 0)
            {
                return new TemplateImportResult { Success = false, Message = "가져올 수 있는 유효한 학생 데이터가 없습니다." };
            }

            _studentManagerService.Students.Clear();
            _studentManagerService.Students.AddRange(imported.OrderBy(s => s.Number));
            _studentManagerService.SaveRoster();

            return new TemplateImportResult
            {
                Success = true,
                ItemCount = imported.Count,
                Message = $"총 {imported.Count}명의 학생 명렬표를 성공적으로 반영했습니다."
            };
        }
        catch (Exception ex)
        {
            return new TemplateImportResult { Success = false, Message = $"가져오기 실패: {ex.Message}" };
        }
    }
    #endregion

    #region 2. 학사일정 & D-Day (Academic Schedule)
    public void ExportAcademicScheduleTemplate(string filePath)
    {
        var sb = new StringBuilder();
        sb.AppendLine("날짜,일정명,휴업구분,비고");

        int year = DateTime.Today.Year;
        sb.AppendLine($"{year}-03-02,개학식 및 입학식,해당없음,신학기");
        sb.AppendLine($"{year}-05-01,개교기념일,재량휴업일,학교휴업");
        sb.AppendLine($"{year}-05-05,어린이날,공휴일,법정공휴일");
        sb.AppendLine($"{year}-07-24,여름방학식,해당없음,방학식");
        sb.AppendLine($"{year}-09-01,2학기 개학식,해당없음,개학");
        sb.AppendLine($"{year}-12-31,종업식 및 졸업식,해당없음,학년종료");

        File.WriteAllText(filePath, sb.ToString(), Utf8Bom);
    }

    public TemplateImportResult ImportAcademicScheduleCsv(string filePath)
    {
        try
        {
            var lines = ReadLinesWithEncoding(filePath);
            if (lines.Count < 2)
            {
                return new TemplateImportResult { Success = false, Message = "파일에 데이터가 없거나 형식이 올바르지 않습니다." };
            }

            var imported = new List<AcademicScheduleItem>();

            for (int i = 1; i < lines.Count; i++)
            {
                var line = lines[i].Trim();
                if (string.IsNullOrWhiteSpace(line)) continue;

                var cols = SplitCsvRow(line);
                if (cols.Count < 2) continue;

                string dateRaw = cols[0].Trim().Replace(".", "-").Replace("/", "-");
                if (!DateTime.TryParse(dateRaw, out DateTime date)) continue;

                string eventName = cols[1].Trim();
                if (string.IsNullOrWhiteSpace(eventName)) continue;

                string dayType = "해당없음";
                if (cols.Count > 2)
                {
                    string h = cols[2].Trim();
                    if (h == "Y" || h == "휴업" || h == "휴업일" || h == "재량휴업일") dayType = "휴업일";
                    else if (h == "공휴일") dayType = "공휴일";
                }

                string content = cols.Count > 3 ? cols[3].Trim() : "";

                imported.Add(new AcademicScheduleItem
                {
                    RawDate = date.ToString("yyyyMMdd"),
                    EventName = eventName,
                    AcademicYear = (date.Month < 3 ? date.Year - 1 : date.Year).ToString(),
                    SubtractionDayType = dayType,
                    EventContent = content
                });
            }

            if (imported.Count == 0)
            {
                return new TemplateImportResult { Success = false, Message = "가져올 수 있는 유효한 학사일정 데이터가 없습니다." };
            }

            string cachePath = Path.Combine(_configService.ConfigDir, "academic_schedule_cache.json");
            var existing = new List<AcademicScheduleItem>();
            if (File.Exists(cachePath))
            {
                try
                {
                    string oldJson = File.ReadAllText(cachePath);
                    var oldList = JsonSerializer.Deserialize<List<AcademicScheduleItem>>(oldJson, JsonOpts);
                    if (oldList != null) existing = oldList;
                }
                catch { }
            }

            foreach (var item in imported)
            {
                existing.RemoveAll(e => e.RawDate == item.RawDate && e.EventName == item.EventName);
                existing.Add(item);
            }

            existing = existing.OrderBy(e => e.RawDate).ToList();
            string newJson = JsonSerializer.Serialize(existing, JsonOpts);
            File.WriteAllText(cachePath, newJson, Utf8Bom);

            return new TemplateImportResult
            {
                Success = true,
                ItemCount = imported.Count,
                Message = $"총 {imported.Count}개의 학사일정을 성공적으로 반영했습니다."
            };
        }
        catch (Exception ex)
        {
            return new TemplateImportResult { Success = false, Message = $"가져오기 실패: {ex.Message}" };
        }
    }
    #endregion

    #region 3. 주간 시간표 (Weekly Timetable)
    public void ExportTimetableTemplate(string filePath)
    {
        var sb = new StringBuilder();
        sb.AppendLine("교시,월,화,수,목,금");
        sb.AppendLine("1,국어,수학,국어,영어,사회");
        sb.AppendLine("2,수학,국어,체육,음악,과학");
        sb.AppendLine("3,사회,과학,수학,국어,미술");
        sb.AppendLine("4,과학,사회,도덕,수학,미술");
        sb.AppendLine("5,체육,영어,실과,동아리,도덕");
        sb.AppendLine("6,음악,창체,실과,동아리,");

        File.WriteAllText(filePath, sb.ToString(), Utf8Bom);
    }

    public TemplateImportResult ImportTimetableCsv(string filePath)
    {
        try
        {
            var lines = ReadLinesWithEncoding(filePath);
            if (lines.Count < 2)
            {
                return new TemplateImportResult { Success = false, Message = "시간표 데이터가 부족합니다." };
            }

            string[] dayKeys = { "mon", "tue", "wed", "thu", "fri" };
            var table = new Dictionary<string, List<Dictionary<string, string>>>();
            foreach (var dk in dayKeys) table[dk] = new List<Dictionary<string, string>>();

            int rowCount = 0;
            for (int i = 1; i < lines.Count; i++)
            {
                var line = lines[i].Trim();
                if (string.IsNullOrWhiteSpace(line)) continue;

                var cols = SplitCsvRow(line);
                if (cols.Count < 2) continue;

                rowCount++;
                for (int d = 0; d < 5; d++)
                {
                    string subj = (d + 1 < cols.Count) ? cols[d + 1].Trim() : "";
                    table[dayKeys[d]].Add(new Dictionary<string, string>
                    {
                        { "subject", subj },
                        { "tag", "담임" }
                    });
                }
            }

            if (rowCount == 0)
            {
                return new TemplateImportResult { Success = false, Message = "가져올 수 있는 시간표 행이 없습니다." };
            }

            string timetableFile = Path.Combine(_configService.ConfigDir, "custom_timetable.json");
            string json = JsonSerializer.Serialize(table, JsonOpts);
            File.WriteAllText(timetableFile, json, Utf8Bom);

            return new TemplateImportResult
            {
                Success = true,
                ItemCount = rowCount,
                Message = $"총 {rowCount}개 교시의 주간 시간표를 성공적으로 반영했습니다."
            };
        }
        catch (Exception ex)
        {
            return new TemplateImportResult { Success = false, Message = $"시간표 가져오기 실패: {ex.Message}" };
        }
    }
    #endregion

    #region 4. 전체 설정 공유 패키지 (Full Config Package)
    public void ExportFullConfigPackage(string filePath)
    {
        var pkg = new DataSharePackage
        {
            MainWidgetLayout = _configService.MainWidgetLayout,
            TimetableSettings = _configService.TimetableSettings,
            PeriodAlarmConfig = _configService.PeriodAlarmConfig,
            BoardSetStore = _configService.BoardSetStore,
            Students = _studentManagerService.Students
        };

        string cachePath = Path.Combine(_configService.ConfigDir, "academic_schedule_cache.json");
        if (File.Exists(cachePath))
        {
            try
            {
                string json = File.ReadAllText(cachePath);
                pkg.AcademicSchedules = JsonSerializer.Deserialize<List<AcademicScheduleItem>>(json, JsonOpts);
            }
            catch { }
        }

        string pkgJson = JsonSerializer.Serialize(pkg, JsonOpts);
        File.WriteAllText(filePath, pkgJson, Utf8Bom);
    }

    public TemplateImportResult ImportFullConfigPackage(string filePath)
    {
        try
        {
            string json = File.ReadAllText(filePath, Encoding.UTF8);
            var pkg = JsonSerializer.Deserialize<DataSharePackage>(json, JsonOpts);
            if (pkg == null)
            {
                return new TemplateImportResult { Success = false, Message = "설정 패키지 파일을 파싱할 수 없습니다." };
            }

            if (pkg.MainWidgetLayout != null)
            {
                _configService.MainWidgetLayout = pkg.MainWidgetLayout;
                _configService.SaveMainWidgetLayout();
            }

            if (pkg.PeriodAlarmConfig != null)
            {
                _configService.PeriodAlarmConfig = pkg.PeriodAlarmConfig;
                _configService.SavePeriodAlarmConfig();
            }

            if (pkg.BoardSetStore != null)
            {
                _configService.BoardSetStore = pkg.BoardSetStore;
                _configService.SaveBoardSetStore();
            }

            if (pkg.Students != null && pkg.Students.Count > 0)
            {
                _studentManagerService.Students.Clear();
                _studentManagerService.Students.AddRange(pkg.Students);
                _studentManagerService.SaveRoster();
            }

            if (pkg.AcademicSchedules != null && pkg.AcademicSchedules.Count > 0)
            {
                string cachePath = Path.Combine(_configService.ConfigDir, "academic_schedule_cache.json");
                File.WriteAllText(cachePath, JsonSerializer.Serialize(pkg.AcademicSchedules, JsonOpts), Utf8Bom);
            }

            return new TemplateImportResult
            {
                Success = true,
                Message = "놀티쳐 맞춤 설정 패키지를 성공적으로 불러와 적용했습니다."
            };
        }
        catch (Exception ex)
        {
            return new TemplateImportResult { Success = false, Message = $"설정 패키지 가져오기 실패: {ex.Message}" };
        }
    }
    #endregion

    #region Helpers
    private static List<string> ReadLinesWithEncoding(string filePath)
    {
        byte[] bytes = File.ReadAllBytes(filePath);

        if (bytes.Length >= 3 && bytes[0] == 0xEF && bytes[1] == 0xBB && bytes[2] == 0xBF)
        {
            return File.ReadAllLines(filePath, Encoding.UTF8).ToList();
        }

        try
        {
            string textUtf8 = new UTF8Encoding(false, true).GetString(bytes);
            return textUtf8.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None).ToList();
        }
        catch
        {
            Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
            var euckr = Encoding.GetEncoding(949);
            string textAnsi = euckr.GetString(bytes);
            return textAnsi.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None).ToList();
        }
    }

    private static List<string> SplitCsvRow(string row)
    {
        var result = new List<string>();
        bool inQuotes = false;
        var cur = new StringBuilder();

        for (int i = 0; i < row.Length; i++)
        {
            char c = row[i];
            if (c == '"')
            {
                if (inQuotes && i + 1 < row.Length && row[i + 1] == '"')
                {
                    cur.Append('"');
                    i++;
                }
                else
                {
                    inQuotes = !inQuotes;
                }
            }
            else if (c == ',' && !inQuotes)
            {
                result.Add(cur.ToString());
                cur.Clear();
            }
            else
            {
                cur.Append(c);
            }
        }
        result.Add(cur.ToString());
        return result;
    }

    private static string EscapeCsv(string? val)
    {
        if (string.IsNullOrEmpty(val)) return "";
        if (val.Contains(',') || val.Contains('"') || val.Contains('\n') || val.Contains('\r'))
        {
            return $"\"{val.Replace("\"", "\"\"")}\"";
        }
        return val;
    }
    #endregion
}
