using System;
using System.Media;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class NoiseTrafficLightWindow : Window
{
    private readonly INoiseMeterService _noiseMeter;
    private readonly IDisplayManager _displayManager;
    private readonly ISoundService _soundService;
    private bool _isFullscreen = false;
    private WindowState _prevWindowState;
    private WindowStyle _prevWindowStyle;

    private static readonly Brush BrushGreenActive = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#10B981"));
    private static readonly Brush BrushGreenDim = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#102E20"));
    private static readonly Brush BrushYellowActive = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F59E0B"));
    private static readonly Brush BrushYellowDim = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#3A2C10"));
    private static readonly Brush BrushRedActive = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#EF4444"));
    private static readonly Brush BrushRedDim = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#3B1818"));

    public NoiseTrafficLightWindow(
        INoiseMeterService noiseMeter,
        IDisplayManager displayManager,
        ISoundService soundService)
    {
        InitializeComponent();
        _noiseMeter = noiseMeter;
        _displayManager = displayManager;
        _soundService = soundService;

        _noiseMeter.NoiseUpdated += OnNoiseUpdated;
        _noiseMeter.RedWarningTriggered += OnRedWarningTriggered;

        Loaded += NoiseTrafficLightWindow_Loaded;
        Closing += (s, e) =>
        {
            e.Cancel = true;
            _noiseMeter.Stop();
            Hide();
        };
    }

    private void NoiseTrafficLightWindow_Loaded(object sender, RoutedEventArgs e)
    {
        // Populate mics
        var devices = _noiseMeter.GetInputDevices();
        ComboMics.Items.Clear();
        if (devices.Count == 0)
        {
            ComboMics.Items.Add("마이크 없음");
            ComboMics.SelectedIndex = 0;
        }
        else
        {
            foreach (var d in devices)
            {
                ComboMics.Items.Add(d);
            }
            ComboMics.SelectedIndex = 0;
        }

        // Start listening
        _noiseMeter.Start(0);
        UpdateMicButtonUI();
    }

    public new void Show()
    {
        base.Show();
        if (!_noiseMeter.IsRunning)
        {
            _noiseMeter.Start(ComboMics.SelectedIndex >= 0 ? ComboMics.SelectedIndex : 0);
            UpdateMicButtonUI();
        }
    }

    private void OnNoiseUpdated(double db, NoiseState state, int warnings)
    {
        Dispatcher.Invoke(() =>
        {
            TxtLiveDb.Text = $"{db:0.0} dB";
            TxtWarningCount.Text = $"{warnings} 회";

            // Update Progress Bar
            double maxWidth = ActualWidth > 80 ? ActualWidth - 70 : 400;
            double pct = Math.Max(0.0, Math.Min(1.0, db / 100.0));
            BarDecibelFill.Width = Math.Max(12.0, pct * maxWidth);

            switch (state)
            {
                case NoiseState.Green:
                    // Green ON
                    LightGreen.Background = BrushGreenActive;
                    GlowGreen.Opacity = 1.0;
                    IconGreen.Opacity = 1.0;
                    // Yellow OFF
                    LightYellow.Background = BrushYellowDim;
                    GlowYellow.Opacity = 0.0;
                    IconYellow.Opacity = 0.3;
                    // Red OFF
                    LightRed.Background = BrushRedDim;
                    GlowRed.Opacity = 0.0;
                    IconRed.Opacity = 0.3;

                    BarDecibelFill.Background = BrushGreenActive;
                    TxtStatusMessage.Text = "🟢 참 잘하고 있어요! (정숙 유지 중)";
                    TxtStatusMessage.Foreground = BrushGreenActive;
                    break;

                case NoiseState.Yellow:
                    // Green OFF
                    LightGreen.Background = BrushGreenDim;
                    GlowGreen.Opacity = 0.0;
                    IconGreen.Opacity = 0.3;
                    // Yellow ON
                    LightYellow.Background = BrushYellowActive;
                    GlowYellow.Opacity = 1.0;
                    IconYellow.Opacity = 1.0;
                    // Red OFF
                    LightRed.Background = BrushRedDim;
                    GlowRed.Opacity = 0.0;
                    IconRed.Opacity = 0.3;

                    BarDecibelFill.Background = BrushYellowActive;
                    TxtStatusMessage.Text = "🟡 목소리를 조금만 낮춰볼까요? (주의)";
                    TxtStatusMessage.Foreground = BrushYellowActive;
                    break;

                case NoiseState.Red:
                    // Green OFF
                    LightGreen.Background = BrushGreenDim;
                    GlowGreen.Opacity = 0.0;
                    IconGreen.Opacity = 0.3;
                    // Yellow OFF
                    LightYellow.Background = BrushYellowDim;
                    GlowYellow.Opacity = 0.0;
                    IconYellow.Opacity = 0.3;
                    // Red ON
                    LightRed.Background = BrushRedActive;
                    GlowRed.Opacity = 1.0;
                    IconRed.Opacity = 1.0;

                    BarDecibelFill.Background = BrushRedActive;
                    TxtStatusMessage.Text = "🔴 쉿! 교실이 너무 시끄러워요! (경고)";
                    TxtStatusMessage.Foreground = BrushRedActive;
                    break;
            }
        });
    }

    private void OnRedWarningTriggered()
    {
        Dispatcher.Invoke(() =>
        {
            if (ChkSoundAlarm.IsChecked == true)
            {
                try
                {
                    SystemSounds.Exclamation.Play();
                }
                catch { }
            }
        });
    }

    private void SliderThreshold_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (SliderYellow == null || SliderRed == null) return;

        // Ensure Red >= Yellow + 5
        if (SliderRed.Value < SliderYellow.Value + 5)
        {
            SliderRed.Value = SliderYellow.Value + 5;
        }

        double yVal = Math.Round(SliderYellow.Value);
        double rVal = Math.Round(SliderRed.Value);

        TxtYellowVal.Text = $"{yVal} dB";
        TxtRedVal.Text = $"{rVal} dB";

        _noiseMeter.YellowThreshold = yVal;
        _noiseMeter.RedThreshold = rVal;
    }

    private void BtnPresetQuiet_Click(object sender, RoutedEventArgs e)
    {
        SliderYellow.Value = 45;
        SliderRed.Value = 58;
    }

    private void BtnPresetDiscussion_Click(object sender, RoutedEventArgs e)
    {
        SliderYellow.Value = 62;
        SliderRed.Value = 76;
    }

    private void BtnPresetActive_Click(object sender, RoutedEventArgs e)
    {
        SliderYellow.Value = 75;
        SliderRed.Value = 88;
    }

    private void BtnToggleMic_Click(object sender, RoutedEventArgs e)
    {
        if (_noiseMeter.IsRunning)
        {
            _noiseMeter.Stop();
        }
        else
        {
            _noiseMeter.Start(ComboMics.SelectedIndex >= 0 ? ComboMics.SelectedIndex : 0);
        }
        UpdateMicButtonUI();
    }

    private void UpdateMicButtonUI()
    {
        if (_noiseMeter.IsRunning)
        {
            BtnToggleMic.Content = "🎙️ 감지 일시정지";
            BtnToggleMic.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#B45309"));
        }
        else
        {
            BtnToggleMic.Content = "▶️ 감지 시작";
            BtnToggleMic.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#059669"));
        }
    }

    private void ComboMics_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (ComboMics.SelectedIndex >= 0 && _noiseMeter.IsRunning)
        {
            _noiseMeter.Start(ComboMics.SelectedIndex);
        }
    }

    private void BtnResetWarnings_Click(object sender, RoutedEventArgs e)
    {
        _noiseMeter.ResetWarningCount();
    }

    private void BtnSwitchMonitor_Click(object sender, RoutedEventArgs e)
    {
        _displayManager.MoveToStudentMonitor(this, maximize: false);
    }

    private void BtnFullscreen_Click(object sender, RoutedEventArgs e)
    {
        if (!_isFullscreen)
        {
            _prevWindowState = WindowState;
            _prevWindowStyle = WindowStyle;
            WindowStyle = WindowStyle.None;
            WindowState = WindowState.Maximized;
            _isFullscreen = true;
            BtnFullscreen.Content = "🗗 창모드";
        }
        else
        {
            WindowStyle = _prevWindowStyle;
            WindowState = _prevWindowState;
            _isFullscreen = false;
            BtnFullscreen.Content = "⛶ 전체화면";
        }
    }
}
