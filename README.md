# 🏫 놀티쳐 (KnolTeacher) v3.0.1

> 대한민국 교사를 위한 Windows 올인원 수업·학급경영·스마트보드 데스크톱 애플리케이션

[![Latest Release](https://img.shields.io/github/v/release/LUCKYBRIDGE/knolteacher?label=Release&color=orange)](https://github.com/LUCKYBRIDGE/knolteacher/releases/latest)
[![CI](https://github.com/LUCKYBRIDGE/knolteacher/actions/workflows/ci.yml/badge.svg)](https://github.com/LUCKYBRIDGE/knolteacher/actions/workflows/ci.yml)
[![Platform](https://img.shields.io/badge/Windows-10%20%2F%2011-blue)](https://github.com/LUCKYBRIDGE/knolteacher)
[![Framework](https://img.shields.io/badge/.NET-8.0%20WPF-512BD4)](https://dotnet.microsoft.com/)

현재 주력 구현은 **C# / .NET 8 / WPF** 기반이다. 이전 Python/CustomTkinter 구현은 `legacy-python/`에 보관하며 신규 기능 개발 기준으로 사용하지 않는다.

## 다운로드

최신 사용 버전은 GitHub Releases에서 받는다.

- 최신 릴리스: **v3.0.1**
- 플랫폼: Windows 10/11 x64
- .NET 런타임: self-contained 배포이므로 별도 설치가 필요하지 않는다.
- WebView2를 사용하는 웹 기능은 Windows의 Microsoft Edge WebView2 Runtime을 사용한다. 일반적인 최신 Windows 10/11 환경에는 설치되어 있으나, 제거된 PC에서는 별도 설치가 필요할 수 있다.

> 개발자가 로컬에서 `publish.bat`을 실행하면 배포 파일은 `dist-net\놀티쳐.exe`로 정리된다.

## v3.0.1 주요 개선사항
- ⏱️ **타이머 종료 시 화면 창 유지 & 초과 시간 카운트**: 카운트다운 타이머가 0:00에 도달하더라도 창이 자동으로 사라지지 않고 초과 지연 시간(`0:00 (-0:15)`)을 붉은색으로 계속 표시하며, 교사가 ESC나 닫기 버튼을 누를 때까지 학생 화면에 유지.
- 🎒 **교시별 알람 수정·삭제 & 이동수업·전담수업 이동시간 프리셋**: 시간표 각 교시마다 개별적으로 알람 켜기/끄기(삭제) 지원. 이동 수업(10분 전), 특별실(7분 전), 전담 수업(5분 전) 등 이동시간을 반영한 원클릭 프리셋 및 시간표 행 내 알람 뱃지 제공.
- 🏫 **시군구 단위 정밀 지역 연동 (`강릉(우리학교)`)**: NEIS 학교 도로명주소 및 교육지원청 분석을 통해 "강원" 대신 **"강릉(우리학교)"** 등 시군구 단위로 정밀 표출하며, 해당 지역의 세부 시군구 날씨/미세먼지 직접 선택 지원.

## v3.0.0 핵심 기능

### 📋 학급 관리 허브 (명렬표 · 과제 체크리스트 · 누가기록)
- **학생 명렬표**: DataGrid 인라인 편집, 나이스/엑셀 일괄 복사-붙여넣기 파싱, 동물 아바타 무작위 셔플, UTF-8 BOM 엑셀 호환 CSV 양식 다운로드 & 백업.
- **과제 & 준비물 체크리스트**: 원터치 3색 상태 토글(O 제출완료 / X 미제출 / △ 확인중), 실시간 제출률 계산, **원클릭 미제출자 명단 텍스트 복사** (학부모 알림장·칠판 공지용).
- **누가기록 & 관찰일지**: 8대 영역별 학생 성장 관찰 기록 타임라인, **원클릭 나이스 서술형 종합 평어 자동 생성 & 복사**.

### 🏛️ 17개 시도 교육청 4대 포털 직통 & 100% 검증 교육 바로가기
- **교육청 4대 포털 원클릭 직통**: `[🚀 업무포털 (eduptl.kr)]`, `[💰 K-에듀파인]`, `[📝 4세대 나이스]`, `[🔒 EVPN 원격업무]`, `[📱 QR]` 연동 (강원 `kwe`, 서울 `sen`, 경기 `goe` 등 2026 최신 도메인 완벽 매핑).
- **100% 동작 검증 공식 교육 사이트 (16종)**: 핑키네 놀퀴즈 & 교실자료실(`https://pinky-ne.com/`), 아이스크림, T셀파, 엠티처, 두클래스, 비바샘, 인디스쿨, 띵커벨, 패들렛, 멘티미터, 에듀넷 티-클리어, 교원위, 학교알리미, 4세대 나이스 대국민서비스.

### 🧩 메인화면 커스텀 위젯 시스템
- 대시보드를 자유로운 캔버스 위젯 시스템으로 개편: 위젯 드래그 이동, 리사이즈, 숨김/추가(`[➕ 위젯 추가]`), 기본배치 초기화, 위치 잠금 기능 제공.
- 미니 위젯 4종 추가 탑재: 교실 집중 타이머, 발표자 뽑기, 학급 공지 배너, D-Day 카운트다운.

### ✏️ 스마트 판서 스튜디오 일원화 (`Alt+2`)
- 원터치 배경 전환: `[🖼️ 화면]`(화면 정지 캡처), `[🟩 칠판]`(초록 분필칠판), `[⬜ 화이트]`(화이트보드), `[📐 모눈]`(수학 격자 모눈종이).
- 펜 두께 선택(`2pt`, `4pt`, `8pt`, `16pt`), 수학교구(자, 삼각자, 각도기), 원클릭 클립보드 복사 및 사진 폴더 자동 백업(`[💾 저장]`).

### 📷 스마트 실물화상기 (AF/MF 초점 제어 & 선명화)
- 100% 풀 뷰포트 카메라 스트리밍 및 반응형 글래스모피즘 HUD 독.
- **초점 제어**: 원터치 `[⚡ AF 자동]` 및 수동 슬라이더·미세조절 `[➖]`/`[➕]` 스텝 제어.
- **교재 텍스트 선명화 필터 (`[✨ 선명화]`)**: 광학 줌이 없는 웹캠에서도 교재 작은 인쇄 글씨를 또렷하게 보정하는 Unsharp Mask 필터 탑재.
- 실물화상기 화면 위에서 원클릭으로 판서 스튜디오 즉시 진입 연동.

### 📺 교실 멀티 모니터 & 작업표시줄 UX 원칙
- **독립 교실 도구 창**: 타이머, 뽑기 레이스, 실물화상기, 학급 관리 허브 등은 별개의 창으로 실행되어 하단 작업표시줄에 독립 슬롯으로 표시.
- **올인원 전자칠판 (놀보드)**: 모니터 2에 상시 띄우는 학급 칠판으로, 내부에서 위젯을 열고 닫아도 작업표시줄에 별도 아이콘이 추가되지 않는 깔끔한 단일 창 유지.
- 교시 시작 전 대형 예비령 카운트다운(음수 초과 시간 표시 지원) 및 5분 전 모니터 1 알림 팝업.

### 📝 NEIS 평어 입력 보조
- Excel/클립보드 기반 학생별 평어 파싱 및 바이트 검사
- 학생 번호 기반 순차 입력 보조 및 플로팅 도우미
- 프로그램이 최종 저장을 대신하지 않고 교사가 검토 후 저장하도록 하는 안전한 흐름 유지

### 🎰 3단 어드벤처 뽑기 레이스
- i-Scream 스타일 3단 어드벤처 맵 (S-커브 헤어핀, 다이아몬드 미로 바위섬, 온전한 3D 솔방울, 3개 결승 비눗방울)
- 32종 동물 아바타 및 물리 충돌 완주 시뮬레이션

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
