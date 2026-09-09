using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace KnolTeacher.Desktop.Services;

/// <summary>
/// Local-only preference for deciding how explicit popup/window launch gestures map to displays.
/// This setting never contains student data and is persisted only in the KnolTeacher config folder.
/// </summary>
public sealed class PopupLaunchPreferences
{
    private const string FileName = "popup_display_settings.json";
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };
    private readonly string _path;

    public bool RightClickOpensOnSecondMonitor { get; set; } = true;

    public PopupLaunchPreferences(string configDir)
    {
        _path = Path.Combine(configDir, FileName);
        Load();
    }

    public void Save()
    {
        SafeLocalJsonStore.TrySave(_path, new PopupDisplaySettingsData
        {
            RightClickOpensOnSecondMonitor = RightClickOpensOnSecondMonitor
        }, JsonOptions);
    }

    private void Load()
    {
        if (SafeLocalJsonStore.TryLoad<PopupDisplaySettingsData>(_path, JsonOptions, out var data) && data != null)
        {
            RightClickOpensOnSecondMonitor = data.RightClickOpensOnSecondMonitor;
        }
        else
        {
            // Product default: enabled. A right-click on a confirmed popup launcher targets monitor 2.
            RightClickOpensOnSecondMonitor = true;
        }
    }

    private sealed class PopupDisplaySettingsData
    {
        [JsonPropertyName("right_click_opens_on_second_monitor")]
        public bool RightClickOpensOnSecondMonitor { get; set; } = true;
    }
}
