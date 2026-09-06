using System;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class AutoNoticeSettingsDialog : Window
{
    private readonly IConfigService _configService;
    private readonly string _currentNoticeText;

    public event Action<string>? SetApplied;

    public AutoNoticeSettingsDialog(IConfigService configService, string currentNoticeText = "")
    {
        InitializeComponent();
        _configService = configService;
        _currentNoticeText = currentNoticeText;

        LoadData();
    }

    private void LoadData()
    {
        var preset = _configService.AutoNoticePreset;
        ChkEnableAutoNotice.IsChecked = preset.Enabled;
        TxtMorning.Text = preset.MorningNotice;
        TxtClass.Text = preset.ClassNotice;
        TxtBreak.Text = preset.BreakNotice;
        TxtLunch.Text = preset.LunchNotice;
        TxtDismissal.Text = preset.DismissalNotice;

        RefreshSetList();
    }

    private void RefreshSetList()
    {
        ListBoardSets.ItemsSource = null;
        ListBoardSets.ItemsSource = _configService.BoardSetStore.Sets.ToList();
    }

    private void BtnSaveCurrentAsSet_Click(object sender, RoutedEventArgs e)
    {
        string name = TxtNewSetName.Text.Trim();
        if (string.IsNullOrWhiteSpace(name) || name == "세트 이름 입력...")
        {
            name = $"알림 세트 ({DateTime.Now:MM-dd HH:mm})";
        }

        var newSet = new BoardSetItem
        {
            Name = name,
            Content = _currentNoticeText,
            CreatedAt = DateTime.Now
        };

        _configService.BoardSetStore.Sets.Add(newSet);
        _configService.SaveBoardSetStore();
        RefreshSetList();
        TxtNewSetName.Text = string.Empty;
        MessageBox.Show($"'{name}' 세트가 저장되었습니다.", "세트 저장", MessageBoxButton.OK, MessageBoxImage.Information);
    }

    private void BtnApplySet_Click(object sender, RoutedEventArgs e)
    {
        if (ListBoardSets.SelectedItem is BoardSetItem selected)
        {
            SetApplied?.Invoke(selected.Content);
            _configService.BoardSetStore.ActiveSetId = selected.Id;
            _configService.SaveBoardSetStore();
            Close();
        }
        else
        {
            MessageBox.Show("적용할 알림 세트를 선택해 주세요.", "알림", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }

    private void BtnDeleteSet_Click(object sender, RoutedEventArgs e)
    {
        if (ListBoardSets.SelectedItem is BoardSetItem selected)
        {
            if (MessageBox.Show($"'{selected.Name}' 세트를 삭제하시겠습니까?", "삭제 확인", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
            {
                _configService.BoardSetStore.Sets.Remove(selected);
                _configService.SaveBoardSetStore();
                RefreshSetList();
            }
        }
    }

    private void ListBoardSets_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        // Optional detail preview
    }

    private void BtnSaveAndClose_Click(object sender, RoutedEventArgs e)
    {
        var preset = _configService.AutoNoticePreset;
        preset.Enabled = ChkEnableAutoNotice.IsChecked == true;
        preset.MorningNotice = TxtMorning.Text.Trim();
        preset.ClassNotice = TxtClass.Text.Trim();
        preset.BreakNotice = TxtBreak.Text.Trim();
        preset.LunchNotice = TxtLunch.Text.Trim();
        preset.DismissalNotice = TxtDismissal.Text.Trim();

        _configService.SaveAutoNoticePreset();
        Close();
    }

    private void BtnCancel_Click(object sender, RoutedEventArgs e)
    {
        Close();
    }
}
