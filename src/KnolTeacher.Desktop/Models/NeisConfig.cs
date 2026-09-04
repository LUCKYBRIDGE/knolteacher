using System.Text.Json.Serialization;

namespace KnolTeacher.Desktop.Models;

public class NeisConfig
{
    [JsonPropertyName("api_key")]
    public string ApiKey { get; set; } = string.Empty;

    [JsonPropertyName("office_code")]
    public string OfficeCode { get; set; } = string.Empty;

    [JsonPropertyName("office_name")]
    public string OfficeName { get; set; } = string.Empty;

    [JsonPropertyName("school_code")]
    public string SchoolCode { get; set; } = string.Empty;

    [JsonPropertyName("school_name")]
    public string SchoolName { get; set; } = string.Empty;

    [JsonPropertyName("school_type")]
    public string SchoolType { get; set; } = "초등학교";

    [JsonPropertyName("grade")]
    public string Grade { get; set; } = "1";

    [JsonPropertyName("class_nm")]
    public string ClassName { get; set; } = "1";

    [JsonPropertyName("ay")]
    public string AcademicYear { get; set; } = DateTime.Now.Year.ToString();

    [JsonPropertyName("sem")]
    public string Semester { get; set; } = "1";
}
