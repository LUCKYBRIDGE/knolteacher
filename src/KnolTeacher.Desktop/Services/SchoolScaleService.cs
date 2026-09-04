using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Services;

public interface ISchoolScaleService
{
    Task<List<SchoolSearchResultItem>> SearchSchoolsAsync(string keyword, string? officeCode = null, int maxResults = 50);
    Task<SchoolScaleDetail?> GetSchoolScaleDetailAsync(SchoolSearchResultItem school, int? academicYear = null);
}

public class SchoolScaleService : ISchoolScaleService
{
    private readonly IConfigService _configService;
    private static readonly HttpClient _httpClient = new()
    {
        Timeout = TimeSpan.FromSeconds(8)
    };

    private const string BaseUrl = "https://open.neis.go.kr/hub";

    public SchoolScaleService(IConfigService configService)
    {
        _configService = configService;
    }

    public async Task<List<SchoolSearchResultItem>> SearchSchoolsAsync(string keyword, string? officeCode = null, int maxResults = 50)
    {
        var results = new List<SchoolSearchResultItem>();
        if (string.IsNullOrWhiteSpace(keyword)) return results;

        string trimmed = keyword.Trim();
        string encoded = Uri.EscapeDataString(trimmed);
        string apiKey = _configService.NeisConfig?.ApiKey ?? string.Empty;

        string url = $"{BaseUrl}/schoolInfo?Type=json&pIndex=1&pSize=100&SCHUL_NM={encoded}";
        if (!string.IsNullOrEmpty(officeCode) && officeCode != "ALL")
        {
            url += $"&ATPT_OFCDC_SC_CODE={officeCode}";
        }
        if (!string.IsNullOrEmpty(apiKey))
        {
            url += $"&KEY={apiKey}";
        }

        try
        {
            string json = await _httpClient.GetStringAsync(url);
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            if (root.TryGetProperty("schoolInfo", out var schoolArray) && schoolArray.GetArrayLength() > 1)
            {
                var rows = schoolArray[1].GetProperty("row");
                foreach (var row in rows.EnumerateArray())
                {
                    var item = new SchoolSearchResultItem
                    {
                        SchoolCode = GetStringProp(row, "SD_SCHUL_CODE"),
                        OfficeCode = GetStringProp(row, "ATPT_OFCDC_SC_CODE"),
                        OfficeName = GetStringProp(row, "ATPT_OFCDC_SC_NM"),
                        SchoolName = GetStringProp(row, "SCHUL_NM"),
                        SchoolType = GetStringProp(row, "SCHUL_KND_SC_NM"),
                        LocationName = GetStringProp(row, "LCTN_SC_NM"),
                        JurisdictionName = GetStringProp(row, "JU_ORG_NM"),
                        FondType = GetStringProp(row, "FOND_SC_NM"),
                        RoadAddress = GetStringProp(row, "ORG_RDNMA"),
                        TelNo = GetStringProp(row, "ORG_TELNO"),
                        FaxNo = GetStringProp(row, "ORG_FAXNO"),
                        HomePage = GetStringProp(row, "HMPG_ADRES"),
                        CoEduType = GetStringProp(row, "COEDU_SC_NM"),
                        FoundationDate = GetStringProp(row, "FOND_YMD"),
                        Anniversary = GetStringProp(row, "FOAS_MEMRD")
                    };

                    results.Add(item);
                    if (results.Count >= maxResults) break;
                }
            }
        }
        catch (Exception ex)
        {
            App.BootLog($"[SchoolScaleService.SearchSchoolsAsync] Error: {ex.Message}");
        }

        return results;
    }

    public async Task<SchoolScaleDetail?> GetSchoolScaleDetailAsync(SchoolSearchResultItem school, int? academicYear = null)
    {
        if (school == null || string.IsNullOrEmpty(school.SchoolCode) || string.IsNullOrEmpty(school.OfficeCode))
            return null;

        int targetYear = academicYear ?? DateTime.Today.Year;
        string apiKey = _configService.NeisConfig?.ApiKey ?? string.Empty;

        // 1. Try querying total classes for targetYear, fallback to targetYear - 1 if 0 classes found
        int totalClassCount = await QueryClassTotalCountAsync(school.OfficeCode, school.SchoolCode, targetYear, apiKey);
        if (totalClassCount == 0 && targetYear == DateTime.Today.Year)
        {
            int fallbackCount = await QueryClassTotalCountAsync(school.OfficeCode, school.SchoolCode, targetYear - 1, apiKey);
            if (fallbackCount > 0)
            {
                targetYear -= 1;
                totalClassCount = fallbackCount;
            }
        }

        var detail = new SchoolScaleDetail
        {
            SchoolInfo = school,
            AcademicYear = targetYear,
            TotalClassCount = totalClassCount
        };

        // Determine grades to query
        int maxGrade = 6;
        if (school.SchoolType.Contains("중학교") || school.SchoolType.Contains("고등학교"))
        {
            maxGrade = 3;
        }

        var gradeItems = new List<GradeClassCountItem>();
        int gradeClassSum = 0;

        // Query per grade
        for (int g = 1; g <= maxGrade; g++)
        {
            int count = await QueryGradeClassCountAsync(school.OfficeCode, school.SchoolCode, targetYear, g, apiKey);
            gradeClassSum += count;
            gradeItems.Add(new GradeClassCountItem
            {
                Grade = g.ToString(),
                GradeName = $"{g}학년",
                ClassCount = count
            });
        }

        // Special classes = Total - sum of standard grades
        int specialClasses = Math.Max(0, totalClassCount - gradeClassSum);
        detail.SpecialClassCount = specialClasses;
        if (specialClasses > 0)
        {
            gradeItems.Add(new GradeClassCountItem
            {
                Grade = "특수",
                GradeName = "특수학급",
                ClassCount = specialClasses
            });
        }

        // Calculate relative visual bar width
        int maxInGrade = gradeItems.Count > 0 ? Math.Max(1, gradeItems.Max(x => x.ClassCount)) : 1;
        foreach (var item in gradeItems)
        {
            item.BarWidthPercent = Math.Max(12.0, (double)item.ClassCount / maxInGrade * 100.0);
        }
        detail.GradeClasses = gradeItems;

        // Classify scale
        ClassifySchoolScale(detail);

        return detail;
    }

    private async Task<int> QueryClassTotalCountAsync(string officeCode, string schoolCode, int year, string apiKey)
    {
        string url = $"{BaseUrl}/classInfo?Type=json&pIndex=1&pSize=1&ATPT_OFCDC_SC_CODE={officeCode}&SD_SCHUL_CODE={schoolCode}&AY={year}";
        if (!string.IsNullOrEmpty(apiKey)) url += $"&KEY={apiKey}";

        try
        {
            string json = await _httpClient.GetStringAsync(url);
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            if (root.TryGetProperty("classInfo", out var arr) && arr.GetArrayLength() > 0)
            {
                var head = arr[0].GetProperty("head");
                if (head.GetArrayLength() > 0 && head[0].TryGetProperty("list_total_count", out var countProp))
                {
                    return countProp.GetInt32();
                }
            }
        }
        catch (Exception ex)
        {
            App.BootLog($"[QueryClassTotalCountAsync] {ex.Message}");
        }
        return 0;
    }

    private async Task<int> QueryGradeClassCountAsync(string officeCode, string schoolCode, int year, int grade, string apiKey)
    {
        string url = $"{BaseUrl}/classInfo?Type=json&pIndex=1&pSize=1&ATPT_OFCDC_SC_CODE={officeCode}&SD_SCHUL_CODE={schoolCode}&AY={year}&GRADE={grade}";
        if (!string.IsNullOrEmpty(apiKey)) url += $"&KEY={apiKey}";

        try
        {
            string json = await _httpClient.GetStringAsync(url);
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            if (root.TryGetProperty("classInfo", out var arr) && arr.GetArrayLength() > 0)
            {
                var head = arr[0].GetProperty("head");
                if (head.GetArrayLength() > 0 && head[0].TryGetProperty("list_total_count", out var countProp))
                {
                    return countProp.GetInt32();
                }
            }
        }
        catch (Exception ex)
        {
            App.BootLog($"[QueryGradeClassCountAsync] G{grade}: {ex.Message}");
        }
        return 0;
    }

    private static void ClassifySchoolScale(SchoolScaleDetail detail)
    {
        int total = detail.TotalClassCount;
        bool isElem = detail.SchoolInfo.SchoolType.Contains("초등학교");

        if (isElem)
        {
            detail.EstimatedMinStudents = total * 21;
            detail.EstimatedMaxStudents = total * 25;

            if (total >= 48)
            {
                detail.ScaleCategory = "🔴 초거대규모 학교 (과밀 관리 대상)";
                detail.ScaleBadgeBg = "#FEE2E2"; // Red
                detail.ScaleBadgeFg = "#991B1B";
                detail.ScaleSummaryText = $"총 {total}학급의 초거대규모 학교로, 학년당 평균 {(double)total / 6:0.#}학급 편성 및 학생 밀도가 매우 높습니다.";
            }
            else if (total >= 36)
            {
                detail.ScaleCategory = "🟠 대규모 거대학교 (36학급 이상)";
                detail.ScaleBadgeBg = "#FFEDD5"; // Orange
                detail.ScaleBadgeFg = "#9A3412";
                detail.ScaleSummaryText = $"총 {total}학급의 대규모 학교로 교원 및 학생 정원이 많아 전담/부장 보직 규모가 큽니다.";
            }
            else if (total >= 24)
            {
                detail.ScaleCategory = "🟢 중대규모 학교 (24~35학급)";
                detail.ScaleBadgeBg = "#DCFCE7"; // Green
                detail.ScaleBadgeFg = "#166534";
                detail.ScaleSummaryText = $"총 {total}학급의 안정적인 중대규모 학교입니다.";
            }
            else if (total >= 12)
            {
                detail.ScaleCategory = "🔵 일반 중규모 학교 (12~23학급)";
                detail.ScaleBadgeBg = "#E0E7FF"; // Indigo
                detail.ScaleBadgeFg = "#3730A3";
                detail.ScaleSummaryText = $"총 {total}학급 규모로 학년당 2~4학급 수준의 균형잡힌 규모입니다.";
            }
            else if (total >= 6)
            {
                detail.ScaleCategory = "🟣 소규모 학교 (6~11학급)";
                detail.ScaleBadgeBg = "#F3E8FF"; // Purple
                detail.ScaleBadgeFg = "#6B21A8";
                detail.ScaleSummaryText = $"총 {total}학급 규모로 학년당 1~2학급 편성되는 아담한 소규모 학교입니다.";
            }
            else
            {
                detail.ScaleCategory = "⚪ 초소규모 / 분교장 (6학급 미만)";
                detail.ScaleBadgeBg = "#F1F5F9"; // Slate
                detail.ScaleBadgeFg = "#334155";
                detail.ScaleSummaryText = $"총 {total}학급 규모의 초소규모 학교 또는 복식학급 운영 학교입니다.";
            }
        }
        else
        {
            detail.EstimatedMinStudents = total * 24;
            detail.EstimatedMaxStudents = total * 29;

            if (total >= 36)
            {
                detail.ScaleCategory = "🔴 대규모 중·고교 (36학급 이상)";
                detail.ScaleBadgeBg = "#FEE2E2";
                detail.ScaleBadgeFg = "#991B1B";
                detail.ScaleSummaryText = $"총 {total}학급의 대형 학교입니다.";
            }
            else if (total >= 21)
            {
                detail.ScaleCategory = "🟢 중규모 중·고교 (21~35학급)";
                detail.ScaleBadgeBg = "#DCFCE7";
                detail.ScaleBadgeFg = "#166534";
                detail.ScaleSummaryText = $"총 {total}학급의 표준 중규모 학교입니다.";
            }
            else
            {
                detail.ScaleCategory = "🟣 소규모 중·고교 (20학급 이하)";
                detail.ScaleBadgeBg = "#F3E8FF";
                detail.ScaleBadgeFg = "#6B21A8";
                detail.ScaleSummaryText = $"총 {total}학급의 소규모 학교입니다.";
            }
        }
    }

    private static string GetStringProp(JsonElement elem, string prop)
    {
        if (elem.TryGetProperty(prop, out var val) && val.ValueKind == JsonValueKind.String)
        {
            return val.GetString() ?? string.Empty;
        }
        return string.Empty;
    }
}
