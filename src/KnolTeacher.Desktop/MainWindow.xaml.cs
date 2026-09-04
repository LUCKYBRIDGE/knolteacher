using System.Collections.ObjectModel;
using Microsoft.Win32;
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
using MessageBoxButton = System.Windows.MessageBoxButton;
using MessageBoxResult = System.Windows.MessageBoxResult;
using MessageBoxImage = System.Windows.MessageBoxImage;

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
    private readonly IQrCodeService _qrCodeService;
    private readonly INeisCommentBatchService _neisCommentBatchService;
    private readonly ISiteBookmarkService _siteBookmarkService;
    private readonly DispatcherTimer _statusTimer;
    private readonly ObservableCollection<NeisStudentComment> _neisComments = new();
    private int _currentNeisIndex = 0;
    private bool _isSplitScreen = false;
    private double _prevLeft, _prevTop, _prevWidth, _prevHeight;
    private WindowState _prevWindowState;

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
        IQrCodeService qrCodeService,
        INeisCommentBatchService neisCommentBatchService,
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
        _qrCodeService = qrCodeService;
        _neisCommentBatchService = neisCommentBatchService;
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

            // 5. Bind NEIS Student Comments DataGrid
            GridNeisComments.ItemsSource = _neisComments;
            UpdateCurrentTargetDisplay();
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
        else
        {
            _displayManager.MoveToStudentMonitor(_timerWindow, maximize: false);
            _timerWindow.Show();
            _timerWindow.Activate();
        }
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
        else
        {
            _displayManager.MoveToStudentMonitor(_timerWindow, maximize: false);
            _timerWindow.Show();
            _timerWindow.Activate();
        }
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
            NavBtnNeis.Background = transparentBrush;
            NavBtnNeis.Foreground = textMainBrush;

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
            else if (index == 5)
            {
                NavBtnNeis.Background = accentBrush;
                NavBtnNeis.Foreground = Brushes.White;
                TxtViewTitle.Text = "📝 나이스 평어 일괄입력 도구";
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
            _displayManager.MoveToStudentMonitor(_studentDisplayWindow, maximize: true);
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
        else
        {
            _displayManager.MoveToStudentMonitor(_timerWindow, maximize: false);
            _timerWindow.Show();
            _timerWindow.Activate();
        }
    }

    private void BtnLaunchPicker_Click(object sender, RoutedEventArgs e)
    {
        if (_pickerWindow.IsVisible) _pickerWindow.Hide();
        else
        {
            _displayManager.MoveToStudentMonitor(_pickerWindow, maximize: false);
            _pickerWindow.Show();
            _pickerWindow.Activate();
        }
    }

    private void BtnLaunchVisualizer_Click(object sender, RoutedEventArgs e)
    {
        if (_visualizerWindow.IsVisible) _visualizerWindow.Hide();
        else
        {
            _displayManager.MoveToStudentMonitor(_visualizerWindow, maximize: false);
            _visualizerWindow.Show();
            _visualizerWindow.Activate();
        }
    }

    private void BtnLaunchDock_Click(object sender, RoutedEventArgs e)
    {
        if (_dockWindow.IsVisible) _dockWindow.Hide();
        else { _dockWindow.Show(); _dockWindow.Activate(); }
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

    #region QR Code & NEIS Comment Batch Handlers

    private void BtnQuickQr_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new QrCodeModalDialog(_qrCodeService, "📱 빠른 QR코드 생성기", "https://pinky-ne.com/")
        {
            Owner = this
        };
        dlg.ShowDialog();
    }

    private void BtnBannerQr_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new QrCodeModalDialog(_qrCodeService, "🌟 핑키네 교실자료실 QR코드", "https://pinky-ne.com/")
        {
            Owner = this
        };
        dlg.ShowDialog();
    }

    private void BtnOfficeQr_Click(object sender, RoutedEventArgs e)
    {
        var office = _siteBookmarkService.EducationOffices.FirstOrDefault(o => o.DomainCode == _siteBookmarkService.SelectedRegionCode)
                     ?? _siteBookmarkService.EducationOffices.FirstOrDefault();
        string url = office?.Url ?? "https://gwe.eduptl.kr/";
        string title = $"🏫 {office?.RegionName ?? "교육청"} K-에듀파인 QR코드";
        var dlg = new QrCodeModalDialog(_qrCodeService, title, url)
        {
            Owner = this
        };
        dlg.ShowDialog();
    }

    private void BtnSiteQr_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement fe && fe.Tag is SiteBookmarkItem item)
        {
            var dlg = new QrCodeModalDialog(_qrCodeService, $"{item.Icon} {item.Title} QR코드", item.Url)
            {
                Owner = this
            };
            dlg.ShowDialog();
        }
    }

    private void UpdateNeisSummary()
    {
        int total = _neisComments.Count;
        int over = _neisComments.Count(c => c.IsOverLimit);
        TxtNeisSummary.Text = over > 0 
            ? $"등록된 학생: {total}명 (⚠️ {over}명 바이트 초과)" 
            : $"등록된 학생: {total}명 (모두 정상)";
        UpdateCurrentTargetDisplay();
    }

    private void UpdateCurrentTargetDisplay()
    {
        if (_neisComments.Count == 0)
        {
            TxtCurrentTargetBadge.Text = "🎯 현재 대상: 없음";
            TxtCurrentTargetPreview.Text = "엑셀 파일을 열거나 복사내용을 붙여넣어 주세요.";
            return;
        }

        if (_currentNeisIndex < 0) _currentNeisIndex = 0;
        if (_currentNeisIndex >= _neisComments.Count) _currentNeisIndex = _neisComments.Count - 1;

        var student = _neisComments[_currentNeisIndex];
        TxtCurrentTargetBadge.Text = $"🎯 대상: {student.StudentNumber}번 {student.StudentName} ({_currentNeisIndex + 1}/{_neisComments.Count})";
        string preview = string.IsNullOrWhiteSpace(student.CommentText) ? "(작성된 평어 없음)" : student.CommentText;
        TxtCurrentTargetPreview.Text = preview;

        GridNeisComments.SelectedIndex = _currentNeisIndex;
        GridNeisComments.ScrollIntoView(student);
    }

    private void BtnNeisSplitScreen_Click(object sender, RoutedEventArgs e)
    {
        var workArea = SystemParameters.WorkArea;
        if (!_isSplitScreen)
        {
            _prevWindowState = WindowState;
            WindowState = WindowState.Normal;
            _prevLeft = Left;
            _prevTop = Top;
            _prevWidth = Width;
            _prevHeight = Height;

            // Snap right half of screen and pin topmost
            Left = workArea.Left + (workArea.Width / 2.0);
            Top = workArea.Top;
            Width = workArea.Width / 2.0;
            Height = workArea.Height;
            Topmost = true;
            _isSplitScreen = true;

            BtnNeisSplitScreen.Content = "🪟 원래 크기 복원";
            HudNotificationWindow.Instance.ShowToast("🪟 분할화면 모드", "화면 우측에 고정되었습니다.\n좌측에 나이스를 띄워두고 작업하세요!");
        }
        else
        {
            Left = _prevLeft;
            Top = _prevTop;
            Width = _prevWidth;
            Height = _prevHeight;
            WindowState = _prevWindowState;
            Topmost = false;
            _isSplitScreen = false;

            BtnNeisSplitScreen.Content = "🪟 나이스 좌우 분할 맞춤";
            HudNotificationWindow.Instance.ShowToast("🪟 화면 복원", "원래 창 크기와 위치로 복원되었습니다.");
        }
    }

    private void BtnNeisPrev_Click(object sender, RoutedEventArgs e)
    {
        if (_neisComments.Count == 0) return;
        if (_currentNeisIndex > 0)
        {
            _currentNeisIndex--;
            UpdateCurrentTargetDisplay();
        }
    }

    private void BtnNeisNext_Click(object sender, RoutedEventArgs e)
    {
        if (_neisComments.Count == 0) return;
        if (_currentNeisIndex < _neisComments.Count - 1)
        {
            _currentNeisIndex++;
            UpdateCurrentTargetDisplay();
        }
    }

    private void BtnNeisCopyAndNext_Click(object sender, RoutedEventArgs e)
    {
        if (_neisComments.Count == 0)
        {
            System.Windows.MessageBox.Show("복사할 학생 평어가 없습니다.", "알림", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        var student = _neisComments[_currentNeisIndex];
        string text = student.CommentText ?? string.Empty;
        Clipboard.SetText(text);

        HudNotificationWindow.Instance.ShowToast("📋 복사완료", $"{student.StudentNumber}번 {student.StudentName} 평어 복사됨!\n나이스 칸에 Ctrl+V 하세요.");

        if (_currentNeisIndex < _neisComments.Count - 1)
        {
            _currentNeisIndex++;
        }
        UpdateCurrentTargetDisplay();
    }

    private void BtnRowCopy_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement fe && fe.Tag is NeisStudentComment student)
        {
            string text = student.CommentText ?? string.Empty;
            Clipboard.SetText(text);
            _currentNeisIndex = _neisComments.IndexOf(student);
            UpdateCurrentTargetDisplay();
            HudNotificationWindow.Instance.ShowToast("📋 개별 복사", $"{student.StudentNumber}번 {student.StudentName} 평어가 복사되었습니다.");
        }
    }

    private void BtnDownloadNeisTemplate_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var sfd = new SaveFileDialog
            {
                Filter = "Excel 통합 문서 (*.xlsx)|*.xlsx",
                FileName = $"나이스_평어_입력양식_{DateTime.Now:yyyyMMdd}.xlsx"
            };
            if (sfd.ShowDialog() == true)
            {
                _neisCommentBatchService.GenerateExcelTemplate(sfd.FileName);
                HudNotificationWindow.Instance.ShowToast("📥", "나이스 표준 엑셀 양식이 저장되었습니다.");
                if (System.Windows.MessageBox.Show("저장된 엑셀 양식을 바로 여시겠습니까?", "양식 열기", MessageBoxButton.YesNo, MessageBoxImage.Information) == MessageBoxResult.Yes)
                {
                    Process.Start(new ProcessStartInfo(sfd.FileName) { UseShellExecute = true });
                }
            }
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show($"양식 저장 실패: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void BtnOpenNeisExcel_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var ofd = new OpenFileDialog
            {
                Filter = "Excel 파일 (*.xlsx)|*.xlsx"
            };
            if (ofd.ShowDialog() == true)
            {
                var parsed = _neisCommentBatchService.ParseExcelFile(ofd.FileName);
                _neisComments.Clear();
                foreach (var c in parsed) _neisComments.Add(c);
                _currentNeisIndex = 0;
                UpdateNeisSummary();
                HudNotificationWindow.Instance.ShowToast("📂", $"{_neisComments.Count}명의 학생 평어를 불러왔습니다.");
            }
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show($"엑셀 열기 오류: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void BtnPasteFromClipboard_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            string clip = Clipboard.GetText();
            if (string.IsNullOrWhiteSpace(clip))
            {
                System.Windows.MessageBox.Show("클립보드에 복사된 내용이 없습니다.\n엑셀에서 번호, 성명, 평어 셀들을 선택 후 Ctrl+C를 누르고 다시 시도하세요.", "알림", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            var parsed = _neisCommentBatchService.ParseClipboardText(clip);
            if (parsed.Count == 0)
            {
                System.Windows.MessageBox.Show("클립보드 데이터에서 학생 평어를 파싱하지 못했습니다.\n번호, 성명, 평어 열이 포함되어 있는지 확인해 주세요.", "알림", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            _neisComments.Clear();
            foreach (var c in parsed) _neisComments.Add(c);
            _currentNeisIndex = 0;
            UpdateNeisSummary();
            HudNotificationWindow.Instance.ShowToast("📋", $"엑셀 복사 데이터로부터 {parsed.Count}명의 평어를 붙여넣었습니다.");
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show($"붙여넣기 오류: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void BtnClearNeisData_Click(object sender, RoutedEventArgs e)
    {
        if (_neisComments.Count > 0 && System.Windows.MessageBox.Show("등록된 학생 평어 목록을 모두 비우시겠습니까?", "목록 비우기", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
        {
            _neisComments.Clear();
            _currentNeisIndex = 0;
            UpdateNeisSummary();
        }
    }

    private void BtnCopyNeisScript_Click(object sender, RoutedEventArgs e)
    {
        if (_neisComments.Count == 0)
        {
            System.Windows.MessageBox.Show("입력할 학생 평어가 없습니다.\n먼저 엑셀 파일을 불러오거나 복사한 내용을 붙여넣어 주세요.", "알림", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        string script = _neisCommentBatchService.GenerateNeisConsoleScript(_neisComments.ToList(), "BEHAVIOR");
        Clipboard.SetText(script);

        System.Windows.MessageBox.Show(
            "🚀 [나이스 1초 일괄입력 코드가 복사되었습니다!]\n\n" +
            "【사용 방법】\n" +
            "1. 4세대 나이스 웹 화면(행동특성 또는 학기말종합의견)을 켭니다.\n" +
            "2. 키보드 [F12] (개발자 도구)를 누릅니다.\n" +
            "3. 상단의 [Console] (콘솔) 탭을 클릭합니다.\n" +
            "4. [Ctrl + V]로 붙여넣은 후 [Enter]를 누르면,\n" +
            "   " + _neisComments.Count + "명의 학생 번호에 맞춰 1초 만에 자동으로 쏙 채워집니다!\n\n" +
            "※ 입력 확인 후 나이스 상단의 [저장] 버튼을 클릭해 완료하세요.",
            "나이스 일괄입력 코드 복사 완료",
            MessageBoxButton.OK,
            MessageBoxImage.Information);
    }

    private void BtnOpenFloatingPaster_Click(object sender, RoutedEventArgs e)
    {
        if (_neisComments.Count == 0)
        {
            System.Windows.MessageBox.Show("입력할 학생 평어가 없습니다.\n먼저 엑셀을 열거나 복사내용을 붙여넣어 주세요.", "알림", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        var win = new NeisFloatingPasterWindow(_neisComments.ToList());
        win.Show();
    }

    private void BtnNeisHelp_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new NeisHelpDialog
        {
            Owner = this
        };
        dlg.ShowDialog();
    }

    #endregion
}
