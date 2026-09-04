using System;
using System.Text.Json.Serialization;

namespace KnolTeacher.Desktop.Models;

public class YouTubeTrackItem
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = Guid.NewGuid().ToString("N");

    [JsonPropertyName("name")]
    public string Name { get; set; } = "유튜브 음악";

    [JsonPropertyName("author")]
    public string Author { get; set; } = "YouTube";

    [JsonPropertyName("video_id")]
    public string VideoId { get; set; } = string.Empty;

    [JsonPropertyName("url")]
    public string Url { get; set; } = string.Empty;

    [JsonPropertyName("emoji")]
    public string Emoji { get; set; } = "🎵";

    [JsonPropertyName("category")]
    public string Category { get; set; } = "교실 BGM";

    [JsonPropertyName("loop")]
    public bool Loop { get; set; } = true;

    [JsonPropertyName("is_section_repeat")]
    public bool IsSectionRepeat { get; set; } = false;

    [JsonPropertyName("start_seconds")]
    public int StartSeconds { get; set; } = 0;

    [JsonPropertyName("end_seconds")]
    public int EndSeconds { get; set; } = 0;

    [JsonIgnore]
    public string SectionDisplay => IsSectionRepeat 
        ? $"🔂 {StartSeconds / 60:D2}:{StartSeconds % 60:D2} ~ {EndSeconds / 60:D2}:{EndSeconds % 60:D2}" 
        : "전체 재생";
}
