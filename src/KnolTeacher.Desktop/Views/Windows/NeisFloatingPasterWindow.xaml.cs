using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Threading;
using KnolTeacher.Desktop.Models;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class NeisFloatingPasterWindow : Window
{
    private readonly List<NeisStudentComment> _comments;
    private int _currentIndex = 0;
    private DispatcherTimer? _autoSequenceTimer;
    private bool _isAutoSequencing = false;

    // Win32 Global Hotkey (F8)
    [DllImport("user32.dll")]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

    [DllImport("user32.dll")]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    [DllImport("user32.dll")]
    private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);

    private const int HOTKEY_ID_F8 = 9001;
    private const byte VK_CONTROL = 0x11;
    private const byte VK_V = 0x56;
    private const byte VK_TAB = 0x09;
    private const uint KEYEVENTF_KEYUP = 0x0002;
    private const uint VK_F8 = 0x77;

    private HwndSource? _hwndSource;

    public NeisFloatingPasterWindow(List<NeisStudentComment> comments, int initialIndex = 0)
    {
        _comments = comments ?? new List<NeisStudentComment>();
        _currentIndex = Math.Clamp(initialIndex, 0, Math.Max(0, _comments.Count - 1));
        InitializeComponent();

        Loaded += (s, e) =>
        {
            Left = SystemParameters.WorkArea.Right - Width - 30;
            Top = SystemParameters.WorkArea.Top + 60;
            UpdateStudentDisplay();

            // Register global F8 hotkey
            var helper = new WindowInteropHelper(this);
            _hwndSource = HwndSource.FromHwnd(helper.Handle);
            _hwndSource?.AddHook(HwndHook);
            RegisterHotKey(helper.Handle, HOTKEY_ID_F8, 0, VK_F8);
        };

        Closed += (s, e) =>
        {
            StopAutoSequence();
            var helper = new WindowInteropHelper(this);
            UnregisterHotKey(helper.Handle, HOTKEY_ID_F8);
            _hwndSource?.RemoveHook(HwndHook);
        };

        KeyDown += (s, e) =>
        {
            if (e.Key == Key.Space || e.Key == Key.Enter)
            {
                CopyCurrentAndAdvance(sendPaste: false);
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
            else if (e.Key == Key.Escape)
            {
                if (_isAutoSequencing)
                {
                    StopAutoSequence();
                    HudNotificationWindow.Instance.ShowToast("⏹️", "자동 연속 입력을 중단했습니다.");
                    e.Handled = true;
                }
            }
        };
    }

    private IntPtr HwndHook(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        const int WM_HOTKEY = 0x0312;
        if (msg == WM_HOTKEY && wParam.ToInt32() == HOTKEY_ID_F8)
        {
            // F8 pressed globally while teacher is on NEIS
            CopyCurrentAndAdvance(sendPaste: true);
            handled = true;
        }
        return IntPtr.Zero;
    }

    private void Header_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.LeftButton == MouseButtonState.Pressed) DragMove();
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

    private void CopyCurrentAndAdvance(bool sendPaste = false)
    {
        if (_comments.Count == 0) return;
        var s = _comments[_currentIndex];

        try
        {
            Clipboard.SetText(s.CommentText ?? "");
        }
        catch { }

        if (sendPaste)
        {
            // Simulate Ctrl+V and Tab into target NEIS window
            Task.Run(async () =>
            {
                await Task.Delay(50);
                // Ctrl+V
                keybd_event(VK_CONTROL, 0, 0, UIntPtr.Zero);
                keybd_event(VK_V, 0, 0, UIntPtr.Zero);
                keybd_event(VK_V, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
                keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);

                await Task.Delay(100);
                // Tab
                keybd_event(VK_TAB, 0, 0, UIntPtr.Zero);
                keybd_event(VK_TAB, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            });
        }

        HudNotificationWindow.Instance.ShowToast("📋", $"[{s.StudentNumber}번 {s.StudentName}] 평어 복사 완료 ({_currentIndex + 1}/{_comments.Count})");

        if (_currentIndex < _comments.Count - 1)
        {
            _currentIndex++;
            UpdateStudentDisplay();
        }
        else
        {
            HudNotificationWindow.Instance.ShowToast("🎉", "모든 학생의 평어 입력이 완료되었습니다! 나이스에서 [저장]을 눌러주세요.");
            StopAutoSequence();
        }
    }

    private void BtnCopyAndNext_Click(object sender, RoutedEventArgs e)
    {
        CopyCurrentAndAdvance(sendPaste: false);
    }

    private async void BtnAutoSequence_Click(object sender, RoutedEventArgs e)
    {
        if (_isAutoSequencing)
        {
            StopAutoSequence();
            return;
        }

        if (_comments.Count == 0) return;

        _isAutoSequencing = true;
        BtnAutoSequence.Background = System.Windows.Media.Brushes.Red;
        BtnAutoSequence.Content = "⏹️ 자동 연속 입력 중지 (Esc)";

        // 3 second prep countdown
        for (int sec = 3; sec > 0; sec--)
        {
            if (!_isAutoSequencing) return;
            BtnAutoSequence.Content = $"⏳ {sec}초 후 시작! 나이스 1번 칸을 클릭해 두세요...";
            await Task.Delay(1000);
        }

        if (!_isAutoSequencing) return;

        BtnAutoSequence.Content = "⏹️ 자동 연속 입력 진행 중... (중단: Esc)";

        _autoSequenceTimer = new DispatcherTimer
        {
            Interval = TimeSpan.FromMilliseconds(1500)
        };

        _autoSequenceTimer.Tick += (s, ev) =>
        {
            if (!_isAutoSequencing) return;

            CopyCurrentAndAdvance(sendPaste: true);

            if (_currentIndex >= _comments.Count - 1)
            {
                StopAutoSequence();
            }
        };

        _autoSequenceTimer.Start();
    }

    private void StopAutoSequence()
    {
        _isAutoSequencing = false;
        _autoSequenceTimer?.Stop();
        _autoSequenceTimer = null;
        BtnAutoSequence.Background = new System.Windows.Media.SolidColorBrush((System.Windows.Media.Color)System.Windows.Media.ColorConverter.ConvertFromString("#059669"));
        BtnAutoSequence.Content = "▶ 1.5초 간격 전원 자동 순차 입력 시작";
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

    private void BtnHelp_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new NeisHelpDialog
        {
            Owner = this
        };
        dlg.ShowDialog();
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();
}