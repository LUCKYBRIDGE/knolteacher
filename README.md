# 🏫 놀티쳐 (KnolTeacher)

> **대한민국 선생님들을 위한 스마트 올인원 교사용 Always-On 수업·학급경영·하드웨어 데스크**  
> *초등·중등·고등학교 선생님들의 일과 관리, 실시간 급식, 화면 판서, 수업 도구, 스마트 실물화상기, 나이스(NEIS) 자동입력, PC 전원 예약을 하나의 프로그램으로 완벽 지원합니다.*

<div align="center">

[![최신 버전 다운로드](https://img.shields.io/badge/📥_최신_버전_다운로드-놀티쳐.exe-0284c7?style=for-the-badge&logo=windows)](https://github.com/LUCKYBRIDGE/knolteacher/releases/latest)
[![GitHub Release](https://img.shields.io/github/v/release/LUCKYBRIDGE/knolteacher?color=orange&label=Release&style=for-the-badge)](https://github.com/LUCKYBRIDGE/knolteacher/releases)
[![Platform](https://img.shields.io/badge/Platform-Windows_10_/_11-blue.svg?style=for-the-badge)](https://github.com/LUCKYBRIDGE/knolteacher)

</div>

---

## 📥 다운로드 및 빠른 시작 (Quick Start)

### 1️⃣ 사용자용: 무설치 단일 실행 파일 (`놀티쳐.exe`)
* 👉 **[🚀 최신 버전 놀티쳐.exe 다운로드하기 (GitHub Releases)](https://github.com/LUCKYBRIDGE/knolteacher/releases/latest)**
* 다운로드받은 **`놀티쳐.exe`**를 바탕화면에 두고 더블 클릭하시면 즉시 실행됩니다 (Python 설치 불필요).

### 2️⃣ 개발자용: 다른 컴퓨터에서 개발 환경 이어하기
새로운 컴퓨터에서 이 프로젝트를 이어 작업할 때는 아래 2단계만 실행하면 완벽하게 준비됩니다:
```bash
git clone https://github.com/LUCKYBRIDGE/knolteacher.git
cd knolteacher
setup_env.bat
```
*(또는 `pip install -r requirements.txt` 후 `python main.py` 실행)*

> 💡 **아키텍처 및 상세 인수인계 문서**: 프로젝트 루트의 [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md)에 모든 모듈 구조, 하드웨어 특이사항, 설정 파일 규격이 상세히 정리되어 있습니다.

---

## 🌟 핵심 기능 소개

### 1. 📋 학생용 대형 놀티쳐 보드 (단축키: `F2`)
* **다중 위젯 데스크톱 윈도우 시스템**: 화면 전환 없이 보드 위에 타이머, 시간표, 급식, 주사위, 추첨, 판서 등 여러 도구 창을 동시에 자유롭게 띄우고 배치.
* **60 FPS 무잔상 델타 트래킹**: 마우스 이동과 1:1로 일체되어 부드럽게 움직이며, 끝단이 단정하게 마감된 둥근 카드 디자인.
* **보드 전용 인터랙티브 판서 위젯**:
  - `[ 🏫 초록칠판 ]` (분필 모드) ↔ `[ 📋 화이트보드 ]` (마커 모드) 원클릭 전환
  - 자유 손글씨, 형광펜, 지우개, 굵기 조절
  - **텍스트 입력(T)**: 칠판 어디든 클릭하여 키보드로 바로 텍스트 타이핑 필기 가능
* **작업표시줄 전용 아이콘**: 메인 창(베이지톤)과 한눈에 구분되는 **산뜻한 블루톤 전용 아이콘** 탑재.

### 2. 📷 스마트 실물화상기 (Document Camera / Visualizer)
* **USB 실물화상기(BESTCAM, ELMO, AVer 등) 및 웹캠 실시간 스트리밍**
* **검은 화면 자동 치유 (Auto-Healing)**: 드라이버 대역폭 이슈로 검은 화면이 송출될 경우 안전 호환 모드로 1초 만에 자동 복구.
* **강력한 수업용 비디오 컨트롤**:
  - 90° 회전, 좌우/상하 반전, 화면 일시정지(Freeze)
  - 고대비 흑백 문서 강조 모드, 디지털 줌 (1.0x ~ 3.5x)
  - 원클릭 고화질 스냅샷 캡처 및 화면 판서 연동

### 3. 🎨 알람 화면 시각적 WYSIWYG 커스텀 디자이너
* 수업 시작 카운트다운 알람 창을 선생님이 원하는 디자인으로 직접 커스텀!
* 제목, 타이머 숫자, 맞춤 안내 문구, 학교 스티커(📚⏰⭐💖🥛 등)를 마우스로 직접 드래그하여 배치.
* 다크, 초록칠판, 화이트, 베이지 4대 테마 및 모니터 1/2 선택, `[ 🔔 실제 화면 미리보기 테스트 ]` 지원.

### 4. ✏️ 화면 전체 판서 (단축키: `Alt+2`)
* 어떤 화면(나이스, 유튜브, PPT, 웹 브라우저) 위에서도 즉시 투명 오버레이로 자유 판서.
* **무료 글꼴 선택기**: 맑은 고딕, 나눔고딕, 돋움, 굴림, 바탕, 궁서, Arial 등 원하는 서체로 텍스트 글상자 작성.

### 5. ⌨️ 전역 단축키 센터 (Alt+1 ~ Alt+9, F2)
* `Alt+1` (돋보기), `Alt+2` (판서), `Alt+3` (타이머), `Alt+4` (라이브줌), `Alt+5` (녹화), `Alt+6` (캡처), `F2` (보드), `Alt+8` (추첨), `Alt+9` (스마트독)
* 단축키 안내 치트시트 및 단축키 커스텀 변경 지원 (`hotkeys_config.json`).

### 6. 🔄 정기 반복 알람 & 전원 자동화 센터
* 매일, 평일(월~금), 특정 요일 반복 알람 및 PC 자동 종료/절전 스케줄링.
* 대한민국 법정 공휴일 자동 인식 건너뛰기 지원.

---

## 🛠️ 단일 실행 파일 (`놀티쳐.exe`) 빌드 방법

```bash
python build_exe.py
```
* 빌드 완료 시 `dist/놀티쳐.exe` 및 `dist/knolteacher.exe`가 생성됩니다.

---

## 📜 라이선스 & 저작권
**Copyright 2026. 교사 서정완. All rights reserved.**  
*본 프로그램은 대한민국 교원들의 편리하고 스마트한 교육 환경을 위해 개발되었습니다.*
