using System.Windows;
using System.Windows.Input;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class ClassroomSoundboardWindow : Window
{
    private readonly ISoundService _soundService;

    public ClassroomSoundboardWindow(ISoundService soundService)
    {
        InitializeComponent();
        _soundService = soundService;

        Closing += (s, e) =>
        {
            e.Cancel = true;
            Hide();
        };

        KeyDown += ClassroomSoundboardWindow_KeyDown;
    }

    private void ClassroomSoundboardWindow_KeyDown(object sender, KeyEventArgs e)
    {
        switch (e.Key)
        {
            case Key.D1 or Key.NumPad1:
                _soundService.PlayDingDongDang();
                break;
            case Key.D2 or Key.NumPad2:
                _soundService.PlayBuzzer();
                break;
            case Key.D3 or Key.NumPad3:
                _soundService.PlayApplause();
                break;
            case Key.D4 or Key.NumPad4:
                _soundService.PlayFanfare();
                break;
            case Key.D5 or Key.NumPad5:
                _soundService.PlayDrumroll();
                break;
            case Key.D6 or Key.NumPad6:
                _soundService.PlayAttentionChime();
                break;
            case Key.D7 or Key.NumPad7:
                _soundService.PlayWhistle();
                break;
            case Key.D8 or Key.NumPad8:
                _soundService.PlayBeep();
                break;
        }
    }

    private void BtnDingDong_Click(object sender, RoutedEventArgs e) => _soundService.PlayDingDongDang();
    private void BtnBuzzer_Click(object sender, RoutedEventArgs e) => _soundService.PlayBuzzer();
    private void BtnApplause_Click(object sender, RoutedEventArgs e) => _soundService.PlayApplause();
    private void BtnFanfare_Click(object sender, RoutedEventArgs e) => _soundService.PlayFanfare();
    private void BtnDrumroll_Click(object sender, RoutedEventArgs e) => _soundService.PlayDrumroll();
    private void BtnChime_Click(object sender, RoutedEventArgs e) => _soundService.PlayAttentionChime();
    private void BtnWhistle_Click(object sender, RoutedEventArgs e) => _soundService.PlayWhistle();
    private void BtnTick_Click(object sender, RoutedEventArgs e) => _soundService.PlayBeep();
}
