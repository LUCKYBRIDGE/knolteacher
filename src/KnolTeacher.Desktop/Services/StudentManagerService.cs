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
    bool UseNamesInPicker { get; set; }
    bool PersistPersonalDetails { get; set; }

    void LoadRoster();
    StudentItem? PickRandom(bool excludePicked = true);
    void ResetPicked();
    List<List<StudentItem>> CreateGroups(int groupSize);
    List<StudentItem> ShuffleForSeating();
    void ConfigureNumberOnlyRoster(int studentCount);
    void SaveRoster();
    void UpdateStudentAvatar(int studentNumber, string avatarId);
}

public class StudentManagerService : IStudentManagerService
{
    private const int DefaultStudentCount = 25;

    private readonly IConfigService _configService;
    private readonly Random _random = new();

    public List<StudentItem> Students { get; private set; } = new();
    public HashSet<int> PickedStudentNumbers { get; } = new();
    public bool UseNamesInPicker { get; set; }
    public bool PersistPersonalDetails { get; set; }

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

                bool hasPersistPersonalDetailsFlag = false;
                bool hasUseNamesFlag = false;
                using (var doc = JsonDocument.Parse(json))
                {
                    if (doc.RootElement.ValueKind == JsonValueKind.Object)
                    {
                        hasPersistPersonalDetailsFlag = doc.RootElement.TryGetProperty("persist_personal_details", out _);
                        hasUseNamesFlag = doc.RootElement.TryGetProperty("use_names_in_picker", out _);
                    }
                }

                var container = JsonSerializer.Deserialize<StudentRosterContainer>(json, options);
                if (container?.Students != null && container.Students.Count > 0)
                {
                    Students = container.Students
                        .Where(s => s.Number > 0)
                        .OrderBy(s => s.Number)
                        .ToList();

                    if (Students.Count > 0)
                    {
                        // Backward compatibility: old roster files did not have the explicit persistence flag.
                        // If they already contain personal fields, preserve those values instead of silently erasing them.
                        PersistPersonalDetails = hasPersistPersonalDetailsFlag
                            ? container.PersistPersonalDetails
                            : Students.Any(HasPersonalDetails);

                        UseNamesInPicker = hasUseNamesFlag
                            ? container.UseNamesInPicker
                            : false;

                        return;
                    }
                }
            }
            catch (Exception ex)
            {
                App.BootLog($"[StudentManager] Failed to load local roster: {ex.GetType().Name}");
            }
        }

        // Privacy-first default: no names or other personal fields are required.
        ConfigureNumberOnlyRoster(DefaultStudentCount);
        UseNamesInPicker = false;
        PersistPersonalDetails = false;
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

    public void ConfigureNumberOnlyRoster(int studentCount)
    {
        studentCount = Math.Clamp(studentCount, 1, 60);
        Students = Enumerable.Range(1, studentCount)
            .Select(i => new StudentItem { Number = i })
            .ToList();
        PickedStudentNumbers.Clear();
        UseNamesInPicker = false;
        PersistPersonalDetails = false;
    }

    public void SaveRoster()
    {
        try
        {
            string path = Path.Combine(_configService.ConfigDir, "student_roster.json");
            var persistedStudents = PersistPersonalDetails
                ? Students.Select(CloneStudent).ToList()
                : Students.Select(s => s.ToNumberOnlyCopy(keepAvatar: true)).ToList();

            var container = new StudentRosterContainer
            {
                UseNamesInPicker = PersistPersonalDetails && UseNamesInPicker,
                PersistPersonalDetails = PersistPersonalDetails,
                Students = persistedStudents
            };

            var options = new JsonSerializerOptions
            {
                WriteIndented = true,
                Encoder = JavaScriptEncoder.Create(UnicodeRanges.All)
            };
            string json = JsonSerializer.Serialize(container, options);
            File.WriteAllText(path, json);
        }
        catch (Exception ex)
        {
            // Do not log names or other student fields.
            App.BootLog($"[StudentManager] Failed to save local roster: {ex.GetType().Name}");
        }
    }

    public void UpdateStudentAvatar(int studentNumber, string avatarId)
    {
        var student = Students.FirstOrDefault(s => s.Number == studentNumber);
        if (student != null)
        {
            student.AvatarId = avatarId;
            SaveRoster();
        }
    }

    private static bool HasPersonalDetails(StudentItem student)
    {
        return !string.IsNullOrWhiteSpace(student.Name)
            || !string.IsNullOrWhiteSpace(student.Gender)
            || !string.IsNullOrWhiteSpace(student.Role)
            || !string.IsNullOrWhiteSpace(student.BirthDate)
            || !string.IsNullOrWhiteSpace(student.Contact)
            || !string.IsNullOrWhiteSpace(student.Note);
    }

    private static StudentItem CloneStudent(StudentItem student)
    {
        return new StudentItem
        {
            Number = student.Number,
            Name = student.Name,
            Gender = student.Gender,
            Role = student.Role,
            BirthDate = student.BirthDate,
            Contact = student.Contact,
            Note = student.Note,
            AvatarId = student.AvatarId
        };
    }
}
