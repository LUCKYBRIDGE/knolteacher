"""
놀티쳐 실물화상기 (Visualizer / Document Camera)
- USB 실물화상기(BESTCAM, ELMO, AVer, IPEVO 등) 및 웹캠 실시간 고화질 스트리밍
- DirectShow 네이티브 백엔드 및 검은 화면 자동 치유(Auto-Healing)
- 90° 회전, 좌우/상하 반전, 화면 정지(Freeze), 고대비 문서 모드, 디지털 줌 (1.0x ~ 3.0x)
- 고속 캔버스 렌더러 (Zero-Flicker)
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
import numpy as np

from src.font_config import setup_global_fonts, get_font
from src.tooltip import attach_tooltip

def get_pnp_camera_names():
    """Windows PnP 장치 친화적 이름 목록 조회"""
    names = []
    if sys.platform == "win32":
        try:
            cmd = 'powershell -NoProfile -Command "Get-PnpDevice -Class Camera,Image -Status OK | Select-Object -ExpandProperty FriendlyName"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=2)
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
        self.geometry("1060x720")
        self.minsize(700, 500)
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
        # 1. 상단 컨트롤 툴바
        self.toolbar = ctk.CTkFrame(self, fg_color="#1e293b", height=52, corner_radius=0)
        self.toolbar.pack(fill="x", side="top")
        self.toolbar.pack_propagate(False)

        tb_inner = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        tb_inner.pack(fill="both", expand=True, padx=12, pady=8)

        # 카메라 선택 드롭다운
        self.cam_combo = ctk.CTkComboBox(
            tb_inner, values=["[0] 실물화상기 (BESTCAM S3)"],
            width=200, height=34, font=get_font(10, "bold"),
            command=self._on_cam_changed
        )
        self.cam_combo.pack(side="left", padx=(0, 4))
        attach_tooltip(self.cam_combo, "입력 실물화상기/카메라 선택")

        # 🔄 새로고침 / 재연결 버튼
        refresh_cam_btn = ctk.CTkButton(
            tb_inner, text="🔄 새로고침", width=80, height=34,
            font=get_font(10, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=self._reconnect_camera
        )
        refresh_cam_btn.pack(side="left", padx=(0, 4))
        attach_tooltip(refresh_cam_btn, "카메라 연결을 새로고침하고 다시 엽니다.")

        # 해상도 선택 (검은 화면 방지 호환 모드)
        self.res_combo = ctk.CTkComboBox(
            tb_inner, values=["자동 (호환 모드)", "표준 (640x480)", "고화질 (720p)", "초고화질 (1080p)"],
            width=124, height=34, font=get_font(9, "bold"), state="readonly",
            command=self._on_res_changed
        )
        self.res_combo.set("자동 (호환 모드)")
        self.res_combo.pack(side="left", padx=(0, 8))
        attach_tooltip(self.res_combo, "화상기 지원 해상도를 선택합니다. 검은 화면 시 '자동 (호환 모드)'을 선택하세요.")

        self._sep(tb_inner)

        # 90도 회전
        self.rot_btn = ctk.CTkButton(
            tb_inner, text="90° 회전", width=68, height=34,
            font=get_font(10, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=self._rotate_90
        )
        self.rot_btn.pack(side="left", padx=2)

        # 좌우 반전
        self.flip_h_btn = ctk.CTkButton(
            tb_inner, text="좌우반전", width=68, height=34,
            font=get_font(10, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=self._toggle_flip_h
        )
        self.flip_h_btn.pack(side="left", padx=2)

        # 상하 반전
        self.flip_v_btn = ctk.CTkButton(
            tb_inner, text="상하반전", width=68, height=34,
            font=get_font(10, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=self._toggle_flip_v
        )
        self.flip_v_btn.pack(side="left", padx=2)

        self._sep(tb_inner)

        # 화면 일시정지 (Freeze)
        self.freeze_btn = ctk.CTkButton(
            tb_inner, text="화면정지", width=68, height=34,
            font=get_font(10, "bold"), fg_color="#334155", hover_color="#ea580c",
            corner_radius=6, command=self._toggle_freeze
        )
        self.freeze_btn.pack(side="left", padx=2)

        # 문서 강조 모드 (흑백 고대비)
        self.doc_btn = ctk.CTkButton(
            tb_inner, text="문서강조", width=68, height=34,
            font=get_font(10, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=self._toggle_doc_mode
        )
        self.doc_btn.pack(side="left", padx=2)

        self._sep(tb_inner)

        # 디지털 줌
        ctk.CTkButton(
            tb_inner, text="-", width=28, height=34,
            font=get_font(13, "bold"), fg_color="#334155", hover_color="#475569",
            corner_radius=6, command=lambda: self._zoom_step(-0.25)
        ).pack(side="left", padx=1)

        self.zoom_lbl = ctk.CTkLabel(
            tb_inner, text="1.0x", width=42,
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
                font=("Malgun Gothic", 14, "bold"), justify="center"
            )
        else:
            self.canvas.itemconfig(self._canvas_text_id, text=msg)
            self.canvas.coords(self._canvas_text_id, w // 2, h // 2)

    # ─── 카메라 감지 & 시작 ──────────────────────────────────────────────────
    def _detect_and_start_camera(self):
        self._draw_placeholder("실물화상기(BESTCAM 등) 카메라를 연결하는 중...")
        self.discovered_cam_names = None

        # 1. 즉시 0번 카메라 연결 시작 (지연 0초)
        self.current_cam_index = 0
        self._start_camera(0)

        # 2. 비동기로 FriendlyName 조회 (순수 파이썬 변수에만 저장)
        def _fetch_names():
            try:
                pnp = get_pnp_camera_names()
                self.discovered_cam_names = pnp
            except Exception:
                pass
        threading.Thread(target=_fetch_names, daemon=True).start()

    def _reconnect_camera(self):
        self._draw_placeholder("카메라에 다시 연결하는 중입니다...")
        self._start_camera(self.current_cam_index)

    def _on_res_changed(self, val: str):
        self._reconnect_camera()

    def _on_cam_changed(self, val: str):
        try:
            import re
            m = re.search(r'\[(\d+)\]', val) or re.search(r'(\d+)', val)
            idx = int(m.group(1)) if m else 0
            self.current_cam_index = idx
            self._draw_placeholder(f"[{val}] 카메라로 전환 중입니다...")
            self._start_camera(idx)
        except Exception:
            pass

    def _start_camera(self, cam_index: int):
        self._stop_camera()

        self.current_cam_index = cam_index
        self.is_running = True
        self.is_frozen = False
        self.frozen_frame = None

        res_mode = "자동 (호환 모드)"
        if hasattr(self, "res_combo") and self.res_combo.winfo_exists():
            res_mode = self.res_combo.get()

        self.capture_thread = threading.Thread(
            target=self._capture_worker,
            args=(cam_index, res_mode),
            daemon=True
        )
        self.capture_thread.start()

    def _stop_camera(self):
        self.is_running = False
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=0.4)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        time.sleep(0.08)

    def _capture_worker(self, cam_index: int, res_mode: str = "자동 (호환 모드)"):
        # 1. DirectShow 오픈
        cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            time.sleep(0.08)
            cap = cv2.VideoCapture(cam_index)

        if not cap.isOpened():
            self.latest_frame = None
            self.status_msg = "카메라 장치를 열 수 없습니다.\nUSB 연결 상태를 확인해주세요."
            return

        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # BESTCAM S3 등 실물화상기는 640x480(VGA)에서 검은 화면 없이 선명하게 작동함
        if "1080p" in res_mode:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        elif "720p" in res_mode:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        else:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.cap = cap

        fail_count = 0
        black_count = 0
        auto_healed = False

        while self.is_running and cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                # 검은 화면(Black Frame: 평균 밝기 < 0.5) 감지 시 안전 모드(640x480) 자동 복구
                m_val = float(np.mean(frame))
                if m_val < 0.5:
                    black_count += 1
                    if black_count > 5 and not auto_healed:
                        print("[Visualizer] Black frame detected! Fallback to safe 640x480")
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        auto_healed = True
                        black_count = 0
                else:
                    black_count = 0
                    self.latest_frame = frame
                    fail_count = 0
            else:
                fail_count += 1
                time.sleep(0.02)
            time.sleep(0.01)

        cap.release()

    # ─── 무깜빡임(Zero-Flicker) 캔버스 렌더러 ────────────────────────────────
    def _schedule_render(self):
        if not self.winfo_exists():
            return
        self._render_frame()
        self.after(33, self._schedule_render)

    def _render_frame(self):
        # 1. 비동기 카메라 이름 목록 감지 시 메인 스레드에서 콤보박스 갱신
        if getattr(self, "discovered_cam_names", None):
            pnp = self.discovered_cam_names
            self.discovered_cam_names = None
            val_list = [f"[{i}] {name}" for i, name in enumerate(pnp)]
            if val_list and hasattr(self, "cam_combo") and self.cam_combo.winfo_exists():
                self.cam_combo.configure(values=val_list)
                self.cam_combo.set(val_list[0])

        # 2. 상태 메시지 표시
        if getattr(self, "status_msg", None):
            self._draw_placeholder(self.status_msg)
            self.status_msg = None

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

        # 5. 비율 유지 리사이즈 (화면 꽉 차게 고품질 스케일링)
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

    # ─── 조작 액션 ─────────────────────────────────────────────────────────
    def _rotate_90(self):
        self.rotation_deg = (self.rotation_deg + 90) % 360
        self.rot_btn.configure(text=f"{self.rotation_deg}° 회전" if self.rotation_deg else "90° 회전")

    def _toggle_flip_h(self):
        self.flip_horizontal = not self.flip_horizontal
        self.flip_h_btn.configure(fg_color="#0284c7" if self.flip_horizontal else "#334155")

    def _toggle_flip_v(self):
        self.flip_vertical = not self.flip_vertical
        self.flip_v_btn.configure(fg_color="#0284c7" if self.flip_vertical else "#334155")

    def _toggle_freeze(self):
        self.is_frozen = not self.is_frozen
        if self.is_frozen:
            self.frozen_frame = self.latest_frame.copy() if self.latest_frame is not None else None
            self.freeze_btn.configure(fg_color="#ea580c", text="정지 해제")
        else:
            self.frozen_frame = None
            self.freeze_btn.configure(fg_color="#334155", text="화면정지")

    def _toggle_doc_mode(self):
        self.doc_mode = not self.doc_mode
        self.doc_btn.configure(fg_color="#0284c7" if self.doc_mode else "#334155")

    def _zoom_step(self, delta: float):
        self.zoom_level = max(1.0, min(3.5, round(self.zoom_level + delta, 2)))
        self.zoom_lbl.configure(text=f"{self.zoom_level:.1f}x")

    def _on_mouse_wheel(self, event):
        delta = 0.2 if event.delta > 0 else -0.2
        self._zoom_step(delta)

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        if self.is_fullscreen:
            self.fs_btn.configure(text="창모드 (Esc)")
        else:
            self.fs_btn.configure(text="전체화면")

    def _exit_fullscreen(self):
        if self.is_fullscreen:
            self._toggle_fullscreen()

    def _open_drawing(self):
        from src.drawing_overlay import ScreenDrawingOverlay
        ScreenDrawingOverlay.toggle(self.parent_app or self)

    def _save_snapshot(self):
        frame = self.frozen_frame if self.is_frozen else self.latest_frame
        if frame is None:
            messagebox.showwarning("안내", "캡처할 카메라 화면이 없습니다.")
            return

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        def_path = os.path.join(os.path.expanduser("~"), "Desktop", f"실물화상기_{now_str}.png")
        file_path = filedialog.asksaveasfilename(
            parent=self, title="스냅샷 저장",
            initialfile=os.path.basename(def_path),
            initialdir=os.path.dirname(def_path),
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg")]
        )
        if file_path:
            try:
                cv2.imwrite(file_path, frame)
                messagebox.showinfo("저장 완료", f"화면이 성공적으로 저장되었습니다:\n{file_path}")
            except Exception as e:
                messagebox.showerror("저장 오류", f"저장 중 오류가 발생했습니다: {e}")

    def close(self):
        self._stop_camera()
        VisualizerWindow._instance = None
        self.destroy()
