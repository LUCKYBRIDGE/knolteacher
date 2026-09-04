using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Text.Unicode;
using System.Threading.Tasks;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Services;

public interface IYouTubeService
{
    List<YouTubeTrackItem> Playlist { get; }
    event Action? OnPlaylistChanged;

    string ExtractVideoId(string urlOrId);
    Task<(string title, string author)> FetchMetaAsync(string videoId);
    void AddTrack(YouTubeTrackItem track);
    void UpdateTrack(YouTubeTrackItem track);
    void DeleteTrack(string id);
    void SavePlaylist();
    void ResetToDefaults();
}

public class YouTubeService : IYouTubeService
{
    private readonly string _playlistFile;
    private readonly HttpClient _httpClient = new() { Timeout = TimeSpan.FromSeconds(5) };
    private readonly JsonSerializerOptions _jsonOptions = new()
    {
        WriteIndented = true,
        Encoder = JavaScriptEncoder.Create(UnicodeRanges.All)
    };

    public List<YouTubeTrackItem> Playlist { get; private set; } = new();
    public event Action? OnPlaylistChanged;

    public YouTubeService(IConfigService configService)
    {
        _playlistFile = Path.Combine(configService.ConfigDir, "classroom_bgm_playlist.json");
        LoadPlaylist();
    }

    public string ExtractVideoId(string urlOrId)
    {
        string text = urlOrId.Trim();
        if (Regex.IsMatch(text, @"^[a-zA-Z0-9_-]{11}$"))
        {
            return text;
        }

        var patterns = new[]
        {
            @"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/live\/|\/shorts\/)([a-zA-Z0-9_-]{11})",
            @"youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})",
            @"music\.youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})"
        };

        foreach (var p in patterns)
        {
            var m = Regex.Match(text, p);
            if (m.Success)
            {
                return m.Groups[1].Value;
            }
        }

        return string.Empty;
    }

    public async Task<(string title, string author)> FetchMetaAsync(string videoId)
    {
        try
        {
            string url = $"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={videoId}&format=json";
            string json = await _httpClient.GetStringAsync(url);
            using var doc = JsonDocument.Parse(json);
            string title = doc.RootElement.TryGetProperty("title", out var t) ? t.GetString() ?? "" : "";
            string author = doc.RootElement.TryGetProperty("author_name", out var a) ? a.GetString() ?? "" : "";
            return (string.IsNullOrEmpty(title) ? $"유튜브 음악 ({videoId})" : title, string.IsNullOrEmpty(author) ? "YouTube" : author);
        }
        catch
        {
            return ($"유튜브 음악 ({videoId})", "YouTube");
        }
    }

    private void LoadPlaylist()
    {
        if (File.Exists(_playlistFile))
        {
            try
            {
                string json = File.ReadAllText(_playlistFile);
                var list = JsonSerializer.Deserialize<List<YouTubeTrackItem>>(json, _jsonOptions);
                if (list != null && list.Count > 0)
                {
                    Playlist = list;
                    return;
                }
            }
            catch { }
        }

        ResetToDefaults();
    }

    public void ResetToDefaults()
    {
        Playlist = new List<YouTubeTrackItem>
        {
            new()
            {
                Name = "🌿 [집중/자습] 편안하고 차분한 로파이 피아노 BGM",
                Author = "Lofi Classroom",
                VideoId = "5qap5aO4i9A",
                Url = "https://www.youtube.com/watch?v=5qap5aO4i9A",
                Emoji = "🌿",
                Category = "집중",
                Loop = true
            },
            new()
            {
                Name = "☕ [독서/아침] 따뜻한 휴식 칠 비트 음악",
                Author = "Chill Beats",
                VideoId = "DWcJFNfaw9c",
                Url = "https://www.youtube.com/watch?v=DWcJFNfaw9c",
                Emoji = "☕",
                Category = "독서",
                Loop = true
            },
            new()
            {
                Name = "🧹 [정리/활동] 신나고 경쾌한 교실 정리정돈 음악",
                Author = "Upbeat Classroom",
                VideoId = "jfKfPfyJRdk",
                Url = "https://www.youtube.com/watch?v=jfKfPfyJRdk",
                Emoji = "🧹",
                Category = "정리",
                Loop = true
            },
            new()
            {
                Name = "🕊️ [명상/휴식] 마음이 편안해지는 자연 소리와 피아노",
                Author = "Peaceful Piano",
                VideoId = "7NOSDKb0HlU",
                Url = "https://www.youtube.com/watch?v=7NOSDKb0HlU",
                Emoji = "🕊️",
                Category = "휴식",
                Loop = true
            }
        };

        SavePlaylist();
    }

    public void AddTrack(YouTubeTrackItem track)
    {
        Playlist.Add(track);
        SavePlaylist();
        OnPlaylistChanged?.Invoke();
    }

    public void UpdateTrack(YouTubeTrackItem track)
    {
        int idx = Playlist.FindIndex(t => t.Id == track.Id);
        if (idx >= 0)
        {
            Playlist[idx] = track;
            SavePlaylist();
            OnPlaylistChanged?.Invoke();
        }
    }

    public void DeleteTrack(string id)
    {
        Playlist.RemoveAll(t => t.Id == id);
        SavePlaylist();
        OnPlaylistChanged?.Invoke();
    }

    public void SavePlaylist()
    {
        try
        {
            string json = JsonSerializer.Serialize(Playlist, _jsonOptions);
            File.WriteAllText(_playlistFile, json);
        }
        catch { }
    }
}
