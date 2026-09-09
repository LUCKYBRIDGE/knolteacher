using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;

namespace KnolTeacher.Desktop.Services;

public class UpdateService : IUpdateService
{
    public const string FallbackVersion = "v0.0.0";
    public const string LocalExecutableName = "놀티쳐.exe";
    public const string PrimaryReleaseAssetName = "KnolTeacher.exe";
    public const string LegacyReleaseAssetName = "놀티쳐.exe";

    private const string LatestReleaseApi = "https://api.github.com/repos/LUCKYBRIDGE/knolteacher/releases/latest";
    private const string UpdateSuccessMarkerFile = "update_completed.txt";
    private const string UpdateFailureMarkerFile = "update_failed.txt";

    public string CurrentVersion
    {
        get
        {
            try
            {
                var ver = Assembly.GetExecutingAssembly().GetName().Version;
                if (ver != null && ver.Major >= 0 && ver.Minor >= 0 && ver.Build >= 0)
                {
                    return $"v{ver.Major}.{ver.Minor}.{ver.Build}";
                }
            }
            catch
            {
            }

            try
            {
                string? executablePath = Environment.ProcessPath;
                if (!string.IsNullOrWhiteSpace(executablePath) &&
                    TryGetExecutableVersion(executablePath, out string fileVersion))
                {
                    return fileVersion;
                }
            }
            catch
            {
            }

            return FallbackVersion;
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
                foreach (string acceptedName in new[] { PrimaryReleaseAssetName, LegacyReleaseAssetName })
                {
                    foreach (var asset in assetsProp.EnumerateArray())
                    {
                        string assetName = asset.TryGetProperty("name", out var assetNameProp)
                            ? assetNameProp.GetString() ?? string.Empty
                            : string.Empty;

                        if (!string.Equals(assetName, acceptedName, StringComparison.OrdinalIgnoreCase))
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

                    if (!string.IsNullOrWhiteSpace(result.DownloadUrl))
                    {
                        break;
                    }
                }
            }

            if (result.HasUpdate && string.IsNullOrWhiteSpace(result.DownloadUrl))
            {
                Debug.WriteLine($"Latest release {latestTag} has no supported KnolTeacher executable asset.");
                result.HasUpdate = false;
            }
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"CheckForUpdatesAsync error: {ex.GetType().Name}");
        }

        return result;
    }

    public async Task<string> DownloadUpdateAsync(
        UpdateInfo updateInfo,
        IProgress<(long bytesDownloaded, long totalBytes, double percentage)>? progress,
        CancellationToken cancellationToken = default)
    {
        if (!IsAcceptedReleaseAssetName(updateInfo.AssetName))
        {
            throw new InvalidDataException($"정식 놀티쳐 업데이트 파일명이 아닙니다: {updateInfo.AssetName}");
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
        string destPath = Path.Combine(tempDir, LocalExecutableName);

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

            if (!TryGetExecutableVersion(destPath, out string downloadedVersion) ||
                !IsSameProductVersion(downloadedVersion, updateInfo.LatestVersion))
            {
                throw new InvalidDataException(
                    $"다운로드된 실행 파일 버전이 Release 버전과 일치하지 않습니다. Release={updateInfo.LatestVersion}, File={downloadedVersion}");
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

        if (!string.Equals(Path.GetFileName(downloadedFilePath), LocalExecutableName, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidDataException($"로컬 적용용 놀티쳐 실행 파일이 아닙니다: {Path.GetFileName(downloadedFilePath)}");
        }

        if (!TryGetExecutableVersion(downloadedFilePath, out string downloadedVersion))
        {
            throw new InvalidDataException("다운로드된 실행 파일의 버전 정보를 확인할 수 없습니다.");
        }

        string? runningExe = Environment.ProcessPath;
        if (string.IsNullOrWhiteSpace(runningExe))
        {
            throw new InvalidOperationException("현재 실행 중인 놀티쳐 경로를 확인할 수 없어 안전하게 업데이트할 수 없습니다.");
        }

        string installDirectory = Path.GetDirectoryName(runningExe) ?? AppContext.BaseDirectory;
        string targetExe = Path.Combine(installDirectory, LocalExecutableName);
        string expectedHash = ComputeSha256Hex(downloadedFilePath);
        int currentPid = Process.GetCurrentProcess().Id;

        string configDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            ".knol_teacher_desk");
        string successMarker = Path.Combine(configDir, UpdateSuccessMarkerFile);
        string failureMarker = Path.Combine(configDir, UpdateFailureMarkerFile);

        string scriptPath = Path.Combine(Path.GetTempPath(), $"knol_updater_{Guid.NewGuid():N}.ps1");
        string script = BuildPowerShellUpdaterScript(
            downloadedFilePath,
            targetExe,
            runningExe,
            successMarker,
            failureMarker,
            expectedHash,
            downloadedVersion,
            currentPid,
            scriptPath);

        File.WriteAllText(scriptPath, script, new UTF8Encoding(encoderShouldEmitUTF8Identifier: true));

        var psi = new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = $"-NoProfile -ExecutionPolicy Bypass -File \"{scriptPath}\"",
            CreateNoWindow = true,
            UseShellExecute = false
        };

        Process.Start(psi);
        Application.Current.Shutdown();
    }

    public bool TryConsumeUpdateCompletion(out string version)
    {
        version = string.Empty;
        string path = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            ".knol_teacher_desk",
            UpdateSuccessMarkerFile);

        try
        {
            if (!File.Exists(path)) return false;
            string value = File.ReadAllText(path).Trim();
            File.Delete(path);
            if (!Version.TryParse(value.TrimStart('v', 'V'), out var parsed) || parsed.Build < 0)
            {
                return false;
            }

            version = $"v{parsed.Major}.{parsed.Minor}.{parsed.Build}";
            return IsSameProductVersion(version, CurrentVersion);
        }
        catch
        {
            version = string.Empty;
            return false;
        }
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

    public static bool IsSameProductVersion(string left, string right)
    {
        if (!Version.TryParse(left.TrimStart('v', 'V').Trim(), out var a) ||
            !Version.TryParse(right.TrimStart('v', 'V').Trim(), out var b))
        {
            return false;
        }

        return a.Major == b.Major && a.Minor == b.Minor && a.Build == b.Build;
    }

    public static bool IsAcceptedReleaseAssetName(string? assetName)
    {
        if (string.IsNullOrWhiteSpace(assetName)) return false;
        return string.Equals(assetName, PrimaryReleaseAssetName, StringComparison.OrdinalIgnoreCase) ||
               string.Equals(assetName, LegacyReleaseAssetName, StringComparison.OrdinalIgnoreCase);
    }

    private static bool TryGetExecutableVersion(string filePath, out string version)
    {
        version = string.Empty;
        try
        {
            string? raw = FileVersionInfo.GetVersionInfo(filePath).FileVersion;
            if (!Version.TryParse(raw, out var parsed) || parsed.Build < 0)
            {
                return false;
            }

            version = $"v{parsed.Major}.{parsed.Minor}.{parsed.Build}";
            return true;
        }
        catch
        {
            return false;
        }
    }

    private static string ComputeSha256Hex(string filePath)
    {
        using var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read, FileShare.Read);
        using var sha = SHA256.Create();
        return Convert.ToHexString(sha.ComputeHash(stream));
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

    private static string BuildPowerShellUpdaterScript(
        string source,
        string target,
        string runningExe,
        string successMarker,
        string failureMarker,
        string expectedHash,
        string expectedVersion,
        int currentPid,
        string scriptPath)
    {
        string sourcePs = EscapePowerShellLiteral(source);
        string targetPs = EscapePowerShellLiteral(target);
        string runningPs = EscapePowerShellLiteral(runningExe);
        string successPs = EscapePowerShellLiteral(successMarker);
        string failurePs = EscapePowerShellLiteral(failureMarker);
        string scriptPs = EscapePowerShellLiteral(scriptPath);

        return $@"$ErrorActionPreference = 'Stop'
$source = '{sourcePs}'
$target = '{targetPs}'
$running = '{runningPs}'
$successMarker = '{successPs}'
$failureMarker = '{failurePs}'
$expectedHash = '{expectedHash}'
$expectedVersion = '{expectedVersion}'
$scriptPath = '{scriptPs}'

try {{
    try {{ Wait-Process -Id {currentPid} -ErrorAction SilentlyContinue }} catch {{ }}

    $copied = $false
    for ($i = 0; $i -lt 12; $i++) {{
        try {{
            Copy-Item -LiteralPath $source -Destination $target -Force
            $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToUpperInvariant()
            if ($actualHash -eq $expectedHash) {{
                $copied = $true
                break
            }}
        }} catch {{ }}
        Start-Sleep -Milliseconds 500
    }}

    if (-not $copied) {{ throw 'verified replacement failed' }}

    $markerDir = Split-Path -Parent $successMarker
    New-Item -ItemType Directory -Path $markerDir -Force | Out-Null
    Set-Content -LiteralPath $successMarker -Value $expectedVersion -Encoding UTF8
    if (Test-Path -LiteralPath $failureMarker) {{ Remove-Item -LiteralPath $failureMarker -Force -ErrorAction SilentlyContinue }}

    if (($running -ne $target) -and (Test-Path -LiteralPath $running)) {{
        Remove-Item -LiteralPath $running -Force -ErrorAction SilentlyContinue
    }}

    Start-Process -FilePath $target
    Start-Sleep -Milliseconds 700
    Remove-Item -LiteralPath $source -Force -ErrorAction SilentlyContinue
}}
catch {{
    try {{
        $markerDir = Split-Path -Parent $failureMarker
        New-Item -ItemType Directory -Path $markerDir -Force | Out-Null
        Set-Content -LiteralPath $failureMarker -Value 'replacement_failed' -Encoding UTF8
        if (Test-Path -LiteralPath $target) {{ Start-Process -FilePath $target }}
        elseif (Test-Path -LiteralPath $running) {{ Start-Process -FilePath $running }}
    }} catch {{ }}
}}
finally {{
    Start-Sleep -Milliseconds 500
    Remove-Item -LiteralPath $scriptPath -Force -ErrorAction SilentlyContinue
}}
";
    }

    private static string EscapePowerShellLiteral(string value)
        => value.Replace("'", "''", StringComparison.Ordinal);

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
        }
    }
}
