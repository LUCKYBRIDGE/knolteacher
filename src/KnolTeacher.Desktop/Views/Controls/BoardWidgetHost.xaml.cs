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

            // Boundaries
            newLeft = Math.Max(0, Math.Min(newLeft, canvas.ActualWidth - ActualWidth));
            newTop = Math.Max(0, Math.Min(newTop, canvas.ActualHeight - ActualHeight));

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

        double newWidth = ActualWidth + e.HorizontalChange;
        double newHeight = ActualHeight + e.VerticalChange;

        if (newWidth >= MinWidth)
        {
            Width = newWidth;
        }

        if (newHeight >= MinHeight)
        {
            Height = newHeight;
        }

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
