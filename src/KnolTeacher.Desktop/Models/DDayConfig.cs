using System;

namespace KnolTeacher.Desktop.Models;

public class DDayConfig
{
    public string Title { get; set; } = "여름방학";
    public DateTime TargetDate { get; set; } = DateTime.Today.AddDays(14);
    public bool IsActive { get; set; } = true;
}
