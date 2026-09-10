# KnolTeacher 현재 프로젝트 컨텍스트

> 이 문서는 **현재 .NET 8 WPF 구현**을 이해하기 위한 인수인계 문서이다. 과거 Python 버전의 `legacy-python/PROJECT_CONTEXT.md`를 현재 기준으로 사용하지 않는다.

## 1. 기준 상태

- 제품명: 놀티쳐 (KnolTeacher)
- 기준 버전: v3.0.9 Stable Release
- 자동 업데이트 연속성 기준선: v3.0.9 이후 설치본
- 플랫폼: Windows 10/11 x64
- 프레임워크: .NET 8 WPF
- 앱 프로젝트: `src/KnolTeacher.Desktop/KnolTeacher.Desktop.csproj`
- 버전 SSOT: `Directory.Build.props`의 `KnolTeacherVersion`
- 배포: self-contained, single-file, win-x64
- 로컬 사용자 실행 파일: `놀티쳐.exe`
- GitHub Release transport asset: `KnolTeacher.exe`

버전과 브랜치는 계속 변경되므로 작업 시작 시 현재 `main`, 최신 Release, 열린 PR, Actions와 `Directory.Build.props`를 다시 확인한다. v3.0.9 이후 첫 데스크톱 코드 변경은 반드시 중앙 버전을 다음 버전으로 올린 뒤 진행한다.

## 2. 제품 정의

KnolTeacher는 단순한 도구 모음보다 **교실 운영 환경(Classroom Operating Environment)**에 가깝다. 다음 네 영역을 하나의 Windows 앱에 통합한다.

### 교사 업무 & 학급 관리

- 번호 우선 학생 명렬과 선택형 이름/아바타
- 과제/준비물 체크리스트
- 누가기록 및 NEIS 서술형 평어 보조
- NEIS Excel/클립보드 입력 보조
- 17개 시도 교육청 업무포털 / K-에듀파인 / NEIS / EVPN 바로가기
- QR 생성, 전자서명·직인

### 수업 진행

- 교실 타이머
- 발표자 추첨
- 32종 동물 뽑기 레이스
- 통합 판서 스튜디오
- 스마트 실물화상기
- 플로팅 도크와 전역 단축키
- 소음 신호등, 자리 바꾸기, 사운드보드

### 학생 제시

- 놀보드(StudentDisplayWindow)
- 13종 in-canvas 위젯
- 모니터 2 기본 학생 화면
- 위젯 이동, 8방향 resize, 잠금, 닫기, 재열기, 레이아웃 저장

### 교실 운영

- 메인화면 커스텀 위젯
- 시간표, 급식, 날씨/미세먼지
- 일정, 알림, D-Day
- 교시 예비령/카운트다운
- 반복 스케줄 및 예약

## 3. 핵심 아키텍처

### App / MainWindow

- `App.xaml`, `App.xaml.cs`: 앱 수명주기, DI, 전역 초기화, 단축키 연결
- `MainWindow.xaml`, `MainWindow.xaml.cs`: 메인 대시보드 및 주요 기능 진입점
- `MainWindow.V309Ux.cs`: v3.0.9 런타임 버전/팝업 멀티 모니터 UX 보완

`MainWindow`는 여전히 큰 code-behind를 가진 핵심 기술 부채다. 전체 재작성보다 기능 영역별 View/ViewModel/Service 분리를 단계적으로 진행한다.

### 주요 Services

- `ConfigService`: 설정과 위젯 레이아웃 로컬 저장
- `SafeLocalFileStore` / `SafeLocalJsonStore`: 원자적 로컬 저장, backup/복구 기반
- `StudentManagerService`: 번호 우선 학생 관리
- `ClassroomRecordService`: 교사 기록/체크리스트/NEIS 참고 자료
- `DisplayManager`: 모니터 탐색과 창 이동
- `GlobalHotkeyService`: 전역 단축키
- `TimetableService`: 시간표
- `SchedulerService`: 반복 예약/알림
- `AcademicCalendarService`: 학교 학사일정
- `WeatherService`: 학교 위치 기반 날씨/미세먼지
- `NeisService`, `NeisCommentBatchService`: NEIS 보조
- `QrCodeService`: QR 생성
- `UpdateService`: GitHub Release 확인, 안전 다운로드, 교체, 재실행

## 4. 데이터 정책

학생·학급 개인정보는 Local-Only가 원칙이다.

- 학생 데이터를 KnolTeacher 서버/클라우드/원격 텔레메트리로 자동 전송하지 않는다.
- 저장하지 않아도 되는 데이터는 저장하지 않는다.
- 핵심 수업 기능은 학생 이름 없이 번호만으로 동작한다.
- 이름/성별/아바타 등 개인 식별 정보는 선택 기능이다.
- 영구 저장이 필요한 작은 데이터는 가능한 한 SafeLocal 저장 계층을 사용한다.
- 실제 학생 개인정보, 평어, 학교 계정 정보는 저장소/로그/테스트 fixture에 넣지 않는다.

기본 설정 폴더는 사용자 홈의 `.knol_teacher_desk`다. 저장 실패 로그에는 파일 내용이나 사용자별 전체 경로를 기록하지 않는다.

## 5. 놀보드 구조

### 실제 in-canvas 위젯 13종

`WidgetRegistry` 기준:

1. timer
2. picker
3. dice
4. wheel
5. score
6. drawing
7. timetable
8. meal
9. memo
10. checklist
11. qr
12. weather
13. dday

`pinball`은 WidgetRegistry 위젯이 아니다. `StudentPickerWindow`를 사용하는 **별도 창 도구**다.

### 공통 Host

`BoardWidgetHost`가 다음 공통 계약을 담당한다.

- drag 이동
- N/S/E/W/NW/NE/SW/SE 8방향 resize
- 최소 크기 제한
- canvas 범위 clamp
- 위치/크기 lock
- content zoom
- 닫기
- `IWidgetLifecycle` Activate/Deactivate/Dispose 연결

### lifecycle

장시간 동작이 있는 위젯은 hide/delete 시 자원을 정리한다.

- Timer: DispatcherTimer 중지/복원
- Picker: 진행 중 추첨 CancellationToken 취소
- Dice: 주사위 animation 취소
- Wheel: 회전 animation 취소
- Timetable: service event 구독/해제
- Meal: 비동기 NEIS 급식 요청 취소
- Weather: 비동기 날씨 요청 취소
- Memo: static notice event, 자동공지 timer, TTS 정리

Score와 Memo 영구 데이터는 로컬 SafeLocal 저장 계층을 사용한다.

## 6. 팝업 / 위젯 구분과 멀티 모니터 정책

기본 물리 환경:

- Monitor 1: 교사 메인 PC
- Monitor 2: 학생용 전자칠판/TV

학생 제시 화면인 놀보드 자체는 모니터 2 기본 배치를 유지한다.

사용자가 **독립 Window/Dialog를 여는 버튼을 명시적으로 누르는 경우**:

- 왼클릭 → 모니터 1
- 우클릭 → 모니터 2 (`팝업 우클릭 모니터 2` 설정 기본 ON)
- 단일 모니터 → 모니터 1 fallback

놀보드 내부 위젯, 탭, 드로어, 패널 전환은 popup 규칙 대상이 아니다. 실제 위젯 런처는 별도 Window 런처와 미묘하게 다른 teal/slate 톤을 사용한다.

뽑기 레이스는 위젯이 아니라 별도 Window이므로 이 popup 입력 규칙을 따른다.

## 7. 일정 / 캘린더

`TeacherCalendarEvent`와 `calendar_events.json`을 유지한다.

v3.0.9부터 UI의 중심 개념은 `일정`이다.

- 메모는 별도 기능이 아니라 일정의 선택 상세정보/준비사항
- 등록 흐름: 제목 → 날짜/시간 → 알림 → 구분 → 메모
- `Ctrl+Enter` 저장, `Esc` 취소
- 메인 달력: `새 일정` / `일정 보기`
- 기존 데이터 schema 호환 유지

## 8. 자동 업데이트 계약

v3.0.9가 자동 업데이트 연속성의 공식 기준선이다. v3.0.9 이전 배포본과의 자동 업데이트 호환은 필수 지원 범위가 아니다.

### 버전

`Directory.Build.props` → `.csproj` Version/AssemblyVersion/FileVersion/InformationalVersion → 실행 중 UI 표시는 같은 버전 계약을 사용한다. `3.0.9 → 3.0.10 → 3.1.0`처럼 자릿수와 minor가 바뀌는 경우에도 semantic version 비교를 사용한다.

### 파일명

- 개발/로컬 최종 산출물: `dist-net/놀티쳐.exe`
- GitHub Release asset: `KnolTeacher.exe`
- updater 구현상 허용 이름: `KnolTeacher.exe`, legacy `놀티쳐.exe`
- 공식 미래 Release transport 이름: `KnolTeacher.exe`
- `default.exe`, `setup.exe` 등 임의 이름은 허용하지 않는다.

### 검증/적용

1. GitHub latest stable Release 조회
2. 대상 asset 이름 확인
3. HTTPS GitHub URL 확인
4. 다운로드
5. 크기 확인
6. SHA-256 확인
7. 다운로드 exe embedded FileVersion 확인
8. 기존 프로세스 종료
9. 설치 위치 `놀티쳐.exe` 교체 재시도
10. 설치된 파일 SHA-256 재검증
11. 설치 위치의 새 `놀티쳐.exe` 실행
12. 완료 marker를 새 앱이 소비해 업데이트 완료 안내

임시 다운로드 파일을 그대로 새 제품 실행 파일처럼 사용하지 않는다.

## 9. Release 계약

- `vX.Y.Z` tag == `KnolTeacherVersion`
- Release commit은 검증된 `main`에 포함되어야 한다.
- Release workflow는 restore → build → test → `publish.bat`을 다시 수행한다.
- `dist-net`에는 `놀티쳐.exe` 한 파일만 있어야 한다.
- embedded FileVersion을 tag 버전과 비교한다.
- GitHub에는 `KnolTeacher.exe` 한 asset만 업로드한다.
- upload asset 크기와 digest를 검증한다.
- Release는 draft에서 asset 검증을 끝낸 뒤에만 stable로 공개한다.
- draft 생성 직후 GitHub API 반영 지연은 retry로 흡수하며, 검증 실패 시 stable 공개하지 않는다.

## 10. 검증 기준

```powershell
dotnet restore KnolTeacher.sln
dotnet build KnolTeacher.sln -c Release --no-restore
dotnet test KnolTeacher.sln -c Release --no-build --no-restore
```

```bat
publish.bat
```

기능별 smoke test에서 특히 확인한다.

- 앱 실행/종료
- 단일/듀얼 모니터
- 팝업 좌클릭/우클릭 위치
- 놀보드 Hide/재열기
- 13종 위젯 열기/닫기/재열기/이동/8방향 resize/lock
- timer/event/async 중복 동작 여부
- 일정 등록/수정/삭제/알람
- 업데이트 확인/다운로드/교체/재실행
- NEIS 입력은 비식별 샘플로 dry-run

## 11. 다음 구조 개선 방향

v3.0.9 안정화 이후의 우선순위는 기능 수 증가보다 다음 구조 개선이다.

1. MainWindow의 기능 영역별 View/ViewModel 분리
2. Window/Navigation/Dialog/Notification 책임의 공통 service화
3. 저장 오류를 사용자에게 전달할 수 있는 명시적 결과 계약
4. 핵심 Service 단위 테스트 확대
5. 실제 Windows classroom smoke checklist 정형화

현재 구현 상태가 문서보다 우선한다. 큰 변경 전 `AGENTS.md`와 `docs/DEVELOPMENT_MASTER_PLAN.md`를 다시 확인한다.