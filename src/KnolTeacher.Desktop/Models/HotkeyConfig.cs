using System.Text.Json.Serialization;

namespace KnolTeacher.Desktop.Models;

public class HotkeyItem
{
    [JsonPropertyName("id")]
    public int Id { get; set; }

    [JsonPropertyName("action")]
    public string Action { get; set; } = string.Empty;

    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("desc")]
    public string Description { get; set; } = string.Empty;

    [JsonPropertyName("mod")]
    public string Modifier { get; set; } = "Alt"; // "Alt", "Ctrl", "None", etc.

    [JsonPropertyName("key")]
    public string Key { get; set; } = "1";

    [JsonPropertyName("enabled")]
    public bool Enabled { get; set; } = true;
}

public static class DefaultHotkeys
{
    public static List<HotkeyItem> GetDefaults() => new()
    {
        new() { Id = 1, Action = "magnifier", Name = "화면 돋보기", Description = "마우스 주변 부분 확대경", Modifier = "Alt", Key = "1", Enabled = true },
        new() { Id = 2, Action = "drawing", Name = "화면 판서", Description = "화면 위 자유 펜 판서 & 기하도구", Modifier = "Alt", Key = "2", Enabled = true },
        new() { Id = 3, Action = "timer", Name = "교실 타이머", Description = "초점 집중 카운트다운 타이머", Modifier = "Alt", Key = "3", Enabled = true },
        new() { Id = 4, Action = "live_zoom", Name = "라이브 줌", Description = "화면 전체 실시간 줌인", Modifier = "Alt", Key = "4", Enabled = true },
        new() { Id = 5, Action = "recorder", Name = "화면 녹화", Description = "수업 화면 및 음성 녹화 시작/종료", Modifier = "Alt", Key = "5", Enabled = true },
        new() { Id = 6, Action = "snip", Name = "화면 캡처", Description = "사각 영역 즉시 캡처 & 복사", Modifier = "Alt", Key = "6", Enabled = true },
        new() { Id = 7, Action = "board", Name = "놀티쳐 보드", Description = "학생용 대형 올인원 보드 실행", Modifier = "Alt", Key = "7", Enabled = true },
        new() { Id = 8, Action = "picker", Name = "발표자 추첨", Description = "무작위 발표자 학생 이름 뽑기", Modifier = "Alt", Key = "8", Enabled = true },
        new() { Id = 9, Action = "dock", Name = "스마트 플로팅 독", Description = "화면 상단 미니 리모컨 토글", Modifier = "Alt", Key = "9", Enabled = true },
        new() { Id = 10, Action = "board_f2", Name = "놀티쳐 보드 (F2)", Description = "놀티쳐 보드 1초 원클릭 실행", Modifier = "None", Key = "F2", Enabled = true },
        new() { Id = 11, Action = "youtube", Name = "유튜브 BGM 플레이어", Description = "무광고 유튜브 교실 BGM 토글 (Alt+Y)", Modifier = "Alt", Key = "Y", Enabled = true },
    };
}
