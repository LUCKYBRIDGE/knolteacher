using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Text.Json.Serialization;
using System.Windows;
using System.Windows.Media;

namespace KnolTeacher.Desktop.Models;

public class PeriodItem : INotifyPropertyChanged
{
    private int _period;
    private string _name = string.Empty;
    private string _start = "09:00";
    private string _end = "09:40";
    private string _subject = string.Empty;
    private string _tag = "담임";
    private bool _isLunch;
    private bool _alarmEnabled = true;
    private bool _isCurrentPeriod;
    private string _alarmBadgeText = "🔔 5분전";
    private Brush _alarmBadgeBg = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#EEF2FF"));
    private Brush _alarmBadgeFg = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#4F46E5"));

    [JsonPropertyName("period")]
    public int Period
    {
        get => _period;
        set => SetField(ref _period, value);
    }

    [JsonPropertyName("name")]
    public string Name
    {
        get => _name;
        set => SetField(ref _name, value);
    }

    [JsonPropertyName("start")]
    public string Start
    {
        get => _start;
        set
        {
            if (SetField(ref _start, value))
                OnPropertyChanged(nameof(TimeRange));
        }
    }

    [JsonPropertyName("end")]
    public string End
    {
        get => _end;
        set
        {
            if (SetField(ref _end, value))
                OnPropertyChanged(nameof(TimeRange));
        }
    }

    [JsonPropertyName("subject")]
    public string Subject
    {
        get => _subject;
        set => SetField(ref _subject, value);
    }

    [JsonPropertyName("tag")]
    public string Tag
    {
        get => _tag;
        set => SetField(ref _tag, value);
    }

    [JsonPropertyName("is_lunch")]
    public bool IsLunch
    {
        get => _isLunch;
        set => SetField(ref _isLunch, value);
    }

    [JsonPropertyName("alarm_enabled")]
    public bool AlarmEnabled
    {
        get => _alarmEnabled;
        set => SetField(ref _alarmEnabled, value);
    }

    [JsonIgnore]
    public bool IsCurrentPeriod
    {
        get => _isCurrentPeriod;
        set => SetField(ref _isCurrentPeriod, value);
    }

    [JsonIgnore]
    public string TimeRange => $"{Start} ~ {End}";

    [JsonIgnore]
    public string DisplayBadge => IsLunch ? "점심" : $"{Period}교시";

    [JsonIgnore]
    public string AlarmBadgeText
    {
        get => _alarmBadgeText;
        set => SetField(ref _alarmBadgeText, value);
    }

    [JsonIgnore]
    public Brush AlarmBadgeBg
    {
        get => _alarmBadgeBg;
        set => SetField(ref _alarmBadgeBg, value);
    }

    [JsonIgnore]
    public Brush AlarmBadgeFg
    {
        get => _alarmBadgeFg;
        set => SetField(ref _alarmBadgeFg, value);
    }

    [JsonIgnore]
    public Visibility AlarmBadgeVisibility => IsLunch ? Visibility.Collapsed : Visibility.Visible;

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
