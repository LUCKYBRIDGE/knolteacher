using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Threading;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class ClassroomTimerWindow : Window
{
    private readonly ISoundService _soundService;
    private readonly DispatcherTimer _timer;
    private int _remainingSeconds = 300; // 5 mins
    private int _initialSeconds = 300;
    private bool _isRunning = false;

    public ClassroomTimerWindow(ISoundService soundService)
    {
        _soundService = soundService;
        InitializeComponent();

        _timer = new DispatcherTimer
        {
            Interval = TimeSpan.FromSeconds(1)
        };
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
                _soundService.PlayChime();
                MessageBox.Show("시간이 모두 종료되었습니다!", "타이머 종료", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }
    }

    private void UpdateDisplay()
    {
        int min = _remainingSeconds / 60;
        int sec = _remainingSeconds % 60;
        TxtTime.Text = $"{min:D2}:{sec:D2}";

        if (!_isRunning && TbMinutes != null && TbSeconds != null)
        {
            TbMinutes.Text = $"{min:D2}";
            TbSeconds.Text = $"{sec:D2}";
        }
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
        }
    }

    private void BtnReset_Click(object sender, RoutedEventArgs e)
    {
        _timer.Stop();
        _isRunning = false;
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
            BtnStartPause.Content = "▶ 시작";
            _initialSeconds = mins * 60;
            _remainingSeconds = _initialSeconds;
            UpdateDisplay();
        }
    }

    protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
    {
        // Don't dispose on window close; just hide to preserve state
        e.Cancel = true;
        Hide();
    }
}
