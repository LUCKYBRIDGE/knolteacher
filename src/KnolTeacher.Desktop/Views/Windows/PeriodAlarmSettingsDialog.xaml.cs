using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class PeriodAlarmSettingsDialog : Window
{
    private readonly IConfigService _configService;
    private readonly ISoundService _soundService;
    private readonly ITimetableService _timetableService;
    private PeriodAlarmSystemConfig _editingConfig;
    private List<PeriodCountdownItem> _overridesList = new();

    public PeriodAlarmSettingsDialog(
        IConfigService configService,
        ISoundService soundService,
        ITimetableService timetableService)
    {
        _configService = configService;
        _soundService = soundService;
        _timetableService = timetableService;
        InitializeComponent();

        _editingConfig = CloneConfig(_configService.PeriodAlarmConfig);
        PopulateUi();
    }

    private PeriodAlarmSystemConfig CloneConfig(PeriodAlarmSystemConfig src)
    {
        var result = new PeriodAlarmSystemConfig
        {
            GlobalConfig = CloneItem(src.GlobalConfig)
        };
        foreach (var kvp in src.PeriodOverrides)
        {
            result.PeriodOverrides[kvp.Key] = CloneItem(kvp.Value);
        }
        return result;
    }

    private PeriodCountdownItem CloneItem(PeriodCountdownItem src) => new()
    {
        PeriodNumber = src.PeriodNumber,
        Name = src.Name,
        Enabled = src.Enabled,
        UseGlobal = src.UseGlobal,
        ClassType = src.ClassType,
        LeadStartMinutes = src.LeadStartMinutes,
        LeadStartSeconds = src.LeadStartSeconds,
        LeadEndMinutes = src.LeadEndMinutes,
        LeadEndSeconds = src.LeadEndSeconds,
        TargetMonitorIndex = src.TargetMonitorIndex,
        PreNoticeText = src.PreNoticeText,
        PostNoticeText = src.PostNoticeText,
        PlaySoundChime = src.PlaySoundChime,
        AutoCloseSeconds = src.AutoCloseSeconds
    };

    private void PopulateUi()
    {
        var g = _editingConfig.GlobalConfig;
        ChkGlobalEnabled.IsChecked = g.Enabled;
        TbStartMin.Text = g.LeadStartMinutes.ToString();
        TbStartSec.Text = $"{g.LeadStartSeconds:D2}";
        TbEndMin.Text = g.LeadEndMinutes.ToString();
        TbEndSec.Text = $"{g.LeadEndSeconds:D2}";
        TbPreNotice.Text = g.PreNoticeText;

        var tg = _editingConfig.TravelGlobalConfig;
        TbTravelStartMin.Text = tg.LeadStartMinutes.ToString();
        TbTravelStartSec.Text = $"{tg.LeadStartSeconds:D2}";
        TbTravelEndMin.Text = tg.LeadEndMinutes.ToString();
        TbTravelEndSec.Text = $"{tg.LeadEndSeconds:D2}";
        TbTravelPreNotice.Text = tg.PreNoticeText;

        TbPostNotice.Text = g.PostNoticeText;
        ChkSoundChime.IsChecked = g.PlaySoundChime;
        TbAutoCloseSec.Text = g.AutoCloseSeconds.ToString();

        // Monitor Selection (0: Monitor 2 권장, 1: Monitor 1, 2: 마우스 위치)
        int mon = g.TargetMonitorIndex;
        if (mon == 1) CbMonitorSelect.SelectedIndex = 0;
        else if (mon == 0) CbMonitorSelect.SelectedIndex = 1;
        else CbMonitorSelect.SelectedIndex = 2;

        UpdateTimeCalculation();

        // Overrides (1~7교시)
        _overridesList = _editingConfig.PeriodOverrides.Values.OrderBy(p => p.PeriodNumber).ToList();
        ListPeriodOverrides.ItemsSource = _overridesList;

        // Storage Settings (Tab 3)
        TxtCurrentSaveDirectory.Text = _configService.GetEffectiveSaveDirectory();
        ChkCreateSubfolderForDrawings.IsChecked = _configService.StorageConfig.CreateSubfolderForDrawings;
    }

    private void TimeCalc_TextChanged(object sender, TextChangedEventArgs e)
    {
        UpdateTimeCalculation();
    }

    private void UpdateTimeCalculation()
    {
        if (TxtCalculatedDuration != null && TbStartMin != null && TbStartSec != null && TbEndMin != null && TbEndSec != null)
        {
            int sMin = int.TryParse(TbStartMin.Text, out int sm) ? sm : 5;
            int sSec = int.TryParse(TbStartSec.Text, out int ss) ? ss : 0;
            int eMin = int.TryParse(TbEndMin.Text, out int em) ? em : 3;
            int eSec = int.TryParse(TbEndSec.Text, out int es) ? es : 0;

            int totalStart = sMin * 60 + sSec;
            int totalEnd = eMin * 60 + eSec;
            int diff = Math.Max(0, totalStart - totalEnd);

            int dMin = diff / 60;
            int dSec = diff % 60;
            TxtCalculatedDuration.Text = $"💡 교실수업: 대형 타이머가 {dMin}분 {dSec:D2}초 동안 카운트다운됩니다.";
        }

        if (TxtTravelCalculatedDuration != null && TbTravelStartMin != null && TbTravelStartSec != null && TbTravelEndMin != null && TbTravelEndSec != null)
        {
            int tsMin = int.TryParse(TbTravelStartMin.Text, out int tsm) ? tsm : 10;
            int tsSec = int.TryParse(TbTravelStartSec.Text, out int tss) ? tss : 0;
            int teMin = int.TryParse(TbTravelEndMin.Text, out int tem) ? tem : 3;
            int teSec = int.TryParse(TbTravelEndSec.Text, out int tes) ? tes : 0;

            int totalStart = tsMin * 60 + tsSec;
            int totalEnd = teMin * 60 + teSec;
            int diff = Math.Max(0, totalStart - totalEnd);

            int dMin = diff / 60;
            int dSec = diff % 60;
            TxtTravelCalculatedDuration.Text = $"💡 이동수업: 대형 타이머가 {dMin}분 {dSec:D2}초 동안 카운트다운됩니다.";
        }
    }

    private void BtnTestRun_Click(object sender, RoutedEventArgs e)
    {
        int targetMon = -1;
        if (CbMonitorSelect.SelectedItem is ComboBoxItem item && item.Tag is string tagStr && int.TryParse(tagStr, out int mIdx))
        {
            targetMon = mIdx;
        }

        var testItem = new PeriodCountdownItem
        {
            PeriodNumber = 2,
            Name = "2교시",
            TargetMonitorIndex = targetMon,
            PreNoticeText = TbPreNotice.Text,
            PostNoticeText = TbPostNotice.Text,
            PlaySoundChime = ChkSoundChime.IsChecked == true,
            AutoCloseSeconds = 5
        };

        // Run 10-second test countdown overlay
        var overlay = new ClassroomCountdownOverlayWindow(testItem, "2교시 (테스트)", "국어", _soundService, overrideDurationSeconds: 10);
        overlay.Show();
    }

    private void BtnQuickPreset_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.DataContext is PeriodCountdownItem item && btn.Tag is string mode)
        {
            item.Enabled = true;
            item.UseGlobal = false;

            if (mode == "travel" || mode == "travel_10")
            {
                item.ClassType = "travel";
                item.LeadStartMinutes = _editingConfig.TravelGlobalConfig.LeadStartMinutes > 0 ? _editingConfig.TravelGlobalConfig.LeadStartMinutes : 10;
                item.LeadStartSeconds = _editingConfig.TravelGlobalConfig.LeadStartSeconds;
                item.LeadEndMinutes = _editingConfig.TravelGlobalConfig.LeadEndMinutes;
                item.LeadEndSeconds = _editingConfig.TravelGlobalConfig.LeadEndSeconds;
                item.PreNoticeText = $"🎒 다음 시간 {item.Name} ({{과목}}) 이동수업입니다! 이동시간을 고려하여 필요한 준비물을 챙겨 조용히 이동합시다.";
            }
            else
            {
                item.ClassType = "classroom";
                item.LeadStartMinutes = _editingConfig.GlobalConfig.LeadStartMinutes > 0 ? _editingConfig.GlobalConfig.LeadStartMinutes : 5;
                item.LeadStartSeconds = _editingConfig.GlobalConfig.LeadStartSeconds;
                item.LeadEndMinutes = _editingConfig.GlobalConfig.LeadEndMinutes;
                item.LeadEndSeconds = _editingConfig.GlobalConfig.LeadEndSeconds;
                item.PreNoticeText = $"🔔 다음 시간 {item.Name} ({{과목}}) 준비 시간입니다! 자리에 앉아 교과서를 펴주세요.";
            }
        }
    }

    private void BtnQuickDisable_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.DataContext is PeriodCountdownItem item)
        {
            item.Enabled = false;
            item.UseGlobal = false;
        }
    }

    private void BtnResetDefaults_Click(object sender, RoutedEventArgs e)
    {
        if (MessageBox.Show("모든 예비령 및 카운트다운 알람 설정을 초기 기본값으로 되돌리시겠습니까?", "초기화 확인", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
        {
            _editingConfig = PeriodAlarmSystemConfig.CreateDefault();
            PopulateUi();
        }
    }

    private void BtnCancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }

    private void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        var g = _editingConfig.GlobalConfig;
        g.Enabled = ChkGlobalEnabled.IsChecked == true;
        g.LeadStartMinutes = int.TryParse(TbStartMin.Text, out int sm) ? Math.Max(0, sm) : 5;
        g.LeadStartSeconds = int.TryParse(TbStartSec.Text, out int ss) ? Math.Clamp(ss, 0, 59) : 0;
        g.LeadEndMinutes = int.TryParse(TbEndMin.Text, out int em) ? Math.Max(0, em) : 3;
        g.LeadEndSeconds = int.TryParse(TbEndSec.Text, out int es) ? Math.Clamp(es, 0, 59) : 0;

        if (CbMonitorSelect.SelectedItem is ComboBoxItem item && item.Tag is string tagStr && int.TryParse(tagStr, out int mIdx))
        {
            g.TargetMonitorIndex = mIdx;
        }

        g.PreNoticeText = TbPreNotice.Text;
        g.PostNoticeText = TbPostNotice.Text;
        g.PlaySoundChime = ChkSoundChime.IsChecked == true;
        g.AutoCloseSeconds = int.TryParse(TbAutoCloseSec.Text, out int ac) ? Math.Max(2, ac) : 8;

        var tg = _editingConfig.TravelGlobalConfig;
        tg.Enabled = g.Enabled;
        tg.ClassType = "travel";
        tg.LeadStartMinutes = int.TryParse(TbTravelStartMin.Text, out int tsm) ? Math.Max(0, tsm) : 10;
        tg.LeadStartSeconds = int.TryParse(TbTravelStartSec.Text, out int tss) ? Math.Clamp(tss, 0, 59) : 0;
        tg.LeadEndMinutes = int.TryParse(TbTravelEndMin.Text, out int tem) ? Math.Max(0, tem) : 3;
        tg.LeadEndSeconds = int.TryParse(TbTravelEndSec.Text, out int tes) ? Math.Clamp(tes, 0, 59) : 0;
        tg.TargetMonitorIndex = g.TargetMonitorIndex;
        tg.PreNoticeText = TbTravelPreNotice.Text;
        tg.PostNoticeText = g.PostNoticeText;
        tg.PlaySoundChime = g.PlaySoundChime;
        tg.AutoCloseSeconds = g.AutoCloseSeconds;

        _configService.PeriodAlarmConfig = _editingConfig;
        _configService.SavePeriodAlarmConfig();

        // Sync periods alarm_enabled state
        var periods = _timetableService.GetPeriods();
        bool anyChanged = false;
        foreach (var p in periods)
        {
            if (p.IsLunch) continue;
            var eff = _editingConfig.GetEffectiveConfig(p.Period);
            bool shouldEnable = _editingConfig.GlobalConfig.Enabled && eff.Enabled;
            if (p.AlarmEnabled != shouldEnable)
            {
                p.AlarmEnabled = shouldEnable;
                anyChanged = true;
            }
        }
        if (anyChanged)
        {
            _timetableService.SavePeriods(periods);
        }

        // Storage settings (Tab 3)
        string chosenSaveDir = TxtCurrentSaveDirectory.Text.Trim();
        if (!string.IsNullOrWhiteSpace(chosenSaveDir))
        {
            _configService.SetDefaultSaveDirectory(chosenSaveDir);
        }
        _configService.StorageConfig.CreateSubfolderForDrawings = ChkCreateSubfolderForDrawings.IsChecked == true;
        _configService.SaveStorageConfig();

        HudNotificationWindow.Instance.ShowToast("💾", "설정이 성공적으로 저장되었습니다.");
        DialogResult = true;
        Close();
    }

    public void SelectTab(int index)
    {
        if (AlarmTabs != null && index >= 0 && index < AlarmTabs.Items.Count)
        {
            AlarmTabs.SelectedIndex = index;
        }
    }

    private void BtnBrowseSaveFolder_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new Microsoft.Win32.OpenFolderDialog
        {
            Title = "놀티쳐 파일 기본 저장 폴더 선택",
            InitialDirectory = TxtCurrentSaveDirectory.Text
        };
        if (dlg.ShowDialog() == true)
        {
            if (!string.IsNullOrWhiteSpace(dlg.FolderName))
            {
                TxtCurrentSaveDirectory.Text = dlg.FolderName;
            }
        }
    }

    private void BtnOpenCurrentSaveFolder_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            string dir = TxtCurrentSaveDirectory.Text.Trim();
            if (string.IsNullOrWhiteSpace(dir) || !System.IO.Directory.Exists(dir))
            {
                dir = _configService.GetEffectiveSaveDirectory();
            }
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = dir,
                UseShellExecute = true
            });
        }
        catch (Exception ex)
        {
            MessageBox.Show($"폴더 열기 실패: {ex.Message}", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void BtnPresetSaveDir_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string tag)
        {
            string targetPath = tag switch
            {
                "downloads" => System.IO.Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads"),
                "desktop" => Environment.GetFolderPath(Environment.SpecialFolder.Desktop),
                "documents" => Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                "pictures" => Environment.GetFolderPath(Environment.SpecialFolder.MyPictures),
                _ => System.IO.Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads")
            };
            TxtCurrentSaveDirectory.Text = targetPath;
        }
    }
}
