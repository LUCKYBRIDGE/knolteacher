using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class StudentDisplayWindow
{
    private static readonly bool V309WidgetUxRegistered = RegisterV309WidgetUx();
    private bool _v309WidgetUxApplied;
    private PopupLaunchPreferences? _v309PopupLaunchPreferences;

    private static bool RegisterV309WidgetUx()
    {
        EventManager.RegisterClassHandler(
            typeof(StudentDisplayWindow),
            FrameworkElement.LoadedEvent,
            new RoutedEventHandler(StudentDisplayWindowV309_Loaded),
            handledEventsToo: true);

        // Existing widget-state code updates button colors after open/close. Refresh our
        // popup-vs-widget visual contract after routed button clicks so the distinction
        // remains visible for the whole session, not only immediately after startup.
        EventManager.RegisterClassHandler(
            typeof(StudentDisplayWindow),
            Button.ClickEvent,
            new RoutedEventHandler(StudentDisplayWindowV309_ButtonClick),
            handledEventsToo: true);

        return true;
    }

    private static void StudentDisplayWindowV309_Loaded(object sender, RoutedEventArgs e)
    {
        if (sender is not StudentDisplayWindow window) return;

        window.InitializeV309WidgetUx();
        _ = window.Dispatcher.BeginInvoke(
            DispatcherPriority.ContextIdle,
            new Action(window.RefreshV309LauncherVisuals));
    }

    private static void StudentDisplayWindowV309_ButtonClick(object sender, RoutedEventArgs e)
    {
        if (sender is not StudentDisplayWindow window || !window._v309WidgetUxApplied) return;

        _ = window.Dispatcher.BeginInvoke(
            DispatcherPriority.ContextIdle,
            new Action(window.RefreshV309LauncherVisuals));
    }

    private void InitializeV309WidgetUx()
    {
        if (_v309WidgetUxApplied) return;
        _v309WidgetUxApplied = true;

        _v309PopupLaunchPreferences = new PopupLaunchPreferences(_configService.ConfigDir);

        // Pinball is not a board widget: it resolves to StudentPickerWindow. Keeping it in
        // the "+ 위젯" combo was the clearest source of user confusion, so remove it there
        // and leave the dedicated dock button as an explicit separate-window launcher.
        for (int i = CbAddWidget.Items.Count - 1; i >= 0; i--)
        {
            if (CbAddWidget.Items[i] is ComboBoxItem item &&
                string.Equals(item.Tag?.ToString(), "pinball", StringComparison.OrdinalIgnoreCase))
            {
                CbAddWidget.Items.RemoveAt(i);
            }
        }

        BtnToolPinball.Click -= DockToolBtn_Click;
        BtnToolPinball.Click += BtnPinballWindow_Click;
        BtnToolPinball.MouseRightButtonUp += BtnPinballWindow_MouseRightButtonUp;

        RefreshV309LauncherVisuals();
    }

    private void RefreshV309LauncherVisuals()
    {
        if (!_v309WidgetUxApplied) return;
        if (FindResource("BoardNavButtonStyle") is not Style baseStyle) return;

        Brush widgetIdleBackground = BrushFrom("#17313A");
        Brush widgetIdleBorder = BrushFrom("#2F5B66");
        Brush widgetIdleForeground = BrushFrom("#D6EEF2");
        Brush widgetActiveBackground = BrushFrom("#0F766E");
        Brush widgetActiveBorder = BrushFrom("#5EEAD4");

        // These are the actual in-canvas widgets registered by WidgetRegistry.
        Button[] widgetButtons =
        {
            BtnToolTimer,
            BtnToolPicker,
            BtnToolDice,
            BtnToolWheel,
            BtnToolScore,
            BtnToolDrawing,
            BtnToolTimetable,
            BtnToolMeal,
            BtnToolMemo,
            BtnToolChecklist,
            BtnToolQr,
            BtnToolWeather,
            BtnToolDDay
        };

        foreach (Button button in widgetButtons)
        {
            bool active = button.Tag is string tag && FindWidget(tag) != null;
            button.Style = baseStyle;
            button.Background = active ? widgetActiveBackground : widgetIdleBackground;
            button.BorderBrush = active ? widgetActiveBorder : widgetIdleBorder;
            button.Foreground = active ? Brushes.White : widgetIdleForeground;
            button.BorderThickness = new Thickness(active ? 1.5 : 1.0);
            button.FontWeight = active ? FontWeights.Bold : FontWeights.SemiBold;

            string existing = button.ToolTip?.ToString() ?? string.Empty;
            if (!existing.StartsWith("위젯 ·", StringComparison.Ordinal))
            {
                button.ToolTip = string.IsNullOrWhiteSpace(existing)
                    ? "위젯 · 놀보드 안에 열립니다."
                    : $"위젯 · {existing}";
            }
        }

        // Pinball is deliberately styled like an ordinary window tool rather than a widget.
        bool pinballVisible = _pinballWindow?.IsVisible == true;
        BtnToolPinball.Style = baseStyle;
        BtnToolPinball.Background = BrushFrom(pinballVisible ? "#334155" : "#1E293B");
        BtnToolPinball.BorderBrush = BrushFrom(pinballVisible ? "#93C5FD" : "#475569");
        BtnToolPinball.Foreground = pinballVisible ? Brushes.White : BrushFrom("#CBD5E1");
        BtnToolPinball.BorderThickness = new Thickness(pinballVisible ? 1.5 : 1.0);
        BtnToolPinball.FontWeight = pinballVisible ? FontWeights.Bold : FontWeights.SemiBold;
        BtnToolPinball.ToolTip = "별도 창 도구 · 왼클릭은 모니터 1, 우클릭은 모니터 2에서 엽니다.";

        CbAddWidget.Background = BrushFrom("#132A32");
        CbAddWidget.Foreground = widgetIdleForeground;
        CbAddWidget.BorderBrush = widgetIdleBorder;
        CbAddWidget.ToolTip = "이 목록의 도구는 별도 팝업이 아니라 놀보드 안의 위젯으로 열립니다.";
    }

    private void BtnPinballWindow_Click(object sender, RoutedEventArgs e)
    {
        OpenPinballOnMonitor(0);
        e.Handled = true;
    }

    private void BtnPinballWindow_MouseRightButtonUp(object sender, MouseButtonEventArgs e)
    {
        _v309PopupLaunchPreferences ??= new PopupLaunchPreferences(_configService.ConfigDir);
        if (!_v309PopupLaunchPreferences.RightClickOpensOnSecondMonitor)
        {
            return;
        }

        int targetMonitor = _displayManager?.IsDualMonitor == true ? 1 : 0;
        OpenPinballOnMonitor(targetMonitor);
        e.Handled = true;
    }

    private void OpenPinballOnMonitor(int monitorIndex)
    {
        var app = Application.Current as App;
        var resolved = app?.Services?.GetService(typeof(StudentPickerWindow)) as StudentPickerWindow;
        if (resolved != null)
        {
            _pinballWindow = resolved;
        }
        else if (_pinballWindow == null)
        {
            _pinballWindow = new StudentPickerWindow(_studentService, _soundService, _displayManager);
        }

        if (_pinballWindow == null) return;

        if (_displayManager != null)
        {
            _displayManager.MoveWindowToScreen(_pinballWindow, monitorIndex, maximize: false);
        }

        _pinballWindow.Show();
        _pinballWindow.Activate();
        RefreshV309LauncherVisuals();
    }

    private static SolidColorBrush BrushFrom(string hex)
        => new((Color)ColorConverter.ConvertFromString(hex));
}
