using System;
using System.Diagnostics;
using System.IO;
using Microsoft.Win32;

namespace KnolTeacher.Desktop.Services;

public interface IStartupService
{
    bool IsStartupEnabled();
    bool SetStartupEnabled(bool enable);
}

public class StartupService : IStartupService
{
    private const string RunRegistryKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string AppName = "KnolTeacher";

    public bool IsStartupEnabled()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(RunRegistryKey, false);
            if (key == null) return false;

            var val = key.GetValue(AppName) as string;
            return !string.IsNullOrWhiteSpace(val);
        }
        catch
        {
            return false;
        }
    }

    public bool SetStartupEnabled(bool enable)
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(RunRegistryKey, true);
            if (key == null) return false;

            if (enable)
            {
                string exePath = GetExecutablePath();
                if (string.IsNullOrWhiteSpace(exePath) || !File.Exists(exePath))
                {
                    return false;
                }

                key.SetValue(AppName, $"\"{exePath}\"");
            }
            else
            {
                key.DeleteValue(AppName, false);
            }

            return true;
        }
        catch
        {
            return false;
        }
    }

    private static string GetExecutablePath()
    {
        string? path = Environment.ProcessPath;
        if (!string.IsNullOrWhiteSpace(path) && path.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
        {
            return path;
        }

        try
        {
            var p = Process.GetCurrentProcess();
            string? fileName = p.MainModule?.FileName;
            if (!string.IsNullOrWhiteSpace(fileName) && fileName.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
            {
                return fileName;
            }
        }
        catch { }

        string desktopPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "놀티쳐.exe");
        if (File.Exists(desktopPath))
        {
            return desktopPath;
        }

        return path ?? string.Empty;
    }
}
