# KnolTeacher 개발 지침

이 문서는 저장소 전체에 적용되는 개발 기준이다. 세부 로드맵은 `docs/DEVELOPMENT_MASTER_PLAN.md`를 따른다.

## 1. 현재 구현 기준

- 제품: 놀티쳐 (KnolTeacher)
- 현재 기준 버전: v3.0.9 (Stable Release)
- 자동 업데이트 연속성 기준선: v3.0.9 이후 설치본
- 버전 SSOT: 루트 `Directory.Build.props`의 `KnolTeacherVersion`
- 주력 구현: C# / .NET 8 / WPF
- 대상: Windows 10/11 x64
- 솔루션: `KnolTeacher.sln`
- 앱 프로젝트: `src/KnolTeacher.Desktop/KnolTeacher.Desktop.csproj`
- 과거 Python 구현: `legacy-python/`에 보관

작업 시작 시 문서에 적힌 버전을 그대로 신뢰하지 말고 GitHub의 현재 `main`, 최신 Release, 열린 PR, Actions와 `Directory.Build.props`의 `KnolTeacherVersion`을 먼저 확인한다. v3.0.9 stable 이후 데스크톱 앱 코드를 변경하는 첫 PR은 반드시 `KnolTeacherVersion`을 다음 버전으로 먼저 올린다.

## 2. 정보 우선순위

충돌이 있을 때 다음 순서를 따른다.

1. 현재 `main`의 실제 코드와 `Directory.Build.props`
2. 이 `AGENTS.md`
3. `docs/DEVELOPMENT_MASTER_PLAN.md`
4. `docs/PROJECT_CONTEXT.md`
5. `README.md`
6. `legacy-python/`

`legacy-python/`은 현재 아키텍처의 근거로 사용하지 않는다.

## 3. Git 작업 규칙

- `main`에 직접 수정하지 않는다.
- 최신 `main`에서 작업 브랜치를 만든 뒤 PR을 사용한다.
- 작업 시작 전에 main HEAD, 작업 브랜치 HEAD, 열린 PR, Actions, 최신 Release를 확인한다.
- 하나의 PR은 가능한 한 하나의 책임에 집중한다.
- 기능과 무관한 대규모 포맷팅을 섞지 않는다.
- `bin/`, `obj/`, `dist-net/` 등 빌드 산출물을 커밋하지 않는다.
- 빌드 성공만으로 완료로 판단하지 않고 관련 테스트와 패키징 검증을 수행한다.
- Release는 검증된 `main` 커밋만 대상으로 한다.

## 4. 제품의 불변 원칙

### 4.1 올인원 Windows 교사용 앱

KnolTeacher는 수업 도구, 놀보드, 학급 운영, 학생 제시, 교사업무 보조 기능을 하나의 Windows 데스크톱 앱에서 제공한다. 특별한 이유 없이 별도 설치 프로그램이나 별도 앱으로 분리하지 않는다.

### 4.2 Local-Only 학생 데이터

학생·학급 개인정보는 Local-Only를 기본 원칙으로 한다.

- 학생 개인정보를 KnolTeacher 서버, 클라우드 동기화, 원격 텔레메트리로 자동 전송하지 않는다.
- 외부 AI 서비스에 학생 이름, 평어, 누가기록, 연락처 등을 자동 전송하지 않는다.
- 외부 전송이 필요한 미래 기능은 별도 설계 검토와 명시적 사용자 동의 없이는 추가하지 않는다.
- 기능상 저장할 필요가 없는 학생 데이터는 저장하지 않는다.
- 민감 데이터 보호의 첫 수단은 암호화가 아니라 데이터 최소화다.

### 4.3 학생 번호 우선

핵심 수업 기능은 학생 이름 없이 번호만으로 완전히 동작해야 한다.

- 필수 식별자는 학생 번호다.
- 이름, 성별, 아바타 등은 선택 정보다.
- 발표자 추첨, 자리 배치, 모둠, 체크리스트, 점수 등은 번호만으로 사용할 수 있어야 한다.
- 이름이나 개별 기록이 필요한 교사 기록 기능은 수업 도구 도메인과 가능한 한 분리한다.

### 4.4 저장 정책

데이터는 다음 순서로 판단한다.

1. 저장하지 않아도 되는가? → 세션/메모리만 사용한다.
2. 저장이 필요한가? → 사용자 PC 로컬에만 저장한다.
3. 손실 시 문제가 큰가? → 원자적 저장, 검증, 로컬 백업/복구를 적용한다.
4. 민감한가? → 저장 필요성을 다시 검토하고 필요한 경우에만 로컬 보호를 추가한다.

작은 JSON/텍스트 영구 저장은 가능한 한 `SafeLocalJsonStore` / `SafeLocalFileStore`를 사용한다. 저장 실패를 빈 `catch { }`로 완전히 숨기지 않으며 로그에는 데이터 내용이나 사용자별 전체 경로를 남기지 않는다.

## 5. 아키텍처 경계

### Services
설정, 학생 번호/선택 명렬, 시간표, NEIS, QR, 스케줄, 디스플레이, 단축키, 업데이트 등 재사용 가능한 로직과 I/O를 둔다.

### Views/Windows
독립 창과 대화상자를 둔다. 멀티 모니터 이동은 가능한 한 `IDisplayManager`를 통해 처리한다.

### Views/Controls
놀보드 위젯과 판서 수학교구 등 재사용 가능한 UI를 둔다. 장시간 실행되는 위젯은 타이머, 이벤트 구독, 비동기 요청의 생명주기를 명시적으로 관리한다.

### ViewModels
새 UI 로직이나 대형 code-behind 분리는 테스트 가능성과 책임 분리에 실질적 이점이 있을 때 단계적으로 수행한다. 전체 UI를 한 번에 재작성하지 않는다.

### legacy-python
과거 구현 보존 전용이다. 사용자가 명시적으로 비교/마이그레이션을 요청하지 않는 한 신규 기능을 추가하지 않는다.

## 6. 놀보드 계약

현재 `WidgetRegistry`가 정의하는 실제 in-canvas 위젯은 13종이다.

- timer
- picker
- dice
- wheel
- score
- drawing
- timetable
- meal
- memo
- checklist
- qr
- weather
- dday

`pinball`(뽑기 레이스)은 놀보드 위젯이 아니라 `StudentPickerWindow` 독립 창 도구다. 위젯 목록이나 위젯 색상으로 오인시키지 않는다.

위젯 생명주기 원칙:

- 놀보드 Hide와 실제 위젯 삭제를 구분한다.
- Hide 시 불필요한 timer/polling/비동기 작업을 일시 중지한다.
- 다시 표시할 때 필요한 작업만 재개한다.
- 실제 삭제 시 timer 중지, event 구독 해제, CancellationToken 취소, 기타 리소스 해제를 보장한다.
- static 이벤트 또는 장수명 service 이벤트 구독은 반드시 해제 가능해야 한다.
- 공통 `BoardWidgetHost`의 이동, 8방향 resize, lock, close, zoom 계약을 유지한다.
- 전자칠판을 고려해 이동/리사이즈/닫기 hit target을 충분히 확보한다.

## 7. 교실 멀티 모니터 UX

기본 교실 시나리오:

- 모니터 1: 교사 PC
- 모니터 2: 학생용 전자칠판/TV

학생 제시 화면인 놀보드 자체는 모니터 2 기본 배치를 유지한다. 다만 **사용자가 버튼으로 명시적으로 여는 독립 Window/Dialog**는 다음 입력 계약을 따른다.

- 왼클릭: 모니터 1에서 연다.
- 우클릭: `팝업 우클릭 모니터 2` 설정이 켜져 있으면 모니터 2에서 연다.
- 해당 설정 기본값은 ON이다.
- 단일 모니터에서는 모니터 1로 안전하게 fallback한다.
- 놀보드 in-canvas 위젯, 탭, 드로어, 내부 패널 전환에는 이 규칙을 적용하지 않는다.
- 위젯 런처는 독립 창 런처와 구별되는 은은한 시각 톤을 유지한다.

전체화면, Topmost, 전역 단축키 기능은 다른 창의 제어권을 불필요하게 빼앗지 않도록 한다.

## 8. 일정 UX 원칙

개인 캘린더 데이터 모델의 중심 개념은 `일정`이다.

- 메모는 별도 경쟁 기능이 아니라 일정의 선택 상세정보/준비사항이다.
- 기존 `TeacherCalendarEvent`와 `calendar_events.json` 호환성을 불필요하게 깨뜨리지 않는다.
- 일정 등록, 선택일 보기, 월간 학사일정의 역할을 UI에서 명확히 구분한다.

## 9. NEIS 관련 안전 원칙

- 학생 번호/행 매칭이 어긋나지 않도록 입력 대상이 화면에서 확인 가능해야 한다.
- 자동 입력 기능은 교사의 검토를 대체하지 않는다.
- 최종 저장을 자동으로 확정하지 않는 안전장치를 임의로 제거하지 않는다.
- DOM/포커스 의존 기능은 실패 시 중단 가능하고 복구 가능해야 한다.
- 실제 학생 개인정보, 평어, 학교 계정 정보는 저장소·로그·테스트 fixture에 넣지 않는다.

## 10. 버전·문서 동기화

버전은 `Directory.Build.props`의 `KnolTeacherVersion` 한 곳에서 관리한다. `.csproj`의 `Version`, `AssemblyVersion`, `FileVersion`, `InformationalVersion`은 이 값을 소비하고 숫자를 별도 하드코딩하지 않는다.

- 최신 Release보다 데스크톱 코드가 변경되면 개발 버전은 최신 Release보다 커야 한다.
- 같은 다음 Release 후보 버전에 여러 검증된 PR을 누적할 수 있다.
- updater fallback에 실제 제품 버전을 하드코딩하지 않는다.
- 앱 화면의 버전 표시는 실행 중인 Assembly/FileVersion을 사용한다.

릴리스 버전을 확정할 때 점검한다.

- `Directory.Build.props`
- 실행 파일 embedded FileVersion
- `README.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/DEVELOPMENT_MASTER_PLAN.md`
- GitHub tag / Release / asset
- updater 다운로드·교체·재실행 계약

## 11. 검증

최소 검증:

```powershell
dotnet restore KnolTeacher.sln
dotnet build KnolTeacher.sln -c Release --no-restore
dotnet test KnolTeacher.sln -c Release --no-build --no-restore
```

Windows 올인원 패키징:

```bat
publish.bat
```

성공 후 `dist-net`에는 로컬 사용자용 `놀티쳐.exe` 한 파일만 존재해야 한다.

주요 smoke test:

- 앱 실행/종료
- 단일/다중 모니터
- 명시적 팝업 좌클릭/우클릭 표시 위치
- 놀보드 열기/Hide/재열기
- 13종 위젯 생성/닫기/재생성/이동/8방향 resize/lock
- 반복 생성·삭제 시 timer/event/async 중복 여부
- 타이머/추첨/실물화상기
- 설정 저장 후 재실행
- 업데이트 확인/다운로드/무결성 검증/교체/새 버전 재실행
- NEIS는 비식별 샘플로 dry-run

## 12. 단일 파일 Release / 자동 업데이트 계약

이 계약은 **v3.0.9 이후 설치본의 업데이트 연속성**을 위해 깨뜨리지 않는다. v3.0.9 이전 배포본에서의 자동 업데이트 호환은 필수 제품 계약이 아니다.

- 공식 Windows 배포물은 `win-x64`, self-contained, single-file 실행 파일 하나다.
- 로컬 사용자 실행 파일명은 `놀티쳐.exe`다.
- GitHub Release의 기본 transport asset 이름은 ASCII `KnolTeacher.exe`다.
- updater는 `KnolTeacher.exe`와 구현상 legacy `놀티쳐.exe`를 허용한다. 공식 미래 Release는 `KnolTeacher.exe`를 사용하며 `default.exe`, `setup.exe` 등 임의 이름을 허용하지 않는다.
- GitHub Release에는 실행 asset을 정확히 하나만 둔다.
- Release tag는 `vX.Y.Z`이고 `KnolTeacherVersion`과 일치해야 한다.
- 빌드된 실행 파일의 embedded FileVersion이 Release 버전과 일치해야 한다.
- updater는 GitHub HTTPS download URL, asset 크기, SHA-256 digest를 검증한다.
- 다운로드한 실행 파일 자체의 embedded version도 대상 Release와 일치해야 한다.
- 업데이트 적용 후 설치 위치의 `놀티쳐.exe`가 다운로드 파일과 같은 SHA-256인지 확인한 뒤에만 새 프로세스를 연다.
- 업데이트 완료 후에는 임시 다운로드 파일이 아니라 설치 위치의 새 `놀티쳐.exe`를 재실행한다.
- v3.0.9 이후 설치본은 별도 installer 없이 앱의 버전 확인 → 업데이트 → 자동 재실행 흐름을 유지한다.
- `3.0.9 → 3.0.10 → 3.1.0`처럼 자릿수나 minor가 바뀌어도 semantic version 순서로 비교해야 한다.
- 개발 커밋마다 Release하지 않고 검증된 기능 묶음을 버전으로 확정한 뒤 Release한다.

## 13. 개발 로드맵

현재 단계별 계획과 완료 조건은 `docs/DEVELOPMENT_MASTER_PLAN.md`를 따른다. 큰 구조 변경 전에 해당 문서를 갱신하고, 실제 구현 상태가 계획 문서보다 우선한다.