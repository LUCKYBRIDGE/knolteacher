using System;
using System.Collections.Generic;
using System.Diagnostics;
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
    private bool _isReady = false;
    private int _layoutSaveSuppressionDepth = 0;

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

    #region Widget Management & Presets

    private bool IsLayoutSaveSuppressed => _layoutSaveSuppressionDepth > 0;

    private void BeginLayoutBatch()
    {
        _layoutSaveSuppressionDepth++;
    }

    private void EndLayoutBatch(bool saveFinalState)
    {
        if (_layoutSaveSuppressionDepth > 0)
        {
            _layoutSaveSuppressionDepth--;
        }

        if (saveFinalState && _layoutSaveSuppressionDepth == 0)
        {
            SaveWidgetsLayout();
        }
    }

    public void ClearWidgets(bool saveLayout = true)
    {
        foreach (var widget in _widgets.ToArray())
        {
            widget.DisposeContent();
            WidgetCanvas.Children.Remove(widget);
        }

        _widgets.Clear();
        UpdateDockButtonsState();

        if (saveLayout)
        {
            SaveWidgetsLayout();
        }
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

        host.Closed += target =>
        {
            WidgetCanvas.Children.Remove(target);
            _widgets.Remove(target);
            UpdateDockButtonsState();
            SaveWidgetsLayout();
        };

        host.MovedOrResized += _ => SaveWidgetsLayout();

        _widgets.Add(host);
        WidgetCanvas.Children.Add(host);
        UpdateDockButtonsState();
        SaveWidgetsLayout();
        return host;
    }

    public void SaveWidgetsLayout()
    {
        if (!_isReady || IsLayoutSaveSuppressed) return;

        try
        {
            var list = new List<NolboardWidgetState>();
            foreach (var widget in _widgets)
            {
                double x = Canvas.GetLeft(widget);
                double y = Canvas.GetTop(widget);
                if (double.IsNaN(x) || double.IsInfinity(x)) x = 0;
                if (double.IsNaN(y) || double.IsInfinity(y)) y = 0;

                double width = widget.ActualWidth > 0
                    ? widget.ActualWidth
                    : (double.IsNaN(widget.Width) ? 340 : widget.Width);
                double height = widget.ActualHeight > 0
                    ? widget.ActualHeight
                    : (double.IsNaN(widget.Height) ? 260 : widget.Height);

                list.Add(new NolboardWidgetState
                {
                    Tag = widget.WidgetType,
                    X = x,
                    Y = y,
                    Width = width,
                    Height = height
                });
            }

            var layout = _configService.NolboardLayout ?? new NolboardLayoutConfig();
            layout.SchemaVersion = NolboardLayoutConfig.CurrentSchemaVersion;
            layout.Widgets = list;
            layout.HasCustomLayout = true;
            layout.CanvasWidth = WidgetCanvas.ActualWidth > 0 ? WidgetCanvas.ActualWidth : 0;
            layout.CanvasHeight = WidgetCanvas.ActualHeight > 0 ? WidgetCanvas.ActualHeight : 0;
            _configService.NolboardLayout = layout;
            _configService.SaveNolboardLayout();
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[Nolboard] Failed to save layout: {ex.GetType().Name}");
        }
    }

    public bool RestoreWidgetsLayout()
    {
        var layout = _configService.NolboardLayout;
        if (layout == null || !layout.HasCustomLayout)
        {
            return false;
        }

        BeginLayoutBatch();
        try
        {
            ClearWidgets(saveLayout: false);

            // An intentionally empty custom workspace must remain empty on next launch.
            if (layout.Widgets == null || layout.Widgets.Count == 0)
            {
                return true;
            }

            double currentCanvasWidth = WidgetCanvas.ActualWidth;
            double currentCanvasHeight = WidgetCanvas.ActualHeight;
            double scaleX = 1.0;
            double scaleY = 1.0;

            if (layout.CanvasWidth > 200 && layout.CanvasHeight > 200 &&
                currentCanvasWidth > 200 && currentCanvasHeight > 200)
            {
                scaleX = currentCanvasWidth / layout.CanvasWidth;
                scaleY = currentCanvasHeight / layout.CanvasHeight;
            }

            foreach (var state in layout.Widgets)
            {
                if (string.IsNullOrWhiteSpace(state.Tag)) continue;

                var host = SpawnWidget(state.Tag, state.X * scaleX, state.Y * scaleY);
                if (host == null) continue;

                if (state.Width > 100)
                {
                    host.Width = Math.Max(host.MinWidth, state.Width * scaleX);
                }

                if (state.Height > 80)
                {
                    host.Height = Math.Max(host.MinHeight, state.Height * scaleY);
                }
            }

            layout.SchemaVersion = NolboardLayoutConfig.CurrentSchemaVersion;
            ClampAllWidgetsWithinCanvas();
            UpdateDockButtonsState();
            return true;
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"[Nolboard] Failed to restore layout: {ex.GetType().Name}");
            return false;
        }
        finally
        {
            EndLayoutBatch(saveFinalState: false);
        }
    }

    private void BtnSaveBoardLayout_Click(object sender, RoutedEventArgs e)
    {
        SaveWidgetsLayout();
        MessageBox.Show("현재 놀보드 위젯 배치가 안전하게 저장되었습니다.\n다음에 놀보드를 열 때 이 상태로 자동 복원됩니다.", "놀보드 배치 저장 완료", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    public BoardWidgetHost? FindWidget(string type) =>
        _widgets.Find(w => string.Equals(w.WidgetType, type, StringComparison.OrdinalIgnoreCase));

    public void ToggleWidget(string key)
    {
        if (key == "pinball")
        {
            OpenPinballWindow();
            return;
        }

        var existing = FindWidget(key);
        if (existing != null)
        {
            existing.DisposeContent();
            WidgetCanvas.Children.Remove(existing);
            _widgets.Remove(existing);
            UpdateDockButtonsState();
            SaveWidgetsLayout();
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

        var definition = WidgetRegistry.GetOrDefault(tag);
        if (definition == null)
        {
            return null;
        }

        if (!definition.AllowMultiple)
        {
            var existing = FindWidget(tag);
            if (existing != null)
            {
                existing.BringToFront();
                return existing;
            }
        }

        double nextX = x ?? (40 + (_widgets.Count * 30) % 360);
        double nextY = y ?? (40 + (_widgets.Count * 30) % 240);

        UserControl? view = tag switch
        {
            "timer" => new TimerWidgetView(_soundService),
            "picker" => new PickerWidgetView(_studentService, _soundService),
            "dice" => new DiceWidgetView(_soundService),
            "wheel" => new WheelWidgetView(_soundService),
            "score" => new ScoreWidgetView(),
            "drawing" => new DrawingWidgetView(),
            "timetable" => new TimetableWidgetView(_timetableService),
            "meal" => new MealWidgetView(_neisService),
            "memo" => new MemoWidgetView(_configService, _ttsService),
            "checklist" => new ChecklistWidgetView(_configService, _studentService),
            "qr" => new QrWidgetView(_qrCodeService),
            "weather" => new WeatherWidgetView(_weatherService),
            "dday" => new DDayWidgetView(_configService),
            _ => null
        };

        return view == null
            ? null
            : AddWidget(definition.Type, definition.Title, view, nextX, nextY, definition.DefaultWidth, definition.DefaultHeight);
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
        bool active = _widgets.Exists(w => string.Equals(w.WidgetType, tag, StringComparison.OrdinalIgnoreCase));
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

    private void OnWidgetCanvasSizeChanged(object sender, SizeChangedEventArgs e)
    {
        double newWidth = e.NewSize.Width;
        double newHeight = e.NewSize.Height;
        double oldWidth = e.PreviousSize.Width;
        double oldHeight = e.PreviousSize.Height;

        if (oldWidth > 200 && oldHeight > 200 && newWidth > 200 && newHeight > 200)
        {
            double scaleX = newWidth / oldWidth;
            double scaleY = newHeight / oldHeight;

            if (Math.Abs(scaleX - 1.0) > 0.01 || Math.Abs(scaleY - 1.0) > 0.01)
            {
                foreach (var widget in _widgets)
                {
                    double curLeft = Canvas.GetLeft(widget);
                    double curTop = Canvas.GetTop(widget);
                    if (double.IsNaN(curLeft)) curLeft = 20;
                    if (double.IsNaN(curTop)) curTop = 20;

                    double curW = widget.ActualWidth > 0 ? widget.ActualWidth : (double.IsNaN(widget.Width) ? 400 : widget.Width);
                    double curH = widget.ActualHeight > 0 ? widget.ActualHeight : (double.IsNaN(widget.Height) ? 300 : widget.Height);

                    double nextW = Math.Max(widget.MinWidth, curW * scaleX);
                    double nextH = Math.Max(widget.MinHeight, curH * scaleY);
                    double nextLeft = curLeft * scaleX;
                    double nextTop = curTop * scaleY;

                    if (nextW > newWidth - 20) nextW = Math.Max(widget.MinWidth, newWidth - 20);
                    if (nextH > newHeight - 20) nextH = Math.Max(widget.MinHeight, newHeight - 20);

                    double maxLeft = Math.Max(10, newWidth - nextW - 10);
                    double maxTop = Math.Max(10, newHeight - nextH - 10);

                    widget.Width = nextW;
                    widget.Height = nextH;
                    Canvas.SetLeft(widget, Math.Clamp(nextLeft, 10, maxLeft));
                    Canvas.SetTop(widget, Math.Clamp(nextTop, 10, maxTop));
                }
            }
        }

        ClampAllWidgetsWithinCanvas();
    }

    public void ClampAllWidgetsWithinCanvas()
    {
        double canvasWidth = WidgetCanvas.ActualWidth;
        double canvasHeight = WidgetCanvas.ActualHeight;
        if (canvasWidth <= 100 || canvasHeight <= 100) return;

        foreach (var widget in _widgets)
        {
            double curLeft = Canvas.GetLeft(widget);
            double curTop = Canvas.GetTop(widget);
            if (double.IsNaN(curLeft)) curLeft = 20;
            if (double.IsNaN(curTop)) curTop = 20;

            double actualWidth = widget.ActualWidth > 0 ? widget.ActualWidth : widget.Width;
            double actualHeight = widget.ActualHeight > 0 ? widget.ActualHeight : widget.Height;
            if (double.IsNaN(actualWidth) || actualWidth <= 0) actualWidth = widget.MinWidth;
            if (double.IsNaN(actualHeight) || actualHeight <= 0) actualHeight = widget.MinHeight;

            if (actualWidth > canvasWidth - 20)
            {
                widget.Width = Math.Max(widget.MinWidth, canvasWidth - 20);
                actualWidth = widget.Width;
            }

            if (actualHeight > canvasHeight - 20)
            {
                widget.Height = Math.Max(widget.MinHeight, canvasHeight - 20);
                actualHeight = widget.Height;
            }

            double maxLeft = Math.Max(10, canvasWidth - actualWidth - 10);
            double maxTop = Math.Max(10, canvasHeight - actualHeight - 10);
            Canvas.SetLeft(widget, Math.Clamp(curLeft, 10, maxLeft));
            Canvas.SetTop(widget, Math.Clamp(curTop, 10, maxTop));
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
            var widget = _widgets[0];
            double ww = Math.Max(widget.MinWidth, Math.Min(780, canvasWidth - 40));
            double wh = Math.Max(widget.MinHeight, Math.Min(520, canvasHeight - 40));
            Canvas.SetLeft(widget, Math.Max(20, (canvasWidth - ww) / 2));
            Canvas.SetTop(widget, Math.Max(20, (canvasHeight - wh) / 2));
            widget.Width = ww;
            widget.Height = wh;
        }
        else if (n == 2)
        {
            double halfW = (canvasWidth - 36) / 2;
            double h = Math.Max(300, canvasHeight - 40);
            for (int i = 0; i < 2; i++)
            {
                var widget = _widgets[i];
                Canvas.SetLeft(widget, 12 + i * (halfW + 12));
                Canvas.SetTop(widget, 16);
                widget.Width = Math.Max(widget.MinWidth, halfW);
                widget.Height = Math.Max(widget.MinHeight, h);
            }
        }
        else if (n == 3)
        {
            double colW = (canvasWidth - 48) / 3;
            double h = Math.Max(300, canvasHeight - 36);
            for (int i = 0; i < 3; i++)
            {
                var widget = _widgets[i];
                Canvas.SetLeft(widget, 12 + i * (colW + 12));
                Canvas.SetTop(widget, 16);
                widget.Width = Math.Max(widget.MinWidth, colW);
                widget.Height = Math.Max(widget.MinHeight, h);
            }
        }
        else if (n == 4)
        {
            double halfW = (canvasWidth - 36) / 2;
            double halfH = (canvasHeight - 36) / 2;
            for (int i = 0; i < 4; i++)
            {
                int row = i / 2;
                int col = i % 2;
                var widget = _widgets[i];
                Canvas.SetLeft(widget, 12 + col * (halfW + 12));
                Canvas.SetTop(widget, 12 + row * (halfH + 12));
                widget.Width = Math.Max(widget.MinWidth, halfW);
                widget.Height = Math.Max(widget.MinHeight, halfH);
            }
        }
        else
        {
            int cols = n <= 6 ? 3 : 4;
            int rows = (n + cols - 1) / cols;
            double cellWidth = (canvasWidth - (cols + 1) * 12) / cols;
            double cellHeight = (canvasHeight - (rows + 1) * 12) / rows;
            for (int i = 0; i < n; i++)
            {
                int row = i / cols;
                int col = i % cols;
                var widget = _widgets[i];
                Canvas.SetLeft(widget, 12 + col * (cellWidth + 12));
                Canvas.SetTop(widget, 12 + row * (cellHeight + 12));
                widget.Width = Math.Max(widget.MinWidth, cellWidth);
                widget.Height = Math.Max(widget.MinHeight, cellHeight);
            }
        }

        ClampAllWidgetsWithinCanvas();
        SaveWidgetsLayout();
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
        BeginLayoutBatch();
        try
        {
            ClearWidgets(saveLayout: false);
            AddWidget("timer", "⏱️ 수업 타이머", new TimerWidgetView(_soundService), 30, 30, 340, 240);
            AddWidget("picker", "🎯 발표자 추첨", new PickerWidgetView(_studentService, _soundService), 400, 30, 360, 280);
            AddWidget("dice", "🎲 스마트 주사위 & 통계", new DiceWidgetView(_soundService), 30, 300, 480, 290);
        }
        finally
        {
            EndLayoutBatch(saveFinalState: true);
        }
    }

    private void ApplyPresetBoard()
    {
        BeginLayoutBatch();
        try
        {
            ClearWidgets(saveLayout: false);
            AddWidget("timetable", "📅 오늘의 시간표", new TimetableWidgetView(_timetableService), 30, 30, 330, 480);
            AddWidget("meal", "🍱 오늘의 급식", new MealWidgetView(_neisService), 390, 30, 330, 480);
            AddWidget("memo", "📝 학급 알림장", new MemoWidgetView(_configService, _ttsService), 750, 30, 380, 480);
        }
        finally
        {
            EndLayoutBatch(saveFinalState: true);
        }
    }

    private void ApplyPresetSplit()
    {
        BeginLayoutBatch();
        try
        {
            ClearWidgets(saveLayout: false);
            AddWidget("timer", "⏱️ 수업 타이머", new TimerWidgetView(_soundService), 30, 30, 320, 240);
            AddWidget("picker", "🎯 발표자 추첨", new PickerWidgetView(_studentService, _soundService), 30, 290, 320, 260);
            AddWidget("timetable", "📅 오늘의 시간표", new TimetableWidgetView(_timetableService), 380, 30, 300, 520);
            AddWidget("meal", "🍱 오늘의 급식", new MealWidgetView(_neisService), 710, 30, 300, 520);
        }
        finally
        {
            EndLayoutBatch(saveFinalState: true);
        }
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
            CbAddWidget.SelectedIndex = 0;
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

        foreach (var widget in _widgets)
        {
            widget.IsLocked = _isWidgetsLocked;
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

        foreach (var widget in _widgets)
        {
            widget.CardOpacity = _currentCardOpacity;
        }
    }

    #endregion
}
