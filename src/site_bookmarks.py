import os
import sys
import json
import webbrowser
import tkinter.messagebox as messagebox
import customtkinter as ctk
from typing import Callable, Optional
from src.font_config import setup_global_fonts, get_font
from src.config_utils import get_config_dir

DEFAULT_BOOKMARKS = [
    {
        "id": "nolquiz",
        "title": "놀퀴즈 (Pinky-NE)",
        "desc": "초등 실시간 퀴즈 & 수업 게임",
        "url": "https://pinky-ne.com/",
        "icon": "🎯",
        "color": "#ec4899",
        "category": "수업활동"
    },
    {
        "id": "eduptl",
        "title": "K-에듀파인 / 업무포털",
        "desc": "강원 교육행정정보 업무포털",
        "url": "https://gwe.eduptl.kr/",
        "icon": "🏫",
        "color": "#0284c7",
        "category": "행정업무"
    },
    {
        "id": "gwe_sw",
        "title": "강원 SW 인증키 & 다운로드",
        "desc": "MS 오피스, 한글 등 정품 SW",
        "url": "https://office.gwe.go.kr/",
        "icon": "🔑",
        "color": "#10b981",
        "category": "행정업무"
    },
    {
        "id": "gwe_airo",
        "title": "강원 아이로 (AI로)",
        "desc": "강원 교수학습지원 & AI 학습 포털",
        "url": "https://airo.gwedu.kr/",
        "icon": "🚀",
        "color": "#8b5cf6",
        "category": "수업활동"
    },
    {
        "id": "iscream",
        "title": "아이스크림 (i-Scream)",
        "desc": "초등 수업 디지털 콘텐츠 포털",
        "url": "https://www.i-scream.co.kr/",
        "icon": "🍦",
        "color": "#f59e0b",
        "category": "수업활동"
    },
    {
        "id": "indischool",
        "title": "인디스쿨 (IndiSchool)",
        "desc": "전국 초등교사 커뮤니티 & 자료",
        "url": "https://www.indischool.com/",
        "icon": "🧑‍🏫",
        "color": "#0ea5e9",
        "category": "수업자료"
    },
    {
        "id": "edunet",
        "title": "에듀넷·티-클리어",
        "desc": "국가 교육과정 및 공식 수업자료",
        "url": "https://www.edunet.net/",
        "icon": "📚",
        "color": "#14b8a6",
        "category": "수업자료"
    },
    {
        "id": "thinkerbell",
        "title": "띵커벨 (ThinkerBell)",
        "desc": "실시간 퀴즈, 워크시트, 토의토론",
        "url": "https://www.tkbell.co.kr/",
        "icon": "🔔",
        "color": "#f97316",
        "category": "수업활동"
    },
    {
        "id": "canva",
        "title": "캔바 (Canva 교육용)",
        "desc": "학급 템플릿 & 교사용 디자인 도구",
        "url": "https://www.canva.com/ko_kr/education/",
        "icon": "🎨",
        "color": "#6366f1",
        "category": "교무도구"
    },
    {
        "id": "miricanvas",
        "title": "미리캔버스",
        "desc": "수업 PPT 및 학습지 디자인",
        "url": "https://www.miricanvas.com/",
        "icon": "📑",
        "color": "#06b6d4",
        "category": "교무도구"
    }
]

class SiteBookmarkManager:
    """
    교사용 유용한 사이트 북마크 관리자
    """
    def __init__(self):
        self.config_dir = get_config_dir()
        self.file_path = os.path.join(self.config_dir, "site_bookmarks.json")
        self.bookmarks = self._load()

    def _load(self) -> list[dict]:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, list) and saved:
                        return saved
            except Exception:
                pass
        return [dict(b) for b in DEFAULT_BOOKMARKS]

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.bookmarks, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_bookmark(self, title: str, url: str, desc: str = "", icon: str = "🌐", color: str = "#0a84ff") -> dict:
        url = url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        new_item = {
            "id": f"custom_{int(os.times().elapsed * 1000)}",
            "title": title.strip(),
            "desc": desc.strip() if desc.strip() else url,
            "url": url,
            "icon": icon.strip() if icon.strip() else "🌐",
            "color": color,
            "category": "사용자지정"
        }
        self.bookmarks.insert(0, new_item)  # 최상단 추가
        self.save()
        return new_item

    def remove_bookmark(self, item_id: str):
        self.bookmarks = [b for b in self.bookmarks if b.get("id") != item_id]
        self.save()

    def reset_to_default(self):
        self.bookmarks = [dict(b) for b in DEFAULT_BOOKMARKS]
        self.save()

    def open_site(self, url: str):
        try:
            webbrowser.open(url)
        except Exception:
            pass

site_bookmark_manager = SiteBookmarkManager()


class AddSiteDialog(ctk.CTkToplevel):
    """
    선생님이 원하는 사이트 바로가기 신규 등록 다이얼로그
    """
    def __init__(self, parent, on_added_callback: Callable[[], None]):
        super().__init__(parent)
        self.on_added_callback = on_added_callback
        self.title("➕ 새 사이트 바로가기 추가")
        self.geometry("460x420")
        self.minsize(400, 360)
        self.attributes("-topmost", True)
        self.transient(parent)
        self.grab_set()

        setup_global_fonts(self)
        self._load_icon()

        self._build_ui()

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="#0b0f19", corner_radius=14, border_width=1, border_color="#38bdf8")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # 헤더
        hdr = ctk.CTkFrame(container, fg_color="#161e31", corner_radius=10)
        hdr.pack(fill="x", padx=8, pady=(8, 12))

        ctk.CTkLabel(
            hdr,
            text="➕ 내가 원하는 사이트 바로가기 등록",
            font=get_font(13, "bold"),
            text_color="#38bdf8"
        ).pack(side="left", padx=10, pady=8)

        form = ctk.CTkFrame(container, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=12, pady=4)

        # 1. 사이트 이름
        ctk.CTkLabel(form, text="사이트 이름 (필수):", font=get_font(11, "bold")).pack(anchor="w", pady=(4, 2))
        self.title_entry = ctk.CTkEntry(form, placeholder_text="예: 클래스123, 패들렛, 구글 클래스룸", font=get_font(11), height=32)
        self.title_entry.pack(fill="x", pady=(0, 8))

        # 2. 사이트 URL 주소
        ctk.CTkLabel(form, text="웹사이트 URL 주소 (필수):", font=get_font(11, "bold")).pack(anchor="w", pady=(4, 2))
        self.url_entry = ctk.CTkEntry(form, placeholder_text="예: https://class123.ac 또는 padlet.com", font=get_font(11), height=32)
        self.url_entry.pack(fill="x", pady=(0, 8))

        # 3. 간단 설명
        ctk.CTkLabel(form, text="간단한 설명 (선택):", font=get_font(11, "bold")).pack(anchor="w", pady=(4, 2))
        self.desc_entry = ctk.CTkEntry(form, placeholder_text="예: 학급 칭찬 보상 및 쑥쑥이 관리", font=get_font(11), height=32)
        self.desc_entry.pack(fill="x", pady=(0, 8))

        # 4. 아이콘 이모지 선택
        ctk.CTkLabel(form, text="아이콘 선택:", font=get_font(11, "bold")).pack(anchor="w", pady=(4, 2))
        icon_row = ctk.CTkFrame(form, fg_color="transparent")
        icon_row.pack(fill="x", pady=(0, 12))

        self.selected_icon = ctk.StringVar(value="🌐")
        icons = ["🌐", "⭐", "📚", "🎮", "🎯", "💡", "📌", "🚀", "🎨", "🏫"]
        for ic in icons:
            ctk.CTkRadioButton(
                icon_row,
                text=ic,
                value=ic,
                variable=self.selected_icon,
                font=get_font(13),
                width=36
            ).pack(side="left", padx=2)

        # 하단 버튼 (추가, 취소)
        btn_box = ctk.CTkFrame(container, fg_color="transparent")
        btn_box.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(
            btn_box,
            text="취소",
            font=get_font(11),
            fg_color="#374151",
            hover_color="#4b5563",
            width=80,
            height=34,
            command=self.destroy
        ).pack(side="left")

        ctk.CTkButton(
            btn_box,
            text="✨ 바로가기 등록 완료",
            font=get_font(12, "bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=34,
            command=self._save_new_site
        ).pack(side="right", fill="x", expand=True, padx=(8, 0))

    def _save_new_site(self):
        title = self.title_entry.get().strip()
        url = self.url_entry.get().strip()
        desc = self.desc_entry.get().strip()
        icon = self.selected_icon.get()

        if not title:
            messagebox.showwarning("입력 확인", "사이트 이름을 입력해 주세요.", parent=self)
            self.title_entry.focus_set()
            return

        if not url:
            messagebox.showwarning("입력 확인", "웹사이트 URL 주소를 입력해 주세요.", parent=self)
            self.url_entry.focus_set()
            return

        site_bookmark_manager.add_bookmark(title=title, url=url, desc=desc, icon=icon)
        if self.on_added_callback:
            self.on_added_callback()

        self.destroy()


class SiteBookmarksDialog(ctk.CTkToplevel):
    """
    교사용 유용한 사이트 바로가기 플로팅 모달 창 (추가/삭제/실행)
    """
    def __init__(self, parent=None, on_changed_callback: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.parent = parent
        self.on_changed_callback = on_changed_callback
        self.title("🌐 교사용 유용한 교육 사이트 바로가기 관리")
        self.geometry("680x560")
        self.minsize(540, 440)
        self.attributes("-topmost", True)
        self.resizable(True, True)

        setup_global_fonts(self)
        self._load_icon()

        self._build_ui()

    def _load_icon(self):
        base_dir = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="#0b0f19", corner_radius=14, border_width=1, border_color="#0a84ff")
        container.pack(fill="both", expand=True, padx=8, pady=8)

        # 상단 헤더
        hdr = ctk.CTkFrame(container, fg_color="#161e31", corner_radius=10)
        hdr.pack(fill="x", padx=6, pady=6)

        ctk.CTkLabel(
            hdr,
            text="🌐 교사용 유용한 사이트 바로가기 관리",
            font=get_font(13, "bold"),
            text_color="#38bdf8"
        ).pack(side="left", padx=10, pady=8)

        btn_box = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_box.pack(side="right", padx=6, pady=4)

        ctk.CTkButton(
            btn_box,
            text="➕ 새 사이트 추가",
            font=get_font(11, "bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=28,
            command=self._open_add_site_dialog
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_box,
            text="🔄 기본값 복원",
            font=get_font(10),
            fg_color="#374151",
            hover_color="#4b5563",
            height=28,
            command=self._reset_defaults
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_box,
            text="✕",
            width=26,
            height=26,
            font=get_font(11, "bold"),
            fg_color="#3f1d24",
            hover_color="#dc2626",
            text_color="#fca5a5",
            corner_radius=6,
            command=self.destroy
        ).pack(side="left", padx=(2, 4))

        # 사이트 카드 스크롤 영역
        self.scroll = ctk.CTkScrollableFrame(container, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self._render_site_grid()

    def _open_add_site_dialog(self):
        AddSiteDialog(self, on_added_callback=self._on_site_list_changed)

    def _on_site_list_changed(self):
        self._render_site_grid()
        if self.on_changed_callback:
            self.on_changed_callback()

    def _reset_defaults(self):
        if messagebox.askyesno("기본값 복원", "모든 사이트 목록을 기본 10개 목록으로 초기화하시겠습니까?", parent=self):
            site_bookmark_manager.reset_to_default()
            self._on_site_list_changed()

    def _delete_site(self, item_id: str, title: str):
        if messagebox.askyesno("사이트 삭제", f"'{title}' 바로가기를 삭제하시겠습니까?", parent=self):
            site_bookmark_manager.remove_bookmark(item_id)
            self._on_site_list_changed()

    def _render_site_grid(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        bookmarks = site_bookmark_manager.bookmarks

        grid = ctk.CTkFrame(self.scroll, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        for i, item in enumerate(bookmarks):
            row = i // 2
            col = i % 2

            card = ctk.CTkFrame(grid, fg_color="#181d28", corner_radius=10, border_width=1, border_color="#2d3748")
            card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=(8, 2))

            icon_lbl = ctk.CTkLabel(top_row, text=item.get("icon", "🌐"), font=get_font(15))
            icon_lbl.pack(side="left", padx=(0, 6))

            title_lbl = ctk.CTkLabel(
                top_row,
                text=item["title"],
                font=get_font(12, "bold"),
                text_color="#f8fafc",
                anchor="w"
            )
            title_lbl.pack(side="left", fill="x", expand=True)

            # 삭제 버튼
            del_btn = ctk.CTkButton(
                top_row,
                text="🗑️",
                width=24,
                height=24,
                font=get_font(10),
                fg_color="#374151",
                hover_color="#dc2626",
                text_color="#fca5a5",
                corner_radius=6,
                command=lambda b_id=item.get("id"), b_title=item["title"]: self._delete_site(b_id, b_title)
            )
            del_btn.pack(side="right")

            desc_lbl = ctk.CTkLabel(
                card,
                text=item.get("desc", ""),
                font=get_font(10),
                text_color="#94a3b8",
                anchor="w"
            )
            desc_lbl.pack(fill="x", padx=10, pady=(0, 6))

            btn_row = ctk.CTkFrame(card, fg_color="transparent")
            btn_row.pack(fill="x", padx=10, pady=(0, 8))

            ctk.CTkButton(
                btn_row,
                text="🔗 바로가기 열기",
                font=get_font(11, "bold"),
                fg_color=item.get("color", "#0284c7"),
                hover_color="#0369a1",
                height=28,
                corner_radius=6,
                command=lambda u=item["url"]: site_bookmark_manager.open_site(u)
            ).pack(side="left", fill="x", expand=True)
