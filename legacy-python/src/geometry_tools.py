"""
놀티쳐 판서용 기하 측정 도구 (Geometry Tools)
- 반투명 정밀 눈금자 (Ruler)
- 반투명 직각 삼각자 (Set Square / Triangle)
- 반투명 180도 각도기 (Protractor)
- 모눈종이(Grid) 격자선 관리자
"""
import math
import tkinter as tk

class GridManager:
    """판서 캔버스 모눈종이(격자선) 관리자"""
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.is_active = False
        self.grid_size = 40  # 40px 격자

    def toggle(self, bg_mode="screen"):
        self.is_active = not self.is_active
        if self.is_active:
            self.draw(bg_mode)
        else:
            self.clear()
        return self.is_active

    def draw(self, bg_mode="screen"):
        self.clear()
        w = self.canvas.winfo_width() or 1920
        h = self.canvas.winfo_height() or 1080
        
        # 배경 모드에 따라 눈금 색상 최적화
        if bg_mode == "greenboard":
            line_col = "#2a5441"
            major_col = "#387056"
        elif bg_mode == "whiteboard":
            line_col = "#e2e8f0"
            major_col = "#cbd5e1"
        else:
            line_col = "#334155"
            major_col = "#475569"

        # 세로선
        for x in range(0, w, self.grid_size):
            is_major = (x % (self.grid_size * 5) == 0)
            col = major_col if is_major else line_col
            self.canvas.create_line(x, 0, x, h, fill=col, width=1.5 if is_major else 1, dash=(2, 2) if not is_major else (), tags=("grid_line", "bg_layer"))
        
        # 가로선
        for y in range(0, h, self.grid_size):
            is_major = (y % (self.grid_size * 5) == 0)
            col = major_col if is_major else line_col
            self.canvas.create_line(0, y, w, y, fill=col, width=1.5 if is_major else 1, dash=(2, 2) if not is_major else (), tags=("grid_line", "bg_layer"))

        # 최하단으로 정렬
        self.canvas.tag_lower("grid_line")

    def clear(self):
        self.canvas.delete("grid_line")


class GeometryObject:
    """캔버스 위에서 드래그 이동 및 회전 가능한 측정 도구 베이스 클래스"""
    def __init__(self, canvas: tk.Canvas, cx: float, cy: float, tag_prefix: str):
        self.canvas = canvas
        self.cx = cx
        self.cy = cy
        self.angle = 0.0  # 도(degree) 단위
        self.tag = f"{tag_prefix}_{id(self)}"
        self._drag_start = (0, 0)
        self._rot_start_angle = 0.0

    def rotate_point(self, px, py):
        rad = math.radians(self.angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        rx = cos_a * px - sin_a * py + self.cx
        ry = sin_a * px + cos_a * py + self.cy
        return rx, ry

    def delete(self):
        self.canvas.delete(self.tag)

    def _bind_events(self, body_tag, rot_tag, close_tag):
        # 이동 바인딩
        self.canvas.tag_bind(body_tag, "<Button-1>", self._on_body_press)
        self.canvas.tag_bind(body_tag, "<B1-Motion>", self._on_body_drag)
        self.canvas.tag_bind(body_tag, "<Button-3>", lambda e: self.delete())  # 우클릭 삭제

        # 회전 바인딩
        if rot_tag:
            self.canvas.tag_bind(rot_tag, "<Button-1>", self._on_rot_press)
            self.canvas.tag_bind(rot_tag, "<B1-Motion>", self._on_rot_drag)

        # 닫기 버튼
        if close_tag:
            self.canvas.tag_bind(close_tag, "<Button-1>", lambda e: self.delete())

    def _on_body_press(self, event):
        self._drag_start = (event.x, event.y)

    def _on_body_drag(self, event):
        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]
        self.cx += dx
        self.cy += dy
        self._drag_start = (event.x, event.y)
        self.redraw()

    def _on_rot_press(self, event):
        dx = event.x - self.cx
        dy = event.y - self.cy
        current_mouse_angle = math.degrees(math.atan2(dy, dx))
        self._rot_start_angle = current_mouse_angle - self.angle

    def _on_rot_drag(self, event):
        dx = event.x - self.cx
        dy = event.y - self.cy
        cur_mouse = math.degrees(math.atan2(dy, dx))
        self.angle = (cur_mouse - self._rot_start_angle) % 360
        self.redraw()

    def redraw(self):
        pass


class RulerTool(GeometryObject):
    """정밀 25cm 반투명 눈금자"""
    def __init__(self, canvas: tk.Canvas, x=300, y=300):
        super().__init__(canvas, x, y, "ruler")
        self.length = 450  # 450px = 약 25cm
        self.height = 70
        self.redraw()

    def redraw(self):
        self.canvas.delete(self.tag)
        hw = self.length / 2
        hh = self.height / 2

        # 4개 꼭짓점
        p1 = self.rotate_point(-hw, -hh)
        p2 = self.rotate_point(hw, -hh)
        p3 = self.rotate_point(hw, hh)
        p4 = self.rotate_point(-hw, hh)

        # 반투명 자 본체
        body_id = self.canvas.create_polygon(
            p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], p4[0], p4[1],
            fill="#e0f2fe", outline="#0284c7", width=2, stipple="gray50",
            tags=(self.tag, f"{self.tag}_body")
        )

        # 상단 눈금선들 (18px 간격 = 1cm 단위)
        cm_step = 18
        num_cms = int(self.length // cm_step)
        start_x = -hw + 15
        
        for i in range(num_cms):
            cur_x = start_x + i * cm_step
            if cur_x > hw - 20:
                break
            
            # 1cm 대눈금
            lp1 = self.rotate_point(cur_x, -hh)
            lp2 = self.rotate_point(cur_x, -hh + 14)
            self.canvas.create_line(lp1[0], lp1[1], lp2[0], lp2[1], fill="#0369a1", width=1.5, tags=self.tag)

            # 숫자 표시
            tp = self.rotate_point(cur_x, -hh + 24)
            self.canvas.create_text(tp[0], tp[1], text=str(i), fill="#0f172a", font=("Consolas", 8, "bold"), tags=self.tag)

            # 5mm 중눈금
            if i < num_cms - 1:
                mid_x = cur_x + cm_step / 2
                mp1 = self.rotate_point(mid_x, -hh)
                mp2 = self.rotate_point(mid_x, -hh + 9)
                self.canvas.create_line(mp1[0], mp1[1], mp2[0], mp2[1], fill="#0284c7", width=1, tags=self.tag)

        # 중앙 브랜드 라벨
        cp = self.rotate_point(0, 5)
        self.canvas.create_text(cp[0], cp[1], text=f"📏 놀티쳐 자 ({int(self.angle)}°)", fill="#0369a1", font=("Malgun Gothic", 9, "bold"), tags=(self.tag, f"{self.tag}_body"))

        # 우측 회전 핸들 (녹색 원)
        rp = self.rotate_point(hw - 14, 0)
        rot_id = self.canvas.create_oval(
            rp[0]-9, rp[1]-9, rp[0]+9, rp[1]+9,
            fill="#10b981", outline="#ffffff", width=1.5,
            tags=(self.tag, f"{self.tag}_rot")
        )

        # 좌측 닫기 핸들 (빨간 X 원)
        close_p = self.rotate_point(-hw + 14, 0)
        close_id = self.canvas.create_oval(
            close_p[0]-8, close_p[1]-8, close_p[0]+8, close_p[1]+8,
            fill="#ef4444", outline="#ffffff", width=1.5,
            tags=(self.tag, f"{self.tag}_close")
        )
        self.canvas.create_text(close_p[0], close_p[1], text="✕", fill="#ffffff", font=("Malgun Gothic", 8, "bold"), tags=(self.tag, f"{self.tag}_close"))

        self._bind_events(f"{self.tag}_body", f"{self.tag}_rot", f"{self.tag}_close")


class TriangleTool(GeometryObject):
    """반투명 직각 삼각자 (45-45-90°)"""
    def __init__(self, canvas: tk.Canvas, x=450, y=350):
        super().__init__(canvas, x, y, "triangle")
        self.size = 260
        self.redraw()

    def redraw(self):
        self.canvas.delete(self.tag)
        s = self.size
        # 직각 꼭짓점이 (-s/3, s/3) 근처인 삼각형
        ox, oy = -s/3, s/3
        p_right = self.rotate_point(ox, oy)
        p_top = self.rotate_point(ox, oy - s)
        p_right_edge = self.rotate_point(ox + s, oy)

        # 외곽 삼각형 (반투명)
        self.canvas.create_polygon(
            p_right[0], p_right[1], p_top[0], p_top[1], p_right_edge[0], p_right_edge[1],
            fill="#fed7aa", outline="#ea580c", width=2, stipple="gray50",
            tags=(self.tag, f"{self.tag}_body")
        )

        # 내부 구멍 삼각형
        in_s = s * 0.45
        ip_r = self.rotate_point(ox + 25, oy - 25)
        ip_t = self.rotate_point(ox + 25, oy - 25 - in_s)
        ip_e = self.rotate_point(ox + 25 + in_s, oy - 25)
        self.canvas.create_polygon(
            ip_r[0], ip_r[1], ip_t[0], ip_t[1], ip_e[0], ip_e[1],
            fill="#ffffff", outline="#f97316", width=1.5,
            tags=(self.tag, f"{self.tag}_body")
        )

        # 밑변 눈금 (cm)
        step = 18
        for i in range(int(s // step) - 1):
            gx = ox + (i + 1) * step
            if gx > ox + s - 20: break
            gp1 = self.rotate_point(gx, oy)
            gp2 = self.rotate_point(gx, oy - 10)
            self.canvas.create_line(gp1[0], gp1[1], gp2[0], gp2[1], fill="#c2410c", width=1.5, tags=self.tag)

        # 직각 마크
        sq1 = self.rotate_point(ox + 16, oy)
        sq2 = self.rotate_point(ox + 16, oy - 16)
        sq3 = self.rotate_point(ox, oy - 16)
        self.canvas.create_line(sq1[0], sq1[1], sq2[0], sq2[1], sq3[0], sq3[1], fill="#ea580c", width=1.5, tags=self.tag)

        # 중앙 텍스트
        tp = self.rotate_point(ox + s * 0.35, oy - s * 0.35)
        self.canvas.create_text(tp[0], tp[1], text=f"📐 삼각자 ({int(self.angle)}°)", fill="#9a3412", font=("Malgun Gothic", 9, "bold"), tags=(self.tag, f"{self.tag}_body"))

        # 회전 핸들 (빗변 중앙)
        rot_p = self.rotate_point(ox + s * 0.5, oy - s * 0.5)
        self.canvas.create_oval(
            rot_p[0]-9, rot_p[1]-9, rot_p[0]+9, rot_p[1]+9,
            fill="#10b981", outline="#ffffff", width=1.5,
            tags=(self.tag, f"{self.tag}_rot")
        )

        # 닫기 핸들
        cl_p = self.rotate_point(ox + 14, oy - 14)
        self.canvas.create_oval(
            cl_p[0]-8, cl_p[1]-8, cl_p[0]+8, cl_p[1]+8,
            fill="#ef4444", outline="#ffffff", width=1.5,
            tags=(self.tag, f"{self.tag}_close")
        )
        self.canvas.create_text(cl_p[0], cl_p[1], text="✕", fill="#ffffff", font=("Malgun Gothic", 8, "bold"), tags=(self.tag, f"{self.tag}_close"))

        self._bind_events(f"{self.tag}_body", f"{self.tag}_rot", f"{self.tag}_close")


class ProtractorTool(GeometryObject):
    """반투명 180도 정밀 각도기"""
    def __init__(self, canvas: tk.Canvas, x=600, y=350):
        super().__init__(canvas, x, y, "protractor")
        self.radius = 140
        self.redraw()

    def redraw(self):
        self.canvas.delete(self.tag)
        r = self.radius

        # 반원 폴리곤 점들 생성 (위쪽 반원: -180도 ~ 0도)
        pts = []
        for deg in range(0, 181, 5):
            rad = math.radians(180 - deg)
            lx = r * math.cos(rad)
            ly = -r * math.sin(rad)
            rx, ry = self.rotate_point(lx, ly)
            pts.extend([rx, ry])

        # 중심점 기준 닫기
        cx0, cy0 = self.rotate_point(0, 0)
        pts.extend([cx0, cy0])

        # 반투명 반원 면
        self.canvas.create_polygon(
            *pts, fill="#ddd6fe", outline="#7c3aed", width=2, stipple="gray50",
            tags=(self.tag, f"{self.tag}_body")
        )

        # 밑변 기준선
        bl1 = self.rotate_point(-r, 0)
        bl2 = self.rotate_point(r, 0)
        self.canvas.create_line(bl1[0], bl1[1], bl2[0], bl2[1], fill="#6d28d9", width=2, tags=self.tag)

        # 중심 십자 가이드 (+)
        self.canvas.create_line(cx0 - 8, cy0, cx0 + 8, cy0, fill="#4c1d95", width=2, tags=self.tag)
        c_top = self.rotate_point(0, -10)
        self.canvas.create_line(cx0, cy0, c_top[0], c_top[1], fill="#4c1d95", width=2, tags=self.tag)

        # 각도 눈금들 (10도 단위)
        for deg in range(0, 181, 10):
            rad = math.radians(180 - deg)
            is_cardinal = (deg % 30 == 0 or deg == 90)
            
            p_out = self.rotate_point(r * math.cos(rad), -r * math.sin(rad))
            tick_len = 14 if is_cardinal else 8
            p_in = self.rotate_point((r - tick_len) * math.cos(rad), -(r - tick_len) * math.sin(rad))
            self.canvas.create_line(p_out[0], p_out[1], p_in[0], p_in[1], fill="#5b21b6", width=1.5 if is_cardinal else 1, tags=self.tag)

            if is_cardinal:
                tp = self.rotate_point((r - 24) * math.cos(rad), -(r - 24) * math.sin(rad))
                self.canvas.create_text(tp[0], tp[1], text=str(deg), fill="#3b0764", font=("Consolas", 7, "bold"), tags=self.tag)

        # 중앙 텍스트
        cp = self.rotate_point(0, -r * 0.45)
        self.canvas.create_text(cp[0], cp[1], text=f"🧭 각도기 ({int(self.angle)}°)", fill="#5b21b6", font=("Malgun Gothic", 9, "bold"), tags=(self.tag, f"{self.tag}_body"))

        # 회전 핸들 (상단 꼭대기 90도 부근)
        rot_p = self.rotate_point(0, -r + 16)
        self.canvas.create_oval(
            rot_p[0]-9, rot_p[1]-9, rot_p[0]+9, rot_p[1]+9,
            fill="#10b981", outline="#ffffff", width=1.5,
            tags=(self.tag, f"{self.tag}_rot")
        )

        # 닫기 핸들
        cl_p = self.rotate_point(0, -8)
        self.canvas.create_oval(
            cl_p[0]-8, cl_p[1]-8, cl_p[0]+8, cl_p[1]+8,
            fill="#ef4444", outline="#ffffff", width=1.5,
            tags=(self.tag, f"{self.tag}_close")
        )
        self.canvas.create_text(cl_p[0], cl_p[1], text="✕", fill="#ffffff", font=("Malgun Gothic", 8, "bold"), tags=(self.tag, f"{self.tag}_close"))

        self._bind_events(f"{self.tag}_body", f"{self.tag}_rot", f"{self.tag}_close")
