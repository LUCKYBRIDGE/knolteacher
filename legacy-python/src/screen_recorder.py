import os
import sys
import time
import shutil
import tempfile
import datetime
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import cv2
import numpy as np
from PIL import ImageGrab
from src.font_config import get_font


class ScreenRecorderController:
    """
    Alt+5: 현재 화면 작업 녹화 (시작 / 종료 및 저장)
    - Alt+5 누르면 녹화 시작 (화면 우상단 🔴 REC 뱃지)
    - 다시 Alt+5 또는 ESC 누르면 녹화 종료
    - 녹화 종료 후 파일 저장 대화상자(MP4/AVI) 팝업
    """
    is_recording = False
    _thread = None
    _badge = None
    _temp_filepath = None
    _stop_event = threading.Event()
    _start_time = 0

    @classmethod
    def toggle(cls):
        if cls.is_recording:
            cls.stop_and_save()
        else:
            cls.start()

    @classmethod
    def start(cls):
        if cls.is_recording:
            return
        cls.is_recording = True
        cls._stop_event.clear()
        cls._start_time = time.time()

        # 임시 비디오 파일 생성
        temp_dir = tempfile.gettempdir()
        cls._temp_filepath = os.path.join(temp_dir, f"knol_rec_{int(time.time())}.avi")

        # 플로팅 REC 뱃지 띄우기
        cls._show_badge()

        # 백그라운드 녹화 스레드 시작
        cls._thread = threading.Thread(target=cls._record_worker, daemon=True)
        cls._thread.start()

    @classmethod
    def _show_badge(cls):
        try:
            badge = tk.Toplevel()
            badge.title("녹화 중")
            badge.attributes("-topmost", True)
            badge.overrideredirect(True)
            badge.configure(bg="#090d16")

            sw = badge.winfo_screenwidth()
            badge.geometry(f"140x36+{sw - 160}+20")

            frame = tk.Frame(badge, bg="#090d16", highlightbackground="#ef4444", highlightthickness=2)
            frame.pack(fill="both", expand=True)

            lbl = tk.Label(frame, text="🔴 REC 00:00", font=("Consolas", 11, "bold"), fg="#ef4444", bg="#090d16")
            lbl.pack(expand=True)

            cls._badge = badge
            cls._badge_lbl = lbl
            cls._update_badge_time()
        except Exception:
            pass

    @classmethod
    def _update_badge_time(cls):
        if not cls.is_recording or not cls._badge or not cls._badge.winfo_exists():
            return
        elapsed = int(time.time() - cls._start_time)
        m, s = divmod(elapsed, 60)
        # 빨간 원 깜빡임 효과
        dot = "🔴" if elapsed % 2 == 0 else "⚪"
        cls._badge_lbl.config(text=f"{dot} REC {m:02d}:{s:02d}")
        cls._badge.after(500, cls._update_badge_time)

    @classmethod
    def _record_worker(cls):
        # 첫 프레임으로 크기 확인
        sample = ImageGrab.grab()
        w, h = sample.size

        # XVID 코덱 AVI (가장 호환성 높고 빠른 인코딩)
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        fps = 15.0
        out = cv2.VideoWriter(cls._temp_filepath, fourcc, fps, (w, h))

        frame_duration = 1.0 / fps

        while not cls._stop_event.is_set():
            t0 = time.time()
            img = ImageGrab.grab()
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            out.write(frame)

            spent = time.time() - t0
            sleep_t = frame_duration - spent
            if sleep_t > 0:
                time.sleep(sleep_t)

        out.release()

    @classmethod
    def stop_and_save(cls):
        if not cls.is_recording:
            return
        cls.is_recording = False
        cls._stop_event.set()

        # 뱃지 제거
        if cls._badge:
            try:
                cls._badge.destroy()
            except Exception:
                pass
            cls._badge = None

        if cls._thread:
            cls._thread.join(timeout=2.0)
            cls._thread = None

        # 파일 저장 다이얼로그 팝업
        cls._prompt_save()

    @classmethod
    def _prompt_save(cls):
        if not cls._temp_filepath or not os.path.exists(cls._temp_filepath):
            return

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_fn = f"놀티쳐_화면녹화_{now_str}.avi"

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        save_path = filedialog.asksaveasfilename(
            parent=root,
            title="화면 녹화 영상 저장",
            initialfile=default_fn,
            defaultextension=".avi",
            filetypes=[("AVI 동영상", "*.avi"), ("MP4 동영상", "*.mp4"), ("모든 파일", "*.*")]
        )
        root.destroy()

        if save_path:
            try:
                shutil.copy2(cls._temp_filepath, save_path)
                messagebox.showinfo("저장 완료", f"녹화 영상이 안전하게 저장되었습니다:\n{save_path}")
            except Exception as e:
                messagebox.showerror("저장 실패", f"파일 저장 중 오류가 발생했습니다:\n{e}")

        # 임시 파일 정리
        try:
            if os.path.exists(cls._temp_filepath):
                os.remove(cls._temp_filepath)
        except Exception:
            pass
        cls._temp_filepath = None
