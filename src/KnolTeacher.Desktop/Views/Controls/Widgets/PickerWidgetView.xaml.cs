using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class PickerWidgetView : UserControl
{
    private readonly IStudentManagerService? _studentService;
    private readonly ISoundService? _soundService;
    private readonly List<string> _pickedHistory = new();
    private bool _isPicking = false;
    private bool _isReady = false;

    public PickerWidgetView(IStudentManagerService? studentService = null, ISoundService? soundService = null)
    {
        _studentService = studentService;
        _soundService = soundService;
        InitializeComponent();
        _isReady = true;
    }

    private void Filter_Changed(object sender, RoutedEventArgs e)
    {
        if (!_isReady) return;
        _pickedHistory.Clear();
        if (TxtWinner != null)
        {
            TxtWinner.Text = "?";
            TxtWinner.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#38BDF8"));
        }
        if (TxtHistory != null)
        {
            TxtHistory.Text = "기록: 없음";
        }
    }

    private void Range_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (!_isReady) return;
        _pickedHistory.Clear();
        if (TxtWinner != null)
        {
            TxtWinner.Text = "?";
            TxtWinner.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#38BDF8"));
        }
        if (TxtHistory != null)
        {
            TxtHistory.Text = "기록: 없음";
        }
    }

    private async void BtnPick_Click(object sender, RoutedEventArgs e)
    {
        if (_isPicking) return;

        bool isName = RbName.IsChecked == true;
        int genderIdx = CbGender?.SelectedIndex ?? 0;
        string? genderFilter = genderIdx switch
        {
            1 => "남",
            2 => "여",
            _ => null
        };

        List<string> candidates = new();
        var allStudents = _studentService?.Students ?? new();
        var students = genderFilter != null 
            ? allStudents.Where(s => s.Gender == genderFilter).ToList() 
            : allStudents;

        if (isName && students.Count > 0)
        {
            foreach (var s in students)
            {
                string tag = s.Gender == "남" ? " 👦" : (s.Gender == "여" ? " 👧" : "");
                candidates.Add($"{s.Number}번 {s.Name}{tag}");
            }
        }
        else
        {
            int start = (TbStartNum != null && int.TryParse(TbStartNum.Text, out int sNum)) ? Math.Max(1, sNum) : 1;
            int end = (TbEndNum != null && int.TryParse(TbEndNum.Text, out int eNum)) ? Math.Max(start, eNum) : 25;
            for (int i = start; i <= end; i++)
            {
                candidates.Add($"{i}번");
            }
        }

        var available = candidates.Where(c => !_pickedHistory.Contains(c)).ToList();
        if (available.Count == 0)
        {
            TxtWinner.Text = "전원 완료!";
            TxtWinner.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#10B981"));
            TxtHistory.Text = "모든 학생이 다 뽑혔습니다!";
            return;
        }

        _isPicking = true;
        BtnPick.IsEnabled = false;

        var rng = new Random();
        for (int step = 0; step < 12; step++)
        {
            TxtWinner.Text = candidates[rng.Next(candidates.Count)];
            TxtWinner.Foreground = Brushes.White;
            await Task.Delay(40 + step * 10);
        }

        string winner = available[rng.Next(available.Count)];
        _pickedHistory.Add(winner);

        TxtWinner.Text = winner;
        TxtWinner.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#10B981"));
        TxtHistory.Text = $"기록 ({_pickedHistory.Count}명): {string.Join(", ", _pickedHistory)}";

        _soundService?.PlayChime();
        _isPicking = false;
        BtnPick.IsEnabled = true;
    }
}
