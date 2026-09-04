using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace KnolTeacher.Desktop.Models;

public class StudentItem
{
    [JsonPropertyName("number")]
    public int Number { get; set; }

    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("gender")]
    public string Gender { get; set; } = string.Empty;

    public string DisplayText => $"{Number}번 {Name}";
}

public class StudentRosterContainer
{
    [JsonPropertyName("use_names_in_picker")]
    public bool UseNamesInPicker { get; set; } = true;

    [JsonPropertyName("students")]
    public List<StudentItem> Students { get; set; } = new();
}
