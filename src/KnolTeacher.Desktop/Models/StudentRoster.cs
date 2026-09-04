using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json.Serialization;

namespace KnolTeacher.Desktop.Models;

public class AnimalAvatarInfo
{
    public string Id { get; set; } = string.Empty;
    public string NameKo { get; set; } = string.Empty;
    public string ImageUri => $"/assets/avatars/{Id}.png";
}

public static class AnimalAvatarCatalog
{
    public static readonly List<AnimalAvatarInfo> Avatars = new()
    {
        new() { Id = "avatar_01", NameKo = "곰" },
        new() { Id = "avatar_02", NameKo = "토끼" },
        new() { Id = "avatar_03", NameKo = "고양이" },
        new() { Id = "avatar_04", NameKo = "강아지" },
        new() { Id = "avatar_05", NameKo = "여우" },
        new() { Id = "avatar_06", NameKo = "판다" },
        new() { Id = "avatar_07", NameKo = "코알라" },
        new() { Id = "avatar_08", NameKo = "사자" },
        new() { Id = "avatar_09", NameKo = "호랑이" },
        new() { Id = "avatar_10", NameKo = "펭귄" },
        new() { Id = "avatar_11", NameKo = "병아리" },
        new() { Id = "avatar_12", NameKo = "개구리" },
        new() { Id = "avatar_13", NameKo = "돼지" },
        new() { Id = "avatar_14", NameKo = "원숭이" },
        new() { Id = "avatar_15", NameKo = "사슴" },
        new() { Id = "avatar_16", NameKo = "코끼리" },
        new() { Id = "avatar_17", NameKo = "기린" },
        new() { Id = "avatar_18", NameKo = "양" },
        new() { Id = "avatar_19", NameKo = "부엉이" },
        new() { Id = "avatar_20", NameKo = "수달" },
        new() { Id = "avatar_21", NameKo = "물개" },
        new() { Id = "avatar_22", NameKo = "고래" },
        new() { Id = "avatar_23", NameKo = "다람쥐" },
        new() { Id = "avatar_24", NameKo = "고슴도치" },
        new() { Id = "avatar_25", NameKo = "오리" },
        new() { Id = "avatar_26", NameKo = "햄스터" },
        new() { Id = "avatar_27", NameKo = "너구리" },
        new() { Id = "avatar_28", NameKo = "알파카" },
        new() { Id = "avatar_29", NameKo = "늑대" },
        new() { Id = "avatar_30", NameKo = "앵무새" },
        new() { Id = "avatar_31", NameKo = "비버" },
        new() { Id = "avatar_32", NameKo = "유니콘" },
    };

    public static string GetAnimalName(string id)
    {
        return Avatars.FirstOrDefault(a => a.Id == id)?.NameKo ?? "동물";
    }
}

public class StudentItem
{
    [JsonPropertyName("number")]
    public int Number { get; set; }

    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("gender")]
    public string Gender { get; set; } = string.Empty;

    [JsonPropertyName("avatar_id")]
    public string AvatarId { get; set; } = string.Empty;

    [JsonIgnore]
    public string EffectiveAvatarId
    {
        get
        {
            if (!string.IsNullOrWhiteSpace(AvatarId)) return AvatarId;
            int idx = (Math.Max(1, Number) - 1) % 32 + 1;
            return $"avatar_{idx:D2}";
        }
    }

    [JsonIgnore]
    public string AvatarUri => $"/assets/avatars/{EffectiveAvatarId}.png";

    [JsonIgnore]
    public string AvatarName => AnimalAvatarCatalog.GetAnimalName(EffectiveAvatarId);

    [JsonIgnore]
    public string DisplayText => $"{Number}번 {Name}";
}

public class StudentRosterContainer
{
    [JsonPropertyName("use_names_in_picker")]
    public bool UseNamesInPicker { get; set; } = true;

    [JsonPropertyName("students")]
    public List<StudentItem> Students { get; set; } = new();
}
