using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Reflection;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;

namespace KnolTeacher.Desktop.Services;

public class UpdateService : IUpdateService
{
    public const string FallbackVersion = "v3.0.2";

    public string CurrentVersion
    {
        get
        {
            try
            {
                var ver = Assembly.GetExecutingAssembly().GetName().Version;
                return ver != null ? $"v{ver.Major}.{ver.Minor}.{ver.Build}" : FallbackVersion;
            }
            catch
            {
                return FallbackVersion;
            }
        }
    }

    public async Task<UpdateInfo> CheckForUpdatesAsync()
    {
        var result = new UpdateInfo
        {
            CurrentVersion = CurrentVersion,
            HasUpdate = false
        };

        try
        {
            using var client = new HttpClient();
            client.DefaultRequestHeaders.UserAgent.ParseAdd("KnolTeacherApp");
            client.Timeout = TimeSpan.FromSeconds(5);

            var resp = await client.GetAsync("https://api.github.com/repos/LUCKYBRIDGE/knolteacher/releases/latest");
            if (!resp.IsSuccessStatusCode)
            {
                return result;
            }

            string json = await resp.Content.ReadAsStringAsync();
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            string latestTag = root.GetProperty("tag_name").GetString() ?? "";
            string releaseTitle = root.TryGetProperty("name", out var nameProp) ? nameProp.GetString() ?? "" : "";
            string releaseNotes = root.TryGetProperty("body", out var bodyProp) ? bodyProp.GetString() ?? "" : "";
            string htmlUrl = root.TryGetProperty("html_url", out var htmlProp) ? htmlProp.GetString() ?? "" : "";

            result.LatestVersion = latestTag;
            result.ReleaseTitle = string.IsNullOrWhiteSpace(releaseTitle) ? latestTag : releaseTitle;
            result.ReleaseNotes = releaseNotes;
            result.HtmlUrl = htmlUrl;

            // Check if latestTag > CurrentVersion
            result.HasUpdate = IsNewerVersion(latestTag, CurrentVersion);

            // Find executable asset (.exe)
            if (root.TryGetProperty("assets", out var assetsProp) && assetsProp.ValueKind == JsonValueKind.Array)
            {
                foreach (var asset in assetsProp.EnumerateArray())
                {
                    string name = asset.GetProperty("name").GetString() ?? "";
                    string downloadUrl = asset.GetProperty("browser_download_url").GetString() ?? "";
                    long size = asset.TryGetProperty("size", out var sizeProp) ? sizeProp.GetInt64() : 0;

                    if (name.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
                    {
                        result.AssetName = name;
                        result.DownloadUrl = downloadUrl;
                        result.AssetSize = size;
                        break;
                    }
                }

                // Fallback to first asset if no .exe found
                if (string.IsNullOrEmpty(result.DownloadUrl) && assetsProp.GetArrayLength() > 0)
                {
                    var firstAsset = assetsProp[0];
                    result.AssetName = firstAsset.GetProperty("name").GetString() ?? "";
                    result.DownloadUrl = firstAsset.GetProperty("browser_download_url").GetString() ?? "";
                    result.AssetSize = firstAsset.TryGetProperty("size", out var sProp) ? sProp.GetInt64() : 0;
                }
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"CheckForUpdatesAsync error: {ex.Message}");
        }

        return result;
    }

    public async Task<string> DownloadUpdateAsync(
        UpdateInfo updateInfo,
        IProgress<(long bytesDownloaded, long totalBytes, double percentage)>? progress,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(updateInfo.DownloadUrl))
        {
            throw new InvalidOperationException("다운로드 가능한 업데이트 파일 URL이 없습니다.");
        }

        string tempDir = Path.Combine(Path.GetTempPath(), "KnolTeacherUpdates");
        Directory.CreateDirectory(tempDir);

        string fileName = !string.IsNullOrWhiteSpace(updateInfo.AssetName) ? updateInfo.AssetName : $"KnolTeacher_Update_{updateInfo.LatestVersion}.exe";
        string destPath = Path.Combine(tempDir, fileName);

        using var client = new HttpClient();
        client.DefaultRequestHeaders.UserAgent.ParseAdd("KnolTeacherApp");

        using var response = await client.GetAsync(updateInfo.DownloadUrl, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
        response.EnsureSuccessStatusCode();

        long totalBytes = response.Content.Headers.ContentLength ?? updateInfo.AssetSize;
        using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        using var fileStream = new FileStream(destPath, FileMode.Create, FileAccess.Write, FileShare.None, 8192, true);

        byte[] buffer = new byte[65536];
        long totalRead = 0;
        int bytesRead;

        while ((bytesRead = await stream.ReadAsync(buffer, 0, buffer.Length, cancellationToken)) > 0)
        {
            await fileStream.WriteAsync(buffer.AsMemory(0, bytesRead), cancellationToken);
            totalRead += bytesRead;
            if (totalBytes > 0)
            {
                double pct = (double)totalRead / totalBytes * 100.0;
                progress?.Report((totalRead, totalBytes, pct));
            }
        }

        return destPath;
    }

    public void ApplyUpdateAndRestart(string downloadedFilePath)
    {
        if (!File.Exists(downloadedFilePath))
        {
            throw new FileNotFoundException("다운로드된 업데이트 파일을 찾을 수 없습니다.", downloadedFilePath);
        }

        string? currentExe = Environment.ProcessPath;
        int currentPid = Process.GetCurrentProcess().Id;

        // If it is an installer or if current process path is unknown
        if (string.IsNullOrWhiteSpace(currentExe) || downloadedFilePath.Contains("setup", StringComparison.OrdinalIgnoreCase))
        {
            Process.Start(new ProcessStartInfo(downloadedFilePath) { UseShellExecute = true });
            Application.Current.Shutdown();
            return;
        }

        // Generate batch script to replace current running executable and restart
        string scriptPath = Path.Combine(Path.GetTempPath(), $"knol_updater_{Guid.NewGuid():N}.cmd");
        string scriptContent = $@"@echo off
chcp 65001 > nul
echo [놀티쳐] 최신 버전으로 자동 업데이트 진행 중...
timeout /t 2 /nobreak > nul

:waitloop
tasklist /fi ""PID eq {currentPid}"" | find ""{currentPid}"" > nul
if not errorlevel 1 (
    timeout /t 1 /nobreak > nul
    goto waitloop
)

copy /y ""{downloadedFilePath}"" ""{currentExe}"" > nul
if errorlevel 1 (
    start """" ""{downloadedFilePath}""
    del ""%~f0""
    exit
)

start """" ""{currentExe}""
del ""%~f0""
";
        File.WriteAllText(scriptPath, scriptContent, System.Text.Encoding.Default);

        var psi = new ProcessStartInfo
        {
            FileName = "cmd.exe",
            Arguments = $"/c \"{scriptPath}\"",
            CreateNoWindow = true,
            UseShellExecute = false
        };

        Process.Start(psi);
        Application.Current.Shutdown();
    }

    public static bool IsNewerVersion(string latestTag, string currentVersion)
    {
        string cleanLatest = latestTag.TrimStart('v', 'V').Trim();
        string cleanCurrent = currentVersion.TrimStart('v', 'V').Trim();

        if (Version.TryParse(cleanLatest, out var vLatest) && Version.TryParse(cleanCurrent, out var vCurrent))
        {
            return vLatest > vCurrent;
        }

        return string.Compare(cleanLatest, cleanCurrent, StringComparison.OrdinalIgnoreCase) > 0;
    }
}
