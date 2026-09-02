import json
import urllib.request
import urllib.parse
from typing import Optional, Any

class CdpBridge:
    """
    Chrome / Edge 브라우저 DevTools Protocol(CDP) 직접 연결 및 스크립트 실행 브릿지
    """
    def __init__(self, port: int = 9222):
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"

    def is_browser_connected(self) -> bool:
        """디버깅 포트가 열려있는지 확인"""
        try:
            req = urllib.request.Request(f"{self.base_url}/json/version", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=1) as response:
                return response.status == 200
        except Exception:
            return False

    def find_neis_tab(self) -> Optional[dict[str, Any]]:
        """열려있는 브라우저 탭 중 나이스 탭 탐색"""
        try:
            req = urllib.request.Request(f"{self.base_url}/json/list", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=2) as response:
                tabs = json.loads(response.read().decode("utf-8"))
                for tab in tabs:
                    url = tab.get("url", "").lower()
                    title = tab.get("title", "")
                    if "neis.go.kr" in url or "나이스" in title or "행동특성" in title or "학기말" in title:
                        return tab
                # 나이스 탭이 없으면 첫 번째 활성 탭
                return tabs[0] if tabs else None
        except Exception as e:
            print(f"Error finding tab: {e}")
            return None

cdp_bridge = CdpBridge()
