using System;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.Views.Windows;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class MemoWidgetView : UserControl
{
    private readonly IConfigService? _configService;
    private readonly ITtsService? _ttsService;
    private readonly ITimetableService? _timetableService;
    private readonly string _memoFile;
    private readonly DispatcherTimer _autoNoticeTimer;
    private string _lastAutoNoticeSlot = string.Empty;

    public MemoWidgetView(IConfigService? configService = null, ITtsService? ttsService = null, ITimetableService? timetableService = null)
    {
        InitializeComponent();
        _configService = configService;
        _ttsService = ttsService ?? (Application.Current as App)?.Services?.GetService(typeof(ITtsService)) as ITtsService;
        _timetableService = timetableService ?? (Application.Current as App)?.Services?.GetService(typeof(ITimetableService)) as ITimetableService;

        string dir = _configService?.ConfigDir ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".knol_teacher_desk");
        _memoFile = Path.Combine(dir, "board_memo.txt");

        Loaded += (s, e) =>
        {
            if (File.Exists(_memoFile))
            {
                try { TbMemo.Text = File.ReadAllText(_memoFile); } catch { }
            }
            else
            {
                TbMemo.Text = "• [알림] 오늘 5교시는 음악실에서 수업합니다.\n• [준비물] 수학익힘책 42쪽 풀어오기\n• [과제] 주말 독서록 작성하기";
            }
        };

        TbMemo.TextChanged += (s, e) =>
        {
            try { File.WriteAllText(_memoFile, TbMemo.Text); } catch { }
        };

        _autoNoticeTimer = new DispatcherTimer { Interval = TimeSpan.FromMinutes(1) };
        _autoNoticeTimer.Tick += (s, e) => CheckAutoNoticeTime();
        _autoNoticeTimer.Start();
    }

    private void CheckAutoNoticeTime()
    {
        if (_configService == null) return;
        var preset = _configService.AutoNoticePreset;
        if (!preset.Enabled) return;

        var now = DateTime.Now;
        var time = now.TimeOfDay;

        string currentSlot = "";
        string noticeText = "";

        if (time >= new TimeSpan(8, 20, 0) && time < new TimeSpan(9, 0, 0))
        {
            currentSlot = "morning";
            noticeText = preset.MorningNotice;
        }
        else if (time >= new TimeSpan(12, 0, 0) && time < new TimeSpan(13, 0, 0))
        {
            currentSlot = "lunch";
            noticeText = preset.LunchNotice;
        }
        else if (time >= new TimeSpan(14, 30, 0))
        {
            currentSlot = "dismissal";
            noticeText = preset.DismissalNotice;
        }

        if (!string.IsNullOrEmpty(currentSlot) && currentSlot != _lastAutoNoticeSlot && !string.IsNullOrWhiteSpace(noticeText))
        {
            _lastAutoNoticeSlot = currentSlot;
            // Prepend or show auto notice banner if not already present
            if (!TbMemo.Text.Contains(noticeText))
            {
                TbMemo.Text = $"[자동 공지] {noticeText}\n" + TbMemo.Text;
            }
        }
    }

    private void BtnInsertTag_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is string tag)
        {
            if (!string.IsNullOrEmpty(TbMemo.Text) && !TbMemo.Text.EndsWith("\n"))
            {
                TbMemo.AppendText("\n");
            }
            TbMemo.AppendText(tag);
            TbMemo.CaretIndex = TbMemo.Text.Length;
            TbMemo.Focus();
        }
    }

    private void BtnClear_Click(object sender, RoutedEventArgs e)
    {
        if (MessageBox.Show("알림장 내용을 모두 지우시겠습니까?", "알림장 비우기", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
        {
            TbMemo.Clear();
            try { File.WriteAllText(_memoFile, ""); } catch { }
        }
    }

    private void BtnZoomNotice_Click(object sender, RoutedEventArgs e)
    {
        var zoomWin = new NoticeZoomWindow(TbMemo.Text, _ttsService);
        zoomWin.ShowDialog();
    }

    private void BtnTtsNotice_Click(object sender, RoutedEventArgs e)
    {
        if (_ttsService == null) return;
        if (_ttsService.IsSpeaking)
        {
            _ttsService.Stop();
            BtnTtsNotice.Content = "🔊 읽어주기";
            BtnTtsNotice.Background = (System.Windows.Media.Brush)new System.Windows.Media.BrushConverter().ConvertFromString("#0D9488")!;
        }
        else
        {
            BtnTtsNotice.Content = "⏹️ 중지";
            BtnTtsNotice.Background = System.Windows.Media.Brushes.Crimson;
            _ = _ttsService.SpeakAsync(TbMemo.Text);
        }
    }

    private void BtnBoardSets_Click(object sender, RoutedEventArgs e)
    {
        if (_configService == null) return;
        var dialog = new AutoNoticeSettingsDialog(_configService, TbMemo.Text);
        dialog.Owner = Window.GetWindow(this);
        dialog.SetApplied += (appliedText) =>
        {
            TbMemo.Text = appliedText;
        };
        dialog.ShowDialog();
    }
}
