using System.Collections.Generic;

namespace KnolTeacher.Desktop.Models;

public class NolboardWidgetState
{
    public string Tag { get; set; } = string.Empty;
    public double X { get; set; }
    public double Y { get; set; }
    public double Width { get; set; }
    public double Height { get; set; }
}

public class NolboardLayoutConfig
{
    public const int CurrentSchemaVersion = 2;

    public int SchemaVersion { get; set; } = CurrentSchemaVersion;
    public bool HasCustomLayout { get; set; } = false;
    public double CanvasWidth { get; set; }
    public double CanvasHeight { get; set; }
    public List<NolboardWidgetState> Widgets { get; set; } = new();
}
