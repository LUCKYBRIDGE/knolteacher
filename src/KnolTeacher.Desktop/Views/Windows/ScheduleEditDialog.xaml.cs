using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class ScheduleEditDialog : Window
{
    public RecurringScheduleItem? ResultItem { get; private set; }
    private readonly RecurringScheduleItem? _originalItem;

    public ScheduleEditDialog(RecurringScheduleItem? item = null)
    {
        _originalItem = item;
        InitializeComponent();

        // Fill hours (01~12)
        for (int h = 1; h <= 12; h++)
        {
            CbHour.Items.Add($"{h:D2}시");
        }
        CbHour.SelectedIndex = 8; // default 09시

        // Fill minutes (00~55, step 5)
        for (int m = 0; m < 60; m += 5)
        {
            CbMinute.Items.Add($"{m:D2}분");
        }
        CbMinute.SelectedIndex = 0; // default 00분

        DpDate.SelectedDate = DateTime.Today;

        if (_originalItem != null)
        {
            TbTitle.Text = _originalItem.Title;
            TbMemo.Text = _originalItem.Memo;
            ChkSkipHolidays.IsChecked = _originalItem.SkipHolidays;

            CbAmPm.SelectedIndex = _originalItem.AmPm == "오후" ? 1 : 0;
            CbHour.SelectedIndex = Math.Clamp(_originalItem.Hour12 - 1, 0, 11);
            CbMinute.SelectedIndex = Math.Clamp(_originalItem.Minute / 5, 0, 11);

            if (_originalItem.IsSingle)
            {
                RbSingle.IsChecked = true;
                if (DateTime.TryParse(_originalItem.TargetDate, out var dt))
                {
                    DpDate.SelectedDate = dt;
                }
            }
            else
            {
                RbRecurring.IsChecked = true;
            }

            foreach (ComboBoxItem ci in CbActionType.Items)
            {
                if (ci.Tag is string tag && tag == _originalItem.ActionType)
                {
                    ci.IsSelected = true;
                    break;
                }
            }

            var days = _originalItem.RepeatDays ?? new();
            ChkMon.IsChecked = days.Contains(0);
            ChkTue.IsChecked = days.Contains(1);
            ChkWed.IsChecked = days.Contains(2);
            ChkThu.IsChecked = days.Contains(3);
            ChkFri.IsChecked = days.Contains(4);
            ChkSat.IsChecked = days.Contains(5);
            ChkSun.IsChecked = days.Contains(6);
        }
        else
        {
            TbTitle.Text = "새로운 예약";
        }
    }

    private void RbScheduleType_Changed(object sender, RoutedEventArgs e)
    {
        if (PanelSingleDate == null || PanelRecurringDays == null) return;

        bool isSingle = RbSingle.IsChecked == true;
        PanelSingleDate.Visibility = isSingle ? Visibility.Visible : Visibility.Collapsed;
        PanelRecurringDays.Visibility = isSingle ? Visibility.Collapsed : Visibility.Visible;
    }

    private void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        string title = TbTitle.Text.Trim();
        if (string.IsNullOrEmpty(title))
        {
            MessageBox.Show("예약 제목을 입력해 주세요.", "입력 확인", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        string actionType = "alarm";
        if (CbActionType.SelectedItem is ComboBoxItem selAction && selAction.Tag is string actTag)
        {
            actionType = actTag;
        }

        string ampm = CbAmPm.SelectedIndex == 1 ? "오후" : "오전";
        int hour12 = CbHour.SelectedIndex + 1;
        int minute = CbMinute.SelectedIndex * 5;

        int hour24 = hour12;
        if (ampm == "오후" && hour12 < 12) hour24 += 12;
        if (ampm == "오전" && hour12 == 12) hour24 = 0;

        string timeStr = $"{hour24:D2}:{minute:D2}";
        bool isSingle = RbSingle.IsChecked == true;

        var days = new List<int>();
        if (!isSingle)
        {
            if (ChkMon.IsChecked == true) days.Add(0);
            if (ChkTue.IsChecked == true) days.Add(1);
            if (ChkWed.IsChecked == true) days.Add(2);
            if (ChkThu.IsChecked == true) days.Add(3);
            if (ChkFri.IsChecked == true) days.Add(4);
            if (ChkSat.IsChecked == true) days.Add(5);
            if (ChkSun.IsChecked == true) days.Add(6);

            if (days.Count == 0)
            {
                MessageBox.Show("최소 하나 이상의 반복 요일을 선택해 주세요.", "입력 확인", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
        }

        ResultItem = _originalItem ?? new RecurringScheduleItem();
        ResultItem.Title = title;
        ResultItem.ActionType = actionType;
        ResultItem.AmPm = ampm;
        ResultItem.Hour12 = hour12;
        ResultItem.Minute = minute;
        ResultItem.TimeString = timeStr;
        ResultItem.IsSingle = isSingle;
        ResultItem.TargetDate = isSingle && DpDate.SelectedDate.HasValue ? DpDate.SelectedDate.Value.ToString("yyyy-MM-dd") : string.Empty;
        ResultItem.RepeatDays = days;
        ResultItem.RepeatMode = isSingle ? "1회성" : (days.Count == 5 && !days.Contains(5) && !days.Contains(6) ? "평일(월~금)" : (days.Count == 7 ? "매일" : "요일선택"));
        ResultItem.SkipHolidays = ChkSkipHolidays.IsChecked == true;
        ResultItem.Memo = TbMemo.Text.Trim();
        ResultItem.Enabled = true;
        ResultItem.IsCompleted = false;

        DialogResult = true;
        Close();
    }

    private void BtnCancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}