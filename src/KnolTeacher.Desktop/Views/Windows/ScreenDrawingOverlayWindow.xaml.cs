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

    protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
    {
        e.Cancel = true;
        CloseOverlay();
    }
}
