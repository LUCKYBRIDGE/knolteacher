using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Services;

public interface IAcademicCalendarService
{
    Task<List<AcademicScheduleItem>> GetFullYearScheduleAsync(int? academicYear = null, bool forceRefresh = false);
    Task<List<AcademicScheduleItem>> GetScheduleForMonthAsync(int year, int month, bool forceRefresh = false);
    Task<List<AcademicScheduleItem>> GetUpcomingDDayEventsAsync(int limit = 4);
    List<CalendarDayCell> GenerateMonthGrid(int year, int month, List<AcademicScheduleItem> events, DateTime? selectedDate = null, List<TeacherCalendarEvent>? teacherEvents = null);
}

public class AcademicCalendarService : IAcademicCalendarService
{
    private readonly IConfigService _configService;
    private static readonly HttpClient _httpClient = new()
    {
        Timeout = TimeSpan.FromSeconds(8)
    };

    private const string BaseUrl = "https://open.neis.go.kr/hub";
    private readonly string _cacheFilePath;
    private List<AcademicScheduleItem>? _memoryCache;
    private int _cachedYear = 0;

    public AcademicCalendarService(IConfigService configService)
    {
        _configService = configService;
        _cacheFilePath = Path.Combine(_configService.ConfigDir, "academic_schedule_cache.json");
    }

    public async Task<List<AcademicScheduleItem>> GetFullYearScheduleAsync(int? academicYear = null, bool forceRefresh = false)
    {
        int targetYear = academicYear ?? (DateTime.Today.Month < 3 ? DateTime.Today.Year - 1 : DateTime.Today.Year);

        if (!forceRefresh && _memoryCache != null && _cachedYear == targetYear)
        {
            return _memoryCache;
        }

        // Try reading local file cache first if not forced
        if (!forceRefresh && File.Exists(_cacheFilePath))
        {
            try
            {
                string cachedJson = await File.ReadAllTextAsync(_cacheFilePath);
                var items = JsonSerializer.Deserialize<List<AcademicScheduleItem>>(cachedJson);
                if (items != null && items.Count > 0 && items.Any(i => i.AcademicYear == targetYear.ToString()))
                {
                    _memoryCache = items;
                    _cachedYear = targetYear;
                    return items;
                }
            }
            catch { }
        }

        var cfg = _configService.NeisConfig;
        if (string.IsNullOrEmpty(cfg.OfficeCode) || string.IsNullOrEmpty(cfg.SchoolCode))
        {
            // Fallback default sample events if school not yet configured
            var fallback = GenerateDefaultSchedule(targetYear);
            _memoryCache = fallback;
            _cachedYear = targetYear;
            return fallback;
        }

        string apiKey = cfg.ApiKey?.Trim() ?? string.Empty;
        string url = $"{BaseUrl}/SchoolSchedule?Type=json&pIndex=1&pSize=1000" +
                     $"&ATPT_OFCDC_SC_CODE={cfg.OfficeCode}&SD_SCHUL_CODE={cfg.SchoolCode}&AY={targetYear}";

        if (!string.IsNullOrEmpty(apiKey))
        {
            url += $"&KEY={apiKey}";
        }

        try
        {
            string json = await _httpClient.GetStringAsync(url);
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            if (root.TryGetProperty("SchoolSchedule", out var schedArray) && schedArray.GetArrayLength() > 1)
            {
                var rowElement = schedArray[1].GetProperty("row");
                var items = new List<AcademicScheduleItem>();

                foreach (var r in rowElement.EnumerateArray())
                {
                    string eventNm = r.TryGetProperty("EVENT_NM", out var ev) ? ev.GetString() ?? "" : "";
                    if (string.IsNullOrWhiteSpace(eventNm) || eventNm == "토요휴업일")
                    {
                        // Filter out normal Saturday closures to keep calendar clean
                        continue;
                    }

                    var item = new AcademicScheduleItem
                    {
                        RawDate = r.TryGetProperty("AA_YMD", out var ymd) ? ymd.GetString() ?? "" : "",
                        EventName = eventNm,
                        EventContent = r.TryGetProperty("EVENT_CNTNT", out var cnt) ? cnt.GetString() ?? "" : "",
                        SubtractionDayType = r.TryGetProperty("SBTR_DD_SC_NM", out var sb) ? sb.GetString() ?? "" : "",
                        AcademicYear = targetYear.ToString()
                    };
                    items.Add(item);
                }

                _memoryCache = items.OrderBy(i => i.RawDate).ToList();
                _cachedYear = targetYear;

                // Save to local cache file
                try
                {
                    string saveJson = JsonSerializer.Serialize(_memoryCache, new JsonSerializerOptions { WriteIndented = true });
                    await File.WriteAllTextAsync(_cacheFilePath, saveJson);
                }
                catch { }

                return _memoryCache;
            }
        }
        catch { }

        // Fallback if network or API error
        if (_memoryCache != null && _memoryCache.Count > 0)
        {
            return _memoryCache;
        }

        var defaultFallback = GenerateDefaultSchedule(targetYear);
        _memoryCache = defaultFallback;
        _cachedYear = targetYear;
        return defaultFallback;
    }

    public async Task<List<AcademicScheduleItem>> GetScheduleForMonthAsync(int year, int month, bool forceRefresh = false)
    {
        int ay = month < 3 ? year - 1 : year;
        var all = await GetFullYearScheduleAsync(ay, forceRefresh);
        string prefix = $"{year}{month:D2}";
        return all.Where(e => e.RawDate.StartsWith(prefix)).ToList();
    }

    public async Task<List<AcademicScheduleItem>> GetUpcomingDDayEventsAsync(int limit = 4)
    {
        int currentYear = DateTime.Today.Year;
        int ay = DateTime.Today.Month < 3 ? currentYear - 1 : currentYear;
        var all = await GetFullYearScheduleAsync(ay);

        // Filter upcoming events from today onwards
        var upcoming = all
            .Where(e => e.Date.HasValue && e.Date.Value.Date >= DateTime.Today &&
                        !e.EventName.Contains("공휴일") &&
                        !e.EventName.Contains("휴업일"))
            .OrderBy(e => e.Date)
            .Take(limit)
            .ToList();

        if (upcoming.Count == 0)
        {
            // If no major school event found, return generic upcoming milestones
            upcoming.Add(new AcademicScheduleItem
            {
                RawDate = DateTime.Today.AddDays(7).ToString("yyyyMMdd"),
                EventName = "학급 회의 및 정리"
            });
        }

        return upcoming;
    }

    public List<CalendarDayCell> GenerateMonthGrid(int year, int month, List<AcademicScheduleItem> events, DateTime? selectedDate = null, List<TeacherCalendarEvent>? teacherEvents = null)
    {
        var cells = new List<CalendarDayCell>();
        var firstDayOfMonth = new DateTime(year, month, 1);
        int daysInMonth = DateTime.DaysInMonth(year, month);

        // Day of week for 1st day (0 = Sunday, 1 = Monday, ... 6 = Saturday)
        int startDayOfWeek = (int)firstDayOfMonth.DayOfWeek;

        // Previous month filler days
        var prevMonth = firstDayOfMonth.AddMonths(-1);
        int daysInPrevMonth = DateTime.DaysInMonth(prevMonth.Year, prevMonth.Month);

        for (int i = startDayOfWeek - 1; i >= 0; i--)
        {
            var date = new DateTime(prevMonth.Year, prevMonth.Month, daysInPrevMonth - i);
            string isoDate = date.ToString("yyyy-MM-dd");
            var tEvents = teacherEvents?.Where(t => t.Date == isoDate).ToList() ?? new();
            cells.Add(new CalendarDayCell
            {
                Date = date,
                IsCurrentMonth = false,
                IsSelected = selectedDate.HasValue && selectedDate.Value.Date == date.Date,
                TeacherEvents = tEvents
            });
        }

        // Current month days
        for (int d = 1; d <= daysInMonth; d++)
        {
            var date = new DateTime(year, month, d);
            string dateKey = date.ToString("yyyyMMdd");
            string isoDate = date.ToString("yyyy-MM-dd");
            var dayEvents = events.Where(e => e.RawDate == dateKey).ToList();
            var tEvents = teacherEvents?.Where(t => t.Date == isoDate).ToList() ?? new();

            cells.Add(new CalendarDayCell
            {
                Date = date,
                IsCurrentMonth = true,
                IsSelected = selectedDate.HasValue && selectedDate.Value.Date == date.Date,
                Events = dayEvents,
                TeacherEvents = tEvents
            });
        }

        // Next month filler days to complete grid (multiples of 7, up to 35 or 42)
        int totalCells = cells.Count <= 35 ? 35 : 42;
        int remaining = totalCells - cells.Count;
        var nextMonth = firstDayOfMonth.AddMonths(1);

        for (int d = 1; d <= remaining; d++)
        {
            var date = new DateTime(nextMonth.Year, nextMonth.Month, d);
            string isoDate = date.ToString("yyyy-MM-dd");
            var tEvents = teacherEvents?.Where(t => t.Date == isoDate).ToList() ?? new();
            cells.Add(new CalendarDayCell
            {
                Date = date,
                IsCurrentMonth = false,
                IsSelected = selectedDate.HasValue && selectedDate.Value.Date == date.Date,
                TeacherEvents = tEvents
            });
        }

        return cells;
    }

    private List<AcademicScheduleItem> GenerateDefaultSchedule(int year)
    {
        return new List<AcademicScheduleItem>
        {
            new() { RawDate = $"{year}0303", EventName = "개학식 및 입학식", SubtractionDayType = "해당없음" },
            new() { RawDate = $"{year}0505", EventName = "어린이날", SubtractionDayType = "공휴일" },
            new() { RawDate = $"{year}0718", EventName = "여름방학식", SubtractionDayType = "해당없음" },
            new() { RawDate = $"{year}0822", EventName = "2학기 개학식", SubtractionDayType = "해당없음" },
            new() { RawDate = $"{year}1009", EventName = "한글날", SubtractionDayType = "공휴일" },
            new() { RawDate = $"{year}1224", EventName = "겨울방학식", SubtractionDayType = "해당없음" },
            new() { RawDate = $"{year + 1}0105", EventName = "졸업식 및 종업식", SubtractionDayType = "해당없음" }
        };
    }
}
