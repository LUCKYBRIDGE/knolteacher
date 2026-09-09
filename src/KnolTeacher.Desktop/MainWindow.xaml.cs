using System.IO;
using System.Text.Json;
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
using KnolTeacher.Desktop.Views.Controls;
using KnolTeacher.Desktop.Views.Controls.Widgets;
using System.Linq;
using MessageBoxButton = System.Windows.MessageBoxButton;
using MessageBoxResult = System.Windows.MessageBoxResult;
using MessageBoxImage = System.Windows.MessageBoxImage;
using MessageBox = System.Windows.MessageBox;
using Button = System.Windows.Controls.Button;

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
    private readonly SchoolScaleWindow _schoolScaleWindow;
    private readonly NoiseTrafficLightWindow _noiseTrafficLightWindow;
    private readonly IWeatherService _weatherService;
    private readonly WorkdayCalculatorWindow _workdayCalculatorWindow;
    private readonly SmartSeatShuffleWindow _smartSeatShuffleWindow;
    private readonly ClassroomSoundboardWindow _soundboardWindow;
    private readonly IAcademicCalendarService _academicCalendarService;
    private readonly ITrayService _trayService;
    private readonly DigitalSignatureWindow _signatureWindow;
    private readonly IEarlyLeaveCalculatorService _earlyLeaveCalculatorService;
    private readonly IUpdateService _updateService;
    private readonly DispatcherTimer _statusTimer;
    private readonly DispatcherTimer _clockTimer;
    private readonly ObservableCollection<NeisStudentComment> _neisComments = new();
    private ObservableCollection<TodoItem> _todoItems = new();
    private int _currentNeisIndex = 0;
    private bool _isSplitScreen = false;
    private double _prevLeft, _prevTop, _prevWidth, _prevHeight;
    private WindowState _prevWindowState;

    private int _calYear = DateTime.Today.Year;
    private int _calMonth = DateTime.Today.Month;
    private DateTime _selectedCalDate = DateTime.Today;
    private List<AcademicScheduleItem> _monthScheduleEvents = new();
    private DateTime _selectedMealDate = DateTime.Today;
    private readonly List<MainWidgetCard> _mainWidgets = new();
    private readonly IStartupService _startupService;
    private readonly IDataShareService _dataShareService;
    private readonly TemplateShareWindow _templateShareWindow;
    private int _tutorialStep = 1;

    public MainWindow(
        MainViewModel viewModel,
        StudentDisplayWindow studentDisplayWindow,
        ScreenDrawingOverlayWindow screenDrawingOverlayWindow,
        VisualizerWindow visualizerWindow,
        ClassroomTimerWindow timerWindow,
        StudentPickerWindow pickerWindow,
        FloatingToolbarWindow dockWindow,
        SchoolScaleWindow schoolScaleWindow,
        NoiseTrafficLightWindow noiseTrafficLightWindow,
        IWeatherService weatherService,
        WorkdayCalculatorWindow workdayCalculatorWindow,
        SmartSeatShuffleWindow smartSeatShuffleWindow,
        ClassroomSoundboardWindow soundboardWindow,
        IAcademicCalendarService academicCalendarService,
        ITrayService trayService,
        DigitalSignatureWindow signatureWindow,
        IEarlyLeaveCalculatorService earlyLeaveCalculatorService,
        IUpdateService updateService,
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
        ISiteBookmarkService siteBookmarkService,
        IStartupService startupService,
        IDataShareService dataShareService,
        TemplateShareWindow templateShareWindow)
    {
        DataContext = viewModel;
        _studentDisplayWindow = studentDisplayWindow;
        _screenDrawingOverlayWindow = screenDrawingOverlayWindow;
        _visualizerWindow = visualizerWindow;
        _timerWindow = timerWindow;
        _pickerWindow = pickerWindow;
        _dockWindow = dockWindow;
        _schoolScaleWindow = schoolScaleWindow;
        _noiseTrafficLightWindow = noiseTrafficLightWindow;
        _weatherService = weatherService;
        _workdayCalculatorWindow = workdayCalculatorWindow;
        _smartSeatShuffleWindow = smartSeatShuffleWindow;
        _soundboardWindow = soundboardWindow;
        _academicCalendarService = academicCalendarService;
        _trayService = trayService;
        _signatureWindow = signatureWindow;
        _earlyLeaveCalculatorService = earlyLeaveCalculatorService;
        _updateService = updateService;
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
        _startupService = startupService;
        _dataShareService = dataShareService;
        _templateShareWindow = templateShareWindow;
        _templateShareWindow.DataChanged += OnExternalDataChanged;

        InitializeComponent();
        UpdateWindowTitle(0);

        _statusTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(10) };
        _statusTimer.Tick += (s, e) => UpdatePeriodStatus();

        _clockTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(1) };
        _clockTimer.Tick += (s, e) => UpdateBigClock();

        Loaded += MainWindow_Loaded;
        Closing += (s, e) => App.BootLog($"MainWindow Closing: Cancel={e.Cancel}");
        Closed += (s, e) => App.BootLog("MainWindow Closed");
    }

    private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        try
        {
            // Responsive Screen Bounds: Open generously on modern classroom displays (1080p / 1440p) with spacious, unclipped layout
            var workArea = SystemParameters.WorkArea;
            if (workArea.Width > 0 && workArea.Height > 0)
            {
                // Takes ~92% width and ~94% height of screen work area for an open, airy desktop classroom feel
                double targetWidth = Math.Max(1360, Math.Min(1680, workArea.Width * 0.92));
                double targetHeight = Math.Max(840, Math.Min(980, workArea.Height * 0.94));

                Width = Math.Max(MinWidth, Math.Min(targetWidth, workArea.Width - 24.0));
                Height = Math.Max(MinHeight, Math.Min(targetHeight, workArea.Height - 24.0));

                Left = Math.Max(workArea.Left + 12.0, workArea.Left + (workArea.Width - Width) / 2.0);
                Top = Math.Max(workArea.Top + 12.0, workArea.Top + (workArea.Height - Height) / 2.0);
            }

            // 0. Initialize System Tray & Background Minimization
            _trayService.Initialize(
                this,
                openMapAction: () => BtnLaunchSchoolScale_Click(this, new RoutedEventArgs()),
                openSignatureAction: () => BtnLaunchSignature_Click(this, new RoutedEventArgs())
            );

            // 1. Start Big Modern Clock
            _clockTimer.Start();
            UpdateBigClock();

            // 2. Bind Schedules
            if (_configService.RecurringSchedules != null)
            {
                ListSchedules.ItemsSource = _configService.RecurringSchedules;
            }

            // 3. Load Timetable & Status
            RefreshTimetable();
            _timetableService.OnTimetableChanged += () => Dispatcher.Invoke(RefreshTimetable);
            _statusTimer.Start();

            // 4. Load Academic Calendar & Upcoming D-Days (NEIS)
            _ = LoadCalendarAsync();
            _ = LoadUpcomingDDaysAsync();

            // 5. Load NEIS Lunch Menu & Weather
            _ = LoadNeisDataAsync(_selectedMealDate);
            InitWeatherRegions();
            await LoadWeatherAsync();

            // 6. Load Bookmarks & Education Offices
            CbEducationOffice.ItemsSource = _siteBookmarkService.EducationOffices;
            CbEducationOffice.SelectedValue = _siteBookmarkService.SelectedRegionCode;
            ListBookmarks.ItemsSource = _siteBookmarkService.Bookmarks;
            _siteBookmarkService.OnBookmarksChanged += () => Dispatcher.Invoke(() =>
            {
                ListBookmarks.ItemsSource = null;
                ListBookmarks.ItemsSource = _siteBookmarkService.Bookmarks;
            });

            // 7. Bind NEIS Student Comments DataGrid
            GridNeisComments.ItemsSource = _neisComments;
            UpdateCurrentTargetDisplay();

            // 8. Initialize Main Screen Widgets & Customization
            InitWidgetSystem();
            LoadTodos();
            LoadMainNotice();
            UpdateMonitorStatusBadge();

            // 9. Startup Auto-Run Status & Tutorial Auto-Launch
            ChkAutoStartup.IsChecked = _startupService.IsStartupEnabled();

            string currentVer = System.Reflection.Assembly.GetExecutingAssembly().GetName().Version?.ToString() ?? "2.9.0";
            if (string.IsNullOrEmpty(_configService.LastSeenTutorialVersion))
            {
                _ = Dispatcher.InvokeAsync(async () =>
                {
                    await Task.Delay(800);
                    StartTutorial(isFirstRun: true);
                });
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"MainWindow_Loaded note: {ex.Message}");
        }
    }

    private void UpdateBigClock()
    {
        try
        {
            TxtBigClockTime.Text = DateTime.Now.ToString("HH:mm:ss");
            TxtBigClockDate.Text = DateTime.Now.ToString("yyyy년 M월 d일 (ddd)");

            if (TxtHeaderGreeting != null)
            {
                int hour = DateTime.Now.Hour;
                string greeting = hour switch
                {
                    < 9 => "활기찬 아침입니다! 🌅",
                    < 12 => "즐거운 오전 수업 시간입니다! 🌿",
                    < 13 => "맛있는 점심시간입니다! 🍱",
                    < 17 => "보람찬 오후 시간입니다! ✨",
                    _ => "오늘 하루도 수고 많으셨습니다! 🌙"
                };
                TxtHeaderGreeting.Text = greeting;
            }
        }
        catch { }
    }

    private void RefreshTimetable()
    {
        ListTimetable.ItemsSource = null;
        ListTimetable.ItemsSource = _timetableService.GetTodaySchedule();

        bool alarmOn = _timetableService.Settings.EnablePeriodAlarm;
        if (TxtPeriodAlarmIcon != null && TxtPeriodAlarmLabel != null)
        {
            TxtPeriodAlarmIcon.Text = alarmOn ? "🔔" : "🔕";
            TxtPeriodAlarmLabel.Text = alarmOn ? "알람 ON" : "알람 OFF";
            TxtPeriodAlarmLabel.Foreground = alarmOn 
                ? (Brush)FindResource("BeigeTextMain") 
                : (Brush)FindResource("BeigeTextMuted");
        }
        BtnTogglePeriodAlarm.ToolTip = alarmOn 
            ? "수업 시작 예비령 및 교시 알람: 켜짐 (클릭하여 끄기)" 
            : "수업 시작 예비령 및 교시 알람: 꺼짐 (클릭하여 켜기)";

        UpdatePeriodStatus();
    }

    private void UpdatePeriodStatus()
    {
        var (cur, rem) = _timetableService.GetCurrentPeriodStatus();
        if (cur != null)
        {
            if (TxtCurrentPeriodStatus != null) TxtCurrentPeriodStatus.Text = $"🟢 현재: {cur.Name} ({cur.Subject}) - 잔여 {rem}분";
            if (TxtCurrentPeriodStatus != null) TxtCurrentPeriodStatus.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#059669"));
            if (TxtMiniClockPeriod != null) TxtMiniClockPeriod.Text = cur.Name;

            if (TxtLivePeriodStatus != null)
            {
                TxtLivePeriodStatus.Text = $"{cur.Name} ({cur.Subject}) • {rem}분 남음";
                DotLiveStatus.Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#10B981"));
                TxtLivePeriodStatus.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E293B"));
                PillLivePeriodStatus.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F8FAFC"));
                PillLivePeriodStatus.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#E2E8F0"));
            }
        }
        else
        {
            if (TxtCurrentPeriodStatus != null) TxtCurrentPeriodStatus.Text = "☕ 현재: 쉬는 시간 / 수업 준비 중";
            if (TxtCurrentPeriodStatus != null) TxtCurrentPeriodStatus.Foreground = (SolidColorBrush)FindResource("BeigeAccent");
            if (TxtMiniClockPeriod != null) TxtMiniClockPeriod.Text = "쉬는 시간";

            if (TxtLivePeriodStatus != null)
            {
                TxtLivePeriodStatus.Text = "☕ 쉬는 시간 / 수업 준비";
                DotLiveStatus.Fill = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#94A3B8"));
                TxtLivePeriodStatus.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#475569"));
                PillLivePeriodStatus.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F8FAFC"));
                PillLivePeriodStatus.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#E2E8F0"));
            }
        }
    }

    #region Classroom Banner & Sound Handlers

    private void BtnEditBanner_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new PromptInputDialog("오늘의 학급 안내 / 목표 수정", "학생들에게 상단 배너로 띄워줄 안내 문구를 입력하세요:", TxtClassBanner.Text) { Owner = this };
        if (dlg.ShowDialog() == true && !string.IsNullOrWhiteSpace(dlg.InputText))
        {
            TxtClassBanner.Text = dlg.InputText.Trim();
            HudNotificationWindow.Instance.ShowToast("📢", "학급 안내 문구가 변경되었습니다.");
        }
    }

    private void BtnBannerChime_Click(object sender, RoutedEventArgs e)
    {
        _soundService.PlayChime();
        HudNotificationWindow.Instance.ShowToast("🔔", "집중 차임벨이 울렸습니다.");
    }

    #endregion

    #region Academic Calendar & D-Days

    private async Task LoadCalendarAsync(bool force = false)
    {
        try
        {
            TxtCalMonthYear.Text = $"{_calYear}년 {_calMonth}월";
            _monthScheduleEvents = await _academicCalendarService.GetScheduleForMonthAsync(_calYear, _calMonth, force);
            var cells = _academicCalendarService.GenerateMonthGrid(_calYear, _calMonth, _monthScheduleEvents, _selectedCalDate);
            ListCalendarCells.ItemsSource = cells;
            if (ListMonthAcademicEvents != null && _monthScheduleEvents != null)
            {
                ListMonthAcademicEvents.ItemsSource = _monthScheduleEvents
                    .Where(ev => ev.Date.HasValue)
                    .OrderBy(ev => ev.Date!.Value)
                    .ToList();
            }
            UpdateSelectedDayDetail(_selectedCalDate);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"LoadCalendarAsync error: {ex.Message}");
        }
    }

    private async Task LoadUpcomingDDaysAsync()
    {
        try
        {
            var ddays = await _academicCalendarService.GetUpcomingDDayEventsAsync(6);
            ListUpcomingDDays.ItemsSource = ddays;
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"LoadUpcomingDDaysAsync error: {ex.Message}");
        }
    }

    private void UpdateSelectedDayDetail(DateTime date, List<AcademicScheduleItem>? dayEvents = null)
    {
        TxtCalSelectedDate.Text = date.ToString("M월 d일 (ddd)");
        var evs = dayEvents ?? _monthScheduleEvents.Where(e => e.Date?.Date == date.Date).ToList();
        if (evs.Count > 0)
        {
            string summary = string.Join(" · ", evs.Select(e => e.EventName));
            TxtCalSelectedEvent.Text = summary;
            TxtCalSelectedEvent.Foreground = evs.Any(e => e.IsHoliday)
                ? new SolidColorBrush((Color)ColorConverter.ConvertFromString("#EF4444"))
                : (SolidColorBrush)FindResource("BeigeTextMain");
        }
        else
        {
            TxtCalSelectedEvent.Text = "등록된 학사일정이 없습니다.";
            TxtCalSelectedEvent.Foreground = (SolidColorBrush)FindResource("BeigeTextMuted");
        }
    }

    private void BtnCalPrev_Click(object sender, RoutedEventArgs e)
    {
        if (_calMonth == 1) { _calYear--; _calMonth = 12; }
        else { _calMonth--; }
        _ = LoadCalendarAsync();
    }

    private void BtnCalNext_Click(object sender, RoutedEventArgs e)
    {
        if (_calMonth == 12) { _calYear++; _calMonth = 1; }
        else { _calMonth++; }
        _ = LoadCalendarAsync();
    }

    private void BtnCalToday_Click(object sender, RoutedEventArgs e)
    {
        _calYear = DateTime.Today.Year;
        _calMonth = DateTime.Today.Month;
        _selectedCalDate = DateTime.Today;
        _ = LoadCalendarAsync();
    }

    private void BtnRefreshAcademicCalendar_Click(object sender, RoutedEventArgs e)
    {
        _ = LoadCalendarAsync(force: true);
        _ = LoadUpcomingDDaysAsync();
        HudNotificationWindow.Instance.ShowToast("🔄", "학사일정을 새로고침했습니다.");
    }

    private void CalDay_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (sender is FrameworkElement elem && elem.Tag is CalendarDayCell cell)
        {
            _selectedCalDate = cell.Date;
            var cells = _academicCalendarService.GenerateMonthGrid(_calYear, _calMonth, _monthScheduleEvents, _selectedCalDate);
            ListCalendarCells.ItemsSource = cells;
            if (ListMonthAcademicEvents != null && _monthScheduleEvents != null)
            {
                ListMonthAcademicEvents.ItemsSource = _monthScheduleEvents
                    .Where(ev => ev.Date.HasValue)
                    .OrderBy(ev => ev.Date!.Value)
                    .ToList();
            }
            UpdateSelectedDayDetail(cell.Date, cell.Events);
        }
    }

    private void TxtClassNoticeMemo_TextChanged(object sender, TextChangedEventArgs e)
    {
        // Keep notice memo in local state
    }

    private void BtnEarlyLeaveQuickCalc_Click(object sender, RoutedEventArgs e)
    {
        var result = _earlyLeaveCalculatorService.Calculate(_calYear, _calMonth, _monthScheduleEvents);

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"🏖️ [{_calYear}년 {_calMonth}월 교원 15일 복무·조퇴 간편 계산기]");
        sb.AppendLine("───────────────────────────");
        sb.AppendLine($"• 해당 월 총 일수: {result.TotalCalendarDays}일");
        sb.AppendLine($"• 주말(토·일): {result.WeekendDays}일");
        sb.AppendLine($"• 방학/공휴일/재량휴업일: {result.HolidayAndVacationDays}일");
        sb.AppendLine($"• ⭐️ 실 근무 소정일수: {result.NetWorkDays}일 (기준: {result.RequiredWorkDays}일)");
        sb.AppendLine("───────────────────────────");
        if (result.IsEligibleForEarlyLeave)
        {
            sb.AppendLine($"✅ [조퇴/연가 여유]: 수당 전액 수령 가능");
            sb.AppendLine($"   15일 기준보다 {result.MarginDays}일의 여유가 있습니다.");
            sb.AppendLine($"   (최대 {result.MarginDays}일간 연가·조퇴·지각을 사용해도 15일 소정일수 충족)");
        }
        else
        {
            int deficit = Math.Abs(result.MarginDays);
            sb.AppendLine($"⚠️ [주의]: 15일 기준 {deficit}일 부족");
            sb.AppendLine($"   이 달은 방학·휴업 등으로 실 근무 가능일수({result.NetWorkDays}일)가 15일 미만입니다.");
            sb.AppendLine($"   정액급식비 및 직급보조비 일할계산 여부를 확인하세요.");
        }
        sb.AppendLine("───────────────────────────");
        sb.AppendLine("※ 자세한 일자별 계산 및 세부 설정은 빠른 도구의 '월 15일 복무 계산기'를 이용하세요.");

        System.Windows.MessageBox.Show(sb.ToString(), $"{_calYear}년 {_calMonth}월 복무·조퇴 가능일수 분석", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    #endregion

    #region Lunch Meal with Date Navigation

    private async Task LoadNeisDataAsync(DateTime? date = null)
    {
        var targetDate = date ?? _selectedMealDate;
        try
        {
            TxtMealDate.Text = targetDate.Date == DateTime.Today ? "오늘" : targetDate.ToString("M/d (ddd)");
            TxtMealMenu.Text = "식단 불러오는 중...";
            var meal = await _neisService.GetMealAsync(targetDate);
            if (meal != null)
            {
                TxtMealMenu.Text = meal.MenuText;
                TxtMealCalorie.Text = $"열량: {meal.Calorie}";
                if (TxtMealCaloriePill != null) TxtMealCaloriePill.Text = meal.Calorie;
            }
            else
            {
                TxtMealMenu.Text = "등록된 급식 정보가 없습니다.";
                TxtMealCalorie.Text = "열량: 0 kcal";
                if (TxtMealCaloriePill != null) TxtMealCaloriePill.Text = "0 kcal";
            }
        }
        catch
        {
            TxtMealMenu.Text = "식단 정보를 불러올 수 없습니다.";
        }
    }

    private void BtnMealPrev_Click(object sender, RoutedEventArgs e)
    {
        _selectedMealDate = _selectedMealDate.AddDays(-1);
        _ = LoadNeisDataAsync(_selectedMealDate);
    }

    private void BtnMealNext_Click(object sender, RoutedEventArgs e)
    {
        _selectedMealDate = _selectedMealDate.AddDays(1);
        _ = LoadNeisDataAsync(_selectedMealDate);
    }

    private void BtnMealToday_Click(object sender, RoutedEventArgs e)
    {
        _selectedMealDate = DateTime.Today;
        _ = LoadNeisDataAsync(_selectedMealDate);
    }

    #endregion

    #region Signature & Hotkey Guide Launchers

    private void BtnLaunchSignature_Click(object sender, RoutedEventArgs e)
    {
        if (_signatureWindow.IsVisible)
        {
            _signatureWindow.Activate();
        }
        else
        {
            _signatureWindow.Show();
            _signatureWindow.Activate();
        }
    }

    private void BtnShowHotkeyGuide_Click(object sender, RoutedEventArgs e)
    {
        string guide =
            "✨ [놀티쳐 백그라운드 상주 & 전역 단축키 가이드]\n\n" +
            "놀티쳐 창 우측 상단의 닫기(X)를 누르면 앱이 종료되지 않고\n" +
            "작업표시줄 우측 '시스템 트레이(숨김 아이콘)'에 안전하게 들어갑니다.\n\n" +
            "어떤 프로그램(PPT, 한글, 브라우저, 나이스 등)을 사용 중이어도 언제든 즉시 실행:\n\n" +
            "• F2: 놀보드 (전자 칠판 & 판서 화면 열기/숨기기)\n" +
            "• Alt + 1: 메인 놀티쳐 창 보이기 / 숨기기\n" +
            "• Alt + 2: 4K 화면 전체 판서 (0ms 실시간 화면 프리즈)\n" +
            "• Alt + 3: 교실 집중 타이머 (카운트다운 & 차임벨)\n" +
            "• Alt + 8: 동물 뽑기 레이스\n" +
            "• Alt + 9: 화면 상단 도구바\n" +
            "• Alt + S: 🔏 디지털 전자서명 & 공문서 직인 도장 생성기\n" +
            "• Alt + N: 🚦 실시간 교실 소음 신호등\n" +
            "• Alt + B: 🔔 원터치 교실 효과음 사운드보드\n" +
            "• Alt + Q: 📱 빠른 웹페이지/텍스트 QR코드 생성기\n\n" +
            "※ 작업표시줄 트레이 아이콘을 우클릭하면 수업도구 바로가기 메뉴 및 완전 종료가 가능합니다.";
        System.Windows.MessageBox.Show(guide, "놀티쳐 전역 단축키 & 트레이 모드 안내", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    #endregion

    private void InitWeatherRegions()
    {
        try
        {
            if (ComboWeatherRegion.Items.Count == 0)
            {
                // 1. Resolve school-specific local region (e.g. 강릉 for 강릉교동초등학교)
                var schoolRegion = _weatherService.ResolveSchoolRegion();
                string schoolTag = $"🏫 {schoolRegion.Name} (우리학교)";
                ComboWeatherRegion.Items.Add(schoolTag);

                // 2. Add other regions
                foreach (var r in _weatherService.SupportedRegions)
                {
                    if (r.Name != schoolRegion.Name)
                    {
                        ComboWeatherRegion.Items.Add(r.Name);
                    }
                }
                ComboWeatherRegion.SelectedIndex = 0;
            }
        }
        catch { }
    }

    private async Task LoadWeatherAsync()
    {
        try
        {
            string selRegion = ComboWeatherRegion.SelectedItem as string ?? "서울";
            var w = await _weatherService.GetWeatherAndAirQualityAsync(selRegion);
            if (w != null)
            {
                TxtWeatherIcon.Text = w.WeatherIcon;
                TxtWeatherTemp.Text = $"{w.Temperature:0.0}°C";
                TxtWeatherDesc.Text = $"{w.RegionName} · {w.WeatherDescription}";
                TxtWeatherApparent.Text = $"체감 {w.ApparentTemperature:0.0}° · 습도 {w.Humidity}%";

                TxtPm10Val.Text = $"{w.Pm10Grade} {w.Pm10:0}";
                BadgePm10.Background = (Brush)new BrushConverter().ConvertFromString(w.Pm10BadgeBg)!;
                TxtPm10Val.Foreground = (Brush)new BrushConverter().ConvertFromString(w.Pm10BadgeFg)!;

                TxtPm25Val.Text = $"{w.Pm25Grade} {w.Pm25:0}";
                BadgePm25.Background = (Brush)new BrushConverter().ConvertFromString(w.Pm25BadgeBg)!;
                TxtPm25Val.Foreground = (Brush)new BrushConverter().ConvertFromString(w.Pm25BadgeFg)!;

                TxtOutdoorGuide.Text = w.OutdoorActivityGuide;
                BadgeOutdoorGuide.Background = (Brush)new BrushConverter().ConvertFromString(w.OutdoorGuideBg)!;
                TxtOutdoorGuide.Foreground = (Brush)new BrushConverter().ConvertFromString(w.OutdoorGuideFg)!;
            }
        }
        catch { }
    }

    private async void ComboWeatherRegion_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (IsLoaded)
        {
            await LoadWeatherAsync();
        }
    }

    private async void BtnRefreshWeather_Click(object sender, RoutedEventArgs e)
    {
        await LoadWeatherAsync();
        HudNotificationWindow.Instance.ShowToast("⛅", "날씨 및 미세먼지 정보를 갱신했습니다.");
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
            _timerWindow.PositionToDefaultMonitor();
            _timerWindow.Show();
            _timerWindow.Activate();
        }
    }

    private void BtnShiftTimetable_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new PromptInputDialog("시간 일괄 조정 (당기기/미루기)", "일괄 변경할 시간(분)을 입력하세요:\n(+5: 5분 미루기, -5: 5분 당기기)", "5")
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
        if (sender is FrameworkElement fe && fe.Tag is PeriodItem item)
        {
            var dlg = new PeriodTimerEditDialog(item, _configService, _soundService, _displayManager, _timerWindow, _timetableService)
            {
                Owner = this
            };
            dlg.ShowDialog();
        }
        else
        {
            if (_timerWindow.IsVisible) _timerWindow.Hide();
            else
            {
                _timerWindow.PositionToDefaultMonitor();
                _timerWindow.Show();
                _timerWindow.Activate();
            }
        }
    }

    private void MenuItemPeriodTimerSettings_Click(object sender, RoutedEventArgs e)
    {
        var item = GetPeriodItemFromMenuItem(sender);
        if (item != null)
        {
            var dlg = new PeriodTimerEditDialog(item, _configService, _soundService, _displayManager, _timerWindow, _timetableService)
            {
                Owner = this
            };
            dlg.ShowDialog();
        }
    }

    private PeriodItem? GetPeriodItemFromMenuItem(object sender)
    {
        if (sender is System.Windows.Controls.MenuItem menuItem)
        {
            DependencyObject current = menuItem;
            while (current != null)
            {
                if (current is ContextMenu cm)
                {
                    if (cm.PlacementTarget is FrameworkElement fe && fe.DataContext is PeriodItem item)
                    {
                        return item;
                    }
                    break;
                }
                current = LogicalTreeHelper.GetParent(current) ?? VisualTreeHelper.GetParent(current);
            }
        }
        return null;
    }

    private void MenuEditSubject_Click(object sender, RoutedEventArgs e)
    {
        var item = GetPeriodItemFromMenuItem(sender);
        if (item != null && !item.IsLunch)
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

    private void MenuQuickSubject_Click(object sender, RoutedEventArgs e)
    {
        if (sender is System.Windows.Controls.MenuItem mi && mi.Tag is string subject && !string.IsNullOrWhiteSpace(subject))
        {
            var item = GetPeriodItemFromMenuItem(sender);
            if (item != null && !item.IsLunch)
            {
                _timetableService.UpdateTodayPeriodSubject(item.Period - 1, subject, item.Tag);
                RefreshTimetable();
                HudNotificationWindow.Instance.ShowToast("📚", $"{item.Name} 과목이 '{subject}'(으)로 변경되었습니다.");
            }
        }
    }

    private void MenuQuickTag_Click(object sender, RoutedEventArgs e)
    {
        if (sender is System.Windows.Controls.MenuItem mi && mi.Tag is string tag)
        {
            var item = GetPeriodItemFromMenuItem(sender);
            if (item != null && !item.IsLunch)
            {
                _timetableService.UpdateTodayPeriodSubject(item.Period - 1, item.Subject, tag);
                RefreshTimetable();
                string tagMsg = string.IsNullOrWhiteSpace(tag) ? "태그가 해제되었습니다." : $"'{tag}' 태그로 설정되었습니다.";
                HudNotificationWindow.Instance.ShowToast("🏷️", $"{item.Name} {tagMsg}");
            }
        }
    }

    private void MenuItemTimer_Click(object sender, RoutedEventArgs e)
    {
        var item = GetPeriodItemFromMenuItem(sender);
        if (item != null)
        {
            if (_timerWindow.IsVisible) _timerWindow.Hide();
            else
            {
                _timerWindow.PositionToDefaultMonitor();
                _timerWindow.Show();
                _timerWindow.Activate();
            }
        }
    }

    private void MenuItemToggleAlarm_Click(object sender, RoutedEventArgs e)
    {
        var item = GetPeriodItemFromMenuItem(sender);
        if (item != null && !item.IsLunch)
        {
            _timetableService.TogglePeriodAlarm(item.Period);
            RefreshTimetable();
            HudNotificationWindow.Instance.ShowToast(item.AlarmEnabled ? "🔔" : "🔕", $"{item.Name} 알람 상태가 변경되었습니다.");
        }
    }

    private void MenuClearSubject_Click(object sender, RoutedEventArgs e)
    {
        var item = GetPeriodItemFromMenuItem(sender);
        if (item != null && !item.IsLunch)
        {
            _timetableService.UpdateTodayPeriodSubject(item.Period - 1, "-", "");
            RefreshTimetable();
            HudNotificationWindow.Instance.ShowToast("🧹", $"{item.Name} 과목이 비워졌습니다.");
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
            if (DrawerOverlay != null) DrawerOverlay.Visibility = Visibility.Collapsed;

            var accentBrush = (SolidColorBrush)FindResource("BeigeAccent");
            var transparentBrush = Brushes.Transparent;
            var textMainBrush = (SolidColorBrush)FindResource("BeigeTextMain");

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

            if (index == 0)
            {
                NavBtnToday.Background = (Brush)FindResource("BeigeAccentSoft");
                NavBtnToday.Foreground = accentBrush;
                if (BtnReturnDashboard != null) BtnReturnDashboard.Visibility = Visibility.Collapsed;
                TxtViewTitle.Text = "📅 오늘의 일과 & 급식";
            }
            else
            {
                if (BtnReturnDashboard != null) BtnReturnDashboard.Visibility = Visibility.Visible;

                if (index == 1) { NavBtnTools.Background = (Brush)FindResource("BeigeAccentSoft"); NavBtnTools.Foreground = accentBrush; TxtViewTitle.Text = "🧰 수업 & 교실 도구"; }
                else if (index == 2) { NavBtnSchedule.Background = (Brush)FindResource("BeigeAccentSoft"); NavBtnSchedule.Foreground = accentBrush; TxtViewTitle.Text = "⏰ 예약 실행 & 알림"; }
                else if (index == 3) { NavBtnZen.Background = (Brush)FindResource("BeigeAccentSoft"); NavBtnZen.Foreground = accentBrush; TxtViewTitle.Text = "🧹 바탕화면 & PC 정리"; }
                else if (index == 4) { NavBtnSites.Background = (Brush)FindResource("BeigeAccentSoft"); NavBtnSites.Foreground = accentBrush; TxtViewTitle.Text = "🌐 유용한 교육 사이트"; }
                else if (index == 5) { NavBtnNeis.Background = (Brush)FindResource("BeigeAccentSoft"); NavBtnNeis.Foreground = accentBrush; TxtViewTitle.Text = "📝 나이스 평어 일괄입력"; }
            }
        }
    }

    private void MainTabs_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (e.Source == MainTabs)
        {
            UpdateWindowTitle(MainTabs.SelectedIndex);
            if (BtnToggleWidgetEdit != null)
            {
                BtnToggleWidgetEdit.Visibility = MainTabs.SelectedIndex == 0 ? Visibility.Visible : Visibility.Collapsed;
            }
            if (MainTabs.SelectedIndex != 0 && _isWidgetEditMode)
            {
                SetWidgetEditMode(false);
            }
        }
    }

    private void UpdateWindowTitle(int tabIndex)
    {
        string screenTitle = tabIndex switch
        {
            0 => "메인화면",
            1 => "수업 & 교실 도구",
            2 => "예약 실행 & 알림",
            3 => "바탕화면 & PC 정리",
            4 => "교육 사이트 모음",
            5 => "나이스 평어 일괄입력",
            _ => "메인화면"
        };

        this.Title = screenTitle;
        if (AppTitleBar != null)
        {
            AppTitleBar.Title = screenTitle;
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
        try
        {
            if (BtnCheckVersion != null)
            {
                BtnCheckVersion.IsEnabled = false;
                BtnCheckVersion.Content = "⏳ 버전 확인 중...";
            }

            var updateInfo = await _updateService.CheckForUpdatesAsync();

            if (updateInfo.HasUpdate)
            {
                // Show in-app update dialog without external browser redirect!
                var dialog = new AppUpdateDialog(_updateService, updateInfo)
                {
                    Owner = this
                };
                dialog.ShowDialog();
            }
            else
            {
                string msg =
                    $"🎉 현재 최신 버전({_updateService.CurrentVersion})을 사용 중입니다!\n\n" +
                    "• 학생 제출물 & 과제 체크리스트 위젯 (바둑판 1~30, 다중 탭)\n" +
                    "• 시간대별 알림장 자동 안내 문구 & 세트 묶음 관리\n" +
                    "• 48pt 대형 공지 확대경 & 한국어 TTS 음성 낭독\n" +
                    "• 놀보드 위젯 위치 잠금 🔒 & 카드 투명도(20~100%) 조절\n" +
                    "• 교실 소음 신호등 3단계 표정 & 일시정지 (발표·활동)\n" +
                    "• 학사일정 연계 교원 월 15일 복무·조퇴 자동 계산기\n\n" +
                    "모든 최신 기능과 시스템 안정성이 완벽하게 유지되고 있습니다.";

                System.Windows.MessageBox.Show(
                    msg,
                    $"놀티쳐 최신 버전 확인 ({_updateService.CurrentVersion})",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);
            }
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show(
                $"버전 확인 중 문제가 발생했습니다:\n{ex.Message}",
                "버전 확인 안내",
                MessageBoxButton.OK,
                MessageBoxImage.Warning);
        }
        finally
        {
            if (BtnCheckVersion != null)
            {
                BtnCheckVersion.IsEnabled = true;
                BtnCheckVersion.Content = $"🚀 버전 확인 ({_updateService.CurrentVersion})";
            }
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
            _timerWindow.PositionToDefaultMonitor();
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

    private void BtnLaunchSchoolScale_Click(object sender, RoutedEventArgs e)
    {
        if (_schoolScaleWindow.IsVisible)
        {
            _schoolScaleWindow.Activate();
        }
        else
        {
            _schoolScaleWindow.Show();
            _schoolScaleWindow.Activate();
        }
    }

    private void BtnLaunchNoiseTrafficLight_Click(object sender, RoutedEventArgs e)
    {
        if (_noiseTrafficLightWindow.IsVisible)
        {
            _noiseTrafficLightWindow.Activate();
        }
        else
        {
            _noiseTrafficLightWindow.Show();
            _noiseTrafficLightWindow.Activate();
        }
    }

    private void BtnLaunchChecklist_Click(object sender, RoutedEventArgs e)
    {
        if (!_studentDisplayWindow.IsVisible)
        {
            _displayManager.MoveToStudentMonitor(_studentDisplayWindow, maximize: true);
            _studentDisplayWindow.Show();
        }
        _studentDisplayWindow.Activate();
        _studentDisplayWindow.ToggleWidget("checklist");
    }

    private void BtnLaunchWorkdayCalculator_Click(object sender, RoutedEventArgs e)
    {
        if (_workdayCalculatorWindow.IsVisible)
        {
            _workdayCalculatorWindow.Activate();
        }
        else
        {
            _workdayCalculatorWindow.Show();
            _workdayCalculatorWindow.Activate();
        }
    }

    private void BtnLaunchSeatShuffle_Click(object sender, RoutedEventArgs e)
    {
        if (_smartSeatShuffleWindow.IsVisible)
        {
            _smartSeatShuffleWindow.Activate();
        }
        else
        {
            _smartSeatShuffleWindow.Show();
            _smartSeatShuffleWindow.Activate();
        }
    }

    private void BtnLaunchSoundboard_Click(object sender, RoutedEventArgs e)
    {
        if (_soundboardWindow.IsVisible)
        {
            _soundboardWindow.Activate();
        }
        else
        {
            _soundboardWindow.Show();
            _soundboardWindow.Activate();
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
            "🚀 [나이스 일괄 복사 붙여넣기 코드가 복사되었습니다!]\n\n" +
            "【사용 방법】\n" +
            "1. 4세대 나이스 웹 화면(행동특성 또는 학기말종합의견)을 켭니다.\n" +
            "2. 키보드 [F12] (개발자 도구)를 누릅니다.\n" +
            "3. 상단의 [Console] (콘솔) 탭을 클릭합니다.\n" +
            "4. [Ctrl + V]로 붙여넣은 후 [Enter]를 누르면,\n" +
            "   " + _neisComments.Count + "명의 학생 번호에 맞춰 1초 만에 자동으로 쏙 채워집니다!\n\n" +
            "※ 입력 확인 후 나이스 상단의 [저장] 버튼을 클릭해 완료하세요.",
            "나이스 일괄 복사 붙여넣기 코드 복사 완료",
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

    #region Bento Grid, Todo List & Navigation Drawer Handlers

    private bool _isWidgetEditMode = false;
    private DispatcherTimer? _miniTimer;
    private int _miniTimerRemainingSeconds = 300;
    private bool _isMiniTimerRunning = false;
    private DateTime _miniDDayTarget = DateTime.Today.AddDays(14);
    private string _miniDDayTitle = "여름방학";
    private int _ddayPresetIndex = 0;
    private readonly (string title, DateTime target)[] _ddayPresets = new[]
    {
        ("여름방학", new DateTime(DateTime.Today.Year, 7, 24)),
        ("2학기 개학", new DateTime(DateTime.Today.Year, 8, 20)),
        ("가을 운동회", new DateTime(DateTime.Today.Year, 10, 15)),
        ("겨울방학", new DateTime(DateTime.Today.Year, 12, 28)),
        ("종업식 & 졸업식", new DateTime(DateTime.Today.Year + 1, 1, 10))
    };
    private static readonly string[] _avatarPool = { "🦁", "🐯", "🐻", "🐼", "🐨", "🦊", "🐰", "🐵", "🦄", "🐶", "🐱", "🐸" };
    private readonly Random _rand = new();

    private MainWidgetCard? GetCardById(string widgetId) => widgetId switch
    {
        "timetable" => CardTimetable,
        "todo" => CardTodo,
        "calendar" => CardCalendar,
        "meal" => CardMeal,
        "timer" => CardTimer,
        "picker" => CardPicker,
        "notice" => CardNotice,
        "dday" => CardDDay,
        _ => null
    };

    private IEnumerable<MainWidgetCard> GetAllCards()
    {
        if (CardTimetable != null) yield return CardTimetable;
        if (CardTodo != null) yield return CardTodo;
        if (CardCalendar != null) yield return CardCalendar;
        if (CardMeal != null) yield return CardMeal;
        if (CardTimer != null) yield return CardTimer;
        if (CardPicker != null) yield return CardPicker;
        if (CardNotice != null) yield return CardNotice;
        if (CardDDay != null) yield return CardDDay;
    }

    private void InitWidgetSystem()
    {
        foreach (var card in GetAllCards())
        {
            card.Moved += OnWidgetCardMoved;
            card.Resized += OnWidgetCardResized;
            card.Closed += OnWidgetCardClosed;
        }

        LoadWidgetLayout();
        InitMiniWidgets();
    }

    private void LoadWidgetLayout()
    {
        var layout = _configService.MainWidgetLayout;
        if (layout == null || layout.Widgets == null || layout.Widgets.Count == 0)
        {
            double w = MainWidgetScrollViewer?.ActualWidth > 0 ? MainWidgetScrollViewer.ActualWidth : 1460;
            double h = MainWidgetScrollViewer?.ActualHeight > 0 ? MainWidgetScrollViewer.ActualHeight : 860;
            layout = MainWidgetLayoutConfig.CreateDefault(w, h);
            _configService.MainWidgetLayout = layout;
        }

        ApplyWidgetLayout(layout);
    }

    private void ApplyWidgetLayout(MainWidgetLayoutConfig layout)
    {
        if (MainWidgetCanvas == null) return;

        bool isLocked = layout.IsLocked;
        UpdateLockVisuals(isLocked);

        foreach (var state in layout.Widgets)
        {
            var card = GetCardById(state.Id);
            if (card == null) continue;

            Canvas.SetLeft(card, Math.Max(0, state.X));
            Canvas.SetTop(card, Math.Max(0, state.Y));

            if (state.Width > 0) card.Width = state.Width;
            if (state.Height > 0) card.Height = state.Height;

            card.Visibility = state.IsVisible ? Visibility.Visible : Visibility.Collapsed;
            card.IsLocked = isLocked;
            card.IsEditMode = _isWidgetEditMode;
            if (state.ZIndex > 0) Panel.SetZIndex(card, state.ZIndex);
        }

        UpdateCanvasBounds();
    }

    private void UpdateCanvasBounds()
    {
        if (MainWidgetCanvas == null || MainWidgetScrollViewer == null) return;

        double maxRight = MainWidgetScrollViewer.ActualWidth > 0 ? MainWidgetScrollViewer.ActualWidth - 20 : 1460;
        double maxBottom = MainWidgetScrollViewer.ActualHeight > 0 ? MainWidgetScrollViewer.ActualHeight - 20 : 860;

        foreach (var card in GetAllCards())
        {
            if (card.Visibility != Visibility.Visible) continue;
            double left = Canvas.GetLeft(card);
            double top = Canvas.GetTop(card);
            double w = card.ActualWidth > 0 ? card.ActualWidth : card.Width;
            double h = card.ActualHeight > 0 ? card.ActualHeight : card.Height;

            if (double.IsNaN(w) || w <= 0) w = 320;
            if (double.IsNaN(h) || h <= 0) h = 260;

            maxRight = Math.Max(maxRight, left + w + 20);
            maxBottom = Math.Max(maxBottom, top + h + 20);
        }

        MainWidgetCanvas.Width = maxRight;
        MainWidgetCanvas.Height = maxBottom;
    }

    private void OnWidgetCardMoved(MainWidgetCard card)
    {
        var state = _configService.MainWidgetLayout.Widgets.FirstOrDefault(w => w.Id == card.WidgetId);
        if (state != null)
        {
            state.X = Canvas.GetLeft(card);
            state.Y = Canvas.GetTop(card);
            state.ZIndex = Panel.GetZIndex(card);
            _configService.SaveMainWidgetLayout();
        }
        UpdateCanvasBounds();
    }

    private void OnWidgetCardResized(MainWidgetCard card)
    {
        var state = _configService.MainWidgetLayout.Widgets.FirstOrDefault(w => w.Id == card.WidgetId);
        if (state != null)
        {
            state.Width = card.ActualWidth > 0 ? card.ActualWidth : card.Width;
            state.Height = card.ActualHeight > 0 ? card.ActualHeight : card.Height;
            _configService.SaveMainWidgetLayout();
        }
        UpdateCanvasBounds();
    }

    private void OnWidgetCardClosed(MainWidgetCard card)
    {
        var state = _configService.MainWidgetLayout.Widgets.FirstOrDefault(w => w.Id == card.WidgetId);
        if (state != null)
        {
            state.IsVisible = false;
            _configService.SaveMainWidgetLayout();
        }
        UpdateCanvasBounds();
    }

    private void BtnToggleWidgetEdit_Click(object sender, RoutedEventArgs e)
    {
        SetWidgetEditMode(!_isWidgetEditMode);
    }

    private void BtnFinishWidgetEdit_Click(object sender, RoutedEventArgs e)
    {
        SetWidgetEditMode(false);
    }

    private void SetWidgetEditMode(bool editMode)
    {
        _isWidgetEditMode = editMode;

        if (_isWidgetEditMode)
        {
            TxtWidgetEditIcon.Text = "💾";
            TxtWidgetEditLabel.Text = "편집 완료";
            BtnToggleWidgetEdit.Background = new SolidColorBrush((System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#2563EB"));
            BtnToggleWidgetEdit.Foreground = System.Windows.Media.Brushes.White;
            if (BarWidgetEditTools != null) BarWidgetEditTools.Visibility = Visibility.Visible;
        }
        else
        {
            TxtWidgetEditIcon.Text = "⚙️";
            TxtWidgetEditLabel.Text = "위젯 편집";
            BtnToggleWidgetEdit.Background = new SolidColorBrush((System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#F1F5F9"));
            BtnToggleWidgetEdit.Foreground = new SolidColorBrush((System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#334155"));
            if (BarWidgetEditTools != null) BarWidgetEditTools.Visibility = Visibility.Collapsed;
            _configService.SaveMainWidgetLayout();
        }

        foreach (var card in GetAllCards())
        {
            card.IsEditMode = _isWidgetEditMode;
        }
    }

    private void BtnAddWidgetMenu_Click(object sender, RoutedEventArgs e)
    {
        if (BtnAddWidgetMenu.ContextMenu != null)
        {
            BtnAddWidgetMenu.ContextMenu.PlacementTarget = BtnAddWidgetMenu;
            BtnAddWidgetMenu.ContextMenu.IsOpen = true;
        }
    }

    private void MenuItemAddWidget_Click(object sender, RoutedEventArgs e)
    {
        if (sender is System.Windows.Controls.MenuItem mi && mi.Tag is string widgetId)
        {
            var card = GetCardById(widgetId);
            if (card != null)
            {
                card.Visibility = Visibility.Visible;
                card.BringToFront();

                if (Canvas.GetLeft(card) <= 0 && Canvas.GetTop(card) <= 0)
                {
                    Canvas.SetLeft(card, 60);
                    Canvas.SetTop(card, 60);
                }

                var state = _configService.MainWidgetLayout.Widgets.FirstOrDefault(w => w.Id == widgetId);
                if (state == null)
                {
                    state = new MainWidgetState { Id = widgetId, X = Canvas.GetLeft(card), Y = Canvas.GetTop(card), Width = card.Width, Height = card.Height, IsVisible = true };
                    _configService.MainWidgetLayout.Widgets.Add(state);
                }
                else
                {
                    state.IsVisible = true;
                    state.X = Canvas.GetLeft(card);
                    state.Y = Canvas.GetTop(card);
                }
                _configService.SaveMainWidgetLayout();
                UpdateCanvasBounds();
            }
        }
    }

    private void BtnResetWidgetLayout_Click(object sender, RoutedEventArgs e)
    {
        double w = MainWidgetScrollViewer?.ActualWidth > 0 ? MainWidgetScrollViewer.ActualWidth : 1460;
        double h = MainWidgetScrollViewer?.ActualHeight > 0 ? MainWidgetScrollViewer.ActualHeight : 860;

        var defaultLayout = MainWidgetLayoutConfig.CreateDefault(w, h);
        defaultLayout.IsLocked = _configService.MainWidgetLayout.IsLocked;
        _configService.MainWidgetLayout = defaultLayout;
        _configService.SaveMainWidgetLayout();

        ApplyWidgetLayout(defaultLayout);
    }

    private void BtnToggleWidgetLock_Click(object sender, RoutedEventArgs e)
    {
        bool newLock = !_configService.MainWidgetLayout.IsLocked;
        _configService.MainWidgetLayout.IsLocked = newLock;
        _configService.SaveMainWidgetLayout();
        UpdateLockVisuals(newLock);

        foreach (var card in GetAllCards())
        {
            card.IsLocked = newLock;
        }
    }

    private void UpdateLockVisuals(bool isLocked)
    {
        if (TxtWidgetLockIcon != null) TxtWidgetLockIcon.Text = isLocked ? "🔒" : "🔓";
        if (TxtWidgetLockLabel != null) TxtWidgetLockLabel.Text = isLocked ? "잠금 해제" : "위치 잠금";
    }

    private void MainWidgetScrollViewer_SizeChanged(object sender, SizeChangedEventArgs e)
    {
        UpdateCanvasBounds();
    }

    private void InitMiniWidgets()
    {
        _miniTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(1) };
        _miniTimer.Tick += (s, e) =>
        {
            if (_miniTimerRemainingSeconds > 0)
            {
                _miniTimerRemainingSeconds--;
                UpdateMiniTimerDisplay();
                if (_miniTimerRemainingSeconds == 0)
                {
                    _miniTimer.Stop();
                    _isMiniTimerRunning = false;
                    if (BtnMiniTimerStart != null) BtnMiniTimerStart.Content = "▶ 시작";
                    if (TxtMiniTimerState != null) TxtMiniTimerState.Text = "🔔 시간 종료!";
                    try { _soundService?.PlayChime(); } catch { }
                }
            }
        };
        UpdateMiniTimerDisplay();
        UpdateMiniDDayDisplay();
    }

    private void UpdateMiniTimerDisplay()
    {
        if (TxtMiniTimerDisplay != null)
        {
            int m = _miniTimerRemainingSeconds / 60;
            int s = _miniTimerRemainingSeconds % 60;
            TxtMiniTimerDisplay.Text = $"{m:D2}:{s:D2}";
        }
    }

    private void BtnMiniTimerPreset_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && int.TryParse(btn.Tag?.ToString(), out int sec))
        {
            _miniTimerRemainingSeconds = sec;
            if (TxtMiniTimerState != null) TxtMiniTimerState.Text = "집중 시간";
            UpdateMiniTimerDisplay();
        }
    }

    private void BtnMiniTimerStart_Click(object sender, RoutedEventArgs e)
    {
        if (_isMiniTimerRunning)
        {
            _miniTimer?.Stop();
            _isMiniTimerRunning = false;
            BtnMiniTimerStart.Content = "▶ 시작";
            if (TxtMiniTimerState != null) TxtMiniTimerState.Text = "일시정지됨";
        }
        else
        {
            if (_miniTimerRemainingSeconds <= 0) _miniTimerRemainingSeconds = 300;
            _miniTimer?.Start();
            _isMiniTimerRunning = true;
            BtnMiniTimerStart.Content = "⏸ 일시정지";
            if (TxtMiniTimerState != null) TxtMiniTimerState.Text = "⏱️ 집중 시간 진행 중";
        }
    }

    private void BtnMiniTimerReset_Click(object sender, RoutedEventArgs e)
    {
        _miniTimer?.Stop();
        _isMiniTimerRunning = false;
        _miniTimerRemainingSeconds = 300;
        if (BtnMiniTimerStart != null) BtnMiniTimerStart.Content = "▶ 시작";
        if (TxtMiniTimerState != null) TxtMiniTimerState.Text = "집중 시간";
        UpdateMiniTimerDisplay();
    }

    private void ApplyDefaultWidgetLayout()
    {
        BtnResetWidgetLayout_Click(this, new RoutedEventArgs());
    }

    private void SaveCurrentWidgetLayout()
    {
        _configService.SaveMainWidgetLayout();
    }

    private void BtnMiniPickerDraw_Click(object sender, RoutedEventArgs e)
    {
        if (_neisComments != null && _neisComments.Count > 0)
        {
            int idx = _rand.Next(_neisComments.Count);
            var student = _neisComments[idx];
            string emoji = _avatarPool[_rand.Next(_avatarPool.Length)];
            if (TxtMiniPickerEmoji != null) TxtMiniPickerEmoji.Text = emoji;
            if (TxtMiniPickerResult != null) TxtMiniPickerResult.Text = $"{student.StudentNumber}번 {student.StudentName}";
            if (TxtMiniPickerSub != null) TxtMiniPickerSub.Text = "🎉 축하합니다! 당첨되었습니다.";
        }
        else
        {
            int num = _rand.Next(1, 26);
            string emoji = _avatarPool[_rand.Next(_avatarPool.Length)];
            if (TxtMiniPickerEmoji != null) TxtMiniPickerEmoji.Text = emoji;
            if (TxtMiniPickerResult != null) TxtMiniPickerResult.Text = $"{num}번 학생";
            if (TxtMiniPickerSub != null) TxtMiniPickerSub.Text = "🎉 축하합니다! 당첨되었습니다.";
        }
    }

    private void BtnSaveMiniNotice_Click(object sender, RoutedEventArgs e)
    {
        MessageBox.Show("학급 공지사항이 저장되었습니다.", "공지 저장", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private void UpdateMiniDDayDisplay()
    {
        if (TxtMiniDDayTitle != null) TxtMiniDDayTitle.Text = _miniDDayTitle;
        if (TxtMiniDDayDate != null) TxtMiniDDayDate.Text = $"목표일: {_miniDDayTarget:yyyy-MM-dd}";
        if (TxtMiniDDayCount != null)
        {
            int days = (_miniDDayTarget.Date - DateTime.Today).Days;
            TxtMiniDDayCount.Text = days == 0 ? "D-Day!" : (days > 0 ? $"D-{days}" : $"D+{-days}");
        }
    }

    private void BtnSetMiniDDay_Click(object sender, RoutedEventArgs e)
    {
        _ddayPresetIndex = (_ddayPresetIndex + 1) % _ddayPresets.Length;
        var preset = _ddayPresets[_ddayPresetIndex];
        _miniDDayTitle = preset.title;
        _miniDDayTarget = preset.target;
        UpdateMiniDDayDisplay();
    }

    #region Todo List Handlers (오늘의 할 일)

    private void LoadTodos()
    {
        try
        {
            string file = Path.Combine(_configService.ConfigDir, "todos.json");
            if (File.Exists(file))
            {
                string json = File.ReadAllText(file);
                var list = JsonSerializer.Deserialize<List<TodoItem>>(json);
                if (list != null && list.Count > 0)
                {
                    _todoItems = new ObservableCollection<TodoItem>(list);
                    if (ListTodoItems != null) ListTodoItems.ItemsSource = _todoItems;
                    return;
                }
            }
        }
        catch { }

        _todoItems = new ObservableCollection<TodoItem>
        {
            new TodoItem { Text = "1교시 수학 교구 확인 (자, 각도기)", IsCompleted = false },
            new TodoItem { Text = "학부모 상담 설문지 취합 및 확인", IsCompleted = false },
            new TodoItem { Text = "하교 전 알림장 지도 및 준비물 확인", IsCompleted = false }
        };
        if (ListTodoItems != null) ListTodoItems.ItemsSource = _todoItems;
        SaveTodos();
    }

    private void SaveTodos()
    {
        try
        {
            string file = Path.Combine(_configService.ConfigDir, "todos.json");
            string json = JsonSerializer.Serialize(_todoItems.ToList(), new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(file, json);
        }
        catch { }
    }

    private void BtnAddTodo_Click(object sender, RoutedEventArgs e)
    {
        if (TbNewTodo != null && !string.IsNullOrWhiteSpace(TbNewTodo.Text))
        {
            _todoItems.Add(new TodoItem { Text = TbNewTodo.Text.Trim(), IsCompleted = false });
            TbNewTodo.Text = string.Empty;
            SaveTodos();
        }
    }

    private void TbNewTodo_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
        {
            BtnAddTodo_Click(sender, e);
        }
    }

    private void TodoCheckbox_Click(object sender, RoutedEventArgs e)
    {
        SaveTodos();
    }

    private void BtnDeleteTodo_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement fe && fe.Tag is TodoItem item)
        {
            _todoItems.Remove(item);
            SaveTodos();
        }
    }

    private void BtnTodoMore_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement fe && fe.ContextMenu != null)
        {
            fe.ContextMenu.PlacementTarget = fe;
            fe.ContextMenu.IsOpen = true;
        }
    }

    private void MenuClearCompletedTodos_Click(object sender, RoutedEventArgs e)
    {
        var completed = _todoItems.Where(t => t.IsCompleted).ToList();
        foreach (var item in completed) _todoItems.Remove(item);
        SaveTodos();
    }

    private void MenuResetSampleTodos_Click(object sender, RoutedEventArgs e)
    {
        _todoItems.Clear();
        _todoItems.Add(new TodoItem { Text = "1교시 수학 교구 확인 (자, 각도기)", IsCompleted = false });
        _todoItems.Add(new TodoItem { Text = "학부모 상담 설문지 취합 및 확인", IsCompleted = false });
        _todoItems.Add(new TodoItem { Text = "하교 전 알림장 지도 및 준비물 확인", IsCompleted = false });
        SaveTodos();
    }

    #endregion

    #region Dual-Focus Workspace: Teacher Todo vs Student Notice & Monitor Sync

    private string _noticeFile => Path.Combine(_configService.ConfigDir, "board_memo.txt");

    private void LoadMainNotice()
    {
        try
        {
            if (File.Exists(_noticeFile))
            {
                TbMainNotice.Text = File.ReadAllText(_noticeFile);
            }
            else
            {
                TbMainNotice.Text = "• [알림] 오늘 5교시는 음악실에서 수업합니다.\n• [준비물] 수학익힘책 42쪽 풀어오기\n• [과제] 주말 독서록 작성하기";
                File.WriteAllText(_noticeFile, TbMainNotice.Text);
            }
        }
        catch { }

        MemoWidgetView.OnNoticeChanged += (newText, sender) =>
        {
            if (sender != this)
            {
                Dispatcher.Invoke(() =>
                {
                    if (TbMainNotice != null && TbMainNotice.Text != newText)
                    {
                        TbMainNotice.Text = newText;
                    }
                });
            }
        };
    }

    private void RbMemoTab_Checked(object sender, RoutedEventArgs e)
    {
        if (PanelTeacherTodo == null || PanelStudentNotice == null) return;

        if (RbTabTeacherTodo?.IsChecked == true)
        {
            PanelTeacherTodo.Visibility = Visibility.Visible;
            PanelStudentNotice.Visibility = Visibility.Collapsed;
        }
        else
        {
            PanelTeacherTodo.Visibility = Visibility.Collapsed;
            PanelStudentNotice.Visibility = Visibility.Visible;
        }
    }

    private void TbMainNotice_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (TbMainNotice == null) return;
        try
        {
            File.WriteAllText(_noticeFile, TbMainNotice.Text);
        }
        catch { }
        MemoWidgetView.NotifyNoticeChanged(TbMainNotice.Text, this);
    }

    private void BtnInsertNoticeTag_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string tag)
        {
            if (!string.IsNullOrEmpty(TbMainNotice.Text) && !TbMainNotice.Text.EndsWith("\n"))
            {
                TbMainNotice.AppendText("\n");
            }
            TbMainNotice.AppendText(tag);
            TbMainNotice.CaretIndex = TbMainNotice.Text.Length;
            TbMainNotice.Focus();
        }
    }

    private void BtnSendNoticeToMonitor2_Click(object sender, RoutedEventArgs e)
    {
        _displayManager.MoveToStudentMonitor(_studentDisplayWindow, maximize: true);
        _studentDisplayWindow.Show();
        _studentDisplayWindow.Activate();

        var existingMemo = _studentDisplayWindow.FindWidget("memo");
        if (existingMemo == null)
        {
            _studentDisplayWindow.SpawnWidget("memo", 750, 30);
        }
        HudNotificationWindow.Instance.ShowToast("📢", "학급 알림장을 모니터 2(학생 화면)에 띄웠습니다.");
    }

    private void BtnZoomNoticeFromMain_Click(object sender, RoutedEventArgs e)
    {
        var tts = (Application.Current as App)?.Services?.GetService(typeof(ITtsService)) as ITtsService;
        var zoomWin = new NoticeZoomWindow(TbMainNotice.Text, tts);
        zoomWin.ShowDialog();
    }

    private void BtnTtsNoticeMain_Click(object sender, RoutedEventArgs e)
    {
        var tts = (Application.Current as App)?.Services?.GetService(typeof(ITtsService)) as ITtsService;
        if (tts == null) return;
        if (tts.IsSpeaking)
        {
            tts.Stop();
            BtnTtsNoticeMain.Content = "🔊 낭독";
        }
        else
        {
            BtnTtsNoticeMain.Content = "⏹️ 중지";
            _ = tts.SpeakAsync(TbMainNotice.Text);
        }
    }

    private void UpdateMonitorStatusBadge()
    {
        if (PillMonitorStatus == null || TxtMonitorStatus == null || TxtMonitorIcon == null) return;

        bool isDual = _displayManager.IsDualMonitor;
        if (isDual)
        {
            PillMonitorStatus.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#EFF6FF"));
            PillMonitorStatus.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#BFDBFE"));
            TxtMonitorIcon.Text = "📺";
            TxtMonitorStatus.Text = "듀얼 모니터 (모니터 2 학생용 감지)";
            TxtMonitorStatus.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1D4ED8"));
        }
        else
        {
            PillMonitorStatus.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F1F5F9"));
            PillMonitorStatus.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#E2E8F0"));
            TxtMonitorIcon.Text = "💻";
            TxtMonitorStatus.Text = "단일 모니터 모드 (화면 공유)";
            TxtMonitorStatus.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#64748B"));
        }
    }

    private void PillMonitorStatus_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        string desc = _displayManager.MonitorStatusDescription;
        int count = _displayManager.ScreenCount;
        string msg = $"🖥️ 디스플레이 환경 안내\n\n" +
                     $"• 감지된 모니터: 총 {count}대\n" +
                     $"• 상태: {desc}\n\n" +
                     $"【기본 화면 배치 원칙】\n" +
                     $"• 모니터 1: 선생님 메인 PC (교사 비공개 업무, 시간표, 개인 할 일)\n" +
                     $"• 모니터 2: 학생용 전자칠판 / TV (놀보드, 알림장, 판서, 타이머, 뽑기)\n\n" +
                     (count >= 2 
                        ? "✅ 듀얼 모니터가 최적화되어 작동 중입니다. 학생용 도구는 모니터 2에 우선 전송됩니다." 
                        : "ℹ️ 현재 단일 모니터 환경입니다. 모든 학생용 도구는 현재 화면(모니터 1) 위에 안전하게 표시됩니다.");

        MessageBox.Show(msg, "디스플레이 및 모니터 설정 안내", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    #endregion

    #region Drawer & Timetable More Handlers

    private void BtnToggleDrawer_Click(object sender, RoutedEventArgs e)
    {
        if (DrawerOverlay != null)
        {
            DrawerOverlay.Visibility = (DrawerOverlay.Visibility == Visibility.Visible) ? Visibility.Collapsed : Visibility.Visible;
        }
    }

    private void BtnCloseDrawer_Click(object sender, RoutedEventArgs e)
    {
        if (DrawerOverlay != null) DrawerOverlay.Visibility = Visibility.Collapsed;
    }

    private void DrawerBackdrop_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (DrawerOverlay != null) DrawerOverlay.Visibility = Visibility.Collapsed;
    }

    private void BtnReturnDashboard_Click(object sender, RoutedEventArgs e)
    {
        MainTabs.SelectedIndex = 0;
        if (BtnReturnDashboard != null) BtnReturnDashboard.Visibility = Visibility.Collapsed;
        NavBtnToday.Background = (Brush)FindResource("BeigeAccentSoft");
        NavBtnToday.Foreground = (Brush)FindResource("BeigeAccent");
    }

    private void BtnTimetableMore_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement fe && fe.ContextMenu != null)
        {
            fe.ContextMenu.PlacementTarget = fe;
            fe.ContextMenu.IsOpen = true;
        }
    }

    private void BtnEditAllTimetable_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new PeriodAlarmSettingsDialog(_configService, _soundService, _timetableService) { Owner = this };
        dlg.ShowDialog();
        RefreshTimetable();
    }

    #endregion

    #endregion

    #region Template Sharing, Startup & Interactive Tutorial

    private void OnExternalDataChanged()
    {
        Dispatcher.Invoke(async () =>
        {
            RefreshTimetable();
            await LoadCalendarAsync();
            await LoadUpcomingDDaysAsync();
            LoadWidgetLayout();
        });
    }

    private void BtnLaunchTemplateShare_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            _templateShareWindow.Owner = this;
            _templateShareWindow.ShowDialog();
        }
        catch
        {
            _templateShareWindow.Show();
        }
    }

    private void BtnOpenTutorial_Click(object sender, RoutedEventArgs e)
    {
        StartTutorial(isFirstRun: false);
    }

    private void ChkAutoStartup_Click(object sender, RoutedEventArgs e)
    {
        bool isEnabled = ChkAutoStartup.IsChecked == true;
        bool success = _startupService.SetStartupEnabled(isEnabled);
        if (success)
        {
            System.Windows.MessageBox.Show(
                isEnabled ? "놀티쳐가 윈도우 시작 프로그램으로 등록되었습니다.\r\nPC 부팅 시 자동으로 실행됩니다."
                          : "시작 프로그램 등록이 해제되었습니다.",
                "시작 프로그램 설정", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        else
        {
            ChkAutoStartup.IsChecked = !isEnabled;
            System.Windows.MessageBox.Show("시작 프로그램 설정을 변경하지 못했습니다.", "설정 안내", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void StartTutorial(bool isFirstRun = true)
    {
        _tutorialStep = 1;
        TutorialOverlay.Visibility = Visibility.Visible;
        RenderTutorialStep();
    }

    private void RenderTutorialStep()
    {
        TxtTutorialStepBadge.Text = $"{_tutorialStep} / 5 단계";
        TutorialActionBox.Visibility = Visibility.Visible;
        BtnTutorialPrev.IsEnabled = _tutorialStep > 1;
        BtnTutorialNext.Content = "다음 ▶";

        if (_tutorialStep == 1)
        {
            MainTabs.SelectedIndex = 0;
            TxtTutorialStepIcon.Text = "📐";
            TxtTutorialStepTitle.Text = "메인화면 & 나만의 위젯 커스텀";
            TxtTutorialStepDesc.Text = "첫 화면에서 시간표, 급식, 날씨, 캘린더, D-Day, 학급 안내를 한눈에 확인할 수 있습니다. 위젯 모서리를 끌어 크기를 조절하고, '위젯 크기·배치 설정'으로 자유롭게 첫 화면을 완성해 보세요.";
            ChkTutorialAction.Content = "추천 3단 정돈형 위젯 배치 바로 적용하기";
            ChkTutorialAction.IsChecked = true;
            TxtTutorialActionHint.Text = "체크 시 시간표, 캘린더, 급식·D-Day가 3개 열로 깔끔하게 정돈됩니다.";
            UpdateTutorialSpotlight(PillLivePeriodStatus);
        }
        else if (_tutorialStep == 2)
        {
            MainTabs.SelectedIndex = 0;
            TxtTutorialStepIcon.Text = "⏰";
            TxtTutorialStepTitle.Text = "시간표 & 수업 시작 1분 전 예비령";
            TxtTutorialStepDesc.Text = "실시간 교시 남은 시간 카운트다운과 수업 시작 1분 전 집중 차임벨(예비령)을 제공합니다. 엑셀/CSV 양식으로 시간표를 한 번에 불러올 수도 있습니다.";
            ChkTutorialAction.Content = "수업 시작 1분 전 예비령 알림 차임벨 켜기";
            ChkTutorialAction.IsChecked = true;
            TxtTutorialActionHint.Text = "수업 시작 전 학생들의 주의 집중을 돕는 은은한 차임벨과 카운트다운을 켭니다.";
            UpdateTutorialSpotlight(ListTimetable);
        }
        else if (_tutorialStep == 3)
        {
            MainTabs.SelectedIndex = 0;
            TxtTutorialStepIcon.Text = "📺";
            TxtTutorialStepTitle.Text = "학생용 화면 / 전자칠판 놀보드 (F2)";
            TxtTutorialStepDesc.Text = "F2 키 또는 사이드바 버튼을 누르면 모니터 2(학생 TV/전자칠판)에 놀보드가 열립니다. 화면 판서, 집중 타이머, 실물화상기, 집중벨 등 수업 보조 도구를 자유롭게 배치할 수 있습니다.";
            ChkTutorialAction.Content = "학생용 화면(모니터 2) 자동 감지 및 배치";
            ChkTutorialAction.IsChecked = true;
            TxtTutorialActionHint.Text = "듀얼 모니터 환경에서 학생용 화면을 자동으로 감지하여 놀보드를 우선 띄웁니다.";
            UpdateTutorialSpotlight(PillLivePeriodStatus);
        }
        else if (_tutorialStep == 4)
        {
            MainTabs.SelectedIndex = 1;
            TxtTutorialStepIcon.Text = "📋";
            TxtTutorialStepTitle.Text = "양식 공유 & 시작 프로그램 설정";
            TxtTutorialStepDesc.Text = "동료 교사와 학생 명렬표, 학사일정, 주간 시간표 엑셀/CSV 양식을 손쉽게 주고받아 로컬에 즉시 반영하세요! PC 부팅 시 놀티쳐가 자동으로 켜지도록 설정할 수도 있습니다.";
            ChkTutorialAction.Content = "컴퓨터 켤 때 놀티쳐 자동 실행하기";
            ChkTutorialAction.IsChecked = _startupService.IsStartupEnabled();
            TxtTutorialActionHint.Text = "아침 출근 후 PC를 켜면 수업 준비가 바로 완료되도록 윈도우 시작 프로그램에 등록합니다.";
            UpdateTutorialSpotlight(ChkAutoStartup);
        }
        else if (_tutorialStep == 5)
        {
            MainTabs.SelectedIndex = 0;
            TxtTutorialStepIcon.Text = "🚀";
            TxtTutorialStepTitle.Text = "환영합니다! 모든 준비가 완료되었습니다";
            TxtTutorialStepDesc.Text = "놀티쳐는 선생님의 행복한 교실과 편리한 수업을 진심으로 응원합니다. 언제든 우측 상단 '도움말/튜토리얼' 버튼으로 다시 확인할 수 있습니다.";
            TutorialActionBox.Visibility = Visibility.Collapsed;
            BtnTutorialNext.Content = "🚀 놀티쳐 시작하기";
            UpdateTutorialSpotlight(null);
        }
    }

    private void BtnTutorialNext_Click(object sender, RoutedEventArgs e)
    {
        if (_tutorialStep == 1 && ChkTutorialAction.IsChecked == true)
        {
            ApplyDefaultWidgetLayout();
            SaveCurrentWidgetLayout();
        }
        else if (_tutorialStep == 2 && ChkTutorialAction.IsChecked == true)
        {
            _timetableService.SetAllAlarms(true);
        }
        else if (_tutorialStep == 3 && ChkTutorialAction.IsChecked == true)
        {
            _configService.TimerTargetMonitorIndex = 1;
            _configService.SaveTimerSettings();
        }
        else if (_tutorialStep == 4 && ChkTutorialAction.IsChecked == true)
        {
            _startupService.SetStartupEnabled(true);
            ChkAutoStartup.IsChecked = true;
        }
        else if (_tutorialStep == 5)
        {
            FinishTutorial();
            return;
        }

        _tutorialStep++;
        RenderTutorialStep();
    }

    private void BtnTutorialPrev_Click(object sender, RoutedEventArgs e)
    {
        if (_tutorialStep > 1)
        {
            _tutorialStep--;
            RenderTutorialStep();
        }
    }

    private void BtnTutorialSkip_Click(object sender, RoutedEventArgs e)
    {
        FinishTutorial();
    }

    private void FinishTutorial()
    {
        TutorialOverlay.Visibility = Visibility.Collapsed;
        TutorialSpotlightBorder.Visibility = Visibility.Collapsed;
        MainTabs.SelectedIndex = 0;

        string currentVer = System.Reflection.Assembly.GetExecutingAssembly().GetName().Version?.ToString() ?? "2.9.0";
        _configService.LastSeenTutorialVersion = currentVer;
        _configService.SaveTutorialVersion();
    }

    private void TutorialOverlay_BackgroundClick(object sender, MouseButtonEventArgs e)
    {
    }

    private void UpdateTutorialSpotlight(FrameworkElement? target)
    {
        if (target == null || !target.IsVisible)
        {
            TutorialSpotlightBorder.Visibility = Visibility.Collapsed;
            return;
        }

        Dispatcher.InvokeAsync(async () =>
        {
            await Task.Delay(60);
            try
            {
                var point = target.TranslatePoint(new Point(0, 0), TutorialCanvas);
                Canvas.SetLeft(TutorialSpotlightBorder, Math.Max(0, point.X - 6));
                Canvas.SetTop(TutorialSpotlightBorder, Math.Max(0, point.Y - 6));
                TutorialSpotlightBorder.Width = Math.Max(40, target.ActualWidth + 12);
                TutorialSpotlightBorder.Height = Math.Max(30, target.ActualHeight + 12);
                TutorialSpotlightBorder.Visibility = Visibility.Visible;
            }
            catch
            {
                TutorialSpotlightBorder.Visibility = Visibility.Collapsed;
            }
        });
    }

    #endregion
}
