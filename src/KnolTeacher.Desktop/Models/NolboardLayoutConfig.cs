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
    /// <summary>
    /// Layout schema version. Version 1 files had no explicit schema/canvas metadata.
    /// </summary>
    public int SchemaVersion { get; set; } = 2;

    public bool HasCustomLayout { get; set; } = false;

    /// <summary>
    /// Canvas dimensions at save time. Used to restore/clamp layouts safely on another display size.
    /// Zero means legacy/unknown and keeps the existing absolute-position behavior.
    /// </summary>
    public double CanvasWidth { get; set; }
    public double CanvasHeight { get; set; }

    public List<NolboardWidgetState> Widgets { get; set; } = new();
}
