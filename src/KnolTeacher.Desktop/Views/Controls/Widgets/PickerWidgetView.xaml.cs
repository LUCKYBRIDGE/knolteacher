using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.Views.Controls;
using KnolTeacher.Desktop.Views.Windows;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class PickerWidgetView : UserControl, IWidgetLifecycle
{
    private readonly IStudentManagerService? _studentService;
    private readonly ISoundService? _soundService;
    private readonly List<string> _pickedHistory = new();
    private CancellationTokenSource? _pickCts;
    private PopupLaunchPreferences? _popupLaunchPreferences;
    private bool _isPicking;
    private bool _isReady;
    private bool _isActive;
    private bool _disposed;

    public PickerWidgetView(IStudentManagerService? studentService = null, ISoundService? soundService = null)
    {
        _studentService = studentService;
        _soundService = soundService;
        InitializeComponent();
        _isReady = true;
    }

    public void Activate()
    {
        if (_disposed) return;
        _isActive = true;
    }

    public void Deactivate()
    {
        if (_disposed || !_isActive) return;
        _isActive = false;
        CancelPick();
    }

    public void Dispose()
    {
        if (_disposed) return;
        _isActive = false;
        CancelPick();
        _disposed = true;
    }

    private void CancelPick()
    {
        var cts = _pickCts;
        _pickCts = null;
        if (cts == null) return;

        try { cts.Cancel(); } catch { }
        cts.Dispose();
    }

    private void BtnOpenPinball_Click(object sender, RoutedEventArgs e)
    {
        OpenPinballOnMonitor(0);
        e.Handled = true;
    }

    private void BtnOpenPinball_MouseRightButtonUp(object sender, MouseButtonEventArgs e)
    {
        var app = Application.Current as App;
        var configService = app?.Services?.GetService(typeof(IConfigService)) as IConfigService;
        if (configService != null)
        {
            _popupLaunchPreferences ??= new PopupLaunchPreferences(configService.ConfigDir);
            if (!_popupLaunchPreferences.RightClickOpensOnSecondMonitor)
            {
                return;
            }
        }

        var displayManager = app?.Services?.GetService(typeof(IDisplayManager)) as IDisplayManager;
        int targetMonitor = displayManager?.IsDualMonitor == true ? 1 : 0;
        OpenPinballOnMonitor(targetMonitor);
        e.Handled = true;
    }

    private void OpenPinballOnMonitor(int monitorIndex)
    {
        var app = Application.Current as App;
        var window = app?.Services?.GetService(typeof(StudentPickerWindow)) as StudentPickerWindow;
        var displayManager = app?.Services?.GetService(typeof(IDisplayManager)) as IDisplayManager;

        if (window == null && _studentService != null && _soundService != null)
        {
            window = new StudentPickerWindow(_studentService, _soundService, displayManager);
        }

        if (window == null) return;

        displayManager?.MoveWindowToScreen(window, monitorIndex, maximize: false);
        window.Show();
        window.Activate();
    }

    private void ResetDisplay()
    {
        if (!_isReady) return;
        _pickedHistory.Clear();
        if (TxtWinner != null)
        {
            TxtWinner.Text = "?";
            TxtWinner.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#38BDF8"));
        }
        if (BorderWinnerAvatar != null)
        {
            BorderWinnerAvatar.Visibility = Visibility.Collapsed;
        }
        if (TxtHistory != null)
        {
            TxtHistory.Text = "기록: 없음";
        }
    }

    private void Filter_Changed(object sender, RoutedEventArgs e)
    {
        ResetDisplay();
    }

    private void Range_TextChanged(object sender, TextChangedEventArgs e)
    {
        ResetDisplay();
    }

    private async void BtnPick_Click(object sender, RoutedEventArgs e)
    {
        if (_isPicking || !_isActive || _disposed) return;

        bool personalDetailsEnabled = _studentService?.PersistPersonalDetails == true;
        bool isName = personalDetailsEnabled
            && _studentService?.UseNamesInPicker == true
            && RbName.IsChecked == true;

        int genderIdx = CbGender?.SelectedIndex ?? 0;
        string? genderFilter = personalDetailsEnabled
            ? genderIdx switch
            {
                1 => "남",
                2 => "여",
                _ => null
            }
            : null;

        var allStudents = _studentService?.Students ?? new();
        var students = genderFilter != null
            ? allStudents.Where(s => s.Gender == genderFilter).ToList()
            : allStudents;

        List<(string Display, string? AvatarId)> candidates = new();

        if (isName && students.Count > 0)
        {
            foreach (var student in students)
            {
                string tag = student.Gender == "남" ? " 👦" : (student.Gender == "여" ? " 👧" : string.Empty);
                candidates.Add(($"{student.DisplayText}{tag}", student.EffectiveAvatarId));
            }
        }
        else
        {
            int start = TbStartNum != null && int.TryParse(TbStartNum.Text, out int startNumber)
                ? Math.Max(1, startNumber)
                : 1;
            int end = TbEndNum != null && int.TryParse(TbEndNum.Text, out int endNumber)
                ? Math.Max(start, endNumber)
                : 25;

            for (int number = start; number <= end; number++)
            {
                var matchedStudent = allStudents.FirstOrDefault(s => s.Number == number);
                candidates.Add(($"{number}번", matchedStudent?.EffectiveAvatarId ?? $"avatar_{(number - 1) % 32 + 1:D2}"));
            }
        }

        var available = candidates.Where(candidate => !_pickedHistory.Contains(candidate.Display)).ToList();
        if (available.Count == 0)
        {
            TxtWinner.Text = "전원 완료!";
            TxtWinner.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#10B981"));
            if (BorderWinnerAvatar != null) BorderWinnerAvatar.Visibility = Visibility.Collapsed;
            if (TxtHistory != null) TxtHistory.Text = "모든 학생이 다 뽑혔습니다!";
            return;
        }

        CancelPick();
        _pickCts = new CancellationTokenSource();
        var token = _pickCts.Token;

        _isPicking = true;
        BtnPick.IsEnabled = false;

        try
        {
            var rng = new Random();
            for (int step = 0; step < 12; step++)
            {
                token.ThrowIfCancellationRequested();
                var temp = candidates[rng.Next(candidates.Count)];
                TxtWinner.Text = temp.Display;
                TxtWinner.Foreground = Brushes.White;
                var tempBitmap = AnimalAvatarCatalog.GetAvatarBitmap(temp.AvatarId);
                if (tempBitmap != null && BorderWinnerAvatar != null && ImgWinnerAvatar != null)
                {
                    ImgWinnerAvatar.ImageSource = tempBitmap;
                    BorderWinnerAvatar.Visibility = Visibility.Visible;
                }
                else if (BorderWinnerAvatar != null)
                {
                    BorderWinnerAvatar.Visibility = Visibility.Collapsed;
                }
                await Task.Delay(40 + step * 10, token);
            }

            token.ThrowIfCancellationRequested();
            if (_disposed || !_isActive) return;

            var winner = available[rng.Next(available.Count)];
            _pickedHistory.Add(winner.Display);

            TxtWinner.Text = winner.Display;
            TxtWinner.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#10B981"));
            var winnerBitmap = AnimalAvatarCatalog.GetAvatarBitmap(winner.AvatarId);
            if (winnerBitmap != null && BorderWinnerAvatar != null && ImgWinnerAvatar != null)
            {
                ImgWinnerAvatar.ImageSource = winnerBitmap;
                BorderWinnerAvatar.Visibility = Visibility.Visible;
            }
            else if (BorderWinnerAvatar != null)
            {
                BorderWinnerAvatar.Visibility = Visibility.Collapsed;
            }

            if (TxtHistory != null)
            {
                TxtHistory.Text = $"기록 ({_pickedHistory.Count}명): {string.Join(", ", _pickedHistory)}";
            }

            _soundService?.PlayChime();
        }
        catch (OperationCanceledException) when (token.IsCancellationRequested)
        {
            // Normal lifecycle cancellation.
        }
        finally
        {
            _isPicking = false;
            if (!_disposed && BtnPick != null)
            {
                BtnPick.IsEnabled = true;
            }
        }
    }
}
