using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class TimerWidgetView : UserControl
{
    private readonly ISoundService? _soundService;
    private readonly DispatcherTimer _timer;
    private int _remainingSeconds = 300;
    private int _initialSeconds = 300;
    private bool _isRunning = false;

    public TimerWidgetView(ISoundService? soundService = null)
    {
        _soundService = soundService;
        InitializeComponent();

        _timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(1) };
        _timer.Tick += Timer_Tick;
        UpdateDisplay();
    }

    private void Timer_Tick(object? sender, EventArgs e)
    {
        if (_remainingSeconds > 0)
        {
            _remainingSeconds--;
            UpdateDisplay();

            if (_remainingSeconds == 0)
            {
                _timer.Stop();
                _isRunning = false;
                BtnStartPause.Content = "▶ 시작";
                TxtDisplay.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#EF4444"));
                TxtDisplay.Text = "종료!";
                _soundService?.PlayChime();
            }
        }
    }

    private void UpdateDisplay()
    {
        int m = _remainingSeconds / 60;
        int s = _remainingSeconds % 60;
        TxtDisplay.Text = $"{m:D2}:{s:D2}";
        TxtDisplay.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#38BDF8"));

        if (!_isRunning && TbMinutes != null && TbSeconds != null)
        {
            TbMinutes.Text = $"{m:D2}";
            TbSeconds.Text = $"{s:D2}";
        }
    }

    private void BtnApplyManualTime_Click(object sender, RoutedEventArgs e)
    {
        if (TbMinutes != null && TbSeconds != null &&
            int.TryParse(TbMinutes.Text, out int m) &&
            int.TryParse(TbSeconds.Text, out int s))
        {
            int total = Math.Max(1, m * 60 + s);
            _timer.Stop();
            _isRunning = false;
            BtnStartPause.Content = "▶ 시작";
            BtnStartPause.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0284C7"));
            _initialSeconds = total;
            _remainingSeconds = total;
            UpdateDisplay();
        }
    }

    private void TbTime_KeyDown(object sender, System.Windows.Input.KeyEventArgs e)
    {
        if (e.Key == System.Windows.Input.Key.Enter)
        {
            BtnApplyManualTime_Click(sender, e);
        }
    }

    private void BtnAddSec_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string deltaStr && int.TryParse(deltaStr, out int delta))
        {
            _remainingSeconds = Math.Max(0, _remainingSeconds + delta);
            _initialSeconds = Math.Max(_initialSeconds, _remainingSeconds);
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
            BtnStartPause.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0284C7"));
        }
        else
        {
            if (_remainingSeconds <= 0)
            {
                _remainingSeconds = _initialSeconds;
            }
            _timer.Start();
            _isRunning = true;
            BtnStartPause.Content = "⏸ 일시정지";
            BtnStartPause.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#EA580C"));
        }
    }

    private void BtnReset_Click(object sender, RoutedEventArgs e)
    {
        _timer.Stop();
        _isRunning = false;
        _remainingSeconds = _initialSeconds;
        BtnStartPause.Content = "▶ 시작";
        BtnStartPause.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0284C7"));
        UpdateDisplay();
    }

    private void BtnPreset_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string secStr && int.TryParse(secStr, out int sec))
        {
            _timer.Stop();
            _isRunning = false;
            BtnStartPause.Content = "▶ 시작";
            BtnStartPause.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0284C7"));
            _initialSeconds = sec;
            _remainingSeconds = sec;
            UpdateDisplay();
        }
    }
}
