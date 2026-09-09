using System.Text.Json;
using KnolTeacher.Desktop.Services;
using Xunit;

namespace KnolTeacher.Tests;

public sealed class SafeLocalJsonStoreTests : IDisposable
{
    private readonly string _root = Path.Combine(
        Path.GetTempPath(),
        "KnolTeacher.Json.Tests",
        Guid.NewGuid().ToString("N"));

    private readonly JsonSerializerOptions _options = new()
    {
        WriteIndented = true
    };

    public SafeLocalJsonStoreTests()
    {
        Directory.CreateDirectory(_root);
    }

    [Fact]
    public void TrySaveAndLoad_RoundTripsValidPrimary()
    {
        string path = Path.Combine(_root, "settings.json");

        bool saved = SafeLocalJsonStore.TrySave(
            path,
            new SampleSettings { Number = 7, Label = "교실" },
            _options);
        bool loaded = SafeLocalJsonStore.TryLoad<SampleSettings>(path, _options, out var value);

        Assert.True(saved);
        Assert.True(loaded);
        Assert.NotNull(value);
        Assert.Equal(7, value.Number);
        Assert.Equal("교실", value.Label);
    }

    [Fact]
    public void InvalidPrimary_UsesValidatedBackupAndRepairsPrimary()
    {
        string path = Path.Combine(_root, "settings.json");

        Assert.True(SafeLocalJsonStore.TrySave(
            path,
            new SampleSettings { Number = 42, Label = "known-good" },
            _options));
        Assert.True(SafeLocalJsonStore.TrySave(
            path,
            new SampleSettings { Number = 99, Label = "newer" },
            _options));

        // The second atomic save leaves the first valid JSON in .bak.
        File.WriteAllText(path, "{ definitely-not-json");

        bool loaded = SafeLocalJsonStore.TryLoad<SampleSettings>(path, _options, out var recovered);

        Assert.True(loaded);
        Assert.NotNull(recovered);
        Assert.Equal(42, recovered.Number);
        Assert.Equal("known-good", recovered.Label);

        var repaired = JsonSerializer.Deserialize<SampleSettings>(File.ReadAllText(path), _options);
        Assert.NotNull(repaired);
        Assert.Equal(42, repaired.Number);
        Assert.Equal("known-good", repaired.Label);
    }

    [Fact]
    public void InvalidPrimaryAndInvalidBackup_ReturnsFalse()
    {
        string path = Path.Combine(_root, "settings.json");
        File.WriteAllText(path, "not-json");
        File.WriteAllText(SafeLocalFileStore.BackupPath(path), "also-not-json");

        bool loaded = SafeLocalJsonStore.TryLoad<SampleSettings>(path, _options, out var value);

        Assert.False(loaded);
        Assert.Null(value);
    }

    [Fact]
    public void MissingPrimary_UsesValidBackupAndRestoresPrimary()
    {
        string path = Path.Combine(_root, "settings.json");
        string backup = SafeLocalFileStore.BackupPath(path);
        File.WriteAllText(backup, JsonSerializer.Serialize(
            new SampleSettings { Number = 11, Label = "backup-only" },
            _options));

        bool loaded = SafeLocalJsonStore.TryLoad<SampleSettings>(path, _options, out var value);

        Assert.True(loaded);
        Assert.NotNull(value);
        Assert.Equal(11, value.Number);
        Assert.True(File.Exists(path));
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

    public sealed class SampleSettings
    {
        public int Number { get; set; }
        public string Label { get; set; } = string.Empty;
    }
}
