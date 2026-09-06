using System;
using System.Windows;
using System.Windows.Input;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class NoticeZoomWindow : Window
{
    private readonly ITtsService? _ttsService;
    private string _currentText = string.Empty;

    public NoticeZoomWindow(string noticeText, ITtsService? ttsService = null)
    {
        InitializeComponent();
        _ttsService = ttsService;
        _currentText = string.IsNullOrWhiteSpace(noticeText) ? "등록된 알림장 내용이 없습니다." : noticeText;
        TxtLargeNotice.Text = _currentText;

        if (_ttsService != null)
        {
            _ttsService.SpeakingStateChanged += OnSpeakingStateChanged;
        }

        Closed += (s, e) =>
        {
            if (_ttsService != null)
            {
                _ttsService.SpeakingStateChanged -= OnSpeakingStateChanged;
                _ttsService.Stop();
            }
        };
    }

    private void OnSpeakingStateChanged(bool isSpeaking)
    {
        Dispatcher.Invoke(() =>
        {
            if (isSpeaking)
            {
                TxtTtsLabel.Text = "⏹️ 낭독 중지";
                BtnTts.Background = System.Windows.Media.Brushes.Crimson;
            }
            else
            {
                TxtTtsLabel.Text = "🔊 음성으로 읽기";
                BtnTts.Background = (System.Windows.Media.Brush)new System.Windows.Media.BrushConverter().ConvertFromString("#0369A1")!;
            }
        });
    }

    private void BtnTts_Click(object sender, RoutedEventArgs e)
    {
        if (_ttsService == null) return;

        if (_ttsService.IsSpeaking)
        {
            _ttsService.Stop();
        }
        else
        {
            _ = _ttsService.SpeakAsync(_currentText);
        }
    }

    private void BtnClose_Click(object sender, RoutedEventArgs e)
    {
        Close();
    }

    private void Window_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Escape)
        {
            Close();
            e.Handled = true;
        }
    }

    private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        Close();
    }

    private void Card_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        e.Handled = true; // Prevent closing when clicking card itself
    }
}
