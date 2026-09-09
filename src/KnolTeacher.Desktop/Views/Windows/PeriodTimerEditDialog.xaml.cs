using System;
using System.Windows;
using System.Windows.Controls;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class PeriodTimerEditDialog : Window
{
    private readonly PeriodItem _periodItem;
    private readonly IConfigService _configService;
    private readonly ISoundService _soundService;
    private readonly IDisplayManager? _displayManager;
    private readonly ClassroomTimerWindow? _timerWindow;
    private readonly ITimetableService? _timetableService;
    private PeriodCountdownItem _itemConfig;

    public PeriodTimerEditDialog(
        PeriodItem periodItem,
        IConfigService configService,
        ISoundService soundService,
        IDisplayManager? displayManager = null,
        ClassroomTimerWindow? timerWindow = null,
        ITimetableService? timetableService = null)
    {
        _periodItem = periodItem;
        _configService = configService;
        _soundService = soundService;
        _displayManager = displayManager;
        _timerWindow = timerWindow;
        _timetableService = timetableService;

        InitializeComponent();

        TxtHeaderTitle.Text = $"{_periodItem.Name} ({_periodItem.Subject}) 시작 전 타이머 설정";
        TxtBadgePeriod.Text = _periodItem.Name;
        TxtHeaderTimeRange.Text = $"수업 시간: {_periodItem.TimeRange} (시작 전 학생 화면에 카운트다운 타이머 표출)";

        // Get effective config or clone from overrides
        string key = _periodItem.Period.ToString();
        var sysCfg = _configService.PeriodAlarmConfig;
        if (sysCfg.PeriodOverrides.TryGetValue(key, out var existing))
        {
            _itemConfig = CloneItem(existing);
        }
        else
        {
            _itemConfig = CloneItem(sysCfg.GlobalConfig);
            _itemConfig.PeriodNumber = _periodItem.Period;
            _itemConfig.Name = _periodItem.Name;
            _itemConfig.UseGlobal = false;
        }

        PopulateUi();
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
        ChkEnabled.IsChecked = _itemConfig.Enabled;
        ChkUseGlobal.IsChecked = _itemConfig.UseGlobal;

        TbStartMin.Text = _itemConfig.LeadStartMinutes.ToString();
        TbStartSec.Text = $"{_itemConfig.LeadStartSeconds:D2}";
        TbEndMin.Text = _itemConfig.LeadEndMinutes.ToString();
        TbEndSec.Text = $"{_itemConfig.LeadEndSeconds:D2}";

        string defaultPreNotice = string.IsNullOrEmpty(_itemConfig.PreNoticeText)
            ? $"🔔 다음 시간 {_periodItem.Name} ({_periodItem.Subject}) 준비 시간입니다! 자리에 앉아 교과서를 펴주세요."
            : _itemConfig.PreNoticeText;
        TbPreNotice.Text = defaultPreNotice;

        string defaultPostNotice = string.IsNullOrEmpty(_itemConfig.PostNoticeText)
            ? "👏 수업 준비 완료! 자리에 모두 착석했습니다."
            : _itemConfig.PostNoticeText;
        TbPostNotice.Text = defaultPostNotice;

        ChkSoundChime.IsChecked = _itemConfig.PlaySoundChime;

        int mon = _itemConfig.TargetMonitorIndex;
        if (mon == 1) CbMonitorSelect.SelectedIndex = 0;
        else if (mon == 0) CbMonitorSelect.SelectedIndex = 1;
        else CbMonitorSelect.SelectedIndex = 2;

        UpdateTimeCalculation();
        UpdateGlobalToggleState();
    }

    private void ChkUseGlobal_Click(object sender, RoutedEventArgs e)
    {
        UpdateGlobalToggleState();
        if (ChkUseGlobal.IsChecked == true)
        {
            var g = _configService.PeriodAlarmConfig.GlobalConfig;
            TbStartMin.Text = g.LeadStartMinutes.ToString();
            TbStartSec.Text = $"{g.LeadStartSeconds:D2}";
            TbEndMin.Text = g.LeadEndMinutes.ToString();
            TbEndSec.Text = $"{g.LeadEndSeconds:D2}";
            TbPreNotice.Text = g.PreNoticeText;
            TbPostNotice.Text = g.PostNoticeText;
            UpdateTimeCalculation();
        }
    }

    private void UpdateGlobalToggleState()
    {
        bool useGlobal = ChkUseGlobal.IsChecked == true;
        PanelCustomTimeSettings.Opacity = useGlobal ? 0.65 : 1.0;
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
        int eMin = int.TryParse(TbEndMin.Text, out int em) ? em : 0;
        int eSec = int.TryParse(TbEndSec.Text, out int es) ? es : 0;

        int totalStart = sMin * 60 + sSec;
        int totalEnd = eMin * 60 + eSec;
        int diff = Math.Max(0, totalStart - totalEnd);

        int dMin = diff / 60;
        int dSec = diff % 60;

        TxtCalculatedDuration.Text = $"💡 수업 시작 {sMin}분 {sSec:D2}초 전 화면에 대형 타이머가 켜져 총 {dMin}분 {dSec:D2}초 동안 작동합니다.";
    }

    private void BtnPresetTravel_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string mode)
        {
            ChkEnabled.IsChecked = true;
            ChkUseGlobal.IsChecked = false;
            UpdateGlobalToggleState();

            switch (mode)
            {
                case "travel_10": // 이동수업 10분 전 ~ 3분 전
                    TbStartMin.Text = "10";
                    TbStartSec.Text = "00";
                    TbEndMin.Text = "3";
                    TbEndSec.Text = "00";
                    TbPreNotice.Text = $"🎒 다음 시간은 {_periodItem.Subject} 이동수업입니다! 이동시간을 고려하여 교과서와 준비물을 챙겨 전담실로 조용히 이동합시다.";
                    break;
                case "special_7": // 특별실 7분 전 ~ 2분 전
                    TbStartMin.Text = "7";
                    TbStartSec.Text = "00";
                    TbEndMin.Text = "2";
                    TbEndSec.Text = "00";
                    TbPreNotice.Text = $"🏃 다음 시간은 {_periodItem.Subject} 특별실 수업입니다! 필요한 준비물을 챙겨 특별실로 이동해 주세요.";
                    break;
                case "specialist_5": // 전담수업 5분 전 ~ 0초
                    TbStartMin.Text = "5";
                    TbStartSec.Text = "00";
                    TbEndMin.Text = "0";
                    TbEndSec.Text = "00";
                    TbPreNotice.Text = $"👨‍🏫 다음 시간은 {_periodItem.Subject} 전담 선생님 수업입니다! 바르게 앉아 선생님을 맞이합시다.";
                    break;
                case "regular_5": // 일반수업 5분 전 ~ 3분 전
                    TbStartMin.Text = "5";
                    TbStartSec.Text = "00";
                    TbEndMin.Text = "3";
                    TbEndSec.Text = "00";
                    TbPreNotice.Text = $"🔔 다음 시간 {_periodItem.Name} ({_periodItem.Subject}) 준비 시간입니다! 자리에 앉아 교과서를 펴주세요.";
                    break;
                case "fast_3": // 직전 3분 전 ~ 0초
                    TbStartMin.Text = "3";
                    TbStartSec.Text = "00";
                    TbEndMin.Text = "0";
                    TbEndSec.Text = "00";
                    TbPreNotice.Text = $"🔔 곧 {_periodItem.Name} ({_periodItem.Subject}) 수업이 시작됩니다! 모든 준비를 마쳐주세요.";
                    break;
            }
            UpdateTimeCalculation();
        }
    }

    private void BtnPresetTiming_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string tag)
        {
            var parts = tag.Split(',');
            if (parts.Length == 4)
            {
                TbStartMin.Text = parts[0];
                TbStartSec.Text = parts[1].PadLeft(2, '0');
                TbEndMin.Text = parts[2];
                TbEndSec.Text = parts[3].PadLeft(2, '0');
                UpdateTimeCalculation();
            }
        }
    }

    private void BtnPresetMessage_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string template)
        {
            string msg = template
                .Replace("{교시}", _periodItem.Name)
                .Replace("{과목}", _periodItem.Subject);
            TbPreNotice.Text = msg;
        }
    }

    private void BtnTestRun_Click(object sender, RoutedEventArgs e)
    {
        int targetMon = 1;
        if (CbMonitorSelect.SelectedItem is ComboBoxItem item && item.Tag is string tagStr && int.TryParse(tagStr, out int mIdx))
        {
            targetMon = mIdx;
        }

        var testItem = new PeriodCountdownItem
        {
            PeriodNumber = _periodItem.Period,
            Name = _periodItem.Name,
            TargetMonitorIndex = targetMon,
            PreNoticeText = TbPreNotice.Text,
            PostNoticeText = TbPostNotice.Text,
            PlaySoundChime = ChkSoundChime.IsChecked == true,
            AutoCloseSeconds = 5
        };

        var overlay = new ClassroomCountdownOverlayWindow(
            testItem,
            $"{_periodItem.Name} (테스트)",
            _periodItem.Subject,
            _soundService,
            overrideDurationSeconds: 10
        );
        overlay.Show();
    }

    private void BtnLaunchClassTimer_Click(object sender, RoutedEventArgs e)
    {
        if (_timerWindow != null)
        {
            _timerWindow.PositionToDefaultMonitor();
            _timerWindow.Show();
            _timerWindow.Activate();
        }
        Close();
    }

    private void BtnOpenGlobalSettings_Click(object sender, RoutedEventArgs e)
    {
        var ttSvc = _timetableService ?? (Application.Current as App)?.Services?.GetService(typeof(ITimetableService)) as ITimetableService;
        if (ttSvc == null) return;

        var dlg = new PeriodAlarmSettingsDialog(_configService, _soundService, ttSvc)
        {
            Owner = this
        };
        dlg.ShowDialog();
        // Reload if changed
        var sysCfg = _configService.PeriodAlarmConfig;
        string key = _periodItem.Period.ToString();
        if (sysCfg.PeriodOverrides.TryGetValue(key, out var existing))
        {
            _itemConfig = CloneItem(existing);
            PopulateUi();
        }
    }

    private void BtnCancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }

    private void BtnDeleteAlarm_Click(object sender, RoutedEventArgs e)
    {
        ChkEnabled.IsChecked = false;
        _itemConfig.Enabled = false;
        _itemConfig.UseGlobal = false;

        var sysCfg = _configService.PeriodAlarmConfig;
        sysCfg.PeriodOverrides[_periodItem.Period.ToString()] = _itemConfig;
        _configService.SavePeriodAlarmConfig();

        if (_timetableService != null)
        {
            var p = _timetableService.GetPeriods().FirstOrDefault(x => x.Period == _periodItem.Period);
            if (p != null)
            {
                p.AlarmEnabled = false;
                _timetableService.SavePeriods(_timetableService.GetPeriods());
            }
        }

        HudNotificationWindow.Instance.ShowToast("🔕", $"{_periodItem.Name} 시작 전 알람이 삭제(꺼짐)되었습니다.");
        DialogResult = true;
        Close();
    }

    private void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        int sMin = int.TryParse(TbStartMin.Text, out int sm) ? Math.Max(0, sm) : 5;
        int sSec = int.TryParse(TbStartSec.Text, out int ss) ? Math.Clamp(ss, 0, 59) : 0;
        int eMin = int.TryParse(TbEndMin.Text, out int em) ? Math.Max(0, em) : 0;
        int eSec = int.TryParse(TbEndSec.Text, out int es) ? Math.Clamp(es, 0, 59) : 0;

        int targetMon = 1;
        if (CbMonitorSelect.SelectedItem is ComboBoxItem item && item.Tag is string tagStr && int.TryParse(tagStr, out int mIdx))
        {
            targetMon = mIdx;
        }

        _itemConfig.PeriodNumber = _periodItem.Period;
        _itemConfig.Name = _periodItem.Name;
        _itemConfig.Enabled = ChkEnabled.IsChecked == true;
        _itemConfig.UseGlobal = ChkUseGlobal.IsChecked == true;
        _itemConfig.LeadStartMinutes = sMin;
        _itemConfig.LeadStartSeconds = sSec;
        _itemConfig.LeadEndMinutes = eMin;
        _itemConfig.LeadEndSeconds = eSec;
        _itemConfig.PreNoticeText = TbPreNotice.Text.Trim();
        _itemConfig.PostNoticeText = TbPostNotice.Text.Trim();
        _itemConfig.PlaySoundChime = ChkSoundChime.IsChecked == true;
        _itemConfig.TargetMonitorIndex = targetMon;

        var sysCfg = _configService.PeriodAlarmConfig;
        sysCfg.PeriodOverrides[_periodItem.Period.ToString()] = _itemConfig;
        _configService.SavePeriodAlarmConfig();

        if (_timetableService != null)
        {
            var p = _timetableService.GetPeriods().FirstOrDefault(x => x.Period == _periodItem.Period);
            if (p != null)
            {
                p.AlarmEnabled = _itemConfig.Enabled;
                _timetableService.SavePeriods(_timetableService.GetPeriods());
            }
        }

        HudNotificationWindow.Instance.ShowToast("🔔", $"{_periodItem.Name} 시작 전 타이머 설정이 저장되었습니다.");
        DialogResult = true;
        Close();
    }
}
