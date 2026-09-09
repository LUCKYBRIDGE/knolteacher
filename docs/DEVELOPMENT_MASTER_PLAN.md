# KnolTeacher Development Master Plan

> 기준 제품: 놀티쳐 (KnolTeacher) v3.0.6
> 목적: 교사용 올인원 Windows 앱을 안정적으로 확장하면서 Local-Only 학생 데이터, 전자칠판 UX, 단일 파일 자동 업데이트 계약을 지킨다.

## 1. 제품 방향

KnolTeacher는 수업 도구, 놀보드, 학급 운영, 학생 발표, 교사업무 보조 기능을 하나의 Windows 데스크톱 앱에서 제공하는 Classroom Operating Environment를 지향한다.

현재 가장 중요한 목표는 기능 수를 급격히 늘리는 것이 아니라 다음 세 가지를 먼저 제품 기반으로 확정하는 것이다.

1. 장시간 교실 사용에서도 누수와 중복 동작이 없는 안정성
2. 학생 번호만으로 사용할 수 있는 Local-Only / Data-Minimization 구조
3. `놀티쳐.exe` 한 파일을 GitHub Release에서 받아 기존 설치본이 원클릭으로 업데이트되는 배포 구조

전체 재작성은 하지 않는다. 기존 .NET 8 WPF 코드와 서비스 경계를 유지하면서 단계적으로 분리한다.

---

## 2. 절대 요구사항

### 2.1 Local-Only / Data Minimization

- 학생·학급 개인정보는 서버나 클라우드에 자동 저장하지 않는다.
- 외부 텔레메트리로 학생 데이터를 보내지 않는다.
- 외부 AI 서비스에 학생 이름, 누가기록, 평어, 연락처 등 민감정보를 자동 전송하지 않는다.
- 저장이 필요하지 않은 학생 데이터는 영구 저장하지 않는다.
- 핵심 수업 기능은 학생 이름 없이 번호만으로 동작한다.
- 학생 이름, 아바타, 교사 기록은 선택 기능으로 둔다.
- 향후 외부 전송 기능이 필요하면 별도 설계 검토와 명시적 사용자 동의를 전제로 한다.

### 2.2 올인원 단일 실행 파일

Windows 공식 Release는 다음 조건을 만족해야 한다.

- `win-x64`
- self-contained
- single-file
- 사용자 asset 이름: `놀티쳐.exe`
- GitHub Release의 앱 실행 asset은 `놀티쳐.exe` 한 파일
- 별도 installer/MSI/sidecar DLL을 기본 배포 방식으로 요구하지 않는다.

기존 사용자는 바탕화면의 `놀티쳐.exe`를 계속 사용하면서 앱의 버전 확인 기능으로 새 버전을 확인하고, 업데이트 버튼으로 다운로드·교체·재실행할 수 있어야 한다.

### 2.3 GitHub 중심 배포

- `main`: 실제 제품 코드의 기준
- PR + CI: 변경 검증 경로
- `vX.Y.Z` tag: 배포 확정점
- GitHub Release: 최종 사용자 배포 원천
- 앱 updater: GitHub latest Release만 확인

Release tag와 `.csproj` Version이 다르면 배포하지 않는다.

---

## 3. 현재 확인된 핵심 기술 부채

### P0 — 안정성

- `MemoWidgetView` static 이벤트 구독 해제 부재
- `MemoWidgetView` 1분 `DispatcherTimer` 생명주기 관리 부재
- `DDayWidgetView` static 이벤트 구독 해제 부재
- `TimetableWidgetView` 서비스 이벤트 구독 해제 부재
- `TimerWidgetView` 삭제/비활성화 시 timer 정리 계약 부재
- 놀보드 창은 닫을 때 `Hide()`만 하므로 위젯 백그라운드 작업이 계속 실행될 수 있음
- 여러 저장 코드에서 빈 `catch { }`로 실패가 숨겨짐
- CI가 현재 기능 테스트 없이 컴파일 성공 중심

### P0 — 업데이트/배포

- 기존 updater가 Release의 첫 `.exe`를 선택할 수 있어 배포 asset 계약이 느슨함
- 다운로드된 실행 파일의 cryptographic integrity 검증이 없음
- 기존 Release asset 이름이 사용자용 `놀티쳐.exe`와 불일치한 이력이 있음
- 자동 Release workflow가 없어 수동 배포 과정에서 버전/파일명 불일치 가능

### P1 — 놀보드 UX

- `BoardWidgetHost` resize가 우하단 한 방향만 지원
- resize hit area가 약 18×18로 전자칠판에서 작음
- 닫기 버튼이 약 22×22로 작음
- TitleBar 약 36px만 이동 handle 역할
- 모든 위젯이 동일한 `MinWidth=240`, `MinHeight=180`을 공유
- 콤보박스 경로에서 동일 위젯 중복 생성 가능
- layout 복원 중 `SpawnWidget()`이 저장을 유발하여 불필요한 중간 저장 발생
- toolbar 표시 상태 변화 시 widget clamp가 충분히 명시적이지 않음

### P1 — 구조

- `MainWindow.xaml`과 `MainWindow.xaml.cs`가 지나치게 많은 UI/업무 책임을 보유
- `MainViewModel`은 얇고 실제 로직 상당수가 code-behind에 남아 있음
- App composition root에서도 window routing/hotkey 동작 책임이 커지고 있음

---

## 4. 단계별 개발 계획

## Phase 0 — Foundation / Release Safety

상태: **진행 중**

목표: 이후 리팩터링과 기능 개발을 안전하게 수행할 기반을 만든다.

### 작업

- [x] `AGENTS.md`를 현재 v3.0.6 기준으로 갱신
- [x] Local-Only / 학생 번호 우선 원칙을 저장소 개발 헌법에 추가
- [x] 단일 파일 Release / updater 계약을 개발 헌법에 추가
- [x] `docs/DEVELOPMENT_MASTER_PLAN.md` 생성
- [x] `.csproj` single-file 설정에 all-content bundling 추가
- [x] `publish.bat`이 `dist-net/놀티쳐.exe` 하나만 남기도록 변경
- [x] CI에서 `publish.bat` 실행 및 단일 파일 산출물 검증
- [x] tag 기반 GitHub Release workflow 추가
- [x] updater가 정확히 `놀티쳐.exe`만 선택하도록 변경
- [x] updater가 GitHub HTTPS asset만 허용하도록 변경
- [x] updater에 Release asset size + SHA-256 digest 검증 추가
- [ ] PR CI 통과 확인
- [ ] Windows 실제 실행 smoke test
- [ ] 다음 정식 버전에서 기존 v3.0.6 설치본 → 새 버전 원클릭 업데이트 검증

### 완료 조건

- PR build 성공
- `dist-net`에 `놀티쳐.exe` 한 파일만 생성
- 공식 Release asset도 `놀티쳐.exe` 한 파일
- 잘못된 asset 이름, 크기 불일치, SHA-256 불일치 시 updater가 적용을 거부
- 정상 Release에서는 기존 앱의 버전 확인 → 다운로드 → 교체 → 재실행 흐름 유지

---

## Phase 1 — v3.0.7 Stability / Widget Lifecycle

목표: 놀보드를 반복해서 열고 닫거나 위젯을 생성/삭제해도 timer와 event handler가 누적되지 않게 한다.

### 설계

공통 lifecycle 계약을 도입한다.

```csharp
public interface IWidgetLifecycle
{
    void Activate();
    void Deactivate();
    void Dispose();
}
```

의미는 다음과 같이 고정한다.

- `Activate`: 화면에 다시 표시되었을 때 필요한 timer/polling/data refresh 재개
- `Deactivate`: 놀보드 Hide 등 일시 비활성화 시 불필요한 timer/polling 중지
- `Dispose`: 위젯 실제 삭제 또는 앱 종료 시 event unsubscribe, timer stop, cancellation, disposable resource 해제

### 작업

- [ ] `IWidgetLifecycle` 도입
- [ ] `BoardWidgetHost`가 content lifecycle을 호출하도록 연결
- [ ] `StudentDisplayWindow.Show/Hide`와 widget activate/deactivate 연결
- [ ] 실제 widget remove 시 dispose 호출
- [ ] 앱 종료 시 전체 widget dispose
- [ ] `MemoWidgetView` static event 익명 람다 제거 및 명시적 unsubscribe
- [ ] `MemoWidgetView` timer activate/deactivate/dispose
- [ ] `DDayWidgetView` static event unsubscribe
- [ ] `TimetableWidgetView` service event unsubscribe
- [ ] `TimerWidgetView` timer lifecycle 처리
- [ ] `WeatherWidgetView` 등 비동기 요청에 `CancellationToken` 적용
- [ ] 위젯 20회 이상 생성/삭제 반복 smoke test
- [ ] 놀보드 Hide/Show 반복 시 중복 notification/tick 확인

### 완료 조건

- 닫힌 위젯의 timer가 계속 tick하지 않음
- static/service event handler가 반복 생성만큼 누적되지 않음
- 놀보드를 Hide한 동안 불필요한 polling이 정지
- 다시 표시했을 때 기능이 정상 복원

---

## Phase 2 — v3.1.0 NolBoard Workspace UX

목표: 전자칠판에서 자연스럽게 이동·리사이즈 가능한 widget workspace로 개선한다.

### 작업

- [ ] 8방향 resize 또는 WPF Adorner 기반 resize 도입
- [ ] 실제 touch hit area 32 DIP 이상 확보
- [ ] TitleBar 44~48 DIP 수준으로 개선
- [ ] 닫기/조작 버튼 touch target 확대
- [ ] drag/pointer capture 안정화
- [ ] 위젯별 `MinWidth`, `MinHeight` 정의
- [ ] Widget Registry 도입
- [ ] 각 widget의 기본 size, min size, allow-multiple, resize/zoom capability 중앙 관리
- [ ] 콤보박스/도구바의 중복 생성 정책 통일
- [ ] toolbar 펼침/접힘 시 canvas boundary 재계산 및 clamp
- [ ] fullscreen/normal 전환 시 layout 보존 개선
- [ ] weather/meal 등 main ↔ NolBoard 디자인 및 data refresh 정책 정리

### 권장 WidgetDefinition 예시

```csharp
public sealed record WidgetDefinition(
    string Type,
    string Title,
    double DefaultWidth,
    double DefaultHeight,
    double MinWidth,
    double MinHeight,
    bool AllowMultiple,
    bool CanResize,
    bool CanZoom);
```

---

## Phase 3 — Local-Only Classroom Domain

목표: 학생 번호만으로 핵심 수업 기능이 완전히 작동하도록 학생 도메인의 의존성을 정리한다.

### 데이터 분류

#### App Settings — 로컬 저장

- theme
- hotkeys
- monitor selection
- widget layout
- 학생 수
- 비민감 UI 설정

#### Classroom Runtime — 기본 메모리

- 현재 추첨 상태
- 현재 레이스 결과
- 일시 모둠/점수 상태 중 보존이 불필요한 항목
- 일회성 수업 상태

#### Optional Local Records — 사용자가 기능을 쓸 때만 로컬 저장

- 학생 이름
- 누가기록
- 체크리스트 장기 기록
- NEIS 보조용 교사 기록

### 작업

- [ ] 학생 identity에서 `Number` 필수, `DisplayName` 선택 구조 확립
- [ ] 이름이 null/empty여도 모든 classroom tool 정상 작동
- [ ] 발표자 추첨/자리/모둠/체크/점수의 name dependency 제거
- [ ] classroom tool과 teacher record domain 경계 강화
- [ ] 불필요한 runtime persistence 제거
- [ ] 학생 개인정보가 network request/log에 포함되지 않는지 검토

---

## Phase 4 — Local Persistence Reliability

목표: 클라우드를 도입하지 않고 로컬 데이터 손실 가능성을 줄인다.

### 작업

- [ ] 공통 `SafeFileStore` 도입
- [ ] temp write → flush → validate → atomic replace
- [ ] 중요 로컬 데이터 `.bak` 또는 versioned local backup
- [ ] JSON schema version 도입
- [ ] corruption fallback / recovery
- [ ] migration framework
- [ ] empty `catch { }` 제거 또는 로깅 가능한 오류 정책으로 변경
- [ ] 로그에 학생 이름/평어/연락처/NEIS 내용 기록 금지
- [ ] 사용자에게 실제 조치가 필요한 저장 실패만 UI notification

암호화는 저장 필요성 검토 이후에도 보호 가치가 있는 데이터에만 별도 적용한다. 데이터 최소화를 대체하지 않는다.

---

## Phase 5 — MainWindow Incremental Decomposition

목표: 기능 회귀 없이 거대한 MainWindow의 책임을 단계적으로 분리한다.

### 후보 분리 순서

1. Weather
2. Calendar / D-Day
3. Timetable
4. Notice / Memo
5. Classroom status widgets
6. Quick tools / site shortcuts
7. NEIS panel

각 영역을 가능한 경우 `View + ViewModel + Service` 경계로 이동한다.

### 금지

- 전체 WPF UI 동시 재작성
- 기능 리팩터링과 대규모 디자인 변경을 한 PR에 혼합
- 서비스 경계를 무시한 ViewModel 비대화

---

## Phase 6 — Test / CI Expansion

목표: 빌드 성공을 넘어 주요 도메인 회귀를 자동 검출한다.

### 우선 테스트 대상

- `UpdateService` version parsing / asset selection / digest parsing
- `TimetableService`
- `AcademicCalendarService`
- `SchedulerService`
- `StudentManagerService`
- `ClassroomRecordService`
- `NeisCommentBatchService`
- `EarlyLeaveCalculator`
- `WorkdayCalculator`
- layout serialization/migration

WPF UI automation은 처음부터 전 범위로 도입하지 않는다. 순수 로직과 persistence를 먼저 테스트한다.

---

## 5. Release 운영 절차

정식 Release는 아래 순서를 따른다.

1. 기능/수정 PR들을 `main`에 병합
2. `main` 최신 CI 확인
3. `.csproj` Version / AssemblyVersion / FileVersion 변경
4. `README.md`, `docs/PROJECT_CONTEXT.md` 버전 및 변경사항 동기화
5. release candidate Windows smoke test
6. `vX.Y.Z` tag 생성
7. GitHub Actions Release workflow 실행
8. `놀티쳐.exe` 한 파일만 Release asset으로 생성되었는지 확인
9. 기존 설치본에서 버전 확인
10. 다운로드 → SHA-256 검증 → 기존 exe 교체 → 재실행 확인

개발 commit마다 Release하지 않는다.

---

## 6. Definition of Done

### 공통

- 최신 `main` 기준 브랜치
- build 성공
- 관련 테스트 성공
- 민감 데이터 외부 전송 추가 없음
- 새 persistent data가 있으면 저장 필요성 검토
- 사용자 설정/기존 데이터 migration 고려
- 관련 문서 갱신

### 놀보드 변경

- single monitor
- dual monitor
- open / hide / reopen
- widget add / remove 반복
- fullscreen / normal
- toolbar collapse / expand
- layout save / restart / restore
- touch target 확인

### Release 변경

- `publish.bat` 성공
- `dist-net/놀티쳐.exe` 외 파일 없음
- Release asset 이름 정확히 `놀티쳐.exe`
- tag == project Version
- update URL HTTPS GitHub
- asset size 검증
- SHA-256 검증
- 교체 후 같은 경로에서 재실행

---

## 7. 현재 다음 작업

Phase 0 PR을 CI까지 통과시킨 후 바로 Phase 1 Widget Lifecycle 작업을 별도 PR로 시작한다.

Phase 1에서는 시각 디자인 변경을 최소화하고 memory/event/timer lifecycle 문제만 먼저 해결한다. 그 안정화가 완료된 다음 Phase 2에서 놀보드 resize와 touch UX를 변경한다.
