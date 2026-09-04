using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Shapes;

namespace KnolTeacher.Desktop.Views.Controls;

public partial class ProtractorToolControl : UserControl
{
    private bool _isDragging = false;
    private Point _startPoint;
    public event Action? CloseRequested;

    public ProtractorToolControl()
    {
        InitializeComponent();
        Loaded += (s, e) => DrawDegreeTicks();
        MouseWheel += (s, e) =>
        {
            double delta = e.Delta > 0 ? 5 : -5;
            SetAngle(ProtractorRotate.Angle + delta);
            e.Handled = true;
        };
    }

    private void DrawDegreeTicks()
    {
        CanvasDegreeTicks.Children.Clear();
        double cx = 190;
        double cy = 190;
        double outerR = 178;

        for (int deg = 0; deg <= 180; deg += 2)
        {
            double rad = Math.PI * (180 - deg) / 180.0;
            double tickLen = (deg % 10 == 0) ? 14 : ((deg % 5 == 0) ? 9 : 5);
            double innerR = outerR - tickLen;

            double x1 = cx + Math.Cos(rad) * outerR;
            double y1 = cy - Math.Sin(rad) * outerR;
            double x2 = cx + Math.Cos(rad) * innerR;
            double y2 = cy - Math.Sin(rad) * innerR;

            var line = new Line
            {
                X1 = x1,
                Y1 = y1,
                X2 = x2,
                Y2 = y2,
                Stroke = Brushes.Black,
                StrokeThickness = (deg % 10 == 0) ? 1.5 : 0.8
            };
            CanvasDegreeTicks.Children.Add(line);

            // Degree numbers (outer 0 to 180)
            if (deg % 10 == 0 && deg > 0 && deg < 180)
            {
                double textR = outerR - 24;
                double tx = cx + Math.Cos(rad) * textR;
                double ty = cy - Math.Sin(rad) * textR;

                var txt = new TextBlock
                {
                    Text = deg.ToString(),
                    FontSize = 8,
                    FontWeight = FontWeights.Bold,
                    Foreground = Brushes.Black
                };
                Canvas.SetLeft(txt, tx - 7);
                Canvas.SetTop(txt, ty - 6);
                CanvasDegreeTicks.Children.Add(txt);
            }
        }
    }

    private void SetAngle(double angle)
    {
        angle = (angle % 360 + 360) % 360;
        ProtractorRotate.Angle = Math.Round(angle);
        TxtAngle.Text = $"{Math.Round(angle)}°";
    }

    private void BtnRotateCW_Click(object sender, RoutedEventArgs e) => SetAngle(ProtractorRotate.Angle + 15);
    private void BtnRotateCCW_Click(object sender, RoutedEventArgs e) => SetAngle(ProtractorRotate.Angle - 15);
    private void BtnResetAngle_Click(object sender, RoutedEventArgs e) => SetAngle(0);
    private void BtnClose_Click(object sender, RoutedEventArgs e) => CloseRequested?.Invoke();

    private void Protractor_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.OriginalSource is Button) return;
        _isDragging = true;
        _startPoint = e.GetPosition(Parent as UIElement);
        CaptureMouse();
    }

    private void Protractor_MouseMove(object sender, MouseEventArgs e)
    {
        if (_isDragging && Parent is Canvas canvas)
        {
            Point current = e.GetPosition(canvas);
            double dx = current.X - _startPoint.X;
            double dy = current.Y - _startPoint.Y;

            double left = Canvas.GetLeft(this);
            double top = Canvas.GetTop(this);
            if (double.IsNaN(left)) left = 0;
            if (double.IsNaN(top)) top = 0;

            Canvas.SetLeft(this, left + dx);
            Canvas.SetTop(this, top + dy);
            _startPoint = current;
        }
    }

    private void Protractor_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        _isDragging = false;
        ReleaseMouseCapture();
    }
}