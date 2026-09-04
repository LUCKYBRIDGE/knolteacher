using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
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

    private void ResetDisplay()
    {
        if (!_isReady) return;
        _pickedHistory.Clear();
        if (TxtWinner != null)
        {
            TxtWinner.Text = "?";
            TxtWinner.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#38BDF8"));
        }
        if (BorderWinnerAvatar != null)
        {
            BorderWinnerAvatar.Visibility = Visibility.Collapsed;
        }
        if (TxtHistory != null)
        {
            TxtHistory.Text = "기록: 없음";
        }
    }

    private void Filter_Changed(object sender, RoutedEventArgs e)
    {
        ResetDisplay();
    }

    private void Range_TextChanged(object sender, TextChangedEventArgs e)
    {
        ResetDisplay();
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

        var allStudents = _studentService?.Students ?? new();
        var students = genderFilter != null 
            ? allStudents.Where(s => s.Gender == genderFilter).ToList() 
            : allStudents;

        List<(string Display, string? AvatarUri)> candidates = new();

        if (isName && students.Count > 0)
        {
            foreach (var s in students)
            {
                string tag = s.Gender == "남" ? " 👦" : (s.Gender == "여" ? " 👧" : "");
                candidates.Add(($"{s.Number}번 {s.Name}{tag}", s.AvatarUri));
            }
        }
        else
        {
            int start = (TbStartNum != null && int.TryParse(TbStartNum.Text, out int sNum)) ? Math.Max(1, sNum) : 1;
            int end = (TbEndNum != null && int.TryParse(TbEndNum.Text, out int eNum)) ? Math.Max(start, eNum) : 25;
            for (int i = start; i <= end; i++)
            {
                var matchedStudent = allStudents.FirstOrDefault(s => s.Number == i);
                candidates.Add(($"{i}번", matchedStudent?.AvatarUri));
            }
        }

        var available = candidates.Where(c => !_pickedHistory.Contains(c.Display)).ToList();
        if (available.Count == 0)
        {
            TxtWinner.Text = "전원 완료!";
            TxtWinner.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#10B981"));
            if (BorderWinnerAvatar != null) BorderWinnerAvatar.Visibility = Visibility.Collapsed;
            if (TxtHistory != null) TxtHistory.Text = "모든 학생이 다 뽑혔습니다!";
            return;
        }

        _isPicking = true;
        BtnPick.IsEnabled = false;

        var rng = new Random();
        for (int step = 0; step < 12; step++)
        {
            var temp = candidates[rng.Next(candidates.Count)];
            TxtWinner.Text = temp.Display;
            TxtWinner.Foreground = Brushes.White;
            if (!string.IsNullOrEmpty(temp.AvatarUri) && BorderWinnerAvatar != null && ImgWinnerAvatar != null)
            {
                try
                {
                    ImgWinnerAvatar.ImageSource = new BitmapImage(new Uri(temp.AvatarUri, UriKind.RelativeOrAbsolute));
                    BorderWinnerAvatar.Visibility = Visibility.Visible;
                }
                catch
                {
                    BorderWinnerAvatar.Visibility = Visibility.Collapsed;
                }
            }
            else if (BorderWinnerAvatar != null)
            {
                BorderWinnerAvatar.Visibility = Visibility.Collapsed;
            }
            await Task.Delay(40 + step * 10);
        }

        var winner = available[rng.Next(available.Count)];
        _pickedHistory.Add(winner.Display);

        TxtWinner.Text = winner.Display;
        TxtWinner.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#10B981"));
        if (!string.IsNullOrEmpty(winner.AvatarUri) && BorderWinnerAvatar != null && ImgWinnerAvatar != null)
        {
            try
            {
                ImgWinnerAvatar.ImageSource = new BitmapImage(new Uri(winner.AvatarUri, UriKind.RelativeOrAbsolute));
                BorderWinnerAvatar.Visibility = Visibility.Visible;
            }
            catch
            {
                BorderWinnerAvatar.Visibility = Visibility.Collapsed;
            }
        }
        else if (BorderWinnerAvatar != null)
        {
            BorderWinnerAvatar.Visibility = Visibility.Collapsed;
        }

        if (TxtHistory != null)
        {
            TxtHistory.Text = $"기록 ({_pickedHistory.Count}명): {string.Join(", ", _pickedHistory)}";
        }

        _soundService?.PlayChime();
        _isPicking = false;
        BtnPick.IsEnabled = true;
    }
}
