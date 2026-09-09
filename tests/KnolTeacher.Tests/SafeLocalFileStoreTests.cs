using System.Text;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Tests;

public sealed class SafeLocalFileStoreTests : IDisposable
{
    private readonly string _root = Path.Combine(
        Path.GetTempPath(),
        "KnolTeacher.Tests",
        Guid.NewGuid().ToString("N"));

    public SafeLocalFileStoreTests()
    {
        Directory.CreateDirectory(_root);
    }

    [Fact]
    public void FirstWrite_CreatesPrimaryWithoutBackup()
    {
        string path = Path.Combine(_root, "settings.json");

        SafeLocalFileStore.WriteAllTextAtomic(path, "first");

        Assert.Equal("first", File.ReadAllText(path, Encoding.UTF8));
        Assert.False(File.Exists(SafeLocalFileStore.BackupPath(path)));
    }

    [Fact]
    public void SecondWrite_CreatesBackupOfPreviousPrimary()
    {
        string path = Path.Combine(_root, "settings.json");

        SafeLocalFileStore.WriteAllTextAtomic(path, "first");
        SafeLocalFileStore.WriteAllTextAtomic(path, "second");

        Assert.Equal("second", File.ReadAllText(path, Encoding.UTF8));
        Assert.Equal("first", File.ReadAllText(SafeLocalFileStore.BackupPath(path), Encoding.UTF8));
    }

    [Fact]
    public void RestoreFromBackup_RepairsPrimaryAndPreservesKnownGoodBackup()
    {
        string path = Path.Combine(_root, "settings.json");

        SafeLocalFileStore.WriteAllTextAtomic(path, "known-good");
        SafeLocalFileStore.WriteAllTextAtomic(path, "corrupted-primary");

        bool restored = SafeLocalFileStore.TryRestorePrimaryFromBackup(path);

        Assert.True(restored);
        Assert.Equal("known-good", File.ReadAllText(path, Encoding.UTF8));
        Assert.Equal("known-good", File.ReadAllText(SafeLocalFileStore.BackupPath(path), Encoding.UTF8));
    }

    [Fact]
    public void PreserveExistingBackup_DoesNotReplaceKnownGoodBackup()
    {
        string path = Path.Combine(_root, "settings.json");

        SafeLocalFileStore.WriteAllTextAtomic(path, "known-good");
        SafeLocalFileStore.WriteAllTextAtomic(path, "untrusted-primary");
        SafeLocalFileStore.WriteAllTextAtomic(path, "new-primary", preserveExistingBackup: true);

        Assert.Equal("new-primary", File.ReadAllText(path, Encoding.UTF8));
        Assert.Equal("known-good", File.ReadAllText(SafeLocalFileStore.BackupPath(path), Encoding.UTF8));
    }

    [Fact]
    public void ScrubPreviousContent_ReplacesPrimaryAndBackupWithSanitizedSnapshot()
    {
        string path = Path.Combine(_root, "student_roster.json");
        const string personal = "{\"name\":\"홍길동\",\"contact\":\"010-0000-0000\"}";
        const string sanitized = "{\"number\":1,\"avatar_id\":\"avatar_01\"}";

        SafeLocalFileStore.WriteAllTextAtomic(path, personal);
        SafeLocalFileStore.WriteAllTextAtomic(path, personal + " ");
        SafeLocalFileStore.WriteAllTextAtomic(path, sanitized, scrubPreviousContent: true);

        string primary = File.ReadAllText(path, Encoding.UTF8);
        string backup = File.ReadAllText(SafeLocalFileStore.BackupPath(path), Encoding.UTF8);

        Assert.Equal(sanitized, primary);
        Assert.Equal(sanitized, backup);
        Assert.DoesNotContain("홍길동", primary);
        Assert.DoesNotContain("홍길동", backup);
        Assert.DoesNotContain("010-0000-0000", primary);
        Assert.DoesNotContain("010-0000-0000", backup);
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
