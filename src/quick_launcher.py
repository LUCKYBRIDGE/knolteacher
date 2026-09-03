"""
놀티쳐 (KnolTeacher) - 자주 실행하는 프로그램 및 바로가기 매니저 (Quick Launcher)
- 교사 전용 맞춤 프로그램/문서/웹사이트 바로가기 등록 & 원클릭 실행
- 파일 탐색기(.exe, .lnk, .hwp, .pdf, .pptx 등) 및 URL 웹링크 완벽 지원
- 플로팅 툴바, 바탕화면 글래스 위젯, 학생 공유 화면과 완벽 연동
"""

import os
import sys
import json
import uuid
import webbrowser
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from src.config_utils import get_config_dir
from src.font_config import get_font
from src.tooltip import attach_tooltip
from src.icon_renderer import get_icon, COL_MAIN, COL_ACTIVE, COL_ORANGE, COL_GREEN


class QuickLauncherManager:
    _instance = None
    CONFIG_FILE = os.path.join(get_config_dir(), "quick_shortcuts.json")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.shortcuts = []
        self._load()

    def _get_default_presets(self):
        return [
            {
                "id": "calc",
                "name": "계산기",
                "target": "calc.exe",
                "type": "app",
                "emoji": "🧮"
            },
            {
                "id": "notepad",
                "name": "메모장",
                "target": "notepad.exe",
                "type": "app",
                "emoji": "📝"
            },
            {
                "id": "paint",
                "name": "그림판",
                "target": "mspaint.exe",
                "type": "app",
                "emoji": "🎨"
            },
            {
                "id": "indischool",
                "name": "인디스쿨",
                "target": "https://www.indischool.com",
                "type": "url",
                "emoji": "🏫"
            },
            {
                "id": "iscream",
                "name": "아이스크림",
                "target": "https://www.i-scream.co.kr",
                "type": "url",
                "emoji": "🍦"
            }
        ]

    def _load(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.shortcuts = json.load(f)
                    if isinstance(self.shortcuts, list) and len(self.shortcuts) > 0:
                        return
            except Exception:
                pass
        self.shortcuts = self._get_default_presets()
        self._save()

    def _save(self):
        try:
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.shortcuts, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_shortcuts(self):
        return list(self.shortcuts)

    def add_shortcut(self, name: str, target: str, s_type: str = "app", emoji: str = "🚀"):
        item = {
            "id": str(uuid.uuid4())[:8],
            "name": name.strip(),
            "target": target.strip(),
            "type": s_type,
            "emoji": emoji.strip() or "🚀"
        }
        self.shortcuts.append(item)
        self._save()
        return item

    def remove_shortcut(self, shortcut_id: str):
        self.shortcuts = [s for s in self.shortcuts if s.get("id") != shortcut_id]
        self._save()

    def launch(self, target: str):
        """프로그램/문서/URL 실행"""
        target = target.strip()
        if not target:
            return False

        try:
            if target.startswith("http://") or target.startswith("https://"):
                webbrowser.open(target)
                return True

            # 파일/프로그램 실행
            if os.path.exists(target):
                os.startfile(target)
                return True

            # 시스템 내장 명령어 (calc.exe, notepad.exe 등)
            subprocess.Popen(target, shell=True)
            return True
        except Exception as e:
            messagebox.showerror("실행 실패", f"프로그램 또는 링크를 실행할 수 없습니다.\n\n경로: {target}\n오류: {e}")
            return False

    def open_add_dialog(self, parent=None, on_success=None):
        """바로가기 등록 모달 팝업"""
        dlg = ctk.CTkToplevel(parent)
        dlg.title("자주 쓰는 프로그램 / 바로가기 등록")
        dlg.geometry("440x360")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.grab_set()

        ctk.CTkLabel(
            dlg, text="🚀 자주 쓰는 프로그램 / 바로가기 등록",
            font=get_font(13, "bold"), text_color="#0284c7"
        ).pack(pady=(16, 10))

        form = ctk.CTkFrame(dlg, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20, pady=4)

        # 1. 이름
        ctk.CTkLabel(form, text="표시 이름:", font=get_font(10, "bold"), anchor="w").pack(fill="x", pady=(4, 1))
        name_entry = ctk.CTkEntry(form, placeholder_text="예: 한글 2024, 수업용 PDF, e학습터 등", font=get_font(11))
        name_entry.pack(fill="x", pady=(0, 8))

        # 2. 이모지/아이콘
        ctk.CTkLabel(form, text="아이콘 이모지:", font=get_font(10, "bold"), anchor="w").pack(fill="x", pady=(4, 1))
        emoji_entry = ctk.CTkEntry(form, placeholder_text="예: 📄, 🌐, 📚, 🎬, 🎮, 🏫 (비워두면 기본)", font=get_font(11))
        emoji_entry.pack(fill="x", pady=(0, 8))

        # 3. 경로 또는 웹 URL
        ctk.CTkLabel(form, text="실행 파일 경로 또는 웹사이트 URL:", font=get_font(10, "bold"), anchor="w").pack(fill="x", pady=(4, 1))
        path_box = ctk.CTkFrame(form, fg_color="transparent")
        path_box.pack(fill="x", pady=(0, 8))

        target_entry = ctk.CTkEntry(path_box, placeholder_text="C:/.../app.exe 또는 https://...", font=get_font(11))
        target_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        def _browse_file():
            f = filedialog.askopenfilename(
                title="실행할 프로그램 또는 문서 파일 선택",
                filetypes=[
                    ("모든 지원 파일", "*.exe;*.lnk;*.bat;*.cmd;*.hwp;*.hwpx;*.pdf;*.pptx;*.xlsx;*.docx"),
                    ("실행 파일 및 바로가기 (*.exe, *.lnk)", "*.exe;*.lnk"),
                    ("한글 및 오피스 문서 (*.hwp, *.pdf, *.pptx)", "*.hwp;*.hwpx;*.pdf;*.pptx;*.xlsx"),
                    ("모든 파일 (*.*)", "*.*")
                ],
                parent=dlg
            )
            if f:
                target_entry.delete(0, "end")
                target_entry.insert(0, f)
                if not name_entry.get().strip():
                    base = os.path.splitext(os.path.basename(f))[0]
                    name_entry.insert(0, base)
                if not emoji_entry.get().strip():
                    ext = os.path.splitext(f)[1].lower()
                    if ext in [".hwp", ".hwpx", ".doc", ".docx"]:
                        emoji_entry.insert(0, "📄")
                    elif ext in [".pdf"]:
                        emoji_entry.insert(0, "📕")
                    elif ext in [".pptx", ".ppt"]:
                        emoji_entry.insert(0, "📊")
                    elif ext in [".xlsx", ".xls"]:
                        emoji_entry.insert(0, "📈")
                    else:
                        emoji_entry.insert(0, "💻")

        ctk.CTkButton(
            path_box, text="찾아보기...", width=80, font=get_font(10, "bold"),
            fg_color="#334155", hover_color="#475569", command=_browse_file
        ).pack(side="left")

        # 4. 하단 저장 버튼
        btn_box = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(6, 16))

        def _save_action():
            n = name_entry.get().strip()
            t = target_entry.get().strip()
            e = emoji_entry.get().strip() or ("🌐" if t.startswith("http") else "💻")
            if not n or not t:
                messagebox.showwarning("입력 필요", "이름과 실행 경로(또는 URL)를 입력해주세요.", parent=dlg)
                return
            s_type = "url" if t.startswith("http://") or t.startswith("https://") else "app"
            self.add_shortcut(n, t, s_type, e)
            dlg.destroy()
            if on_success:
                on_success()

        ctk.CTkButton(
            btn_box, text="등록 완료 ✔️", font=get_font(11, "bold"),
            fg_color="#0284c7", hover_color="#0369a1", height=36,
            command=_save_action
        ).pack(side="left", fill="x", expand=True, padx=4)

        ctk.CTkButton(
            btn_box, text="취소", font=get_font(10),
            fg_color="#64748b", hover_color="#475569", height=36, width=70,
            command=dlg.destroy
        ).pack(side="left", padx=4)


quick_launcher = QuickLauncherManager.get_instance()
