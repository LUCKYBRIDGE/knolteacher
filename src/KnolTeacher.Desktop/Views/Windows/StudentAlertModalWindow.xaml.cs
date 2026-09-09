using System;
using System.Windows;
using System.Windows.Input;
using System.Windows.Threading;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class StudentAlertModalWindow : Window
{
    private readonly DispatcherTimer _timer;
    private int _remainingSeconds;
    private int _totalSeconds;
    private bool _isPaused = false;
    private readonly ISoundService? _soundService;

    public StudentAlertModalWindow(
        string title,
        string message,
        bool showTimer = false,
        int timerMinutes = 10,
        ISoundService? soundService = null,
        string emoji = "🧹",
        string category = "교실 전체 알림")
    {
        _soundService = soundService;
        InitializeComponent();

        TxtTitle.Text = string.IsNullOrWhiteSpace(title) ? "교실 안내 알림" : title;
        TxtMessage.Text = string.IsNullOrWhiteSpace(message) ? "선생님의 지도와 안내에 따라 질서 있게 행동합시다." : message;
        TxtMainEmoji.Text = string.IsNullOrWhiteSpace(emoji) ? "📢" : emoji;
        TxtHeaderBadge.Text = category;

        if (showTimer && timerMinutes > 0)
        {
            PanelTimer.Visibility = Visibility.Visible;
            _totalSeconds = timerMinutes * 60;
            _remainingSeconds = _totalSeconds;
            UpdateTimerDisplay();

            _timer = new DispatcherTimer
            {
                Interval = TimeSpan.FromSeconds(1)
            };
            _timer.Tick += Timer_Tick;
            _timer.Start();
        }
        else
        {
            PanelTimer.Visibility = Visibility.Collapsed;
            _timer = new DispatcherTimer(); // dummy
        }

        Loaded += (s, e) =>
        {
            try
            {
                _soundService?.PlayChime();
            }
            catch { }
        };
    }

    private void Timer_Tick(object? sender, EventArgs e)
    {
        if (_isPaused) return;

        if (_remainingSeconds > 0)
        {
            _remainingSeconds--;
            UpdateTimerDisplay();

            if (_remainingSeconds == 0)
            {
                _timer.Stop();
                try
                {
                    _soundService?.PlayChime();
                }
                catch { }
                TxtTimerDigits.Text = "종료!";
                TxtTimerDigits.Foreground = System.Windows.Media.Brushes.OrangeRed;
            }
        }
    }

    private void UpdateTimerDisplay()
    {
        int min = _remainingSeconds / 60;
        int sec = _remainingSeconds % 60;
        TxtTimerDigits.Text = $"{min:00}:{sec:00}";

        if (_totalSeconds > 0)
        {
            double pct = (double)_remainingSeconds / _totalSeconds * 100.0;
            PbTimerProgress.Value = Math.Clamp(pct, 0, 100);
        }
    }

    private void BtnPauseTimer_Click(object sender, RoutedEventArgs e)
    {
        _isPaused = !_isPaused;
        BtnPauseTimer.Content = _isPaused ? "계속" : "일시정지";
    }

    private void BtnAddMinute_Click(object sender, RoutedEventArgs e)
    {
        _remainingSeconds += 60;
        _totalSeconds += 60;
        UpdateTimerDisplay();
    }

    private void BtnResetTimer_Click(object sender, RoutedEventArgs e)
    {
        _remainingSeconds = _totalSeconds;
        UpdateTimerDisplay();
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e)
    {
        _timer.Stop();
        Close();
    }

    private void Window_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Escape)
        {
            _timer.Stop();
            Close();
        }
    }

    private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        // Allow background click to not disrupt presentation
    }
}
