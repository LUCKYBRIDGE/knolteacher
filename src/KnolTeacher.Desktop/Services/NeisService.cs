using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Services;

public interface INeisService
{
    Task<MealInfo?> GetMealAsync(DateTime? date = null);
    Task<List<TimetablePeriodItem>> GetTimetableAsync(DateTime? date = null);
}

public class NeisService : INeisService
{
    private readonly IConfigService _configService;
    private static readonly HttpClient _httpClient = new()
    {
        Timeout = TimeSpan.FromSeconds(5)
    };

    private const string BaseUrl = "https://open.neis.go.kr/hub";

    public NeisService(IConfigService configService)
    {
        _configService = configService;
    }

    public async Task<MealInfo?> GetMealAsync(DateTime? date = null)
    {
        var targetDate = date ?? DateTime.Today;
        var cfg = _configService.NeisConfig;

        if (string.IsNullOrEmpty(cfg.OfficeCode) || string.IsNullOrEmpty(cfg.SchoolCode))
        {
            return new MealInfo
            {
                DateString = targetDate.ToString("yyyy-MM-dd"),
                Dishes = new() { "학교 정보가 설정되지 않았습니다.", "환경설정에서 학교를 등록해 주세요." },
                Calorie = "0 kcal"
            };
        }

        string ymd = targetDate.ToString("yyyyMMdd");
        string url = $"{BaseUrl}/mealServiceDietInfo?Type=json&pIndex=1&pSize=10" +
                     $"&ATPT_OFCDC_SC_CODE={cfg.OfficeCode}&SD_SCHUL_CODE={cfg.SchoolCode}&MLSV_YMD={ymd}&MMEAL_SC_CODE=2";

        if (!string.IsNullOrEmpty(cfg.ApiKey))
        {
            url += $"&KEY={cfg.ApiKey}";
        }

        try
        {
            string json = await _httpClient.GetStringAsync(url);
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            if (root.TryGetProperty("mealServiceDietInfo", out var mealArray) && mealArray.GetArrayLength() > 1)
            {
                var rowElement = mealArray[1].GetProperty("row")[0];
                string rawDishes = rowElement.GetProperty("DDISH_NM").GetString() ?? "";
                string calorie = rowElement.TryGetProperty("CAL_INFO", out var cal) ? cal.GetString() ?? "" : "";
                string origin = rowElement.TryGetProperty("ORPLC_INFO", out var orig) ? orig.GetString() ?? "" : "";

                var dishes = new List<string>();
                var rawLines = rawDishes.Replace("<br/>", "\n").Replace("<br>", "\n").Split('\n');
                foreach (var line in rawLines)
                {
                    string cleaned = line.Trim();
                    if (!string.IsNullOrEmpty(cleaned))
                    {
                        dishes.Add(cleaned);
                    }
                }

                return new MealInfo
                {
                    DateString = targetDate.ToString("yyyy-MM-dd"),
                    Dishes = dishes,
                    Calorie = calorie,
                    Origin = origin
                };
            }
        }
        catch { }

        return new MealInfo
        {
            DateString = targetDate.ToString("yyyy-MM-dd"),
            Dishes = new() { "등록된 급식 식단표가 없습니다.", "(주말, 공휴일 또는 방학)" },
            Calorie = "0 kcal"
        };
    }

    public async Task<List<TimetablePeriodItem>> GetTimetableAsync(DateTime? date = null)
    {
        var targetDate = date ?? DateTime.Today;
        var cfg = _configService.NeisConfig;

        var defaultList = new List<TimetablePeriodItem>
        {
            new() { Period = 1, Subject = "국어", TimeRange = "09:00 ~ 09:40" },
            new() { Period = 2, Subject = "수학", TimeRange = "09:50 ~ 10:30" },
            new() { Period = 3, Subject = "사회", TimeRange = "10:40 ~ 11:20" },
            new() { Period = 4, Subject = "과학", TimeRange = "11:30 ~ 12:10" },
            new() { Period = 5, Subject = "체육", TimeRange = "13:00 ~ 13:40" },
            new() { Period = 6, Subject = "미술", TimeRange = "13:50 ~ 14:30" },
        };

        if (string.IsNullOrEmpty(cfg.OfficeCode) || string.IsNullOrEmpty(cfg.SchoolCode))
        {
            return defaultList;
        }

        string endpoint = cfg.SchoolType switch
        {
            "중학교" => "misTimetable",
            "고등학교" => "hisTimetable",
            _ => "elsTimetable"
        };

        string ymd = targetDate.ToString("yyyyMMdd");
        string url = $"{BaseUrl}/{endpoint}?Type=json&pIndex=1&pSize=20" +
                     $"&ATPT_OFCDC_SC_CODE={cfg.OfficeCode}&SD_SCHUL_CODE={cfg.SchoolCode}" +
                     $"&AY={cfg.AcademicYear}&SEM={cfg.Semester}&ALL_TI_YMD={ymd}" +
                     $"&GRADE={cfg.Grade}&CLASS_NM={cfg.ClassName}";

        if (!string.IsNullOrEmpty(cfg.ApiKey))
        {
            url += $"&KEY={cfg.ApiKey}";
        }

        try
        {
            string json = await _httpClient.GetStringAsync(url);
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            if (root.TryGetProperty(endpoint, out var ttArray) && ttArray.GetArrayLength() > 1)
            {
                var rows = ttArray[1].GetProperty("row");
                var result = new List<TimetablePeriodItem>();
                int periodNum = 1;

                foreach (var row in rows.EnumerateArray())
                {
                    string subj = row.GetProperty("ITRT_CNTNT").GetString() ?? "";
                    string timeRange = periodNum <= defaultList.Count ? defaultList[periodNum - 1].TimeRange : "";
                    result.Add(new TimetablePeriodItem
                    {
                        Period = periodNum++,
                        Subject = subj,
                        TimeRange = timeRange
                    });
                }

                if (result.Count > 0) return result;
            }
        }
        catch { }

        return defaultList;
    }
}
