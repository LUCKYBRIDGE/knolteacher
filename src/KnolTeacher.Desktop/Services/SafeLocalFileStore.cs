using System;
using System.IO;
using System.Text;

namespace KnolTeacher.Desktop.Services;

/// <summary>
/// Local-only persistence helper for small KnolTeacher text/JSON files.
/// Writes to a sibling temporary file, flushes it to disk, then atomically replaces
/// the destination while keeping one local .bak copy of the previous valid file.
/// No cloud or remote storage is involved.
/// </summary>
public static class SafeLocalFileStore
{
    public static string BackupPath(string path) => path + ".bak";

    public static string ReadAllTextWithBackup(string path, Encoding? encoding = null)
    {
        encoding ??= Encoding.UTF8;

        try
        {
            return File.ReadAllText(path, encoding);
        }
        catch when (File.Exists(BackupPath(path)))
        {
            return File.ReadAllText(BackupPath(path), encoding);
        }
    }

    public static bool TryReadAllTextWithBackup(string path, out string content, Encoding? encoding = null)
    {
        try
        {
            content = ReadAllTextWithBackup(path, encoding);
            return true;
        }
        catch
        {
            content = string.Empty;
            return false;
        }
    }

    public static void WriteAllTextAtomic(string path, string content, Encoding? encoding = null)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            throw new ArgumentException("A destination path is required.", nameof(path));
        }

        encoding ??= new UTF8Encoding(encoderShouldEmitUTF8Identifier: false);

        string? directory = Path.GetDirectoryName(path);
        if (!string.IsNullOrWhiteSpace(directory))
        {
            Directory.CreateDirectory(directory);
        }

        string tempPath = path + $".tmp.{Guid.NewGuid():N}";
        string backupPath = BackupPath(path);

        try
        {
            using (var stream = new FileStream(
                       tempPath,
                       FileMode.CreateNew,
                       FileAccess.Write,
                       FileShare.None,
                       4096,
                       FileOptions.WriteThrough))
            using (var writer = new StreamWriter(stream, encoding, 4096, leaveOpen: true))
            {
                writer.Write(content);
                writer.Flush();
                stream.Flush(flushToDisk: true);
            }

            if (File.Exists(path))
            {
                // File.Replace is atomic on the same Windows volume and creates/refreshes the backup.
                File.Replace(tempPath, path, backupPath, ignoreMetadataErrors: true);
            }
            else
            {
                File.Move(tempPath, path);
            }
        }
        catch
        {
            TryDelete(tempPath);
            throw;
        }
    }

    public static void DeletePrimaryAndBackup(string path)
    {
        TryDelete(path);
        TryDelete(BackupPath(path));
    }

    private static void TryDelete(string path)
    {
        try
        {
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
        catch
        {
            // Cleanup failures must not hide the original persistence result.
        }
    }
}
