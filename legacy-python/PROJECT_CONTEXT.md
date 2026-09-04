# 🏫 놀티쳐 (KnolTeacher) - 프로젝트 컨텍스트 & 개발 인수인계 가이드
> **이 문서는 다른 컴퓨터나 새로운 AI 어시스턴트가 레포지토리에 연결되었을 때, 현재 작업 상태와 아키텍처를 100% 즉시 파악하고 중단 없이 작업을 이어갈 수 있도록 작성된 공식 인수인계 마스터 문서입니다.**

---

## 📌 1. 프로젝트 정체성 & 기본 정보
- **프로젝트 명칭**: 놀티쳐 (KnolTeacher)
- **영문 명칭**: `knolteacher`
- **실행 파일**: `dist/놀티쳐.exe`, `dist/knolteacher.exe`
- **GitHub 공식 저장소**: `https://github.com/LUCKYBRIDGE/knolteacher.git` (main 브랜치)
- **최신 릴리스**: `v1.0.0`
- **목적**: 대한민국 초·중·고등학교 선생님들을 위한 올인원 Always-On 스마트 교실 수업, 학급경영, 하드웨어 제어 데스크톱 애플리케이션
- **기술 스택**:
  - Python 3.12+ (Windows 10/11 64-bit 최적화)
  - CustomTkinter 6.0.0 + Tkinter (모던 다크/라이트/웜베이지 UI)
  - OpenCV (DirectShow 기반 저지연 웹캠/실물화상기 스트리밍)
  - Pillow (안티앨리어싱 고품질 실시간 이미지 스케일링)
  - PyInstaller (단일 실행 파일 원클릭 패키징)

---

## 🏗️ 2. 핵심 아키텍처 & 모듈 맵 (Current Implementation State)

### 1) `main.py`
- 애플리케이션 진입점 (Single Instance Mutex 락 탑재로 중복 실행 원천 차단)
- DPI Aware 설정 및 전역 폰트 초기화

### 2) `src/ui.py` (메인 컨트롤 타워)
- **클래스**: `App(ctk.CTk)`
- **주요 탭 구성**:
  - `today` (오늘의 일과): 나이스 연동 시간표, 실시간 점심 급식 식단표, 수업 교시별 개별 알람 관리, `[ 🎨 알람 디자인 ]` 버튼
  - `classroom_tools` (수업 진행 도구): 5대 도구 런처, `[ ⌨️ 빠른 도구 단축키 안내 & 설정 ]` (Alt+1~9)
  - `schedule_hub` (스마트 예약 센터): 일회성/반복 예약 모니터, `[ 🔄 정기 반복 설정 관리 ]`, `[ 🎨 알람 디자인 커스텀 ]`, 스마트 Diff 갱신 렌더러
  - `zen_cleaner` (바탕화면 1초 정리): 원클릭 파일 자동 분류, 아이콘 숨김
- **교시별 알람 설정 다이얼로그**: `ClassAlarmCustomDialog` (알람 시간, 모니터 1/2 선택, 알람 화면 디자인 커스텀 연동)

### 3) `src/student_display.py` (학생용 대형 놀티쳐 보드)
- **클래스**: `StudentDisplayWindow(ctk.CTkToplevel)`, `BoardWidgetWindow`, `BoardDrawingCanvasWidget`
- **단축키**: `F2` 전역 단축키로 토글
- **작업표시줄 전용 아이콘**:
  - 일반 창([베이지톤 아이콘])과 뚜렷이 구분되도록 **산뜻한 블루톤 전용 아이콘(`assets/board_icon.ico`)** 및 독립 프로세스 AppUserModelID 적용
- **MDI 다중 위젯 시스템 (`BoardWidgetWindow`)**:
  - 화면 전환이 아닌, 보드 위에 타이머, 시간표, 급식, 주사위, 추첨, 판서 등 여러 위젯을 동시에 띄워두는 데스크톱 창 시스템
  - **끝단 정리 완료**: 흉측한 모서리 사각형 블록을 100% 제거하고 `corner_radius=10`, 1.5px 단일 테두리로 마감. 우측 하단 슬림 리사이즈 그립(`⤡`)
  - **잔상 & 렉 0%**: `update_idletasks()` 완전 제거, 순수 델타(`dx, dy`) 마우스 트래킹 및 60 FPS 쓰로틀링(16ms)
- **보드 전용 판서 위젯 (`BoardDrawingCanvasWidget`)**:
  - 전체화면 오버레이 대신 보드 위 독립 위젯으로 동작하는 **'빈 칠판 / 화이트보드'**
  - `[ 🏫 초록칠판 ]` (초록 배경 + 분필 컬러) ↔ `[ 📋 화이트보드 ]` (흰색 배경 + 마커 컬러) 원클릭 전환
  - 자유 손글씨 펜, 형광펜, 지우개, 굵기 조절, 실행 취소(Undo), 전체 지우기
  - **텍스트 입력(T)**: 칠판 아무 곳이나 클릭하여 키보드로 텍스트 직접 입력 가능

### 4) `src/visualizer_window.py` (스마트 실물화상기)
- **클래스**: `VisualizerWindow(ctk.CTkToplevel)`
- **하드웨어 핵심 특성 (BESTCAM S3 호환)**:
  - 1080p 강제 설정 시 센서 버퍼가 채워지지 않아 검은 화면(mean=0.0)을 내보내는 하드웨어 특성에 맞춰, **안전 호환 해상도(640x480 VGA)를 기본값으로 오픈**
  - 검은 화면 감지 시 640x480으로 복구하는 **자가 치유(Auto-Healing)** 탑재
  - 화면은 Tkinter 캔버스에 양방향 안티앨리어싱(`cv2.INTER_LINEAR`)으로 꽉 차게 업스케일링 렌더링되어 선명함
  - 상단 툴바: `[ 🔄 새로고침 ]`, `[ 📺 해상도: 자동 (호환 모드) / 표준 / 720p / 1080p ]`, 90도 회전, 반전, 화면정지, 문서강조, 디지털 줌

### 5) `src/alarm_designer_dialog.py` & `src/alarm_design_manager.py` (알람 화면 커스텀 디자이너)
- **클래스**: `AlarmCustomDesignerDialog`, `AlarmDesignManager`
- **기능**:
  - 실제 알람 팝업 화면과 100% 동일한 WYSIWYG 캔버스 에디터
  - 제목, 타이머 숫자, 맞춤 안내 문구, 학교 스티커(📚⏰⭐💖🥛 등)를 마우스로 직접 드래그하여 원하는 위치로 자유 배치
  - 테마 색상(다크, 초록칠판, 화이트, 베이지), 창 크기, 출력 위치(우상단, 중앙, 하단중앙), 모니터 1/2 선택
  - `[ 🔔 실제 화면 미리보기 테스트 ]` 지원
  - 영구 저장: `alarm_design_config.json`

### 6) `src/class_countdown_popup.py` (사전 카운트다운 팝업)
- **클래스**: `ClassCountdownPopup(ctk.CTkToplevel)`
- 수업 시작 n분 전(기본 1분 전)에 최상위 플로팅으로 등장하여 카운트다운 후 차임벨 자동 재생
- `AlarmDesignManager`의 커스텀 좌표, 크기, 문구, 스티커를 100% 반영하여 렌더링

### 7) `src/drawing_overlay.py` (화면 전체 판서)
- **클래스**: `ScreenDrawingOverlay`
- **단축키**: `Alt+2`
- 화면 전체 투명 오버레이 판서
- **무료 글꼴 선택기 탑재**: `맑은 고딕`, `나눔고딕`, `돋움`, `굴림`, `바탕`, `궁서`, `Arial` 중 선택하여 텍스트 글상자(T) 작성 지원

### 8) `src/repeat_schedule_manager.py` & `src/recurring_dialog.py` (정기 반복 센터)
- **클래스**: `RecurringScheduleManager`, `RecurringScheduleDialog`
- 평일(월~금) / 매일 / 요일 직접 선택 반복 알람 및 PC 자동 종료/절전
- 대한민국 법정 공휴일 자동 인식 건너뛰기 지원
- 영구 저장: `recurring_schedules.json`

### 9) `src/hotkey_manager.py` & `src/hotkey_dialog.py` (전역 단축키)
- **기본 키 매핑**:
  - `Alt+1`: 돋보기
  - `Alt+2`: 화면 판서
  - `Alt+3`: 타이머
  - `Alt+4`: 라이브 줌
  - `Alt+5`: 화면 녹화
  - `Alt+6`: 영역 캡처
  - `F2` (또는 `Alt+7`): 놀티쳐 보드
  - `Alt+8`: 발표자 추첨
  - `Alt+9`: 스마트 독
- 무재부팅 1초 실시간 재등록(`reload()`) 및 영구 저장(`hotkeys_config.json`)

### 10) `src/floating_toolbar.py` (스마트 독)
- Dynamic Island 감성의 슬림 캡슐 독 (높이 38px)
- 12종 수업 도구 커스텀 넣고 빼기(On/Off) 및 실시간 시간표 남은 시간 티커 지원

### 11) `src/font_config.py` (폰트 표준화)
- 혼자 튀거나 깨지는 고정폭 영문 폰트(`Consolas`) 및 깨지는 유니코드 제거
- Windows 표준 고품질 무료 서체인 **맑은 고딕 볼드(`Malgun Gothic`, bold)**로 전면 통일

---

## ⚠️ 3. 하드웨어 & 환경 주의사항 (Must-Know Quirks)

1. **실물화상기 (BESTCAM S3) 주의**:
   - OpenCV에서 `cv2.VideoCapture` 오픈 시 절대로 `1920x1080`이나 `MJPG` 포맷을 하드코딩으로 강제하면 안 됩니다. BESTCAM S3는 1080p 요청 시 검은 프레임(`mean == 0.0`)만 내보냅니다.
   - 640x480 기본 해상도로 받아 Canvas에서 업스케일링해야 화면이 깨끗하고 밝게 나옵니다.
2. **Tkinter 스레드 안전성 (Thread-Safety)**:
   - Tkinter 위젯 메서드(`winfo_exists()`, `after()`, `configure()`)는 **반드시 메인 스레드에서만 호출**해야 합니다.
   - 백그라운드 스레드에서 `self.after()`를 직접 호출하면 `RuntimeError: main thread is not in main loop`가 발생하므로, 백그라운드 스레드는 순수 파이썬 변수나 큐에 데이터를 기록하고 메인 스레드가 읽도록 해야 합니다.
3. **위젯 드래그 & 리사이즈 잔상 방지**:
   - 마우스 `<B1-Motion>` 핸들러에서 절대로 `update_idletasks()`를 호출하지 마십시오. CustomTkinter 캔버스에 심각한 테두리 잔상(Ghosting)이 발생합니다.
   - 이동과 크기 조절은 `dx = event.x_root - self._start_mouse_x`의 상대 델타 방식을 사용해야 창이 튀지 않습니다.

---

## 📂 4. 영구 설정 파일 저장 경로 (`src/config_utils.py`)
모든 사용자 데이터는 다음 경로에 안전하게 JSON으로 보관됩니다:
- **경로**: `C:\Users\<User>\.knol_teacher_desk\` (또는 `%APPDATA%\knol_teacher_desk\`)
- **파일 목록**:
  - `settings.json`: 학교 코드, 기본 설정, 모니터 설정
  - `timetable.json`: 시간표 및 교시별 시간
  - `hotkeys_config.json`: 커스텀 전역 단축키 설정
  - `recurring_schedules.json`: 정기 반복 알람 및 전원 스케줄
  - `alarm_design_config.json`: 알람 화면 커스텀 디자인 좌표/문구/테마
  - `dock_config.json`: 스마트 독 활성화 도구 목록
  - `student_list.json`: 학생 명렬표

---

## 🚀 5. 개발 환경 설정 & 빌드 가이드

### 1단계: 저장소 클론 및 패키지 설치
```bash
git clone https://github.com/LUCKYBRIDGE/knolteacher.git
cd knolteacher
pip install -r requirements.txt
```

### 2단계: 소스코드 실행 테스트
```bash
python main.py
```

### 3단계: 단일 실행 파일 (`놀티쳐.exe`) 빌드
```bash
python build_exe.py
```
- 빌드 완료 시 `dist/놀티쳐.exe` 및 `dist/knolteacher.exe`가 생성됩니다 (약 88MB).

### 4단계: 바탕화면 배포
```powershell
powershell -Command "Stop-Process -Name '놀티쳐','knolteacher' -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 1; Copy-Item 'dist\놀티쳐.exe' 'C:\Users\owner\Desktop\놀티쳐.exe' -Force"
```

### 5단계: GitHub 릴리스 업로드
```bash
git add -A
git commit -m "commit message"
git push origin main
gh release upload v1.0.0 "dist/놀티쳐.exe" "dist/knolteacher.exe" --clobber
```
