using System;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Threading;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class StudentPickerWindow : Window
{
    private readonly IStudentManagerService _studentService;
    private readonly ISoundService _soundService;
    private readonly DispatcherTimer _shuffleTimer;
    private int _shuffleCount = 0;
    private StudentItem? _finalPicked;

    public StudentPickerWindow(IStudentManagerService studentService, ISoundService soundService)
    {
        _studentService = studentService;
        _soundService = soundService;
        InitializeComponent();

        _shuffleTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromMilliseconds(50)
        };
        _shuffleTimer.Tick += ShuffleTimer_Tick;

        UpdateStatus();
    }

    private void UpdateStatus()
    {
        int total = _studentService.Students.Count;
        int picked = _studentService.PickedStudentNumbers.Count;
        int remaining = Math.Max(0, total - picked);
        TxtRemaining.Text = $"남은 학생: {remaining}명 / 총 {total}명";
    }

    private void BtnPick_Click(object sender, RoutedEventArgs e)
    {
        bool exclude = ChkExcludePicked.IsChecked == true;
        _finalPicked = _studentService.PickRandom(exclude);

        if (_finalPicked == null)
        {
            MessageBox.Show("추첨할 학생이 없습니다.", "안내", MessageBoxButton.OK, MessageBoxImage.Information);
            return;
        }

        // Start Roulette Animation
        BtnPick.IsEnabled = false;
        _shuffleCount = 0;
        _shuffleTimer.Start();
    }

    private void ShuffleTimer_Tick(object? sender, EventArgs e)
    {
        _shuffleCount++;
        if (_studentService.Students.Count > 0)
        {
            int rndIndex = Random.Shared.Next(_studentService.Students.Count);
            var temp = _studentService.Students[rndIndex];
            TxtWinnerNumber.Text = $"{temp.Number}번";
            TxtWinnerName.Text = temp.Name;
        }

        if (_shuffleCount > 18)
        {
            _shuffleTimer.Stop();
            BtnPick.IsEnabled = true;

            if (_finalPicked != null)
            {
                TxtWinnerNumber.Text = $"🎉 {_finalPicked.Number}번 🎉";
                TxtWinnerName.Text = _finalPicked.Name;
            }

            _soundService.PlayChime();
            UpdateStatus();
        }
    }

    private void BtnReset_Click(object sender, RoutedEventArgs e)
    {
        _studentService.ResetPicked();
        UpdateStatus();
        TxtWinnerNumber.Text = "🎉";
        TxtWinnerName.Text = "초기화 완료";
    }

    protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
    {
        e.Cancel = true;
        Hide();
    }
}
