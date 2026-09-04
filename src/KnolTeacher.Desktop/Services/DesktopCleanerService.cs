using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using Microsoft.Win32;

namespace KnolTeacher.Desktop.Services;

public interface IDesktopCleanerService
{
    (bool Success, string Message, int MovedCount) OrganizeDesktop();
    (bool Success, string Message, int RestoredCount) UndoOrganize();
    (bool Success, bool IsVisible, string Message) ToggleDesktopIcons();
    (bool Success, string Message, int DeletedCount, double FreedMb) CleanTempAndDownloads(int daysOld = 30);
}

public class DesktopCleanerService : IDesktopCleanerService
{
    private readonly List<(string Source, string Dest)> _lastOrganizedRecords = new();

    private string DesktopPath => Environment.GetFolderPath(Environment.SpecialFolder.Desktop);
    private string DownloadsPath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");

    [DllImport("shell32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    private static extern void SHChangeNotify(uint wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);

    private const uint SHCNE_ASSOCCHANGED = 0x08000000;
    private const uint SHCNF_FLUSH = 0x1000;

    public (bool Success, string Message, int MovedCount) OrganizeDesktop()
    {
        string desktop = DesktopPath;
        if (!Directory.Exists(desktop))
        {
            return (false, "바탕화면 경로를 찾을 수 없습니다.", 0);
        }

        var categories = new Dictionary<string, HashSet<string>>(StringComparer.OrdinalIgnoreCase)
        {
            ["📁 [문서·수업자료]"] = new() { ".hwp", ".hwpx", ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".csv" },
            ["📁 [사진·이미지]"] = new() { ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".psd" },
            ["📁 [동영상·오디오]"] = new() { ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".mp3", ".wav", ".m4a", ".flac" },
            ["📁 [압축·설치파일]"] = new() { ".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".exe", ".msi" }
        };

        var protectedFiles = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "놀티쳐.exe", "놀티쳐 데스크.exe", "knolteacher.exe", "KnolTeacher.Desktop.exe", "desktop.ini"
        };

        _lastOrganizedRecords.Clear();
        int movedCount = 0;

        try
        {
            var files = Directory.GetFiles(desktop);
            foreach (var filePath in files)
            {
                string fileName = Path.GetFileName(filePath);
                string ext = Path.GetExtension(filePath);

                if (ext.Equals(".lnk", StringComparison.OrdinalIgnoreCase) || protectedFiles.Contains(fileName))
                {
                    continue;
                }

                string targetFolder = "📁 [기타 파일]";
                foreach (var kvp in categories)
                {
                    if (kvp.Value.Contains(ext))
                    {
                        targetFolder = kvp.Key;
                        break;
                    }
                }

                string targetDir = Path.Combine(desktop, targetFolder);
                Directory.CreateDirectory(targetDir);

                string dstPath = Path.Combine(targetDir, fileName);
                if (File.Exists(dstPath))
                {
                    string baseName = Path.GetFileNameWithoutExtension(fileName);
                    string ts = DateTime.Now.ToString("HHmmss");
                    dstPath = Path.Combine(targetDir, $"{baseName}_{ts}{ext}");
                }

                File.Move(filePath, dstPath);
                _lastOrganizedRecords.Add((filePath, dstPath));
                movedCount++;
            }

            if (movedCount > 0)
            {
                return (true, $"총 {movedCount}개의 파일을 성격별 폴더로 깔끔하게 정리했습니다!", movedCount);
            }
            return (true, "정리할 대상 파일이 없습니다. 이미 바탕화면이 깨끗합니다!", 0);
        }
        catch (Exception ex)
        {
            return (false, $"정리 중 오류 발생: {ex.Message}", movedCount);
        }
    }

    public (bool Success, string Message, int RestoredCount) UndoOrganize()
    {
        if (_lastOrganizedRecords.Count == 0)
        {
            return (false, "되돌릴 직전 정리 기록이 없습니다.", 0);
        }

        int restoredCount = 0;
        try
        {
            for (int i = _lastOrganizedRecords.Count - 1; i >= 0; i--)
            {
                var record = _lastOrganizedRecords[i];
                if (File.Exists(record.Dest))
                {
                    File.Move(record.Dest, record.Source);
                    restoredCount++;
                }
            }

            _lastOrganizedRecords.Clear();
            return (true, $"총 {restoredCount}개의 파일을 원래 자리로 복원했습니다!", restoredCount);
        }
        catch (Exception ex)
        {
            return (false, $"복원 중 오류 발생: {ex.Message}", restoredCount);
        }
    }

    public (bool Success, bool IsVisible, string Message) ToggleDesktopIcons()
    {
        const string keyPath = @"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced";
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(keyPath, true);
            if (key == null)
            {
                return (false, true, "레지스트리 키를 열 수 없습니다.");
            }

            object? val = key.GetValue("HideIcons");
            int currentVal = (val is int i) ? i : 0;
            int newVal = (currentVal == 0) ? 1 : 0;

            key.SetValue("HideIcons", newVal, RegistryValueKind.DWord);

            // Explorer Refresh
            SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_FLUSH, IntPtr.Zero, IntPtr.Zero);

            bool isVisible = (newVal == 0);
            string msg = isVisible ? "바탕화면 아이콘이 다시 표시되었습니다." : "수업 집중 모드: 바탕화면 아이콘이 모두 숨겨졌습니다.";
            return (true, isVisible, msg);
        }
        catch (Exception ex)
        {
            return (false, true, $"아이콘 토글 실패: {ex.Message}");
        }
    }

    public (bool Success, string Message, int DeletedCount, double FreedMb) CleanTempAndDownloads(int daysOld = 30)
    {
        int deletedCount = 0;
        long freedBytes = 0;
        var thresholdDate = DateTime.Now.AddDays(-daysOld);

        // 1. Temp Directory
        string tempDir = Path.GetTempPath();
        try
        {
            if (Directory.Exists(tempDir))
            {
                var files = Directory.GetFiles(tempDir);
                foreach (var f in files)
                {
                    try
                    {
                        var info = new FileInfo(f);
                        if (info.LastWriteTime < thresholdDate)
                        {
                            long len = info.Length;
                            File.Delete(f);
                            freedBytes += len;
                            deletedCount++;
                        }
                    }
                    catch { }
                }
            }

            double freedMb = Math.Round(freedBytes / (1024.0 * 1024.0), 2);
            return (true, $"임시 파일 {deletedCount}개 정리 완료! (총 {freedMb}MB 확보)", deletedCount, freedMb);
        }
        catch (Exception ex)
        {
            return (false, $"정리 중 오류: {ex.Message}", deletedCount, 0);
        }
    }
}
