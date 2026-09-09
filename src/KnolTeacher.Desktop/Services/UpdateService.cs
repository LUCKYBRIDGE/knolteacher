using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;

namespace KnolTeacher.Desktop.Services;

public class UpdateService : IUpdateService
{
    public const string FallbackVersion = "v3.0.6";
    public const string ReleaseAssetName = "놀티쳐.exe";

    private const string LatestReleaseApi = "https://api.github.com/repos/LUCKYBRIDGE/knolteacher/releases/latest";

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

            using var resp = await client.GetAsync(LatestReleaseApi);
            if (!resp.IsSuccessStatusCode)
            {
                return result;
            }

            string json = await resp.Content.ReadAsStringAsync();
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            string latestTag = root.GetProperty("tag_name").GetString() ?? string.Empty;
            string releaseTitle = root.TryGetProperty("name", out var nameProp) ? nameProp.GetString() ?? string.Empty : string.Empty;
            string releaseNotes = root.TryGetProperty("body", out var bodyProp) ? bodyProp.GetString() ?? string.Empty : string.Empty;
            string htmlUrl = root.TryGetProperty("html_url", out var htmlProp) ? htmlProp.GetString() ?? string.Empty : string.Empty;

            result.LatestVersion = latestTag;
            result.ReleaseTitle = string.IsNullOrWhiteSpace(releaseTitle) ? latestTag : releaseTitle;
            result.ReleaseNotes = releaseNotes;
            result.HtmlUrl = htmlUrl;
            result.HasUpdate = IsNewerVersion(latestTag, CurrentVersion);

            if (root.TryGetProperty("assets", out var assetsProp) && assetsProp.ValueKind == JsonValueKind.Array)
            {
                foreach (var asset in assetsProp.EnumerateArray())
                {
                    string assetName = asset.TryGetProperty("name", out var assetNameProp)
                        ? assetNameProp.GetString() ?? string.Empty
                        : string.Empty;

                    if (!string.Equals(assetName, ReleaseAssetName, StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    result.AssetName = assetName;
                    result.DownloadUrl = asset.TryGetProperty("browser_download_url", out var downloadProp)
                        ? downloadProp.GetString() ?? string.Empty
                        : string.Empty;
                    result.AssetSize = asset.TryGetProperty("size", out var sizeProp) ? sizeProp.GetInt64() : 0;
                    result.AssetDigest = asset.TryGetProperty("digest", out var digestProp) && digestProp.ValueKind == JsonValueKind.String
                        ? digestProp.GetString() ?? string.Empty
                        : string.Empty;
                    break;
                }
            }

            // 업데이트가 있어도 정식 단일 실행 파일이 없는 Release는 사용자에게 제안하지 않는다.
            if (result.HasUpdate && string.IsNullOrWhiteSpace(result.DownloadUrl))
            {
                Debug.WriteLine($"Latest release {latestTag} has no required asset: {ReleaseAssetName}");
                result.HasUpdate = false;
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
        if (!string.Equals(updateInfo.AssetName, ReleaseAssetName, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidDataException($"정식 업데이트 파일명이 아닙니다. 필요한 파일: {ReleaseAssetName}");
        }

        if (string.IsNullOrWhiteSpace(updateInfo.DownloadUrl))
        {
            throw new InvalidOperationException("다운로드 가능한 업데이트 파일 URL이 없습니다.");
        }

        if (!Uri.TryCreate(updateInfo.DownloadUrl, UriKind.Absolute, out var downloadUri) ||
            !string.Equals(downloadUri.Scheme, Uri.UriSchemeHttps, StringComparison.OrdinalIgnoreCase) ||
            !string.Equals(downloadUri.Host, "github.com", StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidDataException("신뢰할 수 없는 업데이트 다운로드 주소입니다.");
        }

        if (string.IsNullOrWhiteSpace(updateInfo.AssetDigest))
        {
            throw new InvalidDataException("업데이트 파일의 SHA-256 무결성 정보가 없습니다.");
        }

        string tempDir = Path.Combine(Path.GetTempPath(), "KnolTeacherUpdates");
        Directory.CreateDirectory(tempDir);
        string destPath = Path.Combine(tempDir, ReleaseAssetName);

        try
        {
            using var client = new HttpClient();
            client.DefaultRequestHeaders.UserAgent.ParseAdd("KnolTeacherApp");

            using var response = await client.GetAsync(updateInfo.DownloadUrl, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
            response.EnsureSuccessStatusCode();

            long totalBytes = response.Content.Headers.ContentLength ?? updateInfo.AssetSize;

            await using (var stream = await response.Content.ReadAsStreamAsync(cancellationToken))
            await using (var fileStream = new FileStream(destPath, FileMode.Create, FileAccess.Write, FileShare.None, 65536, true))
            {
                byte[] buffer = new byte[65536];
                long totalRead = 0;
                int bytesRead;

                while ((bytesRead = await stream.ReadAsync(buffer.AsMemory(0, buffer.Length), cancellationToken)) > 0)
                {
                    await fileStream.WriteAsync(buffer.AsMemory(0, bytesRead), cancellationToken);
                    totalRead += bytesRead;

                    if (totalBytes > 0)
                    {
                        double pct = (double)totalRead / totalBytes * 100.0;
                        progress?.Report((totalRead, totalBytes, pct));
                    }
                }

                await fileStream.FlushAsync(cancellationToken);
            }

            long downloadedSize = new FileInfo(destPath).Length;
            if (updateInfo.AssetSize > 0 && downloadedSize != updateInfo.AssetSize)
            {
                throw new InvalidDataException($"업데이트 파일 크기가 일치하지 않습니다. 예상 {updateInfo.AssetSize:N0} bytes, 실제 {downloadedSize:N0} bytes");
            }

            if (!await VerifySha256Async(destPath, updateInfo.AssetDigest, cancellationToken))
            {
                throw new InvalidDataException("업데이트 파일 SHA-256 검증에 실패했습니다. 파일을 적용하지 않습니다.");
            }

            return destPath;
        }
        catch
        {
            TryDelete(destPath);
            throw;
        }
    }

    public void ApplyUpdateAndRestart(string downloadedFilePath)
    {
        if (!File.Exists(downloadedFilePath))
        {
            throw new FileNotFoundException("다운로드된 업데이트 파일을 찾을 수 없습니다.", downloadedFilePath);
        }

        if (!string.Equals(Path.GetFileName(downloadedFilePath), ReleaseAssetName, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidDataException($"정식 업데이트 실행 파일이 아닙니다: {Path.GetFileName(downloadedFilePath)}");
        }

        string? currentExe = Environment.ProcessPath;
        int currentPid = Process.GetCurrentProcess().Id;

        if (string.IsNullOrWhiteSpace(currentExe))
        {
            Process.Start(new ProcessStartInfo(downloadedFilePath) { UseShellExecute = true });
            Application.Current.Shutdown();
            return;
        }

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

    private static async Task<bool> VerifySha256Async(string filePath, string digest, CancellationToken cancellationToken)
    {
        const string prefix = "sha256:";
        if (!digest.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        string expectedHex = digest[prefix.Length..].Trim();
        if (expectedHex.Length != 64)
        {
            return false;
        }

        byte[] expected;
        try
        {
            expected = Convert.FromHexString(expectedHex);
        }
        catch (FormatException)
        {
            return false;
        }

        using var sha256 = SHA256.Create();
        await using var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.Read, 65536, true);
        byte[] actual = await sha256.ComputeHashAsync(stream, cancellationToken);
        return CryptographicOperations.FixedTimeEquals(actual, expected);
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
            // 임시 업데이트 파일 정리 실패는 원래 예외를 가리지 않는다.
        }
    }
}
