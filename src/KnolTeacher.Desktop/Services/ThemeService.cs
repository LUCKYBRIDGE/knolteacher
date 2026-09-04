using System;
using System.Windows;
using System.Windows.Media;

namespace KnolTeacher.Desktop.Services;

public interface IThemeService
{
    string CurrentTheme { get; }
    void ApplyTheme(string themeName);
}

public class ThemeService : IThemeService
{
    private readonly IConfigService _configService;

    public string CurrentTheme { get; private set; } = "Beige";

    public ThemeService(IConfigService configService)
    {
        _configService = configService;
        CurrentTheme = _configService.TimetableSettings.ThemeMode;
        if (string.IsNullOrEmpty(CurrentTheme)) CurrentTheme = "Beige";
    }

    public void ApplyTheme(string themeName)
    {
        CurrentTheme = themeName;
        _configService.TimetableSettings.ThemeMode = themeName;
        _configService.SaveTimetableSettings();

        var res = Application.Current.Resources;

        if (themeName == "Dark")
        {
            // 🌙 Slate Dark Studio
            SetBrush(res, "BeigeAppBg", "#0B0F19");
            SetBrush(res, "BeigeSidebarBg", "#111827");
            SetBrush(res, "BeigeSidebarHover", "#1F2937");
            SetBrush(res, "BeigeAccent", "#38BDF8");
            SetBrush(res, "BeigeAccentHover", "#0284C7");
            SetBrush(res, "BeigeAccentSoft", "#0C4A6E");
            SetBrush(res, "BeigeCardBg", "#161F30");
            SetBrush(res, "BeigeCardInner", "#111622");
            SetBrush(res, "BeigeCardBorder", "#26354D");
            SetBrush(res, "BeigeTextMain", "#F8FAFC");
            SetBrush(res, "BeigeTextSub", "#CBD5E1");
            SetBrush(res, "BeigeTextMuted", "#64748B");
            SetBrush(res, "BeigeLunchBg", "#141E30");
            SetBrush(res, "BeigeLunchBorder", "#293548");
            SetBrush(res, "BeigeLunchText", "#38BDF8");
        }
        else if (themeName == "Light")
        {
            // 🌊 Modern Fluent Sky (Clean Light)
            SetBrush(res, "BeigeAppBg", "#F1F5F9");
            SetBrush(res, "BeigeSidebarBg", "#E2E8F0");
            SetBrush(res, "BeigeSidebarHover", "#CBD5E1");
            SetBrush(res, "BeigeAccent", "#0284C7");
            SetBrush(res, "BeigeAccentHover", "#0369A1");
            SetBrush(res, "BeigeAccentSoft", "#E0F2FE");
            SetBrush(res, "BeigeCardBg", "#FFFFFF");
            SetBrush(res, "BeigeCardInner", "#F8FAFC");
            SetBrush(res, "BeigeCardBorder", "#E2E8F0");
            SetBrush(res, "BeigeTextMain", "#0F172A");
            SetBrush(res, "BeigeTextSub", "#334155");
            SetBrush(res, "BeigeTextMuted", "#64748B");
            SetBrush(res, "BeigeLunchBg", "#F0F9FF");
            SetBrush(res, "BeigeLunchBorder", "#BAE6FD");
            SetBrush(res, "BeigeLunchText", "#0284C7");
        }
        else
        {
            // 🌾 Classic Warm Beige (Default)
            SetBrush(res, "BeigeAppBg", "#F8F5EE");
            SetBrush(res, "BeigeSidebarBg", "#ECE3D4");
            SetBrush(res, "BeigeSidebarHover", "#DFD2BE");
            SetBrush(res, "BeigeAccent", "#B45309");
            SetBrush(res, "BeigeAccentHover", "#92400E");
            SetBrush(res, "BeigeAccentSoft", "#FEF3C7");
            SetBrush(res, "BeigeCardBg", "#FFFFFF");
            SetBrush(res, "BeigeCardInner", "#FCFBF9");
            SetBrush(res, "BeigeCardBorder", "#DBCDBA");
            SetBrush(res, "BeigeTextMain", "#1C1917");
            SetBrush(res, "BeigeTextSub", "#44403C");
            SetBrush(res, "BeigeTextMuted", "#78716C");
            SetBrush(res, "BeigeLunchBg", "#FBF7F0");
            SetBrush(res, "BeigeLunchBorder", "#E7DAC7");
            SetBrush(res, "BeigeLunchText", "#92400E");
        }
    }

    private static void SetBrush(ResourceDictionary res, string key, string hex)
    {
        var color = (Color)ColorConverter.ConvertFromString(hex);
        if (res.Contains(key))
        {
            res[key] = new SolidColorBrush(color);
        }
        else
        {
            res.Add(key, new SolidColorBrush(color));
        }
    }
}
