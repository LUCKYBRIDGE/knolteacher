"""
놀티쳐 데스크 - 아이콘 렌더러
커스텀 Canvas 기반 벡터 아이콘 생성기
(참고 이미지처럼 깔끔한 아웃라인 스타일, PIL PhotoImage 반환)
"""

import math
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

# ── 공통 설정 ────────────────────────────────────────────────────────────────
ICON_SIZE = 28          # 기본 아이콘 크기 (px)
STROKE = 2.2            # 선 굵기
PADDING = 5             # 내부 여백
BG = (0, 0, 0, 0)      # 투명 배경

# 팔레트
COL_MAIN   = "#e2e8f0"   # 기본 아이콘 색 (밝은 회백)
COL_ACTIVE = "#38bdf8"   # 선택/활성 상태 (하늘색)
COL_DANGER = "#f87171"   # 위험 동작 (빨강)
COL_GREEN  = "#4ade80"   # 안전/저장 동작 (초록)
COL_ORANGE = "#fb923c"   # 경고/강조 (주황)


def _hex(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)


def _make_canvas(size=ICON_SIZE) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (size, size), BG)
    draw = ImageDraw.Draw(img)
    return img, draw


def _line(draw, pts, color, w=STROKE):
    """점들을 이어 선 그리기"""
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=_hex(color), width=max(1, int(w)))


def _circle(draw, cx, cy, r, color, w=STROKE):
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        outline=_hex(color), width=max(1, int(w))
    )


def _rect_outline(draw, x0, y0, x1, y1, color, w=STROKE, radius=2):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, outline=_hex(color), width=max(1, int(w)))


def to_ctk_image(img: Image.Image, size=ICON_SIZE):
    """PIL Image → CTkImage"""
    import customtkinter as ctk
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


# ══════════════════════════════════════════════════════════════════════════════
# 아이콘 드로잉 함수들
# ══════════════════════════════════════════════════════════════════════════════

def icon_pen(color=COL_MAIN, size=ICON_SIZE) -> Image.Image:
    """✏️ 펜/연필"""
    img, draw = _make_canvas(size)
    p = PADDING
    # 연필 몸통 (대각선 사각형)
    draw.polygon([
        (p+2, size-p-2), (p, size-p-6),
        (size-p-4, p+2), (size-p, p+6)
    ], outline=_hex(color), width=max(1, int(STROKE)))
    # 연필 팁
    draw.polygon([
        (p+2, size-p-2), (p, size-p-6),
        (p+5, size-p-1)
    ], fill=_hex(color))
    return img


def icon_highlighter(color=COL_ORANGE, size=ICON_SIZE) -> Image.Image:
    """🖍️ 형광펜"""
    img, draw = _make_canvas(size)
    p = PADDING
    sw = max(1, int(STROKE))
    # 넓적한 마커 몸통
    draw.polygon([
        (p, size-p-3), (p+2, size-p),
        (size-p-2, p+3), (size-p-5, p)
    ], outline=_hex(color), width=sw)
    # 두꺼운 끝부분
    draw.line([(p, size-p-3), (p+2, size-p)], fill=_hex(color), width=sw+1)
    return img


def icon_arrow(color=COL_MAIN, size=ICON_SIZE) -> Image.Image:
    """↗ 화살표"""
    img, draw = _make_canvas(size)
    p = PADDING + 1
    sw = max(1, int(STROKE))
    # 선
    draw.line([(p, size-p), (size-p, p)], fill=_hex(color), width=sw)
    # 화살표 머리
    draw.line([(size-p, p), (size-p-5, p)], fill=_hex(color), width=sw)
    draw.line([(size-p, p), (size-p, p+5)], fill=_hex(color), width=sw)
    return img


def icon_rectangle(color=COL_MAIN, size=ICON_SIZE) -> Image.Image:
    """▢ 사각형"""
    img, draw = _make_canvas(size)
    p = PADDING + 1
    _rect_outline(draw, p, p+2, size-p, size-p-2, color, radius=3)
    return img


def icon_text(color=COL_MAIN, size=ICON_SIZE) -> Image.Image:
    """T 텍스트"""
    img, draw = _make_canvas(size)
    p = PADDING
    sw = max(1, int(STROKE))
    # 가로 상단 선
    draw.line([(p, p+2), (size-p, p+2)], fill=_hex(color), width=sw)
    # 세로 중앙 선
    draw.line([(size//2, p+2), (size//2, size-p-2)], fill=_hex(color), width=sw)
    # 하단 세리프
    draw.line([(size//2-4, size-p-2), (size//2+4, size-p-2)], fill=_hex(color), width=sw)
    return img


def icon_eraser(color=COL_MAIN, size=ICON_SIZE) -> Image.Image:
    """🧹 지우개"""
    img, draw = _make_canvas(size)
    p = PADDING
    sw = max(1, int(STROKE))
    # 지우개 몸통 (비스듬한 사각형)
    draw.polygon([
        (p, size-p-4), (p+4, size-p),
        (size-p-2, p+4), (size-p-6, p)
    ], outline=_hex(color), width=sw)
    # 지운 흔적 바닥선
    draw.line([(p+4, size-p), (size-p+2, size-p)], fill=_hex(color), width=sw)
    return img


def icon_undo(color=COL_MAIN, size=ICON_SIZE) -> Image.Image:
    """↩ 실행취소"""
    img, draw = _make_canvas(size)
    p = PADDING + 1
    sw = max(1, int(STROKE))
    cx, cy = size//2, size//2
    r = size//2 - p
    # 반원 호
    draw.arc([cx-r, cy-r+2, cx+r, cy+r+2], start=200, end=360, fill=_hex(color), width=sw)
    draw.arc([cx-r, cy-r+2, cx+r, cy+r+2], start=0, end=30, fill=_hex(color), width=sw)
    # 화살표 머리 (왼쪽 방향)
    ax = cx - r + 2
    ay = cy + 2
    draw.line([(ax, ay-4), (ax, ay+2)], fill=_hex(color), width=sw)
    draw.line([(ax, ay-4), (ax+5, ay-4)], fill=_hex(color), width=sw)
    return img


def icon_trash(color=COL_DANGER, size=ICON_SIZE) -> Image.Image:
    """🗑️ 삭제"""
    img, draw = _make_canvas(size)
    p = PADDING
    sw = max(1, int(STROKE))
    bx0, bx1 = p+2, size-p-2
    # 본체
    _rect_outline(draw, bx0, p+5, bx1, size-p, color, radius=2)
    # 뚜껑
    draw.line([(p, p+5), (size-p, p+5)], fill=_hex(color), width=sw)
    draw.line([(size//2-3, p+2), (size//2+3, p+2)], fill=_hex(color), width=sw)
    draw.line([(size//2-3, p+2), (bx0+1, p+5)], fill=_hex(color), width=sw)
    draw.line([(size//2+3, p+2), (bx1-1, p+5)], fill=_hex(color), width=sw)
    # 내부 세로 줄
    m = size//2
    draw.line([(m, p+7), (m, size-p-2)], fill=_hex(color), width=sw)
    draw.line([(m-4, p+7), (m-4, size-p-2)], fill=_hex(color), width=sw)
    draw.line([(m+4, p+7), (m+4, size-p-2)], fill=_hex(color), width=sw)
    return img


def icon_camera(color=COL_GREEN, size=ICON_SIZE) -> Image.Image:
    """📸 캡처/저장"""
    img, draw = _make_canvas(size)
    p = PADDING
    sw = max(1, int(STROKE))
    # 카메라 몸통
    _rect_outline(draw, p, p+4, size-p, size-p, color, radius=3)
    # 뷰파인더 (상단 노치)
    draw.polygon([
        (size//2-4, p), (size//2+4, p),
        (size//2+5, p+4), (size//2-5, p+4)
    ], outline=_hex(color), width=sw)
    # 렌즈
    _circle(draw, size//2, size//2+3, 5, color, sw)
    _circle(draw, size//2, size//2+3, 2, color, sw)
    return img


def icon_pin(color=COL_MAIN, pinned=True, size=ICON_SIZE) -> Image.Image:
    """📌 핀 고정"""
    img, draw = _make_canvas(size)
    p = PADDING
    sw = max(1, int(STROKE))
    cx = size//2
    # 핀 머리
    _circle(draw, cx, p+4, 4, COL_ACTIVE if pinned else color, sw)
    # 핀 몸체
    draw.line([(cx, p+8), (cx, size-p-3)], fill=_hex(COL_ACTIVE if pinned else color), width=sw)
    # 핀 받침
    draw.line([(cx-4, size-p-3), (cx+4, size-p-3)], fill=_hex(COL_ACTIVE if pinned else color), width=sw)
    return img


def icon_minus(color=COL_MAIN, size=ICON_SIZE) -> Image.Image:
    """— 최소화"""
    img, draw = _make_canvas(size)
    p = PADDING + 2
    draw.line([(p, size//2), (size-p, size//2)], fill=_hex(color), width=max(2, int(STROKE)))
    return img


def icon_close(color=COL_DANGER, size=ICON_SIZE) -> Image.Image:
    """✕ 닫기"""
    img, draw = _make_canvas(size)
    p = PADDING + 2
    sw = max(2, int(STROKE))
    draw.line([(p, p), (size-p, size-p)], fill=_hex(color), width=sw)
    draw.line([(size-p, p), (p, size-p)], fill=_hex(color), width=sw)
    return img


def icon_drag(color="#475569", size=ICON_SIZE) -> Image.Image:
    """⋮⋮ 드래그 핸들 (6점 그리드)"""
    img, draw = _make_canvas(size)
    r = 2
    positions = [
        (size//2-4, size//2-5), (size//2+4, size//2-5),
        (size//2-4, size//2),   (size//2+4, size//2),
        (size//2-4, size//2+5), (size//2+4, size//2+5),
    ]
    for cx, cy in positions:
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=_hex(color))
    return img


def icon_timer(color=COL_MAIN, size=ICON_SIZE) -> Image.Image:
    """⏱ 타이머/스톱워치"""
    img, draw = _make_canvas(size)
    p = PADDING
    sw = max(1, int(STROKE))
    cx, cy = size//2, size//2 + 2
    r = size//2 - p - 1
    # 시계 본체
    _circle(draw, cx, cy, r, color, sw)
    # 12시 방향 버튼
    draw.line([(cx-3, p-1), (cx+3, p-1)], fill=_hex(color), width=sw)
    # 시침 (12시 방향)
    draw.line([(cx, cy), (cx, cy - r + 4)], fill=_hex(color), width=sw)
    # 분침
    draw.line([(cx, cy), (cx + r - 5, cy + 3)], fill=_hex(color), width=sw)
    return img


def icon_dice(color=COL_MAIN, size=ICON_SIZE) -> Image.Image:
    """🎲 뽑기/주사위"""
    img, draw = _make_canvas(size)
    p = PADDING
    sw = max(1, int(STROKE))
    _rect_outline(draw, p, p, size-p, size-p, color, radius=4)
    dot_r = 2
    dots = [
        (p+5, p+5), (size-p-5, size-p-5),
        (size-p-5, p+5), (p+5, size-p-5),
        (size//2, size//2)
    ]
    for dx, dy in dots:
        draw.ellipse([dx-dot_r, dy-dot_r, dx+dot_r, dy+dot_r], fill=_hex(color))
    return img


def icon_wheel(color=COL_MAIN, size=ICON_SIZE) -> Image.Image:
    """🎡 돌림판"""
    img, draw = _make_canvas(size)
    p = PADDING
    sw = max(1, int(STROKE))
    cx, cy = size//2, size//2
    r = size//2 - p
    _circle(draw, cx, cy, r, color, sw)
    for angle_deg in [0, 60, 120, 180, 240, 300]:
        a = math.radians(angle_deg)
        draw.line([(cx, cy), (cx + r * math.cos(a), cy + r * math.sin(a))],
                  fill=_hex(color), width=sw)
    _circle(draw, cx, cy, 3, color, sw)
    return img


def icon_ladder(color=COL_MAIN, size=ICON_SIZE) -> Image.Image:
    """🪜 사다리"""
    img, draw = _make_canvas(size)
    p = PADDING
    sw = max(1, int(STROKE))
    x0, x1 = p+2, size-p-2
    # 세로 기둥 2개
    draw.line([(x0, p), (x0, size-p)], fill=_hex(color), width=sw)
    draw.line([(x1, p), (x1, size-p)], fill=_hex(color), width=sw)
    # 가로 발판 4개
    for y in [p+4, p+9, size-p-9, size-p-4]:
        draw.line([(x0, y), (x1, y)], fill=_hex(color), width=sw)
    return img


def icon_widget(color=COL_MAIN, size=ICON_SIZE) -> Image.Image:
    """📌 위젯 - 미니 캘린더"""
    img, draw = _make_canvas(size)
    p = PADDING
    sw = max(1, int(STROKE))
    _rect_outline(draw, p, p+3, size-p, size-p, color, radius=3)
    draw.line([(p, p+8), (size-p, p+8)], fill=_hex(color), width=sw)
    # 날짜 격자 점
    dot_r = 1
    for row in range(2):
        for col in range(3):
            dx = p + 4 + col * 6
            dy = p + 13 + row * 6
            draw.ellipse([dx-dot_r, dy-dot_r, dx+dot_r, dy+dot_r], fill=_hex(color))
    # 상단 탭
    for bx in [size//2-4, size//2+4]:
        draw.line([(bx, p), (bx, p+4)], fill=_hex(color), width=sw)
    return img


def icon_home(color=COL_MAIN, size=ICON_SIZE) -> Image.Image:
    """🏠 메인/홈"""
    img, draw = _make_canvas(size)
    p = PADDING
    sw = max(1, int(STROKE))
    cx = size//2
    # 지붕
    draw.polygon([(p, size//2), (cx, p+1), (size-p, size//2)],
                 outline=_hex(color), width=sw)
    # 몸체
    _rect_outline(draw, p+3, size//2-1, size-p-3, size-p, color, radius=1)
    # 문
    mx = cx - 3
    draw.rectangle([mx, size-p-6, mx+6, size-p], outline=_hex(color), width=sw)
    return img


def icon_drawing(color=COL_ORANGE, size=ICON_SIZE) -> Image.Image:
    """✏ 판서 (도구들 모음)"""
    img, draw = _make_canvas(size)
    p = PADDING
    sw = max(1, int(STROKE))
    # 굵은 선으로 판서 궤적 표현
    draw.line([(p, size-p), (p+4, size-p-6), (p+10, p+6), (size-p-4, p+2)],
              fill=_hex(color), width=sw+1)
    # 펜 팁
    _circle(draw, size-p-4, p+2, 3, color, sw)
    return img


def icon_pinball(color=COL_MAIN, size=ICON_SIZE) -> Image.Image:
    """⚾ 핀볼"""
    img, draw = _make_canvas(size)
    p = PADDING
    sw = max(1, int(STROKE))
    cx, cy = size//2, size//2 + 2
    # 공
    _circle(draw, cx, cy, size//2 - p - 1, color, sw)
    # 실밥 곡선 (2개)
    draw.arc([cx-4, cy-6, cx+4, cy+2], start=30, end=150, fill=_hex(color), width=sw)
    draw.arc([cx-4, cy-2, cx+4, cy+6], start=210, end=330, fill=_hex(color), width=sw)
    return img


# ══════════════════════════════════════════════════════════════════════════════
# CTkImage 캐시 (한 번 생성 후 재사용)
# ══════════════════════════════════════════════════════════════════════════════
_cache: dict = {}

def get_icon(name: str, color: str = COL_MAIN, size: int = ICON_SIZE, **kw):
    """
    이름으로 아이콘 CTkImage를 가져옵니다 (캐시 지원).
    name: pen, highlighter, arrow, rect, text, eraser, undo, trash, camera,
          pin, minus, close, drag, timer, dice, wheel, ladder, widget, home,
          drawing, pinball
    """
    cache_key = (name, color, size, tuple(kw.items()))
    if cache_key not in _cache:
        fn_map = {
            "pen": icon_pen, "highlighter": icon_highlighter,
            "arrow": icon_arrow, "rect": icon_rectangle,
            "text": icon_text, "eraser": icon_eraser,
            "undo": icon_undo, "trash": icon_trash,
            "camera": icon_camera, "pin": icon_pin,
            "minus": icon_minus, "close": icon_close,
            "drag": icon_drag, "timer": icon_timer,
            "dice": icon_dice, "wheel": icon_wheel,
            "ladder": icon_ladder, "widget": icon_widget,
            "home": icon_home, "drawing": icon_drawing,
            "pinball": icon_pinball,
        }
        fn = fn_map.get(name)
        if fn is None:
            # 알 수 없는 아이콘 → 빈 이미지
            img = Image.new("RGBA", (size, size), BG)
        else:
            try:
                img = fn(color=color, size=size, **kw)
            except TypeError:
                img = fn(size=size)
        _cache[cache_key] = to_ctk_image(img, size)
    return _cache[cache_key]
