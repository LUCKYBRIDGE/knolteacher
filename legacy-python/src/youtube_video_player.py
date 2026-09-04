"""
놀티쳐 (KnolTeacher) - 학생용 무광고 유튜브 영상 플레이어 (Classroom Video Player)
- 학생 공유 화면 연동: 광고 없이 고화질로 수업 영상 재생
- 64배속 가속 + 0초 끝지점 순간이동 + uBlock 네트워크 차단 4중 결계 탑재
- F11 전체화면 토글 지원
"""

import os
import sys
import argparse
import webview


def make_html(video_id: str, title: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title} - 놀티쳐 수업 영상</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #000;
      overflow: hidden;
      width: 100vw;
      height: 100vh;
      display: flex;
      flex-direction: column;
      font-family: 'Pretendard', -apple-system, sans-serif;
    }}
    #header {{
      height: 42px;
      background: #0f172a;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      color: #f8fafc;
      border-bottom: 1px solid #1e293b;
      user-select: none;
    }}
    .title-box {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      font-weight: 700;
      color: #38bdf8;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
      max-width: 70vw;
    }}
    .badge {{
      background: #059669;
      color: #fff;
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 4px;
      font-weight: bold;
    }}
    .btn-group {{
      display: flex;
      gap: 8px;
    }}
    .btn {{
      background: #1e293b;
      color: #e2e8f0;
      border: 1px solid #334155;
      padding: 4px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .btn:hover {{
      background: #0284c7;
      color: #fff;
      border-color: #38bdf8;
    }}
    #video-container {{
      flex: 1;
      width: 100%;
      height: calc(100vh - 42px);
      position: relative;
      background: #000;
    }}
    #player {{
      width: 100%;
      height: 100%;
    }}
    /* 유튜브 광고 오버레이 및 배너 스타일 레벨 완전 소멸 */
    .video-ads, .ytp-ad-module, .ytp-ad-overlay-container,
    .ytp-ad-message-container, .ytp-ad-action-interstitial,
    .ytp-ad-player-overlay, .ytp-ad-feedback-dialog-container,
    #masthead-ad, ytd-ad-slot-renderer, .ytp-pause-overlay {{
      display: none !important;
      visibility: hidden !important;
      width: 0 !important;
      height: 0 !important;
      opacity: 0 !important;
      pointer-events: none !important;
    }}
  </style>
</head>
<body>
  <div id="header">
    <div class="title-box">
      <span class="badge">무광고 수업 모드</span>
      <span>🎬 {title}</span>
    </div>
    <div class="btn-group">
      <button class="btn" onclick="toggleFullScreen()">⛶ 전체화면</button>
      <button class="btn" style="background:#dc2626; border-color:#ef4444;" onclick="closeWindow()">✕ 닫기</button>
    </div>
  </div>
  <div id="video-container">
    <div id="player"></div>
  </div>

  <script>
    // ══════════════════════════════════════════════════════════════════════════
    // [결계 1] uBlock Origin 네트워크 레벨 광고 요청 차단
    // ══════════════════════════════════════════════════════════════════════════
    const AD_DOMAINS = [
      'googleads', 'doubleclick', 'pagead', 'adservice', 'youtube.com/api/stats/ads',
      'youtube.com/ptracking', 'youtube.com/pagead', 'adunit', '/log_event',
      'play.google.com/log', 'static.doubleclick.net', 'ad.doubleclick.net'
    ];

    function isAdUrl(url) {{
      if (!url) return false;
      var str = String(url).toLowerCase();
      for (var i = 0; i < AD_DOMAINS.length; i++) {{
        if (str.indexOf(AD_DOMAINS[i]) !== -1) return true;
      }}
      return false;
    }}

    const origFetch = window.fetch;
    window.fetch = function(input, init) {{
      var u = (typeof input === 'string') ? input : (input && input.url ? input.url : '');
      if (isAdUrl(u)) {{
        return Promise.resolve(new Response('{{}}', {{
          status: 200,
          headers: {{ 'Content-Type': 'application/json' }}
        }}));
      }}
      return origFetch.apply(this, arguments);
    }};

    const origOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {{
      this._isBlocked = isAdUrl(url);
      return origOpen.apply(this, arguments);
    }};

    const origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function() {{
      if (this._isBlocked) {{
        Object.defineProperty(this, 'readyState', {{ value: 4 }});
        Object.defineProperty(this, 'status', {{ value: 200 }});
        Object.defineProperty(this, 'responseText', {{ value: '{{}}' }});
        var self = this;
        setTimeout(function() {{
          if (typeof self.onreadystatechange === 'function') self.onreadystatechange();
          if (typeof self.onload === 'function') self.onload();
        }}, 1);
        return;
      }}
      return origSend.apply(this, arguments);
    }};

    // ══════════════════════════════════════════════════════════════════════════
    // [결계 2] YouTube Player Iframe 초기화
    // ══════════════════════════════════════════════════════════════════════════
    var tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    var firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

    var player = null;
    function onYouTubeIframeAPIReady() {{
      player = new YT.Player('player', {{
        height: '100%',
        width: '100%',
        videoId: '{video_id}',
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
          'onReady': function(e) {{ e.target.playVideo(); }},
          'onStateChange': function(e) {{ killAdNow(); }}
        }}
      }});
    }}

    // ══════════════════════════════════════════════════════════════════════════
    // [결계 3] 64배속 + 0초 강제 순간이동(duration teleport) 스마트 광고 인터셉터
    // ══════════════════════════════════════════════════════════════════════════
    function killAdNow() {{
      try {{
        var isAd = document.querySelector('.ad-showing, .ad-interrupting, .ytp-ad-module, .video-ads');
        var v = document.querySelector('video');

        if (v && isAd) {{
          v.muted = true;
          v.volume = 0;
          try {{ v.playbackRate = 64.0; }} catch(e1) {{
            try {{ v.playbackRate = 16.0; }} catch(e2) {{}}
          }}
          if (v.duration && isFinite(v.duration)) {{
            v.currentTime = v.duration; // 0.0001초 만에 광고 끝으로 강제 순간이동
          }} else {{
            v.currentTime = 999999;
          }}
          if (player) {{
            if (typeof player.skipAd === 'function') try {{ player.skipAd(); }} catch(e) {{}}
            if (typeof player.cancelPlayback === 'function') try {{ player.cancelPlayback(); }} catch(e) {{}}
          }}
        }} else if (v && !isAd) {{
          v.muted = false;
          v.playbackRate = 1.0;
        }}

        // 스킵 버튼 즉시 클릭
        var skipSelectors = [
          '.ytp-ad-skip-button', '.ytp-ad-skip-button-modern', '.videoAdUiSkipButton',
          '.ytp-ad-overlay-close-button', '.ytp-ad-skip-button-container', '.ytp-skip-ad-button'
        ];
        for (var i = 0; i < skipSelectors.length; i++) {{
          var btns = document.querySelectorAll(skipSelectors[i]);
          for (var j = 0; j < btns.length; j++) {{
            btns[j].click();
          }}
        }}

        // 오버레이 엘리먼트 소멸
        var adOverlays = document.querySelectorAll('.ytp-ad-overlay-container, .ytp-ad-message-container');
        for (var k = 0; k < adOverlays.length; k++) {{
          adOverlays[k].remove();
        }}
      }} catch(e) {{}}
    }}

    var observer = new MutationObserver(function(mutations) {{
      killAdNow();
    }});
    observer.observe(document.documentElement, {{ childList: true, subtree: true, attributes: true }});
    setInterval(killAdNow, 20);

    // 전체화면 및 닫기
    function toggleFullScreen() {{
      if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen().catch(function(err) {{}});
      }} else {{
        if (document.exitFullscreen) {{
          document.exitFullscreen();
        }}
      }}
    }}

    function closeWindow() {{
      window.close();
    }}
  </script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="KnolTeacher Classroom Video Player")
    parser.add_argument("--id", required=True, help="YouTube Video ID")
    parser.add_argument("--title", default="수업 영상", help="Video Title")
    args = parser.parse_args()

    html = make_html(args.id, args.title)

    window = webview.create_window(
        f"🎬 {args.title} - 놀티쳐 수업 영상",
        html=html,
        width=960,
        height=580,
        min_size=(640, 400),
        background_color="#000000"
    )
    webview.start()


if __name__ == '__main__':
    main()
