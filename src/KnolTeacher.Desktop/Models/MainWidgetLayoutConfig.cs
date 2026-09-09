using System;
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
    public int LayoutVersion { get; set; } = 2;
    public bool IsLocked { get; set; } = false;
    public string ActivePreset { get; set; } = "default";
    public List<MainWidgetState> Widgets { get; set; } = new();

    public static MainWidgetLayoutConfig CreateDefault(double canvasWidth = 1460, double canvasHeight = 860)
    {
        double col1W = Math.Max(340, Math.Min(400, canvasWidth * 0.27));
        double col2W = Math.Max(460, Math.Min(560, canvasWidth * 0.41));
        double col3W = Math.Max(340, Math.Min(440, canvasWidth * 0.30));

        double gap = 16;
        double x1 = 12;
        double x2 = x1 + col1W + gap;
        double x3 = x2 + col2W + gap;

        double totalH = Math.Max(780, canvasHeight - 24);
        double h1_1 = Math.Round(totalH * 0.58);
        double h1_2 = totalH - h1_1 - gap;

        return new MainWidgetLayoutConfig
        {
            LayoutVersion = 2,
            IsLocked = false,
            ActivePreset = "default",
            Widgets = new List<MainWidgetState>
            {
                new() { Id = "timetable", X = x1, Y = 12, Width = col1W, Height = h1_1, IsVisible = true, ZIndex = 1 },
                new() { Id = "todo", X = x1, Y = 12 + h1_1 + gap, Width = col1W, Height = h1_2, IsVisible = true, ZIndex = 2 },
                new() { Id = "calendar", X = x2, Y = 12, Width = col2W, Height = totalH, IsVisible = true, ZIndex = 3 },
                new() { Id = "meal", X = x3, Y = 12, Width = col3W, Height = totalH, IsVisible = true, ZIndex = 4 },
                new() { Id = "timer", X = x1 + 20, Y = 30, Width = 360, Height = 260, IsVisible = false, ZIndex = 10 },
                new() { Id = "picker", X = x1 + 40, Y = 310, Width = 360, Height = 280, IsVisible = false, ZIndex = 11 },
                new() { Id = "notice", X = x2 + 20, Y = 30, Width = 480, Height = 220, IsVisible = false, ZIndex = 12 },
                new() { Id = "dday", X = x3 - 20, Y = 40, Width = 360, Height = 220, IsVisible = false, ZIndex = 13 },
                new() { Id = "weather", X = x3, Y = 360, Width = 360, Height = 280, IsVisible = false, ZIndex = 14 }
            }
        };
    }
}
