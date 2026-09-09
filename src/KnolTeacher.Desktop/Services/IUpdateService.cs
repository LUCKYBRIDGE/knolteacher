using System;
using System.Threading;
using System.Threading.Tasks;

namespace KnolTeacher.Desktop.Services;

public class UpdateInfo
{
    public bool HasUpdate { get; set; }
    public string CurrentVersion { get; set; } = "v0.0.0";
    public string LatestVersion { get; set; } = string.Empty;
    public string ReleaseTitle { get; set; } = string.Empty;
    public string ReleaseNotes { get; set; } = string.Empty;
    public string DownloadUrl { get; set; } = string.Empty;
    public string AssetName { get; set; } = string.Empty;
    public string AssetDigest { get; set; } = string.Empty;
    public long AssetSize { get; set; }
    public string HtmlUrl { get; set; } = string.Empty;
}

public interface IUpdateService
{
    string CurrentVersion { get; }
    Task<UpdateInfo> CheckForUpdatesAsync();
    Task<string> DownloadUpdateAsync(UpdateInfo updateInfo, IProgress<(long bytesDownloaded, long totalBytes, double percentage)>? progress, CancellationToken cancellationToken = default);
    void ApplyUpdateAndRestart(string downloadedFilePath);
}
