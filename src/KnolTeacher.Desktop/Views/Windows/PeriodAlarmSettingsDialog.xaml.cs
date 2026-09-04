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
        TbPostNotice.Text = g.PostNoticeText;
        ChkSoundChime.IsChecked = g.PlaySoundChime;
        TbAutoCloseSec.Text = g.AutoCloseSeconds.ToString();

        // Monitor Selection
        int mon = g.TargetMonitorIndex;
        if (mon == 0) CbMonitorSelect.SelectedIndex = 1;
        else if (mon == 1) CbMonitorSelect.SelectedIndex = 2;
        else CbMonitorSelect.SelectedIndex = 0;

        UpdateTimeCalculation();

        // Overrides (1~7교시)
        _overridesList = _editingConfig.PeriodOverrides.Values.OrderBy(p => p.PeriodNumber).ToList();
        ListPeriodOverrides.ItemsSource = _overridesList;
    }

    private void TimeCalc_TextChanged(object sender, TextChangedEventArgs e)
    {
        UpdateTimeCalculation();
    }

    private void UpdateTimeCalculation()
    {
        if (TxtCalculatedDuration == null) return;

        int sMin = int.TryParse(TbStartMin.Text, out int sm) ? sm : 5;
        int sSec = int.TryParse(TbStartSec.Text, out int ss) ? ss : 0;
        int eMin = int.TryParse(TbEndMin.Text, out int em) ? em : 3;
        int eSec = int.TryParse(TbEndSec.Text, out int es) ? es : 0;

        int totalStart = sMin * 60 + sSec;
        int totalEnd = eMin * 60 + eSec;
        int diff = Math.Max(0, totalStart - totalEnd);

        int dMin = diff / 60;
        int dSec = diff % 60;

        TxtCalculatedDuration.Text = $"💡 화면에 대형 타이머가 총 {dMin}분 {dSec:D2}초 동안 카운트다운됩니다.";
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

        _configService.PeriodAlarmConfig = _editingConfig;
        _configService.SavePeriodAlarmConfig();

        HudNotificationWindow.Instance.ShowToast("🔔", "수업 시작 전 카운트다운 알람 설정이 성공적으로 저장되었습니다.");
        DialogResult = true;
        Close();
    }
}
