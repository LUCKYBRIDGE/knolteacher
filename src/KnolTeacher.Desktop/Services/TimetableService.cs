using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Services;

public interface ITimetableService
{
    TimetableSettings Settings { get; }
    event Action? OnTimetableChanged;

    List<PeriodItem> GetTodaySchedule();
    List<PeriodItem> GetPeriods();
    void SavePeriods(List<PeriodItem> periods);
    void ShiftAllPeriods(int minutesDelta);
    void UpdatePeriodSubject(string dayKey, int lessonIndex, string subject, string tag = "담임");
    void UpdateTodayPeriodSubject(int lessonIndex, string subject, string tag = "담임");
    void TogglePeriodAlarm(int periodNumber);
    void SetAllAlarms(bool enabled);
    void SaveSettings();
    (PeriodItem? currentPeriod, int remainingMinutes) GetCurrentPeriodStatus();
}

public class TimetableService : ITimetableService
{
    private readonly IConfigService _configService;
    private readonly string _periodsFile;
    private readonly string _timetableFile;
    private readonly JsonSerializerOptions _jsonOptions = new() { WriteIndented = true, PropertyNameCaseInsensitive = true };

    private List<PeriodItem> _periods = new();
    private Dictionary<string, List<Dictionary<string, string>>> _weeklyTimetable = new();

    public TimetableSettings Settings => _configService.TimetableSettings;

    public event Action? OnTimetableChanged;

    private static readonly string[] DayKeys = { "mon", "tue", "wed", "thu", "fri" };

    public TimetableService(IConfigService configService)
    {
        _configService = configService;
        _periodsFile = Path.Combine(_configService.ConfigDir, "schedule_periods.json");
        _timetableFile = Path.Combine(_configService.ConfigDir, "custom_timetable.json");

        LoadPeriods();
        LoadWeeklyTimetable();
    }

    private void LoadPeriods()
    {
        if (File.Exists(_periodsFile))
        {
            try
            {
                string json = File.ReadAllText(_periodsFile);
                var list = JsonSerializer.Deserialize<List<PeriodItem>>(json, _jsonOptions);
                if (list != null && list.Count > 0)
                {
                    _periods = list;
                    return;
                }
            }
            catch { }
        }

        // Default Korean Elementary School periods (9:10 start, lunch 12:20~13:20)
        _periods = new List<PeriodItem>
        {
            new() { Period = 1, Name = "1교시", Start = "09:10", End = "09:50", IsLunch = false, AlarmEnabled = true },
            new() { Period = 2, Name = "2교시", Start = "10:00", End = "10:40", IsLunch = false, AlarmEnabled = true },
            new() { Period = 3, Name = "3교시", Start = "10:50", End = "11:30", IsLunch = false, AlarmEnabled = true },
            new() { Period = 4, Name = "4교시", Start = "11:40", End = "12:20", IsLunch = false, AlarmEnabled = true },
            new() { Period = 0, Name = "점심시간", Start = "12:20", End = "13:20", IsLunch = true, AlarmEnabled = false },
            new() { Period = 5, Name = "5교시", Start = "13:20", End = "14:00", IsLunch = false, AlarmEnabled = true },
            new() { Period = 6, Name = "6교시", Start = "14:10", End = "14:50", IsLunch = false, AlarmEnabled = true },
            new() { Period = 7, Name = "7교시", Start = "15:00", End = "15:40", IsLunch = false, AlarmEnabled = false }
        };
        SavePeriods(_periods);
    }

    private void LoadWeeklyTimetable()
    {
        if (File.Exists(_timetableFile))
        {
            try
            {
                string json = File.ReadAllText(_timetableFile);
                var dict = JsonSerializer.Deserialize<Dictionary<string, List<Dictionary<string, string>>>>(json, _jsonOptions);
                if (dict != null && dict.Count > 0)
                {
                    _weeklyTimetable = dict;
                    return;
                }
            }
            catch { }
        }

        // Standard default schedule
        _weeklyTimetable = new Dictionary<string, List<Dictionary<string, string>>>
        {
            ["mon"] = new()
            {
                new() { ["subject"] = "국어", ["tag"] = "담임" },
                new() { ["subject"] = "수학", ["tag"] = "담임" },
                new() { ["subject"] = "사회", ["tag"] = "담임" },
                new() { ["subject"] = "과학", ["tag"] = "전담" },
                new() { ["subject"] = "음악", ["tag"] = "전담" },
                new() { ["subject"] = "체육", ["tag"] = "외강" },
                new() { ["subject"] = "", ["tag"] = "담임" }
            },
            ["tue"] = new()
            {
                new() { ["subject"] = "수학", ["tag"] = "담임" },
                new() { ["subject"] = "국어", ["tag"] = "담임" },
                new() { ["subject"] = "체육", ["tag"] = "외강" },
                new() { ["subject"] = "도덕", ["tag"] = "담임" },
                new() { ["subject"] = "영어", ["tag"] = "전담" },
                new() { ["subject"] = "미술", ["tag"] = "전담" },
                new() { ["subject"] = "", ["tag"] = "담임" }
            },
            ["wed"] = new()
            {
                new() { ["subject"] = "국어", ["tag"] = "담임" },
                new() { ["subject"] = "사회", ["tag"] = "담임" },
                new() { ["subject"] = "수학", ["tag"] = "담임" },
                new() { ["subject"] = "과학", ["tag"] = "전담" },
                new() { ["subject"] = "창체", ["tag"] = "담임" },
                new() { ["subject"] = "", ["tag"] = "담임" },
                new() { ["subject"] = "", ["tag"] = "담임" }
            },
            ["thu"] = new()
            {
                new() { ["subject"] = "영어", ["tag"] = "전담" },
                new() { ["subject"] = "수학", ["tag"] = "담임" },
                new() { ["subject"] = "국어", ["tag"] = "담임" },
                new() { ["subject"] = "음악", ["tag"] = "전담" },
                new() { ["subject"] = "실과", ["tag"] = "담임" },
                new() { ["subject"] = "체육", ["tag"] = "외강" },
                new() { ["subject"] = "", ["tag"] = "담임" }
            },
            ["fri"] = new()
            {
                new() { ["subject"] = "사회", ["tag"] = "담임" },
                new() { ["subject"] = "국어", ["tag"] = "담임" },
                new() { ["subject"] = "수학", ["tag"] = "담임" },
                new() { ["subject"] = "미술", ["tag"] = "전담" },
                new() { ["subject"] = "창체", ["tag"] = "담임" },
                new() { ["subject"] = "동아리", ["tag"] = "외강" },
                new() { ["subject"] = "", ["tag"] = "담임" }
            }
        };
        SaveWeeklyTimetable();
    }

    public List<PeriodItem> GetPeriods() => _periods;

    public void SavePeriods(List<PeriodItem> periods)
    {
        _periods = periods;
        try
        {
            string json = JsonSerializer.Serialize(_periods, _jsonOptions);
            File.WriteAllText(_periodsFile, json);
            OnTimetableChanged?.Invoke();
        }
        catch { }
    }

    private void SaveWeeklyTimetable()
    {
        try
        {
            string json = JsonSerializer.Serialize(_weeklyTimetable, _jsonOptions);
            File.WriteAllText(_timetableFile, json);
            OnTimetableChanged?.Invoke();
        }
        catch { }
    }

    public void SaveSettings()
    {
        _configService.SaveTimetableSettings();
        OnTimetableChanged?.Invoke();
    }

    public void ShiftAllPeriods(int minutesDelta)
    {
        string ShiftTime(string timeStr, int delta)
        {
            if (TimeSpan.TryParse(timeStr, out var ts))
            {
                var newTs = ts.Add(TimeSpan.FromMinutes(delta));
                if (newTs < TimeSpan.Zero) newTs = TimeSpan.Zero;
                if (newTs >= TimeSpan.FromHours(24)) newTs = TimeSpan.FromHours(23).Add(TimeSpan.FromMinutes(59));
                return $"{newTs.Hours:D2}:{newTs.Minutes:D2}";
            }
            return timeStr;
        }

        foreach (var p in _periods)
        {
            p.Start = ShiftTime(p.Start, minutesDelta);
            p.End = ShiftTime(p.End, minutesDelta);
        }

        SavePeriods(_periods);
    }

    public void UpdatePeriodSubject(string dayKey, int lessonIndex, string subject, string tag = "담임")
    {
        if (!_weeklyTimetable.ContainsKey(dayKey))
        {
            _weeklyTimetable[dayKey] = new List<Dictionary<string, string>>();
        }

        while (_weeklyTimetable[dayKey].Count <= lessonIndex)
        {
            _weeklyTimetable[dayKey].Add(new() { ["subject"] = "", ["tag"] = "담임" });
        }

        _weeklyTimetable[dayKey][lessonIndex] = new Dictionary<string, string>
        {
            ["subject"] = subject.Trim(),
            ["tag"] = tag
        };

        SaveWeeklyTimetable();
    }

    public void UpdateTodayPeriodSubject(int lessonIndex, string subject, string tag = "담임")
    {
        int w = (int)DateTime.Now.DayOfWeek;
        int idx = w == 0 ? 6 : w - 1; // 0=Mon, 4=Fri
        if (idx >= 0 && idx < DayKeys.Length)
        {
            UpdatePeriodSubject(DayKeys[idx], lessonIndex, subject, tag);
        }
    }

    public void TogglePeriodAlarm(int periodNumber)
    {
        var target = _periods.FirstOrDefault(p => p.Period == periodNumber);
        if (target != null)
        {
            target.AlarmEnabled = !target.AlarmEnabled;
            SavePeriods(_periods);
        }
    }

    public void SetAllAlarms(bool enabled)
    {
        foreach (var p in _periods)
        {
            if (!p.IsLunch)
            {
                p.AlarmEnabled = enabled;
            }
        }
        Settings.EnablePeriodAlarm = enabled;
        SaveSettings();
        SavePeriods(_periods);
    }

    public List<PeriodItem> GetTodaySchedule()
    {
        var now = DateTime.Now;
        int w = (int)now.DayOfWeek;
        int dayIdx = w == 0 ? 6 : w - 1;

        string dayKey = (dayIdx >= 0 && dayIdx < DayKeys.Length) ? DayKeys[dayIdx] : "";
        var subjectsData = _weeklyTimetable.TryGetValue(dayKey, out var subs) ? subs : new();

        var result = new List<PeriodItem>();
        int lessonIdx = 0;
        string currentHm = now.ToString("HH:mm");

        foreach (var p in _periods)
        {
            if (p.Period == 7 && !Settings.EnablePeriod7) continue;

            var copy = new PeriodItem
            {
                Period = p.Period,
                Name = p.Name,
                Start = p.Start,
                End = p.End,
                IsLunch = p.IsLunch,
                AlarmEnabled = p.AlarmEnabled
            };

            if (p.IsLunch)
            {
                copy.Subject = "🍱 점심식사 및 휴식";
                copy.Tag = "점심";
            }
            else
            {
                if (lessonIdx < subjectsData.Count)
                {
                    copy.Subject = subjectsData[lessonIdx].TryGetValue("subject", out var s) ? s : "";
                    copy.Tag = subjectsData[lessonIdx].TryGetValue("tag", out var t) ? t : "담임";
                }
                else
                {
                    copy.Subject = "자율수업";
                    copy.Tag = "담임";
                }
                lessonIdx++;
            }

            // Current active period check
            copy.IsCurrentPeriod = string.Compare(currentHm, copy.Start) >= 0 && string.Compare(currentHm, copy.End) <= 0;
            result.Add(copy);
        }

        return result;
    }

    public (PeriodItem? currentPeriod, int remainingMinutes) GetCurrentPeriodStatus()
    {
        var schedule = GetTodaySchedule();
        var now = DateTime.Now;
        var currentHm = now.ToString("HH:mm");

        var cur = schedule.FirstOrDefault(p => string.Compare(currentHm, p.Start) >= 0 && string.Compare(currentHm, p.End) <= 0);
        if (cur != null && TimeSpan.TryParse(cur.End, out var endTs))
        {
            var endDt = new DateTime(now.Year, now.Month, now.Day, endTs.Hours, endTs.Minutes, 0);
            int rem = Math.Max(0, (int)(endDt - now).TotalMinutes);
            return (cur, rem);
        }

        return (null, 0);
    }
}
