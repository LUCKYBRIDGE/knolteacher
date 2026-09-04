using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

namespace KnolTeacher.Desktop.Services;

public interface IDisplayManager
{
    int ScreenCount { get; }
    int RecommendedStudentMonitorIndex { get; }
    List<ScreenInfo> GetScreens();
    void MoveWindowToScreen(Window window, int screenIndex, bool maximize = false);
    void MoveToStudentMonitor(Window window, bool maximize = false);
}

public class ScreenInfo
{
    public int Index { get; set; }
    public string DeviceName { get; set; } = string.Empty;
    public bool IsPrimary { get; set; }
    public Rect Bounds { get; set; }
    public Rect WorkingArea { get; set; }
    public string DisplayLabel => Index == 1 ? $"📺 모니터 {Index + 1} [학생용 전자칠판/TV] (권장)" : (IsPrimary ? $"💻 모니터 {Index + 1} [선생님 메인 PC]" : $"🖥️ 모니터 {Index + 1}");
}

public class DisplayManager : IDisplayManager
{
    public int ScreenCount => GetScreens().Count;
    public int RecommendedStudentMonitorIndex => ScreenCount >= 2 ? 1 : 0;

    public List<ScreenInfo> GetScreens()
    {
        var rawScreens = new List<ScreenInfo>();
        int rawIndex = 0;

        NativeMethods.EnumDisplayMonitors(IntPtr.Zero, IntPtr.Zero,
            (IntPtr hMonitor, IntPtr hdcMonitor, ref NativeMethods.RECT lprcMonitor, IntPtr dwData) =>
            {
                var mi = new NativeMethods.MONITORINFOEX();
                mi.cbSize = Marshal.SizeOf(typeof(NativeMethods.MONITORINFOEX));

                if (NativeMethods.GetMonitorInfo(hMonitor, ref mi))
                {
                    rawScreens.Add(new ScreenInfo
                    {
                        Index = rawIndex++,
                        DeviceName = mi.szDevice ?? $"Monitor {rawIndex}",
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

        // Sort so that Primary monitor is index 0 (선생님 메인 PC),
        // and secondary monitor is index 1 (학생용 전자칠판/TV 권장).
        var sorted = rawScreens.OrderByDescending(s => s.IsPrimary).ToList();
        for (int i = 0; i < sorted.Count; i++)
        {
            sorted[i].Index = i;
        }

        return sorted;
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
            if (window.WindowState == WindowState.Maximized)
            {
                window.WindowState = WindowState.Normal;
            }

            double w = !double.IsNaN(window.Width) && window.Width > 0 ? window.Width : (window.ActualWidth > 0 ? window.ActualWidth : 520);
            double h = !double.IsNaN(window.Height) && window.Height > 0 ? window.Height : (window.ActualHeight > 0 ? window.ActualHeight : 420);

            window.Left = area.Left + (area.Width - w) / 2;
            window.Top = area.Top + (area.Height - h) / 2;
        }
    }

    public void MoveToStudentMonitor(Window window, bool maximize = false)
    {
        MoveWindowToScreen(window, RecommendedStudentMonitorIndex, maximize);
    }
}
