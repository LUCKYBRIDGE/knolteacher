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
    private readonly JsonSerializerOptions _loadOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        Encoder = JavaScriptEncoder.Create(UnicodeRanges.All)
    };
    private readonly JsonSerializerOptions _saveOptions = new()
    {
        WriteIndented = true,
        Encoder = JavaScriptEncoder.Create(UnicodeRanges.All)
    };
    private bool _preserveBackupOnNextSave;

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
        _preserveBackupOnNextSave = false;

        if (TryLoadRosterFile(path, out var container, out bool hasPersistFlag, out bool hasUseNamesFlag))
        {
            ApplyLoadedRoster(container!, hasPersistFlag, hasUseNamesFlag);
            return;
        }

        string backupPath = SafeLocalFileStore.BackupPath(path);
        if (TryLoadRosterFile(backupPath, out container, out hasPersistFlag, out hasUseNamesFlag))
        {
            ApplyLoadedRoster(container!, hasPersistFlag, hasUseNamesFlag);

            bool repaired = SafeLocalFileStore.TryRestorePrimaryFromBackup(path);
            _preserveBackupOnNextSave = !repaired;

            App.BootLog(repaired
                ? "[StudentManager] Recovered local roster from .bak file and repaired primary."
                : "[StudentManager] Recovered local roster from .bak file; preserving backup on next save.");
            return;
        }

        ConfigureNumberOnlyRoster(DefaultStudentCount);
        UseNamesInPicker = false;
        PersistPersonalDetails = false;
    }

    private bool TryLoadRosterFile(
        string path,
        out StudentRosterContainer? container,
        out bool hasPersistPersonalDetailsFlag,
        out bool hasUseNamesFlag)
    {
        container = null;
        hasPersistPersonalDetailsFlag = false;
        hasUseNamesFlag = false;

        if (!File.Exists(path)) return false;

        try
        {
            string json = File.ReadAllText(path);
            using (var doc = JsonDocument.Parse(json))
            {
                if (doc.RootElement.ValueKind != JsonValueKind.Object)
                {
                    return false;
                }

                hasPersistPersonalDetailsFlag = doc.RootElement.TryGetProperty("persist_personal_details", out _);
                hasUseNamesFlag = doc.RootElement.TryGetProperty("use_names_in_picker", out _);
            }

            container = JsonSerializer.Deserialize<StudentRosterContainer>(json, _loadOptions);
            return container?.Students != null && container.Students.Any(s => s.Number > 0);
        }
        catch (Exception ex)
        {
            App.BootLog($"[StudentManager] Invalid local roster candidate ({Path.GetFileName(path)}): {ex.GetType().Name}");
            container = null;
            return false;
        }
    }

    private void ApplyLoadedRoster(
        StudentRosterContainer container,
        bool hasPersistPersonalDetailsFlag,
        bool hasUseNamesFlag)
    {
        Students = container.Students
            .Where(s => s.Number > 0)
            .OrderBy(s => s.Number)
            .ToList();

        PersistPersonalDetails = hasPersistPersonalDetailsFlag
            ? container.PersistPersonalDetails
            : Students.Any(HasPersonalDetails);

        UseNamesInPicker = hasUseNamesFlag
            ? container.UseNamesInPicker
            : false;
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
        _preserveBackupOnNextSave = false;
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

            string json = JsonSerializer.Serialize(container, _saveOptions);
            SafeLocalFileStore.WriteAllTextAtomic(
                path,
                json,
                preserveExistingBackup: _preserveBackupOnNextSave);
            _preserveBackupOnNextSave = false;
        }
        catch (Exception ex)
        {
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
