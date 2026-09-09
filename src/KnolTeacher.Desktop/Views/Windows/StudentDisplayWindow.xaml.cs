using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Ink;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.Views.Controls;
using KnolTeacher.Desktop.Views.Controls.Widgets;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class StudentDisplayWindow : Window
{
    private readonly ISoundService _soundService;
    private readonly IStudentManagerService _studentService;
    private readonly ITimetableService _timetableService;
    private readonly INeisService _neisService;
    private readonly IConfigService _configService;
    private readonly IQrCodeService _qrCodeService;
    private readonly ITtsService? _ttsService;
    private readonly IDisplayManager? _displayManager;
    private readonly IWeatherService? _weatherService;
    private int _currentMonitorIndex = 1;

    private readonly Stack<Stroke> _undoStack = new();
    private readonly DispatcherTimer _clockTimer;
    private readonly List<BoardWidgetHost> _widgets = new();
    private bool _isWidgetsLocked = false;
    private double _currentCardOpacity = 0.95;

    public StudentDisplayWindow(
        ISoundService soundService,
        IStudentManagerService studentService,
        ITimetableService timetableService,
        INeisService neisService,
        IConfigService configService,
        IQrCodeService qrCodeService,
        ITtsService? ttsService = null,
        IDisplayManager? displayManager = null,
        IWeatherService? weatherService = null)
    {
        _soundService = soundService;
        _studentService = studentService;
        _timetableService = timetableService;
        _neisService = neisService;
        _configService = configService;
        _qrCodeService = qrCodeService;
        _ttsService = ttsService ?? (Application.Current as App)?.Services?.GetService(typeof(ITtsService)) as ITtsService;
        _displayManager = displayManager ?? (Application.Current as App)?.Services?.GetService(typeof(IDisplayManager)) as IDisplayManager;
        _weatherService = weatherService ?? (Application.Current as App)?.Services?.GetService(typeof(IWeatherService)) as IWeatherService;

        InitializeComponent();

        // InkCanvas config
        BoardInkCanvas.DefaultDrawingAttributes = new DrawingAttributes
        {
            Color = Colors.White,
            Width = 4,
            Height = 4,
            FitToCurve = true,
            IgnorePressure = false
        };

        Stylus.SetIsPressAndHoldEnabled(BoardInkCanvas, false);
        Stylus.SetIsFlicksEnabled(BoardInkCanvas, false);

        _clockTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(1) };
        _clockTimer.Tick += (s, e) => TxtClock.Text = DateTime.Now.ToString("HH:mm:ss");
        _clockTimer.Start();
        TxtClock.Text = DateTime.Now.ToString("HH:mm:ss");

        BoardInkCanvas.StrokeCollected += (s, e) => _undoStack.Clear();

        WidgetCanvas.SizeChanged += OnWidgetCanvasSizeChanged;

        _isReady = true;
        Loaded += (s, e) =>
        {
            PositionToDefaultMonitor();
            if (!RestoreWidgetsLayout())
            {
                ApplyPresetTools();
            }
        };
    }

    private bool _isReady = false;

    #region Widget Management & Presets

    public void ClearWidgets()
    {
        foreach (var w in _widgets)
        {
            WidgetCanvas.Children.Remove(w);
        }
        _widgets.Clear();
        UpdateDockButtonsState();
    }

    public BoardWidgetHost AddWidget(string type, string title, UserControl view, double x, double y, double w, double h)
    {
        var host = new BoardWidgetHost
        {
            WidgetType = type,
            Title = title,
            WidgetContent = view,
            Width = w,
            Height = h,
            IsLocked = _isWidgetsLocked,
            CardOpacity = _currentCardOpacity
        };

        Canvas.SetLeft(host, x);
        Canvas.SetTop(host, y);

        host.Closed += (target) =>
        {
            WidgetCanvas.Children.Remove(target);
            _widgets.Remove(target);
            UpdateDockButtonsState();
            SaveWidgetsLayout();
        };

        host.MovedOrResized += (target) =>
        {
            SaveWidgetsLayout();
        };

        _widgets.Add(host);
        WidgetCanvas.Children.Add(host);
        UpdateDockButtonsState();
        SaveWidgetsLayout();
        return host;
    }

    public void SaveWidgetsLayout()
    {
        if (!_isReady) return;
        try
        {
            var list = new List<NolboardWidgetState>();
            foreach (var w in _widgets)
            {
                list.Add(new NolboardWidgetState
                {
                    Tag = w.WidgetType,
                    X = Canvas.GetLeft(w),
                    Y = Canvas.GetTop(w),
                    Width = w.ActualWidth > 0 ? w.ActualWidth : (double.IsNaN(w.Width) ? 340 : w.Width),
                    Height = w.ActualHeight > 0 ? w.ActualHeight : (double.IsNaN(w.Height) ? 260 : w.Height)
                });
            }
            _configService.NolboardLayout.Widgets = list;
            _configService.NolboardLayout.HasCustomLayout = true;
            _configService.SaveNolboardLayout();
        }
        catch { }
    }

    public bool RestoreWidgetsLayout()
    {
        var layout = _configService.NolboardLayout;
        if (layout == null || !layout.HasCustomLayout || layout.Widgets == null || layout.Widgets.Count == 0)
        {
            return false;
        }

        ClearWidgets();
        foreach (var state in layout.Widgets)
        {
            var host = SpawnWidget(state.Tag, state.X, state.Y);
            if (host != null)
            {
                if (state.Width > 100) host.Width = state.Width;
                if (state.Height > 80) host.Height = state.Height;
            }
        }
        return _widgets.Count > 0;
    }

    private void BtnSaveBoardLayout_Click(object sender, RoutedEventArgs e)
    {
        SaveWidgetsLayout();
        MessageBox.Show("현재 놀보드 위젯 배치가 안전하게 저장되었습니다.\n다음에 놀보드를 열 때 이 상태로 자동 복원됩니다.", "놀보드 배치 저장 완료", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    public BoardWidgetHost? FindWidget(string type) => _widgets.Find(w => w.WidgetType == type);

    public void ToggleWidget(string key)
    {
        if (key == "pinball")
        {
            OpenPinballWindow();
            return;
        }

        var existing = _widgets.Find(w => w.WidgetType == key);
        if (existing != null)
        {
            WidgetCanvas.Children.Remove(existing);
            _widgets.Remove(existing);
            UpdateDockButtonsState();
        }
        else
        {
            SpawnWidget(key);
        }
    }

    private StudentPickerWindow? _pinballWindow;

    public void OpenPinballWindow()
    {
        var app = Application.Current as App;
        var win = app?.Services?.GetService(typeof(StudentPickerWindow)) as StudentPickerWindow;
        if (win != null)
        {
            _pinballWindow = win;
        }
        else if (_pinballWindow == null)
        {
            _pinballWindow = new StudentPickerWindow(_studentService, _soundService, _displayManager);
        }
        _displayManager?.MoveToStudentMonitor(_pinballWindow, maximize: false);
        _pinballWindow.Show();
        _pinballWindow.Activate();
    }

    public void PositionToDefaultMonitor()
    {
        if (_displayManager != null)
        {
            _currentMonitorIndex = _displayManager.RecommendedStudentMonitorIndex;
            _displayManager.MoveToStudentMonitor(this, maximize: true);
            UpdateMonitorButtonText();
        }
    }

    private void UpdateMonitorButtonText()
    {
        if (BtnSwitchBoardMonitor != null)
        {
            BtnSwitchBoardMonitor.Content = _currentMonitorIndex == 1 ? "📺 모니터 2 (학생용)" : "💻 모니터 1 (메인)";
        }
    }

    public void ToggleMonitor()
    {
        if (_displayManager == null || _displayManager.ScreenCount < 2) return;
        _currentMonitorIndex = _currentMonitorIndex == 1 ? 0 : 1;
        _displayManager.MoveWindowToScreen(this, _currentMonitorIndex, maximize: true);
        UpdateMonitorButtonText();
    }

    private void BtnSwitchBoardMonitor_Click(object sender, RoutedEventArgs e)
    {
        ToggleMonitor();
    }

    private RulerToolControl? _boardRuler;
    private TriangleRulerToolControl? _boardTriangle;
    private ProtractorToolControl? _boardProtractor;

    private void BtnToggleRuler_Click(object sender, RoutedEventArgs e)
    {
        if (_boardRuler == null)
        {
            _boardRuler = new RulerToolControl();
            _boardRuler.CloseRequested += () =>
            {
                BoardToolsCanvas.Children.Remove(_boardRuler);
                _boardRuler = null;
            };
            Canvas.SetLeft(_boardRuler, Math.Max(40, (BoardContainer.ActualWidth - 460) / 2));
            Canvas.SetTop(_boardRuler, Math.Max(40, (BoardContainer.ActualHeight - 80) / 2));
            BoardToolsCanvas.Children.Add(_boardRuler);
        }
        else
        {
            BoardToolsCanvas.Children.Remove(_boardRuler);
            _boardRuler = null;
        }
    }

    private void BtnToggleTriangle_Click(object sender, RoutedEventArgs e)
    {
        if (_boardTriangle == null)
        {
            _boardTriangle = new TriangleRulerToolControl();
            _boardTriangle.CloseRequested += () =>
            {
                BoardToolsCanvas.Children.Remove(_boardTriangle);
                _boardTriangle = null;
            };
            Canvas.SetLeft(_boardTriangle, Math.Max(40, (BoardContainer.ActualWidth - 320) / 2));
            Canvas.SetTop(_boardTriangle, Math.Max(40, (BoardContainer.ActualHeight - 260) / 2));
            BoardToolsCanvas.Children.Add(_boardTriangle);
        }
        else
        {
            BoardToolsCanvas.Children.Remove(_boardTriangle);
            _boardTriangle = null;
        }
    }

    private void BtnToggleProtractor_Click(object sender, RoutedEventArgs e)
    {
        if (_boardProtractor == null)
        {
            _boardProtractor = new ProtractorToolControl();
            _boardProtractor.CloseRequested += () =>
            {
                BoardToolsCanvas.Children.Remove(_boardProtractor);
                _boardProtractor = null;
            };
            Canvas.SetLeft(_boardProtractor, Math.Max(40, (BoardContainer.ActualWidth - 380) / 2));
            Canvas.SetTop(_boardProtractor, Math.Max(40, (BoardContainer.ActualHeight - 210) / 2));
            BoardToolsCanvas.Children.Add(_boardProtractor);
        }
        else
        {
            BoardToolsCanvas.Children.Remove(_boardProtractor);
            _boardProtractor = null;
        }
    }

    public BoardWidgetHost? SpawnWidget(string tag, double? x = null, double? y = null)
    {
        if (tag == "pinball")
        {
            OpenPinballWindow();
            return null;
        }

        double nextX = x ?? (40 + (_widgets.Count * 30) % 360);
        double nextY = y ?? (40 + (_widgets.Count * 30) % 240);

        return tag switch
        {
            "timer" => AddWidget("timer", "⏱️ 수업 타이머", new TimerWidgetView(_soundService), nextX, nextY, 340, 240),
            "picker" => AddWidget("picker", "🎯 발표자 추첨", new PickerWidgetView(_studentService, _soundService), nextX, nextY, 360, 280),
            "dice" => AddWidget("dice", "🎲 스마트 주사위 & 통계", new DiceWidgetView(_soundService), nextX, nextY, 480, 290),
            "wheel" => AddWidget("wheel", "🎡 회전 돌림판", new WheelWidgetView(_soundService), nextX, nextY, 340, 270),
            "score" => AddWidget("score", "🏆 모둠 점수판", new ScoreWidgetView(), nextX, nextY, 360, 270),
            "drawing" => AddWidget("drawing", "✏️ 칠판 판서장", new DrawingWidgetView(), nextX, nextY, 400, 310),
            "timetable" => AddWidget("timetable", "📅 오늘의 시간표", new TimetableWidgetView(_timetableService), nextX, nextY, 320, 440),
            "meal" => AddWidget("meal", "🍱 오늘의 급식", new MealWidgetView(_neisService), nextX, nextY, 320, 440),
            "memo" => AddWidget("memo", "📝 학급 알림장", new MemoWidgetView(_configService, _ttsService), nextX, nextY, 360, 340),
            "checklist" => AddWidget("checklist", "📋 과제 체크리스트", new ChecklistWidgetView(_configService, _studentService), nextX, nextY, 360, 360),
            "qr" => AddWidget("qr", "📱 실시간 수업 QR코드", new QrWidgetView(_qrCodeService), nextX, nextY, 320, 360),
            "weather" => AddWidget("weather", "☀️ 오늘의 날씨 & 미세먼지", new WeatherWidgetView(_weatherService), nextX, nextY, 340, 290),
            "dday" => AddWidget("dday", "🎯 학급 D-Day", new DDayWidgetView(_configService), nextX, nextY, 340, 240),
            _ => null
        };
    }

    public void UpdateDockButtonsState()
    {
        if (!_isReady) return;

        UpdateBtnState(BtnToolTimer, "timer");
        UpdateBtnState(BtnToolPinball, "pinball");
        UpdateBtnState(BtnToolPicker, "picker");
        UpdateBtnState(BtnToolDice, "dice");
        UpdateBtnState(BtnToolWheel, "wheel");
        UpdateBtnState(BtnToolScore, "score");
        UpdateBtnState(BtnToolDrawing, "drawing");
        UpdateBtnState(BtnToolTimetable, "timetable");
        UpdateBtnState(BtnToolMeal, "meal");
        UpdateBtnState(BtnToolMemo, "memo");
        UpdateBtnState(BtnToolChecklist, "checklist");
        UpdateBtnState(BtnToolQr, "qr");
        UpdateBtnState(BtnToolWeather, "weather");
        UpdateBtnState(BtnToolDDay, "dday");
    }

    private void UpdateBtnState(Button? btn, string tag)
    {
        if (btn == null) return;
        bool active = _widgets.Exists(w => w.WidgetType == tag);
        if (active)
        {
            btn.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0284C7"));
            btn.Foreground = Brushes.White;
            btn.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#38BDF8"));
            btn.BorderThickness = new Thickness(1.5);
            btn.FontWeight = FontWeights.Bold;
        }
        else
        {
            btn.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E293B"));
            btn.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#94A3B8"));
            btn.BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#334155"));
            btn.BorderThickness = new Thickness(1);
            btn.FontWeight = FontWeights.SemiBold;
        }
    }

    private double _prevCanvasWidth = 0;
    private double _prevCanvasHeight = 0;

    private void OnWidgetCanvasSizeChanged(object sender, SizeChangedEventArgs e)
    {
        double newWidth = e.NewSize.Width;
        double newHeight = e.NewSize.Height;
        double oldWidth = e.PreviousSize.Width;
        double oldHeight = e.PreviousSize.Height;

        // Proportional widget scaling & repositioning when window is maximized or resized
        if (oldWidth > 200 && oldHeight > 200 && newWidth > 200 && newHeight > 200)
        {
            double scaleX = newWidth / oldWidth;
            double scaleY = newHeight / oldHeight;

            if (Math.Abs(scaleX - 1.0) > 0.01 || Math.Abs(scaleY - 1.0) > 0.01)
            {
                foreach (var w in _widgets)
                {
                    double curLeft = Canvas.GetLeft(w);
                    double curTop = Canvas.GetTop(w);
                    if (double.IsNaN(curLeft)) curLeft = 20;
                    if (double.IsNaN(curTop)) curTop = 20;

                    double curW = w.ActualWidth > 0 ? w.ActualWidth : (double.IsNaN(w.Width) ? 400 : w.Width);
                    double curH = w.ActualHeight > 0 ? w.ActualHeight : (double.IsNaN(w.Height) ? 300 : w.Height);

                    double nextW = Math.Max(200, curW * scaleX);
                    double nextH = Math.Max(150, curH * scaleY);
                    double nextLeft = curLeft * scaleX;
                    double nextTop = curTop * scaleY;

                    if (nextW > newWidth - 20) nextW = Math.Max(200, newWidth - 20);
                    if (nextH > newHeight - 20) nextH = Math.Max(150, newHeight - 20);

                    double maxLeft = Math.Max(10, newWidth - nextW - 10);
                    double maxTop = Math.Max(10, newHeight - nextH - 10);

                    w.Width = nextW;
                    w.Height = nextH;
                    Canvas.SetLeft(w, Math.Clamp(nextLeft, 10, maxLeft));
                    Canvas.SetTop(w, Math.Clamp(nextTop, 10, maxTop));
                }
            }
        }

        _prevCanvasWidth = newWidth;
        _prevCanvasHeight = newHeight;
        ClampAllWidgetsWithinCanvas();
    }

    public void ClampAllWidgetsWithinCanvas()
    {
        double canvasWidth = WidgetCanvas.ActualWidth;
        double canvasHeight = WidgetCanvas.ActualHeight;
        if (canvasWidth <= 100 || canvasHeight <= 100) return;

        foreach (var w in _widgets)
        {
            double curLeft = Canvas.GetLeft(w);
            double curTop = Canvas.GetTop(w);

            if (double.IsNaN(curLeft)) curLeft = 20;
            if (double.IsNaN(curTop)) curTop = 20;

            if (w.ActualWidth > canvasWidth - 20) w.Width = Math.Max(240, canvasWidth - 20);
            if (w.ActualHeight > canvasHeight - 20) w.Height = Math.Max(180, canvasHeight - 20);

            double maxLeft = Math.Max(0, canvasWidth - w.ActualWidth - 10);
            double maxTop = Math.Max(0, canvasHeight - w.ActualHeight - 10);

            Canvas.SetLeft(w, Math.Clamp(curLeft, 10, maxLeft));
            Canvas.SetTop(w, Math.Clamp(curTop, 10, maxTop));
        }
    }

    public void TileActiveWidgets()
    {
        if (_widgets.Count == 0) return;

        double canvasWidth = WidgetCanvas.ActualWidth;
        double canvasHeight = WidgetCanvas.ActualHeight;
        if (canvasWidth <= 200 || canvasHeight <= 200)
        {
            canvasWidth = Width - 40;
            canvasHeight = Height - 140;
        }

        int n = _widgets.Count;
        if (n == 1)
        {
            var w = _widgets[0];
            double ww = Math.Min(780, canvasWidth - 40);
            double wh = Math.Min(520, canvasHeight - 40);
            Canvas.SetLeft(w, Math.Max(20, (canvasWidth - ww) / 2));
            Canvas.SetTop(w, Math.Max(20, (canvasHeight - wh) / 2));
            w.Width = ww;
            w.Height = wh;
        }
        else if (n == 2)
        {
            double halfW = (canvasWidth - 36) / 2;
            double h = Math.Max(300, canvasHeight - 40);
            for (int i = 0; i < 2; i++)
            {
                var w = _widgets[i];
                Canvas.SetLeft(w, 12 + i * (halfW + 12));
                Canvas.SetTop(w, 16);
                w.Width = halfW;
                w.Height = h;
            }
        }
        else if (n == 3)
        {
            // 3 Columns layout: Perfect for Timetable + Meal + Memo
            double colW = (canvasWidth - 48) / 3;
            double h = Math.Max(300, canvasHeight - 36);
            for (int i = 0; i < 3; i++)
            {
                var w = _widgets[i];
                Canvas.SetLeft(w, 12 + i * (colW + 12));
                Canvas.SetTop(w, 16);
                w.Width = colW;
                w.Height = h;
            }
        }
        else if (n == 4)
        {
            double halfW = (canvasWidth - 36) / 2;
            double halfH = (canvasHeight - 36) / 2;
            for (int i = 0; i < 4; i++)
            {
                int r = i / 2;
                int c = i % 2;
                var w = _widgets[i];
                Canvas.SetLeft(w, 12 + c * (halfW + 12));
                Canvas.SetTop(w, 12 + r * (halfH + 12));
                w.Width = halfW;
                w.Height = halfH;
            }
        }
        else
        {
            int cols = (n <= 6) ? 3 : 4;
            int rows = (n + cols - 1) / cols;
            double cw = (canvasWidth - (cols + 1) * 12) / cols;
            double ch = (canvasHeight - (rows + 1) * 12) / rows;
            for (int i = 0; i < n; i++)
            {
                int r = i / cols;
                int c = i % cols;
                var w = _widgets[i];
                Canvas.SetLeft(w, 12 + c * (cw + 12));
                Canvas.SetTop(w, 12 + r * (ch + 12));
                w.Width = cw;
                w.Height = ch;
            }
        }
    }

    private void DockToolBtn_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string tag)
        {
            ToggleWidget(tag);
        }
    }

    private void BtnTileWidgets_Click(object sender, RoutedEventArgs e)
    {
        TileActiveWidgets();
    }

    private void BtnCloseAllWidgets_Click(object sender, RoutedEventArgs e)
    {
        ClearWidgets();
    }

    private void BtnToggleDock_Click(object sender, RoutedEventArgs e)
    {
        if (DockBody.Visibility == Visibility.Visible)
        {
            DockBody.Visibility = Visibility.Collapsed;
            BtnToggleDock.Content = "▲ 도구 바 펼치기";
        }
        else
        {
            DockBody.Visibility = Visibility.Visible;
            BtnToggleDock.Content = "▼ 도구 바 접기";
        }
    }

    private void ApplyPresetTools()
    {
        ClearWidgets();
        // 1. Timer
        AddWidget("timer", "⏱️ 수업 타이머", new TimerWidgetView(_soundService), 30, 30, 340, 240);
        // 2. Picker
        AddWidget("picker", "🎯 발표자 추첨", new PickerWidgetView(_studentService, _soundService), 400, 30, 360, 280);
        // 3. Dice
        AddWidget("dice", "🎲 스마트 주사위 & 통계", new DiceWidgetView(_soundService), 30, 300, 480, 290);
    }

    private void ApplyPresetBoard()
    {
        ClearWidgets();
        // 1. Timetable
        AddWidget("timetable", "📅 오늘의 시간표", new TimetableWidgetView(_timetableService), 30, 30, 330, 480);
        // 2. Meal
        AddWidget("meal", "🍱 오늘의 급식", new MealWidgetView(_neisService), 390, 30, 330, 480);
        // 3. Memo
        AddWidget("memo", "📝 학급 알림장", new MemoWidgetView(_configService, _ttsService), 750, 30, 380, 480);
    }

    private void ApplyPresetSplit()
    {
        ClearWidgets();
        // 1. Timer
        AddWidget("timer", "⏱️ 수업 타이머", new TimerWidgetView(_soundService), 30, 30, 320, 240);
        // 2. Picker
        AddWidget("picker", "🎯 발표자 추첨", new PickerWidgetView(_studentService, _soundService), 30, 290, 320, 260);
        // 3. Timetable
        AddWidget("timetable", "📅 오늘의 시간표", new TimetableWidgetView(_timetableService), 380, 30, 300, 520);
        // 4. Meal
        AddWidget("meal", "🍱 오늘의 급식", new MealWidgetView(_neisService), 710, 30, 300, 520);
    }

    private void BtnPresetTools_Click(object sender, RoutedEventArgs e) => ApplyPresetTools();
    private void BtnPresetBoard_Click(object sender, RoutedEventArgs e) => ApplyPresetBoard();
    private void BtnPresetSplit_Click(object sender, RoutedEventArgs e) => ApplyPresetSplit();

    private void CbAddWidget_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!_isReady) return;
        if (CbAddWidget?.SelectedItem is ComboBoxItem item && item.Tag is string tag)
        {
            SpawnWidget(tag);
            CbAddWidget.SelectedIndex = 0; // reset
        }
    }

    #endregion

    #region Board Themes & Fullscreen

    private void BtnGreenBoard_Click(object sender, RoutedEventArgs e)
    {
        BoardContainer.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1B4332"));
        BoardInkCanvas.DefaultDrawingAttributes.Color = Colors.White;
    }

    private void BtnWhiteBoard_Click(object sender, RoutedEventArgs e)
    {
        BoardContainer.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F8F9FA"));
        BoardInkCanvas.DefaultDrawingAttributes.Color = (Color)ColorConverter.ConvertFromString("#0F172A");
    }

    private void BtnDarkBoard_Click(object sender, RoutedEventArgs e)
    {
        BoardContainer.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0F172A"));
        BoardInkCanvas.DefaultDrawingAttributes.Color = Colors.White;
    }

    private void BtnFullscreen_Click(object sender, RoutedEventArgs e)
    {
        if (WindowState == WindowState.Maximized)
        {
            WindowState = WindowState.Normal;
            WindowStyle = WindowStyle.SingleBorderWindow;
        }
        else
        {
            WindowStyle = WindowStyle.None;
            WindowState = WindowState.Maximized;
        }
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e)
    {
        SaveWidgetsLayout();
        Hide();
    }

    protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
    {
        SaveWidgetsLayout();
        e.Cancel = true;
        Hide();
    }

    #endregion

    #region Drawing Overlay

    private void ToggleInkMode_Checked(object sender, RoutedEventArgs e)
    {
        PanelInkTools.Visibility = Visibility.Visible;
        BoardInkCanvas.Visibility = Visibility.Visible;
        BoardInkCanvas.IsHitTestVisible = true;
    }

    private void ToggleInkMode_Unchecked(object sender, RoutedEventArgs e)
    {
        PanelInkTools.Visibility = Visibility.Collapsed;
        BoardInkCanvas.IsHitTestVisible = false;
    }

    private void RbPen_Checked(object sender, RoutedEventArgs e)
    {
        if (BoardInkCanvas == null) return;
        BoardInkCanvas.EditingMode = InkCanvasEditingMode.Ink;
    }

    private void RbEraser_Checked(object sender, RoutedEventArgs e)
    {
        if (BoardInkCanvas == null) return;
        BoardInkCanvas.EditingMode = InkCanvasEditingMode.EraseByStroke;
    }

    private void BtnColor_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string hex)
        {
            var color = (Color)ColorConverter.ConvertFromString(hex);
            BoardInkCanvas.DefaultDrawingAttributes.Color = color;
            if (RbEraser.IsChecked == true)
            {
                RbPen.IsChecked = true;
            }
        }
    }

    private void BtnUndo_Click(object sender, RoutedEventArgs e)
    {
        if (BoardInkCanvas.Strokes.Count > 0)
        {
            var last = BoardInkCanvas.Strokes[^1];
            _undoStack.Push(last);
            BoardInkCanvas.Strokes.Remove(last);
        }
    }

    private void BtnClear_Click(object sender, RoutedEventArgs e)
    {
        if (BoardInkCanvas.Strokes.Count > 0)
        {
            BoardInkCanvas.Strokes.Clear();
            _undoStack.Clear();
        }
    }

    #endregion

    #region Lock & Opacity Controls

    private void ToggleLockWidgets_Checked(object sender, RoutedEventArgs e)
    {
        _isWidgetsLocked = true;
        ApplyLockState();
    }

    private void ToggleLockWidgets_Unchecked(object sender, RoutedEventArgs e)
    {
        _isWidgetsLocked = false;
        ApplyLockState();
    }

    private void ApplyLockState()
    {
        if (ToggleLockWidgets != null)
        {
            ToggleLockWidgets.Content = _isWidgetsLocked ? "🔒 위치 잠김" : "🔓 위치 고정";
            ToggleLockWidgets.Background = _isWidgetsLocked
                ? new SolidColorBrush((Color)ColorConverter.ConvertFromString("#EF4444"))
                : new SolidColorBrush((Color)ColorConverter.ConvertFromString("#334155"));
        }

        foreach (var w in _widgets)
        {
            w.IsLocked = _isWidgetsLocked;
        }
    }

    private void BtnOpacityPopup_Click(object sender, RoutedEventArgs e)
    {
        PopupOpacity.IsOpen = !PopupOpacity.IsOpen;
    }

    private void SliderCardOpacity_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        _currentCardOpacity = e.NewValue;
        if (TxtOpacityValue != null)
        {
            TxtOpacityValue.Text = $"{(_currentCardOpacity * 100):0}%";
        }
        foreach (var w in _widgets)
        {
            w.CardOpacity = _currentCardOpacity;
        }
    }

    #endregion
}
