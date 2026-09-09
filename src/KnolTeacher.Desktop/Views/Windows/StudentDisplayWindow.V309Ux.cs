using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class StudentDisplayWindow
{
    private static readonly bool V309WidgetUxRegistered = RegisterV309WidgetUx();
    private bool _v309WidgetUxApplied;

    private static bool RegisterV309WidgetUx()
    {
        EventManager.RegisterClassHandler(
            typeof(StudentDisplayWindow),
            FrameworkElement.LoadedEvent,
            new RoutedEventHandler(StudentDisplayWindowV309_Loaded),
            handledEventsToo: true);
        return true;
    }

    private static void StudentDisplayWindowV309_Loaded(object sender, RoutedEventArgs e)
    {
        if (sender is StudentDisplayWindow window)
        {
            window.ApplyV309WidgetLauncherVisuals();
        }
    }

    private void ApplyV309WidgetLauncherVisuals()
    {
        if (_v309WidgetUxApplied) return;
        _v309WidgetUxApplied = true;

        if (FindResource("BoardNavButtonStyle") is not Style baseStyle) return;

        // Deliberately subtle teal/slate tint: different enough to communicate
        // "this opens inside NolBoard", but not bright enough to compete with lesson content.
        var widgetStyle = new Style(typeof(Button), baseStyle);
        widgetStyle.Setters.Add(new Setter(Button.BackgroundProperty,
            new SolidColorBrush(Color.FromRgb(23, 49, 58))));
        widgetStyle.Setters.Add(new Setter(Button.BorderBrushProperty,
            new SolidColorBrush(Color.FromRgb(47, 91, 102))));
        widgetStyle.Setters.Add(new Setter(Button.ForegroundProperty,
            new SolidColorBrush(Color.FromRgb(214, 238, 242))));

        Button[] widgetButtons =
        {
            BtnToolTimer,
            BtnToolPinball,
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
            button.Style = widgetStyle;
            string existing = button.ToolTip?.ToString() ?? string.Empty;
            button.ToolTip = string.IsNullOrWhiteSpace(existing)
                ? "놀보드 안에 위젯으로 열립니다."
                : $"위젯 · {existing}";
        }

        CbAddWidget.Background = new SolidColorBrush(Color.FromRgb(19, 42, 50));
        CbAddWidget.Foreground = new SolidColorBrush(Color.FromRgb(214, 238, 242));
        CbAddWidget.BorderBrush = new SolidColorBrush(Color.FromRgb(47, 91, 102));
        CbAddWidget.ToolTip = "선택한 도구는 별도 팝업이 아니라 놀보드 안의 위젯으로 열립니다.";
    }
}
