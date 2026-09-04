import os
import io
import sys
import json
import ctypes
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageGrab
from src.config_utils import get_config_dir


class ScreenSnipOverlay(tk.Toplevel):
    """
    Alt+6: 영역 화면 캡처 (스마트 스니핑)
    - 반투명 어두운 화면 위에서 마우스 드래그로 영역 선택
    - 드래그 완료 즉시 Windows 클립보드에 초고속 복사 (한글/PPT/카톡에 Ctrl+V)
    - 설정(ask_save_file)에 따라 파일 저장 대화상자 팝업 지원
    - ESC 누르면 캡처 취소
    """
    _instance = None
    CONFIG_FILE = os.path.join(get_config_dir(), "snip_config.json")

    @classmethod
    def start_snip(cls):
        if cls._instance and cls._instance.winfo_exists():
            cls._instance.destroy()
        cls._instance = cls()

    @classmethod
    def is_save_to_file_enabled(cls) -> bool:
        if os.path.exists(cls.CONFIG_FILE):
            try:
                with open(cls.CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f).get("ask_save_file", False)
            except Exception:
                pass
        return False

    @classmethod
    def set_save_to_file_enabled(cls, enabled: bool):
        try:
            with open(cls.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"ask_save_file": enabled}, f)
        except Exception:
            pass

    def __init__(self):
        super().__init__()
        self.title("화면 캡처")
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.config(cursor="crosshair")

        self.sw = self.winfo_screenwidth()
        self.sh = self.winfo_screenheight()

        # 1. 전체 화면 캡처
        self.original_img = ImageGrab.grab()

        # 2. 50% 어두운 오버레이 배경 생성
        dark_img = Image.new("RGB", self.original_img.size, (20, 25, 35))
        self.dimmed_img = Image.blend(self.original_img, dark_img, 0.55)
        self.dimmed_photo = ImageTk.PhotoImage(self.dimmed_img)

        self.canvas = tk.Canvas(self, bg="#000000", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, image=self.dimmed_photo, anchor="nw")

        # 드래그 좌표
        self.start_x = 0
        self.start_y = 0
        self.rect_id = None
        self.guide_text_id = None

        # 안내 텍스트 표시
        self.canvas.create_text(
            self.sw // 2, 40,
            text="마우스를 드래그하여 캡처할 영역을 선택하세요. [ESC] 취소",
            fill="#38bdf8", font=("Malgun Gothic", 13, "bold"),
            tags="guide"
        )

        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.bind("<Escape>", lambda e: self.destroy())

    def _on_mouse_down(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.canvas.delete("guide")

    def _on_mouse_move(self, event):
        x0 = min(self.start_x, event.x)
        y0 = min(self.start_y, event.y)
        x1 = max(self.start_x, event.x)
        y1 = max(self.start_y, event.y)

        if self.rect_id:
            self.canvas.delete(self.rect_id)
        if self.guide_text_id:
            self.canvas.delete(self.guide_text_id)

        # 선택 영역 테두리
        self.rect_id = self.canvas.create_rectangle(
            x0, y0, x1, y1,
            outline="#38bdf8", width=2
        )

        # 크기 뱃지
        w = x1 - x0
        h = y1 - y0
        self.guide_text_id = self.canvas.create_text(
            x0 + 4, max(16, y0 - 12),
            text=f"{w} × {h}", fill="#38bdf8", font=("Consolas", 10, "bold"),
            anchor="w"
        )

    def _on_mouse_up(self, event):
        x0 = min(self.start_x, event.x)
        y0 = min(self.start_y, event.y)
        x1 = max(self.start_x, event.x)
        y1 = max(self.start_y, event.y)

        # 창 닫기
        self.destroy()
        ScreenSnipOverlay._instance = None

        # 너무 작으면 무시 (오클릭 방지)
        if (x1 - x0) < 10 or (y1 - y0) < 10:
            return

        cropped = self.original_img.crop((x0, y0, x1, y1))

        # 1. 클립보드에 복사 (초고속)
        self._copy_to_clipboard(cropped)

        # 2. 파일 저장 설정이 켜져 있는 경우 팝업
        if self.is_save_to_file_enabled():
            self._prompt_file_save(cropped)

    @classmethod
    def _copy_to_clipboard(cls, pil_img: Image.Image):
        """Pillow 이미지를 Windows 클립보드에 CF_DIB로 직접 복사"""
        try:
            output = io.BytesIO()
            pil_img.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]  # BMP 헤더(14 bytes) 제거 후 DIB 추출
            output.close()

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            user32.OpenClipboard(None)
            user32.EmptyClipboard()

            hCd = kernel32.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
            pchData = kernel32.GlobalLock(hCd)
            ctypes.cdll.msvcrt.memcpy(pchData, data, len(data))
            kernel32.GlobalUnlock(hCd)

            user32.SetClipboardData(8, hCd)  # CF_DIB = 8
            user32.CloseClipboard()
        except Exception:
            pass

    @classmethod
    def _prompt_file_save(cls, pil_img: Image.Image):
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        save_path = filedialog.asksaveasfilename(
            parent=root,
            title="캡처 이미지 저장",
            initialfile=f"놀티쳐_캡처_{now_str}.png",
            defaultextension=".png",
            filetypes=[("PNG 이미지", "*.png"), ("JPG 이미지", "*.jpg"), ("모든 파일", "*.*")]
        )
        root.destroy()

        if save_path:
            try:
                pil_img.save(save_path)
            except Exception as e:
                messagebox.showerror("저장 실패", f"오류 발생: {e}")
