"""
놀티쳐 (KnolTeacher) - 프리미엄 슈퍼샘플링 벡터 아이콘 렌더러
4배 슈퍼샘플링(4x Supersampling) 안티앨리어싱을 통해
각 도구의 기능과 형태를 100% 확실하게 나타내는 고화질 맞춤형 아이콘 세트
"""

import math
from PIL import Image, ImageDraw
import customtkinter as ctk

# 기본 색상 팔레트
COL_MAIN   = "#e2e8f0"  # 연회색 기본
COL_ACTIVE = "#38bdf8"  # 활성 스카이블루
COL_DANGER = "#f87171"  # 위험 레드
COL_GREEN  = "#4ade80"  # 그린
COL_ORANGE = "#fb923c"  # 오렌지
COL_YELLOW = "#fde047"  # 옐로우
COL_PURPLE = "#c084fc"  # 보라

# 4배 슈퍼샘플링 배율
SS = 4

def _hex(h: str, alpha=255):
    h = h.lstrip("#")
    if len(h) == 6:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)
    elif len(h) == 8:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4, 6))
    return (255, 255, 255, alpha)

def _make_canvas(size: int):
    """4배 해상도의 캔버스와 드로우 객체 생성"""
    canvas_sz = size * SS
    img = Image.new("RGBA", (canvas_sz, canvas_sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    return img, d, canvas_sz

def _finish_canvas(img: Image.Image, size: int) -> Image.Image:
    """LANCZOS 필터로 리사이징하여 고품질 안티앨리어싱 적용"""
    return img.resize((size, size), Image.LANCZOS)

# ══════════════════════════════════════════════════════════════════════════════
# 핵심 도구별 전용 고화질 아이콘 렌더러
# ══════════════════════════════════════════════════════════════════════════════

def icon_pen(color=COL_ORANGE, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 볼펜: 뾰족한 메탈 팁, 원통형 바디, 노크 버튼, 클립"""
    img, d, S = _make_canvas(size)
    # 45도 기울어진 볼펜
    # 1. 볼펜 촉 (금속 팁)
    d.polygon([(S*0.16, S*0.76), (S*0.24, S*0.84), (S*0.08, S*0.92)], fill=_hex("#94a3b8"))
    # 볼펜 심 끝 (까만 볼)
    d.ellipse([S*0.06, S*0.90, S*0.11, S*0.95], fill=_hex("#0f172a"))
    # 2. 볼펜 그립부
    d.polygon([(S*0.16, S*0.76), (S*0.24, S*0.84), (S*0.34, S*0.74), (S*0.26, S*0.66)], fill=_hex("#475569"))
    # 3. 볼펜 몸통 (메인 컬러)
    d.polygon([(S*0.26, S*0.66), (S*0.34, S*0.74), (S*0.76, S*0.32), (S*0.68, S*0.24)], fill=_hex(color))
    # 4. 볼펜 몸통 하이라이트 (입체감)
    d.line([(S*0.30, S*0.68), (S*0.70, S*0.28)], fill=_hex("#ffffff", 140), width=int(S*0.04))
    # 5. 상단 링 & 노크 푸시 버튼
    d.polygon([(S*0.68, S*0.24), (S*0.76, S*0.32), (S*0.82, S*0.26), (S*0.74, S*0.18)], fill=_hex("#cbd5e1"))
    d.polygon([(S*0.76, S*0.16), (S*0.84, S*0.24), (S*0.90, S*0.18), (S*0.82, S*0.10)], fill=_hex("#94a3b8"))
    # 6. 포켓 클립 (몸통 옆에 붙은 클립)
    d.line([(S*0.70, S*0.22), (S*0.56, S*0.36), (S*0.58, S*0.40)], fill=_hex("#cbd5e1"), width=int(S*0.05))
    return _finish_canvas(img, size)

def icon_highlighter(color=COL_YELLOW, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 형광펜: 넓적한 사각 바디, 사선 치즐 팁, 그어진 형광 밑줄"""
    img, d, S = _make_canvas(size)
    # 1. 사선 치즐 팁 (Chisel Tip 형광 펜촉)
    tip_pts = [(S*0.22, S*0.68), (S*0.32, S*0.78), (S*0.18, S*0.86), (S*0.12, S*0.80)]
    d.polygon(tip_pts, fill=_hex("#facc15"))
    d.polygon([(S*0.12, S*0.80), (S*0.18, S*0.86), (S*0.14, S*0.90), (S*0.09, S*0.84)], fill=_hex("#ca8a04"))
    # 2. 펜 목 부분 (검은 밴드)
    d.polygon([(S*0.22, S*0.68), (S*0.32, S*0.78), (S*0.38, S*0.72), (S*0.28, S*0.62)], fill=_hex("#1e293b"))
    # 3. 굵은 형광펜 몸통
    body_pts = [(S*0.28, S*0.62), (S*0.38, S*0.72), (S*0.82, S*0.28), (S*0.72, S*0.18)]
    d.polygon(body_pts, fill=_hex(color))
    # 4. 몸통 로고/패턴
    d.line([(S*0.38, S*0.58), (S*0.72, S*0.24)], fill=_hex("#ffffff", 160), width=int(S*0.06))
    # 5. 뒤쪽 캡/뚜껑 마개
    d.polygon([(S*0.72, S*0.18), (S*0.82, S*0.28), (S*0.89, S*0.21), (S*0.79, S*0.11)], fill=_hex("#0f172a"))
    # 6. 바닥에 그어진 형광 획 (강조 라인)
    d.line([(S*0.08, S*0.88), (S*0.50, S*0.88)], fill=_hex(color, 180), width=int(S*0.08))
    return _finish_canvas(img, size)

def icon_eraser(color="#f43f5e", size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 지우개: 사선으로 깎인 화이트 고무 + 파란 띠지 껍질"""
    img, d, S = _make_canvas(size)
    # 지우개 앞부분 (지우는 흰색 고무)
    d.polygon([(S*0.12, S*0.52), (S*0.42, S*0.22), (S*0.56, S*0.36), (S*0.26, S*0.66)], fill=_hex("#f8fafc"))
    # 비스듬히 깎인 앞면
    d.polygon([(S*0.12, S*0.52), (S*0.26, S*0.66), (S*0.20, S*0.74), (S*0.08, S*0.60)], fill=_hex("#e2e8f0"))
    # 지우개 뒷부분 종이 슬리브 (파란색 껍질)
    d.polygon([(S*0.34, S*0.30), (S*0.70, S*0.12), (S*0.88, S*0.30), (S*0.48, S*0.44)], fill=_hex("#0284c7"))
    d.polygon([(S*0.48, S*0.44), (S*0.88, S*0.30), (S*0.82, S*0.48), (S*0.42, S*0.62)], fill=_hex("#0369a1"))
    # 지우개 가루 흔적
    d.ellipse([S*0.10, S*0.80, S*0.14, S*0.84], fill=_hex("#94a3b8"))
    d.ellipse([S*0.20, S*0.84, S*0.25, S*0.89], fill=_hex("#94a3b8"))
    d.ellipse([S*0.28, S*0.78, S*0.32, S*0.82], fill=_hex("#94a3b8"))
    return _finish_canvas(img, size)

def icon_text(color=COL_MAIN, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 텍스트 도구: 세련된 대문자 T + 점선 글상자 프레임"""
    img, d, S = _make_canvas(size)
    # 배경 점선 박스
    d.rounded_rectangle([S*0.10, S*0.10, S*0.90, S*0.90], radius=int(S*0.1), outline=_hex("#38bdf8", 120), width=int(S*0.04))
    # 대문자 T
    # 상단 가로 바
    d.rectangle([S*0.22, S*0.25, S*0.78, S*0.37], fill=_hex(color))
    # 세로 기둥
    d.rectangle([S*0.44, S*0.37, S*0.56, S*0.75], fill=_hex(color))
    # 하단 세리프 받침
    d.rectangle([S*0.36, S*0.72, S*0.64, S*0.78], fill=_hex(color))
    return _finish_canvas(img, size)

def icon_arrow(color=COL_MAIN, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 지시 화살표: 굵고 역동적인 45도 포인터 화살표"""
    img, d, S = _make_canvas(size)
    d.line([(S*0.18, S*0.82), (S*0.72, S*0.28)], fill=_hex(color), width=int(S*0.10))
    # 화살촉 (쐐기형)
    pts = [(S*0.84, S*0.16), (S*0.52, S*0.20), (S*0.80, S*0.48)]
    d.polygon(pts, fill=_hex(color))
    return _finish_canvas(img, size)

def icon_rect(color=COL_MAIN, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 도형: 부드러운 라운드 사각형 프레임"""
    img, d, S = _make_canvas(size)
    d.rounded_rectangle([S*0.14, S*0.18, S*0.86, S*0.82], radius=int(S*0.12), outline=_hex(color), width=int(S*0.09))
    return _finish_canvas(img, size)

def icon_emoji_stamp(color=COL_YELLOW, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 칭찬 스탬프: 방긋 웃는 노란 스마일 얼굴 + 반짝이 별"""
    img, d, S = _make_canvas(size)
    # 얼굴 원
    cx, cy, r = S*0.46, S*0.52, S*0.38
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=_hex("#fde047"), outline=_hex("#ca8a04"), width=int(S*0.04))
    # 눈 (귀여운 눈동자)
    er = S*0.05
    d.ellipse([cx-S*0.14-er, cy-S*0.08-er, cx-S*0.14+er, cy-S*0.08+er], fill=_hex("#1e293b"))
    d.ellipse([cx+S*0.14-er, cy-S*0.08-er, cx+S*0.14+er, cy-S*0.08+er], fill=_hex("#1e293b"))
    # 활짝 웃는 입 (호)
    d.arc([cx-S*0.18, cy-S*0.06, cx+S*0.18, cy+S*0.22], start=20, end=160, fill=_hex("#1e293b"), width=int(S*0.06))
    # 볼터치 핑크
    d.ellipse([cx-S*0.24, cy+S*0.02, cx-S*0.12, cy+S*0.10], fill=_hex("#f43f5e", 160))
    d.ellipse([cx+S*0.12, cy+S*0.02, cx+S*0.24, cy+S*0.10], fill=_hex("#f43f5e", 160))
    # 우상단 칭찬 별 (Sparkle Star)
    sx, sy = S*0.84, S*0.20
    d.polygon([(sx, sy-S*0.12), (sx+S*0.04, sy-S*0.03), (sx+S*0.14, sy), (sx+S*0.04, sy+S*0.03),
               (sx, sy+S*0.12), (sx-S*0.04, sy+S*0.03), (sx-S*0.14, sy), (sx-S*0.04, sy-S*0.03)], fill=_hex("#fbbf24"))
    return _finish_canvas(img, size)

def icon_mouse(color=COL_MAIN, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 마우스: 좌우 버튼 분할선 + 중앙 스크롤 휠"""
    img, d, S = _make_canvas(size)
    # 마우스 외형 (유선형 캡슐)
    x0, y0, x1, y1 = S*0.22, S*0.12, S*0.78, S*0.88
    d.rounded_rectangle([x0, y0, x1, y1], radius=int(S*0.26), fill=_hex("#1e293b"), outline=_hex(color), width=int(S*0.07))
    # 가로 구분선 (버튼과 손바닥 받침 분리)
    d.line([(x0+S*0.04, S*0.44), (x1-S*0.04, S*0.44)], fill=_hex(color), width=int(S*0.05))
    # 상단 세로 분할선 (좌클릭 / 우클릭 분리)
    d.line([(S*0.50, y0+S*0.02), (S*0.50, S*0.44)], fill=_hex(color), width=int(S*0.05))
    # 중앙 스크롤 휠 (도톰한 빨간/파란 휠)
    d.rounded_rectangle([S*0.44, S*0.22, S*0.56, S*0.38], radius=int(S*0.04), fill=_hex("#38bdf8"))
    return _finish_canvas(img, size)

def icon_camera(color=COL_ACTIVE, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 실물화상기/카메라: 카메라 바디 + 대형 렌즈 링 + 플래시"""
    img, d, S = _make_canvas(size)
    # 본체
    d.rounded_rectangle([S*0.12, S*0.26, S*0.88, S*0.84], radius=int(S*0.12), fill=_hex("#1e293b"), outline=_hex(color), width=int(S*0.07))
    # 뷰파인더 솟아오른 펜타프리즘
    d.polygon([(S*0.34, S*0.26), (S*0.42, S*0.16), (S*0.58, S*0.16), (S*0.66, S*0.26)], fill=_hex("#334155"))
    # 중앙 렌즈 외경
    cx, cy, r = S*0.50, S*0.55, S*0.20
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=_hex("#0f172a"), outline=_hex(color), width=int(S*0.06))
    # 렌즈 유리 반사광 (푸른 빛 하이라이트)
    d.arc([cx-r+S*0.04, cy-r+S*0.04, cx+r-S*0.04, cy+r-S*0.04], start=200, end=340, fill=_hex("#38bdf8"), width=int(S*0.05))
    # 플래시 / 센서 도트
    d.ellipse([S*0.74, S*0.34, S*0.82, S*0.42], fill=_hex("#fde047"))
    return _finish_canvas(img, size)

def icon_timer(color=COL_MAIN, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 교실 타이머/스톱워치: 상단 버튼 + 시계 다이얼 + 초침"""
    img, d, S = _make_canvas(size)
    cx, cy, r = S*0.50, S*0.56, S*0.36
    # 스톱워치 상단 버튼
    d.rectangle([cx-S*0.08, S*0.08, cx+S*0.08, S*0.18], fill=_hex("#94a3b8"))
    d.rectangle([cx-S*0.14, S*0.05, cx+S*0.14, S*0.09], fill=_hex("#cbd5e1"))
    # 시계 원형 몸통
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=_hex("#1e293b"), outline=_hex(color), width=int(S*0.07))
    # 12시, 3시, 6시, 9시 눈금
    d.line([(cx, cy-r+S*0.03), (cx, cy-r+S*0.09)], fill=_hex(color), width=int(S*0.05))
    d.line([(cx, cy+r-S*0.09), (cx, cy+r-S*0.03)], fill=_hex(color), width=int(S*0.05))
    d.line([(cx-r+S*0.03, cy), (cx-r+S*0.09, cy)], fill=_hex(color), width=int(S*0.05))
    d.line([(cx+r-S*0.09, cy), (cx+r-S*0.03, cy)], fill=_hex(color), width=int(S*0.05))
    # 빨간색 타이머 초침 바늘 (10시 10분 방향)
    d.line([(cx, cy), (cx+S*0.16, cy-S*0.16)], fill=_hex("#ef4444"), width=int(S*0.06))
    d.line([(cx, cy), (cx-S*0.18, cy-S*0.06)], fill=_hex("#38bdf8"), width=int(S*0.06))
    d.ellipse([cx-S*0.05, cy-S*0.05, cx+S*0.05, cy+S*0.05], fill=_hex("#ffffff"))
    return _finish_canvas(img, size)

def icon_dice(color=COL_PURPLE, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 발표자 뽑기 주사위: 3D 입체 투영 큐브 + 점들"""
    img, d, S = _make_canvas(size)
    # 3D 등각투영 큐브 점들
    c_top = (S*0.50, S*0.12)
    c_mid = (S*0.50, S*0.52)
    p_tl  = (S*0.16, S*0.30)
    p_tr  = (S*0.84, S*0.30)
    p_bl  = (S*0.16, S*0.72)
    p_br  = (S*0.84, S*0.72)
    c_bot = (S*0.50, S*0.92)

    # 상단 면 (밝은 보라)
    d.polygon([c_top, p_tr, c_mid, p_tl], fill=_hex("#c084fc"), outline=_hex("#ffffff"), width=int(S*0.03))
    # 좌측 면 (중간 보라)
    d.polygon([p_tl, c_mid, c_bot, p_bl], fill=_hex("#9333ea"), outline=_hex("#ffffff"), width=int(S*0.03))
    # 우측 면 (진한 보라)
    d.polygon([c_mid, p_tr, p_br, c_bot], fill=_hex("#7e22ce"), outline=_hex("#ffffff"), width=int(S*0.03))

    # 주사위 점 (상단: 1점)
    d.ellipse([S*0.46, S*0.28, S*0.54, S*0.36], fill=_hex("#ffffff"))
    # 좌측: 2점
    d.ellipse([S*0.26, S*0.46, S*0.34, S*0.54], fill=_hex("#ffffff"))
    d.ellipse([S*0.36, S*0.66, S*0.44, S*0.74], fill=_hex("#ffffff"))
    # 우측: 3점
    d.ellipse([S*0.60, S*0.46, S*0.68, S*0.54], fill=_hex("#ffffff"))
    d.ellipse([S*0.68, S*0.58, S*0.76, S*0.66], fill=_hex("#ffffff"))
    d.ellipse([S*0.54, S*0.70, S*0.62, S*0.78], fill=_hex("#ffffff"))
    return _finish_canvas(img, size)

def icon_wheel(color=COL_MAIN, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 돌림판: 6색 무지개 룰렛 판 + 상단 포인터 화살표"""
    img, d, S = _make_canvas(size)
    cx, cy, r = S*0.50, S*0.54, S*0.38
    # 무지개 섹션들
    palette = ["#ef4444", "#f97316", "#facc15", "#22c55e", "#0ea5e9", "#a855f7"]
    for i, col in enumerate(palette):
        st = i * 60
        d.pieslice([cx-r, cy-r, cx+r, cy+r], start=st, end=st+60, fill=_hex(col), outline=_hex("#0f172a"), width=int(S*0.02))
    # 중앙 금속 캡
    d.ellipse([cx-S*0.10, cy-S*0.10, cx+S*0.10, cy+S*0.10], fill=_hex("#ffffff"), outline=_hex("#0f172a"), width=int(S*0.03))
    # 12시 방향 상단 포인터 바늘 (황금색 삼각 핀)
    d.polygon([(cx, S*0.28), (cx-S*0.09, S*0.10), (cx+S*0.09, S*0.10)], fill=_hex("#fbbf24"), outline=_hex("#78350f"), width=int(S*0.03))
    return _finish_canvas(img, size)

def icon_magnifier(color=COL_ACTIVE, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 돋보기 (화면 확대): 볼록 렌즈 유리 + 튼튼한 손잡이"""
    img, d, S = _make_canvas(size)
    # 손잡이 (오른쪽 아래 45도)
    d.line([(S*0.62, S*0.62), (S*0.88, S*0.88)], fill=_hex("#94a3b8"), width=int(S*0.12))
    d.line([(S*0.72, S*0.72), (S*0.90, S*0.90)], fill=_hex("#475569"), width=int(S*0.12))
    # 돋보기 둥근 림(테두리)
    cx, cy, r = S*0.42, S*0.42, S*0.28
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=_hex("#0f172a"), outline=_hex(color), width=int(S*0.08))
    # 렌즈 빛 반사 하이라이트
    d.arc([cx-r+S*0.06, cy-r+S*0.06, cx+r-S*0.06, cy+r-S*0.06], start=180, end=290, fill=_hex("#ffffff", 200), width=int(S*0.05))
    return _finish_canvas(img, size)

def icon_record(color=COL_DANGER, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 화면 녹화: 비디오 캠코더 + 빨간 REC 점"""
    img, d, S = _make_canvas(size)
    # 캠코더 사각 바디
    d.rounded_rectangle([S*0.12, S*0.26, S*0.62, S*0.76], radius=int(S*0.08), fill=_hex("#1e293b"), outline=_hex("#cbd5e1"), width=int(S*0.06))
    # 오른쪽 렌즈 원뿔
    d.polygon([(S*0.62, S*0.40), (S*0.88, S*0.26), (S*0.88, S*0.76), (S*0.62, S*0.62)], fill=_hex("#cbd5e1"))
    # 중앙 붉은 REC 점
    d.ellipse([S*0.26, S*0.40, S*0.48, S*0.62], fill=_hex("#ef4444"))
    return _finish_canvas(img, size)

def icon_snip(color=COL_ACTIVE, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 화면 캡처: 사각형 점선 영역 + 자르는 가위"""
    img, d, S = _make_canvas(size)
    # 사각 테두리
    d.rounded_rectangle([S*0.14, S*0.14, S*0.86, S*0.86], radius=int(S*0.08), outline=_hex("#64748b"), width=int(S*0.05))
    # 가위 손잡이 구멍 (두 개 원)
    d.ellipse([S*0.20, S*0.55, S*0.38, S*0.73], outline=_hex("#38bdf8"), width=int(S*0.05))
    d.ellipse([S*0.35, S*0.68, S*0.53, S*0.86], outline=_hex("#38bdf8"), width=int(S*0.05))
    # 가위 날
    d.line([(S*0.32, S*0.60), (S*0.76, S*0.24)], fill=_hex("#e2e8f0"), width=int(S*0.06))
    d.line([(S*0.44, S*0.72), (S*0.68, S*0.36)], fill=_hex("#e2e8f0"), width=int(S*0.06))
    return _finish_canvas(img, size)

def icon_screen(color=COL_ACTIVE, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 교실 대형 TV / 모니터: 와이드 평판 스크린 + 스탠드"""
    img, d, S = _make_canvas(size)
    # 와이드 스크린
    d.rounded_rectangle([S*0.10, S*0.14, S*0.90, S*0.70], radius=int(S*0.08), fill=_hex("#1e293b"), outline=_hex(color), width=int(S*0.06))
    # 화면 내부 푸른 디스플레이
    d.rectangle([S*0.18, S*0.22, S*0.82, S*0.62], fill=_hex("#0369a1"))
    # 모니터 기둥 스탠드
    d.rectangle([S*0.46, S*0.70, S*0.54, S*0.84], fill=_hex("#94a3b8"))
    # 스탠드 바닥 받침대
    d.rounded_rectangle([S*0.30, S*0.84, S*0.70, S*0.90], radius=int(S*0.03), fill=_hex("#cbd5e1"))
    return _finish_canvas(img, size)

def icon_widget(color=COL_MAIN, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 미니 위젯/시간표: 캘린더 시트 + 푸시핀"""
    img, d, S = _make_canvas(size)
    # 캘린더 판
    d.rounded_rectangle([S*0.16, S*0.20, S*0.84, S*0.88], radius=int(S*0.08), fill=_hex("#1e293b"), outline=_hex(color), width=int(S*0.06))
    # 상단 헤더 바
    d.rounded_rectangle([S*0.16, S*0.20, S*0.84, S*0.40], radius=int(S*0.08), fill=_hex("#ea580c"))
    # 내부 시간표 격자 라인
    d.line([(S*0.26, S*0.54), (S*0.74, S*0.54)], fill=_hex("#64748b"), width=int(S*0.04))
    d.line([(S*0.26, S*0.68), (S*0.74, S*0.68)], fill=_hex("#64748b"), width=int(S*0.04))
    # 링 바인더 구멍
    d.rectangle([S*0.30, S*0.12, S*0.38, S*0.24], fill=_hex("#e2e8f0"))
    d.rectangle([S*0.62, S*0.12, S*0.70, S*0.24], fill=_hex("#e2e8f0"))
    return _finish_canvas(img, size)

def icon_home(color=COL_ACTIVE, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 메인 홈: 지붕 + 굴뚝 + 문이 있는 집"""
    img, d, S = _make_canvas(size)
    # 지붕 (삼각형)
    d.polygon([(S*0.50, S*0.12), (S*0.10, S*0.48), (S*0.90, S*0.48)], fill=_hex(color))
    # 집 본체
    d.rectangle([S*0.22, S*0.46, S*0.78, S*0.88], fill=_hex("#1e293b"), outline=_hex(color), width=int(S*0.06))
    # 출입문
    d.rounded_rectangle([S*0.40, S*0.60, S*0.60, S*0.88], radius=int(S*0.03), fill=_hex("#38bdf8"))
    # 굴뚝
    d.rectangle([S*0.70, S*0.18, S*0.78, S*0.34], fill=_hex("#64748b"))
    return _finish_canvas(img, size)

def icon_broom(color=COL_YELLOW, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 청소/정리: 사선 빗자루 + 반짝이는 별빛"""
    img, d, S = _make_canvas(size)
    # 빗자루 자루
    d.line([(S*0.84, S*0.12), (S*0.44, S*0.56)], fill=_hex("#ca8a04"), width=int(S*0.08))
    # 빗자루 털 (부채꼴)
    d.polygon([(S*0.44, S*0.56), (S*0.54, S*0.64), (S*0.30, S*0.90), (S*0.14, S*0.82)], fill=_hex("#fde047"), outline=_hex("#78350f"), width=int(S*0.03))
    # 반짝이는 별 (청소 완료 효과)
    bx, by = S*0.22, S*0.32
    d.polygon([(bx, by-S*0.10), (bx+S*0.03, by-S*0.03), (bx+S*0.10, by), (bx+S*0.03, by+S*0.03),
               (bx, by+S*0.10), (bx-S*0.03, by+S*0.03), (bx-S*0.10, by), (bx-S*0.03, by-S*0.03)], fill=_hex("#38bdf8"))
    return _finish_canvas(img, size)

def icon_globe(color=COL_ACTIVE, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 웹 사이트: 경위도선이 들어간 지구본"""
    img, d, S = _make_canvas(size)
    cx, cy, r = S*0.50, S*0.50, S*0.38
    # 지구 외곽 원
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=_hex("#0284c7"), outline=_hex("#ffffff"), width=int(S*0.06))
    # 적도 가로선
    d.line([(cx-r, cy), (cx+r, cy)], fill=_hex("#ffffff"), width=int(S*0.04))
    # 경도 타원선
    d.ellipse([cx-r*0.5, cy-r, cx+r*0.5, cy+r], outline=_hex("#ffffff"), width=int(S*0.04))
    d.line([(cx, cy-r), (cx, cy+r)], fill=_hex("#ffffff"), width=int(S*0.04))
    return _finish_canvas(img, size)

def icon_pin(color=COL_MAIN, size=24, pinned=True, **kw) -> Image.Image:
    """누가 봐도 확실한 푸시핀: 빨간/파란 핀 머리 + 뾰족한 은색 바늘"""
    img, d, S = _make_canvas(size)
    pin_col = COL_ACTIVE if pinned else color
    cx = S*0.50
    # 핀 머리
    d.polygon([(cx, S*0.08), (cx+S*0.20, S*0.26), (cx+S*0.10, S*0.48), (cx-S*0.10, S*0.48), (cx-S*0.20, S*0.26)], fill=_hex(pin_col))
    # 핀 허리 밴드
    d.rectangle([cx-S*0.14, S*0.46, cx+S*0.14, S*0.54], fill=_hex("#cbd5e1"))
    # 핀 바늘 (뾰족한 끝)
    d.polygon([(cx-S*0.03, S*0.54), (cx+S*0.03, S*0.54), (cx, S*0.92)], fill=_hex("#94a3b8"))
    return _finish_canvas(img, size)

def icon_undo(color=COL_MAIN, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 실행 취소: 둥글게 유턴하는 커브드 화살표"""
    img, d, S = _make_canvas(size)
    cx, cy, r = S*0.52, S*0.54, S*0.32
    d.arc([cx-r, cy-r, cx+r, cy+r], start=160, end=380, fill=_hex(color), width=int(S*0.09))
    # 유턴 화살촉
    ax, ay = cx-r+S*0.04, cy+S*0.02
    d.polygon([(ax, ay-S*0.14), (ax-S*0.12, ay+S*0.04), (ax+S*0.10, ay+S*0.02)], fill=_hex(color))
    return _finish_canvas(img, size)

def icon_trash(color=COL_DANGER, size=24, **kw) -> Image.Image:
    """누가 봐도 확실한 쓰레기통: 비스듬히 열린 뚜껑 + 세로 줄무늬 바스켓"""
    img, d, S = _make_canvas(size)
    # 통 몸통 (사다리꼴)
    d.polygon([(S*0.22, S*0.34), (S*0.78, S*0.34), (S*0.70, S*0.88), (S*0.30, S*0.88)], fill=_hex("#1e293b"), outline=_hex(color), width=int(S*0.06))
    # 세로 줄무늬
    for x in [S*0.38, S*0.50, S*0.62]:
        d.line([(x, S*0.44), (x, S*0.78)], fill=_hex(color), width=int(S*0.04))
    # 살짝 비스듬히 열린 뚜껑
    d.line([(S*0.14, S*0.32), (S*0.86, S*0.24)], fill=_hex(color), width=int(S*0.08))
    # 뚜껑 손잡이
    d.rectangle([S*0.44, S*0.14, S*0.56, S*0.24], fill=_hex(color))
    return _finish_canvas(img, size)

def icon_close(color=COL_DANGER, size=24, **kw) -> Image.Image:
    """✕ 닫기"""
    img, d, S = _make_canvas(size)
    p = S*0.22
    d.line([(p, p), (S-p, S-p)], fill=_hex(color), width=int(S*0.10))
    d.line([(S-p, p), (p, S-p)], fill=_hex(color), width=int(S*0.10))
    return _finish_canvas(img, size)

def icon_minus(color=COL_MAIN, size=24, **kw) -> Image.Image:
    """— 최소화/접기"""
    img, d, S = _make_canvas(size)
    d.line([(S*0.20, S*0.50), (S*0.80, S*0.50)], fill=_hex(color), width=int(S*0.10))
    return _finish_canvas(img, size)

def icon_drag(color="#64748b", size=24, **kw) -> Image.Image:
    """⋮⋮ 6점 드래그 핸들"""
    img, d, S = _make_canvas(size)
    r = S*0.05
    for cx, cy in [
        (S*0.36, S*0.30), (S*0.64, S*0.30),
        (S*0.36, S*0.50), (S*0.64, S*0.50),
        (S*0.36, S*0.70), (S*0.64, S*0.70),
    ]:
        d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=_hex(color))
    return _finish_canvas(img, size)

def icon_ladder(color=COL_MAIN, size=24, **kw) -> Image.Image:
    """🪜 사다리타기: 2개의 세로 기둥 + 가로 다리들"""
    img, d, S = _make_canvas(size)
    d.line([(S*0.26, S*0.12), (S*0.26, S*0.88)], fill=_hex(color), width=int(S*0.07))
    d.line([(S*0.74, S*0.12), (S*0.74, S*0.88)], fill=_hex(color), width=int(S*0.07))
    for y in [S*0.28, S*0.48, S*0.68]:
        d.line([(S*0.26, y), (S*0.74, y)], fill=_hex(color), width=int(S*0.06))
    return _finish_canvas(img, size)

def icon_pinball(color=COL_MAIN, size=24, **kw) -> Image.Image:
    """⚾ 핀볼: 튕겨나가는 볼과 범퍼 핀들"""
    img, d, S = _make_canvas(size)
    for px, py in [(S*0.30, S*0.30), (S*0.70, S*0.30), (S*0.50, S*0.60)]:
        d.ellipse([px-S*0.08, py-S*0.08, px+S*0.08, py+S*0.08], fill=_hex("#38bdf8"))
    d.ellipse([S*0.42, S*0.72, S*0.58, S*0.88], fill=_hex("#fde047"), outline=_hex("#ca8a04"), width=int(S*0.03))
    return _finish_canvas(img, size)

# ══════════════════════════════════════════════════════════════════════════════
# 사진 1의 6종 타이머 전용 라인아트 아이콘
# ══════════════════════════════════════════════════════════════════════════

def icon_timer_digital(color="#000000", size=36, **kw) -> Image.Image:
    """사진 1: 반원 아치 + 00:00 전자 숫자판"""
    img, d, S = _make_canvas(size)
    d.arc([S*0.14, S*0.14, S*0.86, S*0.86], start=180, end=360, fill=_hex(color), width=int(S*0.06))
    d.ellipse([S*0.11, S*0.47, S*0.17, S*0.53], fill=_hex(color))
    # 00:00
    d.rounded_rectangle([S*0.18, S*0.38, S*0.34, S*0.74], radius=int(S*0.03), outline=_hex(color), width=int(S*0.06))
    d.rounded_rectangle([S*0.37, S*0.38, S*0.53, S*0.74], radius=int(S*0.03), outline=_hex(color), width=int(S*0.06))
    d.ellipse([S*0.55, S*0.48, S*0.58, S*0.51], fill=_hex(color))
    d.ellipse([S*0.55, S*0.61, S*0.58, S*0.64], fill=_hex(color))
    d.rounded_rectangle([S*0.60, S*0.38, S*0.76, S*0.74], radius=int(S*0.03), outline=_hex(color), width=int(S*0.06))
    d.rounded_rectangle([S*0.79, S*0.38, S*0.95, S*0.74], radius=int(S*0.03), outline=_hex(color), width=int(S*0.06))
    return _finish_canvas(img, size)

def icon_timer_analog(color="#000000", size=36, **kw) -> Image.Image:
    """사진 1: 원형 시계 + 12시 바늘 + 중앙 원"""
    img, d, S = _make_canvas(size)
    cx, cy, r = S*0.50, S*0.50, S*0.38
    d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=_hex(color), width=int(S*0.06))
    d.ellipse([cx-r+S*0.04, cy-r+S*0.04, cx+r-S*0.04, cy+r-S*0.04], outline=_hex(color), width=int(S*0.03))
    d.line([(cx, cy-r+S*0.04), (cx, cy-r+S*0.10)], fill=_hex(color), width=int(S*0.05))
    d.line([(cx, cy+r-S*0.10), (cx, cy+r-S*0.04)], fill=_hex(color), width=int(S*0.05))
    d.line([(cx-r+S*0.04, cy), (cx-r+S*0.10, cy)], fill=_hex(color), width=int(S*0.05))
    d.line([(cx+r-S*0.10, cy), (cx+r-S*0.04, cy)], fill=_hex(color), width=int(S*0.05))
    d.line([(cx, cy), (cx, cy-r+S*0.12)], fill=_hex(color), width=int(S*0.06))
    d.polygon([(cx, cy-r+S*0.08), (cx-S*0.05, cy-r+S*0.15), (cx+S*0.05, cy-r+S*0.15)], fill=_hex(color))
    d.ellipse([cx-S*0.06, cy-S*0.06, cx+S*0.06, cy+S*0.06], outline=_hex(color), width=int(S*0.05))
    return _finish_canvas(img, size)

def icon_timer_hourglass(color="#000000", size=36, **kw) -> Image.Image:
    """사진 1: 상하 대칭 잘록한 모래시계 + 받침대"""
    img, d, S = _make_canvas(size)
    d.line([(S*0.22, S*0.18), (S*0.78, S*0.18)], fill=_hex(color), width=int(S*0.06))
    d.line([(S*0.22, S*0.82), (S*0.78, S*0.82)], fill=_hex(color), width=int(S*0.06))
    pts = [
        (S*0.26, S*0.18), (S*0.26, S*0.34), (S*0.46, S*0.50),
        (S*0.26, S*0.66), (S*0.26, S*0.82), (S*0.74, S*0.82),
        (S*0.74, S*0.66), (S*0.54, S*0.50), (S*0.74, S*0.34), (S*0.74, S*0.18)
    ]
    d.polygon(pts, outline=_hex(color), width=int(S*0.06))
    d.line([(S*0.34, S*0.30), (S*0.66, S*0.30)], fill=_hex(color), width=int(S*0.04))
    d.line([(S*0.32, S*0.74), (S*0.68, S*0.74)], fill=_hex(color), width=int(S*0.04))
    return _finish_canvas(img, size)

def icon_timer_pie(color="#000000", size=36, **kw) -> Image.Image:
    """사진 1: 파이 타이머 (부채꼴 음영)"""
    img, d, S = _make_canvas(size)
    cx, cy, r = S*0.50, S*0.50, S*0.38
    for a in range(0, 360, 30):
        rad = math.radians(a)
        x1 = cx + (r - S*0.08) * math.cos(rad)
        y1 = cy + (r - S*0.08) * math.sin(rad)
        x2 = cx + r * math.cos(rad)
        y2 = cy + r * math.sin(rad)
        d.line([(x1, y1), (x2, y2)], fill=_hex(color), width=int(S*0.04))
    d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=_hex(color), width=int(S*0.06))
    d.pieslice([cx-r+S*0.05, cy-r+S*0.05, cx+r-S*0.05, cy+r-S*0.05], start=270, end=330, fill=_hex("#cbd5e1"), outline=_hex(color), width=int(S*0.05))
    d.ellipse([cx-S*0.06, cy-S*0.06, cx+S*0.06, cy+S*0.06], outline=_hex(color), width=int(S*0.05))
    return _finish_canvas(img, size)

def icon_timer_balloon(color="#000000", size=36, **kw) -> Image.Image:
    """사진 1: 풍선 타이머"""
    img, d, S = _make_canvas(size)
    d.ellipse([S*0.22, S*0.14, S*0.78, S*0.74], outline=_hex(color), width=int(S*0.06))
    d.polygon([(S*0.44, S*0.78), (S*0.56, S*0.78), (S*0.50, S*0.72)], outline=_hex(color), width=int(S*0.05))
    d.line([(S*0.50, S*0.78), (S*0.50, S*0.92)], fill=_hex(color), width=int(S*0.05))
    d.arc([S*0.28, S*0.20, S*0.72, S*0.68], start=200, end=250, fill=_hex(color), width=int(S*0.05))
    return _finish_canvas(img, size)

def icon_timer_stopwatch(color="#000000", size=36, **kw) -> Image.Image:
    """사진 1: 스톱워치"""
    img, d, S = _make_canvas(size)
    cx, cy, r = S*0.50, S*0.56, S*0.34
    d.line([(cx-S*0.08, S*0.12), (cx+S*0.08, S*0.12)], fill=_hex(color), width=int(S*0.06))
    d.line([(cx, S*0.12), (cx, S*0.22)], fill=_hex(color), width=int(S*0.05))
    d.line([(cx-S*0.24, S*0.24), (cx-S*0.16, S*0.30)], fill=_hex(color), width=int(S*0.06))
    d.line([(cx+S*0.24, S*0.24), (cx+S*0.16, S*0.30)], fill=_hex(color), width=int(S*0.06))
    d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=_hex(color), width=int(S*0.06))
    for a in range(0, 360, 45):
        rad = math.radians(a)
        px = cx + (r - S*0.08) * math.cos(rad)
        py = cy + (r - S*0.08) * math.sin(rad)
        d.ellipse([px-S*0.02, py-S*0.02, px+S*0.02, py+S*0.02], fill=_hex(color))
    d.line([(cx, cy), (cx, cy-r+S*0.08)], fill=_hex(color), width=int(S*0.05))
    d.ellipse([cx-S*0.04, cy-S*0.04, cx+S*0.04, cy+S*0.04], fill=_hex(color))
    return _finish_canvas(img, size)

def icon_pencil(color="#000000", size=24, **kw) -> Image.Image:
    """사진 3, 4: 색연필/연필"""
    img, d, S = _make_canvas(size)
    pts = [(S*0.22, S*0.74), (S*0.28, S*0.80), (S*0.80, S*0.28), (S*0.74, S*0.22)]
    d.polygon(pts, outline=_hex(color), width=int(S*0.07))
    d.polygon([(S*0.22, S*0.74), (S*0.28, S*0.80), (S*0.14, S*0.86)], fill=_hex(color))
    d.line([(S*0.68, S*0.28), (S*0.74, S*0.34)], fill=_hex(color), width=int(S*0.06))
    return _finish_canvas(img, size)

def icon_pointer(color="#000000", size=24, **kw) -> Image.Image:
    """사진 3, 4: 마우스 포인터 화살표 (선택(V))"""
    img, d, S = _make_canvas(size)
    d.line([(S*0.24, S*0.38), (S*0.14, S*0.38)], fill=_hex(color), width=int(S*0.06))
    d.line([(S*0.28, S*0.30), (S*0.18, S*0.20)], fill=_hex(color), width=int(S*0.06))
    d.line([(S*0.38, S*0.26), (S*0.38, S*0.14)], fill=_hex(color), width=int(S*0.06))
    pts = [
        (S*0.42, S*0.32), (S*0.84, S*0.52), (S*0.64, S*0.60),
        (S*0.76, S*0.86), (S*0.64, S*0.92), (S*0.52, S*0.66), (S*0.36, S*0.74)
    ]
    d.polygon(pts, outline=_hex(color), width=int(S*0.06))
    return _finish_canvas(img, size)

def icon_eraser_box(color="#000000", size=24, **kw) -> Image.Image:
    """사진 3, 4: 지우개 박스"""
    img, d, S = _make_canvas(size)
    d.polygon([(S*0.20, S*0.68), (S*0.54, S*0.34), (S*0.84, S*0.64), (S*0.50, S*0.88)], outline=_hex(color), width=int(S*0.07))
    d.line([(S*0.38, S*0.50), (S*0.68, S*0.80)], fill=_hex(color), width=int(S*0.06))
    d.line([(S*0.20, S*0.88), (S*0.70, S*0.88)], fill=_hex(color), width=int(S*0.06))
    return _finish_canvas(img, size)

def icon_eye(color="#000000", size=24, **kw) -> Image.Image:
    """사진 3, 4: 눈 모양"""
    img, d, S = _make_canvas(size)
    d.arc([S*0.14, S*0.28, S*0.86, S*0.72], start=0, end=180, fill=_hex(color), width=int(S*0.07))
    d.arc([S*0.14, S*0.28, S*0.86, S*0.72], start=180, end=360, fill=_hex(color), width=int(S*0.07))
    d.ellipse([S*0.38, S*0.38, S*0.62, S*0.62], fill=_hex(color))
    return _finish_canvas(img, size)

def icon_rocket(color=COL_ACTIVE, size=24, **kw) -> Image.Image:
    """🚀 우주선 로켓: 빠른 실행 / 바로가기 아이콘"""
    img, d, S = _make_canvas(size)
    pts = [
        (S*0.75, S*0.15), (S*0.82, S*0.35), (S*0.55, S*0.65),
        (S*0.35, S*0.82), (S*0.15, S*0.75), (S*0.35, S*0.45)
    ]
    d.polygon(pts, fill=_hex("#38bdf8"), outline=_hex("#0284c7"), width=int(S*0.04))
    d.ellipse([S*0.48, S*0.38, S*0.62, S*0.52], fill=_hex("#ffffff"), outline=_hex("#0284c7"), width=int(S*0.03))
    d.polygon([(S*0.25, S*0.55), (S*0.12, S*0.65), (S*0.20, S*0.75)], fill=_hex("#f97316"))
    d.polygon([(S*0.55, S*0.25), (S*0.65, S*0.12), (S*0.75, S*0.20)], fill=_hex("#f97316"))
    d.polygon([(S*0.20, S*0.80), (S*0.08, S*0.92), (S*0.28, S*0.88)], fill=_hex("#ef4444"))
    return _finish_canvas(img, size)

def icon_music(color=COL_GREEN, size=24, **kw) -> Image.Image:
    """🎵 8분 음표 한 쌍 (음악 / BGM 아이콘)"""
    img, d, S = _make_canvas(size)
    d.ellipse([S*0.18, S*0.62, S*0.42, S*0.84], fill=_hex(color))
    d.ellipse([S*0.58, S*0.50, S*0.82, S*0.72], fill=_hex(color))
    d.line([(S*0.38, S*0.68), (S*0.38, S*0.22)], fill=_hex(color), width=int(S*0.08))
    d.line([(S*0.78, S*0.56), (S*0.78, S*0.14)], fill=_hex(color), width=int(S*0.08))
    d.polygon([(S*0.34, S*0.24), (S*0.82, S*0.12), (S*0.82, S*0.26), (S*0.34, S*0.38)], fill=_hex(color))
    return _finish_canvas(img, size)

# ══════════════════════════════════════════════════════════════════════════════
# 아이콘 레지스트리 & 캐시 매니저
# ══════════════════════════════════════════════════════════════════════════════

ICON_REGISTRY = {
    "pen":          icon_pen,
    "highlighter":  icon_highlighter,
    "eraser":       icon_eraser,
    "text":         icon_text,
    "arrow":        icon_arrow,
    "rect":         icon_rect,
    "emoji_stamp":  icon_emoji_stamp,
    "mouse":        icon_mouse,
    "camera":       icon_camera,
    "timer":        icon_timer,
    "dice":         icon_dice,
    "wheel":        icon_wheel,
    "magnifier":    icon_magnifier,
    "record":       icon_record,
    "snip":         icon_snip,
    "screen":       icon_screen,
    "widget":       icon_widget,
    "home":         icon_home,
    "broom":        icon_broom,
    "globe":        icon_globe,
    "pin":          icon_pin,
    "undo":         icon_undo,
    "trash":        icon_trash,
    "close":        icon_close,
    "minus":        icon_minus,
    "drag":         icon_drag,
    "ladder":       icon_ladder,
    "pinball":      icon_pinball,
    "drawing":      icon_pen,

    # 사진 1의 6종 전용 타이머 라인아트 아이콘
    "timer_digital":    icon_timer_digital,
    "timer_analog":     icon_timer_analog,
    "timer_hourglass":  icon_timer_hourglass,
    "timer_pie":        icon_timer_pie,
    "timer_balloon":    icon_timer_balloon,
    "timer_stopwatch":  icon_timer_stopwatch,

    "pencil":           icon_pencil,
    "pointer":          icon_pointer,
    "eraser_box":       icon_eraser_box,
    "eye":              icon_eye,
    "rocket":           icon_rocket,
    "music":            icon_music,
}

_CTK_CACHE = {}

def get_icon(name: str, color=COL_MAIN, size=24, **kw) -> ctk.CTkImage:
    """
    이름으로 고화질 안티앨리어싱 CTkImage 반환 (동일 요청 시 캐시 재사용)
    """
    key = (name, color, size, tuple(sorted(kw.items())))
    if key in _CTK_CACHE:
        return _CTK_CACHE[key]

    fn = ICON_REGISTRY.get(name, icon_pen)
    pil_img = fn(color=color, size=size, **kw)
    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(size, size))
    _CTK_CACHE[key] = ctk_img
    return ctk_img
