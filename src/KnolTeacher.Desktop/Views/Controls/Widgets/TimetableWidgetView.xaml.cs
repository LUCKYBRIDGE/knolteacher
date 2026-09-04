using System.Windows;
using System.Windows.Controls;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.Views.Windows;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class TimetableWidgetView : UserControl
{
    private readonly ITimetableService? _timetableService;

    public TimetableWidgetView(ITimetableService? timetableService = null)
    {
        _timetableService = timetableService;
        InitializeComponent();
        Loaded += (s, e) => RefreshData();

        if (_timetableService != null)
        {
            _timetableService.OnTimetableChanged += () => Dispatcher.Invoke(RefreshData);
        }
    }

    public void RefreshData()
    {
        if (_timetableService != null)
        {
            ListItems.ItemsSource = null;
            ListItems.ItemsSource = _timetableService.GetTodaySchedule();
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
