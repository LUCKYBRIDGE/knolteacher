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
    private readonly YouTubePlayerWindow _youtubePlayerWindow;
    private readonly IDesktopCleanerService _cleanerService;

    public FloatingToolbarWindow(
        StudentDisplayWindow studentBoard,
        ScreenDrawingOverlayWindow screenDrawing,
        ClassroomTimerWindow timerWindow,
        VisualizerWindow visualizerWindow,
        StudentPickerWindow pickerWindow,
        YouTubePlayerWindow youtubePlayerWindow,
        IDesktopCleanerService cleanerService)
    {
        _studentBoard = studentBoard;
        _screenDrawing = screenDrawing;
        _timerWindow = timerWindow;
        _visualizerWindow = visualizerWindow;
        _pickerWindow = pickerWindow;
        _youtubePlayerWindow = youtubePlayerWindow;
        _cleanerService = cleanerService;

        InitializeComponent();
        Loaded += (s, e) => PositionAtTopCenter();
    }

    public void PositionAtTopCenter()
    {
        UpdateLayout();
        double screenWidth = SystemParameters.PrimaryScreenWidth;
        double w = ActualWidth > 0 ? ActualWidth : 580;
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
        else _studentBoard.Show();
    }

    private void BtnDraw_Click(object sender, RoutedEventArgs e)
    {
        if (_screenDrawing.IsVisible) _screenDrawing.CloseOverlay();
        else _screenDrawing.FreezeAndShow();
    }

    private void BtnTimer_Click(object sender, RoutedEventArgs e)
    {
        if (_timerWindow.IsVisible) _timerWindow.Hide();
        else _timerWindow.Show();
    }

    private void BtnVisualizer_Click(object sender, RoutedEventArgs e)
    {
        if (_visualizerWindow.IsVisible) _visualizerWindow.Hide();
        else _visualizerWindow.Show();
    }

    private void BtnPicker_Click(object sender, RoutedEventArgs e)
    {
        if (_pickerWindow.IsVisible) _pickerWindow.Hide();
        else _pickerWindow.Show();
    }

    private void BtnYouTube_Click(object sender, RoutedEventArgs e)
    {
        if (_youtubePlayerWindow.IsVisible) _youtubePlayerWindow.Hide();
        else { _youtubePlayerWindow.Show(); _youtubePlayerWindow.Activate(); }
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
