using System.IO;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Unicode;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Services;

public interface IConfigService
{
    string ConfigDir { get; }
    NeisConfig NeisConfig { get; set; }
    TimetableSettings TimetableSettings { get; set; }
    List<RecurringScheduleItem> RecurringSchedules { get; set; }
    List<HotkeyItem> Hotkeys { get; set; }

    PeriodAlarmSystemConfig PeriodAlarmConfig { get; set; }

    void LoadAll();
    void SaveNeisConfig();
    void SaveTimetableSettings();
    void SaveRecurringSchedules();
    void SaveHotkeys();
    void SavePeriodAlarmConfig();
}

public class ConfigService : IConfigService
{
    private readonly JsonSerializerOptions _jsonOptions = new()
    {
        WriteIndented = true,
        Encoder = JavaScriptEncoder.Create(UnicodeRanges.All)
    };

    public string ConfigDir { get; }

    public NeisConfig NeisConfig { get; set; } = new();
    public TimetableSettings TimetableSettings { get; set; } = new();
    public List<RecurringScheduleItem> RecurringSchedules { get; set; } = new();
    public List<HotkeyItem> Hotkeys { get; set; } = new();
    public PeriodAlarmSystemConfig PeriodAlarmConfig { get; set; } = PeriodAlarmSystemConfig.CreateDefault();

    public ConfigService()
    {
        string homeDir = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        ConfigDir = Path.Combine(homeDir, ".knol_teacher_desk");

        if (!Directory.Exists(ConfigDir))
        {
            Directory.CreateDirectory(ConfigDir);
        }

        LoadAll();
    }

    public void LoadAll()
    {
        LoadNeisConfig();
        LoadTimetableSettings();
        LoadRecurringSchedules();
        LoadHotkeys();
        LoadPeriodAlarmConfig();
    }

    private void LoadNeisConfig()
    {
        string path = Path.Combine(ConfigDir, "neis_config.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                NeisConfig = JsonSerializer.Deserialize<NeisConfig>(json, _jsonOptions) ?? new();
                return;
            }
            catch { }
        }
        NeisConfig = new();
        SaveNeisConfig();
    }

    public void SaveNeisConfig()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "neis_config.json");
            string json = JsonSerializer.Serialize(NeisConfig, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }

    private void LoadTimetableSettings()
    {
        string path = Path.Combine(ConfigDir, "timetable_settings.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                TimetableSettings = JsonSerializer.Deserialize<TimetableSettings>(json, _jsonOptions) ?? new();
                return;
            }
            catch { }
        }
        TimetableSettings = new();
        SaveTimetableSettings();
    }

    public void SaveTimetableSettings()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "timetable_settings.json");
            string json = JsonSerializer.Serialize(TimetableSettings, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }

    private void LoadRecurringSchedules()
    {
        string path = Path.Combine(ConfigDir, "recurring_schedules.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                var container = JsonSerializer.Deserialize<RecurringScheduleContainer>(json, _jsonOptions);
                if (container?.Schedules != null && container.Schedules.Count > 0)
                {
                    RecurringSchedules = container.Schedules;
                    return;
                }
            }
            catch { }
        }
        RecurringSchedules = new()
        {
            new RecurringScheduleItem
            {
                Id = "rec_def_leave",
                Title = "퇴근 시간 자동 종료",
                ActionType = "shutdown",
                TimeString = "16:40",
                AmPm = "오후",
                Hour12 = 4,
                Minute = 40,
                RepeatMode = "weekdays",
                RepeatDays = new() { 0, 1, 2, 3, 4 },
                SkipHolidays = true,
                Enabled = false,
                Memo = "선생님 퇴근 시간(16:40) PC 자동 전원 차단"
            },
            new RecurringScheduleItem
            {
                Id = "rec_def_clean",
                Title = "청소 및 하교 지도 알람",
                ActionType = "alarm",
                TimeString = "14:30",
                AmPm = "오후",
                Hour12 = 2,
                Minute = 30,
                RepeatMode = "weekdays",
                RepeatDays = new() { 0, 1, 2, 3, 4 },
                SkipHolidays = true,
                Enabled = false,
                Memo = "교실 청소 및 학생 하교 지도 알람"
            }
        };
        SaveRecurringSchedules();
    }

    public void SaveRecurringSchedules()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "recurring_schedules.json");
            var container = new RecurringScheduleContainer { Schedules = RecurringSchedules };
            string json = JsonSerializer.Serialize(container, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }

    private void LoadHotkeys()
    {
        string path = Path.Combine(ConfigDir, "hotkeys_config.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                var list = JsonSerializer.Deserialize<List<HotkeyItem>>(json, _jsonOptions);
                if (list != null && list.Count > 0)
                {
                    Hotkeys = list;
                    return;
                }
            }
            catch { }
        }
        Hotkeys = DefaultHotkeys.GetDefaults();
        SaveHotkeys();
    }

    public void SaveHotkeys()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "hotkeys_config.json");
            string json = JsonSerializer.Serialize(Hotkeys, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }

    private void LoadPeriodAlarmConfig()
    {
        string path = Path.Combine(ConfigDir, "period_countdown_settings.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                var cfg = JsonSerializer.Deserialize<PeriodAlarmSystemConfig>(json, _jsonOptions);
                if (cfg != null)
                {
                    PeriodAlarmConfig = cfg;
                    return;
                }
            }
            catch { }
        }
        PeriodAlarmConfig = PeriodAlarmSystemConfig.CreateDefault();
        SavePeriodAlarmConfig();
    }

    public void SavePeriodAlarmConfig()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "period_countdown_settings.json");
            string json = JsonSerializer.Serialize(PeriodAlarmConfig, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }
}
