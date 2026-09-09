using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;

namespace KnolTeacher.Desktop.Views.Controls;

public partial class BoardWidgetHost : UserControl
{
    private static int _globalZIndex = 10;

    private string _widgetType = string.Empty;
    private bool _isDragging;
    private Point _dragStartPoint;
    private bool _isLocked;
    private bool _canResize = true;
    private bool _canZoom = true;
    private bool _isContentActive;
    private bool _isContentDisposed;

    public string WidgetId { get; set; } = Guid.NewGuid().ToString();

    public string WidgetType
    {
        get => _widgetType;
        set
        {
            _widgetType = value ?? string.Empty;
            ApplyWidgetDefinition();
        }
    }

    public event Action<BoardWidgetHost>? Closed;
    public event Action<BoardWidgetHost>? MovedOrResized;

    public bool IsLocked
    {
        get => _isLocked;
        set
        {
            _isLocked = value;
            UpdateInteractionState();
        }
    }

    public bool CanResize
    {
        get => _canResize;
        set
        {
            _canResize = value;
            UpdateInteractionState();
        }
    }

    public bool CanZoom
    {
        get => _canZoom;
        set
        {
            _canZoom = value;
            UpdateInteractionState();
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
        set
        {
            if (ReferenceEquals(HostContentPresenter.Content, value)) return;

            DisposeContent();
            HostContentPresenter.Content = value;
            _isContentDisposed = false;
            _isContentActive = false;

            if (IsLoaded && IsVisible)
            {
                ActivateContent();
            }
        }
    }

    public BoardWidgetHost()
    {
        InitializeComponent();

        Stylus.SetIsPressAndHoldEnabled(TitleBar, false);
        Stylus.SetIsFlicksEnabled(TitleBar, false);

        Loaded += BoardWidgetHost_Loaded;
        Unloaded += BoardWidgetHost_Unloaded;
        IsVisibleChanged += BoardWidgetHost_IsVisibleChanged;
        MouseDown += (s, e) => BringToFront();
        TitleBar.LostMouseCapture += (s, e) => _isDragging = false;

        UpdateInteractionState();
    }

    private void ApplyWidgetDefinition()
    {
        var definition = WidgetRegistry.GetOrDefault(_widgetType);
        if (definition == null) return;

        MinWidth = definition.MinWidth;
        MinHeight = definition.MinHeight;
        CanResize = definition.CanResize;
        CanZoom = definition.CanZoom;

        if (double.IsNaN(Width) || Width <= 0)
        {
            Width = definition.DefaultWidth;
        }

        if (double.IsNaN(Height) || Height <= 0)
        {
            Height = definition.DefaultHeight;
        }

        if (string.IsNullOrWhiteSpace(Title) || Title == "위젯 제목")
        {
            Title = definition.Title;
        }
    }

    private void UpdateInteractionState()
    {
        if (!IsInitialized) return;

        TitleBar.Cursor = _isLocked ? Cursors.Arrow : Cursors.SizeAll;
        ResizeLayer.Visibility = !_isLocked && _canResize ? Visibility.Visible : Visibility.Collapsed;
        ZoomControlsContainer.Visibility = _canZoom ? Visibility.Visible : Visibility.Collapsed;
        TxtLockIcon.Visibility = _isLocked ? Visibility.Visible : Visibility.Collapsed;
        TxtDragGrip.Visibility = _isLocked ? Visibility.Collapsed : Visibility.Visible;
    }

    public void ActivateContent()
    {
        if (_isContentDisposed || _isContentActive) return;

        if (HostContentPresenter.Content is IWidgetLifecycle lifecycle)
        {
            lifecycle.Activate();
        }

        _isContentActive = true;
    }

    public void DeactivateContent()
    {
        if (_isContentDisposed || !_isContentActive) return;

        if (HostContentPresenter.Content is IWidgetLifecycle lifecycle)
        {
            lifecycle.Deactivate();
        }

        _isContentActive = false;
    }

    public void DisposeContent()
    {
        if (_isContentDisposed) return;

        DeactivateContent();

        if (HostContentPresenter.Content is IWidgetLifecycle lifecycle)
        {
            lifecycle.Dispose();
        }
        else if (HostContentPresenter.Content is IDisposable disposable)
        {
            disposable.Dispose();
        }

        _isContentDisposed = true;
        _isContentActive = false;
    }

    private void BoardWidgetHost_Loaded(object sender, RoutedEventArgs e)
    {
        BringToFront();
        UpdateInteractionState();
        if (IsVisible)
        {
            ActivateContent();
        }
    }

    private void BoardWidgetHost_Unloaded(object sender, RoutedEventArgs e)
    {
        // A widget removed from the Canvas is not reused. Dispose all external resources.
        DisposeContent();
    }

    private void BoardWidgetHost_IsVisibleChanged(object sender, DependencyPropertyChangedEventArgs e)
    {
        if (e.NewValue is true)
        {
            ActivateContent();
        }
        else
        {
            DeactivateContent();
        }
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

            double currentW = GetCurrentWidth();
            double currentH = GetCurrentHeight();

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
            MovedOrResized?.Invoke(this);
        }
    }

    private void ResizeThumb_DragCompleted(object sender, DragCompletedEventArgs e)
    {
        MovedOrResized?.Invoke(this);
    }

    private void ResizeThumb_DragDelta(object sender, DragDeltaEventArgs e)
    {
        if (_isLocked || !_canResize) return;
        if (sender is not Thumb thumb || thumb.Tag is not string direction) return;
        if (VisualParent is not Canvas canvas) return;

        BringToFront();

        double left = Canvas.GetLeft(this);
        double top = Canvas.GetTop(this);
        if (double.IsNaN(left)) left = 0;
        if (double.IsNaN(top)) top = 0;

        double width = GetCurrentWidth();
        double height = GetCurrentHeight();
        double right = left + width;
        double bottom = top + height;

        double canvasWidth = canvas.ActualWidth > 0 ? canvas.ActualWidth : double.MaxValue;
        double canvasHeight = canvas.ActualHeight > 0 ? canvas.ActualHeight : double.MaxValue;

        if (direction.Contains('W'))
        {
            double maxLeft = Math.Max(0, right - MinWidth);
            double nextLeft = Math.Clamp(left + e.HorizontalChange, 0, maxLeft);
            width = right - nextLeft;
            left = nextLeft;
        }
        else if (direction.Contains('E'))
        {
            double minRight = left + MinWidth;
            double maxRight = Math.Max(minRight, canvasWidth);
            double nextRight = Math.Clamp(right + e.HorizontalChange, minRight, maxRight);
            width = nextRight - left;
        }

        if (direction.Contains('N'))
        {
            double maxTop = Math.Max(0, bottom - MinHeight);
            double nextTop = Math.Clamp(top + e.VerticalChange, 0, maxTop);
            height = bottom - nextTop;
            top = nextTop;
        }
        else if (direction.Contains('S'))
        {
            double minBottom = top + MinHeight;
            double maxBottom = Math.Max(minBottom, canvasHeight);
            double nextBottom = Math.Clamp(bottom + e.VerticalChange, minBottom, maxBottom);
            height = nextBottom - top;
        }

        Width = Math.Max(MinWidth, width);
        Height = Math.Max(MinHeight, height);
        Canvas.SetLeft(this, left);
        Canvas.SetTop(this, top);

        e.Handled = true;
    }

    private double GetCurrentWidth()
    {
        if (ActualWidth > 0) return ActualWidth;
        if (!double.IsNaN(Width) && Width > 0) return Width;
        return Math.Max(MinWidth, 240);
    }

    private double GetCurrentHeight()
    {
        if (ActualHeight > 0) return ActualHeight;
        if (!double.IsNaN(Height) && Height > 0) return Height;
        return Math.Max(MinHeight, 180);
    }

    private double _scale = 1.0;

    private void BtnZoomIn_Click(object sender, RoutedEventArgs e)
    {
        if (!_canZoom) return;

        if (_scale < 2.0)
        {
            _scale = Math.Round(_scale + 0.1, 1);
            ApplyScale();
        }
    }

    private void BtnZoomOut_Click(object sender, RoutedEventArgs e)
    {
        if (!_canZoom) return;

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
        DisposeContent();
        Closed?.Invoke(this);
    }
}
