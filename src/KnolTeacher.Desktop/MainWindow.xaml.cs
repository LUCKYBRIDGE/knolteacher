using System;
using System.Diagnostics;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using Wpf.Ui.Controls;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.ViewModels;
using KnolTeacher.Desktop.Views.Windows;

namespace KnolTeacher.Desktop;

public partial class MainWindow : FluentWindow
{
    private readonly StudentDisplayWindow _studentDisplayWindow;
    private readonly ScreenDrawingOverlayWindow _screenDrawingOverlayWindow;
    private readonly VisualizerWindow _visualizerWindow;
    private readonly ClassroomTimerWindow _timerWindow;
    private readonly StudentPickerWindow _pickerWindow;
    private readonly FloatingToolbarWindow _dockWindow;
    private readonly IDisplayManager _displayManager;
    private readonly INeisService _neisService;
    private readonly IDesktopCleanerService _cleanerService;
    private readonly IConfigService _configService;
    private readonly IThemeService _themeService;
    private readonly ISchedulerService _schedulerService;
    private readonly ITimetableService _timetableService;
    private readonly ISoundService _soundService;
    private readonly IGlobalHotkeyService _hotkeyService;
    private readonly IYouTubeService _youtubeService;
    private readonly YouTubePlayerWindow _youtubePlayerWindow;
    private readonly ISiteBookmarkService _siteBookmarkService;
    private readonly DispatcherTimer _statusTimer;

    public MainWindow(
        MainViewModel viewModel,
        StudentDisplayWindow studentDisplayWindow,
        ScreenDrawingOverlayWindow screenDrawingOverlayWindow,
        VisualizerWindow visualizerWindow,
        ClassroomTimerWindow timerWindow,
        StudentPickerWindow pickerWindow,
        FloatingToolbarWindow dockWindow,
        IDisplayManager displayManager,
        INeisService neisService,
        IDesktopCleanerService cleanerService,
        IConfigService configService,
        IThemeService themeService,
        ISchedulerService schedulerService,
        ITimetableService timetableService,
        ISoundService soundService,
        IGlobalHotkeyService hotkeyService,
        IYouTubeService youtubeService,
        YouTubePlayerWindow youtubePlayerWindow,
        ISiteBookmarkService siteBookmarkService)
    {
        DataContext = viewModel;
        _studentDisplayWindow = studentDisplayWindow;
        _screenDrawingOverlayWindow = screenDrawingOverlayWindow;
        _visualizerWindow = visualizerWindow;
        _timerWindow = timerWindow;
        _pickerWindow = pickerWindow;
        _dockWindow = dockWindow;
        _displayManager = displayManager;
        _neisService = neisService;
        _cleanerService = cleanerService;
        _configService = configService;
        _themeService = themeService;
        _schedulerService = schedulerService;
        _timetableService = timetableService;
        _soundService = soundService;
        _hotkeyService = hotkeyService;
        _youtubeService = youtubeService;
        _youtubePlayerWindow = youtubePlayerWindow;
        _siteBookmarkService = siteBookmarkService;

        InitializeComponent();

        _statusTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(10) };
        _statusTimer.Tick += (s, e) => UpdatePeriodStatus();

        Loaded += MainWindow_Loaded;
        Closing += (s, e) => App.BootLog($"MainWindow Closing: Cancel={e.Cancel}");
        Closed += (s, e) => App.BootLog("MainWindow Closed");
    }

    private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        try
        {
            // 1. Bind Schedules
            if (_configService.RecurringSchedules != null)
            {
                ListSchedules.ItemsSource = _configService.RecurringSchedules;
            }

            // 2. Load Timetable & Status
            RefreshTimetable();
            _timetableService.OnTimetableChanged += () => Dispatcher.Invoke(RefreshTimetable);
            _statusTimer.Start();

            // 3. Load NEIS Lunch Menu
            await LoadNeisDataAsync();

            // 4. Load Bookmarks & Education Offices
            CbEducationOffice.ItemsSource = _siteBookmarkService.EducationOffices;
            CbEducationOffice.SelectedValue = _siteBookmarkService.SelectedRegionCode;
            ListBookmarks.ItemsSource = _siteBookmarkService.Bookmarks;
            _siteBookmarkService.OnBookmarksChanged += () => Dispatcher.Invoke(() =>
            {
                ListBookmarks.ItemsSource = null;
                ListBookmarks.ItemsSource = _siteBookmarkService.Bookmarks;
            });
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"MainWindow_Loaded note: {ex.Message}");
        }
    }

    private void RefreshTimetable()
    {
        ListTimetable.ItemsSource = null;
        ListTimetable.ItemsSource = _timetableService.GetTodaySchedule();

        bool alarmOn = _timetableService.Settings.EnablePeriodAlarm;
        BtnTogglePeriodAlarm.Content = alarmOn ? "🔔 알람 ON" : "🔕 알람 OFF";

        UpdatePeriodStatus();
    }

    private void UpdatePeriodStatus()
    {
        var (cur, rem) = _timetableService.GetCurrentPeriodStatus();
        if (cur != null)
        {
            TxtCurrentPeriodStatus.Text = $"🟢 현재: {cur.Name} ({cur.Subject}) - 잔여 {rem}분";
            TxtCurrentPeriodStatus.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#059669"));
        }
        else
        {
            TxtCurrentPeriodStatus.Text = "☕ 현재: 쉬는 시간 / 수업 준비 중";
            TxtCurrentPeriodStatus.Foreground = (SolidColorBrush)FindResource("BeigeAccent");
        }
    }

    private async Task LoadNeisDataAsync()
    {
        try
        {
            var meal = await _neisService.GetMealAsync();
            if (meal != null)
            {
                TxtMealMenu.Text = meal.MenuText;
                TxtMealCalorie.Text = $"열량: {meal.Calorie}";
            }
        }
        catch { }
    }

    #region Timetable Handlers

    private void BtnTogglePeriodAlarm_Click(object sender, RoutedEventArgs e)
    {
        bool newVal = !_timetableService.Settings.EnablePeriodAlarm;
        _timetableService.SetAllAlarms(newVal);
        RefreshTimetable();
        HudNotificationWindow.Instance.ShowToast(newVal ? "🔔" : "🔕", newVal ? "교시 시작 알람이 켜졌습니다." : "교시 시작 알람이 꺼졌습니다.");
    }

    private void BtnLaunchClassTimer_Click(object sender, RoutedEventArgs e)
    {
        if (_timerWindow.IsVisible) _timerWindow.Hide();
        else { _timerWindow.Show(); _timerWindow.Activate(); }
    }

    private void BtnShiftTimetable_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new PromptInputDialog("시간표 일괄 시차 조정", "일괄 변경할 시간(분)을 입력하세요:\n(+5: 5분 미루기, -5: 5분 당기기)", "5")
        {
            Owner = this
        };

        if (dlg.ShowDialog() == true && int.TryParse(dlg.InputText, out int mins))
        {
            _timetableService.ShiftAllPeriods(mins);
            RefreshTimetable();
            HudNotificationWindow.Instance.ShowToast("🔄", $"시간표가 {mins}분 조정되었습니다.");
        }
    }

    private void BtnItemTimer_Click(object sender, RoutedEventArgs e)
    {
        if (_timerWindow.IsVisible) _timerWindow.Hide();
        else { _timerWindow.Show(); _timerWindow.Activate(); }
    }

    private void BtnEditSubject_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement fe && fe.Tag is PeriodItem item && !item.IsLunch)
        {
            var dlg = new PromptInputDialog($"{item.Name} 과목 수정", $"{item.Name} 과목명을 입력하세요:", item.Subject)
            {
                Owner = this
            };

            if (dlg.ShowDialog() == true && !string.IsNullOrWhiteSpace(dlg.InputText))
            {
                _timetableService.UpdateTodayPeriodSubject(item.Period - 1, dlg.InputText, item.Tag);
                RefreshTimetable();
                HudNotificationWindow.Instance.ShowToast("✏️", $"{item.Name} 과목이 '{dlg.InputText}'(으)로 변경되었습니다.");
            }
        }
    }

    #endregion

    private void NavBtn_Click(object sender, RoutedEventArgs e)
    {
        if (sender is System.Windows.Controls.Button btn && btn.Tag is string tagStr && int.TryParse(tagStr, out int index))
        {
            MainTabs.SelectedIndex = index;

            var accentBrush = (SolidColorBrush)FindResource("BeigeAccent");
            var transparentBrush = Brushes.Transparent;
            var textMainBrush = (SolidColorBrush)FindResource("BeigeTextMain");

            // Reset all
            NavBtnToday.Background = transparentBrush;
            NavBtnToday.Foreground = textMainBrush;
            NavBtnTools.Background = transparentBrush;
            NavBtnTools.Foreground = textMainBrush;
            NavBtnSchedule.Background = transparentBrush;
            NavBtnSchedule.Foreground = textMainBrush;
            NavBtnZen.Background = transparentBrush;
            NavBtnZen.Foreground = textMainBrush;
            NavBtnSites.Background = transparentBrush;
            NavBtnSites.Foreground = textMainBrush;

            // Activate selected
            if (index == 0)
            {
                NavBtnToday.Background = accentBrush;
                NavBtnToday.Foreground = Brushes.White;
                TxtViewTitle.Text = "📅 오늘의 일과 & 급식";
            }
            else if (index == 1)
            {
                NavBtnTools.Background = accentBrush;
                NavBtnTools.Foreground = Brushes.White;
                TxtViewTitle.Text = "🧰 수업 진행 도구 & 화상기";
            }
            else if (index == 2)
            {
                NavBtnSchedule.Background = accentBrush;
                NavBtnSchedule.Foreground = Brushes.White;
                TxtViewTitle.Text = "⏰ 스마트 예약 센터 & 전원 관리";
            }
            else if (index == 3)
            {
                NavBtnZen.Background = accentBrush;
                NavBtnZen.Foreground = Brushes.White;
                TxtViewTitle.Text = "🧹 스마트 데스크 & 바탕화면 1초 정리";
            }
            else if (index == 4)
            {
                NavBtnSites.Background = accentBrush;
                NavBtnSites.Foreground = Brushes.White;
                TxtViewTitle.Text = "🌐 교사용 유용한 교육 사이트 & 업무포털";
            }
        }
    }

    private void LogoSub_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        try
        {
            Process.Start(new ProcessStartInfo("https://pinky-ne.com") { UseShellExecute = true });
        }
        catch { }
    }

    private void BannerPinky_Click(object sender, RoutedEventArgs e)
    {
        _siteBookmarkService.OpenSite("https://pinky-ne.com/");
    }

    private void CbEducationOffice_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (CbEducationOffice.SelectedValue is string code)
        {
            _siteBookmarkService.SelectedRegionCode = code;
            _siteBookmarkService.Save();
        }
    }

    private void BtnOpenOfficePortal_Click(object sender, RoutedEventArgs e)
    {
        _siteBookmarkService.OpenSelectedOfficePortal();
    }

    private void BtnAddCustomSite_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new AddSiteBookmarkDialog { Owner = this };
        if (dlg.ShowDialog() == true)
        {
            _siteBookmarkService.AddCustomSite(dlg.SiteTitle, dlg.SiteUrl, dlg.SiteDesc, dlg.SelectedIcon);
            HudNotificationWindow.Instance.ShowToast("🌐", $"'{dlg.SiteTitle}' 사이트가 등록되었습니다.");
        }
    }

    private void BtnDeleteBookmark_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement fe && fe.Tag is string id)
        {
            if (System.Windows.MessageBox.Show("해당 사이트 바로가기를 삭제하시겠습니까?", "삭제 확인", System.Windows.MessageBoxButton.YesNo, System.Windows.MessageBoxImage.Question) == System.Windows.MessageBoxResult.Yes)
            {
                _siteBookmarkService.RemoveBookmark(id);
                HudNotificationWindow.Instance.ShowToast("🗑️", "사이트 바로가기가 삭제되었습니다.");
            }
        }
    }

    private void BtnResetSites_Click(object sender, RoutedEventArgs e)
    {
        if (System.Windows.MessageBox.Show("기본 교육 사이트 목록으로 초기화하시겠습니까?", "초기화 확인", System.Windows.MessageBoxButton.YesNo, System.Windows.MessageBoxImage.Question) == System.Windows.MessageBoxResult.Yes)
        {
            _siteBookmarkService.ResetToDefaults();
            HudNotificationWindow.Instance.ShowToast("🔄", "기본 교육 사이트 목록으로 복원되었습니다.");
        }
    }

    private void BtnOpenBookmark_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement fe && fe.Tag is string url)
        {
            _siteBookmarkService.OpenSite(url);
        }
    }

    private async void BtnUpdate_Click(object sender, RoutedEventArgs e)
    {
        string currentVersion = "v2.6.0";
        try
        {
            using var client = new System.Net.Http.HttpClient();
            client.DefaultRequestHeaders.UserAgent.ParseAdd("KnolTeacherApp");
            client.Timeout = TimeSpan.FromSeconds(3);
            var resp = await client.GetAsync("https://api.github.com/repos/LUCKYBRIDGE/knolteacher/releases/latest");
            if (resp.IsSuccessStatusCode)
            {
                string json = await resp.Content.ReadAsStringAsync();
                using var doc = System.Text.Json.JsonDocument.Parse(json);
                string latestTag = doc.RootElement.GetProperty("tag_name").GetString() ?? currentVersion;
                string htmlUrl = doc.RootElement.GetProperty("html_url").GetString() ?? "https://github.com/LUCKYBRIDGE/knolteacher/releases";

                if (latestTag != currentVersion)
                {
                    var res = System.Windows.MessageBox.Show(
                        $"새로운 최신 버전({latestTag})이 출시되었습니다!\n(현재 버전: {currentVersion})\n\n지금 다운로드 페이지로 이동하시겠습니까?",
                        "새로운 업데이트 발견",
                        System.Windows.MessageBoxButton.YesNo,
                        System.Windows.MessageBoxImage.Information);
                    if (res == System.Windows.MessageBoxResult.Yes)
                    {
                        Process.Start(new ProcessStartInfo(htmlUrl) { UseShellExecute = true });
                    }
                    return;
                }
            }
        }
        catch { }

        var confirm = System.Windows.MessageBox.Show(
            $"놀티쳐 {currentVersion} 최신 버전을 사용 중입니다.\n(최신 기능 및 안정성이 완벽히 유지되고 있습니다)\n\nGitHub 공식 릴리스 페이지를 확인하시겠습니까?",
            "최신 버전 확인 (v2.6.0)",
            System.Windows.MessageBoxButton.YesNo,
            System.Windows.MessageBoxImage.Information);
        if (confirm == System.Windows.MessageBoxResult.Yes)
        {
            try { Process.Start(new ProcessStartInfo("https://github.com/LUCKYBRIDGE/knolteacher/releases") { UseShellExecute = true }); } catch { }
        }
    }

    // Tools Launch Handlers
    private void BtnLaunchBoard_Click(object sender, RoutedEventArgs e)
    {
        if (_studentDisplayWindow.IsVisible)
        {
            _studentDisplayWindow.Hide();
        }
        else
        {
            if (_displayManager.ScreenCount > 1)
            {
                _displayManager.MoveWindowToScreen(_studentDisplayWindow, 1, maximize: true);
            }
            _studentDisplayWindow.Show();
            _studentDisplayWindow.Activate();
        }
    }

    private void BtnLaunchDrawing_Click(object sender, RoutedEventArgs e)
    {
        if (_screenDrawingOverlayWindow.IsVisible)
        {
            _screenDrawingOverlayWindow.CloseOverlay();
        }
        else
        {
            _screenDrawingOverlayWindow.FreezeAndShow();
        }
    }

    private void BtnLaunchTimer_Click(object sender, RoutedEventArgs e)
    {
        if (_timerWindow.IsVisible) _timerWindow.Hide();
        else { _timerWindow.Show(); _timerWindow.Activate(); }
    }

    private void BtnLaunchPicker_Click(object sender, RoutedEventArgs e)
    {
        if (_pickerWindow.IsVisible) _pickerWindow.Hide();
        else { _pickerWindow.Show(); _pickerWindow.Activate(); }
    }

    private void BtnLaunchVisualizer_Click(object sender, RoutedEventArgs e)
    {
        _visualizerWindow.Show();
        _visualizerWindow.Activate();
    }

    private void BtnLaunchDock_Click(object sender, RoutedEventArgs e)
    {
        if (_dockWindow.IsVisible) _dockWindow.Hide();
        else { _dockWindow.Show(); _dockWindow.Activate(); }
    }

    private void BtnLaunchYouTube_Click(object sender, RoutedEventArgs e)
    {
        if (_youtubePlayerWindow.IsVisible)
        {
            _youtubePlayerWindow.Activate();
        }
        else
        {
            _youtubePlayerWindow.Show();
            _youtubePlayerWindow.Activate();
        }
    }

    private void BtnOpenPeriodAlarmSettings_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new PeriodAlarmSettingsDialog(_configService, _soundService, _timetableService)
        {
            Owner = this
        };
        dlg.ShowDialog();
    }

    private void BtnOpenHotkeySettings_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new HotkeySettingsDialog(_configService, _hotkeyService)
        {
            Owner = this
        };
        dlg.ShowDialog();
    }

    // Zen Cleaner Handlers
    private void BtnOrganizeDesktop_Click(object sender, RoutedEventArgs e)
    {
        var (success, msg, count) = _cleanerService.OrganizeDesktop();
        System.Windows.MessageBox.Show(msg, "바탕화면 자동 정리", System.Windows.MessageBoxButton.OK,
            success ? System.Windows.MessageBoxImage.Information : System.Windows.MessageBoxImage.Warning);
    }

    private void BtnUndoOrganize_Click(object sender, RoutedEventArgs e)
    {
        var (success, msg, count) = _cleanerService.UndoOrganize();
        System.Windows.MessageBox.Show(msg, "정리 실행 취소", System.Windows.MessageBoxButton.OK,
            success ? System.Windows.MessageBoxImage.Information : System.Windows.MessageBoxImage.Warning);
    }

    private void BtnToggleIcons_Click(object sender, RoutedEventArgs e)
    {
        var (success, isVisible, msg) = _cleanerService.ToggleDesktopIcons();
        System.Windows.MessageBox.Show(msg, "수업 집중 모드", System.Windows.MessageBoxButton.OK,
            success ? System.Windows.MessageBoxImage.Information : System.Windows.MessageBoxImage.Warning);
    }

    private void BtnCleanTemp_Click(object sender, RoutedEventArgs e)
    {
        var (success, msg, count, freed) = _cleanerService.CleanTempAndDownloads(30);
        System.Windows.MessageBox.Show(msg, "임시 파일 청소", System.Windows.MessageBoxButton.OK,
            success ? System.Windows.MessageBoxImage.Information : System.Windows.MessageBoxImage.Warning);
    }

    private void BtnTheme_Click(object sender, RoutedEventArgs e)
    {
        if (sender is System.Windows.Controls.Button btn && btn.Tag is string themeTag)
        {
            _themeService.ApplyTheme(themeTag);
        }
    }

    // Schedule Center Handlers
    private void BtnAddSchedule_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new ScheduleEditDialog { Owner = this };
        if (dlg.ShowDialog() == true && dlg.ResultItem != null)
        {
            _configService.RecurringSchedules.Add(dlg.ResultItem);
            _configService.SaveRecurringSchedules();
            RefreshSchedules();
            HudNotificationWindow.Instance.ShowToast("⏰", $"'{dlg.ResultItem.Title}' 예약이 등록되었습니다.");
        }
    }

    private void BtnEditSchedule_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement fe && fe.DataContext is Models.RecurringScheduleItem item)
        {
            var dlg = new ScheduleEditDialog(item) { Owner = this };
            if (dlg.ShowDialog() == true)
            {
                _configService.SaveRecurringSchedules();
                RefreshSchedules();
                HudNotificationWindow.Instance.ShowToast("✏️", $"'{item.Title}' 예약이 수정되었습니다.");
            }
        }
    }

    private void BtnDeleteSchedule_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement fe && fe.DataContext is Models.RecurringScheduleItem item)
        {
            var res = System.Windows.MessageBox.Show($"'{item.Title}' 예약을 정말 삭제하시겠습니까?", "예약 삭제", System.Windows.MessageBoxButton.YesNo, System.Windows.MessageBoxImage.Question);
            if (res == System.Windows.MessageBoxResult.Yes)
            {
                _configService.RecurringSchedules.Remove(item);
                _configService.SaveRecurringSchedules();
                RefreshSchedules();
                HudNotificationWindow.Instance.ShowToast("🗑️", "예약이 삭제되었습니다.");
            }
        }
    }

    private void BtnTestSchedule_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement fe && fe.DataContext is Models.RecurringScheduleItem item)
        {
            _schedulerService.TestRunSchedule(item);
        }
    }

    private void ScheduleToggle_Click(object sender, RoutedEventArgs e)
    {
        _configService.SaveRecurringSchedules();
    }

    private void RefreshSchedules()
    {
        ListSchedules.ItemsSource = null;
        ListSchedules.ItemsSource = _configService.RecurringSchedules;
    }
}