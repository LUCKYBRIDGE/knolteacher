using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;

namespace KnolTeacher.Desktop.Views.Controls;

public class MainWidgetCard : ContentControl
{
    private static int _globalZIndex = 10;

    public static readonly DependencyProperty WidgetIdProperty =
        DependencyProperty.Register(nameof(WidgetId), typeof(string), typeof(MainWidgetCard), new PropertyMetadata(string.Empty));

    public static readonly DependencyProperty TitleProperty =
        DependencyProperty.Register(nameof(Title), typeof(string), typeof(MainWidgetCard), new PropertyMetadata("위젯 창"));

    public static readonly DependencyProperty IconProperty =
        DependencyProperty.Register(nameof(Icon), typeof(string), typeof(MainWidgetCard), new PropertyMetadata("📌"));

    public static readonly DependencyProperty IsLockedProperty =
        DependencyProperty.Register(nameof(IsLocked), typeof(bool), typeof(MainWidgetCard), new PropertyMetadata(false, OnIsLockedChanged));

    public static readonly DependencyProperty DefaultWidthProperty =
        DependencyProperty.Register(nameof(DefaultWidth), typeof(double), typeof(MainWidgetCard), new PropertyMetadata(320.0));

    public static readonly DependencyProperty DefaultHeightProperty =
        DependencyProperty.Register(nameof(DefaultHeight), typeof(double), typeof(MainWidgetCard), new PropertyMetadata(400.0));

    public string WidgetId
    {
        get => (string)GetValue(WidgetIdProperty);
        set => SetValue(WidgetIdProperty, value);
    }

    public string Title
    {
        get => (string)GetValue(TitleProperty);
        set => SetValue(TitleProperty, value);
    }

    public string Icon
    {
        get => (string)GetValue(IconProperty);
        set => SetValue(IconProperty, value);
    }

    public bool IsLocked
    {
        get => (bool)GetValue(IsLockedProperty);
        set => SetValue(IsLockedProperty, value);
    }

    public double DefaultWidth
    {
        get => (double)GetValue(DefaultWidthProperty);
        set => SetValue(DefaultWidthProperty, value);
    }

    public double DefaultHeight
    {
        get => (double)GetValue(DefaultHeightProperty);
        set => SetValue(DefaultHeightProperty, value);
    }

    public event Action<MainWidgetCard>? Closed;
    public event Action<MainWidgetCard>? Moved;
    public event Action<MainWidgetCard>? Resized;

    private bool _isDragging = false;
    private Point _dragStartPoint;
    private double _prevNormalWidth = 320;
    private double _prevNormalHeight = 400;
    private bool _isExpanded = false;

    private FrameworkElement? _headerBar;
    private Thumb? _resizeThumb;
    private Button? _btnToggleSize;
    private Button? _btnClose;
    private FrameworkElement? _lockIcon;
    private FrameworkElement? _dragGrip;

    public MainWidgetCard()
    {
        Loaded += (s, e) =>
        {
            if (double.IsNaN(Width) || Width <= 0) Width = DefaultWidth;
            if (double.IsNaN(Height) || Height <= 0) Height = DefaultHeight;
        };
        MouseDown += (s, e) => BringToFront();
    }

    public override void OnApplyTemplate()
    {
        base.OnApplyTemplate();

        _headerBar = GetTemplateChild("PART_HeaderBar") as FrameworkElement;
        _resizeThumb = GetTemplateChild("PART_ResizeThumb") as Thumb;
        _btnToggleSize = GetTemplateChild("PART_BtnToggleSize") as Button;
        _btnClose = GetTemplateChild("PART_BtnClose") as Button;
        _lockIcon = GetTemplateChild("PART_LockIcon") as FrameworkElement;
        _dragGrip = GetTemplateChild("PART_DragGrip") as FrameworkElement;

        if (_headerBar != null)
        {
            _headerBar.MouseLeftButtonDown += HeaderBar_MouseLeftButtonDown;
            _headerBar.MouseMove += HeaderBar_MouseMove;
            _headerBar.MouseLeftButtonUp += HeaderBar_MouseLeftButtonUp;
        }

        if (_resizeThumb != null)
        {
            _resizeThumb.DragDelta += ResizeThumb_DragDelta;
        }

        if (_btnToggleSize != null)
        {
            _btnToggleSize.Click += (s, e) =>
            {
                if (IsLocked) return;
                ToggleSize();
            };
        }

        if (_btnClose != null)
        {
            _btnClose.Click += (s, e) =>
            {
                Visibility = Visibility.Collapsed;
                Closed?.Invoke(this);
            };
        }

        UpdateLockVisuals();
    }

    private static void OnIsLockedChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
    {
        if (d is MainWidgetCard card)
        {
            card.UpdateLockVisuals();
        }
    }

    private void UpdateLockVisuals()
    {
        if (_headerBar != null) _headerBar.Cursor = IsLocked ? Cursors.Arrow : Cursors.SizeAll;
        if (_resizeThumb != null) _resizeThumb.Visibility = IsLocked ? Visibility.Collapsed : Visibility.Visible;
        if (_lockIcon != null) _lockIcon.Visibility = IsLocked ? Visibility.Visible : Visibility.Collapsed;
        if (_dragGrip != null) _dragGrip.Visibility = IsLocked ? Visibility.Collapsed : Visibility.Visible;
        if (_btnToggleSize != null) _btnToggleSize.IsEnabled = !IsLocked;
    }

    public void BringToFront()
    {
        Panel.SetZIndex(this, ++_globalZIndex);
    }

    private void HeaderBar_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        BringToFront();
        if (IsLocked) return;

        if (e.ClickCount == 2)
        {
            ToggleSize();
            e.Handled = true;
            return;
        }

        if (VisualParent is Canvas)
        {
            _isDragging = true;
            _dragStartPoint = e.GetPosition(this);
            _headerBar?.CaptureMouse();
            e.Handled = true;
        }
    }

    private void HeaderBar_MouseMove(object sender, MouseEventArgs e)
    {
        if (_isDragging && VisualParent is Canvas canvas)
        {
            Point currentPos = e.GetPosition(canvas);
            double newLeft = currentPos.X - _dragStartPoint.X;
            double newTop = currentPos.Y - _dragStartPoint.Y;

            double maxLeft = Math.Max(0, canvas.ActualWidth - ActualWidth);
            double maxTop = Math.Max(0, canvas.ActualHeight - ActualHeight);

            newLeft = Math.Max(0, Math.Min(newLeft, maxLeft));
            newTop = Math.Max(0, Math.Min(newTop, maxTop));

            Canvas.SetLeft(this, newLeft);
            Canvas.SetTop(this, newTop);
            e.Handled = true;
        }
    }

    private void HeaderBar_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
    {
        if (_isDragging)
        {
            _isDragging = false;
            _headerBar?.ReleaseMouseCapture();
            e.Handled = true;
            Moved?.Invoke(this);
        }
    }

    private void ResizeThumb_DragDelta(object sender, DragDeltaEventArgs e)
    {
        if (IsLocked) return;
        BringToFront();

        double currentW = ActualWidth > 0 ? ActualWidth : Width;
        double currentH = ActualHeight > 0 ? ActualHeight : Height;

        double newWidth = Math.Max(MinWidth, currentW + e.HorizontalChange);
        double newHeight = Math.Max(MinHeight, currentH + e.VerticalChange);

        Width = newWidth;
        Height = newHeight;

        e.Handled = true;
        Resized?.Invoke(this);
    }

    public void ToggleSize()
    {
        BringToFront();
        if (!_isExpanded)
        {
            _prevNormalWidth = ActualWidth > 0 ? ActualWidth : Width;
            _prevNormalHeight = ActualHeight > 0 ? ActualHeight : Height;

            double targetW = Math.Max(MinWidth, _prevNormalWidth * 1.25);
            double targetH = Math.Max(MinHeight, _prevNormalHeight * 1.2);

            if (VisualParent is Canvas canvas)
            {
                targetW = Math.Min(targetW, canvas.ActualWidth > 0 ? canvas.ActualWidth : targetW);
                targetH = Math.Min(targetH, canvas.ActualHeight > 0 ? canvas.ActualHeight : targetH);

                double left = Canvas.GetLeft(this);
                double top = Canvas.GetTop(this);
                if (canvas.ActualWidth > 0 && left + targetW > canvas.ActualWidth)
                    Canvas.SetLeft(this, Math.Max(0, canvas.ActualWidth - targetW));
                if (canvas.ActualHeight > 0 && top + targetH > canvas.ActualHeight)
                    Canvas.SetTop(this, Math.Max(0, canvas.ActualHeight - targetH));
            }

            Width = targetW;
            Height = targetH;
            _isExpanded = true;
        }
        else
        {
            Width = Math.Max(MinWidth, _prevNormalWidth);
            Height = Math.Max(MinHeight, _prevNormalHeight);
            _isExpanded = false;
        }
        Resized?.Invoke(this);
    }
}
