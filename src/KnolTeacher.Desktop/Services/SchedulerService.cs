using System;
using System.Diagnostics;
using System.Linq;
using System.Windows.Threading;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Views.Windows;

namespace KnolTeacher.Desktop.Services;

public interface ISchedulerService
{
    void Start();
    void Stop();
    void TestRunSchedule(RecurringScheduleItem item);
}

public class SchedulerService : ISchedulerService
{
    private readonly IConfigService _configService;
    private readonly ISoundService _soundService;
    private readonly ITimetableService _timetableService;
    private readonly DispatcherTimer _timer;
    private string _lastTriggeredScheduleMinute = string.Empty;
    private string _lastTriggeredPeriodMinute = string.Empty;
    private readonly HashSet<string> _triggeredCountdowns = new();

    public SchedulerService(
        IConfigService configService,
        ISoundService soundService,
        ITimetableService timetableService)
    {
        _configService = configService;
        _soundService = soundService;
        _timetableService = timetableService;

        _timer = new DispatcherTimer
        {
            Interval = TimeSpan.FromSeconds(1)
        };
        _timer.Tick += OnTick;
    }

    public void Start()
    {
        _timer.Start();
    }

    public void Stop()
    {
        _timer.Stop();
    }

    private void OnTick(object? sender, EventArgs e)
    {
        var now = DateTime.Now;
        string currentHm = now.ToString("HH:mm");
        string todayDate = now.ToString("yyyy-MM-dd");

        CheckSchedules(now, currentHm, todayDate);
        CheckTimetableAlarms(now, currentHm);
    }

    private void CheckSchedules(DateTime now, string currentHm, string todayDate)
    {
        if (_lastTriggeredScheduleMinute == currentHm) return;

        int dayIndex = (int)now.DayOfWeek;
        int scheduleDay = dayIndex == 0 ? 6 : dayIndex - 1; // 0=Mon, 6=Sun

        var schedules = _configService.RecurringSchedules;
        if (schedules == null) return;

        bool configChanged = false;

        foreach (var item in schedules)
        {
            if (!item.Enabled) continue;
            if (item.TimeString != currentHm) continue;

            if (item.IsSingle)
            {
                // Single reservation check
                if (item.IsCompleted) continue;
                if (!string.IsNullOrEmpty(item.TargetDate) && item.TargetDate != todayDate) continue;

                _lastTriggeredScheduleMinute = currentHm;
                ExecuteAction(item);

                item.IsCompleted = true;
                item.Enabled = false;
                configChanged = true;
            }
            else
            {
                // Recurring reservation check
                if (item.RepeatDays != null && item.RepeatDays.Count > 0 && !item.RepeatDays.Contains(scheduleDay))
                {
                    continue;
                }

                _lastTriggeredScheduleMinute = currentHm;
                ExecuteAction(item);
            }
        }

        if (configChanged)
        {
            _configService.SaveRecurringSchedules();
        }
    }

    private void CheckTimetableAlarms(DateTime now, string currentHm)
    {
        // Skip weekends
        if (now.DayOfWeek == DayOfWeek.Saturday || now.DayOfWeek == DayOfWeek.Sunday) return;

        var schedule = _timetableService.GetTodaySchedule();
        string todayStr = now.ToString("yyyy-MM-dd");

        // 1. Pre-class Warning & Giant Countdown Overlay Trigger
        var periodAlarmCfg = _configService.PeriodAlarmConfig;
        if (periodAlarmCfg != null && periodAlarmCfg.GlobalConfig.Enabled)
        {
            foreach (var p in schedule)
            {
                if (!p.AlarmEnabled || p.IsLunch) continue;

                if (TimeSpan.TryParse(p.Start, out var startTs))
                {
                    var periodStartDt = DateTime.Today.Add(startTs);
                    var effCfg = periodAlarmCfg.GetEffectiveConfig(p.Period);
                    if (!effCfg.Enabled) continue;

                    var triggerDt = periodStartDt.AddSeconds(-effCfg.TotalLeadStartSeconds);
                    string triggerKey = $"{todayStr}_{p.Period}_countdown";

                    if (!_triggeredCountdowns.Contains(triggerKey))
                    {
                        double diffSec = (now - triggerDt).TotalSeconds;
                        if (diffSec >= 0 && diffSec <= 2)
                        {
                            _triggeredCountdowns.Add(triggerKey);
                            var overlay = new ClassroomCountdownOverlayWindow(effCfg, p.Name, p.Subject, _soundService);
                            overlay.Show();
                        }
                    }
                }
            }
        }

        // 2. Minute-level exact start and end chime alarms
        if (_lastTriggeredPeriodMinute == currentHm) return;
        var settings = _timetableService.Settings;

        foreach (var p in schedule)
        {
            if (!p.AlarmEnabled || p.IsLunch) continue;

            // Exact period start alarm
            if (settings.EnablePeriodAlarm && p.Start == currentHm)
            {
                _lastTriggeredPeriodMinute = currentHm;
                _soundService.PlayChime();
                HudNotificationWindow.Instance.ShowToast("🔔", $"[수업 시작] {p.Name} ({p.Subject}) 수업이 시작되었습니다!");
                return;
            }

            // Period end alarm
            if (settings.EnablePeriodEndAlarm && p.End == currentHm)
            {
                _lastTriggeredPeriodMinute = currentHm;
                _soundService.PlayChime();
                HudNotificationWindow.Instance.ShowToast("🔔", $"[쉬는 시간] {p.Name} 수업이 종료되었습니다!");
                return;
            }
        }
    }

    public void TestRunSchedule(RecurringScheduleItem item)
    {
        ExecuteAction(item, isTest: true);
    }

    private void ExecuteAction(RecurringScheduleItem item, bool isTest = false)
    {
        string prefix = isTest ? "[예약 테스트] " : "[예약 실행] ";

        switch (item.ActionType?.ToLowerInvariant())
        {
            case "alarm":
            default:
                _soundService.PlayChime();
                HudNotificationWindow.Instance.ShowToast("🔔", $"{prefix}{item.Title}");
                break;

            case "board":
                HudNotificationWindow.Instance.ShowToast("📋", $"{prefix}놀보드 실행: {item.Title}");
                break;

            case "shutdown":
                HudNotificationWindow.Instance.ShowToast("🛑", $"{prefix}PC 자동 종료: {item.Title}");
                if (!isTest)
                {
                    try
                    {
                        Process.Start(new ProcessStartInfo("shutdown", "/s /t 60 /c \"놀티쳐 예약에 의해 60초 후 PC가 자동 종료됩니다.\"") { CreateNoWindow = true });
                    }
                    catch { }
                }
                break;

            case "sleep":
                HudNotificationWindow.Instance.ShowToast("🌙", $"{prefix}PC 절전 모드: {item.Title}");
                break;

            case "restart":
                HudNotificationWindow.Instance.ShowToast("🔄", $"{prefix}PC 재시작: {item.Title}");
                if (!isTest)
                {
                    try
                    {
                        Process.Start(new ProcessStartInfo("shutdown", "/r /t 60 /c \"놀티쳐 예약에 의해 60초 후 PC가 재시작됩니다.\"") { CreateNoWindow = true });
                    }
                    catch { }
                }
                break;
        }
    }
}