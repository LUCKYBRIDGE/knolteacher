using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace KnolTeacher.Desktop.Models;

public class RecurringScheduleItem
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = Guid.NewGuid().ToString();

    [JsonPropertyName("title")]
    public string Title { get; set; } = string.Empty;

    [JsonPropertyName("action_type")]
    public string ActionType { get; set; } = "alarm"; // "alarm", "board", "shutdown", "sleep", "restart"

    [JsonPropertyName("time_str")]
    public string TimeString { get; set; } = "09:00";

    [JsonPropertyName("ampm")]
    public string AmPm { get; set; } = "오전";

    [JsonPropertyName("hour12")]
    public int Hour12 { get; set; } = 9;

    [JsonPropertyName("minute")]
    public int Minute { get; set; } = 0;

    [JsonPropertyName("repeat_mode")]
    public string RepeatMode { get; set; } = "weekdays"; // "weekdays", "daily", "custom"

    [JsonPropertyName("repeat_days")]
    public List<int> RepeatDays { get; set; } = new() { 0, 1, 2, 3, 4 }; // 0=Mon, 4=Fri

    [JsonPropertyName("skip_holidays")]
    public bool SkipHolidays { get; set; } = true;

    [JsonPropertyName("enabled")]
    public bool Enabled { get; set; } = true;

    [JsonPropertyName("memo")]
    public string Memo { get; set; } = string.Empty;

    [JsonPropertyName("is_single")]
    public bool IsSingle { get; set; } = false;

    [JsonPropertyName("target_date")]
    public string TargetDate { get; set; } = string.Empty;

    [JsonPropertyName("is_completed")]
    public bool IsCompleted { get; set; } = false;

    // 📢 Student Display (Monitor 2) Alert & Timer Popup
    [JsonPropertyName("show_student_popup")]
    public bool ShowStudentPopup { get; set; } = false;

    [JsonPropertyName("popup_message")]
    public string PopupMessage { get; set; } = string.Empty;

    [JsonPropertyName("show_timer")]
    public bool ShowTimer { get; set; } = false;

    [JsonPropertyName("timer_duration_min")]
    public int TimerDurationMinutes { get; set; } = 10;

    // ⏰ 5-minute Advance Warning on Monitor 1 (Teacher screen)
    [JsonPropertyName("enable_advance_warning")]
    public bool EnableAdvanceWarning { get; set; } = true;

    [JsonPropertyName("advance_warning_min")]
    public int AdvanceWarningMinutes { get; set; } = 5;

    [JsonIgnore]
    public string ActionIcon => ActionType?.ToLowerInvariant() switch
    {
        "shutdown" => "🛑",
        "sleep" => "🌙",
        "restart" => "🔄",
        "board" => "📋",
        "student_alert" => "📢",
        "timer" => "⏱️",
        _ => ShowStudentPopup ? "📢" : "🔔"
    };

    [JsonIgnore]
    public string RepeatDisplay
    {
        get
        {
            if (IsSingle)
            {
                string dateStr = string.IsNullOrEmpty(TargetDate) ? "1회성" : TargetDate;
                return $"📅 단건 예약 ({dateStr})";
            }

            return RepeatMode switch
            {
                "daily" => "🔄 매일 반복",
                "weekdays" => "🔄 평일 반복 (월~금)",
                _ => "🔄 요일 지정 반복"
            };
        }
    }

    [JsonIgnore]
    public string StatusBadge
    {
        get
        {
            if (IsSingle && IsCompleted) return "✅ 실행완료";
            return Enabled ? "🟢 활성" : "⚪ 비활성";
        }
    }

    [JsonIgnore]
    public string FeatureSummary
    {
        get
        {
            var parts = new List<string>();
            if (EnableAdvanceWarning) parts.Add($"⏰ {AdvanceWarningMinutes}분 전 알림");
            if (ShowStudentPopup) parts.Add("📺 학생화면 팝업");
            if (ShowTimer) parts.Add($"⏱️ {TimerDurationMinutes}분 타이머");
            return parts.Count > 0 ? string.Join(" · ", parts) : string.Empty;
        }
    }
}

public class RecurringScheduleContainer
{
    [JsonPropertyName("schedules")]
    public List<RecurringScheduleItem> Schedules { get; set; } = new();
}
