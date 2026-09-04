using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Ink;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
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

    private readonly Stack<Stroke> _undoStack = new();
    private readonly DispatcherTimer _clockTimer;
    private readonly List<BoardWidgetHost> _widgets = new();

    public StudentDisplayWindow(
        ISoundService soundService,
        IStudentManagerService studentService,
        ITimetableService timetableService,
        INeisService neisService,
        IConfigService configService,
        IQrCodeService qrCodeService)
    {
        _soundService = soundService;
        _studentService = studentService;
        _timetableService = timetableService;
        _neisService = neisService;
        _configService = configService;
        _qrCodeService = qrCodeService;

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

        _isReady = true;
        Loaded += (s, e) => ApplyPresetTools();
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
            Height = h
        };

        Canvas.SetLeft(host, x);
        Canvas.SetTop(host, y);

        host.Closed += (target) =>
        {
            WidgetCanvas.Children.Remove(target);
            _widgets.Remove(target);
            UpdateDockButtonsState();
        };

        _widgets.Add(host);
        WidgetCanvas.Children.Add(host);
        UpdateDockButtonsState();
        return host;
    }

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
        if (_pinballWindow == null)
        {
            _pinballWindow = new StudentPickerWindow(_studentService, _soundService);
        }
        _pinballWindow.Show();
        _pinballWindow.Activate();
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
            "wheel" => AddWidget("wheel", "🎡 돌려돌려 돌림판", new WheelWidgetView(_soundService), nextX, nextY, 340, 270),
            "score" => AddWidget("score", "🏆 모둠 점수판", new ScoreWidgetView(), nextX, nextY, 360, 270),
            "drawing" => AddWidget("drawing", "✏️ 칠판 판서장", new DrawingWidgetView(), nextX, nextY, 400, 310),
            "timetable" => AddWidget("timetable", "📅 오늘의 시간표", new TimetableWidgetView(_timetableService), nextX, nextY, 320, 440),
            "meal" => AddWidget("meal", "🍱 오늘의 급식", new MealWidgetView(_neisService), nextX, nextY, 320, 440),
            "memo" => AddWidget("memo", "📝 학급 알림장", new MemoWidgetView(_configService), nextX, nextY, 360, 340),
            "qr" => AddWidget("qr", "📱 실시간 수업 QR코드", new QrWidgetView(_qrCodeService), nextX, nextY, 320, 360),
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
        UpdateBtnState(BtnToolQr, "qr");
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
            btn.FontWeight = FontWeights.Normal;
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
            double ww = Math.Min(680, canvasWidth - 40);
            double wh = Math.Min(480, canvasHeight - 40);
            Canvas.SetLeft(w, Math.Max(20, (canvasWidth - ww) / 2));
            Canvas.SetTop(w, Math.Max(20, (canvasHeight - wh) / 2));
            w.Width = ww;
            w.Height = wh;
        }
        else if (n == 2)
        {
            double halfW = (canvasWidth - 30) / 2;
            double h = Math.Max(300, canvasHeight - 40);
            for (int i = 0; i < 2; i++)
            {
                var w = _widgets[i];
                Canvas.SetLeft(w, 10 + i * (halfW + 10));
                Canvas.SetTop(w, 20);
                w.Width = halfW;
                w.Height = h;
            }
        }
        else if (n <= 4)
        {
            double halfW = (canvasWidth - 30) / 2;
            double halfH = (canvasHeight - 30) / 2;
            for (int i = 0; i < n; i++)
            {
                int r = i / 2;
                int c = i % 2;
                var w = _widgets[i];
                Canvas.SetLeft(w, 10 + c * (halfW + 10));
                Canvas.SetTop(w, 10 + r * (halfH + 10));
                w.Width = halfW;
                w.Height = halfH;
            }
        }
        else
        {
            int cols = 3;
            int rows = (n + cols - 1) / cols;
            double cw = (canvasWidth - (cols + 1) * 10) / cols;
            double ch = (canvasHeight - (rows + 1) * 10) / rows;
            for (int i = 0; i < n; i++)
            {
                int r = i / cols;
                int c = i % cols;
                var w = _widgets[i];
                Canvas.SetLeft(w, 10 + c * (cw + 10));
                Canvas.SetTop(w, 10 + r * (ch + 10));
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
        AddWidget("memo", "📝 학급 알림장", new MemoWidgetView(_configService), 750, 30, 380, 480);
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
        Hide();
    }

    protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
    {
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
}
