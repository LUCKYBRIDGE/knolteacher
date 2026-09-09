using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json.Serialization;
using System.Windows.Media.Imaging;

namespace KnolTeacher.Desktop.Models;

public class AnimalAvatarInfo
{
    public string Id { get; set; } = string.Empty;
    public string NameKo { get; set; } = string.Empty;
    public string ImageUri => $"pack://application:,,,/assets/avatars/{Id}.png";
    public BitmapImage? AvatarBitmap => AnimalAvatarCatalog.GetAvatarBitmap(Id);
}

public static class AnimalAvatarCatalog
{
    private static readonly Dictionary<string, BitmapImage> _avatarCache = new(StringComparer.OrdinalIgnoreCase);
    private static readonly object _cacheLock = new();

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

    /// <summary>
    /// Thread-safe cached high-performance loader for 32 animal avatar bitmaps.
    /// Supports WPF Pack URI with fallback to local BaseDirectory/assets/avatars.
    /// </summary>
    public static BitmapImage? GetAvatarBitmap(string? avatarId)
    {
        if (string.IsNullOrWhiteSpace(avatarId)) avatarId = "avatar_01";
        if (!avatarId.StartsWith("avatar_", StringComparison.OrdinalIgnoreCase))
        {
            avatarId = "avatar_01";
        }

        lock (_cacheLock)
        {
            if (_avatarCache.TryGetValue(avatarId, out var cached))
            {
                return cached;
            }

            try
            {
                var packUri = new Uri($"pack://application:,,,/assets/avatars/{avatarId}.png", UriKind.Absolute);
                var bmp = new BitmapImage();
                bmp.BeginInit();
                bmp.UriSource = packUri;
                bmp.CacheOption = BitmapCacheOption.OnLoad;
                bmp.EndInit();
                bmp.Freeze();
                _avatarCache[avatarId] = bmp;
                return bmp;
            }
            catch
            {
                // Pack URI failed, try next.
            }

            try
            {
                string localPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "assets", "avatars", $"{avatarId}.png");
                if (File.Exists(localPath))
                {
                    var bmp = new BitmapImage();
                    bmp.BeginInit();
                    bmp.UriSource = new Uri(localPath, UriKind.Absolute);
                    bmp.CacheOption = BitmapCacheOption.OnLoad;
                    bmp.EndInit();
                    bmp.Freeze();
                    _avatarCache[avatarId] = bmp;
                    return bmp;
                }
            }
            catch
            {
                // Local file failed.
            }

            try
            {
                var packUri = new Uri($"pack://application:,,,/KnolTeacher.Desktop;component/assets/avatars/{avatarId}.png", UriKind.Absolute);
                var bmp = new BitmapImage();
                bmp.BeginInit();
                bmp.UriSource = packUri;
                bmp.CacheOption = BitmapCacheOption.OnLoad;
                bmp.EndInit();
                bmp.Freeze();
                _avatarCache[avatarId] = bmp;
                return bmp;
            }
            catch
            {
                return null;
            }
        }
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

    [JsonPropertyName("role")]
    public string Role { get; set; } = string.Empty;

    [JsonPropertyName("birth_date")]
    public string BirthDate { get; set; } = string.Empty;

    [JsonPropertyName("contact")]
    public string Contact { get; set; } = string.Empty;

    [JsonPropertyName("note")]
    public string Note { get; set; } = string.Empty;

    [JsonPropertyName("avatar_id")]
    public string AvatarId { get; set; } = string.Empty;

    [JsonIgnore]
    public bool HasName => !string.IsNullOrWhiteSpace(Name);

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
    public string AvatarUri => $"pack://application:,,,/assets/avatars/{EffectiveAvatarId}.png";

    [JsonIgnore]
    public BitmapImage? AvatarBitmap => AnimalAvatarCatalog.GetAvatarBitmap(EffectiveAvatarId);

    [JsonIgnore]
    public string AvatarName => AnimalAvatarCatalog.GetAnimalName(EffectiveAvatarId);

    [JsonIgnore]
    public string DisplayText => HasName ? $"{Number}번 {Name.Trim()}" : $"{Number}번";

    public StudentItem ToNumberOnlyCopy(bool keepAvatar = true)
    {
        return new StudentItem
        {
            Number = Number,
            AvatarId = keepAvatar ? AvatarId : string.Empty
        };
    }
}

public class StudentRosterContainer
{
    /// <summary>
    /// Names are opt-in for classroom picker presentation. Number-only is the privacy-first default.
    /// </summary>
    [JsonPropertyName("use_names_in_picker")]
    public bool UseNamesInPicker { get; set; } = false;

    /// <summary>
    /// When false, SaveRoster persists only student number and non-sensitive avatar choice.
    /// Existing legacy roster files are detected by StudentManagerService and preserved.
    /// </summary>
    [JsonPropertyName("persist_personal_details")]
    public bool PersistPersonalDetails { get; set; } = false;

    [JsonPropertyName("students")]
    public List<StudentItem> Students { get; set; } = new();
}
