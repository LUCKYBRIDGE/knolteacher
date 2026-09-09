using KnolTeacher.Desktop.Services;
using Xunit;

namespace KnolTeacher.Tests;

public class PopupLaunchPreferencesTests
{
    [Fact]
    public void NewPreferences_DefaultToRightClickSecondMonitorEnabled()
    {
        string dir = CreateTempDirectory();
        try
        {
            var preferences = new PopupLaunchPreferences(dir);
            Assert.True(preferences.RightClickOpensOnSecondMonitor);
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }

    [Fact]
    public void Preference_IsPersistedLocally()
    {
        string dir = CreateTempDirectory();
        try
        {
            var first = new PopupLaunchPreferences(dir)
            {
                RightClickOpensOnSecondMonitor = false
            };
            first.Save();

            var second = new PopupLaunchPreferences(dir);
            Assert.False(second.RightClickOpensOnSecondMonitor);
            Assert.True(File.Exists(Path.Combine(dir, "popup_display_settings.json")));
        }
        finally
        {
            Directory.Delete(dir, recursive: true);
        }
    }

    private static string CreateTempDirectory()
    {
        string path = Path.Combine(Path.GetTempPath(), "KnolTeacherTests", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(path);
        return path;
    }
}
