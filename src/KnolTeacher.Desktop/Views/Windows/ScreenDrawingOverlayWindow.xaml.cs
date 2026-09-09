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
    public ScreenDrawingOverlayWindow()
    {
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

    public void FreezeAndShow()
    {
        try
        {
            // 1. Get current monitor under mouse cursor
            var rect = NativeMethods.GetCurrentMonitorRect();
            int left = rect.Left;
            int top = rect.Top;
            int width = rect.Right - rect.Left;
            int height = rect.Bottom - rect.Top;

            using (var bmp = new Bitmap(width, height))
            {
                using (var g = Graphics.FromImage(bmp))
                {
                    g.CopyFromScreen(left, top, 0, 0, bmp.Size, CopyPixelOperation.SourceCopy);
                }

                // Convert to WPF BitmapImage
                using (var ms = new MemoryStream())
                {
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
            }

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

    private void Toolbar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ButtonState == MouseButtonState.Pressed)
        {
            DragMove();
        }
    }

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
                    if (FreezeImage != null) FreezeImage.Visibility = Visibility.Visible;
                    break;
                case "chalkboard":
                    if (FreezeImage != null) FreezeImage.Visibility = Visibility.Collapsed;
                    if (BoardBackground != null)
                    {
                        BoardBackground.Visibility = Visibility.Visible;
                        BoardBackground.Background = new System.Windows.Media.SolidColorBrush(
                            (System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#132B1E"));
                    }
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

            // 2. Save PNG to Pictures/놀티쳐_판서
            var picturesDir = Environment.GetFolderPath(Environment.SpecialFolder.MyPictures);
            var saveDir = Path.Combine(picturesDir, "놀티쳐_판서");
            Directory.CreateDirectory(saveDir);

            string fileName = $"판서_{DateTime.Now:yyyyMMdd_HHmmss}.png";
            string fullPath = Path.Combine(saveDir, fileName);

            var encoder = new PngBitmapEncoder();
            encoder.Frames.Add(BitmapFrame.Create(rtb));
            using (var fs = new FileStream(fullPath, FileMode.Create))
            {
                encoder.Save(fs);
            }

            HudNotificationWindow.Instance.ShowToast("💾 판서 저장 완료", $"클립보드 복사 및 저장 완료:\n{fileName}");
        }
        catch (Exception ex)
        {
            MessageBox.Show($"판서 저장 중 오류가 발생했습니다: {ex.Message}", "저장 오류", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
    {
        e.Cancel = true;
        CloseOverlay();
    }
}
