using System;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using KnolTeacher.Desktop.Models;
using KnolTeacher.Desktop.Services;

namespace KnolTeacher.Desktop.Views.Windows;

public partial class YouTubePlayerWindow : Window
{
    private readonly IYouTubeService _youtubeService;
    private YouTubeTrackItem? _currentTrack;
    private bool _isSliderDragging = false;
    private double _currentSeconds = 0;
    private double _totalSeconds = 0;
    private bool _isPlaying = false;
    private bool _isAudioOnly = false;
    private bool _isWebViewReady = false;

    public YouTubePlayerWindow(IYouTubeService youtubeService)
    {
        _youtubeService = youtubeService;
        InitializeComponent();

        RefreshPlaylistDropdown();
        _youtubeService.OnPlaylistChanged += RefreshPlaylistDropdown;

        Loaded += async (s, e) =>
        {
            await InitWebViewAsync();
            if (CbPlaylist.Items.Count > 0)
            {
                CbPlaylist.SelectedIndex = 0;
            }
        };
    }

    private void RefreshPlaylistDropdown()
    {
        CbPlaylist.ItemsSource = null;
        CbPlaylist.ItemsSource = _youtubeService.Playlist.Select(t => $"{t.Emoji} {t.Name}").ToList();
        if (_youtubeService.Playlist.Count > 0 && CbPlaylist.SelectedIndex < 0)
        {
            CbPlaylist.SelectedIndex = 0;
        }
    }

    private async Task InitWebViewAsync()
    {
        try
        {
            await WebPlayer.EnsureCoreWebView2Async();
            WebPlayer.CoreWebView2.Settings.IsStatusBarEnabled = false;
            WebPlayer.CoreWebView2.Settings.AreDevToolsEnabled = false;
            WebPlayer.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;

            WebPlayer.WebMessageReceived += WebPlayer_WebMessageReceived;
            _isWebViewReady = true;

            if (_currentTrack != null)
            {
                LoadTrackHtml(_currentTrack);
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show($"WebView2 초기화 실패: {ex.Message}\nEdge WebView2 런타임 설치 여부를 확인해 주세요.", "오류", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void WebPlayer_WebMessageReceived(object? sender, Microsoft.Web.WebView2.Core.CoreWebView2WebMessageReceivedEventArgs e)
    {
        try
        {
            string raw = e.TryGetWebMessageAsString();
            if (string.IsNullOrEmpty(raw)) return;

            using var doc = JsonDocument.Parse(raw);
            var root = doc.RootElement;
            if (root.TryGetProperty("type", out var typeProp) && typeProp.GetString() == "time")
            {
                _currentSeconds = root.GetProperty("cur").GetDouble();
                _totalSeconds = root.GetProperty("dur").GetDouble();
                int state = root.GetProperty("state").GetInt32();

                _isPlaying = (state == 1);
                BtnPlayPause.Content = _isPlaying ? "⏸" : "▶";

                if (!_isSliderDragging && _totalSeconds > 0)
                {
                    TxtCurrentTime.Text = FormatTime((int)_currentSeconds);
                    TxtTotalTime.Text = FormatTime((int)_totalSeconds);
                    SliderProgress.Maximum = _totalSeconds;
                    SliderProgress.Value = _currentSeconds;
                }
            }
        }
        catch { }
    }

    private string FormatTime(int sec)
    {
        int m = sec / 60;
        int s = sec % 60;
        return $"{m:D2}:{s:D2}";
    }

    private int ParseTime(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return 0;
        var parts = text.Split(':');
        if (parts.Length == 2 && int.TryParse(parts[0], out int m) && int.TryParse(parts[1], out int s))
        {
            return Math.Max(0, m * 60 + s);
        }
        if (int.TryParse(text, out int sec))
        {
            return Math.Max(0, sec);
        }
        return 0;
    }

    public void PlayVideoId(string videoId, string title = "유튜브 재생")
    {
        var track = _youtubeService.Playlist.FirstOrDefault(t => t.VideoId == videoId);
        if (track == null)
        {
            track = new YouTubeTrackItem
            {
                Name = title,
                VideoId = videoId,
                Url = $"https://www.youtube.com/watch?v={videoId}",
                Loop = true
            };
            _youtubeService.AddTrack(track);
        }

        int idx = _youtubeService.Playlist.IndexOf(track);
        if (idx >= 0)
        {
            CbPlaylist.SelectedIndex = idx;
        }
    }

    private void CbPlaylist_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        int idx = CbPlaylist.SelectedIndex;
        if (idx >= 0 && idx < _youtubeService.Playlist.Count)
        {
            _currentTrack = _youtubeService.Playlist[idx];
            TxtNowPlaying.Text = $"{_currentTrack.Emoji} {_currentTrack.Name} ({_currentTrack.Author})";

            TbStartSec.Text = FormatTime(_currentTrack.StartSeconds);
            TbEndSec.Text = FormatTime(_currentTrack.EndSeconds);
            ChkEnableSection.IsChecked = _currentTrack.IsSectionRepeat;
            ToggleLoop.IsChecked = _currentTrack.Loop;

            if (_isWebViewReady)
            {
                LoadTrackHtml(_currentTrack);
            }
        }
    }

    private void LoadTrackHtml(YouTubeTrackItem track)
    {
        string html = $@"<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'/>
  <style>
    html, body {{ margin:0; padding:0; width:100%; height:100%; overflow:hidden; background:#000; }}
    #player {{ width:100%; height:100%; }}
  </style>
</head>
<body>
  <div id='player'></div>
  <script>
    const AD_DOMAINS = ['googleads', 'doubleclick', 'pagead', 'adservice', 'youtube.com/api/stats/ads', 'youtube.com/ptracking', 'youtube.com/pagead', 'adunit', '/log_event'];
    function isAdUrl(u) {{
      if (!u) return false;
      var s = String(u).toLowerCase();
      for (var i=0; i<AD_DOMAINS.length; i++) {{ if (s.indexOf(AD_DOMAINS[i]) !== -1) return true; }}
      return false;
    }}
    const origFetch = window.fetch;
    window.fetch = function(i, init) {{
      var u = (typeof i === 'string') ? i : (i && i.url ? i.url : '');
      if (isAdUrl(u)) return Promise.resolve(new Response('{{}}', {{ status: 200, headers: {{ 'Content-Type': 'application/json' }} }}));
      return origFetch.apply(this, arguments);
    }};

    var tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    var firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

    var player = null;
    var isLoop = {(track.Loop ? "true" : "false")};
    var isSectionRepeat = {(track.IsSectionRepeat ? "true" : "false")};
    var startSec = {track.StartSeconds};
    var endSec = {track.EndSeconds};

    function onYouTubeIframeAPIReady() {{
      player = new YT.Player('player', {{
        height: '100%',
        width: '100%',
        videoId: '{track.VideoId}',
        host: 'https://www.youtube-nocookie.com',
        playerVars: {{
          'autoplay': 1,
          'controls': 1,
          'rel': 0,
          'modestbranding': 1,
          'iv_load_policy': 3,
          'fs': 1,
          'playsinline': 1,
          'enablejsapi': 1
        }},
        events: {{
          'onReady': onPlayerReady,
          'onStateChange': onPlayerStateChange
        }}
      }});
    }}

    function onPlayerReady(event) {{
      event.target.playVideo();
      if (startSec > 0) event.target.seekTo(startSec, true);
    }}

    function onPlayerStateChange(event) {{
      killAdNow();
      if (event.data === YT.PlayerState.ENDED) {{
        if (isSectionRepeat) {{
          player.seekTo(startSec, true);
          player.playVideo();
        }} else if (isLoop) {{
          player.seekTo(0, true);
          player.playVideo();
        }}
      }}
    }}

    function killAdNow() {{
      try {{
        var isAd = document.querySelector('.ad-showing, .ad-interrupting, .ytp-ad-module, .video-ads');
        var v = document.querySelector('video');
        if (v && isAd) {{
          v.muted = true;
          v.volume = 0;
          try {{ v.playbackRate = 64.0; }} catch(e) {{ try {{ v.playbackRate = 16.0; }} catch(e2) {{}} }}
          if (v.duration && isFinite(v.duration)) {{ v.currentTime = v.duration; }} else {{ v.currentTime = 999999; }}
          if (player && typeof player.skipAd === 'function') try {{ player.skipAd(); }} catch(e) {{}}
        }} else if (v && !isAd) {{
          v.muted = false;
          v.playbackRate = 1.0;
        }}
        var skipBtns = document.querySelectorAll('.ytp-ad-skip-button, .ytp-ad-skip-button-modern, .videoAdUiSkipButton, .ytp-ad-skip-button-container, .ytp-skip-ad-button');
        for (var j=0; j<skipBtns.length; j++) skipBtns[j].click();
        var overlays = document.querySelectorAll('.ytp-ad-overlay-container, .ytp-ad-message-container');
        for (var k=0; k<overlays.length; k++) overlays[k].remove();
      }} catch(e) {{}}
    }}
    setInterval(killAdNow, 20);

    setInterval(function() {{
      if (player && typeof player.getCurrentTime === 'function') {{
        var cur = player.getCurrentTime();
        var dur = player.getDuration();
        if (isSectionRepeat && endSec > startSec && cur >= endSec) {{
          player.seekTo(startSec, true);
          player.playVideo();
        }}
        if (window.chrome && window.chrome.webview) {{
          window.chrome.webview.postMessage(JSON.stringify({{
            type: 'time',
            cur: cur,
            dur: dur,
            state: (typeof player.getPlayerState === 'function') ? player.getPlayerState() : -1
          }}));
        }}
      }}
    }}, 250);

    window.playVideo = function() {{ if (player) player.playVideo(); }};
    window.pauseVideo = function() {{ if (player) player.pauseVideo(); }};
    window.seekTo = function(s) {{ if (player) player.seekTo(s, true); }};
    window.setVolume = function(v) {{ if (player) player.setVolume(v); }};
    window.setLoop = function(l) {{ isLoop = l; }};
    window.setSectionRepeat = function(enabled, a, b) {{
      isSectionRepeat = enabled;
      startSec = a;
      endSec = b;
    }};
  </script>
</body>
</html>";

        WebPlayer.NavigateToString(html);
    }

    private async void BtnPlayPause_Click(object sender, RoutedEventArgs e)
    {
        if (!_isWebViewReady) return;
        if (_isPlaying)
        {
            await WebPlayer.ExecuteScriptAsync("window.pauseVideo();");
        }
        else
        {
            await WebPlayer.ExecuteScriptAsync("window.playVideo();");
        }
    }

    private void BtnPrev_Click(object sender, RoutedEventArgs e)
    {
        if (CbPlaylist.Items.Count == 0) return;
        int next = CbPlaylist.SelectedIndex - 1;
        if (next < 0) next = CbPlaylist.Items.Count - 1;
        CbPlaylist.SelectedIndex = next;
    }

    private void BtnNext_Click(object sender, RoutedEventArgs e)
    {
        if (CbPlaylist.Items.Count == 0) return;
        int next = (CbPlaylist.SelectedIndex + 1) % CbPlaylist.Items.Count;
        CbPlaylist.SelectedIndex = next;
    }

    private async void ToggleLoop_Click(object sender, RoutedEventArgs e)
    {
        bool isLoop = ToggleLoop.IsChecked == true;
        if (_currentTrack != null)
        {
            _currentTrack.Loop = isLoop;
            _youtubeService.UpdateTrack(_currentTrack);
        }
        if (_isWebViewReady)
        {
            await WebPlayer.ExecuteScriptAsync($"window.setLoop({(isLoop ? "true" : "false")});");
        }
    }

    private void BtnSetPointA_Click(object sender, RoutedEventArgs e)
    {
        int sec = (int)_currentSeconds;
        TbStartSec.Text = FormatTime(sec);
        ApplySectionRepeat();
    }

    private void BtnSetPointB_Click(object sender, RoutedEventArgs e)
    {
        int sec = (int)_currentSeconds;
        TbEndSec.Text = FormatTime(sec);
        ApplySectionRepeat();
    }

    private void ChkEnableSection_Changed(object sender, RoutedEventArgs e)
    {
        ApplySectionRepeat();
    }

    private void SectionTime_LostFocus(object sender, RoutedEventArgs e)
    {
        ApplySectionRepeat();
    }

    private async void ApplySectionRepeat()
    {
        bool enabled = ChkEnableSection.IsChecked == true;
        int a = ParseTime(TbStartSec.Text);
        int b = ParseTime(TbEndSec.Text);

        if (_currentTrack != null)
        {
            _currentTrack.IsSectionRepeat = enabled;
            _currentTrack.StartSeconds = a;
            _currentTrack.EndSeconds = b;
            _youtubeService.UpdateTrack(_currentTrack);
        }

        if (_isWebViewReady)
        {
            await WebPlayer.ExecuteScriptAsync($"window.setSectionRepeat({(enabled ? "true" : "false")}, {a}, {b});");
        }
    }

    private async void SliderVolume_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (!_isWebViewReady) return;
        await WebPlayer.ExecuteScriptAsync($"window.setVolume({(int)SliderVolume.Value});");
    }

    private void SliderProgress_PreviewMouseDown(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        _isSliderDragging = true;
    }

    private async void SliderProgress_PreviewMouseUp(object sender, System.Windows.Input.MouseButtonEventArgs e)
    {
        _isSliderDragging = false;
        if (_isWebViewReady)
        {
            await WebPlayer.ExecuteScriptAsync($"window.seekTo({SliderProgress.Value});");
        }
    }

    private void BtnAudioModeToggle_Click(object sender, RoutedEventArgs e)
    {
        _isAudioOnly = !_isAudioOnly;
        if (_isAudioOnly)
        {
            PlayerBorder.Visibility = Visibility.Collapsed;
            Height = 220;
            BtnAudioModeToggle.Content = "📺 영상 모드";
            Title = "🎧 교실 BGM 오디오 모드 (화면 숨김)";
        }
        else
        {
            PlayerBorder.Visibility = Visibility.Visible;
            Height = 680;
            BtnAudioModeToggle.Content = "🎧 오디오 모드";
            Title = "🎵 교실 무광고 유튜브 BGM & 영상 플레이어";
        }
    }

    private async void BtnAddLink_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new PromptInputDialog("새 유튜브 링크 등록", "유튜브 영상 또는 음악 링크(URL)를 입력하세요:", "")
        {
            Owner = this
        };

        if (dlg.ShowDialog() == true && !string.IsNullOrWhiteSpace(dlg.InputText))
        {
            string raw = dlg.InputText.Trim();
            string vid = _youtubeService.ExtractVideoId(raw);
            if (string.IsNullOrEmpty(vid))
            {
                MessageBox.Show("유효한 유튜브 링크 또는 동영상 ID가 아닙니다.", "확인", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            var (title, author) = await _youtubeService.FetchMetaAsync(vid);
            var newTrack = new YouTubeTrackItem
            {
                Name = title,
                Author = author,
                VideoId = vid,
                Url = raw,
                Emoji = "🎵",
                Category = "선생님 등록",
                Loop = true
            };

            _youtubeService.AddTrack(newTrack);
            RefreshPlaylistDropdown();
            CbPlaylist.SelectedIndex = _youtubeService.Playlist.Count - 1;
            HudNotificationWindow.Instance.ShowToast("🎵", $"'{title}' 링크가 등록되었습니다.");
        }
    }

    private void BtnDeleteTrack_Click(object sender, RoutedEventArgs e)
    {
        if (_currentTrack != null)
        {
            if (MessageBox.Show($"'{_currentTrack.Name}' 음악을 보관함에서 삭제하시겠습니까?", "삭제 확인", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
            {
                _youtubeService.DeleteTrack(_currentTrack.Id);
                RefreshPlaylistDropdown();
            }
        }
    }

    protected override void OnClosing(System.ComponentModel.CancelEventArgs e)
    {
        e.Cancel = true;
        Hide();
    }
}
