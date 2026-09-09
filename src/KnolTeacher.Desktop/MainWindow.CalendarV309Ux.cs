using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;

namespace KnolTeacher.Desktop;

public partial class MainWindow
{
    private static readonly bool V309CalendarUxRegistered = RegisterV309CalendarUx();
    private bool _v309CalendarUxInitialized;

    private static bool RegisterV309CalendarUx()
    {
        EventManager.RegisterClassHandler(
            typeof(MainWindow),
            FrameworkElement.LoadedEvent,
            new RoutedEventHandler(MainWindowV309Calendar_Loaded),
            handledEventsToo: true);
        return true;
    }

    private static void MainWindowV309Calendar_Loaded(object sender, RoutedEventArgs e)
    {
        if (sender is MainWindow window)
        {
            window.InitializeV309CalendarUx();
        }
    }

    private void InitializeV309CalendarUx()
    {
        if (_v309CalendarUxInitialized) return;
        _v309CalendarUxInitialized = true;

        BtnAddCalendarEvent.Content = "➕ 새 일정";
        BtnAddCalendarEvent.ToolTip = "현재 선택한 날짜에 새 일정을 등록합니다.";
        BtnToggleScheduleDrawer.ToolTip = "선택한 날짜의 일정 목록을 열거나 닫습니다.";

        NormalizeCalendarLabels();

        // Existing code still controls drawer state. Normalize only its legacy wording
        // after those handlers have updated the UI so no behavior is duplicated here.
        BtnToggleScheduleDrawer.Click += (_, _) =>
            _ = Dispatcher.BeginInvoke(DispatcherPriority.ContextIdle, new Action(NormalizeCalendarLabels));
        BtnCloseScheduleDrawer.Click += (_, _) =>
            _ = Dispatcher.BeginInvoke(DispatcherPriority.ContextIdle, new Action(NormalizeCalendarLabels));

        TxtToggleDrawerText.LayoutUpdated += (_, _) => NormalizeDrawerLabel();
        TxtSelectedDayTitle.LayoutUpdated += (_, _) => NormalizeSelectedDayTitle();
    }

    private void NormalizeCalendarLabels()
    {
        NormalizeDrawerLabel();
        NormalizeSelectedDayTitle();

        foreach (var button in FindCalendarVisualChildren<Button>(this))
        {
            if (button.Content is not string content) continue;

            if (content == "➕ 이 날짜에 일정·메모 추가")
            {
                button.Content = "➕ 이 날짜에 일정 추가";
                button.ToolTip = "선택한 날짜로 새 일정 등록 창을 엽니다.";
            }
        }

        foreach (var textBlock in FindCalendarVisualChildren<TextBlock>(this))
        {
            if (textBlock.Text == "선택한 날짜에 등록된 일정이나 메모가 없습니다.")
            {
                textBlock.Text = "선택한 날짜에 등록된 일정이 없습니다.";
            }
        }
    }

    private void NormalizeDrawerLabel()
    {
        if (TxtToggleDrawerText.Text == "일정·메모")
        {
            TxtToggleDrawerText.Text = "일정 보기";
        }
    }

    private void NormalizeSelectedDayTitle()
    {
        const string legacySuffix = " 일정 및 메모";
        if (TxtSelectedDayTitle.Text.EndsWith(legacySuffix, StringComparison.Ordinal))
        {
            TxtSelectedDayTitle.Text = TxtSelectedDayTitle.Text[..^legacySuffix.Length] + " 일정";
        }
    }

    private static IEnumerable<T> FindCalendarVisualChildren<T>(DependencyObject root) where T : DependencyObject
    {
        int count = VisualTreeHelper.GetChildrenCount(root);
        for (int i = 0; i < count; i++)
        {
            DependencyObject child = VisualTreeHelper.GetChild(root, i);
            if (child is T typed)
            {
                yield return typed;
            }

            foreach (var descendant in FindCalendarVisualChildren<T>(child))
            {
                yield return descendant;
            }
        }
    }
}
