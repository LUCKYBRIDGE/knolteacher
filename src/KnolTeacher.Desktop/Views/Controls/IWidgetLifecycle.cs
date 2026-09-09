using System;

namespace KnolTeacher.Desktop.Views.Controls;

/// <summary>
/// Explicit lifecycle contract for NolBoard widget content.
/// Hide/show is treated as deactivate/activate, while removing a widget disposes it.
/// </summary>
public interface IWidgetLifecycle : IDisposable
{
    void Activate();
    void Deactivate();
}
