"""
놀티쳐 데스크 - 아이콘 렌더러
커스텀 Canvas 기반 벡터 아이콘 생성기
(단순하고 직관적인 아웃라인 스타일)
"""

import math
from PIL import Image, ImageDraw

# ── 공통 설정 ────────────────────────────────────────────────────────────────
ICON_SIZE = 28
STROKE    = 2
PADDING   = 5

COL_MAIN   = "#e2e8f0"
COL_ACTIVE = "#38bdf8"
COL_DANGER = "#f87171"
COL_GREEN  = "#4ade80"
COL_ORANGE = "#fb923c"
COL_YELLOW = "#fde047"

BG = (0, 0, 0, 0)

def _hex(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)

def _make(size=ICON_SIZE):
    img = Image.new("RGBA", (size, size), BG)
    return img, ImageDraw.Draw(img)

def _sw(s=STROKE):
    return max(1, int(s))

def _line(d, pts, col, w=STROKE):
    for i in range(len(pts)-1):
        d.line([pts[i], pts[i+1]], fill=_hex(col), width=_sw(w))

def _circle(d, cx, cy, r, col, w=STROKE, fill=None):
    d.ellipse([cx-r, cy-r, cx+r, cy+r],
              outline=_hex(col), width=_sw(w),
              fill=_hex(fill) if fill else None)

def _rect(d, x0, y0, x1, y1, col, w=STROKE, r=2):
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, outline=_hex(col), width=_sw(w))


# ══════════════════════════════════════════════════════════════════════════════
# 아이콘 함수
# ══════════════════════════════════════════════════════════════════════════════

def icon_pen(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """볼펜/펜 — 비스듬한 펜 실루엣"""
    img, d = _make(size)
    p = PADDING
    # 펜 몸통 (가로로 긴 사각형, 45도 회전처럼 보이게)
    # 끝이 뾰족한 펜
    pts = [(p, size-p-3), (p+3, size-p),
           (size-p-2, p+4), (size-p, p)]
    d.polygon(pts, outline=_hex(color), width=_sw())
    # 펜 끝(팁) 채움
    d.polygon([(p, size-p-3), (p+3, size-p), (p+5, size-p-4)], fill=_hex(color))
    # 펜 클립(옆 선)
    d.line([(p+4, size-p-6), (size-p-3, p+3)], fill=_hex(color), width=_sw())
    return img


def icon_highlighter(color=COL_YELLOW, size=ICON_SIZE, **kw) -> Image.Image:
    """형광펜 — 납작한 마커 끝이 사각형인 형광펜"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    # 형광펜 몸통 (굵고 납작한)
    pts_body = [
        (p+1, size-p-4), (p+4, size-p+1),
        (size-p-4, p+1), (size-p-1, p-2)
    ]
    d.polygon(pts_body, outline=_hex(color), width=sw)
    # 형광펜 끝 (납작한 사각형 tip)
    tip = [(p+1, size-p-4), (p+4, size-p+1), (p+8, size-p-3), (p+5, size-p-8)]
    d.polygon(tip, fill=_hex(color))
    # 반투명 강조 효과 — 가로 줄
    mid_col = "#fef08a"
    d.line([(p+5, size-p-7), (size-p-5, p+4)], fill=_hex(mid_col), width=_sw(STROKE+1))
    return img


def icon_arrow(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """↗ 화살표 — 직선 + 머리"""
    img, d = _make(size)
    p = PADDING + 1
    sw = _sw()
    d.line([(p, size-p), (size-p, p)], fill=_hex(color), width=sw+1)
    d.line([(size-p, p), (size-p-6, p)], fill=_hex(color), width=sw+1)
    d.line([(size-p, p), (size-p, p+6)], fill=_hex(color), width=sw+1)
    return img


def icon_rectangle(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """□ 사각형"""
    img, d = _make(size)
    p = PADDING + 1
    _rect(d, p, p+2, size-p, size-p-2, color, r=3)
    return img


def icon_text(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """T — 텍스트 입력"""
    img, d = _make(size)
    p = PADDING
    sw = _sw(STROKE+1)
    cx = size // 2
    d.line([(p, p+2), (size-p, p+2)], fill=_hex(color), width=sw)
    d.line([(cx, p+2), (cx, size-p)], fill=_hex(color), width=sw)
    d.line([(cx-4, size-p), (cx+4, size-p)], fill=_hex(color), width=sw)
    return img


def icon_eraser(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """지우개 — 직사각형 블록 지우개"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    # 지우개 몸통 (직사각형)
    _rect(d, p, size//2-2, size-p, size-p, color, r=3)
    # 지우개 상단 분리선 (색 구분)
    d.line([(p+1, size//2+4), (size-p-1, size//2+4)], fill=_hex(color), width=sw)
    # 지운 흔적 (점선)
    for x in range(p, size-p-4, 5):
        d.line([(x, size//2-4), (x+3, size//2-4)], fill=_hex(color), width=sw)
    return img


def icon_emoji_stamp(color=COL_YELLOW, size=ICON_SIZE, **kw) -> Image.Image:
    """😊 이모지 스탬프 — 노란 원 + 웃는 얼굴"""
    img, d = _make(size)
    p = PADDING - 1
    cx, cy = size//2, size//2
    r = size//2 - p
    # 노란 원형 얼굴
    _circle(d, cx, cy, r, "#fde047", fill="#fde047")
    # 테두리
    _circle(d, cx, cy, r, "#ca8a04", w=_sw(STROKE+0.5))
    # 눈 (두 점)
    er = 2
    d.ellipse([cx-5-er, cy-4-er, cx-5+er, cy-4+er], fill=_hex("#1e293b"))
    d.ellipse([cx+5-er, cy-4-er, cx+5+er, cy-4+er], fill=_hex("#1e293b"))
    # 미소 (호)
    d.arc([cx-5, cy-1, cx+5, cy+6], start=10, end=170, fill=_hex("#1e293b"), width=_sw(STROKE))
    return img


def icon_undo(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """↩ 실행취소"""
    img, d = _make(size)
    p = PADDING + 2
    sw = _sw()
    cx, cy = size//2, size//2 + 1
    r = size//2 - p
    # 반원호
    d.arc([cx-r, cy-r, cx+r, cy+r], start=190, end=360, fill=_hex(color), width=sw+1)
    d.arc([cx-r, cy-r, cx+r, cy+r], start=0,   end=20,  fill=_hex(color), width=sw+1)
    # 화살표 머리
    ax, ay = cx-r+2, cy+1
    d.polygon([(ax, ay-4), (ax, ay+3), (ax+5, ay-1)], fill=_hex(color))
    return img


def icon_trash(color=COL_DANGER, size=ICON_SIZE, **kw) -> Image.Image:
    """🗑 삭제"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    bx0, bx1 = p+2, size-p-2
    cx = size//2
    _rect(d, bx0, p+5, bx1, size-p, color, r=2)
    d.line([(p, p+5), (size-p, p+5)], fill=_hex(color), width=sw)
    d.line([(cx-3, p+1), (bx0+1, p+5)], fill=_hex(color), width=sw)
    d.line([(cx+3, p+1), (bx1-1, p+5)], fill=_hex(color), width=sw)
    d.line([(cx-3, p+1), (cx+3, p+1)], fill=_hex(color), width=sw)
    # 내부 세로선
    for ox in [-4, 0, 4]:
        d.line([(cx+ox, p+8), (cx+ox, size-p-3)], fill=_hex(color), width=sw)
    return img


def icon_camera(color=COL_GREEN, size=ICON_SIZE, **kw) -> Image.Image:
    """📷 단순한 카메라"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    cx = size//2
    # 몸통
    _rect(d, p, p+5, size-p, size-p, color, r=4)
    # 렌즈 (큰 원)
    _circle(d, cx, (p+5+size-p)//2, 6, color, sw)
    # 뷰파인더 노치
    d.rectangle([cx-4, p+2, cx+4, p+5], outline=_hex(color), width=sw)
    # 플래시 도트
    d.ellipse([size-p-5, p+7, size-p-3, p+9], fill=_hex(color))
    return img


def icon_pin(color=COL_MAIN, size=ICON_SIZE, pinned=True, **kw) -> Image.Image:
    """📌 핀"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    cx = size//2
    pin_col = COL_ACTIVE if pinned else color
    # 핀 머리 (다이아몬드 형)
    d.polygon([(cx, p), (cx+5, p+5), (cx, p+10), (cx-5, p+5)],
              outline=_hex(pin_col), width=sw)
    # 핀 몸체
    d.line([(cx, p+10), (cx, size-p-3)], fill=_hex(pin_col), width=sw+1)
    # 받침
    d.line([(cx-4, size-p-3), (cx+4, size-p-3)], fill=_hex(pin_col), width=sw)
    return img


def icon_minus(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """— 최소화"""
    img, d = _make(size)
    p = PADDING + 2
    d.line([(p, size//2), (size-p, size//2)], fill=_hex(color), width=_sw(STROKE+1))
    return img


def icon_close(color=COL_DANGER, size=ICON_SIZE, **kw) -> Image.Image:
    """✕ 닫기"""
    img, d = _make(size)
    p = PADDING + 2
    sw = _sw(STROKE+1)
    d.line([(p, p), (size-p, size-p)], fill=_hex(color), width=sw)
    d.line([(size-p, p), (p, size-p)], fill=_hex(color), width=sw)
    return img


def icon_drag(color="#475569", size=ICON_SIZE, **kw) -> Image.Image:
    """⋮⋮ 드래그 핸들"""
    img, d = _make(size)
    r = 2
    for cx, cy in [
        (size//2-4, size//2-5), (size//2+4, size//2-5),
        (size//2-4, size//2),   (size//2+4, size//2),
        (size//2-4, size//2+5), (size//2+4, size//2+5),
    ]:
        d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=_hex(color))
    return img


def icon_timer(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """⏱ 타이머"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    cx, cy = size//2, size//2+2
    r = size//2-p-1
    _circle(d, cx, cy, r, color, sw)
    d.line([(cx-3, p-1), (cx+3, p-1)], fill=_hex(color), width=sw)
    d.line([(cx, cy), (cx, cy-r+4)], fill=_hex(color), width=sw+1)
    d.line([(cx, cy), (cx+r-5, cy+2)], fill=_hex(color), width=sw)
    return img


def icon_dice(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """🎲 주사위"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    _rect(d, p, p, size-p, size-p, color, r=4)
    dot_r = 2
    for dx, dy in [(p+5, p+5), (size-p-5, size-p-5),
                   (size-p-5, p+5), (p+5, size-p-5), (size//2, size//2)]:
        d.ellipse([dx-dot_r, dy-dot_r, dx+dot_r, dy+dot_r], fill=_hex(color))
    return img


def icon_wheel(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """🎡 돌림판"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    cx, cy = size//2, size//2
    r = size//2-p
    _circle(d, cx, cy, r, color, sw)
    for a in [0, 60, 120, 180, 240, 300]:
        rad = math.radians(a)
        d.line([(cx, cy), (cx+r*math.cos(rad), cy+r*math.sin(rad))],
               fill=_hex(color), width=sw)
    _circle(d, cx, cy, 3, color, sw)
    return img


def icon_ladder(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """🪜 사다리"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    x0, x1 = p+2, size-p-2
    d.line([(x0, p), (x0, size-p)], fill=_hex(color), width=sw)
    d.line([(x1, p), (x1, size-p)], fill=_hex(color), width=sw)
    for y in [p+4, p+9, size-p-9, size-p-4]:
        d.line([(x0, y), (x1, y)], fill=_hex(color), width=sw)
    return img


def icon_widget(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """📅 미니 위젯/캘린더"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    _rect(d, p, p+3, size-p, size-p, color, r=3)
    d.line([(p, p+8), (size-p, p+8)], fill=_hex(color), width=sw)
    dot_r = 1
    for row in range(2):
        for col in range(3):
            dx, dy = p+4+col*6, p+13+row*6
            d.ellipse([dx-dot_r, dy-dot_r, dx+dot_r, dy+dot_r], fill=_hex(color))
    for bx in [size//2-4, size//2+4]:
        d.line([(bx, p), (bx, p+4)], fill=_hex(color), width=sw)
    return img


def icon_home(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """🏠 홈"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    cx = size//2
    d.polygon([(p, size//2), (cx, p+1), (size-p, size//2)],
              outline=_hex(color), width=sw)
    _rect(d, p+3, size//2-1, size-p-3, size-p, color, r=1)
    mx = cx-3
    d.rectangle([mx, size-p-6, mx+6, size-p], outline=_hex(color), width=sw)
    return img


def icon_drawing(color=COL_ORANGE, size=ICON_SIZE, **kw) -> Image.Image:
    """✏ 판서 (퀵바용)"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    d.line([(p, size-p), (p+4, size-p-6), (p+10, p+6), (size-p-4, p+2)],
           fill=_hex(color), width=sw+1)
    _circle(d, size-p-4, p+2, 3, color, sw)
    return img


def icon_pinball(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """⚾ 핀볼"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    cx, cy = size//2, size//2+2
    _circle(d, cx, cy, size//2-p-1, color, sw)
    d.arc([cx-4, cy-6, cx+4, cy+2], start=30, end=150, fill=_hex(color), width=sw)
    d.arc([cx-4, cy-2, cx+4, cy+6], start=210, end=330, fill=_hex(color), width=sw)
    return img


def icon_zoom_in(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """🔍+ 확대"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    cx, cy, r = size//2-2, size//2-2, 7
    _circle(d, cx, cy, r, color, sw)
    d.line([(cx, cy-4), (cx, cy+4)], fill=_hex(color), width=sw)
    d.line([(cx-4, cy), (cx+4, cy)], fill=_hex(color), width=sw)
    d.line([(cx+r-1, cy+r-1), (size-p, size-p)], fill=_hex(color), width=sw+1)
    return img


def icon_zoom_out(color=COL_MAIN, size=ICON_SIZE, **kw) -> Image.Image:
    """🔍- 축소"""
    img, d = _make(size)
    p = PADDING
    sw = _sw()
    cx, cy, r = size//2-2, size//2-2, 7
    _circle(d, cx, cy, r, color, sw)
    d.line([(cx-4, cy), (cx+4, cy)], fill=_hex(color), width=sw)
    d.line([(cx+r-1, cy+r-1), (size-p, size-p)], fill=_hex(color), width=sw+1)
    return img


# ══════════════════════════════════════════════════════════════════════════════
# CTkImage 캐시
# ══════════════════════════════════════════════════════════════════════════════
_cache: dict = {}

_FN_MAP = {
    "pen": icon_pen, "highlighter": icon_highlighter,
    "arrow": icon_arrow, "rect": icon_rectangle,
    "text": icon_text, "eraser": icon_eraser,
    "emoji_stamp": icon_emoji_stamp,
    "undo": icon_undo, "trash": icon_trash,
    "camera": icon_camera, "pin": icon_pin,
    "minus": icon_minus, "close": icon_close,
    "drag": icon_drag, "timer": icon_timer,
    "dice": icon_dice, "wheel": icon_wheel,
    "ladder": icon_ladder, "widget": icon_widget,
    "home": icon_home, "drawing": icon_drawing,
    "pinball": icon_pinball, "zoom_in": icon_zoom_in,
    "zoom_out": icon_zoom_out,
}


def get_icon(name: str, color: str = COL_MAIN, size: int = ICON_SIZE, **kw):
    cache_key = (name, color, size, tuple(sorted(kw.items())))
    if cache_key not in _cache:
        fn = _FN_MAP.get(name)
        if fn is None:
            img = Image.new("RGBA", (size, size), BG)
        else:
            try:
                img = fn(color=color, size=size, **kw)
            except TypeError:
                img = fn(size=size)
        import customtkinter as ctk
        _cache[cache_key] = ctk.CTkImage(img, img, size=(size, size))
    return _cache[cache_key]

