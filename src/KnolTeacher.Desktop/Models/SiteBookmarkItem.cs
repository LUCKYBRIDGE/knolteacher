using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace KnolTeacher.Desktop.Models;

public class SiteBookmarkItem
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("title")]
    public string Title { get; set; } = string.Empty;

    [JsonPropertyName("desc")]
    public string Description { get; set; } = string.Empty;

    [JsonPropertyName("url")]
    public string Url { get; set; } = string.Empty;

    [JsonPropertyName("icon")]
    public string Icon { get; set; } = "🌐";

    [JsonPropertyName("color")]
    public string Color { get; set; } = "#B45309";

    [JsonPropertyName("category")]
    public string Category { get; set; } = "수업자료";

    [JsonPropertyName("is_custom")]
    public bool IsCustom { get; set; } = false;
}

public class EducationOfficeItem
{
    public string RegionName { get; set; } = string.Empty;
    public string OfficeName { get; set; } = string.Empty;
    public string DomainCode { get; set; } = string.Empty;
    public string Url => $"https://{DomainCode}.eduptl.kr/";
    public string DisplayText => $"{RegionName} ({OfficeName})";
}
