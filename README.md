# 🏫 놀티쳐 (KnolTeacher) v3.0.9

> 대한민국 교사를 위한 Windows 올인원 수업·학급경영·스마트보드 데스크톱 애플리케이션

[![Latest Release](https://img.shields.io/github/v/release/LUCKYBRIDGE/knolteacher?label=Release&color=orange)](https://github.com/LUCKYBRIDGE/knolteacher/releases/latest)
[![CI](https://github.com/LUCKYBRIDGE/knolteacher/actions/workflows/ci.yml/badge.svg)](https://github.com/LUCKYBRIDGE/knolteacher/actions/workflows/ci.yml)
[![Platform](https://img.shields.io/badge/Windows-10%20%2F%2011-blue)](https://github.com/LUCKYBRIDGE/knolteacher)
[![Framework](https://img.shields.io/badge/.NET-8.0%20WPF-512BD4)](https://dotnet.microsoft.com/)

현재 주력 구현은 **C# / .NET 8 / WPF** 기반이다. 이전 Python/CustomTkinter 구현은 `legacy-python/`에 보관하며 신규 기능 개발 기준으로 사용하지 않는다.

## 다운로드 및 업데이트

최신 정식 버전은 GitHub Releases에서 받는다. Release 배지는 현재 공개된 stable 버전을 표시한다.

- 플랫폼: Windows 10/11 x64
- 아키텍처: win-x64
- 배포: self-contained + single-file
- GitHub Release transport asset: `KnolTeacher.exe` 1개
- 사용자 PC의 로컬 실행 파일명: `놀티쳐.exe`
- .NET 런타임 별도 설치 불필요
- 자동 업데이트 연속성 공식 기준선: **v3.0.9 이후 설치본**

v3.0.9 이후 설치본은 바탕화면의 `놀티쳐.exe`에서 **버전 확인 → 업데이트 → 자동 재실행** 흐름을 사용한다. 다운로드 파일은 GitHub HTTPS 주소, 크기, SHA-256, embedded FileVersion을 검증하고 설치 위치의 `놀티쳐.exe`로 교체한 뒤 새 버전을 다시 실행한다. v3.0.9 이전 배포본에서의 자동 업데이트 호환은 필수 지원 범위로 두지 않는다.

개발자가 `publish.bat`을 실행하면 `dist-net\놀티쳐.exe` 한 파일만 생성되도록 검증한다.

## v3.0.9 주요 개선사항

### 🔄 버전 확인·원클릭 업데이트 신뢰성 강화

- 화면의 버전 숫자를 하드코딩하지 않고 실제 실행 중인 Assembly/FileVersion에서 표시한다.
- GitHub Release에서는 `KnolTeacher.exe`를 안정적인 ASCII transport 이름으로 사용하고, 로컬에서는 계속 `놀티쳐.exe`를 사용한다.
- updater는 `KnolTeacher.exe`와 구현상 legacy `놀티쳐.exe`를 허용한다. 공식 미래 Release는 `KnolTeacher.exe`를 사용한다.
- asset 크기와 SHA-256뿐 아니라 다운로드한 실행 파일 내부 FileVersion이 대상 Release와 같은지도 확인한다.
- 앱 종료 후 설치 위치의 `놀티쳐.exe`를 재시도 교체하고 SHA-256을 다시 검증한 경우에만 새 버전을 재실행한다.
- 새 버전이 다시 열리면 업데이트 완료 상태를 안내한다.
- v3.0.9 이후에는 `3.0.10`, `3.1.0`처럼 버전 자릿수나 minor가 바뀌어도 semantic version 순서로 업데이트를 판단한다.

### 🖥️ 팝업과 위젯의 멀티 모니터 UX 정리

명확한 독립 Window/Dialog 런처는 다음 규칙을 따른다.

- 왼클릭: 모니터 1
- 우클릭: 모니터 2 (`팝업 우클릭 모니터 2` 설정 기본 ON)
- 단일 모니터: 모니터 1 fallback

놀보드 내부 위젯, 탭, 드로어는 이 규칙의 대상이 아니다. 위젯 버튼은 별도 창 버튼과 구분되도록 과하지 않은 teal/slate 톤을 사용한다.

### 📅 일정 중심 캘린더 UX

- `일정`과 `일정 메모`가 별도 기능처럼 보이던 중복을 정리했다.
- 중심 개념은 일정이며 메모는 `메모 · 준비사항` 선택 상세정보로 제공한다.
- 등록 흐름을 제목 → 날짜/시간 → 알림 → 구분 → 메모 순으로 정리했다.
- 새 일정 창 제목 자동 포커스, `Ctrl+Enter` 저장, `Esc` 취소를 지원한다.
- 메인 달력의 동작을 `새 일정`과 `일정 보기`로 명확히 구분한다.
- 기존 `TeacherCalendarEvent` / `calendar_events.json` 데이터 호환성을 유지한다.

### 📋 놀보드 위젯 안정화

실제 in-canvas 위젯은 13종이다.

`timer`, `picker`, `dice`, `wheel`, `score`, `drawing`, `timetable`, `meal`, `memo`, `checklist`, `qr`, `weather`, `dday`

- `🌱 뽑기 레이스(pinball)`는 위젯이 아니라 별도 `StudentPickerWindow` 도구로 명확히 분리했다.
- `+ 위젯` 목록에서 pinball을 제거하고 별도 창 버튼 톤으로 표시한다.
- 뽑기 레이스도 왼클릭 모니터1 / 우클릭 모니터2 규칙을 따른다.
- 위젯의 열기/닫기 이후에도 위젯 전용 버튼 색 구분이 유지된다.
- 공통 `BoardWidgetHost`의 이동, 잠금, 닫기, zoom, 8방향 resize 구조를 유지한다.
- Timer/Picker/Dice/Wheel/Timetable/Meal/Weather 등 장시간 작업 위젯은 닫기·Hide 시 timer/event/async 작업을 정리하거나 취소한다.

### 💾 로컬 저장 안정성

- 학생 데이터의 **Local-Only / Data-Minimization** 원칙을 유지한다.
- 핵심 수업 기능은 학생 이름 없이 번호만으로 사용할 수 있다.
- Score 위젯은 raw JSON 덮어쓰기 대신 `SafeLocalJsonStore`의 원자적 저장과 로컬 backup을 사용한다.
- Memo 위젯은 키 입력마다 파일을 쓰지 않고 짧은 debounce 후 `SafeLocalFileStore`로 원자적 저장한다.
- Memo 위젯을 닫거나 비활성화할 때 남아 있는 TTS도 정리한다.
- QR 위젯 오류는 더 이상 완전히 묵살하지 않고 안전한 사용자 안내를 제공한다.

## 주요 기능

### 교사 업무 & 학급 관리

- 번호 우선 학생 명렬 및 선택형 이름/아바타
- 과제·준비물 체크리스트
- 누가기록 및 NEIS 서술형 평어 보조
- NEIS Excel/클립보드 입력 보조
- 17개 시도 교육청 업무포털 / K-에듀파인 / 4세대 NEIS / EVPN 바로가기
- QR 생성, 전자서명·직인

### 수업 진행

- 교실 타이머
- 발표자 추첨 및 32종 동물 뽑기 레이스
- 통합 판서 스튜디오
- 스마트 실물화상기
- 플로팅 도크와 전역 단축키
- 소음 신호등, 자리 바꾸기, 사운드보드

### 학생 제시 — 놀보드

- 모니터 2 기본 학생 제시 화면
- 13종 in-canvas 위젯
- 위젯 이동·8방향 크기조절·잠금·닫기·재열기
- 레이아웃 로컬 저장 및 복원
- 칠판/화이트/다크 테마와 판서 수학교구

### 교실 운영

- 커스텀 메인 위젯
- 시간표, 급식, 날씨·미세먼지
- 일정/알림과 D-Day
- 교시 예비령/카운트다운
- 반복 스케줄 및 예약

## 데이터 원칙

KnolTeacher는 학생·학급 개인정보를 서버나 클라우드에 자동 저장하지 않는다.

1. 저장하지 않아도 되는 데이터는 저장하지 않는다.
2. 저장이 필요한 데이터는 사용자 PC 로컬에만 저장한다.
3. 이름 없이 가능한 기능은 학생 번호만으로 완전히 동작한다.
4. 영구 저장이 필요한 작은 설정/데이터는 원자적 저장과 로컬 backup을 우선한다.
5. 실제 학생 개인정보, 평어, 학교 계정 정보는 저장소와 테스트 fixture에 넣지 않는다.

## 개발 및 검증

```powershell
dotnet restore KnolTeacher.sln
dotnet build KnolTeacher.sln -c Release --no-restore
dotnet test KnolTeacher.sln -c Release --no-build --no-restore
```

올인원 패키징:

```bat
publish.bat
```

정상 완료 시 `dist-net`에는 `놀티쳐.exe` 한 파일만 존재한다.

현재 개발 규칙은 `AGENTS.md`, 상세 진행 상태는 `docs/DEVELOPMENT_MASTER_PLAN.md`, 현재 아키텍처 인수인계는 `docs/PROJECT_CONTEXT.md`를 참고한다.

## 과거 버전

v3.0.8 이하의 상세 변경 이력은 GitHub Releases와 git history에서 확인한다. 현재 아키텍처와 신규 개발 판단은 반드시 최신 `main`을 기준으로 한다.