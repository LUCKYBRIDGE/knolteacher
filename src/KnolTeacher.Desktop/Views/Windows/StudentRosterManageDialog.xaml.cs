using System;
using System.Collections.Generic;
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
            EditableStudents.Add(new StudentItem
            {
                Number = s.Number,
                Name = s.Name,
                Gender = s.Gender,
                AvatarId = s.EffectiveAvatarId
            });
        }

        TbStudentCount.Text = EditableStudents.Count.ToString();
        ItemsStudents.ItemsSource = EditableStudents;
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
                // Trigger refresh by removing & reinserting or re-binding
                int idx = EditableStudents.IndexOf(student);
                if (idx >= 0)
                {
                    EditableStudents[idx] = new StudentItem
                    {
                        Number = student.Number,
                        Name = student.Name,
                        Gender = student.Gender,
                        AvatarId = dlg.SelectedAvatarId
                    };
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
            string av = allIds[i % allIds.Count];
            EditableStudents[i] = new StudentItem
            {
                Number = EditableStudents[i].Number,
                Name = EditableStudents[i].Name,
                Gender = EditableStudents[i].Gender,
                AvatarId = av
            };
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
                Name = $"학생 {i}",
                AvatarId = $"avatar_{((i - 1) % 32) + 1:D2}"
            });
        }
    }

    private void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        _studentService.Students.Clear();
        foreach (var s in EditableStudents)
        {
            _studentService.Students.Add(s);
        }
        _studentService.SaveRoster();
        DialogResult = true;
        Close();
    }
}
