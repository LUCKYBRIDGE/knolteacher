import os
import sys
import ctypes
import tkinter as tk
from PIL import Image, ImageTk, ImageGrab


class ScreenMagnifierWindow(tk.Toplevel):
    """
    Alt+1: 정지 화면 돋보기 확대기 (ZoomIt 스타일)
    - 현재 화면을 즉시 일시정지 캡처하여 2.0x 확대 표시
    - 마우스 커서 위치를 따라 자연스럽게 패닝
    - 마우스 휠로 1.2x ~ 5.0x 확대 배율 조절
    - ESC 또는 Alt+1 누르면 즉시 닫힘
    """
    _instance = None

    @classmethod
    def toggle(cls):
        if cls._instance and cls._instance.winfo_exists():
            cls._instance.close()
        else:
            cls._instance = cls()

    def __init__(self):
        super().__init__()
        self.title("화면 확대기")
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.config(cursor="crosshair")

        self.sw = self.winfo_screenwidth()
        self.sh = self.winfo_screenheight()

        # 현재 화면 캡처
        self.original_img = ImageGrab.grab()
        self.zoom_level = 2.0
        self._photo_cache = None

        self.canvas = tk.Canvas(self, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.bind("<Escape>", lambda e: self.close())
        self.bind("<Button-1>", lambda e: self.close())
        self.bind("<Button-3>", lambda e: self.close())
        self.bind("<Motion>", self._on_mouse_move)
        self.bind("<MouseWheel>", self._on_wheel)

        self.cur_mx = self.sw // 2
        self.cur_my = self.sh // 2
        self._render_zoomed(self.cur_mx, self.cur_my)

    def _on_mouse_move(self, event):
        self.cur_mx = event.x
        self.cur_my = event.y
        self._render_zoomed(event.x, event.y)

    def _on_wheel(self, event):
        if event.delta > 0:
            self.zoom_level = min(5.0, round(self.zoom_level + 0.25, 2))
        else:
            self.zoom_level = max(1.2, round(self.zoom_level - 0.25, 2))
        self._render_zoomed(self.cur_mx, self.cur_my)

    def _render_zoomed(self, mx, my):
        # 마우스 위치(mx, my)를 중심으로 확대 영역(crop) 계산
        crop_w = int(self.sw / self.zoom_level)
        crop_h = int(self.sh / self.zoom_level)

        x0 = max(0, min(self.sw - crop_w, mx - crop_w // 2))
        y0 = max(0, min(self.sh - crop_h, my - crop_h // 2))

        cropped = self.original_img.crop((x0, y0, x0 + crop_w, y0 + crop_h))
        zoomed = cropped.resize((self.sw, self.sh), Image.BILINEAR)

        self._photo_cache = ImageTk.PhotoImage(zoomed)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self._photo_cache, anchor="nw")

        # 상단 우측에 자그마한 배율 표시
        self.canvas.create_rectangle(
            self.sw - 110, 20, self.sw - 20, 50,
            fill="#090d16", outline="#38bdf8", width=1
        )
        self.canvas.create_text(
            self.sw - 65, 35,
            text=f"{self.zoom_level:.1f}x (ESC 해제)",
            fill="#38bdf8",
            font=("Malgun Gothic", 10, "bold")
        )

    def close(self):
        try:
            self.destroy()
        except Exception:
            pass
        ScreenMagnifierWindow._instance = None


class LiveZoomController:
    """
    Alt+4: 라이브 줌 (LiveZoom)
    - 화면이 확대된 상태에서 마우스 클릭, 텍스트 입력 등의 평소 컴퓨터 기능 그대로 사용 가능
    - Windows 내장 정품 배율기(Magnifier)를 프로그래밍 방식으로 실행/해제
    - ESC 또는 Alt+4를 다시 누르면 해제
    """
    is_active = False

    @classmethod
    def toggle(cls):
        if cls.is_active:
            cls.stop()
        else:
            cls.start()

    @classmethod
    def start(cls):
        cls.is_active = True
        try:
            # Win + Plus 키를 2번 전송하여 화면 확대 시작
            VK_LWIN = 0x5B
            VK_OEM_PLUS = 0xBB
            KEYEVENTF_KEYUP = 0x0002

            # Win 누름
            ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
            # Plus 누름 & 뗌
            ctypes.windll.user32.keybd_event(VK_OEM_PLUS, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_OEM_PLUS, 0, KEYEVENTF_KEYUP, 0)
            # Win 뗌
            ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        except Exception as e:
            # 폴백: magnify.exe 직접 실행
            import subprocess
            subprocess.Popen("magnify.exe", shell=True)

    @classmethod
    def stop(cls):
        cls.is_active = False
        try:
            # Win + Esc 키를 전송하여 Windows 돋보기 종료
            VK_LWIN = 0x5B
            VK_ESCAPE = 0x1B
            KEYEVENTF_KEYUP = 0x0002

            ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_ESCAPE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_ESCAPE, 0, KEYEVENTF_KEYUP, 0)
            ctypes.windll.user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
        except Exception:
            import subprocess
            subprocess.run("taskkill /f /im magnify.exe", shell=True, check=False)
