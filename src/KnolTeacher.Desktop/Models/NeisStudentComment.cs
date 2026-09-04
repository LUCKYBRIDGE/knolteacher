using System;
using System.Text.Json.Serialization;

namespace KnolTeacher.Desktop.Models;

public class NeisStudentComment
{
    [JsonPropertyName("number")]
    public int StudentNumber { get; set; }

    [JsonPropertyName("name")]
    public string StudentName { get; set; } = string.Empty;

    [JsonPropertyName("content")]
    public string CommentText { get; set; } = string.Empty;

    [JsonPropertyName("byte_count")]
    public int ByteCount => CalculateNeisByteCount(CommentText);

    [JsonPropertyName("is_over_limit")]
    public bool IsOverLimit => ByteCount > MaxByteLimit;

    [JsonPropertyName("max_byte_limit")]
    public int MaxByteLimit { get; set; } = 1500; // 4세대 나이스 기준 1500바이트

    [JsonPropertyName("status")]
    public string StatusDisplay => IsOverLimit ? $"⚠️ {ByteCount}/{MaxByteLimit} Byte (초과)" : $"✅ {ByteCount}/{MaxByteLimit} Byte";

    public static int CalculateNeisByteCount(string text)
    {
        if (string.IsNullOrEmpty(text)) return 0;

        int bytes = 0;
        for (int i = 0; i < text.Length; i++)
        {
            char c = text[i];
            if (c == '\r')
            {
                if (i + 1 < text.Length && text[i + 1] == '\n')
                {
                    bytes += 2;
                    i++;
                }
                else
                {
                    bytes += 2;
                }
            }
            else if (c == '\n')
            {
                bytes += 2;
            }
            else if (c <= 0x7F)
            {
                bytes += 1; // ASCII
            }
            else
            {
                bytes += 3; // 한글 및 특수문자 (UTF-8 3바이트)
            }
        }
        return bytes;
    }
}
