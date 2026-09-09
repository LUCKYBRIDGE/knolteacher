using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Text.Json.Serialization;

namespace KnolTeacher.Desktop.Models;

public class PeriodCountdownItem : INotifyPropertyChanged
{
    private int _periodNumber = 0;
    private string _name = "일괄 기본값";
    private bool _enabled = true;
    private bool _useGlobal = true;
    private int _leadStartMinutes = 5;
    private int _leadStartSeconds = 0;
    private int _leadEndMinutes = 3;
    private int _leadEndSeconds = 0;
    private int _targetMonitorIndex = 1;
    private string _preNoticeText = "🔔 다음 시간 {교시} ({과목}) 준비 시간입니다! 자리에 앉아 교과서를 펴주세요.";
    private string _postNoticeText = "👏 수업 준비 완료! 자리에 모두 착석했습니다.";
    private bool _playSoundChime = true;
    private int _autoCloseSeconds = 8;

    [JsonPropertyName("period_number")]
    public int PeriodNumber
    {
        get => _periodNumber;
        set => SetField(ref _periodNumber, value);
    }

    [JsonPropertyName("name")]
    public string Name
    {
        get => _name;
        set => SetField(ref _name, value);
    }

    [JsonPropertyName("enabled")]
    public bool Enabled
    {
        get => _enabled;
        set
        {
            if (SetField(ref _enabled, value))
                OnPropertyChanged(nameof(TimeSummary));
        }
    }

    [JsonPropertyName("use_global")]
    public bool UseGlobal
    {
        get => _useGlobal;
        set => SetField(ref _useGlobal, value);
    }

    [JsonPropertyName("lead_start_minutes")]
    public int LeadStartMinutes
    {
        get => _leadStartMinutes;
        set
        {
            if (SetField(ref _leadStartMinutes, value))
            {
                OnPropertyChanged(nameof(TotalLeadStartSeconds));
                OnPropertyChanged(nameof(CountdownDurationSeconds));
                OnPropertyChanged(nameof(TimeSummary));
            }
        }
    }

    [JsonPropertyName("lead_start_seconds")]
    public int LeadStartSeconds
    {
        get => _leadStartSeconds;
        set
        {
            if (SetField(ref _leadStartSeconds, value))
            {
                OnPropertyChanged(nameof(TotalLeadStartSeconds));
                OnPropertyChanged(nameof(CountdownDurationSeconds));
                OnPropertyChanged(nameof(TimeSummary));
            }
        }
    }

    [JsonPropertyName("lead_end_minutes")]
    public int LeadEndMinutes
    {
        get => _leadEndMinutes;
        set
        {
            if (SetField(ref _leadEndMinutes, value))
            {
                OnPropertyChanged(nameof(TotalLeadEndSeconds));
                OnPropertyChanged(nameof(CountdownDurationSeconds));
                OnPropertyChanged(nameof(TimeSummary));
            }
        }
    }

    [JsonPropertyName("lead_end_seconds")]
    public int LeadEndSeconds
    {
        get => _leadEndSeconds;
        set
        {
            if (SetField(ref _leadEndSeconds, value))
            {
                OnPropertyChanged(nameof(TotalLeadEndSeconds));
                OnPropertyChanged(nameof(CountdownDurationSeconds));
                OnPropertyChanged(nameof(TimeSummary));
            }
        }
    }

    [JsonPropertyName("target_monitor_index")]
    public int TargetMonitorIndex
    {
        get => _targetMonitorIndex;
        set => SetField(ref _targetMonitorIndex, value);
    }

    [JsonPropertyName("pre_notice_text")]
    public string PreNoticeText
    {
        get => _preNoticeText;
        set => SetField(ref _preNoticeText, value);
    }

    [JsonPropertyName("post_notice_text")]
    public string PostNoticeText
    {
        get => _postNoticeText;
        set => SetField(ref _postNoticeText, value);
    }

    [JsonPropertyName("play_sound_chime")]
    public bool PlaySoundChime
    {
        get => _playSoundChime;
        set => SetField(ref _playSoundChime, value);
    }

    [JsonPropertyName("auto_close_seconds")]
    public int AutoCloseSeconds
    {
        get => _autoCloseSeconds;
        set => SetField(ref _autoCloseSeconds, value);
    }

    [JsonIgnore]
    public int TotalLeadStartSeconds => LeadStartMinutes * 60 + LeadStartSeconds;

    [JsonIgnore]
    public int TotalLeadEndSeconds => LeadEndMinutes * 60 + LeadEndSeconds;

    [JsonIgnore]
    public int CountdownDurationSeconds => Math.Max(1, TotalLeadStartSeconds - TotalLeadEndSeconds);

    [JsonIgnore]
    public string TimeSummary => $"{LeadStartMinutes}분 {LeadStartSeconds:D2}초 전 ~ {LeadEndMinutes}분 {LeadEndSeconds:D2}초 전 (총 {CountdownDurationSeconds / 60}분 {CountdownDurationSeconds % 60}초 카운트다운)";

    public event PropertyChangedEventHandler? PropertyChanged;

    protected void OnPropertyChanged([CallerMemberName] string? propertyName = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }

    protected bool SetField<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value)) return false;
        field = value;
        OnPropertyChanged(propertyName);
        return true;
    }
}

public class PeriodAlarmSystemConfig
{
    [JsonPropertyName("global")]
    public PeriodCountdownItem GlobalConfig { get; set; } = new()
    {
        PeriodNumber = 0,
        Name = "일괄 기본값",
        Enabled = true,
        UseGlobal = false,
        LeadStartMinutes = 5,
        LeadStartSeconds = 0,
        LeadEndMinutes = 3,
        LeadEndSeconds = 0,
        TargetMonitorIndex = 1, // 모니터 2 (학생용 전자칠판/TV 권장)
        PreNoticeText = "🔔 다음 시간 {교시} ({과목}) 준비 시간입니다! 자리에 앉아 교과서를 펴주세요.",
        PostNoticeText = "👏 수업 준비 완료! 자리에 모두 착석했습니다.",
        PlaySoundChime = true,
        AutoCloseSeconds = 8
    };

    [JsonPropertyName("overrides")]
    public Dictionary<string, PeriodCountdownItem> PeriodOverrides { get; set; } = new();

    public PeriodCountdownItem GetEffectiveConfig(int period)
    {
        string key = period.ToString();
        if (PeriodOverrides.TryGetValue(key, out var item) && !item.UseGlobal)
        {
            return item;
        }
        return GlobalConfig;
    }

    public static PeriodAlarmSystemConfig CreateDefault()
    {
        var cfg = new PeriodAlarmSystemConfig();
        for (int p = 1; p <= 7; p++)
        {
            cfg.PeriodOverrides[p.ToString()] = new PeriodCountdownItem
            {
                PeriodNumber = p,
                Name = $"{p}교시",
                Enabled = true,
                UseGlobal = true,
                LeadStartMinutes = 5,
                LeadStartSeconds = 0,
                LeadEndMinutes = 3,
                LeadEndSeconds = 0,
                TargetMonitorIndex = 1,
                PreNoticeText = $"🔔 {p}교시 ({{과목}}) 준비 시간입니다! 자리에 앉아 교과서를 펴주세요.",
                PostNoticeText = $"👏 {p}교시 수업 준비 완료! 자리에 모두 착석했습니다."
            };
        }
        return cfg;
    }
}
