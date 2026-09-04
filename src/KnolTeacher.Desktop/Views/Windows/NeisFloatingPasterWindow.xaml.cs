using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Input;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class NeisFloatingPasterWindow : Window
{
    private readonly List<NeisStudentComment> _comments;
    private int _currentIndex = 0;

    public NeisFloatingPasterWindow(List<NeisStudentComment> comments, int initialIndex = 0)
    {
        _comments = comments ?? new List<NeisStudentComment>();
        _currentIndex = Math.Clamp(initialIndex, 0, Math.Max(0, _comments.Count - 1));
        InitializeComponent();

        Loaded += (s, e) =>
        {
            // Position at top-right of screen
            Left = SystemParameters.WorkArea.Right - Width - 30;
            Top = SystemParameters.WorkArea.Top + 60;
            UpdateStudentDisplay();
        };

        KeyDown += (s, e) =>
        {
            if (e.Key == Key.Space || e.Key == Key.Enter)
            {
                CopyCurrentAndAdvance();
                e.Handled = true;
            }
            else if (e.Key == Key.Left)
            {
                MovePrev();
                e.Handled = true;
            }
            else if (e.Key == Key.Right)
            {
                MoveNext();
                e.Handled = true;
            }
        };
    }

    private void UpdateStudentDisplay()
    {
        if (_comments.Count == 0)
        {
            TxtStudentBadge.Text = "입력할 학생 데이터가 없습니다.";
            TxtByteBadge.Text = "0 Byte";
            TbCommentPreview.Text = "";
            return;
        }

        var s = _comments[_currentIndex];
        TxtStudentBadge.Text = $"👤 [{s.StudentNumber}번 {s.StudentName}] ({_currentIndex + 1} / {_comments.Count}명)";
        TxtByteBadge.Text = s.StatusDisplay;
        TbCommentPreview.Text = s.CommentText;
    }

    private void CopyCurrentAndAdvance()
    {
        if (_comments.Count == 0) return;
        var s = _comments[_currentIndex];

        try
        {
            Clipboard.SetText(s.CommentText ?? "");
            HudNotificationWindow.Instance.ShowToast("📋", $"[{s.StudentNumber}번 {s.StudentName}] 평어가 복사되었습니다. 나이스 칸에 Ctrl+V로 붙여넣으세요.");
        }
        catch { }

        if (_currentIndex < _comments.Count - 1)
        {
            _currentIndex++;
            UpdateStudentDisplay();
        }
    }

    private void MovePrev()
    {
        if (_currentIndex > 0)
        {
            _currentIndex--;
            UpdateStudentDisplay();
        }
    }

    private void MoveNext()
    {
        if (_currentIndex < _comments.Count - 1)
        {
            _currentIndex++;
            UpdateStudentDisplay();
        }
    }

    private void BtnPrev_Click(object sender, RoutedEventArgs e) => MovePrev();
    private void BtnNext_Click(object sender, RoutedEventArgs e) => MoveNext();
    private void BtnCopyAndNext_Click(object sender, RoutedEventArgs e) => CopyCurrentAndAdvance();

    private void Header_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.LeftButton == MouseButtonState.Pressed) DragMove();
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();
}
