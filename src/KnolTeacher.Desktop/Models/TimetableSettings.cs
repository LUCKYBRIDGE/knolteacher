using System.Text.Json.Serialization;

namespace KnolTeacher.Desktop.Models;

public class TimetableSettings
{
    [JsonPropertyName("enable_period_alarm")]
    public bool EnablePeriodAlarm { get; set; } = true;

    [JsonPropertyName("alarm_lead_minutes")]
    public int AlarmLeadMinutes { get; set; } = 3;

    [JsonPropertyName("enable_period_end_alarm")]
    public bool EnablePeriodEndAlarm { get; set; } = true;

    [JsonPropertyName("alarm_sound_id")]
    public string AlarmSoundId { get; set; } = "chime";

    [JsonPropertyName("lesson_duration_minutes")]
    public int LessonDurationMinutes { get; set; } = 40;

    [JsonPropertyName("theme_mode")]
    public string ThemeMode { get; set; } = "Beige";

    [JsonPropertyName("window_alpha")]
    public double WindowAlpha { get; set; } = 1.0;

    [JsonPropertyName("lunch_after_period")]
    public int LunchAfterPeriod { get; set; } = 4;

    [JsonPropertyName("enable_period_7")]
    public bool EnablePeriod7 { get; set; } = false;

    [JsonPropertyName("google_sheet_url")]
    public string GoogleSheetUrl { get; set; } = string.Empty;

    [JsonPropertyName("auto_open_mini_ticker")]
    public bool AutoOpenMiniTicker { get; set; } = true;

    [JsonPropertyName("countdown_monitor_index")]
    public int CountdownMonitorIndex { get; set; } = 1;
}
