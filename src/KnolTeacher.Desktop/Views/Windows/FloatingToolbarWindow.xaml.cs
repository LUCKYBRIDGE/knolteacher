using System.Windows;
using System.Windows.Input;
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
        Loaded += (s, e) => PositionAtTopCenter();
    }

    public void PositionAtTopCenter()
    {
        UpdateLayout();
        double screenWidth = SystemParameters.PrimaryScreenWidth;
        double w = ActualWidth > 0 ? ActualWidth : 760;
        Left = Math.Max(20, (screenWidth - w) / 2);
        Top = 16;
    }

    private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ButtonState == MouseButtonState.Pressed)
        {
            DragMove();
        }
    }

    private void BtnBoard_Click(object sender, RoutedEventArgs e)
    {
        if (_studentBoard.IsVisible) _studentBoard.Hide();
        else
        {
            _displayManager?.MoveToStudentMonitor(_studentBoard, maximize: true);
            _studentBoard.Show();
            _studentBoard.Activate();
        }
    }

    private void BtnDraw_Click(object sender, RoutedEventArgs e)
    {
        if (_screenDrawing.IsVisible) _screenDrawing.CloseOverlay();
        else _screenDrawing.FreezeAndShow();
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
    }

    private void BtnNoise_Click(object sender, RoutedEventArgs e)
    {
        if (_noiseWindow.IsVisible) _noiseWindow.Hide();
        else
        {
            _noiseWindow.Show();
            _noiseWindow.Activate();
        }
    }

    private void BtnSoundboard_Click(object sender, RoutedEventArgs e)
    {
        if (_soundboardWindow.IsVisible) _soundboardWindow.Hide();
        else
        {
            _soundboardWindow.Show();
            _soundboardWindow.Activate();
        }
    }

    private void BtnSignature_Click(object sender, RoutedEventArgs e)
    {
        if (_signatureWindow.IsVisible) _signatureWindow.Hide();
        else
        {
            _signatureWindow.Show();
            _signatureWindow.Activate();
        }
    }

    private void BtnSeat_Click(object sender, RoutedEventArgs e)
    {
        if (_seatWindow.IsVisible) _seatWindow.Hide();
        else
        {
            _seatWindow.Show();
            _seatWindow.Activate();
        }
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
