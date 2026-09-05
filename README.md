# 🏫 놀티쳐 (KnolTeacher) v2.9.0

> 대한민국 교사를 위한 Windows 올인원 수업·학급경영·스마트보드 데스크톱 애플리케이션

[![Latest Release](https://img.shields.io/github/v/release/LUCKYBRIDGE/knolteacher?label=Release&color=orange)](https://github.com/LUCKYBRIDGE/knolteacher/releases/latest)
[![CI](https://github.com/LUCKYBRIDGE/knolteacher/actions/workflows/ci.yml/badge.svg)](https://github.com/LUCKYBRIDGE/knolteacher/actions/workflows/ci.yml)
[![Platform](https://img.shields.io/badge/Windows-10%20%2F%2011-blue)](https://github.com/LUCKYBRIDGE/knolteacher)
[![Framework](https://img.shields.io/badge/.NET-8.0%20WPF-512BD4)](https://dotnet.microsoft.com/)

현재 주력 구현은 **C# / .NET 8 / WPF** 기반이다. 이전 Python/CustomTkinter 구현은 `legacy-python/`에 보관하며 신규 기능 개발 기준으로 사용하지 않는다.

## 다운로드

최신 사용 버전은 GitHub Releases에서 받는다.

- 최신 릴리스: **v2.9.0**
- 플랫폼: Windows 10/11 x64
- .NET 런타임: self-contained 배포이므로 별도 설치가 필요하지 않는다.
- WebView2를 사용하는 웹 기능은 Windows의 Microsoft Edge WebView2 Runtime을 사용한다. 일반적인 최신 Windows 10/11 환경에는 설치되어 있으나, 제거된 PC에서는 별도 설치가 필요할 수 있다.

> 개발자가 로컬에서 `publish.bat`을 실행하면 배포 파일은 `dist-net\놀티쳐.exe`로 정리된다.

## v2.9.0 핵심 기능

### 📺 교실 멀티 모니터
교사 PC를 모니터 1, 전자칠판/TV를 모니터 2로 사용하는 환경을 기본 시나리오로 지원한다.

- 집중 타이머: 모니터 2 중앙 기본 표시
- 핀볼 발표자 추첨: 모니터 2 중앙 기본 표시
- 실물화상기: 모니터 2 중앙 기본 표시
- 놀보드: 모니터 2 전체화면 기본 표시
- 수업 예비령 카운트다운: 모니터 2 기본 표시
- 주요 도구에서 모니터 1 ↔ 모니터 2 원터치 전환 지원

### 📝 NEIS 평어 입력 보조
- Excel/클립보드 기반 학생별 평어 파싱
- 4세대 NEIS 입력 제한을 고려한 바이트 검사
- 학생 번호 기반 순차 입력 보조
- F8 기반 빠른 입력 및 다음 칸 이동
- 이전/다음/복사 제어가 가능한 플로팅 도우미
- NEIS와 놀티쳐를 함께 보기 위한 화면 분할 지원
- 프로그램이 최종 저장을 대신하지 않고 교사가 검토 후 저장하도록 하는 안전한 흐름 유지

### 🧩 놀보드
학생용 보조 화면에서 여러 수업 위젯을 동시에 사용하는 인터랙티브 보드이다.

현재 주요 위젯:
- 타이머
- 시간표
- 급식
- QR
- 메모
- 점수판
- 주사위
- 발표자 추첨
- 룰렛
- 판서

### 🎰 발표자 추첨
- 학생 명렬표 연동
- 학생별 동물 아바타
- 32종 아바타 선택/셔플
- 핀볼 방식 추첨
- 클래식 추첨/룰렛 계열 기능
- 놀보드 및 스마트 독 연동

### ✏️ 판서·수학교구
- 화면 전체 판서
- 놀보드 판서 위젯
- 자
- 삼각자
- 각도기
- 펜/형광펜/지우개/텍스트/Undo

### 📷 실물화상기
OpenCvSharp 및 DirectShow 기반 카메라 제시 기능을 제공한다.

### 📱 QR 및 교육 사이트
- URL/텍스트 QR 생성
- QR 이미지 복사/저장
- 교육 사이트 바로가기
- 17개 시도 K-에듀파인 업무포털
- 사용자 사이트 북마크

### ⏰ 시간표·예약·단축키
- 시간표
- 교시/예비령 알림
- 예약 실행
- 전역 단축키
- 스마트 독

## 프로젝트 구조

```text
knolteacher/
├─ AGENTS.md
├─ README.md
├─ KnolTeacher.sln
├─ publish.bat
├─ docs/
│  └─ PROJECT_CONTEXT.md
├─ src/
│  └─ KnolTeacher.Desktop/
│     ├─ App.xaml / App.xaml.cs
│     ├─ MainWindow.xaml / MainWindow.xaml.cs
│     ├─ Models/
│     ├─ Services/
│     ├─ ViewModels/
│     └─ Views/
│        ├─ Controls/
│        └─ Windows/
├─ assets/
└─ legacy-python/
```

## 개발

### 요구 환경
- Windows 10/11 x64
- .NET 8 SDK
- Visual Studio 2022 또는 호환 IDE 권장

### 빌드

```powershell
git clone https://github.com/LUCKYBRIDGE/knolteacher.git
cd knolteacher
dotnet restore KnolTeacher.sln
dotnet build KnolTeacher.sln -c Release
```

### 단일 실행 파일 배포

권장 방법:

```bat
publish.bat
```

성공 시:

```text
dist-net\놀티쳐.exe
```

## 개발 기준 문서

AI 도구나 새로운 개발 환경에서 작업을 시작할 때 다음 순서로 확인한다.

1. `AGENTS.md`
2. `docs/PROJECT_CONTEXT.md`
3. `src/KnolTeacher.Desktop/KnolTeacher.Desktop.csproj`
4. 현재 `main`, Release, PR, Actions 상태

`legacy-python/`의 문서는 과거 Python 구현 기록이며 현재 개발 기준이 아니다.

## 저장소 운영 원칙

- 신규 작업은 작업 브랜치에서 수행하고 PR로 `main`에 반영한다.
- `main`에 직접 기능 코드를 작성하지 않는다.
- 빌드 산출물(`.exe`, `.dll`, `bin/`, `obj/`, `dist-net/`)은 커밋하지 않는다.
- 학생 개인정보와 로컬 설정 파일은 저장소에 커밋하지 않는다.
- 기능 변경 시 README와 프로젝트 컨텍스트가 실제 구현과 어긋나지 않는지 확인한다.

## 라이선스 및 저작권

Copyright 2026. 교사 서정완. All rights reserved.
