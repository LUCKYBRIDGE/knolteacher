using KnolTeacher.Desktop.Services;
using Xunit;

namespace KnolTeacher.Tests;

public sealed class ConfigServicePersistenceTests : IDisposable
{
    private readonly string _root = Path.Combine(
        Path.GetTempPath(),
        "KnolTeacher.Config.Tests",
        Guid.NewGuid().ToString("N"));

    public ConfigServicePersistenceTests()
    {
        Directory.CreateDirectory(_root);
    }

    [Fact]
    public void TimerSettings_SaveAndReload_RoundTripsThroughLocalJsonStore()
    {
        var service = new ConfigService(_root)
        {
            TimerTargetMonitorIndex = 3
        };

        service.SaveTimerSettings();

        var reloaded = new ConfigService(_root);

        Assert.Equal(3, reloaded.TimerTargetMonitorIndex);
    }

    [Fact]
    public void CorruptedTimerPrimary_RecoversValidatedBackup()
    {
        var service = new ConfigService(_root)
        {
            TimerTargetMonitorIndex = 2
        };
        service.SaveTimerSettings();

        service.TimerTargetMonitorIndex = 4;
        service.SaveTimerSettings();

        string timerPath = Path.Combine(_root, "timer_settings.json");
        Assert.True(File.Exists(SafeLocalFileStore.BackupPath(timerPath)));

        // The backup contains the previously valid monitor index (2).
        File.WriteAllText(timerPath, "{ broken-json");

        var recovered = new ConfigService(_root);

        Assert.Equal(2, recovered.TimerTargetMonitorIndex);
        Assert.Contains("\"target_monitor_index\": 2", File.ReadAllText(timerPath));
    }

    [Fact]
    public void ExistingJsonFileNamesRemainBackwardCompatible()
    {
        File.WriteAllText(
            Path.Combine(_root, "timer_settings.json"),
            "{\"target_monitor_index\":5}");
        File.WriteAllText(
            Path.Combine(_root, "tutorial_state.json"),
            "{\"last_seen_version\":\"3.0.7\"}");

        var service = new ConfigService(_root);

        Assert.Equal(5, service.TimerTargetMonitorIndex);
        Assert.Equal("3.0.7", service.LastSeenTutorialVersion);
    }

    public void Dispose()
    {
        try
        {
            if (Directory.Exists(_root))
            {
                Directory.Delete(_root, recursive: true);
            }
        }
        catch
        {
            // Temp cleanup must not mask an assertion failure.
        }
    }
}
