using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class ClassroomCountdownOverlayWindow : Window
{
    private readonly PeriodCountdownItem _config;
    private readonly ISoundService? _soundService;
    private readonly DispatcherTimer _timer;
    private int _remainingSeconds;
    private int _initialSeconds;
    private bool _isCompleted = false;
    private int _autoCloseSecondsRemaining;

    public ClassroomCountdownOverlayWindow(
        PeriodCountdownItem config,
        string periodName,
        string subjectName,
        ISoundService? soundService = null,
        int? overrideDurationSeconds = null)
    {
        _config = config;
        _soundService = soundService;
        InitializeComponent();

        int duration = overrideDurationSeconds ?? _config.CountdownDurationSeconds;
        _initialSeconds = Math.Max(1, duration);
        _remainingSeconds = _initialSeconds;
        _autoCloseSecondsRemaining = Math.Max(3, _config.AutoCloseSeconds);

        TxtPeriodBadge.Text = $"🕒 {periodName} ({subjectName}) 수업 준비";
        string notice = (_config.PreNoticeText ?? "")
            .Replace("{교시}", periodName)
            .Replace("{과목}", subjectName);
        TxtNotice.Text = notice;

        string postNotice = (_config.PostNoticeText ?? "")
            .Replace("{교시}", periodName)
            .Replace("{과목}", subjectName);
        TxtPostNotice.Text = postNotice;

        UpdateDigitsDisplay();

        _timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(1) };
        _timer.Tick += Timer_Tick;

        PreviewKeyDown += (s, e) =>
        {
            if (e.Key == Key.Escape)
            {
                CloseWindow();
                e.Handled = true;
            }
        };

        Loaded += (s, e) =>
        {
            PositionToMonitor(_config.TargetMonitorIndex);
            _timer.Start();
        };
    }

    private void PositionToMonitor(int monitorIndex)
    {
        try
        {
            var displayManager = (Application.Current as App)?.Services?.GetService(typeof(IDisplayManager)) as IDisplayManager;
            if (displayManager != null)
            {
                if (monitorIndex == 1)
                {
                    displayManager.MoveToStudentMonitor(this, maximize: true);
                }
                else
                {
                    int screenIdx = Math.Min(Math.Max(0, monitorIndex), displayManager.ScreenCount - 1);
                    displayManager.MoveWindowToScreen(this, screenIdx, maximize: true);
                }
                return;
            }

            NativeMethods.RECT rect;
            if (monitorIndex < 0)
            {
                // Current cursor monitor
                rect = NativeMethods.GetCurrentMonitorRect();
            }
            else
            {
                // Enumerate and find monitor by index
                var monitors = new List<NativeMethods.RECT>();
                NativeMethods.EnumDisplayMonitors(IntPtr.Zero, IntPtr.Zero, (IntPtr hMon, IntPtr hdc, ref NativeMethods.RECT r, IntPtr d) =>
                {
                    monitors.Add(r);
                    return true;
                }, IntPtr.Zero);

                if (monitorIndex < monitors.Count)
                {
                    rect = monitors[monitorIndex];
                }
                else
                {
                    rect = NativeMethods.GetCurrentMonitorRect();
                }
            }

            int left = rect.Left;
            int top = rect.Top;
            int width = rect.Right - rect.Left;
            int height = rect.Bottom - rect.Top;

            var helper = new System.Windows.Interop.WindowInteropHelper(this);
            NativeMethods.SetWindowPos(helper.Handle, IntPtr.Zero, left, top, width, height, NativeMethods.SWP_SHOWWINDOW | NativeMethods.SWP_NOZORDER);
        }
        catch { }
    }

    private void Timer_Tick(object? sender, EventArgs e)
    {
        if (!_isCompleted)
        {
            _remainingSeconds--;
            UpdateDigitsDisplay();

            if (_remainingSeconds <= 0)
            {
                _isCompleted = true;
                BorderComplete.Visibility = Visibility.Visible;
                TxtCountdown.Text = "00:00";
                TxtCountdown.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#10B981"));
                PbProgress.Value = 0;

                if (_config.PlaySoundChime)
                {
                    _soundService?.PlayChime();
                }

                TxtAutoCloseNotice.Text = $"{_autoCloseSecondsRemaining}초 후 자동으로 닫힙니다...";
            }
        }
        else
        {
            _autoCloseSecondsRemaining--;
            if (_autoCloseSecondsRemaining <= 0)
            {
                CloseWindow();
            }
            else
            {
                TxtAutoCloseNotice.Text = $"{_autoCloseSecondsRemaining}초 후 자동으로 닫힙니다...";
            }
        }
    }

    private void UpdateDigitsDisplay()
    {
        int m = Math.Max(0, _remainingSeconds / 60);
        int s = Math.Max(0, _remainingSeconds % 60);
        TxtCountdown.Text = $"{m:D2}:{s:D2}";

        double pct = _initialSeconds > 0 ? ((double)_remainingSeconds / _initialSeconds) * 100 : 0;
        PbProgress.Value = Math.Clamp(pct, 0, 100);
        TxtAutoCloseNotice.Text = $"수업 준비 카운트다운 진행 중 (잔여: {m}분 {s}초)";
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e)
    {
        CloseWindow();
    }

    private void CloseWindow()
    {
        _timer.Stop();
        Close();
    }
}
