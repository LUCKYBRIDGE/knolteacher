using System.IO;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Serialization;
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
    private const string NeisConfigFile = "neis_config.json";
    private const string TimetableSettingsFile = "timetable_settings.json";
    private const string RecurringSchedulesFile = "recurring_schedules.json";
    private const string HotkeysFile = "hotkeys_config.json";
    private const string PeriodAlarmFile = "period_countdown_settings.json";
    private const string ChecklistFile = "checklist_store.json";
    private const string AutoNoticeFile = "auto_notice_preset.json";
    private const string BoardSetFile = "board_set_store.json";
    private const string TimerSettingsFile = "timer_settings.json";
    private const string MainWidgetLayoutFile = "main_widget_layout.json";
    private const string NolboardLayoutFile = "nolboard_widgets.json";
    private const string DDayFile = "dday_config.json";
    private const string TutorialStateFile = "tutorial_state.json";
    private const string StorageConfigFile = "storage_config.json";
    private const string CalendarEventsFile = "calendar_events.json";

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
        Directory.CreateDirectory(ConfigDir);
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

    private string ConfigPath(string fileName) => Path.Combine(ConfigDir, fileName);

    private bool TryLoadJson<T>(string fileName, out T? value)
        where T : class
        => SafeLocalJsonStore.TryLoad(ConfigPath(fileName), _jsonOptions, out value);

    private void SaveJson<T>(string fileName, T value)
        => SafeLocalJsonStore.TrySave(ConfigPath(fileName), value, _jsonOptions);

    private void LoadNeisConfig()
    {
        if (TryLoadJson<NeisConfig>(NeisConfigFile, out var config))
        {
            NeisConfig = config!;
            return;
        }

        NeisConfig = new();
        SaveNeisConfig();
    }

    public void SaveNeisConfig() => SaveJson(NeisConfigFile, NeisConfig);

    private void LoadTimetableSettings()
    {
        if (TryLoadJson<TimetableSettings>(TimetableSettingsFile, out var settings))
        {
            TimetableSettings = settings!;
            return;
        }

        TimetableSettings = new();
        SaveTimetableSettings();
    }

    public void SaveTimetableSettings() => SaveJson(TimetableSettingsFile, TimetableSettings);

    private void LoadRecurringSchedules()
    {
        if (TryLoadJson<RecurringScheduleContainer>(RecurringSchedulesFile, out var container) &&
            container?.Schedules is { Count: > 0 })
        {
            RecurringSchedules = container.Schedules;
            return;
        }

        RecurringSchedules = CreateDefaultRecurringSchedules();
        SaveRecurringSchedules();
    }

    public void SaveRecurringSchedules()
        => SaveJson(RecurringSchedulesFile, new RecurringScheduleContainer { Schedules = RecurringSchedules });

    private static List<RecurringScheduleItem> CreateDefaultRecurringSchedules()
        => new()
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

    private void LoadHotkeys()
    {
        if (TryLoadJson<List<HotkeyItem>>(HotkeysFile, out var hotkeys) && hotkeys is { Count: > 0 })
        {
            Hotkeys = hotkeys;
            return;
        }

        Hotkeys = DefaultHotkeys.GetDefaults();
        SaveHotkeys();
    }

    public void SaveHotkeys() => SaveJson(HotkeysFile, Hotkeys);

    private void LoadPeriodAlarmConfig()
    {
        if (TryLoadJson<PeriodAlarmSystemConfig>(PeriodAlarmFile, out var config))
        {
            PeriodAlarmConfig = config!;
            return;
        }

        PeriodAlarmConfig = PeriodAlarmSystemConfig.CreateDefault();
        SavePeriodAlarmConfig();
    }

    public void SavePeriodAlarmConfig() => SaveJson(PeriodAlarmFile, PeriodAlarmConfig);

    private void LoadChecklistStore()
    {
        if (TryLoadJson<ChecklistStore>(ChecklistFile, out var store))
        {
            ChecklistStore = store!;
            return;
        }

        ChecklistStore = new();
        SaveChecklistStore();
    }

    public void SaveChecklistStore() => SaveJson(ChecklistFile, ChecklistStore);

    private void LoadAutoNoticePreset()
    {
        if (TryLoadJson<AutoNoticePreset>(AutoNoticeFile, out var preset))
        {
            AutoNoticePreset = preset!;
            return;
        }

        AutoNoticePreset = new();
        SaveAutoNoticePreset();
    }

    public void SaveAutoNoticePreset() => SaveJson(AutoNoticeFile, AutoNoticePreset);

    private void LoadBoardSetStore()
    {
        if (TryLoadJson<BoardSetStore>(BoardSetFile, out var store))
        {
            BoardSetStore = store!;
            return;
        }

        BoardSetStore = new();
        SaveBoardSetStore();
    }

    public void SaveBoardSetStore() => SaveJson(BoardSetFile, BoardSetStore);

    private void LoadTimerSettings()
    {
        if (TryLoadJson<TimerSettingsData>(TimerSettingsFile, out var settings))
        {
            TimerTargetMonitorIndex = settings!.TargetMonitorIndex;
            return;
        }

        TimerTargetMonitorIndex = 1;
    }

    public void SaveTimerSettings()
        => SaveJson(TimerSettingsFile, new TimerSettingsData { TargetMonitorIndex = TimerTargetMonitorIndex });

    private void LoadMainWidgetLayout()
    {
        if (TryLoadJson<MainWidgetLayoutConfig>(MainWidgetLayoutFile, out var layout) &&
            layout?.Widgets is { Count: > 0 })
        {
            MainWidgetLayout = layout;
            return;
        }

        MainWidgetLayout = MainWidgetLayoutConfig.CreateDefault();
        SaveMainWidgetLayout();
    }

    public void SaveMainWidgetLayout() => SaveJson(MainWidgetLayoutFile, MainWidgetLayout);

    private void LoadNolboardLayout()
    {
        if (TryLoadJson<NolboardLayoutConfig>(NolboardLayoutFile, out var layout))
        {
            NolboardLayout = layout!;
            return;
        }

        NolboardLayout = new();
    }

    public void SaveNolboardLayout() => SaveJson(NolboardLayoutFile, NolboardLayout);

    private void LoadDDayConfig()
    {
        if (TryLoadJson<DDayConfig>(DDayFile, out var config))
        {
            DDayConfig = config!;
            return;
        }

        DDayConfig = new();
        SaveDDayConfig();
    }

    public void SaveDDayConfig() => SaveJson(DDayFile, DDayConfig);

    private void LoadTutorialVersion()
    {
        if (TryLoadJson<TutorialStateData>(TutorialStateFile, out var state))
        {
            LastSeenTutorialVersion = state!.LastSeenVersion;
            return;
        }

        LastSeenTutorialVersion = null;
    }

    public void SaveTutorialVersion()
        => SaveJson(TutorialStateFile, new TutorialStateData { LastSeenVersion = LastSeenTutorialVersion });

    public string GetEffectiveSaveDirectory()
    {
        if (!string.IsNullOrWhiteSpace(StorageConfig.DefaultSaveDirectory))
        {
            try
            {
                Directory.CreateDirectory(StorageConfig.DefaultSaveDirectory);
                return StorageConfig.DefaultSaveDirectory;
            }
            catch
            {
                // Fall through to Downloads. The path itself may be user-specific, so do not log it.
            }
        }

        string downloads = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");
        try
        {
            Directory.CreateDirectory(downloads);
        }
        catch
        {
            // Preserve the historical fallback behavior even on restricted school PCs.
        }

        return downloads;
    }

    public void SetDefaultSaveDirectory(string path)
    {
        StorageConfig.DefaultSaveDirectory = path ?? string.Empty;
        if (!string.IsNullOrWhiteSpace(path))
        {
            try
            {
                Directory.CreateDirectory(path);
            }
            catch
            {
                // Save the preference as before; actual use falls back safely when inaccessible.
            }
        }

        SaveStorageConfig();
    }

    private void LoadStorageConfig()
    {
        if (TryLoadJson<StorageConfig>(StorageConfigFile, out var config))
        {
            StorageConfig = config!;
            return;
        }

        StorageConfig = new();
    }

    public void SaveStorageConfig() => SaveJson(StorageConfigFile, StorageConfig);

    private void LoadTeacherCalendarEvents()
    {
        if (TryLoadJson<List<TeacherCalendarEvent>>(CalendarEventsFile, out var events))
        {
            TeacherCalendarEvents = events!;
            return;
        }

        TeacherCalendarEvents = new();
    }

    public void SaveTeacherCalendarEvents() => SaveJson(CalendarEventsFile, TeacherCalendarEvents);

    private sealed class TimerSettingsData
    {
        [JsonPropertyName("target_monitor_index")]
        public int TargetMonitorIndex { get; set; } = 1;
    }

    private sealed class TutorialStateData
    {
        [JsonPropertyName("last_seen_version")]
        public string? LastSeenVersion { get; set; }
    }
}
