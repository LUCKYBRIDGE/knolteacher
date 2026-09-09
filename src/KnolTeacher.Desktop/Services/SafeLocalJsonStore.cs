using System.Diagnostics;
using System.IO;
using System.Text.Json;

namespace KnolTeacher.Desktop.Services;

/// <summary>
/// JSON-specific layer on top of <see cref="SafeLocalFileStore"/>.
/// A primary file is accepted only when it can be deserialized successfully.
/// If the primary is missing, unreadable, or invalid JSON, a valid local .bak file
/// is used and the primary is repaired on a best-effort basis. No remote storage is used.
/// </summary>
public static class SafeLocalJsonStore
{
    public static bool TryLoad<T>(
        string path,
        JsonSerializerOptions options,
        out T? value)
        where T : class
    {
        if (TryDeserialize(path, options, out value))
        {
            return true;
        }

        string backupPath = SafeLocalFileStore.BackupPath(path);
        if (!TryDeserialize(backupPath, options, out value))
        {
            value = null;
            return false;
        }

        // The backup has already been validated as JSON before it is trusted.
        // Repairing the primary is intentionally best-effort: callers can still use
        // the valid in-memory value even if the local filesystem blocks the repair.
        SafeLocalFileStore.TryRestorePrimaryFromBackup(path);
        return true;
    }

    public static bool TrySave<T>(
        string path,
        T value,
        JsonSerializerOptions options,
        bool preserveExistingBackup = false,
        bool scrubPreviousContent = false)
    {
        try
        {
            string json = JsonSerializer.Serialize(value, options);
            SafeLocalFileStore.WriteAllTextAtomic(
                path,
                json,
                preserveExistingBackup: preserveExistingBackup,
                scrubPreviousContent: scrubPreviousContent);
            return true;
        }
        catch (Exception ex)
        {
            TraceFailure("save", path, ex);
            return false;
        }
    }

    private static bool TryDeserialize<T>(
        string path,
        JsonSerializerOptions options,
        out T? value)
        where T : class
    {
        value = null;
        if (!File.Exists(path))
        {
            return false;
        }

        try
        {
            string json = File.ReadAllText(path);
            value = JsonSerializer.Deserialize<T>(json, options);
            return value != null;
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or JsonException or NotSupportedException)
        {
            TraceFailure("load", path, ex);
            value = null;
            return false;
        }
    }

    private static void TraceFailure(string operation, string path, Exception ex)
    {
        // Never log file contents or student/teacher data. File name + exception type is sufficient.
        Debug.WriteLine(
            $"[SafeLocalJsonStore] {operation} failed for '{Path.GetFileName(path)}': {ex.GetType().Name}");
    }
}
