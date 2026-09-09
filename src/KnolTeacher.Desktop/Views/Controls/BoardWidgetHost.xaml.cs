using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;

namespace KnolTeacher.Desktop.Views.Controls;

public partial class BoardWidgetHost : UserControl
{
    private static int _globalZIndex = 10;

    public string WidgetId { get; set; } = Guid.NewGuid().ToString();
    public string WidgetType { get; set; } = string.Empty;

    public event Action<BoardWidgetHost>? Closed;

    private bool _isDragging = false;
    private Point _dragStartPoint;
    private bool _isLocked = false;

    public bool IsLocked
    {
        get => _isLocked;
        set
        {
            _isLocked = value;
            TitleBar.Cursor = _isLocked ? Cursors.Arrow : Cursors.SizeAll;
            ResizeThumb.Visibility = _isLocked ? Visibility.Collapsed : Visibility.Visible;
            TxtLockIcon.Visibility = _isLocked ? Visibility.Visible : Visibility.Collapsed;
            TxtDragGrip.Visibility = _isLocked ? Visibility.Collapsed : Visibility.Visible;
        }
    }

    public double CardOpacity
    {
        get => OuterBorder.Opacity;
        set => OuterBorder.Opacity = Math.Clamp(value, 0.2, 1.0);
    }

    public string Title
    {
        get => TxtTitle.Text;
        set => TxtTitle.Text = value;
    }

    public object WidgetContent
    {
        get => HostContentPresenter.Content;
        set => HostContentPresenter.Content = value;
    }

    public BoardWidgetHost()
    {
        InitializeComponent();
        Loaded += (s, e) => BringToFront();
        MouseDown += (s, e) => BringToFront();
    }

    public void BringToFront()
    {
        Panel.SetZIndex(this, ++_globalZIndex);
    }

    private void TitleBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        BringToFront();
        if (_isLocked) return;

        if (VisualParent is Canvas)
        {
            _isDragging = true;
            _dragStartPoint = e.GetPosition(this);
            TitleBar.CaptureMouse();
            e.Handled = true;
        }
    }

    private void TitleBar_MouseMove(object sender, MouseEventArgs e)
    {
        if (_isDragging && VisualParent is Canvas canvas)
        {
            Point currentPos = e.GetPosition(canvas);
            double newLeft = currentPos.X - _dragStartPoint.X;
            double newTop = currentPos.Y - _dragStartPoint.Y;

            double currentW = ActualWidth > 0 ? ActualWidth : Width;
            double currentH = ActualHeight > 0 ? ActualHeight : Height;

            double maxLeft = Math.Max(0, canvas.ActualWidth - currentW);
            double maxTop = Math.Max(0, canvas.ActualHeight - currentH);

            newLeft = Math.Clamp(newLeft, 0, maxLeft);
            newTop = Math.Clamp(newTop, 0, maxTop);

            Canvas.SetLeft(this, newLeft);
            Canvas.SetTop(this, newTop);
            e.Handled = true;
        }
    }

    private void TitleBar_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (_isDragging)
        {
            _isDragging = false;
            TitleBar.ReleaseMouseCapture();
            e.Handled = true;
        }
    }

    private void ResizeThumb_DragDelta(object sender, DragDeltaEventArgs e)
    {
        if (_isLocked) return;
        BringToFront();

        double curLeft = Canvas.GetLeft(this);
        double curTop = Canvas.GetTop(this);
        if (double.IsNaN(curLeft)) curLeft = 0;
        if (double.IsNaN(curTop)) curTop = 0;

        double canvasWidth = (VisualParent is Canvas canvas) ? canvas.ActualWidth : double.MaxValue;
        double canvasHeight = (VisualParent is Canvas c) ? c.ActualHeight : double.MaxValue;

        double maxAllowedW = Math.Max(MinWidth, canvasWidth - curLeft - 6);
        double maxAllowedH = Math.Max(MinHeight, canvasHeight - curTop - 6);

        double newWidth = Math.Clamp(ActualWidth + e.HorizontalChange, MinWidth, maxAllowedW);
        double newHeight = Math.Clamp(ActualHeight + e.VerticalChange, MinHeight, maxAllowedH);

        Width = newWidth;
        Height = newHeight;

        e.Handled = true;
    }

    private double _scale = 1.0;

    private void BtnZoomIn_Click(object sender, RoutedEventArgs e)
    {
        if (_scale < 2.0)
        {
            _scale = Math.Round(_scale + 0.1, 1);
            ApplyScale();
        }
    }

    private void BtnZoomOut_Click(object sender, RoutedEventArgs e)
    {
        if (_scale > 0.7)
        {
            _scale = Math.Round(_scale - 0.1, 1);
            ApplyScale();
        }
    }

    private void ApplyScale()
    {
        ContentScaleTransform.ScaleX = _scale;
        ContentScaleTransform.ScaleY = _scale;
        TxtZoomLevel.Text = $"{(_scale * 100):0}%";
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e)
    {
        Closed?.Invoke(this);
    }
}
