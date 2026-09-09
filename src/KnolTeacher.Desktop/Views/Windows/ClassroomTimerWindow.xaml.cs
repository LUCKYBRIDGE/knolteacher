using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class ClassroomTimerWindow : Window
{
    private readonly ISoundService _soundService;
    private readonly IDisplayManager? _displayManager;
    private readonly DispatcherTimer _timer;
    private int _remainingSeconds = 300; // 5 mins
    private int _initialSeconds = 300;
    private bool _isRunning = false;
    private bool _isPieMode = false;
    private readonly IConfigService? _configService;
    private int _currentMonitorIndex = 1;

    public ClassroomTimerWindow(ISoundService soundService, IDisplayManager? displayManager = null, IConfigService? configService = null)
    {
        _soundService = soundService;
        _displayManager = displayManager ?? (Application.Current as App)?.Services?.GetService(typeof(IDisplayManager)) as IDisplayManager;
        _configService = configService ?? (Application.Current as App)?.Services?.GetService(typeof(IConfigService)) as IConfigService;
        InitializeComponent();

        _timer = new DispatcherTimer
        {
            Interval = TimeSpan.FromSeconds(1)
        };
        _timer.Tick += Timer_Tick;

        Loaded += (s, e) => PositionToDefaultMonitor();

        UpdateDisplay();
    }

    public void PositionToDefaultMonitor()
    {
        if (_displayManager != null)
        {
            int preferred = _configService?.TimerTargetMonitorIndex ?? 1;
            if (preferred == 1 && _displayManager.ScreenCount >= 2)
            {
                _currentMonitorIndex = 1;
                _displayManager.MoveToStudentMonitor(this, maximize: false);
            }
            else
            {
                _currentMonitorIndex = 0;
                _displayManager.MoveWindowToScreen(this, 0, maximize: false);
            }
            UpdateMonitorButtonText();
        }
    }

    private void UpdateMonitorButtonText()
    {
        if (BtnSwitchMonitor != null)
        {
            BtnSwitchMonitor.Content = _currentMonitorIndex == 1 ? "📺 모니터 2 (학생용)" : "💻 모니터 1 (메인)";
        }
    }

    private void BtnSwitchMonitor_Click(object sender, RoutedEventArgs e)
    {
        if (_displayManager == null || _displayManager.ScreenCount < 2) return;
        _currentMonitorIndex = _currentMonitorIndex == 1 ? 0 : 1;
        _displayManager.MoveWindowToScreen(this, _currentMonitorIndex, maximize: false);
        UpdateMonitorButtonText();

        if (_configService != null)
        {
            _configService.TimerTargetMonitorIndex = _currentMonitorIndex;
            _configService.SaveTimerSettings();
        }
    }

    private bool _hasPlayedEndChime = false;

    private void Timer_Tick(object? sender, EventArgs e)
    {
        _remainingSeconds--;
        UpdateDisplay();

        if (_remainingSeconds == 0 && !_hasPlayedEndChime)
        {
            _hasPlayedEndChime = true;
            try
            {
                _soundService.PlayChime();
            }
            catch { }
        }
    }

    private void UpdateDisplay()
    {
        if (_remainingSeconds >= 0)
        {
            int min = _remainingSeconds / 60;
            int sec = _remainingSeconds % 60;
            TxtTime.Text = $"{min:D2}:{sec:D2}";
            TxtTime.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#38BDF8"));
            if (TxtOverdueTime != null)
            {
                TxtOverdueTime.Visibility = Visibility.Collapsed;
            }

            if (TxtPieTime != null)
            {
                TxtPieTime.Text = $"{min:D2}:{sec:D2}";
                TxtPieTime.Foreground = Brushes.White;
            }

            if (!_isRunning && TbMinutes != null && TbSeconds != null)
            {
                TbMinutes.Text = $"{min:D2}";
                TbSeconds.Text = $"{sec:D2}";
            }
        }
        else
        {
            // Negative Overdue Time (e.g. 0:00 and (-0:55) in bold red)
            int overdueSec = Math.Abs(_remainingSeconds);
            int oMin = overdueSec / 60;
            int oSec = overdueSec % 60;

            TxtTime.Text = "0:00";
            TxtTime.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#EF4444"));

            if (TxtOverdueTime != null)
            {
                TxtOverdueTime.Text = $"(-{oMin}:{oSec:D2})";
                TxtOverdueTime.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#EF4444"));
                TxtOverdueTime.Visibility = Visibility.Visible;
            }

            if (TxtPieTime != null)
            {
                TxtPieTime.Text = $"0:00\n(-{oMin}:{oSec:D2})";
                TxtPieTime.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#EF4444"));
            }
        }

        UpdatePieGeometry();
    }

    private void BtnApplyManualTime_Click(object sender, RoutedEventArgs e)
    {
        if (TbMinutes != null && TbSeconds != null &&
            int.TryParse(TbMinutes.Text.Trim(), out int m) &&
            int.TryParse(TbSeconds.Text.Trim(), out int s))
        {
            int total = Math.Max(1, m * 60 + s);
            _timer.Stop();
            _isRunning = false;
            _hasPlayedEndChime = false;
            BtnStartPause.Content = "▶ 시작";
            _initialSeconds = total;
            _remainingSeconds = total;
            UpdateDisplay();
        }
    }

    private void TbTime_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
        {
            BtnApplyManualTime_Click(sender, e);
        }
    }

    private void BtnAddSec_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string deltaStr && int.TryParse(deltaStr, out int delta))
        {
            _remainingSeconds += delta;
            _initialSeconds = Math.Max(_initialSeconds, _remainingSeconds);
            if (_remainingSeconds > 0) _hasPlayedEndChime = false;
            UpdateDisplay();
        }
    }

    private void BtnStartPause_Click(object sender, RoutedEventArgs e)
    {
        if (_isRunning)
        {
            _timer.Stop();
            _isRunning = false;
            BtnStartPause.Content = "▶ 계속";
        }
        else
        {
            if (_remainingSeconds == 0 && !_hasPlayedEndChime)
            {
                _remainingSeconds = _initialSeconds;
            }
            _timer.Start();
            _isRunning = true;
            BtnStartPause.Content = "⏸ 일시정지";
        }
    }

    private void BtnReset_Click(object sender, RoutedEventArgs e)
    {
        _timer.Stop();
        _isRunning = false;
        _hasPlayedEndChime = false;
        _remainingSeconds = _initialSeconds;
        BtnStartPause.Content = "▶ 시작";
        UpdateDisplay();
    }

    private void BtnPreset_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string minStr && int.TryParse(minStr, out int mins))
        {
            _timer.Stop();
            _isRunning = false;
            _hasPlayedEndChime = false;
            BtnStartPause.Content = "▶ 시작";
            _initialSeconds = mins * 60;
            _remainingSeconds = _initialSeconds;
            UpdateDisplay();
        }
    }

    private void BtnTogglePieMode_Click(object sender, RoutedEventArgs e)
    {
        _isPieMode = !_isPieMode;
        if (PanelDigitalView != null) PanelDigitalView.Visibility = _isPieMode ? Visibility.Collapsed : Visibility.Visible;
        if (PanelPieView != null) PanelPieView.Visibility = _isPieMode ? Visibility.Visible : Visibility.Collapsed;
        if (BtnTogglePieMode != null)
        {
            BtnTogglePieMode.Content = _isPieMode ? "⏱️ 숫자 타이머" : "🥧 원형 타이머";
        }
        UpdatePieGeometry();
    }

    private void UpdatePieGeometry()
    {
        if (TxtPieTime != null)
        {
            int min = _remainingSeconds / 60;
            int sec = _remainingSeconds % 60;
            TxtPieTime.Text = $"{min:D2}:{sec:D2}";
        }

        if (PathPieSlice == null) return;

        double total = Math.Max(1, _initialSeconds);
        double fraction = Math.Clamp((double)_remainingSeconds / total, 0.0, 1.0);

        // Color coding based on remaining time percentage
        string colorHex = fraction switch
        {
            > 0.5 => "#38BDF8", // Sky blue (> 50%)
            > 0.2 => "#F59E0B", // Amber warning (20% ~ 50%)
            _ => "#EF4444"      // Red alert (< 20%)
        };

        try
        {
            PathPieSlice.Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString(colorHex));
        }
        catch
        {
            PathPieSlice.Fill = Brushes.SkyBlue;
        }

        if (fraction <= 0.001)
        {
            PathPieSlice.Data = null;
            return;
        }

        double cx = 100;
        double cy = 100;
        double r = 96;

        if (fraction >= 0.999)
        {
            PathPieSlice.Data = new EllipseGeometry(new Point(cx, cy), r, r);
            return;
        }

        // Clockwise arc from 12 o'clock (0 rad)
        // 12 o'clock is (cx, cy - r)
        double angleRad = fraction * 2.0 * Math.PI;
        double endX = cx + r * Math.Sin(angleRad);
        double endY = cy - r * Math.Cos(angleRad);

        var pathFigure = new PathFigure
        {
            StartPoint = new Point(cx, cy),
            IsClosed = true,
            IsFilled = true
        };

        pathFigure.Segments.Add(new LineSegment(new Point(cx, cy - r), true));
        pathFigure.Segments.Add(new ArcSegment(
            new Point(endX, endY),
            new Size(r, r),
            0,
            angleRad > Math.PI, // Large arc if angle > 180 degrees
            SweepDirection.Clockwise,
            true
        ));

        var pathGeometry = new PathGeometry();
        pathGeometry.Figures.Add(pathFigure);
        PathPieSlice.Data = pathGeometry;
    }

    protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
    {
        // Don't dispose on window close; just hide to preserve state
        e.Cancel = true;
        Hide();
    }
}
