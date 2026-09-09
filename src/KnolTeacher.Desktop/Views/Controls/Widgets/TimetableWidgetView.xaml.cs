using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.Views.Controls;
using KnolTeacher.Desktop.Views.Windows;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class TimetableWidgetView : UserControl, IWidgetLifecycle
{
    private readonly ITimetableService? _timetableService;
    private bool _isActive = false;
    private bool _disposed = false;

    public TimetableWidgetView(ITimetableService? timetableService = null)
    {
        _timetableService = timetableService;
        InitializeComponent();
    }

    public void Activate()
    {
        if (_disposed || _isActive) return;

        _isActive = true;
        if (_timetableService != null)
        {
            _timetableService.OnTimetableChanged += HandleTimetableChanged;
        }
        RefreshData();
    }

    public void Deactivate()
    {
        if (_disposed || !_isActive) return;

        if (_timetableService != null)
        {
            _timetableService.OnTimetableChanged -= HandleTimetableChanged;
        }
        _isActive = false;
    }

    public void Dispose()
    {
        if (_disposed) return;

        Deactivate();
        if (_timetableService != null)
        {
            _timetableService.OnTimetableChanged -= HandleTimetableChanged;
        }
        _disposed = true;
    }

    private void HandleTimetableChanged()
    {
        if (_disposed || !_isActive) return;

        _ = Dispatcher.BeginInvoke(() =>
        {
            if (!_disposed && _isActive)
            {
                RefreshData();
            }
        });
    }

    public void RefreshData()
    {
        if (_timetableService != null)
        {
            ListItems.ItemsSource = null;
            ListItems.ItemsSource = _timetableService.GetTodaySchedule();
        }
    }

    private PeriodItem? GetPeriodItemFromMenuItem(object sender)
    {
        if (sender is MenuItem menuItem)
        {
            DependencyObject current = menuItem;
            while (current != null)
            {
                if (current is ContextMenu cm)
                {
                    if (cm.PlacementTarget is FrameworkElement fe && fe.DataContext is PeriodItem item)
                    {
                        return item;
                    }
                    break;
                }
                current = LogicalTreeHelper.GetParent(current) ?? VisualTreeHelper.GetParent(current);
            }
        }
        return null;
    }

    private void MenuEditSubject_Click(object sender, RoutedEventArgs e)
    {
        var item = GetPeriodItemFromMenuItem(sender);
        if (item != null && !item.IsLunch)
        {
            var win = Window.GetWindow(this);
            var dlg = new PromptInputDialog($"{item.Name} 과목 수정", $"{item.Name} 과목명을 입력하세요:\n(메인 창의 시간표에도 실시간 반영됩니다)", item.Subject)
            {
                Owner = win
            };

            if (dlg.ShowDialog() == true && !string.IsNullOrWhiteSpace(dlg.InputText))
            {
                _timetableService?.UpdateTodayPeriodSubject(item.Period - 1, dlg.InputText, item.Tag);
                RefreshData();
                HudNotificationWindow.Instance.ShowToast("✏️", $"{item.Name} 과목이 '{dlg.InputText}'(으)로 변경되었습니다.");
            }
        }
    }

    private void MenuQuickSubject_Click(object sender, RoutedEventArgs e)
    {
        if (sender is MenuItem mi && mi.Tag is string subject && !string.IsNullOrWhiteSpace(subject))
        {
            var item = GetPeriodItemFromMenuItem(sender);
            if (item != null && !item.IsLunch)
            {
                _timetableService?.UpdateTodayPeriodSubject(item.Period - 1, subject, item.Tag);
                RefreshData();
                HudNotificationWindow.Instance.ShowToast("📚", $"{item.Name} 과목이 '{subject}'(으)로 변경되었습니다.");
            }
        }
    }

    private void MenuQuickTag_Click(object sender, RoutedEventArgs e)
    {
        if (sender is MenuItem mi && mi.Tag is string tag)
        {
            var item = GetPeriodItemFromMenuItem(sender);
            if (item != null && !item.IsLunch)
            {
                _timetableService?.UpdateTodayPeriodSubject(item.Period - 1, item.Subject, tag);
                RefreshData();
                string tagMsg = string.IsNullOrWhiteSpace(tag) ? "태그가 해제되었습니다." : $"'{tag}' 태그로 설정되었습니다.";
                HudNotificationWindow.Instance.ShowToast("🏷️", $"{item.Name} {tagMsg}");
            }
        }
    }

    private void MenuClearSubject_Click(object sender, RoutedEventArgs e)
    {
        var item = GetPeriodItemFromMenuItem(sender);
        if (item != null && !item.IsLunch)
        {
            _timetableService?.UpdateTodayPeriodSubject(item.Period - 1, "-", "");
            RefreshData();
            HudNotificationWindow.Instance.ShowToast("🧹", $"{item.Name} 과목이 비워졌습니다.");
        }
    }

    private void BtnEdit_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement fe && fe.Tag is PeriodItem item && !item.IsLunch)
        {
            var win = Window.GetWindow(this);
            var dlg = new PromptInputDialog($"{item.Name} 과목 수정", $"{item.Name} 과목명을 입력하세요:\n(메인 창의 시간표에도 실시간 반영됩니다)", item.Subject)
            {
                Owner = win
            };

            if (dlg.ShowDialog() == true && !string.IsNullOrWhiteSpace(dlg.InputText))
            {
                _timetableService?.UpdateTodayPeriodSubject(item.Period - 1, dlg.InputText, item.Tag);
                RefreshData();
                HudNotificationWindow.Instance.ShowToast("✏️", $"{item.Name} 과목이 '{dlg.InputText}'(으)로 변경되었습니다.");
            }
        }
    }
}
