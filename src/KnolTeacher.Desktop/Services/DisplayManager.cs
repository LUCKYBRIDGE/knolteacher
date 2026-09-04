using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

namespace KnolTeacher.Desktop.Services;

public interface IDisplayManager
{
    int ScreenCount { get; }
    List<ScreenInfo> GetScreens();
    void MoveWindowToScreen(Window window, int screenIndex, bool maximize = false);
}

public class ScreenInfo
{
    public int Index { get; set; }
    public string DeviceName { get; set; } = string.Empty;
    public bool IsPrimary { get; set; }
    public Rect Bounds { get; set; }
    public Rect WorkingArea { get; set; }
}

public class DisplayManager : IDisplayManager
{
    public int ScreenCount => GetScreens().Count;

    public List<ScreenInfo> GetScreens()
    {
        var screens = new List<ScreenInfo>();
        int index = 0;

        NativeMethods.EnumDisplayMonitors(IntPtr.Zero, IntPtr.Zero,
            (IntPtr hMonitor, IntPtr hdcMonitor, ref NativeMethods.RECT lprcMonitor, IntPtr dwData) =>
            {
                var mi = new NativeMethods.MONITORINFOEX();
                mi.cbSize = Marshal.SizeOf(typeof(NativeMethods.MONITORINFOEX));

                if (NativeMethods.GetMonitorInfo(hMonitor, ref mi))
                {
                    screens.Add(new ScreenInfo
                    {
                        Index = index++,
                        DeviceName = mi.szDevice ?? $"Monitor {index}",
                        IsPrimary = (mi.dwFlags & NativeMethods.MONITORINFOF_PRIMARY) != 0,
                        Bounds = new Rect(mi.rcMonitor.Left, mi.rcMonitor.Top,
                                          mi.rcMonitor.Right - mi.rcMonitor.Left,
                                          mi.rcMonitor.Bottom - mi.rcMonitor.Top),
                        WorkingArea = new Rect(mi.rcWork.Left, mi.rcWork.Top,
                                              mi.rcWork.Right - mi.rcWork.Left,
                                              mi.rcWork.Bottom - mi.rcWork.Top)
                    });
                }
                return true;
            }, IntPtr.Zero);

        return screens;
    }

    public void MoveWindowToScreen(Window window, int screenIndex, bool maximize = false)
    {
        var screens = GetScreens();
        if (screens.Count == 0) return;

        if (screenIndex < 0 || screenIndex >= screens.Count)
        {
            screenIndex = 0;
        }

        var targetScreen = screens[screenIndex];
        var area = targetScreen.WorkingArea;

        window.WindowStartupLocation = WindowStartupLocation.Manual;

        if (maximize)
        {
            window.WindowState = WindowState.Normal;
            window.Left = area.Left;
            window.Top = area.Top;
            window.Width = area.Width;
            window.Height = area.Height;
            window.WindowState = WindowState.Maximized;
        }
        else
        {
            window.Left = area.Left + (area.Width - window.Width) / 2;
            window.Top = area.Top + (area.Height - window.Height) / 2;
        }
    }
}
