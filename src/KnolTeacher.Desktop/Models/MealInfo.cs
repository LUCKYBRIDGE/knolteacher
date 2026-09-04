using System;
using System.Collections.Generic;

namespace KnolTeacher.Desktop.Models;

public class MealInfo
{
    public string DateString { get; set; } = string.Empty;
    public List<string> Dishes { get; set; } = new();
    public string Calorie { get; set; } = string.Empty;
    public string Origin { get; set; } = string.Empty;
    public string MenuText => Dishes.Count > 0 ? " • " + string.Join("\n • ", Dishes) : "등록된 급식 식단표가 없습니다.";
}

public class TimetablePeriodItem
{
    public int Period { get; set; }
    public string Subject { get; set; } = string.Empty;
    public string TimeRange { get; set; } = string.Empty;
}
