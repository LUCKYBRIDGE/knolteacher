using System;
using System.Collections.Generic;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Models;

public class DataSharePackage
{
    public string AppName { get; set; } = "KnolTeacher";
    public string Version { get; set; } = "2.9.0";
    public DateTime ExportedAt { get; set; } = DateTime.Now;
    public string Description { get; set; } = "놀티쳐 교실 맞춤 설정 및 공유 패키지";

    public MainWidgetLayoutConfig? MainWidgetLayout { get; set; }
    public TimetableSettings? TimetableSettings { get; set; }
    public PeriodAlarmSystemConfig? PeriodAlarmConfig { get; set; }
    public BoardSetStore? BoardSetStore { get; set; }
    public List<StudentItem>? Students { get; set; }
    public List<AcademicScheduleItem>? AcademicSchedules { get; set; }
}

public class TemplateImportResult
{
    public bool Success { get; set; }
    public string Message { get; set; } = string.Empty;
    public int ItemCount { get; set; }
}
