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
    ChecklistStore ChecklistStore { get; set; }
    AutoNoticePreset AutoNoticePreset { get; set; }
    BoardSetStore BoardSetStore { get; set; }
    int TimerTargetMonitorIndex { get; set; }
    MainWidgetLayoutConfig MainWidgetLayout { get; set; }
    NolboardLayoutConfig NolboardLayout { get; set; }
    DDayConfig DDayConfig { get; set; }
    List<TeacherCalendarEvent> TeacherCalendarEvents { get; set; }
    string? LastSeenTutorialVersion { get; set; }
    StorageConfig StorageConfig { get; set; }
    string GetEffectiveSaveDirectory();
    void SetDefaultSaveDirectory(string path);
    void SaveStorageConfig();

    void LoadAll();
    void SaveNeisConfig();
    void SaveTimetableSettings();
    void SaveRecurringSchedules();
    void SaveHotkeys();
    void SavePeriodAlarmConfig();
    void SaveChecklistStore();
    void SaveAutoNoticePreset();
    void SaveBoardSetStore();
    void SaveTimerSettings();
    void SaveMainWidgetLayout();
    void SaveNolboardLayout();
    void SaveDDayConfig();
    void SaveTeacherCalendarEvents();
    void SaveTutorialVersion();
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
    public ChecklistStore ChecklistStore { get; set; } = new();
    public AutoNoticePreset AutoNoticePreset { get; set; } = new();
    public BoardSetStore BoardSetStore { get; set; } = new();
    public int TimerTargetMonitorIndex { get; set; } = 1;
    public MainWidgetLayoutConfig MainWidgetLayout { get; set; } = MainWidgetLayoutConfig.CreateDefault();
    public NolboardLayoutConfig NolboardLayout { get; set; } = new();
    public DDayConfig DDayConfig { get; set; } = new();
    public List<TeacherCalendarEvent> TeacherCalendarEvents { get; set; } = new();
    public string? LastSeenTutorialVersion { get; set; }
    public StorageConfig StorageConfig { get; set; } = new();

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
        LoadChecklistStore();
        LoadAutoNoticePreset();
        LoadBoardSetStore();
        LoadTimerSettings();
        LoadMainWidgetLayout();
        LoadNolboardLayout();
        LoadDDayConfig();
        LoadTeacherCalendarEvents();
        LoadTutorialVersion();
        LoadStorageConfig();
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

    private void LoadChecklistStore()
    {
        string path = Path.Combine(ConfigDir, "checklist_store.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                var store = JsonSerializer.Deserialize<ChecklistStore>(json, _jsonOptions);
                if (store != null)
                {
                    ChecklistStore = store;
                    return;
                }
            }
            catch { }
        }
        ChecklistStore = new ChecklistStore();
        SaveChecklistStore();
    }

    public void SaveChecklistStore()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "checklist_store.json");
            string json = JsonSerializer.Serialize(ChecklistStore, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }

    private void LoadAutoNoticePreset()
    {
        string path = Path.Combine(ConfigDir, "auto_notice_preset.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                var preset = JsonSerializer.Deserialize<AutoNoticePreset>(json, _jsonOptions);
                if (preset != null)
                {
                    AutoNoticePreset = preset;
                    return;
                }
            }
            catch { }
        }
        AutoNoticePreset = new AutoNoticePreset();
        SaveAutoNoticePreset();
    }

    public void SaveAutoNoticePreset()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "auto_notice_preset.json");
            string json = JsonSerializer.Serialize(AutoNoticePreset, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }

    private void LoadBoardSetStore()
    {
        string path = Path.Combine(ConfigDir, "board_set_store.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                var store = JsonSerializer.Deserialize<BoardSetStore>(json, _jsonOptions);
                if (store != null)
                {
                    BoardSetStore = store;
                    return;
                }
            }
            catch { }
        }
        BoardSetStore = new BoardSetStore();
        SaveBoardSetStore();
    }

    public void SaveBoardSetStore()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "board_set_store.json");
            string json = JsonSerializer.Serialize(BoardSetStore, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }

    private void LoadTimerSettings()
    {
        string path = Path.Combine(ConfigDir, "timer_settings.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                using var doc = JsonDocument.Parse(json);
                if (doc.RootElement.TryGetProperty("target_monitor_index", out var elem))
                {
                    TimerTargetMonitorIndex = elem.GetInt32();
                    return;
                }
            }
            catch { }
        }
        TimerTargetMonitorIndex = 1; // Default: 1 (모니터 2 / 학생용 전자칠판 권장)
    }

    public void SaveTimerSettings()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "timer_settings.json");
            string json = JsonSerializer.Serialize(new { target_monitor_index = TimerTargetMonitorIndex }, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }

    private void LoadMainWidgetLayout()
    {
        string path = Path.Combine(ConfigDir, "main_widget_layout.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                var layout = JsonSerializer.Deserialize<MainWidgetLayoutConfig>(json, _jsonOptions);
                if (layout != null && layout.Widgets != null && layout.Widgets.Count > 0)
                {
                    MainWidgetLayout = layout;
                    return;
                }
            }
            catch { }
        }
        MainWidgetLayout = MainWidgetLayoutConfig.CreateDefault();
        SaveMainWidgetLayout();
    }

    public void SaveMainWidgetLayout()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "main_widget_layout.json");
            string json = JsonSerializer.Serialize(MainWidgetLayout, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }

    private void LoadNolboardLayout()
    {
        string path = Path.Combine(ConfigDir, "nolboard_widgets.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                var layout = JsonSerializer.Deserialize<NolboardLayoutConfig>(json, _jsonOptions);
                if (layout != null)
                {
                    NolboardLayout = layout;
                    return;
                }
            }
            catch { }
        }
        NolboardLayout = new();
    }

    public void SaveNolboardLayout()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "nolboard_widgets.json");
            string json = JsonSerializer.Serialize(NolboardLayout, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }

    private void LoadDDayConfig()
    {
        string path = Path.Combine(ConfigDir, "dday_config.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                var cfg = JsonSerializer.Deserialize<DDayConfig>(json, _jsonOptions);
                if (cfg != null)
                {
                    DDayConfig = cfg;
                    return;
                }
            }
            catch { }
        }
        DDayConfig = new();
        SaveDDayConfig();
    }

    public void SaveDDayConfig()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "dday_config.json");
            string json = JsonSerializer.Serialize(DDayConfig, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }

    private void LoadTutorialVersion()
    {
        string path = Path.Combine(ConfigDir, "tutorial_state.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                using var doc = JsonDocument.Parse(json);
                if (doc.RootElement.TryGetProperty("last_seen_version", out var prop))
                {
                    LastSeenTutorialVersion = prop.GetString();
                    return;
                }
            }
            catch { }
        }
        LastSeenTutorialVersion = null;
    }

    public void SaveTutorialVersion()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "tutorial_state.json");
            string json = JsonSerializer.Serialize(new { last_seen_version = LastSeenTutorialVersion }, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }

    public string GetEffectiveSaveDirectory()
    {
        if (!string.IsNullOrWhiteSpace(StorageConfig.DefaultSaveDirectory))
        {
            try
            {
                if (!Directory.Exists(StorageConfig.DefaultSaveDirectory))
                {
                    Directory.CreateDirectory(StorageConfig.DefaultSaveDirectory);
                }
                return StorageConfig.DefaultSaveDirectory;
            }
            catch { }
        }

        string downloads = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");
        try
        {
            if (!Directory.Exists(downloads))
            {
                Directory.CreateDirectory(downloads);
            }
        }
        catch { }
        return downloads;
    }

    public void SetDefaultSaveDirectory(string path)
    {
        StorageConfig.DefaultSaveDirectory = path ?? string.Empty;
        if (!string.IsNullOrWhiteSpace(path))
        {
            try
            {
                if (!Directory.Exists(path))
                {
                    Directory.CreateDirectory(path);
                }
            }
            catch { }
        }
        SaveStorageConfig();
    }

    private void LoadStorageConfig()
    {
        string path = Path.Combine(ConfigDir, "storage_config.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                var cfg = JsonSerializer.Deserialize<StorageConfig>(json, _jsonOptions);
                if (cfg != null)
                {
                    StorageConfig = cfg;
                    return;
                }
            }
            catch { }
        }
        StorageConfig = new StorageConfig();
    }

    public void SaveStorageConfig()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "storage_config.json");
            string json = JsonSerializer.Serialize(StorageConfig, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }

    private void LoadTeacherCalendarEvents()
    {
        string path = Path.Combine(ConfigDir, "calendar_events.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                TeacherCalendarEvents = JsonSerializer.Deserialize<List<TeacherCalendarEvent>>(json, _jsonOptions) ?? new();
                return;
            }
            catch { }
        }
        TeacherCalendarEvents = new();
    }

    public void SaveTeacherCalendarEvents()
    {
        try
        {
            string path = Path.Combine(ConfigDir, "calendar_events.json");
            string json = JsonSerializer.Serialize(TeacherCalendarEvents, _jsonOptions);
            File.WriteAllText(path, json);
        }
        catch { }
    }
}
