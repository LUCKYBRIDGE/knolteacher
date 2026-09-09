namespace KnolTeacher.Desktop.Views.Controls;

/// <summary>
/// Central presentation contract for a NolBoard widget.
/// Functional dependencies and view creation stay in StudentDisplayWindow;
/// workspace sizing/capabilities live here so they do not drift across entry points.
/// </summary>
public sealed record WidgetDefinition(
    string Type,
    string Title,
    double DefaultWidth,
    double DefaultHeight,
    double MinWidth,
    double MinHeight,
    bool AllowMultiple = false,
    bool CanResize = true,
    bool CanZoom = true);
