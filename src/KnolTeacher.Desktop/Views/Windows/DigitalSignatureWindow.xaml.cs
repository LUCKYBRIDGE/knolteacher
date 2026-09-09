using System;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Ink;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Microsoft.Win32;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class DigitalSignatureWindow : Window
{
    private bool _isStampMode = true;
    private bool _isCheckerboard = true;
    private bool _isEraserMode = false;
    private Color _inkColor = (Color)ColorConverter.ConvertFromString("#0F172A");
    private double _penThickness = 2.5;
    private SignatureStyle _signatureStyle = SignatureStyle.FountainPen;
    private readonly IConfigService? _configService;

    public DigitalSignatureWindow(IConfigService? configService = null)
    {
        _configService = configService;
        InitializeComponent();

        Loaded += (s, e) =>
        {
            UpdatePenAttributes();
            RenderStamp();
        };

        Closing += (s, e) =>
        {
            e.Cancel = true;
            Hide();
        };
    }

    private void BtnModeStamp_Click(object sender, RoutedEventArgs e)
    {
        _isStampMode = true;
        BtnModeStamp.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0284C7"));
        BtnModeStamp.Foreground = Brushes.White;
        BtnModeSignature.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F1F5F9"));
        BtnModeSignature.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#475569"));

        PanelStampOptions.Visibility = Visibility.Visible;
        PanelSignatureOptions.Visibility = Visibility.Collapsed;

        ViewboxStamp.Visibility = Visibility.Visible;
        SignatureCanvas.Visibility = Visibility.Collapsed;
        RenderStamp();
    }

    private void BtnModeSignature_Click(object sender, RoutedEventArgs e)
    {
        _isStampMode = false;
        BtnModeSignature.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0284C7"));
        BtnModeSignature.Foreground = Brushes.White;
        BtnModeStamp.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F1F5F9"));
        BtnModeStamp.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#475569"));

        PanelSignatureOptions.Visibility = Visibility.Visible;
        PanelStampOptions.Visibility = Visibility.Collapsed;

        SignatureCanvas.Visibility = Visibility.Visible;
        ViewboxStamp.Visibility = Visibility.Collapsed;
    }

    private void StampOptionChanged(object sender, RoutedEventArgs e)
    {
        if (IsLoaded && _isStampMode)
        {
            RenderStamp();
        }
    }

    private void RenderStamp()
    {
        if (StampBorder == null || GridStampContent == null) return;

        string text = TbStampText?.Text.Trim() ?? "홍길동인";
        if (string.IsNullOrEmpty(text)) text = "인";

        // 1. Color
        Color stampColor = (Color)ColorConverter.ConvertFromString("#DC2626");
        if (RbColorDarkRed?.IsChecked == true) stampColor = (Color)ColorConverter.ConvertFromString("#991B1B");
        else if (RbColorBlack?.IsChecked == true) stampColor = (Color)ColorConverter.ConvertFromString("#0F172A");

        var stampBrush = new SolidColorBrush(stampColor);
        double borderThick = SliderBorderThickness?.Value ?? 4;
        StampBorder.BorderBrush = stampBrush;
        StampBorder.BorderThickness = new Thickness(borderThick);

        // 2. Shape
        if (RbShapeSquare?.IsChecked == true)
        {
            StampBorder.Width = 140;
            StampBorder.Height = 140;
            StampBorder.CornerRadius = new CornerRadius(6);
        }
        else if (RbShapeOval?.IsChecked == true)
        {
            StampBorder.Width = 110;
            StampBorder.Height = 150;
            StampBorder.CornerRadius = new CornerRadius(55);
        }
        else // Circle (default)
        {
            StampBorder.Width = 140;
            StampBorder.Height = 140;
            StampBorder.CornerRadius = new CornerRadius(70);
        }

        // 3. Font
        string fontName = "Gungsuh";
        if (ComboStampFont?.SelectedItem is ComboBoxItem item && item.Tag is string tag)
        {
            fontName = tag;
        }
        var stampFontFamily = new FontFamily(fontName + ", Batang, Malgun Gothic");

        // 4. Text Layout inside stamp
        GridStampContent.Children.Clear();
        GridStampContent.RowDefinitions.Clear();
        GridStampContent.ColumnDefinitions.Clear();

        bool isVertical = RbAlignVertical?.IsChecked == true;

        if (text.Length == 4)
        {
            // Standard 2x2 stamp
            GridStampContent.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            GridStampContent.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            GridStampContent.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            GridStampContent.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            // Traditional Korean stamp reads right to left:
            // Top-Right: text[0], Bottom-Right: text[1], Top-Left: text[2], Bottom-Left: text[3]
            char c0 = text[0];
            char c1 = text[1];
            char c2 = text[2];
            char c3 = text[3];

            if (isVertical)
            {
                AddStampChar(c0, 0, 1, stampFontFamily, stampBrush, 40);
                AddStampChar(c1, 1, 1, stampFontFamily, stampBrush, 40);
                AddStampChar(c2, 0, 0, stampFontFamily, stampBrush, 40);
                AddStampChar(c3, 1, 0, stampFontFamily, stampBrush, 40);
            }
            else
            {
                AddStampChar(c0, 0, 0, stampFontFamily, stampBrush, 40);
                AddStampChar(c1, 0, 1, stampFontFamily, stampBrush, 40);
                AddStampChar(c2, 1, 0, stampFontFamily, stampBrush, 40);
                AddStampChar(c3, 1, 1, stampFontFamily, stampBrush, 40);
            }
        }
        else if (text.Length == 3)
        {
            // 3 chars: add '인' or 1 on top, 2 on bottom
            GridStampContent.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            GridStampContent.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            GridStampContent.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            GridStampContent.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            if (isVertical)
            {
                AddStampChar(text[0], 0, 1, stampFontFamily, stampBrush, 40);
                AddStampChar(text[1], 1, 1, stampFontFamily, stampBrush, 40);
                AddStampChar(text[2], 0, 0, stampFontFamily, stampBrush, 40);
                AddStampChar('인', 1, 0, stampFontFamily, stampBrush, 40);
            }
            else
            {
                AddStampChar(text[0], 0, 0, stampFontFamily, stampBrush, 40);
                AddStampChar(text[1], 0, 1, stampFontFamily, stampBrush, 40);
                AddStampChar(text[2], 1, 0, stampFontFamily, stampBrush, 40);
                AddStampChar('인', 1, 1, stampFontFamily, stampBrush, 40);
            }
        }
        else if (text.Length <= 2)
        {
            // 2 chars vertical
            GridStampContent.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            GridStampContent.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            GridStampContent.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            AddStampChar(text[0], 0, 0, stampFontFamily, stampBrush, 48);
            if (text.Length > 1)
            {
                AddStampChar(text[1], 1, 0, stampFontFamily, stampBrush, 48);
            }
        }
        else
        {
            // Longer names (e.g. 5~8 chars, like school seal)
            int cols = 3;
            int rows = (int)Math.Ceiling((double)text.Length / cols);
            for (int r = 0; r < rows; r++) GridStampContent.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            for (int c = 0; c < cols; c++) GridStampContent.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            double size = Math.Max(18, 36 - (text.Length * 1.5));
            int idx = 0;
            for (int r = 0; r < rows; r++)
            {
                for (int c = 0; c < cols && idx < text.Length; c++)
                {
                    AddStampChar(text[idx++], r, c, stampFontFamily, stampBrush, size);
                }
            }
        }
    }

    private void AddStampChar(char ch, int row, int col, FontFamily font, Brush brush, double fontSize)
    {
        var tb = new TextBlock
        {
            Text = ch.ToString(),
            FontFamily = font,
            FontSize = fontSize,
            FontWeight = FontWeights.Bold,
            Foreground = brush,
            HorizontalAlignment = HorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center,
            Margin = new Thickness(1)
        };
        Grid.SetRow(tb, row);
        Grid.SetColumn(tb, col);
        GridStampContent.Children.Add(tb);
    }

    private void PenOptionChanged(object sender, RoutedEventArgs e)
    {
        if (SignatureCanvas == null) return;

        if (RbPenThin?.IsChecked == true) _penThickness = 1.5;
        else if (RbPenMedium?.IsChecked == true) _penThickness = 2.5;
        else if (RbPenThick?.IsChecked == true) _penThickness = 4.0;
        else if (RbPenBold?.IsChecked == true) _penThickness = 6.0;

        if (RbInkBlack?.IsChecked == true) _inkColor = (Color)ColorConverter.ConvertFromString("#0F172A");
        else if (RbInkBlue?.IsChecked == true) _inkColor = (Color)ColorConverter.ConvertFromString("#1D4ED8");
        else if (RbInkRed?.IsChecked == true) _inkColor = (Color)ColorConverter.ConvertFromString("#DC2626");

        UpdatePenAttributes();
    }

    private void UpdatePenAttributes()
    {
        if (SignatureCanvas == null) return;

        var da = new DrawingAttributes
        {
            Color = _inkColor,
            Width = _penThickness,
            Height = _penThickness,
            FitToCurve = true,
            IsHighlighter = false,
            IgnorePressure = false
        };
        SignatureCanvas.DefaultDrawingAttributes = da;
    }

    private void SignatureStyleChanged(object sender, RoutedEventArgs e)
    {
        if (!IsLoaded) return;

        if (RbStyleFountain?.IsChecked == true) _signatureStyle = SignatureStyle.FountainPen;
        else if (RbStyleBrush?.IsChecked == true) _signatureStyle = SignatureStyle.BrushPen;
        else if (RbStyleStandard?.IsChecked == true) _signatureStyle = SignatureStyle.Standard;

        if (SignatureCanvas != null && SignatureCanvas.Strokes.Count > 0)
        {
            SignatureStrokeBeautifier.BeautifyAll(SignatureCanvas.Strokes, _signatureStyle);
        }
    }

    private void SignatureCanvas_StrokeCollected(object sender, InkCanvasStrokeCollectedEventArgs e)
    {
        if (e.Stroke != null && _signatureStyle != SignatureStyle.Standard)
        {
            SignatureStrokeBeautifier.BeautifyStroke(e.Stroke, _signatureStyle);
        }
    }

    private void BtnUndoSignature_Click(object sender, RoutedEventArgs e)
    {
        if (SignatureCanvas != null && SignatureCanvas.Strokes.Count > 0)
        {
            SignatureCanvas.Strokes.RemoveAt(SignatureCanvas.Strokes.Count - 1);
        }
    }

    private void Window_KeyDown(object sender, KeyEventArgs e)
    {
        if (!_isStampMode && (Keyboard.Modifiers & ModifierKeys.Control) == ModifierKeys.Control && e.Key == Key.Z)
        {
            BtnUndoSignature_Click(sender, e);
            e.Handled = true;
        }
    }

    private void BtnToggleEraser_Click(object sender, RoutedEventArgs e)
    {
        _isEraserMode = !_isEraserMode;
        SignatureCanvas.EditingMode = _isEraserMode ? InkCanvasEditingMode.EraseByStroke : InkCanvasEditingMode.Ink;
        BtnToggleEraser.Content = _isEraserMode ? "✏️ 펜 모드로 전환" : "🧹 부분 지우개";
        BtnToggleEraser.Background = _isEraserMode ? new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FEF3C7")) : new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F1F5F9"));
    }

    private void BtnClearSignature_Click(object sender, RoutedEventArgs e)
    {
        SignatureCanvas.Strokes.Clear();
    }

    private void BtnToggleBgGrid_Click(object sender, RoutedEventArgs e)
    {
        _isCheckerboard = !_isCheckerboard;
        if (_isCheckerboard)
        {
            PreviewContainer.Background = (Brush)FindResource("CheckerboardBrush");
            BtnToggleBgGrid.Content = "🏁 투명 격자 배경";
        }
        else
        {
            PreviewContainer.Background = Brushes.White;
            BtnToggleBgGrid.Content = "📄 흰색 종이 배경";
        }
    }

    private BitmapSource RenderTargetToBitmap()
    {
        if (_isStampMode)
        {
            StampBorder.Measure(new Size(StampBorder.Width, StampBorder.Height));
            StampBorder.Arrange(new Rect(0, 0, StampBorder.Width, StampBorder.Height));
            StampBorder.UpdateLayout();

            int w = (int)StampBorder.Width;
            int h = (int)StampBorder.Height;
            var rtb = new RenderTargetBitmap(w, h, 96, 96, PixelFormats.Pbgra32);
            rtb.Render(StampBorder);
            return rtb;
        }
        else
        {
            int w = Math.Max(200, (int)SignatureCanvas.ActualWidth);
            int h = Math.Max(120, (int)SignatureCanvas.ActualHeight);
            var rtb = new RenderTargetBitmap(w, h, 96, 96, PixelFormats.Pbgra32);
            rtb.Render(SignatureCanvas);

            // Auto-crop tightly to stroke bounds with 16px padding
            if (SignatureCanvas.Strokes.Count > 0)
            {
                var bounds = SignatureCanvas.Strokes.GetBounds();
                if (bounds.Width > 4 && bounds.Height > 4)
                {
                    double pad = 16.0;
                    double cropX = Math.Max(0, bounds.Left - pad);
                    double cropY = Math.Max(0, bounds.Top - pad);
                    double cropR = Math.Min(w, bounds.Right + pad);
                    double cropB = Math.Min(h, bounds.Bottom + pad);
                    int cropW = Math.Max(10, (int)(cropR - cropX));
                    int cropH = Math.Max(10, (int)(cropB - cropY));

                    if (cropX + cropW <= w && cropY + cropH <= h)
                    {
                        return new CroppedBitmap(rtb, new Int32Rect((int)cropX, (int)cropY, cropW, cropH));
                    }
                }
            }

            return rtb;
        }
    }

    private void BtnCopyClipboard_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var rtb = RenderTargetToBitmap();
            var encoder = new PngBitmapEncoder();
            encoder.Frames.Add(BitmapFrame.Create(rtb));

            using var ms = new MemoryStream();
            encoder.Save(ms);
            ms.Seek(0, SeekOrigin.Begin);

            // Put transparent PNG and standard bitmap in clipboard
            var dataObj = new DataObject();
            dataObj.SetData("PNG", ms, false);
            dataObj.SetImage(rtb);
            Clipboard.SetDataObject(dataObj, true);

            MessageBox.Show(
                "🌟 투명 배경 전자 도장/서명이 클립보드에 복사되었습니다!\n\n" +
                "한글(HWP), Word, Excel, PPT, 나이스 화면 등에서\n" +
                "[Ctrl + V]를 누르면 문서 글자 위에 자연스럽게 날인됩니다.",
                "클립보드 복사 완료",
                MessageBoxButton.OK,
                MessageBoxImage.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"클립보드 복사 중 오류: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void BtnSavePng_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var rtb = RenderTargetToBitmap();
            var dlg = new SaveFileDialog
            {
                Filter = "PNG 투명 이미지 (*.png)|*.png",
                FileName = _isStampMode ? $"도장_{TbStampText?.Text.Trim()}.png" : "전자서명.png",
                DefaultExt = ".png",
                InitialDirectory = _configService?.GetEffectiveSaveDirectory() ?? string.Empty
            };

            if (dlg.ShowDialog() == true)
            {
                var encoder = new PngBitmapEncoder();
                encoder.Frames.Add(BitmapFrame.Create(rtb));
                using var fs = new FileStream(dlg.FileName, FileMode.Create);
                encoder.Save(fs);

                MessageBox.Show($"'{System.IO.Path.GetFileName(dlg.FileName)}' 파일로 안전하게 저장되었습니다!", "저장 완료", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show($"파일 저장 중 오류: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }
}
