using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Shapes;

namespace KnolTeacher.Desktop.Views.Controls;

public partial class RulerToolControl : UserControl
{
    private bool _isDragging = false;
    private Point _startPoint;
    public event Action? CloseRequested;

    public RulerToolControl()
    {
        InitializeComponent();
        Loaded += (s, e) => DrawTicks();
        MouseWheel += RulerToolControl_MouseWheel;
    }

    private void RulerToolControl_MouseWheel(object sender, MouseWheelEventArgs e)
    {
        double delta = e.Delta > 0 ? 5 : -5;
        SetAngle(RulerRotate.Angle + delta);
        e.Handled = true;
    }

    private void DrawTicks()
    {
        CanvasTicks.Children.Clear();
        double totalLength = 440; // 0 to 20 cm => 22 px per cm
        double pxPerMm = totalLength / 200.0;

        for (int mm = 0; mm <= 200; mm++)
        {
            double x = mm * pxPerMm;
            double tickHeight;

            if (mm % 10 == 0) tickHeight = 18;
            else if (mm % 5 == 0) tickHeight = 12;
            else tickHeight = 7;

            var line = new Line
            {
                X1 = x,
                Y1 = 0,
                X2 = x,
                Y2 = tickHeight,
                Stroke = Brushes.Black,
                StrokeThickness = (mm % 10 == 0) ? 1.5 : 1
            };
            CanvasTicks.Children.Add(line);

            if (mm % 10 == 0)
            {
                int cm = mm / 10;
                var text = new TextBlock
                {
                    Text = cm.ToString(),
                    FontSize = 9,
                    FontWeight = FontWeights.Bold,
                    Foreground = Brushes.Black
                };
                Canvas.SetLeft(text, x - 4);
                Canvas.SetTop(text, tickHeight + 1);
                CanvasTicks.Children.Add(text);
            }
        }
    }

    private void SetAngle(double angle)
    {
        angle = (angle % 360 + 360) % 360;
        RulerRotate.Angle = Math.Round(angle);
        TxtAngle.Text = $"{Math.Round(angle)}°";
    }

    private void BtnRotateCW_Click(object sender, RoutedEventArgs e) => SetAngle(RulerRotate.Angle + 15);
    private void BtnRotateCCW_Click(object sender, RoutedEventArgs e) => SetAngle(RulerRotate.Angle - 15);
    private void BtnResetAngle_Click(object sender, RoutedEventArgs e) => SetAngle(0);
    private void BtnClose_Click(object sender, RoutedEventArgs e) => CloseRequested?.Invoke();

    private void Ruler_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.OriginalSource is Button) return;
        _isDragging = true;
        _startPoint = e.GetPosition(Parent as UIElement);
        CaptureMouse();
    }

    private void Ruler_MouseMove(object sender, MouseEventArgs e)
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

    private void Ruler_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        _isDragging = false;
        ReleaseMouseCapture();
    }
}