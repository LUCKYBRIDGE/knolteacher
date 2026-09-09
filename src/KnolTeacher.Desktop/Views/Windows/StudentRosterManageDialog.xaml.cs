using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Windows;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class StudentRosterManageDialog : Window
{
    private readonly IStudentManagerService _studentService;
    public ObservableCollection<StudentItem> EditableStudents { get; set; } = new();

    public StudentRosterManageDialog(IStudentManagerService studentService)
    {
        _studentService = studentService;
        InitializeComponent();

        foreach (var s in _studentService.Students)
        {
            EditableStudents.Add(CloneStudent(s));
        }

        TbStudentCount.Text = EditableStudents.Count.ToString();
        ChkPersistPersonalDetails.IsChecked = _studentService.PersistPersonalDetails;
        ChkUseNamesInPicker.IsChecked = _studentService.PersistPersonalDetails && _studentService.UseNamesInPicker;
        ItemsStudents.ItemsSource = EditableStudents;
        UpdatePrivacyOptionState();
    }

    private void PrivacyOption_Changed(object sender, RoutedEventArgs e)
    {
        UpdatePrivacyOptionState();
    }

    private void UpdatePrivacyOptionState()
    {
        if (ChkUseNamesInPicker == null || ChkPersistPersonalDetails == null) return;

        bool persist = ChkPersistPersonalDetails.IsChecked == true;
        ChkUseNamesInPicker.IsEnabled = persist;
        if (!persist)
        {
            ChkUseNamesInPicker.IsChecked = false;
        }
    }

    private void BtnChangeAvatar_Click(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement fe && fe.Tag is StudentItem student)
        {
            var dlg = new AvatarPickerModalDialog(student)
            {
                Owner = this
            };
            if (dlg.ShowDialog() == true)
            {
                student.AvatarId = dlg.SelectedAvatarId;
                int idx = EditableStudents.IndexOf(student);
                if (idx >= 0)
                {
                    var replacement = CloneStudent(student);
                    replacement.AvatarId = dlg.SelectedAvatarId;
                    EditableStudents[idx] = replacement;
                }
            }
        }
    }

    private void BtnShuffleAvatars_Click(object sender, RoutedEventArgs e)
    {
        var rand = new Random();
        var allIds = AnimalAvatarCatalog.Avatars.Select(a => a.Id).OrderBy(_ => rand.Next()).ToList();

        for (int i = 0; i < EditableStudents.Count; i++)
        {
            var replacement = CloneStudent(EditableStudents[i]);
            replacement.AvatarId = allIds[i % allIds.Count];
            EditableStudents[i] = replacement;
        }
    }

    private void BtnRegenerate_Click(object sender, RoutedEventArgs e)
    {
        if (!int.TryParse(TbStudentCount.Text, out int count) || count <= 0) count = 25;
        count = Math.Clamp(count, 1, 60);

        EditableStudents.Clear();
        for (int i = 1; i <= count; i++)
        {
            EditableStudents.Add(new StudentItem
            {
                Number = i,
                AvatarId = $"avatar_{((i - 1) % 32) + 1:D2}"
            });
        }

        // Regenerating a roster is an explicit return to privacy-first number-only mode.
        ChkPersistPersonalDetails.IsChecked = false;
        ChkUseNamesInPicker.IsChecked = false;
    }

    private void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        bool persistPersonalDetails = ChkPersistPersonalDetails.IsChecked == true;

        _studentService.Students.Clear();
        foreach (var s in EditableStudents.OrderBy(s => s.Number))
        {
            _studentService.Students.Add(persistPersonalDetails ? CloneStudent(s) : s.ToNumberOnlyCopy(keepAvatar: true));
        }

        _studentService.PersistPersonalDetails = persistPersonalDetails;
        _studentService.UseNamesInPicker = persistPersonalDetails && ChkUseNamesInPicker.IsChecked == true;
        _studentService.ResetPicked();
        _studentService.SaveRoster();

        DialogResult = true;
        Close();
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
