using System;
using System.Collections.Generic;

namespace KnolTeacher.Desktop.Models;

public class ChecklistStudentItem
{
    public int Number { get; set; }
    public string Name { get; set; } = string.Empty;
    public bool IsChecked { get; set; }
    public DateTime? CheckedAt { get; set; }
}

public class ChecklistTabItem
{
    public string Id { get; set; } = Guid.NewGuid().ToString();
    public string Title { get; set; } = "과제 체크";
    public List<ChecklistStudentItem> Students { get; set; } = new();
}

public class ChecklistStore
{
    public string ActiveTabId { get; set; } = string.Empty;
    public bool ShowStudentNames { get; set; } = false;
    public List<ChecklistTabItem> Tabs { get; set; } = new();
}
