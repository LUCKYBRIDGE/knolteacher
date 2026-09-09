using System;
using System.Text.Json.Serialization;
using System.Windows.Media;

namespace KnolTeacher.Desktop.Models;

public class TeacherCalendarEvent
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = Guid.NewGuid().ToString();

    [JsonPropertyName("date")]
    public string Date { get; set; } = DateTime.Today.ToString("yyyy-MM-dd"); // yyyy-MM-dd

    [JsonPropertyName("title")]
    public string Title { get; set; } = string.Empty;

    [JsonPropertyName("memo")]
    public string Memo { get; set; } = string.Empty;

    [JsonPropertyName("is_all_day")]
    public bool IsAllDay { get; set; } = true;

    [JsonPropertyName("time")]
    public string Time { get; set; } = "10:00"; // HH:mm

    [JsonPropertyName("has_alarm")]
    public bool HasAlarm { get; set; } = false;

    [JsonPropertyName("alarm_minutes_before")]
    public int AlarmMinutesBefore { get; set; } = 10; // 0, 5, 10, 15, 30, 60, 1440

    [JsonPropertyName("color")]
    public string Color { get; set; } = "#3B82F6"; // #3B82F6, #10B981, #F59E0B, #EF4444, #8B5CF6

    [JsonPropertyName("is_alarm_triggered")]
    public bool IsAlarmTriggered { get; set; } = false;

    [JsonIgnore]
    public string DisplayTimeText => IsAllDay ? "종일" : Time;

    [JsonIgnore]
    public string AlarmText => HasAlarm
        ? (AlarmMinutesBefore == 0 ? "정각 알람 🔔" : (AlarmMinutesBefore >= 1440 ? "1일 전 알람 🔔" : $"{AlarmMinutesBefore}분 전 🔔"))
        : string.Empty;

    [JsonIgnore]
    public Brush ColorBrush
    {
        get
        {
            try
            {
                return (Brush)new BrushConverter().ConvertFromString(Color)!;
            }
            catch
            {
                return Brushes.DodgerBlue;
            }
        }
    }

    [JsonIgnore]
    public Brush LightBackgroundBrush
    {
        get
        {
            return Color switch
            {
                "#10B981" => (Brush)new BrushConverter().ConvertFromString("#ECFDF5")!,
                "#F59E0B" => (Brush)new BrushConverter().ConvertFromString("#FFFBEB")!,
                "#EF4444" => (Brush)new BrushConverter().ConvertFromString("#FEF2F2")!,
                "#8B5CF6" => (Brush)new BrushConverter().ConvertFromString("#F5F3FF")!,
                _ => (Brush)new BrushConverter().ConvertFromString("#EFF6FF")!
            };
        }
    }

    [JsonIgnore]
    public Brush BorderBrush
    {
        get
        {
            return Color switch
            {
                "#10B981" => (Brush)new BrushConverter().ConvertFromString("#A7F3D0")!,
                "#F59E0B" => (Brush)new BrushConverter().ConvertFromString("#FDE68A")!,
                "#EF4444" => (Brush)new BrushConverter().ConvertFromString("#FECACA")!,
                "#8B5CF6" => (Brush)new BrushConverter().ConvertFromString("#DDD6FE")!,
                _ => (Brush)new BrushConverter().ConvertFromString("#BFDBFE")!
            };
        }
    }
}
