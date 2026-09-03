"""
놀티쳐 실물화상기 (Visualizer / Document Camera)
- USB 실물화상기(BESTCAM, ELMO, AVer, IPEVO 등) 및 웹캠 실시간 고화질 스트리밍
- DirectShow / MSMF 멀티 백엔드 자동 폴백 및 150ms 쿨다운 자가 치유(Self-Healing)
- Windows PnP 장치 친화적 이름(FriendlyName) 자동 감지
- Zero-Flicker(무깜빡임) 고속 캔버스 렌더러 (delete all 제거, itemconfig 교체)
- 90° 회전, 좌우/상하 반전, 화면 정지(Freeze), 고대비 문서 모드, 디지털 줌 (1.0x ~ 3.0x)
"""

import os
import sys
import time
import threading
import datetime
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import cv2

from src.font_config import setup_global_fonts, get_font
from src.tooltip import attach_tooltip

def get_pnp_camera_names():
    """Windows PnP 장치 친화적 이름 목록 조회"""
    names = []
    if sys.platform == "win32":
        try:
            cmd = 'powershell -NoProfile -Command "Get-PnpDevice -Class Camera,Image -Status OK | Select-Object -ExpandProperty FriendlyName"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3)
            lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]
            for l in lines:
                if l and l not in names:
                    names.append(l)
        except Exception:
            pass
    return names

class VisualizerWindow(ctk.CTkToplevel):
    _instance = None

    @classmethod
    def get_instance(cls, parent=None):
        if cls._instance is None or not cls._instance.winfo_exists():
            cls._instance = cls(parent)
        else:
            cls._instance.deiconify()
            cls._instance.lift()
            cls._instance.focus_force()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.title("놀티쳐 스마트 실물화상기")
        self.geometry("1040x700")
        self.minsize(680, 480)
        self.configure(fg_color="#0f172a")

        setup_global_fonts(self)
        self._load_icon()

        # 카메라 및 스트리밍 상태
        self.cap = None
        self.current_cam_index = 0
        self.is_running = False
        self.is_frozen = False
        self.latest_frame = None
        self.frozen_frame = None
        self.capture_thread = None

        # 화면 변환 설정
        self.rotation_deg = 0
        self.flip_horizontal = False
        self.flip_vertical = False
        self.doc_mode = False
        self.sharp_mode = False
        self.zoom_level = 1.0
        self.is_fullscreen = False

        # 캔버스 렌더링 최적화용 ID
        self._canvas_img_id = None
        self._canvas_text_id = None
        self._freeze_box_id = None
        self._freeze_text_id = None
        self._photo_image = None

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._exit_fullscreen())

        self._build_ui()
        self._detect_and_start_camera()
        self._schedule_render()

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def _build_ui(self):
        # 1. 상단 컨트롤 툴바 (단정한 다크 바, 높이 52px)
        self.toolbar = ctk.CTkFrame(self, fg_color="#1e293b", height=52, corner_radius=0)
        self.toolbar.pack(fill="x", side="top")
        self.toolbar.pack_propagate(False)

        tb_inner = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        tb_inner.pack(fill="both", expand=True, padx=12, pady=8)

        # 카메라 선택 드롭다운 (실제 장치명 반영)
        self.cam_combo = ctk.CTkComboBox(
            tb_inner, values=["실물화상기 검색 중..."],
            width=220, height=34, font=get_font(11, "bold"),
            command=self._on_cam_changed
        )
        self.cam_combo.pack(side="left", padx=(0, 4))
        attach_tooltip(self.cam_combo, "입력 실물화상기/카메라 선택")

        refresh_cam_btn = ctk.CTkButton(
            tb_inner, text="새로고침", width=68, height=34,
            font=get_font(10, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=self._detect_and_start_camera
        )
        refresh_cam_btn.pack(side="left", padx=(0, 8))
        attach_tooltip(refresh_cam_btn, "연결된 카메라 목록 새로고침")

        self._sep(tb_inner)

        # 90도 회전
        self.rot_btn = ctk.CTkButton(
            tb_inner, text="90° 회전", width=68, height=34,
            font=get_font(10, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=self._rotate_90
        )
        self.rot_btn.pack(side="left", padx=2)
        attach_tooltip(self.rot_btn, "화면 90도 시계방향 회전")

        # 좌우 반전
        self.fliph_btn = ctk.CTkButton(
            tb_inner, text="좌우반전", width=64, height=34,
            font=get_font(10, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=self._toggle_flip_h
        )
        self.fliph_btn.pack(side="left", padx=2)

        # 상하 반전
        self.flipv_btn = ctk.CTkButton(
            tb_inner, text="상하반전", width=64, height=34,
            font=get_font(10, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=self._toggle_flip_v
        )
        self.flipv_btn.pack(side="left", padx=2)

        self._sep(tb_inner)

        # 화면 일시정지 (Freeze)
        self.freeze_btn = ctk.CTkButton(
            tb_inner, text="화면정지", width=68, height=34,
            font=get_font(10, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=self._toggle_freeze
        )
        self.freeze_btn.pack(side="left", padx=2)
        attach_tooltip(self.freeze_btn, "학생들에게 특정 장면을 멈추어 보여주기")

        # 문서 강조 모드 (흑백/고대비)
        self.doc_btn = ctk.CTkButton(
            tb_inner, text="문서강조", width=68, height=34,
            font=get_font(10, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=self._toggle_doc_mode
        )
        self.doc_btn.pack(side="left", padx=2)
        attach_tooltip(self.doc_btn, "교과서/학습지 글씨 선명하게 강조")

        self._sep(tb_inner)

        # 디지털 줌
        ctk.CTkButton(
            tb_inner, text="−", width=28, height=34,
            font=get_font(13, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=lambda: self._zoom_step(-0.25)
        ).pack(side="left", padx=1)

        self.zoom_lbl = ctk.CTkLabel(
            tb_inner, text="1.0x", width=40,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#38bdf8"
        )
        self.zoom_lbl.pack(side="left", padx=1)

        ctk.CTkButton(
            tb_inner, text="+", width=28, height=34,
            font=get_font(13, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=lambda: self._zoom_step(0.25)
        ).pack(side="left", padx=1)

        # 우측 제어 그룹
        right_box = ctk.CTkFrame(tb_inner, fg_color="transparent")
        right_box.pack(side="right")

        # 닫기
        ctk.CTkButton(
            right_box, text="✕", width=34, height=34,
            font=get_font(12, "bold"), fg_color="#dc2626", hover_color="#b91c1c",
            text_color="#ffffff", corner_radius=6, command=self.close
        ).pack(side="right", padx=(4, 0))

        # 전체화면
        self.fs_btn = ctk.CTkButton(
            right_box, text="전체화면", width=74, height=34,
            font=get_font(10, "bold"), fg_color="#0284c7", hover_color="#0369a1",
            text_color="#ffffff", corner_radius=6, command=self._toggle_fullscreen
        )
        self.fs_btn.pack(side="right", padx=2)

        # 화면 판서 연동
        draw_btn = ctk.CTkButton(
            right_box, text="화면판서", width=74, height=34,
            font=get_font(10, "bold"), fg_color="#ea580c", hover_color="#c2410c",
            text_color="#ffffff", corner_radius=6, command=self._open_drawing
        )
        draw_btn.pack(side="right", padx=2)

        # 스냅샷 캡처
        cap_btn = ctk.CTkButton(
            right_box, text="캡처저장", width=74, height=34,
            font=get_font(10, "bold"), fg_color="#10b981", hover_color="#059669",
            text_color="#ffffff", corner_radius=6, command=self._save_snapshot
        )
        cap_btn.pack(side="right", padx=2)

        # 2. 메인 비디오 캔버스 (Zero-Flicker)
        self.canvas_frame = ctk.CTkFrame(self, fg_color="#000000", corner_radius=0)
        self.canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            self.canvas_frame, bg="#05070d",
            highlightthickness=0, cursor="hand2"
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Double-Button-1>", lambda e: self._toggle_fullscreen())
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)

        self._draw_placeholder("실물화상기 카메라에 연결 중입니다...")

    def _sep(self, parent):
        ctk.CTkFrame(parent, width=1, height=20, fg_color="#334155").pack(side="left", padx=6)

    def _draw_placeholder(self, msg: str):
        w = max(600, self.canvas.winfo_width())
        h = max(400, self.canvas.winfo_height())
        if self._canvas_text_id is None:
            self._canvas_text_id = self.canvas.create_text(
                w // 2, h // 2,
                text=msg, fill="#64748b",
                font=("Malgun Gothic", 15, "bold"), justify="center"
            )
        else:
            self.canvas.itemconfig(self._canvas_text_id, text=msg)
            self.canvas.coords(self._canvas_text_id, w // 2, h // 2)

    # ─── 카메라 탐색 & 안전 오픈 엔진 (Resource Busy 방지) ─────────────────────
    def _detect_and_start_camera(self):
        self._draw_placeholder("연결된 실물화상기 및 웹캠을 검색하는 중...")
        
        def _bg_scan():
            pnp_names = get_pnp_camera_names()
            cams = []

            # 0~9번 인덱스 (총 10개 포트) 정밀 스캔
            for i in range(10):
                opened = False
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    opened = True
                else:
                    cap.release()
                    cap = cv2.VideoCapture(i, cv2.CAP_MSMF)
                    if cap.isOpened():
                        opened = True
                    else:
                        cap.release()
                        cap = cv2.VideoCapture(i)
                        if cap.isOpened():
                            opened = True

                if opened:
                    # 센서 웜업 및 유효 프레임 체크
                    ok = False
                    for _ in range(3):
                        ret, _ = cap.read()
                        if ret:
                            ok = True
                            break
                        time.sleep(0.04)

                    cap.release()

                    friendly = pnp_names[i] if i < len(pnp_names) else f"카메라 장치 {i}"
                    cams.append((i, f"[{i}] {friendly}"))

                time.sleep(0.06)  # 드라이버 릴리즈 안전 대기

            def _apply():
                if not self.winfo_exists():
                    return
                if cams:
                    val_list = [c[1] for c in cams]
                    self.cam_combo.configure(values=val_list)
                    self.cam_combo.set(val_list[0])
                    self.current_cam_index = cams[0][0]
                else:
                    self.cam_combo.configure(values=["[0] 기본 카메라"])
                    self.cam_combo.set("[0] 기본 카메라")
                    self.current_cam_index = 0

                # 150ms 안전 대기 후 첫 카메라 자동 실행
                self.after(150, lambda: self._start_camera(self.current_cam_index))

            self.after(0, _apply)

        threading.Thread(target=_bg_scan, daemon=True).start()

    def _on_cam_changed(self, val: str):
        try:
            import re
            m = re.search(r'\[(\d+)\]', val) or re.search(r'(\d+)', val)
            if m:
                idx = int(m.group(1))
            else:
                idx = 0
            self._draw_placeholder(f"[{val}] 카메라로 전환 중입니다...")
            self.after(100, lambda: self._start_camera(idx))
        except Exception:
            pass

    def _start_camera(self, cam_index: int):
        self._stop_camera()

        self.current_cam_index = cam_index
        self.is_running = True
        self.is_frozen = False
        self.frozen_frame = None

        self.capture_thread = threading.Thread(
            target=self._capture_worker,
            args=(cam_index,),
            daemon=True
        )
        self.capture_thread.start()

    def _stop_camera(self):
        self.is_running = False
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        time.sleep(0.12)  # 핸들 해제 쿨다운

    def _capture_worker(self, cam_index: int):
        # 1단계: DirectShow 오픈 시도
        cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            time.sleep(0.1)
            # 2단계: MSMF 시도
            cap = cv2.VideoCapture(cam_index, cv2.CAP_MSMF)
            if not cap.isOpened():
                cap.release()
                time.sleep(0.1)
                # 3단계: 기본 백엔드 시도
                cap = cv2.VideoCapture(cam_index)

        if not cap.isOpened():
            self.latest_frame = None
            self.after(0, lambda: self._draw_placeholder("카메라 장치를 열 수 없습니다. 연결 상태를 확인해주세요."))
            return

        # 고화질 및 포맷 자동 협상 (MJPG ➡️ YUY2)
        try:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        except Exception:
            pass

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.cap = cap

        # 웜업 및 프레임 캡처 루프
        fail_count = 0
        while self.is_running and cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                self.latest_frame = frame
                fail_count = 0
            else:
                fail_count += 1
                if fail_count > 40:  # 2초 이상 연속 실패 시 재협상
                    try:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    except Exception:
                        pass
                    fail_count = 0
                time.sleep(0.03)
            time.sleep(0.01)

        cap.release()

    # ─── 무깜빡임(Zero-Flicker) 캔버스 렌더러 ────────────────────────────────
    def _schedule_render(self):
        if not self.winfo_exists():
            return
        self._render_frame()
        self.after(33, self._schedule_render)

    def _render_frame(self):
        frame = self.frozen_frame if self.is_frozen else self.latest_frame
        if frame is None:
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 20 or canvas_h <= 20:
            return

        img_bgr = frame.copy()

        # 1. 90도 회전
        if self.rotation_deg == 90:
            img_bgr = cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotation_deg == 180:
            img_bgr = cv2.rotate(img_bgr, cv2.ROTATE_180)
        elif self.rotation_deg == 270:
            img_bgr = cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # 2. 반전
        if self.flip_horizontal and self.flip_vertical:
            img_bgr = cv2.flip(img_bgr, -1)
        elif self.flip_horizontal:
            img_bgr = cv2.flip(img_bgr, 1)
        elif self.flip_vertical:
            img_bgr = cv2.flip(img_bgr, 0)

        # 3. 디지털 줌
        if self.zoom_level > 1.05:
            fh, fw = img_bgr.shape[:2]
            crop_w = int(fw / self.zoom_level)
            crop_h = int(fh / self.zoom_level)
            x0 = (fw - crop_w) // 2
            y0 = (fh - crop_h) // 2
            img_bgr = img_bgr[y0:y0+crop_h, x0:x0+crop_w]

        # 4. 문서 강조 모드 (고대비 흑백)
        if self.doc_mode:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            img_rgb = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
        else:
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # 5. 비율 유지 리사이즈
        ih, iw = img_rgb.shape[:2]
        scale = min(canvas_w / iw, canvas_h / ih)
        new_w = max(1, int(iw * scale))
        new_h = max(1, int(ih * scale))

        img_resized = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        pil_img = Image.fromarray(img_resized)
        self._photo_image = ImageTk.PhotoImage(pil_img)

        pos_x = canvas_w // 2
        pos_y = canvas_h // 2

        # 캔버스 텍스트 숨기기
        if self._canvas_text_id is not None:
            self.canvas.delete(self._canvas_text_id)
            self._canvas_text_id = None

        # Zero-Flicker: itemconfig 교체로 깜빡임 0
        if self._canvas_img_id is None:
            self._canvas_img_id = self.canvas.create_image(pos_x, pos_y, image=self._photo_image, anchor="center")
        else:
            self.canvas.itemconfig(self._canvas_img_id, image=self._photo_image)
            self.canvas.coords(self._canvas_img_id, pos_x, pos_y)

        # 화면 일시정지 뱃지
        if self.is_frozen:
            if self._freeze_box_id is None:
                self._freeze_box_id = self.canvas.create_rectangle(pos_x - 70, 16, pos_x + 70, 48, fill="#ea580c", outline="#fbbf24", width=2)
                self._freeze_text_id = self.canvas.create_text(pos_x, 32, text="화면 일시정지", fill="#ffffff", font=("Malgun Gothic", 12, "bold"))
            else:
                self.canvas.coords(self._freeze_box_id, pos_x - 70, 16, pos_x + 70, 48)
                self.canvas.coords(self._freeze_text_id, pos_x, 32)
                self.canvas.lift(self._freeze_box_id)
                self.canvas.lift(self._freeze_text_id)
        else:
            if self._freeze_box_id is not None:
                self.canvas.delete(self._freeze_box_id)
                self.canvas.delete(self._freeze_text_id)
                self._freeze_box_id = None
                self._freeze_text_id = None

    # ─── 컨트롤 이벤트들 ─────────────────────────────────────────────────
    def _rotate_90(self):
        self.rotation_deg = (self.rotation_deg + 90) % 360
        self.rot_btn.configure(text=f"{self.rotation_deg}° 회전")

    def _toggle_flip_h(self):
        self.flip_horizontal = not self.flip_horizontal
        self.fliph_btn.configure(fg_color="#0284c7" if self.flip_horizontal else "#334155")

    def _toggle_flip_v(self):
        self.flip_vertical = not self.flip_vertical
        self.flipv_btn.configure(fg_color="#0284c7" if self.flip_vertical else "#334155")

    def _toggle_freeze(self):
        self.is_frozen = not self.is_frozen
        if self.is_frozen:
            self.frozen_frame = self.latest_frame.copy() if self.latest_frame is not None else None
            self.freeze_btn.configure(text="정지해제", fg_color="#ea580c")
        else:
            self.frozen_frame = None
            self.freeze_btn.configure(text="화면정지", fg_color="#334155")

    def _toggle_doc_mode(self):
        self.doc_mode = not self.doc_mode
        self.doc_btn.configure(fg_color="#0284c7" if self.doc_mode else "#334155")

    def _zoom_step(self, step: float):
        self.zoom_level = round(max(1.0, min(3.0, self.zoom_level + step)), 2)
        self.zoom_lbl.configure(text=f"{self.zoom_level:.1f}x")

    def _on_mouse_wheel(self, event):
        step = 0.25 if event.delta > 0 else -0.25
        self._zoom_step(step)

    def _save_snapshot(self):
        frame = self.frozen_frame if self.is_frozen else self.latest_frame
        if frame is None:
            messagebox.showwarning("캡처 실패", "현재 캡처할 카메라 화면이 없습니다.")
            return

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"실물화상기_{now_str}.png"
        init_dir = os.path.join(os.path.expanduser("~"), "Desktop")

        path = filedialog.asksaveasfilename(
            title="실물화상기 화면 저장",
            initialdir=init_dir,
            initialfile=default_name,
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg")]
        )
        if path:
            try:
                cv2.imwrite(path, frame)
                messagebox.showinfo("저장 완료", f"화면이 성공적으로 저장되었습니다:\n{path}")
            except Exception as e:
                messagebox.showerror("저장 오류", f"저장 중 오류 발생:\n{e}")

    def _open_drawing(self):
        if self.parent_app and hasattr(self.parent_app, "_open_screen_drawing"):
            self.parent_app._open_screen_drawing()

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        self.fs_btn.configure(text="창 모드" if self.is_fullscreen else "전체화면")

    def _exit_fullscreen(self):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.attributes("-fullscreen", False)
            self.fs_btn.configure(text="전체화면")

    def close(self):
        self._stop_camera()
        VisualizerWindow._instance = None
        self.destroy()
