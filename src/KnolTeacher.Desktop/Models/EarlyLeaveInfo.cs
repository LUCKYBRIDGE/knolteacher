using System;
using System.Collections.Generic;

namespace KnolTeacher.Desktop.Models;

public class EarlyLeaveCalculationResult
{
    public int Year { get; set; }
    public int Month { get; set; }
    public int TotalCalendarDays { get; set; }
    public int WeekendDays { get; set; }
    public int HolidayAndVacationDays { get; set; }
    public int NetWorkDays { get; set; }
    public int RequiredWorkDays { get; set; } = 15;
    public bool IsEligibleForEarlyLeave => NetWorkDays >= RequiredWorkDays;
    public int MarginDays => NetWorkDays - RequiredWorkDays;
    public List<DateTime> OffDays { get; set; } = new();
    public string SummaryMessage { get; set; } = string.Empty;
}
