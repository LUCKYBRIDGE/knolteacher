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
    private readonly IDisplayManager? _displayManager;
    private readonly DispatcherTimer _timer;
    private string _lastTriggeredScheduleMinute = string.Empty;
    private string _lastTriggeredPeriodMinute = string.Empty;
    private readonly HashSet<string> _triggeredCountdowns = new();
    private readonly HashSet<string> _triggeredAdvanceWarnings = new();
    private readonly HashSet<string> _triggeredCalendarAlarms = new();

    public SchedulerService(
        IConfigService configService,
        ISoundService soundService,
        ITimetableService timetableService,
        IDisplayManager? displayManager = null)
    {
        _configService = configService;
        _soundService = soundService;
        _timetableService = timetableService;
        _displayManager = displayManager;

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

        CheckAdvanceWarnings(now, currentHm, todayDate);
        CheckSchedules(now, currentHm, todayDate);
        CheckTimetableAlarms(now, currentHm);
        CheckCalendarEventAlarms(now, currentHm, todayDate);
    }

    private void CheckAdvanceWarnings(DateTime now, string currentHm, string todayDate)
    {
        int dayIndex = (int)now.DayOfWeek;
        int scheduleDay = dayIndex == 0 ? 6 : dayIndex - 1; // 0=Mon, 6=Sun

        var schedules = _configService.RecurringSchedules;
        if (schedules == null) return;

        if (_triggeredAdvanceWarnings.Count > 100)
        {
            _triggeredAdvanceWarnings.RemoveWhere(k => !k.StartsWith(todayDate));
        }

        foreach (var item in schedules)
        {
            if (!item.Enabled) continue;
            if (!item.EnableAdvanceWarning) continue;

            int advanceMinutes = item.AdvanceWarningMinutes > 0 ? item.AdvanceWarningMinutes : 5;

            // Day matching check
            if (item.IsSingle)
            {
                if (item.IsCompleted) continue;
                if (!string.IsNullOrEmpty(item.TargetDate) && item.TargetDate != todayDate) continue;
            }
            else
            {
                if (item.RepeatDays != null && item.RepeatDays.Count > 0 && !item.RepeatDays.Contains(scheduleDay))
                {
                    continue;
                }
            }

            if (!TimeSpan.TryParse(item.TimeString, out var targetTime)) continue;

            var targetDt = DateTime.Today.Add(targetTime);
            var advanceTriggerDt = targetDt.AddMinutes(-advanceMinutes);

            string advKey = $"{todayDate}_{item.Id}_advance";
            if (_triggeredAdvanceWarnings.Contains(advKey)) continue;

            if (advanceTriggerDt.ToString("HH:mm") == currentHm)
            {
                _triggeredAdvanceWarnings.Add(advKey);

                try
                {
                    _soundService.PlayAttentionChime();
                }
                catch
                {
                    _soundService.PlayChime();
                }

                // Show advance notice on Teacher Monitor 1
                HudNotificationWindow.Instance.ShowToast(
                    "⏰",
                    $"[사전 알림] {advanceMinutes}분 후 '{item.Title}' 예약이 실행됩니다. (수업 마무리 준비)",
                    durationMs: 4500
                );
            }
        }
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

        // 1. If student popup or timer is enabled for this schedule, trigger student display window on Monitor 2
        if (item.ShowStudentPopup || item.ShowTimer || string.Equals(item.ActionType, "popup", StringComparison.OrdinalIgnoreCase))
        {
            try
            {
                var modal = new StudentAlertModalWindow(
                    title: item.Title,
                    message: string.IsNullOrWhiteSpace(item.PopupMessage) ? "선생님의 지도와 안내에 따라 질서 있게 행동합시다." : item.PopupMessage,
                    showTimer: item.ShowTimer,
                    timerMinutes: item.TimerDurationMinutes > 0 ? item.TimerDurationMinutes : 10,
                    soundService: _soundService,
                    emoji: GetScheduleEmoji(item.Title, item.ActionType),
                    category: isTest ? "교실 알림 (테스트)" : "예약 교실 알림"
                );

                if (_displayManager != null)
                {
                    _displayManager.MoveToStudentMonitor(modal, maximize: true);
                }
                modal.Show();
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SchedulerService] Failed to show student modal: {ex.Message}");
            }
        }

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

    private static string GetScheduleEmoji(string title, string? actionType)
    {
        if (title.Contains("청소")) return "🧹";
        if (title.Contains("하교") || title.Contains("퇴근") || title.Contains("종례")) return "🎒";
        if (title.Contains("급식") || title.Contains("점심")) return "🍱";
        if (title.Contains("독서") || title.Contains("책")) return "📚";
        if (title.Contains("운동") || title.Contains("체육")) return "🏃";
        if (title.Contains("휴식") || title.Contains("쉬는")) return "☕";
        if (title.Contains("시험") || title.Contains("평가")) return "📝";
        if (actionType == "shutdown") return "🛑";
        if (actionType == "sleep") return "🌙";
        if (actionType == "restart") return "🔄";
        return "📢";
    }

    private void CheckCalendarEventAlarms(DateTime now, string currentHm, string todayDate)
    {
        var events = _configService.TeacherCalendarEvents;
        if (events == null || events.Count == 0) return;

        if (_triggeredCalendarAlarms.Count > 100)
        {
            _triggeredCalendarAlarms.RemoveWhere(k => !k.StartsWith(todayDate));
        }

        bool hasUpdated = false;

        foreach (var ev in events)
        {
            if (!ev.HasAlarm || ev.IsAlarmTriggered) continue;
            if (ev.Date != todayDate) continue;

            string alarmKey = $"{todayDate}_{ev.Id}";
            if (_triggeredCalendarAlarms.Contains(alarmKey)) continue;

            DateTime targetAlarmTime;
            if (ev.IsAllDay)
            {
                // 종일 일정: 당일 아침 08:30 알람
                targetAlarmTime = DateTime.Today.AddHours(8).AddMinutes(30);
            }
            else if (TimeSpan.TryParse(ev.Time, out var eventTime))
            {
                var eventDt = DateTime.Today.Add(eventTime);
                targetAlarmTime = eventDt.AddMinutes(-ev.AlarmMinutesBefore);
            }
            else
            {
                continue;
            }

            if (targetAlarmTime.ToString("HH:mm") == currentHm)
            {
                _triggeredCalendarAlarms.Add(alarmKey);
                ev.IsAlarmTriggered = true;
                hasUpdated = true;

                try
                {
                    _soundService.PlayAttentionChime();
                }
                catch
                {
                    _soundService.PlayChime();
                }

                string offsetDesc = ev.IsAllDay
                    ? "오늘의 일정"
                    : (ev.AlarmMinutesBefore == 0 ? "지금 시작" : $"{ev.AlarmMinutesBefore}분 전");

                string memoText = string.IsNullOrWhiteSpace(ev.Memo) ? "" : $"\n• {ev.Memo}";
                HudNotificationWindow.Instance.ShowToast(
                    "🗓️",
                    $"[캘린더 알림] {ev.Title} ({offsetDesc}){memoText}",
                    durationMs: 5500
                );
            }
        }

        if (hasUpdated)
        {
            _configService.SaveTeacherCalendarEvents();
        }
    }
}