using System;
using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.Views.Controls;
using KnolTeacher.Desktop.Views.Windows;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class MemoWidgetView : UserControl, IWidgetLifecycle
{
    public static event Action<string, object?>? OnNoticeChanged;

    public static void NotifyNoticeChanged(string newText, object? sender)
    {
        OnNoticeChanged?.Invoke(newText, sender);
    }

    private const string DefaultMemo = "• [알림] 오늘 5교시는 음악실에서 수업합니다.\n• [준비물] 수학익힘책 42쪽 풀어오기\n• [과제] 주말 독서록 작성하기";

    private readonly IConfigService? _configService;
    private readonly ITtsService? _ttsService;
    private readonly string _memoFile;
    private readonly DispatcherTimer _autoNoticeTimer;
    private readonly DispatcherTimer _saveDebounceTimer;
    private string _lastAutoNoticeSlot = string.Empty;
    private bool _isActive;
    private bool _disposed;
    private bool _suppressNoticeBroadcast;
    private bool _hasPendingSave;

    public MemoWidgetView(IConfigService? configService = null, ITtsService? ttsService = null, ITimetableService? timetableService = null)
    {
        InitializeComponent();
        _configService = configService;
        _ttsService = ttsService ?? (Application.Current as App)?.Services?.GetService(typeof(ITtsService)) as ITtsService;

        string dir = _configService?.ConfigDir
            ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".knol_teacher_desk");
        _memoFile = Path.Combine(dir, "board_memo.txt");

        TbMemo.TextChanged += TbMemo_TextChanged;

        _autoNoticeTimer = new DispatcherTimer { Interval = TimeSpan.FromMinutes(1) };
        _autoNoticeTimer.Tick += AutoNoticeTimer_Tick;

        // Avoid rewriting the local file for every keystroke. The visible notice still
        // synchronizes immediately, while disk persistence happens after a short quiet period.
        _saveDebounceTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(350) };
        _saveDebounceTimer.Tick += SaveDebounceTimer_Tick;
    }

    public void Activate()
    {
        if (_disposed || _isActive) return;

        _isActive = true;
        OnNoticeChanged += HandleNoticeChanged;
        LoadMemoFromDisk();
        _autoNoticeTimer.Start();
    }

    public void Deactivate()
    {
        if (_disposed) return;

        FlushPendingSave();
        _autoNoticeTimer.Stop();
        _saveDebounceTimer.Stop();
        OnNoticeChanged -= HandleNoticeChanged;
        _isActive = false;

        // A completely hidden/closed board must not leave speech running in the background.
        try
        {
            if (_ttsService?.IsSpeaking == true)
            {
                _ttsService.Stop();
            }
        }
        catch
        {
            // TTS shutdown is best-effort and must never block widget cleanup.
        }
    }

    public void Dispose()
    {
        if (_disposed) return;

        Deactivate();
        _autoNoticeTimer.Tick -= AutoNoticeTimer_Tick;
        _saveDebounceTimer.Tick -= SaveDebounceTimer_Tick;
        TbMemo.TextChanged -= TbMemo_TextChanged;
        OnNoticeChanged -= HandleNoticeChanged;
        _disposed = true;
    }

    private void LoadMemoFromDisk()
    {
        _suppressNoticeBroadcast = true;
        try
        {
            if (SafeLocalFileStore.TryReadAllTextWithBackup(_memoFile, out string saved))
            {
                if (TbMemo.Text != saved)
                {
                    TbMemo.Text = saved;
                }
            }
            else if (string.IsNullOrWhiteSpace(TbMemo.Text))
            {
                TbMemo.Text = DefaultMemo;
            }
        }
        finally
        {
            _suppressNoticeBroadcast = false;
        }
    }

    private void TbMemo_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (_suppressNoticeBroadcast || _disposed) return;

        _hasPendingSave = true;
        _saveDebounceTimer.Stop();
        _saveDebounceTimer.Start();
        NotifyNoticeChanged(TbMemo.Text, this);
    }

    private void SaveDebounceTimer_Tick(object? sender, EventArgs e)
    {
        _saveDebounceTimer.Stop();
        FlushPendingSave();
    }

    private void FlushPendingSave()
    {
        if (!_hasPendingSave) return;

        _saveDebounceTimer.Stop();
        string text = TbMemo.Text;
        try
        {
            SafeLocalFileStore.WriteAllTextAtomic(_memoFile, text);
            _hasPendingSave = false;
        }
        catch (Exception ex)
        {
            // Never log the memo content or a user-specific full path.
            Debug.WriteLine($"[Nolboard.Memo] Local memo save failed: {ex.GetType().Name}");
        }
    }

    private void HandleNoticeChanged(string newText, object? sender)
    {
        if (_disposed || !_isActive || ReferenceEquals(sender, this)) return;

        _ = Dispatcher.BeginInvoke(() =>
        {
            if (_disposed || !_isActive || TbMemo.Text == newText) return;

            _suppressNoticeBroadcast = true;
            try
            {
                TbMemo.Text = newText;
            }
            finally
            {
                _suppressNoticeBroadcast = false;
            }
        });
    }

    private void AutoNoticeTimer_Tick(object? sender, EventArgs e)
    {
        CheckAutoNoticeTime();
    }

    private void CheckAutoNoticeTime()
    {
        if (_configService == null) return;
        var preset = _configService.AutoNoticePreset;
        if (!preset.Enabled) return;

        var now = DateTime.Now;
        var time = now.TimeOfDay;

        string currentSlot = string.Empty;
        string noticeText = string.Empty;

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

        if (!string.IsNullOrEmpty(currentSlot) &&
            currentSlot != _lastAutoNoticeSlot &&
            !string.IsNullOrWhiteSpace(noticeText))
        {
            _lastAutoNoticeSlot = currentSlot;
            if (!TbMemo.Text.Contains(noticeText, StringComparison.Ordinal))
            {
                TbMemo.Text = $"[자동 공지] {noticeText}\n" + TbMemo.Text;
            }
        }
    }

    private void BtnInsertTag_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button btn || btn.Tag is not string tag) return;

        if (!string.IsNullOrEmpty(TbMemo.Text) && !TbMemo.Text.EndsWith("\n", StringComparison.Ordinal))
        {
            TbMemo.AppendText("\n");
        }
        TbMemo.AppendText(tag);
        TbMemo.CaretIndex = TbMemo.Text.Length;
        TbMemo.Focus();
    }

    private void BtnClear_Click(object sender, RoutedEventArgs e)
    {
        if (MessageBox.Show("알림장 내용을 모두 지우시겠습니까?", "알림장 비우기", MessageBoxButton.YesNo, MessageBoxImage.Question) != MessageBoxResult.Yes)
        {
            return;
        }

        TbMemo.Clear();
        FlushPendingSave();
    }

    private void BtnZoomNotice_Click(object sender, RoutedEventArgs e)
    {
        var zoomWindow = new NoticeZoomWindow(TbMemo.Text, _ttsService)
        {
            Owner = Window.GetWindow(this)
        };
        zoomWindow.ShowDialog();
    }

    private void BtnTtsNotice_Click(object sender, RoutedEventArgs e)
    {
        if (_ttsService == null) return;

        if (_ttsService.IsSpeaking)
        {
            _ttsService.Stop();
            BtnTtsNotice.Content = "🔊 읽어주기";
            BtnTtsNotice.Background = (Brush)new BrushConverter().ConvertFromString("#0D9488")!;
        }
        else
        {
            BtnTtsNotice.Content = "⏹️ 중지";
            BtnTtsNotice.Background = Brushes.Crimson;
            _ = _ttsService.SpeakAsync(TbMemo.Text);
        }
    }

    private void BtnBoardSets_Click(object sender, RoutedEventArgs e)
    {
        if (_configService == null) return;

        var dialog = new AutoNoticeSettingsDialog(_configService, TbMemo.Text)
        {
            Owner = Window.GetWindow(this)
        };
        dialog.SetApplied += appliedText => TbMemo.Text = appliedText;
        dialog.ShowDialog();
    }
}
