using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Ink;
using System.Windows.Input;
using System.Windows.Media.Imaging;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.Views.Controls;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class ScreenDrawingOverlayWindow : Window
{
    private readonly IConfigService? _configService;

    public ScreenDrawingOverlayWindow(IConfigService? configService = null)
    {
        _configService = configService;
        InitializeComponent();

        OverlayInkCanvas.DefaultDrawingAttributes = new DrawingAttributes
        {
            Color = (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#EF4444"),
            Width = 4,
            Height = 4,
            FitToCurve = true,
            IgnorePressure = false
        };

        // Disable Windows Touch Stylus Press-and-Hold circle lag
        Stylus.SetIsPressAndHoldEnabled(OverlayInkCanvas, false);
        Stylus.SetIsFlicksEnabled(OverlayInkCanvas, false);

        // ESC key to close
        PreviewKeyDown += (s, e) =>
        {
            if (e.Key == Key.Escape)
            {
                CloseOverlay();
                e.Handled = true;
            }
        };
    }

    public bool IsBoardMode { get; private set; }

    public void FreezeAndShow()
    {
        try
        {
            IsBoardMode = false;
            if (TxtStudioTitle != null) TxtStudioTitle.Text = "🖼️ 화면 주석 판서 (Alt+2)";

            // 1. Get current monitor under mouse cursor
            var rect = NativeMethods.GetCurrentMonitorRect();
            int left = rect.Left;
            int top = rect.Top;
            int width = rect.Right - rect.Left;
            int height = rect.Bottom - rect.Top;

            CaptureScreenToFreezeImage(left, top, width, height);

            OverlayInkCanvas.Strokes.Clear();
            if (RbBgScreen != null) RbBgScreen.IsChecked = true;
            if (BoardBackground != null) BoardBackground.Visibility = Visibility.Collapsed;
            if (FreezeImage != null) FreezeImage.Visibility = Visibility.Visible;

            // 2. Position window exactly over the targeted monitor
            Show();
            var helper = new System.Windows.Interop.WindowInteropHelper(this);
            NativeMethods.SetWindowPos(helper.Handle, IntPtr.Zero, left, top, width, height, NativeMethods.SWP_SHOWWINDOW | NativeMethods.SWP_NOZORDER);

            Activate();
            Focus();
        }
        catch (Exception ex)
        {
            MessageBox.Show($"화면 캡처 실패: {ex.Message}", "판서 오류", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    public void ShowBoardMode(string theme = "chalkboard")
    {
        try
        {
            IsBoardMode = true;

            var rect = NativeMethods.GetCurrentMonitorRect();
            int left = rect.Left;
            int top = rect.Top;
            int width = rect.Right - rect.Left;
            int height = rect.Bottom - rect.Top;

            if (FreezeImage != null)
            {
                FreezeImage.Source = null;
                FreezeImage.Visibility = Visibility.Collapsed;
            }

            if (BoardBackground != null)
            {
                BoardBackground.Visibility = Visibility.Visible;
                switch (theme)
                {
                    case "whiteboard":
                        if (RbBgWhiteboard != null) RbBgWhiteboard.IsChecked = true;
                        if (TxtStudioTitle != null) TxtStudioTitle.Text = "⬜ 수업 화이트보드 (Alt+4)";
                        BoardBackground.Background = System.Windows.Media.Brushes.White;
                        OverlayInkCanvas.DefaultDrawingAttributes.Color = (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#1E293B");
                        break;
                    case "grid":
                        if (RbBgGrid != null) RbBgGrid.IsChecked = true;
                        if (TxtStudioTitle != null) TxtStudioTitle.Text = "📐 수학 모눈 보드판 (Alt+4)";
                        BoardBackground.Background = CreateGridDrawingBrush();
                        OverlayInkCanvas.DefaultDrawingAttributes.Color = (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#1E293B");
                        break;
                    case "chalkboard":
                    default:
                        if (RbBgChalkboard != null) RbBgChalkboard.IsChecked = true;
                        if (TxtStudioTitle != null) TxtStudioTitle.Text = "🟩 수업 칠판 보드판 (Alt+4)";
                        BoardBackground.Background = new System.Windows.Media.SolidColorBrush(
                            (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#132B1E"));
                        OverlayInkCanvas.DefaultDrawingAttributes.Color = (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#FDE047");
                        break;
                }
            }

            OverlayInkCanvas.Strokes.Clear();

            Show();
            var helper = new System.Windows.Interop.WindowInteropHelper(this);
            NativeMethods.SetWindowPos(helper.Handle, IntPtr.Zero, left, top, width, height, NativeMethods.SWP_SHOWWINDOW | NativeMethods.SWP_NOZORDER);

            Activate();
            Focus();
        }
        catch (Exception ex)
        {
            MessageBox.Show($"칠판 보드판 실행 실패: {ex.Message}", "판서 오류", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void CaptureScreenToFreezeImage(int left, int top, int width, int height)
    {
        using var bmp = new Bitmap(width, height);
        using (var g = Graphics.FromImage(bmp))
        {
            g.CopyFromScreen(left, top, 0, 0, bmp.Size, CopyPixelOperation.SourceCopy);
        }

        using var ms = new MemoryStream();
        bmp.Save(ms, ImageFormat.Png);
        ms.Position = 0;
        var bitmapImage = new BitmapImage();
        bitmapImage.BeginInit();
        bitmapImage.CacheOption = BitmapCacheOption.OnLoad;
        bitmapImage.StreamSource = ms;
        bitmapImage.EndInit();
        bitmapImage.Freeze();
        FreezeImage.Source = bitmapImage;
    }

    private void CaptureScreenOnDemand()
    {
        bool wasVisible = IsVisible;
        if (wasVisible)
        {
            Visibility = Visibility.Hidden;
            System.Threading.Thread.Sleep(50);
        }

        var rect = NativeMethods.GetCurrentMonitorRect();
        int left = rect.Left;
        int top = rect.Top;
        int width = rect.Right - rect.Left;
        int height = rect.Bottom - rect.Top;

        CaptureScreenToFreezeImage(left, top, width, height);

        if (wasVisible)
        {
            Visibility = Visibility.Visible;
        }
    }

    private RulerToolControl? _ruler;
    private TriangleRulerToolControl? _triangle;
    private ProtractorToolControl? _protractor;

    public void CloseOverlay()
    {
        OverlayInkCanvas.Strokes.Clear();
        OverlayToolsCanvas.Children.Clear();
        _ruler = null;
        _triangle = null;
        _protractor = null;
        FreezeImage.Source = null;
        if (BoardBackground != null) BoardBackground.Visibility = Visibility.Collapsed;

        // Restore toolbar states
        if (ToolbarBorder != null) ToolbarBorder.Visibility = Visibility.Visible;
        if (MiniToolbarBorder != null) MiniToolbarBorder.Visibility = Visibility.Collapsed;
        if (ToolbarTransform != null)
        {
            ToolbarTransform.X = 0;
            ToolbarTransform.Y = 0;
        }
        if (MiniToolbarTransform != null)
        {
            MiniToolbarTransform.X = 0;
            MiniToolbarTransform.Y = 0;
        }

        Hide();
    }

    private void BtnToggleRuler_Click(object sender, RoutedEventArgs e)
    {
        if (_ruler == null)
        {
            _ruler = new RulerToolControl();
            _ruler.CloseRequested += () =>
            {
                OverlayToolsCanvas.Children.Remove(_ruler);
                _ruler = null;
            };
            double x = Math.Max(40, (ActualWidth - 460) / 2);
            double y = Math.Max(100, (ActualHeight - 80) / 2);
            Canvas.SetLeft(_ruler, x);
            Canvas.SetTop(_ruler, y);
            OverlayToolsCanvas.Children.Add(_ruler);
        }
        else
        {
            OverlayToolsCanvas.Children.Remove(_ruler);
            _ruler = null;
        }
    }

    private void BtnToggleTriangle_Click(object sender, RoutedEventArgs e)
    {
        if (_triangle == null)
        {
            _triangle = new TriangleRulerToolControl();
            _triangle.CloseRequested += () =>
            {
                OverlayToolsCanvas.Children.Remove(_triangle);
                _triangle = null;
            };
            double x = Math.Max(40, (ActualWidth - 320) / 2);
            double y = Math.Max(100, (ActualHeight - 260) / 2);
            Canvas.SetLeft(_triangle, x);
            Canvas.SetTop(_triangle, y);
            OverlayToolsCanvas.Children.Add(_triangle);
        }
        else
        {
            OverlayToolsCanvas.Children.Remove(_triangle);
            _triangle = null;
        }
    }

    private void BtnToggleProtractor_Click(object sender, RoutedEventArgs e)
    {
        if (_protractor == null)
        {
            _protractor = new ProtractorToolControl();
            _protractor.CloseRequested += () =>
            {
                OverlayToolsCanvas.Children.Remove(_protractor);
                _protractor = null;
            };
            double x = Math.Max(40, (ActualWidth - 380) / 2);
            double y = Math.Max(100, (ActualHeight - 210) / 2);
            Canvas.SetLeft(_protractor, x);
            Canvas.SetTop(_protractor, y);
            OverlayToolsCanvas.Children.Add(_protractor);
        }
        else
        {
            OverlayToolsCanvas.Children.Remove(_protractor);
            _protractor = null;
        }
    }

    #region Toolbar Dragging, Folding & Layout

    private bool _isDraggingToolbar;
    private System.Windows.Point _toolbarDragStartPoint;

    private void Toolbar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount == 2)
        {
            // Double click to fold/collapse toolbar
            BtnFoldToolbar_Click(sender, e);
            return;
        }

        if (e.ButtonState == MouseButtonState.Pressed)
        {
            _isDraggingToolbar = true;
            _toolbarDragStartPoint = e.GetPosition(this);
            ToolbarBorder.CaptureMouse();
        }
    }

    private void Toolbar_MouseMove(object sender, MouseEventArgs e)
    {
        if (_isDraggingToolbar && e.LeftButton == MouseButtonState.Pressed)
        {
            System.Windows.Point currentPoint = e.GetPosition(this);
            double deltaX = currentPoint.X - _toolbarDragStartPoint.X;
            double deltaY = currentPoint.Y - _toolbarDragStartPoint.Y;

            ToolbarTransform.X += deltaX;
            ToolbarTransform.Y += deltaY;
            _toolbarDragStartPoint = currentPoint;
        }
    }

    private void Toolbar_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (_isDraggingToolbar)
        {
            _isDraggingToolbar = false;
            ToolbarBorder.ReleaseMouseCapture();
        }
    }

    private bool _isDraggingMiniToolbar;
    private System.Windows.Point _miniDragStartPoint;

    private void MiniToolbar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ButtonState == MouseButtonState.Pressed)
        {
            _isDraggingMiniToolbar = true;
            _miniDragStartPoint = e.GetPosition(this);
            MiniToolbarBorder.CaptureMouse();
        }
    }

    private void MiniToolbar_MouseMove(object sender, MouseEventArgs e)
    {
        if (_isDraggingMiniToolbar && e.LeftButton == MouseButtonState.Pressed)
        {
            System.Windows.Point currentPoint = e.GetPosition(this);
            double deltaX = currentPoint.X - _miniDragStartPoint.X;
            double deltaY = currentPoint.Y - _miniDragStartPoint.Y;

            MiniToolbarTransform.X += deltaX;
            MiniToolbarTransform.Y += deltaY;
            _miniDragStartPoint = currentPoint;
        }
    }

    private void MiniToolbar_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (_isDraggingMiniToolbar)
        {
            _isDraggingMiniToolbar = false;
            MiniToolbarBorder.ReleaseMouseCapture();
        }
    }

    private void BtnFoldToolbar_Click(object sender, RoutedEventArgs e)
    {
        ToolbarBorder.Visibility = Visibility.Collapsed;
        MiniToolbarBorder.Visibility = Visibility.Visible;
        MiniToolbarTransform.X = ToolbarTransform.X;
        MiniToolbarTransform.Y = Math.Max(0, ToolbarTransform.Y);
    }

    private void BtnExpandToolbar_Click(object sender, RoutedEventArgs e)
    {
        MiniToolbarBorder.Visibility = Visibility.Collapsed;
        ToolbarBorder.Visibility = Visibility.Visible;
        ToolbarTransform.X = MiniToolbarTransform.X;
        ToolbarTransform.Y = MiniToolbarTransform.Y;
    }

    private bool _isOneRowMode = false;

    private void BtnToggleRowLayout_Click(object sender, RoutedEventArgs e)
    {
        _isOneRowMode = !_isOneRowMode;
        if (_isOneRowMode)
        {
            ToolbarMainStack.Orientation = Orientation.Horizontal;
            PanelRow1.Margin = new Thickness(0, 0, 10, 0);
            BtnToggleRowLayout.Content = "↕ 2줄로";
            BtnToggleRowLayout.ToolTip = "툴바를 2줄로 표시하여 모든 버튼을 한눈에 확인";
        }
        else
        {
            ToolbarMainStack.Orientation = Orientation.Vertical;
            PanelRow1.Margin = new Thickness(0, 0, 0, 6);
            BtnToggleRowLayout.Content = "↕ 1줄로";
            BtnToggleRowLayout.ToolTip = "툴바를 1줄로 슬림하게 표시";
        }
    }

    #endregion

    private void RbPen_Checked(object sender, RoutedEventArgs e)
    {
        if (OverlayInkCanvas == null) return;
        OverlayInkCanvas.EditingMode = InkCanvasEditingMode.Ink;
        OverlayInkCanvas.DefaultDrawingAttributes.IsHighlighter = false;
        OverlayInkCanvas.DefaultDrawingAttributes.Width = 4;
        OverlayInkCanvas.DefaultDrawingAttributes.Height = 4;
    }

    private void RbHighlighter_Checked(object sender, RoutedEventArgs e)
    {
        if (OverlayInkCanvas == null) return;
        OverlayInkCanvas.EditingMode = InkCanvasEditingMode.Ink;
        OverlayInkCanvas.DefaultDrawingAttributes.IsHighlighter = true;
        OverlayInkCanvas.DefaultDrawingAttributes.Width = 18;
        OverlayInkCanvas.DefaultDrawingAttributes.Height = 28;
    }

    private void RbEraser_Checked(object sender, RoutedEventArgs e)
    {
        if (OverlayInkCanvas == null) return;
        OverlayInkCanvas.EditingMode = InkCanvasEditingMode.EraseByStroke;
    }

    private void BtnColor_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string hex)
        {
            var color = (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString(hex);
            OverlayInkCanvas.DefaultDrawingAttributes.Color = color;
            if (RbEraser.IsChecked == true)
            {
                RbPen.IsChecked = true;
            }
        }
    }

    private void BtnUndo_Click(object sender, RoutedEventArgs e)
    {
        if (OverlayInkCanvas.Strokes.Count > 0)
        {
            OverlayInkCanvas.Strokes.RemoveAt(OverlayInkCanvas.Strokes.Count - 1);
        }
    }

    private void BtnClear_Click(object sender, RoutedEventArgs e)
    {
        OverlayInkCanvas.Strokes.Clear();
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e)
    {
        CloseOverlay();
    }

    private void RbBg_Checked(object sender, RoutedEventArgs e)
    {
        if (sender is RadioButton rb && rb.Tag is string mode)
        {
            switch (mode)
            {
                case "screen":
                    if (BoardBackground != null) BoardBackground.Visibility = Visibility.Collapsed;
                    if (FreezeImage != null)
                    {
                        if (FreezeImage.Source == null)
                        {
                            CaptureScreenOnDemand();
                        }
                        FreezeImage.Visibility = Visibility.Visible;
                    }
                    IsBoardMode = false;
                    if (TxtStudioTitle != null) TxtStudioTitle.Text = "🖼️ 화면 주석 판서 (Alt+2)";
                    break;
                case "chalkboard":
                    if (FreezeImage != null) FreezeImage.Visibility = Visibility.Collapsed;
                    if (BoardBackground != null)
                    {
                        BoardBackground.Visibility = Visibility.Visible;
                        BoardBackground.Background = new System.Windows.Media.SolidColorBrush(
                            (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#132B1E"));
                    }
                    IsBoardMode = true;
                    if (TxtStudioTitle != null) TxtStudioTitle.Text = "🟩 수업 칠판 보드판 (Alt+4)";
                    if (OverlayInkCanvas != null && (OverlayInkCanvas.DefaultDrawingAttributes.Color == System.Windows.Media.Colors.Black || OverlayInkCanvas.DefaultDrawingAttributes.Color == (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#1E293B")))
                    {
                        OverlayInkCanvas.DefaultDrawingAttributes.Color = (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#FDE047");
                    }
                    break;
                case "whiteboard":
                    if (FreezeImage != null) FreezeImage.Visibility = Visibility.Collapsed;
                    if (BoardBackground != null)
                    {
                        BoardBackground.Visibility = Visibility.Visible;
                        BoardBackground.Background = System.Windows.Media.Brushes.White;
                    }
                    IsBoardMode = true;
                    if (TxtStudioTitle != null) TxtStudioTitle.Text = "⬜ 수업 화이트보드 (Alt+4)";
                    if (OverlayInkCanvas != null && OverlayInkCanvas.DefaultDrawingAttributes.Color == System.Windows.Media.Colors.White)
                    {
                        OverlayInkCanvas.DefaultDrawingAttributes.Color = (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#1E293B");
                    }
                    break;
                case "grid":
                    if (FreezeImage != null) FreezeImage.Visibility = Visibility.Collapsed;
                    if (BoardBackground != null)
                    {
                        BoardBackground.Visibility = Visibility.Visible;
                        BoardBackground.Background = CreateGridDrawingBrush();
                    }
                    IsBoardMode = true;
                    if (TxtStudioTitle != null) TxtStudioTitle.Text = "📐 수학 모눈 보드판 (Alt+4)";
                    if (OverlayInkCanvas != null && OverlayInkCanvas.DefaultDrawingAttributes.Color == System.Windows.Media.Colors.White)
                    {
                        OverlayInkCanvas.DefaultDrawingAttributes.Color = (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#1E293B");
                    }
                    break;
            }
        }
    }

    private System.Windows.Media.DrawingBrush CreateGridDrawingBrush()
    {
        var gridDrawing = new System.Windows.Media.GeometryDrawing();
        gridDrawing.Brush = System.Windows.Media.Brushes.White;
        gridDrawing.Pen = new System.Windows.Media.Pen(
            new System.Windows.Media.SolidColorBrush((System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#E2E8F0")), 1);

        var group = new System.Windows.Media.GeometryGroup();
        group.Children.Add(new System.Windows.Media.LineGeometry(new System.Windows.Point(0, 0), new System.Windows.Point(32, 0)));
        group.Children.Add(new System.Windows.Media.LineGeometry(new System.Windows.Point(0, 0), new System.Windows.Point(0, 32)));
        gridDrawing.Geometry = group;

        return new System.Windows.Media.DrawingBrush(gridDrawing)
        {
            TileMode = System.Windows.Media.TileMode.Tile,
            Viewport = new System.Windows.Rect(0, 0, 32, 32),
            ViewportUnits = System.Windows.Media.BrushMappingMode.Absolute
        };
    }

    private void BtnStrokeWidth_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && double.TryParse(btn.Tag?.ToString(), out double width))
        {
            if (OverlayInkCanvas != null)
            {
                OverlayInkCanvas.DefaultDrawingAttributes.Width = width;
                OverlayInkCanvas.DefaultDrawingAttributes.Height = width;
                if (RbEraser.IsChecked == true) RbPen.IsChecked = true;
            }
        }
    }

    private string GetTargetSaveDirectory()
    {
        string baseDir = _configService?.GetEffectiveSaveDirectory()
            ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");

        bool useSubfolder = _configService?.StorageConfig?.CreateSubfolderForDrawings ?? true;
        string saveDir = useSubfolder ? Path.Combine(baseDir, "놀티쳐_판서") : baseDir;

        if (!Directory.Exists(saveDir))
        {
            Directory.CreateDirectory(saveDir);
        }
        return saveDir;
    }

    private void BtnSaveDrawing_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            int w = (int)ActualWidth;
            int h = (int)ActualHeight;
            if (w <= 0 || h <= 0) return;

            var rtb = new RenderTargetBitmap(w, h, 96, 96, System.Windows.Media.PixelFormats.Pbgra32);
            var dv = new System.Windows.Media.DrawingVisual();
            using (var dc = dv.RenderOpen())
            {
                if (BoardBackground != null && BoardBackground.Visibility == Visibility.Visible)
                {
                    dc.DrawRectangle(BoardBackground.Background, null, new Rect(0, 0, w, h));
                }
                else if (FreezeImage?.Source != null)
                {
                    dc.DrawImage(FreezeImage.Source, new Rect(0, 0, w, h));
                }
                else
                {
                    dc.DrawRectangle(System.Windows.Media.Brushes.White, null, new Rect(0, 0, w, h));
                }
            }
            rtb.Render(dv);
            rtb.Render(OverlayInkCanvas);

            // 1. Copy to Clipboard
            Clipboard.SetImage(rtb);

            // 2. Save PNG to configured save directory
            string saveDir = GetTargetSaveDirectory();
            string fileName = $"판서_{DateTime.Now:yyyyMMdd_HHmmss}.png";
            string fullPath = Path.Combine(saveDir, fileName);

            var encoder = new PngBitmapEncoder();
            encoder.Frames.Add(BitmapFrame.Create(rtb));
            using (var fs = new FileStream(fullPath, FileMode.Create))
            {
                encoder.Save(fs);
            }

            HudNotificationWindow.Instance.ShowToast("💾 판서 저장 완료", $"클립보드 복사 및 저장:\n{fileName}");
        }
        catch (Exception ex)
        {
            MessageBox.Show($"판서 저장 중 오류가 발생했습니다: {ex.Message}", "저장 오류", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void BtnOpenSaveFolder_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            string saveDir = GetTargetSaveDirectory();
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = saveDir,
                UseShellExecute = true
            });
        }
        catch (Exception ex)
        {
            MessageBox.Show($"폴더 열기 실패: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void BtnChangeSaveFolder_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var dlg = new Microsoft.Win32.OpenFolderDialog
            {
                Title = "판서 및 파일 기본 저장 폴더 선택",
                InitialDirectory = _configService?.GetEffectiveSaveDirectory() ?? string.Empty
            };

            if (dlg.ShowDialog() == true)
            {
                string chosen = dlg.FolderName;
                if (!string.IsNullOrWhiteSpace(chosen) && Directory.Exists(chosen))
                {
                    if (_configService != null)
                    {
                        _configService.SetDefaultSaveDirectory(chosen);
                        HudNotificationWindow.Instance.ShowToast("📁 저장 위치 변경", $"기본 저장 폴더가 설정되었습니다:\n{chosen}");
                    }
                }
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show($"저장 폴더 변경 실패: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
    {
        e.Cancel = true;
        CloseOverlay();
    }
}
