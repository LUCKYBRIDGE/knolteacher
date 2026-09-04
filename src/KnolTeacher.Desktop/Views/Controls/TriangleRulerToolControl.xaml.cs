using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace KnolTeacher.Desktop.Views.Controls;

public partial class TriangleRulerToolControl : UserControl
{
    private bool _isDragging = false;
    private Point _startPoint;
    public event Action? CloseRequested;

    public TriangleRulerToolControl()
    {
        InitializeComponent();
        MouseWheel += (s, e) =>
        {
            double delta = e.Delta > 0 ? 5 : -5;
            SetAngle(TriRotate.Angle + delta);
            e.Handled = true;
        };
    }

    private void SetAngle(double angle)
    {
        angle = (angle % 360 + 360) % 360;
        TriRotate.Angle = Math.Round(angle);
        TxtAngle.Text = $"{Math.Round(angle)}°";
    }

    private void BtnRotateCW_Click(object sender, RoutedEventArgs e) => SetAngle(TriRotate.Angle + 15);
    private void BtnRotateCCW_Click(object sender, RoutedEventArgs e) => SetAngle(TriRotate.Angle - 15);
    private void BtnResetAngle_Click(object sender, RoutedEventArgs e) => SetAngle(0);
    private void BtnClose_Click(object sender, RoutedEventArgs e) => CloseRequested?.Invoke();

    private void Triangle_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.OriginalSource is Button) return;
        _isDragging = true;
        _startPoint = e.GetPosition(Parent as UIElement);
        CaptureMouse();
    }

    private void Triangle_MouseMove(object sender, MouseEventArgs e)
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

    private void Triangle_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        _isDragging = false;
        ReleaseMouseCapture();
    }
}