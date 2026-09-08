using System.Collections.Generic;

namespace KnolTeacher.Desktop.Models;

public class MainWidgetState
{
    public string Id { get; set; } = string.Empty;
    public double X { get; set; }
    public double Y { get; set; }
    public double Width { get; set; }
    public double Height { get; set; }
    public bool IsVisible { get; set; } = true;
    public int ZIndex { get; set; } = 1;
}

public class MainWidgetLayoutConfig
{
    public bool IsLocked { get; set; } = false;
    public string ActivePreset { get; set; } = "default";
    public List<MainWidgetState> Widgets { get; set; } = new();
}
