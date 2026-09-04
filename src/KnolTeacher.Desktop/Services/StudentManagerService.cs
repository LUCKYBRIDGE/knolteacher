using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Unicode;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Services;

public interface IStudentManagerService
{
    List<StudentItem> Students { get; }
    HashSet<int> PickedStudentNumbers { get; }
    void LoadRoster();
    StudentItem? PickRandom(bool excludePicked = true);
    void ResetPicked();
    List<List<StudentItem>> CreateGroups(int groupSize);
    List<StudentItem> ShuffleForSeating();
}

public class StudentManagerService : IStudentManagerService
{
    private readonly IConfigService _configService;
    private readonly Random _random = new();

    public List<StudentItem> Students { get; private set; } = new();
    public HashSet<int> PickedStudentNumbers { get; } = new();

    public StudentManagerService(IConfigService configService)
    {
        _configService = configService;
        LoadRoster();
    }

    public void LoadRoster()
    {
        string path = Path.Combine(_configService.ConfigDir, "student_roster.json");
        if (File.Exists(path))
        {
            try
            {
                string json = File.ReadAllText(path);
                var options = new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true,
                    Encoder = JavaScriptEncoder.Create(UnicodeRanges.All)
                };
                var container = JsonSerializer.Deserialize<StudentRosterContainer>(json, options);
                if (container?.Students != null && container.Students.Count > 0)
                {
                    Students = container.Students;
                    return;
                }
            }
            catch { }
        }

        // Default Sample Roster if not found
        Students = Enumerable.Range(1, 20)
            .Select(i => new StudentItem { Number = i, Name = $"학생 {i}" })
            .ToList();
    }

    public StudentItem? PickRandom(bool excludePicked = true)
    {
        var available = excludePicked
            ? Students.Where(s => !PickedStudentNumbers.Contains(s.Number)).ToList()
            : Students;

        if (available.Count == 0)
        {
            if (excludePicked && Students.Count > 0)
            {
                // All students picked -> Auto reset or return null
                ResetPicked();
                available = Students;
            }
            else
            {
                return null;
            }
        }

        int index = _random.Next(available.Count);
        var selected = available[index];
        PickedStudentNumbers.Add(selected.Number);
        return selected;
    }

    public void ResetPicked()
    {
        PickedStudentNumbers.Clear();
    }

    public List<List<StudentItem>> CreateGroups(int groupSize)
    {
        if (groupSize <= 0) groupSize = 4;

        var shuffled = Students.OrderBy(_ => _random.Next()).ToList();
        var groups = new List<List<StudentItem>>();

        for (int i = 0; i < shuffled.Count; i += groupSize)
        {
            groups.Add(shuffled.Skip(i).Take(groupSize).ToList());
        }

        return groups;
    }

    public List<StudentItem> ShuffleForSeating()
    {
        return Students.OrderBy(_ => _random.Next()).ToList();
    }
}
