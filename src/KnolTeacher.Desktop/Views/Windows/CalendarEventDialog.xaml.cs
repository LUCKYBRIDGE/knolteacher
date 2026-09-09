using System;
using System.Linq;
using System.Windows;
using System.Windows.Input;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class CalendarEventDialog : Window
{
    public TeacherCalendarEvent ResultEvent { get; private set; }
    public bool IsDeleted { get; private set; }

    private readonly (int offset, string label)[] _alarmOffsets =
    {
        (0, "정각"),
        (5, "5분 전"),
        (10, "10분 전"),
        (15, "15분 전"),
        (30, "30분 전"),
        (60, "1시간 전"),
        (1440, "1일 전 (오전 9시)")
    };

    public CalendarEventDialog(TeacherCalendarEvent? existingEvent = null, DateTime? defaultDate = null)
    {
        InitializeComponent();

        for (int h = 0; h < 24; h++)
        {
            CboHour.Items.Add($"{h:D2}");
        }

        for (int m = 0; m < 60; m += 5)
        {
            CboMinute.Items.Add($"{m:D2}");
        }

        foreach (var item in _alarmOffsets)
        {
            CboAlarmOffset.Items.Add(item.label);
        }

        if (existingEvent != null)
        {
            ResultEvent = new TeacherCalendarEvent
            {
                Id = existingEvent.Id,
                Date = existingEvent.Date,
                Title = existingEvent.Title,
                Memo = existingEvent.Memo,
                IsAllDay = existingEvent.IsAllDay,
                Time = existingEvent.Time,
                HasAlarm = existingEvent.HasAlarm,
                AlarmMinutesBefore = existingEvent.AlarmMinutesBefore,
                Color = existingEvent.Color,
                IsAlarmTriggered = existingEvent.IsAlarmTriggered
            };

            TxtHeaderTitle.Text = "일정 수정";
            BtnDelete.Visibility = Visibility.Visible;
            BtnSave.Content = "수정 저장";
        }
        else
        {
            string dateStr = (defaultDate ?? DateTime.Today).ToString("yyyy-MM-dd");
            ResultEvent = new TeacherCalendarEvent
            {
                Date = dateStr,
                Title = string.Empty,
                IsAllDay = true,
                Time = "10:00",
                HasAlarm = false,
                AlarmMinutesBefore = 10,
                Color = "#3B82F6"
            };

            TxtHeaderTitle.Text = "새 일정";
            BtnDelete.Visibility = Visibility.Collapsed;
            BtnSave.Content = "등록";
        }

        BindDataToUi();
        Loaded += (_, _) =>
        {
            TbTitle.Focus();
            if (!string.IsNullOrWhiteSpace(TbTitle.Text))
            {
                TbTitle.SelectAll();
            }
        };
    }

    private void BindDataToUi()
    {
        DpDate.SelectedDate = DateTime.TryParse(ResultEvent.Date, out var dt) ? dt : DateTime.Today;
        TbTitle.Text = ResultEvent.Title;
        TbMemo.Text = ResultEvent.Memo;

        ChkAllDay.IsChecked = ResultEvent.IsAllDay;
        PanelTime.Visibility = ResultEvent.IsAllDay ? Visibility.Collapsed : Visibility.Visible;

        string time = string.IsNullOrEmpty(ResultEvent.Time) ? "10:00" : ResultEvent.Time;
        var parts = time.Split(':');
        string hour = parts.Length > 0 ? parts[0].PadLeft(2, '0') : "10";
        string min = parts.Length > 1 ? parts[1].PadLeft(2, '0') : "00";

        CboHour.SelectedItem = CboHour.Items.Contains(hour) ? hour : "10";
        if (int.TryParse(min, out int mVal))
        {
            int roundedMin = (mVal / 5) * 5;
            string roundedMinStr = $"{roundedMin:D2}";
            CboMinute.SelectedItem = CboMinute.Items.Contains(roundedMinStr) ? roundedMinStr : "00";
        }
        else
        {
            CboMinute.SelectedIndex = 0;
        }

        ChkAlarm.IsChecked = ResultEvent.HasAlarm;
        PanelAlarmOffset.Visibility = ResultEvent.HasAlarm ? Visibility.Visible : Visibility.Collapsed;

        int offsetIdx = Array.FindIndex(_alarmOffsets, x => x.offset == ResultEvent.AlarmMinutesBefore);
        CboAlarmOffset.SelectedIndex = offsetIdx >= 0 ? offsetIdx : 2;

        switch (ResultEvent.Color)
        {
            case "#10B981": RbColorGreen.IsChecked = true; break;
            case "#F59E0B": RbColorOrange.IsChecked = true; break;
            case "#EF4444": RbColorRed.IsChecked = true; break;
            case "#8B5CF6": RbColorPurple.IsChecked = true; break;
            default: RbColorBlue.IsChecked = true; break;
        }
    }

    private void Window_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Escape)
        {
            DialogResult = false;
            Close();
            e.Handled = true;
            return;
        }

        if (e.Key == Key.Enter && Keyboard.Modifiers.HasFlag(ModifierKeys.Control))
        {
            SaveAndClose();
            e.Handled = true;
        }
    }

    private void ChkAllDay_CheckChanged(object sender, RoutedEventArgs e)
    {
        if (PanelTime == null) return;
        PanelTime.Visibility = ChkAllDay.IsChecked == true ? Visibility.Collapsed : Visibility.Visible;
    }

    private void ChkAlarm_CheckChanged(object sender, RoutedEventArgs e)
    {
        if (PanelAlarmOffset == null) return;
        PanelAlarmOffset.Visibility = ChkAlarm.IsChecked == true ? Visibility.Visible : Visibility.Collapsed;
    }

    private void BtnCancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }

    private void BtnDelete_Click(object sender, RoutedEventArgs e)
    {
        var ans = MessageBox.Show($"'{ResultEvent.Title}' 일정을 정말 삭제하시겠습니까?", "일정 삭제", MessageBoxButton.YesNo, MessageBoxImage.Question);
        if (ans == MessageBoxResult.Yes)
        {
            IsDeleted = true;
            DialogResult = true;
            Close();
        }
    }

    private void BtnSave_Click(object sender, RoutedEventArgs e) => SaveAndClose();

    private void SaveAndClose()
    {
        string title = TbTitle.Text.Trim();
        if (string.IsNullOrEmpty(title))
        {
            MessageBox.Show("일정 제목을 입력해 주세요.", "입력 확인", MessageBoxButton.OK, MessageBoxImage.Warning);
            TbTitle.Focus();
            return;
        }

        DateTime targetDate = DpDate.SelectedDate ?? DateTime.Today;
        ResultEvent.Date = targetDate.ToString("yyyy-MM-dd");
        ResultEvent.Title = title;
        ResultEvent.Memo = TbMemo.Text.Trim();
        ResultEvent.IsAllDay = ChkAllDay.IsChecked == true;

        if (!ResultEvent.IsAllDay)
        {
            string h = CboHour.SelectedItem?.ToString() ?? "10";
            string m = CboMinute.SelectedItem?.ToString() ?? "00";
            ResultEvent.Time = $"{h}:{m}";
        }
        else
        {
            ResultEvent.Time = "09:00";
        }

        ResultEvent.HasAlarm = ChkAlarm.IsChecked == true;
        if (ResultEvent.HasAlarm && CboAlarmOffset.SelectedIndex >= 0 && CboAlarmOffset.SelectedIndex < _alarmOffsets.Length)
        {
            ResultEvent.AlarmMinutesBefore = _alarmOffsets[CboAlarmOffset.SelectedIndex].offset;
        }
        else
        {
            ResultEvent.AlarmMinutesBefore = 10;
        }

        if (RbColorGreen.IsChecked == true) ResultEvent.Color = "#10B981";
        else if (RbColorOrange.IsChecked == true) ResultEvent.Color = "#F59E0B";
        else if (RbColorRed.IsChecked == true) ResultEvent.Color = "#EF4444";
        else if (RbColorPurple.IsChecked == true) ResultEvent.Color = "#8B5CF6";
        else ResultEvent.Color = "#3B82F6";

        ResultEvent.IsAlarmTriggered = false;
        DialogResult = true;
        Close();
    }
}
