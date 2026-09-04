using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace KnolTeacher.Desktop.Models;

public class PeriodCountdownItem
{
    [JsonPropertyName("period_number")]
    public int PeriodNumber { get; set; } = 0; // 0 = Global default

    [JsonPropertyName("name")]
    public string Name { get; set; } = "일괄 기본값";

    [JsonPropertyName("enabled")]
    public bool Enabled { get; set; } = true;

    [JsonPropertyName("use_global")]
    public bool UseGlobal { get; set; } = true;

    [JsonPropertyName("lead_start_minutes")]
    public int LeadStartMinutes { get; set; } = 5;

    [JsonPropertyName("lead_start_seconds")]
    public int LeadStartSeconds { get; set; } = 0;

    [JsonPropertyName("lead_end_minutes")]
    public int LeadEndMinutes { get; set; } = 3;

    [JsonPropertyName("lead_end_seconds")]
    public int LeadEndSeconds { get; set; } = 0;

    [JsonPropertyName("target_monitor_index")]
    public int TargetMonitorIndex { get; set; } = -1; // -1: Current cursor monitor, 0: Primary, 1: Secondary

    [JsonPropertyName("pre_notice_text")]
    public string PreNoticeText { get; set; } = "🔔 다음 시간 {교시} ({과목}) 준비 시간입니다! 자리에 앉아 교과서를 펴주세요.";

    [JsonPropertyName("post_notice_text")]
    public string PostNoticeText { get; set; } = "👏 수업 준비 완료! 자리에 모두 착석했습니다.";

    [JsonPropertyName("play_sound_chime")]
    public bool PlaySoundChime { get; set; } = true;

    [JsonPropertyName("auto_close_seconds")]
    public int AutoCloseSeconds { get; set; } = 8;

    [JsonIgnore]
    public int TotalLeadStartSeconds => LeadStartMinutes * 60 + LeadStartSeconds;

    [JsonIgnore]
    public int TotalLeadEndSeconds => LeadEndMinutes * 60 + LeadEndSeconds;

    [JsonIgnore]
    public int CountdownDurationSeconds => Math.Max(1, TotalLeadStartSeconds - TotalLeadEndSeconds);

    [JsonIgnore]
    public string TimeSummary => $"{LeadStartMinutes}분 {LeadStartSeconds:D2}초 전 ~ {LeadEndMinutes}분 {LeadEndSeconds:D2}초 전 (총 {CountdownDurationSeconds / 60}분 {CountdownDurationSeconds % 60}초 카운트다운)";
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
        TargetMonitorIndex = -1,
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
                TargetMonitorIndex = -1,
                PreNoticeText = $"🔔 {p}교시 ({{과목}}) 준비 시간입니다! 자리에 앉아 교과서를 펴주세요.",
                PostNoticeText = $"👏 {p}교시 수업 준비 완료! 자리에 모두 착석했습니다."
            };
        }
        return cfg;
    }
}
