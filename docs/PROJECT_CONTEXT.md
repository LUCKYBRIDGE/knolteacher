# KnolTeacher 현재 프로젝트 컨텍스트

> 이 문서는 **현재 .NET 8 WPF 구현**을 이해하기 위한 인수인계 문서이다. 과거 Python 버전의 `legacy-python/PROJECT_CONTEXT.md`를 현재 기준으로 사용하지 않는다.

## 1. 기준 상태

- 제품명: 놀티쳐 (KnolTeacher)
- 기준 버전: v2.9.0
- 플랫폼: Windows 10/11 x64
- 프레임워크: .NET 8 WPF
- 앱 프로젝트: `src/KnolTeacher.Desktop/KnolTeacher.Desktop.csproj`
- 배포 방식: self-contained, single-file, win-x64
- 사용자용 로컬 배포 파일: `dist-net/놀티쳐.exe`

버전과 브랜치는 계속 변경될 수 있으므로 작업 시작 시 GitHub의 현재 상태와 `.csproj`를 다시 확인한다.

## 2. 제품 구조

놀티쳐는 네 영역을 하나의 데스크톱 앱으로 통합한다.

### 교사 업무
- NEIS 평어 Excel/클립보드 입력 보조
- 교육 사이트 및 K-에듀파인 바로가기
- QR 생성

### 수업 진행
- 타이머
- 발표자 추첨
- 판서
- 실물화상기
- 스마트 독
- 전역 단축키

### 학생 제시
- 놀보드
- 다중 위젯
- 학생 명렬/동물 아바타
- 모니터 2 기본 출력

### 교실 운영
- 시간표
- 교시/예비령 카운트다운
- 스케줄/예약
- 설정 저장

## 3. 주요 소스 영역

### App / MainWindow
- `App.xaml`, `App.xaml.cs`: 앱 수명주기와 전역 초기화
- `MainWindow.xaml`, `MainWindow.xaml.cs`: 메인 대시보드와 기능 진입점

### Services
- `ConfigService.cs`: 설정
- `DesktopCleanerService.cs`: 바탕화면 정리
- `DisplayManager.cs`: 모니터 탐색·배치
- `GlobalHotkeyService.cs`: 전역 단축키
- `NeisCommentBatchService.cs`: 평어 일괄입력 데이터 처리
- `NeisService.cs`: NEIS 관련 보조 로직
- `QrCodeService.cs`: QR 생성
- `SchedulerService.cs`: 예약/스케줄
- `SiteBookmarkService.cs`: 교육 사이트
- `StudentManagerService.cs`: 학생 명렬
- `ThemeService.cs`: 테마
- `TimetableService.cs`: 시간표

### 놀보드 위젯
`Views/Controls/Widgets/` 아래에 타이머, 시간표, 급식, 메모, QR, 점수판, 주사위, 추첨, 룰렛, 판서 위젯이 분리되어 있다.

### 독립 도구 창
`Views/Windows/` 아래에 놀보드, 타이머, 핀볼 추첨, 실물화상기, 화면 판서, NEIS 입력 도우미, 단축키 설정, 학생 명렬 관리 등의 창이 있다.

### 판서 수학교구
`Views/Controls/`의 `RulerToolControl`, `TriangleRulerToolControl`, `ProtractorToolControl`을 사용한다.

## 4. v2.9.0 디스플레이 정책

교실의 일반적인 듀얼 디스플레이 구성을 다음처럼 본다.

- Monitor 1: 교사 PC
- Monitor 2: 전자칠판/TV/학생용 화면

타이머, 핀볼 추첨, 실물화상기, 놀보드, 예비령 카운트다운은 모니터 2를 기본 대상으로 사용한다. 각 주요 창은 교사가 모니터 1과 2 사이를 즉시 전환할 수 있어야 한다.

단일 모니터 환경에서는 기본 모니터로 안전하게 fallback해야 한다.

## 5. NEIS 입력 흐름

현재 목표는 “무검토 완전자동 저장”이 아니라 **교사가 확인 가능한 빠른 입력 보조**이다.

일반 흐름:

```text
Excel/클립보드
→ 학생별 행 파싱
→ 바이트/입력 데이터 점검
→ 현재 대상 학생 표시
→ F8 또는 수동 복사
→ 다음 입력 칸 이동
→ 교사 검토
→ 교사가 NEIS에서 최종 저장
```

학생 순서가 밀리는 문제를 방지하는 것을 편의성보다 우선한다.

## 6. 배포

개발 빌드:

```powershell
dotnet restore KnolTeacher.sln
dotnet build KnolTeacher.sln -c Release
```

사용자용 single-file 빌드는 루트의 `publish.bat`을 사용한다.

`publish.bat`은 기존 `dist-net`을 정리한 뒤 win-x64 self-contained publish를 수행하고 최종 사용자용 EXE를 `dist-net/놀티쳐.exe`로 정리한다.

## 7. Legacy 정책

`legacy-python/`은 .NET 이전 구현을 보존하기 위한 디렉터리이다.

- 신규 기능 개발 금지
- 현재 빌드/실행 가이드로 사용 금지
- 현재 아키텍처의 근거로 사용 금지
- 마이그레이션 비교가 필요한 경우에만 참조

과거 자동 push 스크립트처럼 현재 저장소를 잘못 조작할 수 있는 파일은 보존 가치보다 위험이 크면 제거한다.

## 8. 다음 개발에서 우선 지킬 것

1. 실제 코드와 문서 버전의 동기화
2. 작업 브랜치 + PR
3. CI build 통과
4. 학생 개인정보를 저장소에 넣지 않기
5. 멀티 모니터와 단일 모니터 모두 확인
6. NEIS 자동화는 검토/중단/복구 가능성 유지
7. 기능 추가보다 기존 서비스와 View 경계를 우선 재사용
