"""
놀티쳐 (KnolTeacher) - 교실 전용 무광고 클린 브라우저 (Classroom Clean Browser)
- 학생 공유 화면(교실 TV) 연동
- X-Frame-Options 제한 없이 세상 모든 웹사이트(네이버, 구글, e학습터 등) 고화질 직접 렌더링
- 매 페이지 로드 시 DOM MutationObserver 기반 광고 차단 JS 자동 주입 (애드센스, 애드핏, 타불라, 팝업 박멸)
"""

import os
import sys
import argparse
import webview

ADBLOCK_JS = """
(function() {
  console.log('[놀티쳐] 교실 클린 광고 차단 엔진 가동 중...');

  const AD_SELECTORS = [
    'ins.adsbygoogle', 'iframe[id*="google_ads"]', '.ad-banner', '[id*="ad-container"]',
    '.kakaopay_ad', '[class*="sponsored"]', '.taboola', '.outbrain', '.dable',
    '.ad_area', '.ad_wrapper', '.banner_ad', '#ad_body', '.aside_ad',
    '.sub_ad', '.top_ad', '.bottom_ad', '.floating_ad', '#criteo-tags-div',
    '.ad_header', '[id*="ad_section"]', '.ad_item', '.advertisement',
    '#banner_area', '.main_ad', '.media_ad', '[data-ad-unit]',
    '.news_ad', '.popup_ad', '.layer_ad', '#ad_layer'
  ];

  function removeAds() {
    AD_SELECTORS.forEach(function(sel) {
      var els = document.querySelectorAll(sel);
      for (var i = 0; i < els.length; i++) {
        els[i].style.display = 'none';
        els[i].style.visibility = 'hidden';
        els[i].remove();
      }
    });

    // 악성/상업용 팝업 창 차단
    window.open = function(url) {
      console.log('[놀티쳐] 교실 화면 내 팝업 차단:', url);
      return null;
    };
  }

  // 즉시 1회 실행
  removeAds();

  // DOM 변화 감지 시 즉각 제거
  try {
    const obs = new MutationObserver(function() {
      removeAds();
    });
    obs.observe(document.documentElement, { childList: true, subtree: true });
  } catch(e) {}

  // 300ms 주기 안전망
  setInterval(removeAds, 300);
})();
"""


def on_loaded(window):
    """페이지 로딩 완료 시 광고 차단 스크립트 주입"""
    try:
        window.evaluate_js(ADBLOCK_JS)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="KnolTeacher Classroom Clean Browser")
    parser.add_argument("--url", default="https://www.naver.com", help="Initial URL")
    args = parser.parse_args()

    window = webview.create_window(
        "🌐 놀티쳐 교실 클린 브라우저 (🛡️ 광고 차단 ON)",
        url=args.url,
        width=1150,
        height=750,
        min_size=(800, 500),
        text_select=True,
        zoomable=True
    )
    window.events.loaded += on_loaded
    webview.start()


if __name__ == '__main__':
    main()
