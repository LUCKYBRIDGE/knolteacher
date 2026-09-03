"""
놀티쳐 (KnolTeacher) - 유튜브 초강력 무광고 백그라운드 오디오 엔진 (Ultimate Zero-Ad Engine)
- 1. 네트워크 레벨 광고 요청 원천 차단 (XHR & Fetch Interception)
- 2. DOM MutationObserver 0ms 초광속 즉시 반응 광고 스키퍼
- 3. 광고 발생 즉시 볼륨 0 + 음소거 + 16배속 + 끝 지점 강제 점프
- 4. yt-dlp 다이렉트 오디오 스트림 최우선 무광고 파이프라인
"""

import os
import sys
import threading
import bottle
from bottle import Bottle, request, response
import webview

PORT = 28888
app = Bottle()
window_ref = None

HTML_CONTENT = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>KnolTeacher Ultimate Zero-Ad Audio Engine</title>
  <style>
    body { margin:0; padding:0; background:#000; overflow:hidden; }
    /* 광고 관련 모든 오버레이 및 배너 스타일 레벨 완전 소멸 */
    .video-ads, .ytp-ad-module, .ytp-ad-overlay-container,
    .ytp-ad-message-container, .ytp-ad-action-interstitial,
    .ytp-ad-player-overlay, .ytp-ad-feedback-dialog-container,
    #masthead-ad, ytd-ad-slot-renderer {
      display: none !important;
      visibility: hidden !important;
      width: 0 !important;
      height: 0 !important;
      opacity: 0 !important;
      pointer-events: none !important;
    }
  </style>
</head>
<body>
  <!-- 1. 무광고 다이렉트 오디오 엘리먼트 -->
  <audio id="directAudio" preload="auto"></audio>

  <!-- 2. Iframe Fallback 엘리먼트 -->
  <div id="player"></div>

  <script>
    // ══════════════════════════════════════════════════════════════════════════
    // [결계 1] 네트워크 레벨 광고 요청 원천 차단 (uBlock Origin 코어 메커니즘)
    // ══════════════════════════════════════════════════════════════════════════
    const AD_DOMAINS = [
      'googleads', 'doubleclick', 'pagead', 'adservice', 'youtube.com/api/stats/ads',
      'youtube.com/ptracking', 'youtube.com/pagead', 'adunit', '/log_event',
      'play.google.com/log', 'static.doubleclick.net', 'ad.doubleclick.net'
    ];

    function isAdUrl(url) {
      if (!url) return false;
      var str = String(url).toLowerCase();
      for (var i = 0; i < AD_DOMAINS.length; i++) {
        if (str.indexOf(AD_DOMAINS[i]) !== -1) return true;
      }
      return false;
    }

    // Fetch 가로채기
    const origFetch = window.fetch;
    window.fetch = function(input, init) {
      var u = (typeof input === 'string') ? input : (input && input.url ? input.url : '');
      if (isAdUrl(u)) {
        return Promise.resolve(new Response('{}', {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        }));
      }
      return origFetch.apply(this, arguments);
    };

    // XHR 가로채기
    const origOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {
      this._isBlocked = isAdUrl(url);
      return origOpen.apply(this, arguments);
    };

    const origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function() {
      if (this._isBlocked) {
        Object.defineProperty(this, 'readyState', { value: 4 });
        Object.defineProperty(this, 'status', { value: 200 });
        Object.defineProperty(this, 'responseText', { value: '{}' });
        var self = this;
        setTimeout(function() {
          if (typeof self.onreadystatechange === 'function') self.onreadystatechange();
          if (typeof self.onload === 'function') self.onload();
        }, 1);
        return;
      }
      return origSend.apply(this, arguments);
    };

    // ══════════════════════════════════════════════════════════════════════════
    // [결계 2] 다이렉트 오디오 vs Iframe 플레이어
    // ══════════════════════════════════════════════════════════════════════════
    var directAudio = document.getElementById('directAudio');
    var player = null;
    var currentMode = 'none';
    var userVolume = 80;

    function playDirect(streamUrl) {
      currentMode = 'direct';
      if (player && player.stopVideo) player.stopVideo();

      directAudio.src = streamUrl;
      directAudio.volume = userVolume / 100.0;
      directAudio.play().catch(function(e) { console.log('Play direct err:', e); });
    }

    var tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    var firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

    function onYouTubeIframeAPIReady() {
      // ready
    }

    function playIframe(id) {
      currentMode = 'iframe';
      directAudio.pause();
      directAudio.src = '';

      if (!player) {
        player = new YT.Player('player', {
          height: '200',
          width: '200',
          videoId: id,
          host: 'https://www.youtube-nocookie.com',
          playerVars: {
            'autoplay': 1,
            'controls': 0,
            'disablekb': 1,
            'fs': 0,
            'rel': 0,
            'modestbranding': 1,
            'iv_load_policy': 3,
            'playsinline': 1,
            'enablejsapi': 1
          },
          events: {
            'onReady': function(e) {
              e.target.setVolume(userVolume);
              e.target.playVideo();
            },
            'onStateChange': onPlayerStateChange
          }
        });
      } else {
        player.loadVideoById(id);
        player.setVolume(userVolume);
        player.playVideo();
      }
    }

    function onPlayerStateChange(event) {
      // 광고 감지 시 즉시 처리
      killAdNow();
    }

    // ══════════════════════════════════════════════════════════════════════════
    // [결계 3] 0ms 초광속 스마트 광고 인터셉터 (MutationObserver + 10ms Watchdog)
    // ══════════════════════════════════════════════════════════════════════════
    function killAdNow() {
      try {
        var isAd = document.querySelector('.ad-showing, .ad-interrupting, .ytp-ad-module, .video-ads');
        var v = document.querySelector('video');

        // 1. 광고 영상 발생 즉시: 소리 완전 차단(Mute) + 16배속 + 비디오 끝으로 점프
        if (v && isAd) {
          v.muted = true;
          v.volume = 0;
          v.playbackRate = 16.0;
          if (v.duration && isFinite(v.duration)) {
            v.currentTime = v.duration - 0.05;
          }
        } else if (v && !isAd) {
          // 일반 영상으로 복귀 시 볼륨 및 배속 정상화
          v.muted = false;
          v.volume = userVolume / 100.0;
          v.playbackRate = 1.0;
        }

        // 2. 모든 스킵 버튼 탐지 즉시 0ms 클릭
        var skipSelectors = [
          '.ytp-ad-skip-button',
          '.ytp-ad-skip-button-modern',
          '.videoAdUiSkipButton',
          '.ytp-ad-overlay-close-button',
          '.ytp-ad-skip-button-container',
          '.ytp-skip-ad-button',
          'button.ytp-ad-skip-button',
          '.ytp-ad-preview-container'
        ];
        for (var i = 0; i < skipSelectors.length; i++) {
          var btns = document.querySelectorAll(skipSelectors[i]);
          for (var j = 0; j < btns.length; j++) {
            btns[j].click();
          }
        }

        // 3. 광고 오버레이 노드 완전 제거
        var adOverlays = document.querySelectorAll('.ytp-ad-overlay-container, .ytp-ad-message-container, #masthead-ad');
        for (var k = 0; k < adOverlays.length; k++) {
          adOverlays[k].remove();
        }
      } catch(e) {}
    }

    // A. DOM 변경 즉시 0ms 인터셉터 (초고속 반응)
    var observer = new MutationObserver(function(mutations) {
      killAdNow();
    });
    observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true });

    // B. 초미세 10ms 주기 워치독 (혹시 모를 누락 방지)
    setInterval(killAdNow, 10);

    // ══════════════════════════════════════════════════════════════════════════
    // [결계 4] 오디오 통합 제어 API
    // ══════════════════════════════════════════════════════════════════════════
    function pauseAll() {
      if (currentMode === 'direct') {
        directAudio.pause();
      } else if (player && player.pauseVideo) {
        player.pauseVideo();
      }
    }

    function resumeAll() {
      if (currentMode === 'direct') {
        directAudio.play();
      } else if (player && player.playVideo) {
        player.playVideo();
      }
    }

    function stopAll() {
      directAudio.pause();
      directAudio.src = '';
      if (player && player.stopVideo) player.stopVideo();
      currentMode = 'none';
    }

    function setVolumeAll(val) {
      userVolume = Math.max(0, Math.min(100, val));
      directAudio.volume = userVolume / 100.0;
      if (player && player.setVolume) player.setVolume(userVolume);
    }
  </script>
</body>
</html>
"""

@app.route('/ping')
def ping():
    return {"status": "ok", "engine": "ultimate_zero_ad"}

@app.route('/play_direct')
def play_direct():
    stream_url = request.query.get('url', '').strip()
    if not stream_url:
        return {"status": "error", "message": "Missing stream url"}
    if window_ref:
        js = f"playDirect({bottle.json_dumps(stream_url)});"
        window_ref.evaluate_js(js)
    return {"status": "playing_direct"}

@app.route('/play_iframe')
def play_iframe():
    vid = request.query.get('id', '').strip()
    if not vid:
        return {"status": "error", "message": "Missing video id"}
    if window_ref:
        js = f"playIframe('{vid}');"
        window_ref.evaluate_js(js)
    return {"status": "playing_iframe", "id": vid}

@app.route('/pause')
def pause():
    if window_ref:
        window_ref.evaluate_js("pauseAll();")
    return {"status": "paused"}

@app.route('/resume')
def resume():
    if window_ref:
        window_ref.evaluate_js("resumeAll();")
    return {"status": "resumed"}

@app.route('/stop')
def stop():
    if window_ref:
        window_ref.evaluate_js("stopAll();")
    return {"status": "stopped"}

@app.route('/volume')
def volume():
    val = request.query.get('val', '80')
    try:
        v = int(val)
        if window_ref:
            window_ref.evaluate_js(f"setVolumeAll({v});")
    except Exception:
        pass
    return {"status": "volume_set", "val": val}

@app.route('/exit')
def exit_worker():
    def _kill():
        import time
        time.sleep(0.5)
        if window_ref:
            window_ref.destroy()
        os._exit(0)
    threading.Thread(target=_kill, daemon=True).start()
    return {"status": "exiting"}

def start_server():
    bottle.run(app, host='127.0.0.1', port=PORT, quiet=True)

def main():
    global window_ref
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    window_ref = webview.create_window(
        'KnolTeacher Ultimate Zero-Ad Audio Engine',
        html=HTML_CONTENT,
        width=10, height=10,
        hidden=True
    )
    webview.start()

if __name__ == '__main__':
    main()
