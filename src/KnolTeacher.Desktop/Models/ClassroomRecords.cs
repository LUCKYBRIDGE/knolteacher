using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Serialization;

namespace KnolTeacher.Desktop.Models;

public class ChecklistItem
{
    [JsonPropertyName("number")]
    public int StudentNumber { get; set; }

    [JsonPropertyName("name")]
    public string StudentName { get; set; } = string.Empty;

    /// <summary>
    /// "Completed" (O), "Incomplete" (X), "Pending" (△)
    /// </summary>
    [JsonPropertyName("status")]
    public string Status { get; set; } = "Incomplete";

    [JsonPropertyName("note")]
    public string Note { get; set; } = string.Empty;

    [JsonIgnore]
    public bool IsCompleted => Status == "Completed";

    [JsonIgnore]
    public string StatusSymbol => Status switch
    {
        "Completed" => "O",
        "Pending" => "△",
        _ => "X"
    };

    [JsonIgnore]
    public string StatusColor => Status switch
    {
        "Completed" => "#10B981", // Green
        "Pending" => "#F59E0B",   // Amber
        _ => "#EF4444"            // Red
    };
}

public class ChecklistGroup
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = Guid.NewGuid().ToString("N")[..8];

    [JsonPropertyName("title")]
    public string Title { get; set; } = string.Empty;

    [JsonPropertyName("category")]
    public string Category { get; set; } = "과제";

    [JsonPropertyName("target_date")]
    public string TargetDate { get; set; } = DateTime.Today.ToString("yyyy-MM-dd");

    [JsonPropertyName("created_at")]
    public DateTime CreatedAt { get; set; } = DateTime.Now;

    [JsonPropertyName("items")]
    public List<ChecklistItem> Items { get; set; } = new();

    [JsonIgnore]
    public int TotalCount => Items.Count;

    [JsonIgnore]
    public int CompletedCount => Items.Count(i => i.Status == "Completed");

    [JsonIgnore]
    public int PendingCount => Items.Count(i => i.Status == "Pending");

    [JsonIgnore]
    public int IncompleteCount => Items.Count(i => i.Status != "Completed" && i.Status != "Pending");

    [JsonIgnore]
    public int CompletionRate => TotalCount == 0 ? 0 : (int)Math.Round((double)CompletedCount / TotalCount * 100);

    [JsonIgnore]
    public string ProgressSummary => $"{CompletedCount}/{TotalCount}명 ({CompletionRate}%)";

    public string GetUncompletedSummary()
    {
        var uncompleted = Items
            .Where(i => i.Status != "Completed")
            .Select(i => $"{i.StudentNumber}번 {i.StudentName}")
            .ToList();

        if (uncompleted.Count == 0)
        {
            return $"[{Title}] 전원 제출 완료! 🎉";
        }

        return $"[{Title}] 미제출 학생 ({uncompleted.Count}명):\n{string.Join(", ", uncompleted)}";
    }
}

public class CumulativeRecordItem
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = Guid.NewGuid().ToString("N")[..8];

    [JsonPropertyName("number")]
    public int StudentNumber { get; set; }

    [JsonPropertyName("name")]
    public string StudentName { get; set; } = string.Empty;

    [JsonPropertyName("date")]
    public DateTime Date { get; set; } = DateTime.Today;

    /// <summary>
    /// 행동특성, 자율활동, 동아리활동, 봉사활동, 진로활동, 상담일지, 생활지도, 학습태도
    /// </summary>
    [JsonPropertyName("category")]
    public string Category { get; set; } = "행동특성";

    [JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;

    /// <summary>
    /// 일반, 칭찬/우수, 지도필요, 상담완료
    /// </summary>
    [JsonPropertyName("tag")]
    public string Tag { get; set; } = "일반";

    [JsonPropertyName("created_at")]
    public DateTime CreatedAt { get; set; } = DateTime.Now;

    [JsonIgnore]
    public string DateString => Date.ToString("yyyy-MM-dd");

    [JsonIgnore]
    public string TagColor => Tag switch
    {
        "칭찬/우수" => "#10B981", // Emerald
        "지도필요" => "#EF4444",   // Rose Red
        "상담완료" => "#8B5CF6",   // Purple
        _ => "#0284C7"            // Sky Blue
    };
}
