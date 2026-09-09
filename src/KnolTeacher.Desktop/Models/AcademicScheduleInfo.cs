using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace KnolTeacher.Desktop.Models;

public class AcademicScheduleItem
{
    [JsonPropertyName("AA_YMD")]
    public string RawDate { get; set; } = string.Empty;

    [JsonPropertyName("EVENT_NM")]
    public string EventName { get; set; } = string.Empty;

    [JsonPropertyName("EVENT_CNTNT")]
    public string EventContent { get; set; } = string.Empty;

    [JsonPropertyName("SBTR_DD_SC_NM")]
    public string SubtractionDayType { get; set; } = string.Empty; // 공휴일, 휴업일, 해당없음

    [JsonPropertyName("AY")]
    public string AcademicYear { get; set; } = string.Empty;

    [JsonPropertyName("ONE_GRADE_EVENT_YN")]
    public string Grade1 { get; set; } = "Y";

    [JsonPropertyName("TW_GRADE_EVENT_YN")]
    public string Grade2 { get; set; } = "Y";

    [JsonPropertyName("THREE_GRADE_EVENT_YN")]
    public string Grade3 { get; set; } = "Y";

    [JsonPropertyName("FR_GRADE_EVENT_YN")]
    public string Grade4 { get; set; } = "Y";

    [JsonPropertyName("FIV_GRADE_EVENT_YN")]
    public string Grade5 { get; set; } = "Y";

    [JsonPropertyName("SIX_GRADE_EVENT_YN")]
    public string Grade6 { get; set; } = "Y";

    // Computed properties for UI
    [JsonIgnore]
    public DateTime? Date
    {
        get
        {
            if (RawDate.Length == 8 &&
                int.TryParse(RawDate.Substring(0, 4), out int y) &&
                int.TryParse(RawDate.Substring(4, 2), out int m) &&
                int.TryParse(RawDate.Substring(6, 2), out int d))
            {
                return new DateTime(y, m, d);
            }
            return null;
        }
    }

    [JsonIgnore]
    public bool IsHoliday => SubtractionDayType is "공휴일" or "휴업일" or "재량휴업일";

    [JsonIgnore]
    public string BadgeColor => SubtractionDayType switch
    {
        "공휴일" => "#EF4444",
        "휴업일" => "#F59E0B",
        _ => "#0284C7"
    };

    [JsonIgnore]
    public int DaysUntil
    {
        get
        {
            if (Date.HasValue)
            {
                return (Date.Value.Date - DateTime.Today).Days;
            }
            return int.MaxValue;
        }
    }

    [JsonIgnore]
    public string DDayText
    {
        get
        {
            int d = DaysUntil;
            if (d == 0) return "D-DAY";
            if (d > 0) return $"D-{d}";
            return $"D+{Math.Abs(d)}";
        }
    }

    [JsonIgnore]
    public string DisplayDateString => Date.HasValue ? Date.Value.ToString("M월 d일 (ddd)") : RawDate;
}

public class CalendarDayCell
{
    public DateTime Date { get; set; }
    public int DayNumber => Date.Day;
    public bool IsCurrentMonth { get; set; } = true;
    public bool IsToday => Date.Date == DateTime.Today;
    public bool IsSelected { get; set; } = false;
    public bool HasEvent => Events.Count > 0;
    public bool HasHoliday => Events.Exists(e => e.IsHoliday);
    public List<AcademicScheduleItem> Events { get; set; } = new();
    public string PrimaryEventText => Events.Count > 0 ? Events[0].EventName : string.Empty;

    public bool IsSunday => Date.DayOfWeek == DayOfWeek.Sunday;
    public bool IsSaturday => Date.DayOfWeek == DayOfWeek.Saturday;

    public string DayForeground
    {
        get
        {
            if (!IsCurrentMonth) return "#CBD5E1";
            if (HasHoliday || IsSunday) return "#EF4444";
            if (IsSaturday) return "#3B82F6";
            return "#334155";
        }
    }

    public string CellBackground
    {
        get
        {
            if (IsSelected) return "#FEF3C7";
            if (IsToday) return "#EFF6FF";
            return "Transparent";
        }
    }

    public string CellBorderBrush
    {
        get
        {
            if (IsSelected) return "#F59E0B";
            if (IsToday) return "#3B82F6";
            return "Transparent";
        }
    }

    public string DotColor => HasHoliday ? "#EF4444" : "#2563EB";
    public System.Windows.Visibility DotVisibility => HasEvent ? System.Windows.Visibility.Visible : System.Windows.Visibility.Collapsed;

    public List<TeacherCalendarEvent> TeacherEvents { get; set; } = new();
    public bool HasTeacherEvent => TeacherEvents.Count > 0;
    public System.Windows.Visibility TeacherDotVisibility => HasTeacherEvent ? System.Windows.Visibility.Visible : System.Windows.Visibility.Collapsed;
    public string TeacherDotColor => TeacherEvents.Count > 0 && !string.IsNullOrEmpty(TeacherEvents[0].Color) ? TeacherEvents[0].Color : "#10B981";
}


