import webbrowser
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from src.font_config import get_font
from src.theme_manager import theme_manager
from src.tooltip import attach_tooltip

class PrivacyPolicyDialog(ctk.CTkToplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title('개인정보 처리방침 & 제작자 안내 - 놀티쳐')
        self.geometry('560x600')
        self.minsize(480, 480)
        self.attributes('-topmost', True)
        self._build_ui()
        self.focus_force()

    def _build_ui(self):
        palette = theme_manager.get_theme()

        top_bar = ctk.CTkFrame(self, fg_color=palette['accent'], corner_radius=0, height=54)
        top_bar.pack(fill='x', side='top')
        top_bar.pack_propagate(False)

        ctk.CTkLabel(
            top_bar,
            text='🔒 놀티쳐 개인정보 처리방침 및 운영 안내',
            font=get_font(13, 'bold'),
            text_color='#ffffff'
        ).pack(side='left', padx=16, pady=10)

        scroll = ctk.CTkScrollableFrame(self, fg_color='transparent')
        scroll.pack(fill='both', expand=True, padx=16, pady=12)

        hero_card = ctk.CTkFrame(scroll, fg_color=palette['card_inner_bg'], corner_radius=10, border_width=1, border_color=palette['card_border'])
        hero_card.pack(fill='x', pady=(0, 10))

        ctk.CTkLabel(
            hero_card,
            text='🛡️ 100% 로컬 영구 보관 및 안전한 단독 운영 원칙',
            font=get_font(12, 'bold'),
            text_color=palette['accent']
        ).pack(anchor='w', padx=14, pady=(12, 4))

        hero_desc = (
            '놀티쳐(KnolTeacher)는 선생님과 학생의 소중한 교육 정보 및 개인정보를 최우선으로 보호합니다.\n'
            '본 소프트웨어에서 다루는 모든 데이터는 외부 클라우드나 원격 서버로 절대 전송되지 않으며, '
            '선생님의 로컬 PC 저장소 내에서만 안전하게 보관 및 운영됩니다.'
        )
        ctk.CTkLabel(
            hero_card,
            text=hero_desc,
            font=get_font(10),
            text_color=palette['text_main'],
            justify='left',
            wraplength=480
        ).pack(anchor='w', padx=14, pady=(0, 12))

        sec1 = ctk.CTkFrame(scroll, fg_color=palette['card_bg'], corner_radius=8, border_width=1, border_color=palette['card_border'])
        sec1.pack(fill='x', pady=(0, 8))
        ctk.CTkLabel(sec1, text='1. 수집 및 저장되는 데이터 항목', font=get_font(11, 'bold'), text_color=palette['text_main']).pack(anchor='w', padx=12, pady=(10, 4))
        sec1_text = (
            '• 학생 명렬표 데이터 (이름, 번호): 발표자 뽑기 및 수업 도구용으로 사용되며 사용자 PC 로컬 파일로만 보관됩니다.\n'
            '• 학급 시간표 및 과목 설정: 학교별 일과 운영을 위해 사용자의 로컬 환경에만 저장됩니다.\n'
            '• 나이스(NEIS) 연동 설정값: 교육청 및 학교 고유 코드(공개 정보)만 로컬에 저장됩니다.\n'
            '• 개인 메모 및 수업 알람 내역: PC 내부 스케줄러에서만 작동합니다.'
        )
        ctk.CTkLabel(sec1, text=sec1_text, font=get_font(9), text_color=palette['text_sub'], justify='left', wraplength=480).pack(anchor='w', padx=12, pady=(0, 10))

        sec2 = ctk.CTkFrame(scroll, fg_color=palette['card_bg'], corner_radius=8, border_width=1, border_color=palette['card_border'])
        sec2.pack(fill='x', pady=(0, 8))
        ctk.CTkLabel(sec2, text='2. 외부 네트워크 통신 범위의 투명한 고지', font=get_font(11, 'bold'), text_color=palette['text_main']).pack(anchor='w', padx=12, pady=(10, 4))
        sec2_text = (
            '• 교육부 나이스(NEIS) Open API: 학교별 공개된 급식 식단표 및 기본 시간표를 조회하기 위해 정부 공공데이터 포털과 통신합니다. (개인정보 전송 없음)\n'
            '• GitHub Releases API: 최신 안정화 버전 업데이트 확인을 위해 버전 번호만 확인합니다.\n'
            '• 기타 일체의 광고 추적기, 외부 분석 툴, 백도어 트래픽이 전혀 포함되어 있지 않습니다.'
        )
        ctk.CTkLabel(sec2, text=sec2_text, font=get_font(9), text_color=palette['text_sub'], justify='left', wraplength=480).pack(anchor='w', padx=12, pady=(0, 10))

        # 3. 데이터 저장 위치 및 다른 PC 이전(백업) 방법
        sec3 = ctk.CTkFrame(scroll, fg_color=palette['card_bg'], corner_radius=8, border_width=1, border_color=palette['card_border'])
        sec3.pack(fill='x', pady=(0, 8))
        ctk.CTkLabel(sec3, text='3. 📁 데이터 저장 위치 및 다른 PC 이전(백업) 방법', font=get_font(11, 'bold'), text_color=palette['text_main']).pack(anchor='w', padx=12, pady=(10, 4))

        from src.config_utils import get_config_dir
        cfg_dir = get_config_dir()
        sec3_text = (
            f'• 실제 저장 경로: {cfg_dir}\n'
            '• 캐시 정리 안전 보장: 본 경로는 윈도우 사용자 영구 프로필 루트에 위치하므로, '
            '알약, V3, 고클린, 윈도우 디스크 정리 등 PC 최적화 도구를 실행해도 임시 파일(캐시)로 분류되지 않아 절대 삭제되지 않습니다.\n'
            '• 다른 컴퓨터로 데이터 이전 방법: 교실 컴퓨터를 교체하거나 다른 PC에서 기존 데이터를 그대로 쓰고 싶으실 경우, '
            '위 폴더를 USB에 그대로 복사하여 새 컴퓨터의 사용자 폴더(C:\\Users\\선생님계정\\)에 붙여넣으시면 '
            '모든 시간표, 나이스 설정, 학생 명렬표, 북마크가 1초 만에 100% 완벽 복원됩니다.'
        )
        ctk.CTkLabel(sec3, text=sec3_text, font=get_font(9), text_color=palette['text_sub'], justify='left', wraplength=480).pack(anchor='w', padx=12, pady=(0, 8))

        ctk.CTkButton(
            sec3,
            text='📂 데이터 저장 폴더 바로 열기',
            font=get_font(10, 'bold'),
            fg_color=palette['sidebar_btn_hover'],
            hover_color=palette['accent_hover'],
            text_color=palette['text_main'],
            height=28,
            corner_radius=6,
            command=self._open_config_folder
        ).pack(anchor='w', padx=12, pady=(0, 10))

        # 4. 소프트웨어 개발 및 제작자 안내
        sec4 = ctk.CTkFrame(scroll, fg_color=palette['card_inner_bg'], corner_radius=8, border_width=1, border_color=palette['card_border'])
        sec4.pack(fill='x', pady=(0, 8))
        ctk.CTkLabel(sec4, text='4. 소프트웨어 개발 및 제작자 안내', font=get_font(11, 'bold'), text_color=palette['text_main']).pack(anchor='w', padx=12, pady=(10, 4))
        sec4_text = (
            '• 개발자 / 저작권자: 교사 서정완 (Copyright 2026. All rights reserved.)\n'
            '• 공식 문의 및 피드백 이메일: lucky20220528@gmail.com\n'
            '• 기능 개선 제안, 버그 제보, 학교 현장 도입 문의 등 소중한 의견을 언제든지 환영합니다.'
        )
        ctk.CTkLabel(sec4, text=sec4_text, font=get_font(9), text_color=palette['text_sub'], justify='left', wraplength=480).pack(anchor='w', padx=12, pady=(0, 10))

        mail_bar = ctk.CTkFrame(sec4, fg_color='transparent')
        mail_bar.pack(fill='x', padx=12, pady=(0, 10))

        ctk.CTkButton(
            mail_bar,
            text='✉️ 제작자에게 이메일 보내기',
            font=get_font(10, 'bold'),
            fg_color=palette['accent'],
            hover_color=palette['accent_hover'],
            text_color='#ffffff',
            height=28,
            corner_radius=6,
            command=self._send_email
        ).pack(side='left', padx=(0, 8))

        ctk.CTkButton(
            mail_bar,
            text='📋 이메일 주소 복사',
            font=get_font(10, 'bold'),
            fg_color=palette['sidebar_btn_hover'],
            hover_color=palette['sidebar_bg'],
            text_color=palette['text_main'],
            border_width=1,
            border_color=palette['card_border'],
            height=28,
            corner_radius=6,
            command=self._copy_email
        ).pack(side='left')

        btm_bar = ctk.CTkFrame(self, fg_color=palette['card_inner_bg'], height=48, corner_radius=0, border_width=1, border_color=palette['card_border'])
        btm_bar.pack(fill='x', side='bottom')
        btm_bar.pack_propagate(False)

        ctk.CTkButton(
            btm_bar,
            text='확인 및 닫기',
            font=get_font(11, 'bold'),
            fg_color=palette['accent'],
            hover_color=palette['accent_hover'],
            text_color='#ffffff',
            width=110,
            height=30,
            corner_radius=6,
            command=self.destroy
        ).pack(side='right', padx=14)

    def _send_email(self):
        webbrowser.open('mailto:lucky20220528@gmail.com?subject=[놀티쳐 문의 및 피드백]')

    def _copy_email(self):
        try:
            self.clipboard_clear()
            self.clipboard_append('lucky20220528@gmail.com')
            messagebox.showinfo('복사 완료', '제작자 공식 이메일 주소(lucky20220528@gmail.com)가 클립보드에 복사되었습니다.')
        except Exception:
            pass

    def _open_config_folder(self):
        import os, subprocess
        from src.config_utils import get_config_dir
        cfg_dir = get_config_dir()
        if os.path.exists(cfg_dir):
            try:
                if os.name == 'nt':
                    os.startfile(cfg_dir)
                else:
                    subprocess.run(['xdg-open', cfg_dir])
            except Exception as e:
                messagebox.showinfo('안내', f'데이터 폴더 경로:\n{cfg_dir}')
        else:
            messagebox.showinfo('안내', f'데이터 폴더 경로:\n{cfg_dir}')

def open_privacy_dialog(parent=None):
    return PrivacyPolicyDialog(parent)
