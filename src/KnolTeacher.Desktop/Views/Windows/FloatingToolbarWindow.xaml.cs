using System;
using System.Windows;
using System.Windows.Input;
using System.Windows.Threading;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class FloatingToolbarWindow : Window
{
    private readonly StudentDisplayWindow _studentBoard;
    private readonly ScreenDrawingOverlayWindow _screenDrawing;
    private readonly ClassroomTimerWindow _timerWindow;
    private readonly VisualizerWindow _visualizerWindow;
    private readonly StudentPickerWindow _pickerWindow;
    private readonly IQrCodeService _qrCodeService;
    private readonly IDesktopCleanerService _cleanerService;
    private readonly DigitalSignatureWindow _signatureWindow;
    private readonly NoiseTrafficLightWindow _noiseWindow;
    private readonly ClassroomSoundboardWindow _soundboardWindow;
    private readonly SmartSeatShuffleWindow _seatWindow;
    private readonly IDisplayManager? _displayManager;
    private readonly DispatcherTimer _activeTimer;
    private bool _isExpanded = false;

    public FloatingToolbarWindow(
        StudentDisplayWindow studentBoard,
        ScreenDrawingOverlayWindow screenDrawing,
        ClassroomTimerWindow timerWindow,
        VisualizerWindow visualizerWindow,
        StudentPickerWindow pickerWindow,
        IQrCodeService qrCodeService,
        IDesktopCleanerService cleanerService,
        DigitalSignatureWindow signatureWindow,
        NoiseTrafficLightWindow noiseWindow,
        ClassroomSoundboardWindow soundboardWindow,
        SmartSeatShuffleWindow seatWindow,
        IDisplayManager? displayManager = null)
    {
        _studentBoard = studentBoard;
        _screenDrawing = screenDrawing;
        _timerWindow = timerWindow;
        _visualizerWindow = visualizerWindow;
        _pickerWindow = pickerWindow;
        _qrCodeService = qrCodeService;
        _cleanerService = cleanerService;
        _signatureWindow = signatureWindow;
        _noiseWindow = noiseWindow;
        _soundboardWindow = soundboardWindow;
        _seatWindow = seatWindow;
        _displayManager = displayManager;

        InitializeComponent();

        _activeTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromMilliseconds(500)
        };
        _activeTimer.Tick += (s, e) => UpdateActiveToolIndicators();

        Loaded += (s, e) =>
        {
            PositionAtTopCenter();
            _activeTimer.Start();
            UpdateActiveToolIndicators();
        };

        IsVisibleChanged += (s, e) =>
        {
            if (IsVisible)
            {
                _activeTimer.Start();
                UpdateActiveToolIndicators();
            }
            else
            {
                _activeTimer.Stop();
            }
        };
    }

    public void PositionAtTopCenter()
    {
        UpdateLayout();
        double screenWidth = SystemParameters.PrimaryScreenWidth;
        double w = ActualWidth > 0 ? ActualWidth : 560;
        Left = Math.Max(20, (screenWidth - w) / 2);
        Top = 16;
    }

    private void EnsureWindowWithinScreen()
    {
        UpdateLayout();
        double screenW = SystemParameters.PrimaryScreenWidth;
        double screenH = SystemParameters.PrimaryScreenHeight;
        if (Left + ActualWidth > screenW) Left = Math.Max(10, screenW - ActualWidth - 10);
        if (Left < 0) Left = 10;
        if (Top < 0) Top = 10;
        if (Top + ActualHeight > screenH) Top = Math.Max(10, screenH - ActualHeight - 10);
    }

    private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ButtonState == MouseButtonState.Pressed)
        {
            DragMove();
        }
    }

    private void UpdateActiveToolIndicators()
    {
        if (!IsVisible) return;

        DotBoard.Visibility = _studentBoard.IsVisible ? Visibility.Visible : Visibility.Collapsed;
        DotDrawScreen.Visibility = (_screenDrawing.IsVisible && !_screenDrawing.IsBoardMode) ? Visibility.Visible : Visibility.Collapsed;
        DotDrawBoard.Visibility = (_screenDrawing.IsVisible && _screenDrawing.IsBoardMode) ? Visibility.Visible : Visibility.Collapsed;
        DotTimer.Visibility = _timerWindow.IsVisible ? Visibility.Visible : Visibility.Collapsed;
        DotPicker.Visibility = _pickerWindow.IsVisible ? Visibility.Visible : Visibility.Collapsed;

        DotVisualizer.Visibility = _visualizerWindow.IsVisible ? Visibility.Visible : Visibility.Collapsed;
        DotNoise.Visibility = _noiseWindow.IsVisible ? Visibility.Visible : Visibility.Collapsed;
        DotSoundboard.Visibility = _soundboardWindow.IsVisible ? Visibility.Visible : Visibility.Collapsed;
        DotSeat.Visibility = _seatWindow.IsVisible ? Visibility.Visible : Visibility.Collapsed;
        DotSignature.Visibility = _signatureWindow.IsVisible ? Visibility.Visible : Visibility.Collapsed;

        if (_displayManager != null && _displayManager.IsDualMonitor)
        {
            BtnSwitchMonitor.ToolTip = "학생 화면(놀보드) 모니터 1 ↔ 2 전환 (듀얼 모니터 감지됨)";
        }
        else
        {
            BtnSwitchMonitor.ToolTip = "단일 모니터 환경 (듀얼 모니터 연결 시 1↔2 전환 지원)";
        }
    }

    private void BtnBoard_Click(object sender, RoutedEventArgs e)
    {
        if (_studentBoard.IsVisible)
        {
            _studentBoard.Hide();
        }
        else
        {
            _displayManager?.MoveToStudentMonitor(_studentBoard, maximize: true);
            _studentBoard.Show();
            _studentBoard.Activate();
        }
        UpdateActiveToolIndicators();
    }

    private void BtnDrawScreen_Click(object sender, RoutedEventArgs e)
    {
        if (_screenDrawing.IsVisible && !_screenDrawing.IsBoardMode)
        {
            _screenDrawing.CloseOverlay();
        }
        else
        {
            _screenDrawing.FreezeAndShow();
        }
        UpdateActiveToolIndicators();
    }

    private void BtnDrawBoard_Click(object sender, RoutedEventArgs e)
    {
        if (_screenDrawing.IsVisible && _screenDrawing.IsBoardMode)
        {
            _screenDrawing.CloseOverlay();
        }
        else
        {
            _screenDrawing.ShowBoardMode("chalkboard");
        }
        UpdateActiveToolIndicators();
    }

    private void BtnTimer_Click(object sender, RoutedEventArgs e)
    {
        if (_timerWindow.IsVisible) _timerWindow.Hide();
        else
        {
            _timerWindow.PositionToDefaultMonitor();
            _timerWindow.Show();
            _timerWindow.Activate();
        }
        UpdateActiveToolIndicators();
    }

    private void BtnPicker_Click(object sender, RoutedEventArgs e)
    {
        if (_pickerWindow.IsVisible) _pickerWindow.Hide();
        else
        {
            _displayManager?.MoveToStudentMonitor(_pickerWindow, maximize: false);
            _pickerWindow.Show();
            _pickerWindow.Activate();
        }
        UpdateActiveToolIndicators();
    }

    private void BtnNotice_Click(object sender, RoutedEventArgs e)
    {
        if (!_studentBoard.IsVisible)
        {
            _displayManager?.MoveToStudentMonitor(_studentBoard, maximize: true);
            _studentBoard.Show();
            _studentBoard.Activate();
        }

        var memoHost = _studentBoard.FindWidget("memo");
        if (memoHost != null)
        {
            memoHost.Visibility = Visibility.Visible;
        }

        HudNotificationWindow.Instance.ShowToast("📢 알림장", "학생 화면(놀보드)에 알림장을 표시합니다.");
        UpdateActiveToolIndicators();
    }

    private void BtnSwitchMonitor_Click(object sender, RoutedEventArgs e)
    {
        if (_displayManager == null || !_displayManager.IsDualMonitor)
        {
            HudNotificationWindow.Instance.ShowToast("💻 단일 모니터", "현재 단일 모니터 환경입니다.\n듀얼 모니터(학생 화면) 연결 시 자동 지원됩니다.");
            return;
        }

        if (!_studentBoard.IsVisible)
        {
            _displayManager.MoveToStudentMonitor(_studentBoard, maximize: true);
            _studentBoard.Show();
            _studentBoard.Activate();
            HudNotificationWindow.Instance.ShowToast("📺 놀보드 표시", "학생용 모니터에 놀보드를 열었습니다.");
        }
        else
        {
            _studentBoard.ToggleMonitor();
            HudNotificationWindow.Instance.ShowToast("📺 화면 전환", "놀보드 표시 모니터를 전환했습니다.");
        }
        UpdateActiveToolIndicators();
    }

    private void BtnToggleExpand_Click(object sender, RoutedEventArgs e)
    {
        _isExpanded = !_isExpanded;
        SecondaryToolsPanel.Visibility = _isExpanded ? Visibility.Visible : Visibility.Collapsed;
        TxtExpandIcon.Text = _isExpanded ? "▲" : "▼";
        BtnToggleExpand.ToolTip = _isExpanded ? "보조 교실 도구 접기 (콤팩트 모드)" : "보조 교실 도구 더보기 (화상기, 소음, 효과음 등)";
        EnsureWindowWithinScreen();
    }

    private void BtnVisualizer_Click(object sender, RoutedEventArgs e)
    {
        if (_visualizerWindow.IsVisible) _visualizerWindow.Hide();
        else
        {
            _displayManager?.MoveToStudentMonitor(_visualizerWindow, maximize: false);
            _visualizerWindow.Show();
            _visualizerWindow.Activate();
        }
        UpdateActiveToolIndicators();
    }

    private void BtnNoise_Click(object sender, RoutedEventArgs e)
    {
        if (_noiseWindow.IsVisible) _noiseWindow.Hide();
        else
        {
            _noiseWindow.Show();
            _noiseWindow.Activate();
        }
        UpdateActiveToolIndicators();
    }

    private void BtnSoundboard_Click(object sender, RoutedEventArgs e)
    {
        if (_soundboardWindow.IsVisible) _soundboardWindow.Hide();
        else
        {
            _soundboardWindow.Show();
            _soundboardWindow.Activate();
        }
        UpdateActiveToolIndicators();
    }

    private void BtnSignature_Click(object sender, RoutedEventArgs e)
    {
        if (_signatureWindow.IsVisible) _signatureWindow.Hide();
        else
        {
            _signatureWindow.Show();
            _signatureWindow.Activate();
        }
        UpdateActiveToolIndicators();
    }

    private void BtnSeat_Click(object sender, RoutedEventArgs e)
    {
        if (_seatWindow.IsVisible) _seatWindow.Hide();
        else
        {
            _seatWindow.Show();
            _seatWindow.Activate();
        }
        UpdateActiveToolIndicators();
    }

    private void BtnQr_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new QrCodeModalDialog(_qrCodeService, "📱 QR코드 생성기", "https://pinky-ne.com");
        dlg.Show();
    }

    private void BtnZen_Click(object sender, RoutedEventArgs e)
    {
        var (_, _, msg) = _cleanerService.ToggleDesktopIcons();
        MessageBox.Show(msg, "젠 클리너", MessageBoxButton.OK, MessageBoxImage.Information);
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
}
