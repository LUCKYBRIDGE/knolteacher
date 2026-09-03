import os
import sys
import time
import threading
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk, ImageEnhance
import cv2

from src.font_config import setup_global_fonts, get_font
from src.tooltip import attach_tooltip


class VisualizerWindow(ctk.CTkToplevel):
    """
    놀티쳐 데스크 실물화상기 (Visualizer / Document Camera)
    - 컴퓨터/웹캠/외장 USB 실물화상기 실시간 고화질 스트리밍
    - 90° 회전, 좌우/상하 반전, 화면 정지(Freeze)
    - 문서 명암 강조(흑백 텍스트 모드), 디지털 줌 (1.0x ~ 3.0x)
    - 고화질 스냅샷 캡처 및 화면 위 즉각 판서 연동
    - F11 전체화면 및 듀얼 모니터 완벽 지원
    """
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
        self.title("놀티쳐 실물화상기")
        self.geometry("1000x680")
        self.minsize(640, 440)
        self.configure(fg_color="#090d16")

        setup_global_fonts(self)
        self._load_icon()

        # 카메라 및 스트리밍 상태
        self.cap = None
        self.current_cam_index = 0
        self.is_running = False
        self.is_frozen = False
        self.latest_frame = None        # cv2 BGR frame
        self.frozen_frame = None        # freeze 시 보관 frame
        self.capture_thread = None

        # 화면 변환 설정
        self.rotation_deg = 0          # 0, 90, 180, 270
        self.flip_horizontal = False    # 좌우 반전
        self.flip_vertical = False      # 상하 반전
        self.doc_mode = False           # 흑백/고대비 문서 모드
        self.sharp_mode = False         # 소프트웨어 선명화 필터
        self.zoom_level = 1.0           # 1.0x ~ 3.0x
        self.is_fullscreen = False

        # 초점 제어 상태
        self.is_autofocus = True
        self.manual_focus_val = 50

        # 포토이미지 보관 (GC 방지)
        self._photo_image = None
        self._last_w = 0
        self._last_h = 0

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._exit_fullscreen())

        self._build_ui()
        self._detect_cameras()
        self._start_camera(self.current_cam_index)
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
        # 1. 상단 컨트롤 툴바
        self.toolbar = ctk.CTkFrame(self, fg_color="#111827", height=52, corner_radius=0)
        self.toolbar.pack(fill="x", side="top")
        self.toolbar.pack_propagate(False)

        tb_inner = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        tb_inner.pack(fill="both", expand=True, padx=12, pady=8)

        # 카메라 선택 드롭다운
        self.cam_combo = ctk.CTkComboBox(
            tb_inner, values=["카메라 0 (기본)"],
            width=140, height=32, font=get_font(11),
            command=self._on_cam_changed
        )
        self.cam_combo.pack(side="left", padx=(0, 4))
        attach_tooltip(self.cam_combo, "입력 카메라/실물화상기 디바이스 선택")

        refresh_cam_btn = ctk.CTkButton(
            tb_inner, text="🔄", width=32, height=32,
            font=get_font(11), fg_color="#1e293b", hover_color="#334155",
            corner_radius=6, command=self._detect_cameras
        )
        refresh_cam_btn.pack(side="left", padx=(0, 8))
        attach_tooltip(refresh_cam_btn, "연결된 카메라 목록 새로고침")

        self._sep(tb_inner)

        # 화면 회전 및 반전
        self.rot_btn = ctk.CTkButton(
            tb_inner, text="⟳ 0°", width=54, height=32,
            font=get_font(11, "bold"), fg_color="#1e293b", hover_color="#334155",
            corner_radius=6, command=self._rotate_90
        )
        self.rot_btn.pack(side="left", padx=2)
        attach_tooltip(self.rot_btn, "화면 90도 회전 (0° → 90° → 180° → 270°)")

        self.flip_h_btn = ctk.CTkButton(
            tb_inner, text="↔ 좌우", width=52, height=32,
            font=get_font(10, "bold"), fg_color="#1e293b", hover_color="#334155",
            corner_radius=6, command=self._toggle_flip_h
        )
        self.flip_h_btn.pack(side="left", padx=2)
        attach_tooltip(self.flip_h_btn, "화면 좌우 반전 (미러링)")

        self.flip_v_btn = ctk.CTkButton(
            tb_inner, text="↕ 상하", width=52, height=32,
            font=get_font(10, "bold"), fg_color="#1e293b", hover_color="#334155",
            corner_radius=6, command=self._toggle_flip_v
        )
        self.flip_v_btn.pack(side="left", padx=2)
        attach_tooltip(self.flip_v_btn, "화면 상하 반전 (거꾸로 설치된 카메라용)")

        self._sep(tb_inner)

        # 초점 제어 (자동초점 토글 + 수동초점 슬라이더)
        self.af_btn = ctk.CTkButton(
            tb_inner, text="⚡ AF자동", width=70, height=32,
            font=get_font(10, "bold"), fg_color="#059669", hover_color="#047857",
            corner_radius=6, command=self._toggle_autofocus
        )
        self.af_btn.pack(side="left", padx=2)
        attach_tooltip(self.af_btn, "카메라 하드웨어 자동초점(AF) 켜기 / 수동초점 전환")

        focus_box = ctk.CTkFrame(tb_inner, fg_color="transparent")
        focus_box.pack(side="left", padx=2)
        ctk.CTkLabel(focus_box, text="초점", font=get_font(10), text_color="#94a3b8").pack(side="left", padx=(2, 4))

        self.focus_slider = ctk.CTkSlider(
            focus_box, from_=0, to=255, number_of_steps=51,
            width=80, height=16, command=self._on_focus_slider_changed
        )
        self.focus_slider.set(50)
        self.focus_slider.pack(side="left")
        self.focus_slider.configure(state="disabled")
        attach_tooltip(self.focus_slider, "수동 초점 미세 조절 슬라이더 (AF 해제 시 사용)")

        # 소프트웨어 선명화
        self.sharp_btn = ctk.CTkButton(
            tb_inner, text="✨ 선명화", width=62, height=32,
            font=get_font(10, "bold"), fg_color="#1e293b", hover_color="#334155",
            corner_radius=6, command=self._toggle_sharp_mode
        )
        self.sharp_btn.pack(side="left", padx=2)
        attach_tooltip(self.sharp_btn, "학습지/교재 글씨 윤곽선을 또렷하게 선명화")

        self._sep(tb_inner)

        # 정지 (Freeze)
        self.freeze_btn = ctk.CTkButton(
            tb_inner, text="❄️ 화면정지", width=80, height=32,
            font=get_font(11, "bold"), fg_color="#1e293b", hover_color="#0284c7",
            corner_radius=6, command=self._toggle_freeze
        )
        self.freeze_btn.pack(side="left", padx=2)
        attach_tooltip(self.freeze_btn, "화면 일시정지 (화면 동결하여 손을 치우고 설명)")

        # 문서/학습지 모드
        self.doc_btn = ctk.CTkButton(
            tb_inner, text="📄 문서강조", width=76, height=32,
            font=get_font(10, "bold"), fg_color="#1e293b", hover_color="#059669",
            corner_radius=6, command=self._toggle_doc_mode
        )
        self.doc_btn.pack(side="left", padx=2)
        attach_tooltip(self.doc_btn, "시험지/교재 글씨를 또렷하게 고대비 흑백 강조")

        self._sep(tb_inner)

        # 줌 컨트롤 (A- / 배율 / A+)
        ctk.CTkButton(
            tb_inner, text="−", width=28, height=32,
            font=get_font(13, "bold"), fg_color="#1e293b", hover_color="#334155",
            corner_radius=6, command=lambda: self._zoom_step(-0.25)
        ).pack(side="left", padx=1)

        self.zoom_lbl = ctk.CTkLabel(
            tb_inner, text="1.0x", width=42,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color="#38bdf8"
        )
        self.zoom_lbl.pack(side="left", padx=1)

        ctk.CTkButton(
            tb_inner, text="+", width=28, height=32,
            font=get_font(13, "bold"), fg_color="#1e293b", hover_color="#334155",
            corner_radius=6, command=lambda: self._zoom_step(0.25)
        ).pack(side="left", padx=1)

        self._sep(tb_inner)

        # 우측 기능 그룹
        right_box = ctk.CTkFrame(tb_inner, fg_color="transparent")
        right_box.pack(side="right")

        # 닫기
        ctk.CTkButton(
            right_box, text="✕", width=32, height=32,
            font=get_font(12, "bold"), fg_color="#3f1d24", hover_color="#dc2626",
            text_color="#fca5a5", corner_radius=6, command=self.close
        ).pack(side="right", padx=(2, 0))

        # 전체화면
        self.fs_btn = ctk.CTkButton(
            right_box, text="⛶", width=32, height=32,
            font=get_font(12), fg_color="#1e293b", hover_color="#334155",
            corner_radius=6, command=self._toggle_fullscreen
        )
        self.fs_btn.pack(side="right", padx=2)
        attach_tooltip(self.fs_btn, "전체화면 토글 (F11)")

        # 판서 연동
        draw_btn = ctk.CTkButton(
            right_box, text="✏️ 화면판서", width=80, height=32,
            font=get_font(11, "bold"), fg_color="#0284c7", hover_color="#0369a1",
            corner_radius=6, command=self._open_drawing
        )
        draw_btn.pack(side="right", padx=3)
        attach_tooltip(draw_btn, "실물화상기 화면 위에 자유 판서 시작")

        # 스냅샷 캡처
        cap_btn = ctk.CTkButton(
            right_box, text="📸 캡처저장", width=80, height=32,
            font=get_font(11, "bold"), fg_color="#059669", hover_color="#047857",
            corner_radius=6, command=self._save_snapshot
        )
        cap_btn.pack(side="right", padx=3)
        attach_tooltip(cap_btn, "현재 실물화상기 화면 고화질 이미지 저장")

        # 2. 메인 비디오 캔버스
        self.canvas_frame = ctk.CTkFrame(self, fg_color="#000000", corner_radius=0)
        self.canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            self.canvas_frame, bg="#05070d",
            highlightthickness=0, cursor="hand2"
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Double-Button-1>", lambda e: self._toggle_fullscreen())
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)

        # 대기 상태 메시지
        self._draw_placeholder("카메라를 연결하고 시작하는 중...")

    def _sep(self, parent):
        ctk.CTkFrame(parent, width=1, height=20, fg_color="#334155").pack(side="left", padx=5)

    def _draw_placeholder(self, msg: str):
        self.canvas.delete("all")
        w = max(600, self.canvas.winfo_width())
        h = max(400, self.canvas.winfo_height())
        self.canvas.create_text(
            w // 2, h // 2,
            text=f"📷 {msg}",
            fill="#64748b",
            font=("Malgun Gothic", 16, "bold"),
            justify="center"
        )

    # ─── 카메라 탐색 & 스레드 ─────────────────────────────────────────────
    def _detect_cameras(self):
        cams = []
        for i in range(4):
            # DirectShow로 빠른 체크
            temp_cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if temp_cap.isOpened():
                ret, _ = temp_cap.read()
                if ret:
                    cams.append(f"카메라 {i}" + (" (기본)" if i == 0 else ""))
                temp_cap.release()
            else:
                temp_cap.release()

        if not cams:
            cams = ["카메라 0 (기본)"]

        self.cam_combo.configure(values=cams)
        self.cam_combo.set(cams[0])

    def _on_cam_changed(self, val: str):
        try:
            # "카메라 1 ..." 에서 숫자 추출
            idx_str = val.split()[1]
            idx = int(idx_str)
            self._start_camera(idx)
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

    def _capture_worker(self, cam_index: int):
        # 1. DirectShow 우선 시도, 실패 시 기본 백엔드
        cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(cam_index)

        if not cap.isOpened():
            self.latest_frame = None
            return

        # 고화질 시도 (1920x1080 -> 실패 시 카메라가 지원하는 최고 해상도로 fallback)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.cap = cap

        while self.is_running and cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                self.latest_frame = frame
            else:
                time.sleep(0.03)
            time.sleep(0.01)

        cap.release()

    # ─── 렌더링 루프 ──────────────────────────────────────────────────────
    def _schedule_render(self):
        if not self.winfo_exists():
            return

        self._render_frame()
        # 약 30 FPS로 부드럽게 재생
        self.after(33, self._schedule_render)

    def _render_frame(self):
        # 정지 모드일 때는 동결된 프레임 사용
        frame = self.frozen_frame if self.is_frozen else self.latest_frame
        if frame is None:
            return

        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 10 or canvas_h <= 10:
            return

        # 프레임 복사 및 가공
        img_bgr = frame.copy()

        # 1. 회전
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

        # 3. 디지털 줌 (중앙 크롭)
        if self.zoom_level > 1.05:
            fh, fw = img_bgr.shape[:2]
            crop_w = int(fw / self.zoom_level)
            crop_h = int(fh / self.zoom_level)
            x0 = (fw - crop_w) // 2
            y0 = (fh - crop_h) // 2
            img_bgr = img_bgr[y0:y0+crop_h, x0:x0+crop_w]

        # 4. 소프트웨어 선명화 (샤프닝)
        if self.sharp_mode:
            import numpy as np
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
            img_bgr = cv2.filter2D(img_bgr, -1, kernel)

        # 5. 문서 강조 모드 (고대비 흑백)
        if self.doc_mode:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            # 적응형 대비 향상
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            img_rgb = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
        else:
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # 5. 비율 유지 리사이즈 (Letterbox)
        ih, iw = img_rgb.shape[:2]
        scale = min(canvas_w / iw, canvas_h / ih)
        new_w = max(1, int(iw * scale))
        new_h = max(1, int(ih * scale))

        img_resized = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        pil_img = Image.fromarray(img_resized)

        self._photo_image = ImageTk.PhotoImage(pil_img)

        # 캔버스 중앙 정렬
        self.canvas.delete("all")
        pos_x = canvas_w // 2
        pos_y = canvas_h // 2
        self.canvas.create_image(pos_x, pos_y, image=self._photo_image, anchor="center")

        # 화면 정지 뱃지 표시
        if self.is_frozen:
            self.canvas.create_rectangle(
                pos_x - 70, 16, pos_x + 70, 48,
                fill="#ea580c", outline="#fbbf24", width=2
            )
            self.canvas.create_text(
                pos_x, 32,
                text="❄️ 화면 일시정지",
                fill="#ffffff",
                font=("Malgun Gothic", 12, "bold")
            )

    # ─── 컨트롤 이벤트 ───────────────────────────────────────────────────
    def _rotate_90(self):
        self.rotation_deg = (self.rotation_deg + 90) % 360
        self.rot_btn.configure(text=f"⟳ {self.rotation_deg}°")

    def _toggle_flip_h(self):
        self.flip_horizontal = not self.flip_horizontal
        self.flip_h_btn.configure(
            fg_color="#0284c7" if self.flip_horizontal else "#1e293b"
        )

    def _toggle_flip_v(self):
        self.flip_vertical = not self.flip_vertical
        self.flip_v_btn.configure(
            fg_color="#0284c7" if self.flip_vertical else "#1e293b"
        )

    def _toggle_autofocus(self):
        self.is_autofocus = not self.is_autofocus
        if self.is_autofocus:
            self.af_btn.configure(text="⚡ AF자동", fg_color="#059669")
            self.focus_slider.configure(state="disabled")
            if self.cap:
                try:
                    self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                except Exception:
                    pass
        else:
            self.af_btn.configure(text="🎯 수동초점", fg_color="#ea580c")
            self.focus_slider.configure(state="normal")
            val = float(self.focus_slider.get())
            if self.cap:
                try:
                    self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                    self.cap.set(cv2.CAP_PROP_FOCUS, val)
                except Exception:
                    pass

    def _on_focus_slider_changed(self, val):
        if not self.is_autofocus and self.cap:
            try:
                self.cap.set(cv2.CAP_PROP_FOCUS, float(val))
            except Exception:
                pass

    def _toggle_sharp_mode(self):
        self.sharp_mode = not self.sharp_mode
        self.sharp_btn.configure(
            fg_color="#0284c7" if self.sharp_mode else "#1e293b",
            text="✨ 선명ON" if self.sharp_mode else "✨ 선명화"
        )

    def _toggle_freeze(self):
        self.is_frozen = not self.is_frozen
        if self.is_frozen:
            # 현재 최신 프레임 고정
            self.frozen_frame = self.latest_frame.copy() if self.latest_frame is not None else None
            self.freeze_btn.configure(
                text="▶ 재생", fg_color="#ea580c", hover_color="#c2410c"
            )
        else:
            self.frozen_frame = None
            self.freeze_btn.configure(
                text="❄️ 화면정지", fg_color="#1e293b", hover_color="#0284c7"
            )

    def _toggle_doc_mode(self):
        self.doc_mode = not self.doc_mode
        self.doc_btn.configure(
            fg_color="#059669" if self.doc_mode else "#1e293b",
            text="📄 문서ON" if self.doc_mode else "📄 문서강조"
        )

    def _zoom_step(self, delta: float):
        self.zoom_level = max(1.0, min(3.0, round(self.zoom_level + delta, 2)))
        self.zoom_lbl.configure(text=f"{self.zoom_level:.1f}x")

    def _on_mouse_wheel(self, event):
        delta = 0.15 if event.delta > 0 else -0.15
        self._zoom_step(delta)

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        if self.is_fullscreen:
            self.toolbar.pack_forget()
            self.fs_btn.configure(text="🗗")
        else:
            self.toolbar.pack(fill="x", side="top", before=self.canvas_frame)
            self.fs_btn.configure(text="⛶")

    def _exit_fullscreen(self):
        if self.is_fullscreen:
            self._toggle_fullscreen()

    def _save_snapshot(self):
        frame = self.frozen_frame if self.is_frozen else self.latest_frame
        if frame is None:
            messagebox.showwarning("안내", "저장할 카메라 화면이 없습니다.")
            return

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_fn = f"놀티쳐_실물화상기_{now_str}.png"
        path = filedialog.asksaveasfilename(
            title="실물화상기 스냅샷 저장",
            initialfile=default_fn,
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPG Image", "*.jpg"), ("All Files", "*.*")]
        )
        if not path:
            return

        try:
            # 현재 회전/반전 적용한 상태로 저장
            save_img = frame.copy()
            if self.rotation_deg == 90:
                save_img = cv2.rotate(save_img, cv2.ROTATE_90_CLOCKWISE)
            elif self.rotation_deg == 180:
                save_img = cv2.rotate(save_img, cv2.ROTATE_180)
            elif self.rotation_deg == 270:
                save_img = cv2.rotate(save_img, cv2.ROTATE_90_COUNTERCLOCKWISE)

            if self.flip_horizontal and self.flip_vertical:
                save_img = cv2.flip(save_img, -1)
            elif self.flip_horizontal:
                save_img = cv2.flip(save_img, 1)
            elif self.flip_vertical:
                save_img = cv2.flip(save_img, 0)

            # 한글 경로 지원을 위해 cv2.imencode 사용
            ext = os.path.splitext(path)[1].lower()
            if ext in [".jpg", ".jpeg"]:
                ok, enc = cv2.imencode(".jpg", save_img)
            else:
                ok, enc = cv2.imencode(".png", save_img)

            if ok:
                with open(path, "wb") as f:
                    f.write(enc.tobytes())
                messagebox.showinfo("저장 완료", f"스냅샷이 저장되었습니다:\n{path}")
        except Exception as e:
            messagebox.showerror("저장 실패", f"스냅샷 저장 중 오류 발생:\n{e}")

    def _open_drawing(self):
        """현재 화면 위에 전체화면 판서 오버레이 즉각 호출"""
        from src.drawing_overlay import ScreenDrawingOverlay
        ScreenDrawingOverlay.get_instance(self).show()

    def close(self):
        self._stop_camera()
        try:
            self.destroy()
        except Exception:
            pass
        VisualizerWindow._instance = None
