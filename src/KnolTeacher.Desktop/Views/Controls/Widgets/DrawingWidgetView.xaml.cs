using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Ink;
using System.Windows.Media;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class DrawingWidgetView : UserControl
{
    private readonly Stack<Stroke> _undoStack = new();
    private bool _isReady = false;

    public DrawingWidgetView()
    {
        InitializeComponent();
        MiniInkCanvas.DefaultDrawingAttributes = new DrawingAttributes
        {
            Color = Colors.White,
            Width = 3,
            Height = 3,
            FitToCurve = true
        };

        MiniInkCanvas.StrokeCollected += (s, e) => _undoStack.Clear();
        _isReady = true;
    }

    private void BtnModeGreen_Click(object sender, RoutedEventArgs e)
    {
        InkBorder.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1B4332"));
        MiniInkCanvas.DefaultDrawingAttributes.Color = Colors.White;
    }

    private void BtnModeWhite_Click(object sender, RoutedEventArgs e)
    {
        InkBorder.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F8F9FA"));
        MiniInkCanvas.DefaultDrawingAttributes.Color = (Color)ColorConverter.ConvertFromString("#0F172A");
    }

    private void RbPen_Checked(object sender, RoutedEventArgs e)
    {
        if (!_isReady || MiniInkCanvas == null) return;
        MiniInkCanvas.EditingMode = InkCanvasEditingMode.Ink;
    }

    private void RbEraser_Checked(object sender, RoutedEventArgs e)
    {
        if (!_isReady || MiniInkCanvas == null) return;
        MiniInkCanvas.EditingMode = InkCanvasEditingMode.EraseByStroke;
    }

    private void BtnColor_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string hex)
        {
            var color = (Color)ColorConverter.ConvertFromString(hex);
            MiniInkCanvas.DefaultDrawingAttributes.Color = color;
            if (RbEraser.IsChecked == true)
            {
                RbPen.IsChecked = true;
            }
        }
    }

    private void BtnUndo_Click(object sender, RoutedEventArgs e)
    {
        if (MiniInkCanvas.Strokes.Count > 0)
        {
            var last = MiniInkCanvas.Strokes[^1];
            _undoStack.Push(last);
            MiniInkCanvas.Strokes.Remove(last);
        }
    }

    private void BtnClear_Click(object sender, RoutedEventArgs e)
    {
        if (MiniInkCanvas.Strokes.Count > 0)
        {
            MiniInkCanvas.Strokes.Clear();
            _undoStack.Clear();
        }
    }
}
