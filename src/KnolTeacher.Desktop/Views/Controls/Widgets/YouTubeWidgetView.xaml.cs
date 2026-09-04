using System;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;
using KnolTeacher.Desktop.Views.Windows;

namespace KnolTeacher.Desktop.Views.Controls.Widgets;

public partial class YouTubeWidgetView : UserControl
{
    private readonly IYouTubeService? _youtubeService;
    private readonly Action<string?>? _openPlayerCallback;

    public YouTubeWidgetView(IYouTubeService? youtubeService = null, Action<string?>? openPlayerCallback = null)
    {
        _youtubeService = youtubeService;
        _openPlayerCallback = openPlayerCallback;
        InitializeComponent();

        Loaded += (s, e) => RefreshTracks();
        if (_youtubeService != null)
        {
            _youtubeService.OnPlaylistChanged += RefreshTracks;
        }
    }

    private void RefreshTracks()
    {
        if (_youtubeService == null) return;
        CbTracks.ItemsSource = null;
        CbTracks.ItemsSource = _youtubeService.Playlist.Select(t => $"{t.Emoji} {t.Name}").ToList();
        if (_youtubeService.Playlist.Count > 0 && CbTracks.SelectedIndex < 0)
        {
            CbTracks.SelectedIndex = 0;
        }
    }

    private void CbTracks_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (_youtubeService == null) return;
        int idx = CbTracks.SelectedIndex;
        if (idx >= 0 && idx < _youtubeService.Playlist.Count)
        {
            var track = _youtubeService.Playlist[idx];
            TxtTitle.Text = track.Name;
            TxtStatus.Text = $"{track.Author} • {track.SectionDisplay}";
        }
    }

    private void BtnOpenPlayer_Click(object sender, RoutedEventArgs e)
    {
        string? vid = null;
        if (_youtubeService != null && CbTracks.SelectedIndex >= 0 && CbTracks.SelectedIndex < _youtubeService.Playlist.Count)
        {
            vid = _youtubeService.Playlist[CbTracks.SelectedIndex].VideoId;
        }

        if (_openPlayerCallback != null)
        {
            _openPlayerCallback(vid);
        }
        else if (_youtubeService != null)
        {
            var win = new YouTubePlayerWindow(_youtubeService);
            if (!string.IsNullOrEmpty(vid)) win.PlayVideoId(vid);
            win.Show();
        }
    }

    private async void BtnAdd_Click(object sender, RoutedEventArgs e)
    {
        if (_youtubeService == null) return;
        var win = Window.GetWindow(this);
        var dlg = new PromptInputDialog("새 유튜브 링크 등록", "유튜브 URL을 입력하세요:", "")
        {
            Owner = win
        };

        if (dlg.ShowDialog() == true && !string.IsNullOrWhiteSpace(dlg.InputText))
        {
            string raw = dlg.InputText.Trim();
            string vid = _youtubeService.ExtractVideoId(raw);
            if (!string.IsNullOrEmpty(vid))
            {
                var (title, author) = await _youtubeService.FetchMetaAsync(vid);
                _youtubeService.AddTrack(new YouTubeTrackItem
                {
                    Name = title,
                    Author = author,
                    VideoId = vid,
                    Url = raw,
                    Loop = true
                });
                RefreshTracks();
                CbTracks.SelectedIndex = _youtubeService.Playlist.Count - 1;
            }
        }
    }
}
