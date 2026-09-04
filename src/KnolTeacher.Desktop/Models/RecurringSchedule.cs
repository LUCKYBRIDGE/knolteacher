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

    [JsonIgnore]
    public string ActionIcon => ActionType?.ToLowerInvariant() switch
    {
        "shutdown" => "🛑",
        "sleep" => "🌙",
        "restart" => "🔄",
        "board" => "📋",
        _ => "🔔"
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
}

public class RecurringScheduleContainer
{
    [JsonPropertyName("schedules")]
    public List<RecurringScheduleItem> Schedules { get; set; } = new();
}
