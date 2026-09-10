# KnolTeacher Development Master Plan

> 기준 제품: 놀티쳐 (KnolTeacher) v3.0.9 Stable Release  
> 자동 업데이트 지원 기준선: v3.0.9 이후 설치본  
> 목적: 교사용 올인원 Windows 앱을 안정적으로 확장하면서 Local-Only 학생 데이터, 전자칠판 UX, 단일 파일 자동 업데이트 계약을 지킨다.

## 1. 제품 방향

KnolTeacher는 수업 도구, 놀보드, 학급 운영, 학생 제시, 교사업무 보조 기능을 하나의 Windows 데스크톱 앱에서 제공하는 **Classroom Operating Environment**를 지향한다.

현재 우선순위는 기능 수를 빠르게 늘리는 것보다 다음 기반을 유지·강화하는 것이다.

1. 장시간 교실 사용에서도 timer/event/async 작업이 누적되지 않는 안정성
2. 학생 번호만으로 사용할 수 있는 Local-Only / Data-Minimization 구조
3. `놀티쳐.exe` 한 파일로 실행되는 배포와 안전한 GitHub 자동 업데이트
4. 독립 Window와 놀보드 in-canvas 위젯이 사용 전부터 구별되는 명확한 UX
5. 대형 MainWindow를 전체 재작성 없이 단계적으로 분리하는 구조 개선

---

## 2. 절대 요구사항

### 2.1 Local-Only / Data Minimization

- 학생·학급 개인정보를 서버나 클라우드에 자동 저장하지 않는다.
- 외부 텔레메트리로 학생 데이터를 보내지 않는다.
- 외부 AI 서비스에 학생 이름, 누가기록, 평어, 연락처 등 민감정보를 자동 전송하지 않는다.
- 저장이 필요하지 않은 학생 데이터는 영구 저장하지 않는다.
- 핵심 수업 기능은 학생 이름 없이 번호만으로 완전히 동작한다.
- 학생 이름, 성별, 아바타, 교사 기록은 필요한 기능에서만 선택적으로 사용한다.

### 2.2 올인원 단일 실행 파일

공식 Windows Release:

- win-x64
- self-contained
- single-file
- 로컬 사용자 실행 파일: `놀티쳐.exe`
- GitHub transport asset: `KnolTeacher.exe` 한 파일
- 별도 installer/MSI/sidecar DLL을 기본 배포 방식으로 요구하지 않는다.

### 2.3 GitHub 중심 배포

- `main`: 실제 제품 코드 기준
- PR + CI: 변경 검증 경로
- `vX.Y.Z`: 배포 확정 tag
- GitHub Release: 최종 사용자 배포 원천
- updater: GitHub latest stable Release 조회

Release tag, `Directory.Build.props`, 실행 파일 embedded FileVersion이 일치하지 않으면 배포하지 않는다.

### 2.4 자동 업데이트 지원 기준선

- 자동 업데이트 연속성의 공식 기준선은 **v3.0.9**다.
- v3.0.9 이후 정식 Release는 앱의 `버전 확인 → 다운로드 → 검증 → 설치 위치 교체 → 새 버전 자동 재실행` 흐름을 유지해야 한다.
- v3.0.9 이전 배포본과의 자동 업데이트 호환은 필수 제품 계약으로 두지 않는다.
- 앞으로 Release asset transport 이름은 `KnolTeacher.exe`를 기본으로 유지한다.
- 로컬 사용자 실행 파일명은 계속 `놀티쳐.exe`를 유지한다.

---

## 3. v3.0.7 ~ v3.0.9 안정화 결과

### Foundation / 저장 안정성 — 완료

- [x] 학생 번호 우선 / Local-Only 원칙을 `AGENTS.md`에 명문화
- [x] 기능상 필요 없는 개인정보를 저장하지 않는 Data-Minimization 원칙 확정
- [x] `SafeLocalFileStore` 원자적 저장/backup 기반 구축
- [x] `SafeLocalJsonStore` 검증된 JSON load/save/backup 복구 기반 구축
- [x] 주요 Config 저장 경로를 SafeLocal 계층으로 전환
- [x] Score 위젯 JSON을 SafeLocal 저장으로 전환
- [x] Memo 위젯을 debounce + atomic local 저장으로 전환

### 놀보드 lifecycle / layout — 완료

- [x] `IWidgetLifecycle` 계약 도입
- [x] Timer DispatcherTimer 정리
- [x] Picker/Dice/Wheel 진행 animation 취소
- [x] Timetable service event 구독/해제
- [x] Meal/Weather 비동기 요청 CancellationToken 취소
- [x] Memo static event / timer / TTS 정리
- [x] 놀보드 Hide와 실제 위젯 삭제 lifecycle 구분
- [x] 동일 위젯 중복 생성 방지
- [x] layout restore batch 중 불필요한 중간 저장 억제
- [x] empty custom workspace 복원
- [x] canvas 크기 변화 시 clamp/scale 복원

### 놀보드 조작 UX — 완료

- [x] `WidgetRegistry` 기반 13종 실제 위젯 정의
- [x] 위젯별 default/min size 계약
- [x] `BoardWidgetHost` N/S/E/W/NW/NE/SW/SE 8방향 resize
- [x] 전자칠판용 확대 hit target
- [x] drag 이동 / lock / close / zoom
- [x] 위젯 닫기 후 layout 저장 및 재열기
- [x] 위젯 launcher에 은은한 별도 색상 적용
- [x] 기존 active-state 코드가 위젯 색상 구분을 덮어쓰던 문제 보완
- [x] `pinball`을 위젯 목록에서 제거하고 별도 Window 도구로 분리
- [x] Registry 계약 테스트 추가

### 일정 UX — 완료

- [x] `일정`과 `일정 메모` 중복 개념 정리
- [x] Memo를 일정의 선택 상세정보/준비사항으로 재정의
- [x] 제목 → 날짜/시간 → 알림 → 구분 → 메모 입력 순서
- [x] Ctrl+Enter 저장 / Esc 취소
- [x] 메인 달력 `새 일정` / `일정 보기` 역할 구분
- [x] 기존 `TeacherCalendarEvent` / `calendar_events.json` schema 호환 유지

### 업데이트 / Release 안전성 — 완료

- [x] 버전 SSOT를 `Directory.Build.props`로 통합
- [x] UI 버전 표시를 실행 중 Assembly/FileVersion 기반으로 전환
- [x] local output `놀티쳐.exe` 한 파일 검증
- [x] GitHub transport asset을 ASCII `KnolTeacher.exe`로 분리
- [x] updater 허용 asset 이름을 `KnolTeacher.exe` + legacy `놀티쳐.exe`로 제한
- [x] GitHub HTTPS URL 제한
- [x] asset size 검증
- [x] SHA-256 digest 검증
- [x] 다운로드 exe embedded FileVersion 검증
- [x] 설치 위치 exe 교체 재시도
- [x] 설치 후 SHA-256 재검증
- [x] 설치 위치의 새 `놀티쳐.exe`만 재실행
- [x] 업데이트 완료 marker / 새 버전 안내
- [x] Release workflow restore/build/test/publish/asset 검증/stable publish 자동화
- [x] draft Release 생성 직후 GitHub API 반영 지연에 대한 retry 처리
- [x] v3.0.9 → v3.0.10 / v3.1.0 / v4.0.0 semantic version 회귀 테스트 추가

### 팝업 멀티 모니터 UX — 완료

- [x] 독립 Window/Dialog의 명시적 launcher만 popup 대상으로 정의
- [x] 왼클릭 → Monitor 1
- [x] 우클릭 → Monitor 2 설정, 기본 ON
- [x] 단일 모니터 fallback
- [x] in-canvas 위젯/탭/드로어 제외
- [x] 뽑기 레이스 별도 Window에도 동일한 명시적 클릭 규칙 적용

---

## 4. v3.0.9 Release 마감 상태

v3.0.9는 아래 자동 검증과 배포 조건을 모두 만족한 stable Release다.

- [x] 업데이트/팝업 UX PR CI 통과 및 main 병합
- [x] 일정 UX PR CI 통과 및 main 병합
- [x] 놀보드 안정화 PR CI 통과 및 main 병합
- [x] 문서의 버전/배포/멀티 모니터 계약을 실제 코드와 일치시킴
- [x] 문서 정합성 PR CI 통과 및 main 병합
- [x] main 최종 CI 성공 확인
- [x] `release/release-version.txt`를 3.0.9로 승격하는 Release PR 병합
- [x] Release workflow의 restore/build/test/publish 성공
- [x] GitHub latest stable tag가 `v3.0.9`
- [x] Release asset이 `KnolTeacher.exe` 정확히 1개
- [x] asset digest/size/embedded version 검증 성공
- [x] draft Release API race 재발 방지 workflow 보강 및 CI 통과
- [x] v3.0.9 이후 semantic version 업데이트 계약 테스트 보강
- [x] v3.0.9 마감 시점의 stale/superseded 열린 PR 정리

실제 Windows 교실 PC의 물리적 상호작용은 CI가 대체할 수 없으므로 다음 smoke test는 배포 후 운영 검증 항목으로 유지한다.

- v3.0.9 설치본 실행
- 이후 새 버전이 나왔을 때 버전 확인
- 새 버전 다운로드
- 교체
- 자동 재실행
- 상단 버전이 새 실행 파일의 실제 버전으로 표시되는지 확인
- 듀얼 모니터 popup 좌/우 클릭 확인
- 놀보드 위젯 반복 생성/닫기/재열기/resize

이 운영 smoke test에서 문제가 발견되면 같은 버전의 Release asset을 교체하지 않고 다음 patch 버전으로 수정한다.

---

## 5. v3.1 이후 구조 개선

v3.0.9 안정화 완료 후에는 기능 추가보다 구조적 위험을 단계적으로 줄인다.

### Phase A — MainWindow 책임 분리

우선 분리 후보:

- Dashboard
- Calendar
- Weather
- Timetable
- D-Day
- Notice
- NEIS panel
- widget customization

원칙:

- 전체 화면을 한 번에 MVVM으로 다시 쓰지 않는다.
- 기존 Service 경계를 재사용한다.
- 한 PR에 한 기능 영역을 옮긴다.
- 동작을 바꾸지 않는 구조 리팩터링과 기능 변경을 가능한 한 분리한다.

### Phase B — Window / Navigation 공통화

도입 후보:

- WindowManager / PopupLauncher
- NavigationService
- DialogService
- NotificationService
- WidgetRegistry 확장
- Command/Action registry

목표는 MainWindow와 App composition root가 개별 Window를 직접 많이 제어하는 결합을 줄이는 것이다.

### Phase C — 테스트 확대

우선 단위 테스트 후보:

- StudentManagerService
- TimetableService
- SchedulerService
- AcademicCalendarService
- ClassroomRecordService
- NeisCommentBatchService
- EarlyLeaveCalculatorService
- WorkdayCalculatorService
- update/version contract
- widget registry/layout serialization

WPF UI automation을 처음부터 광범위하게 도입하기보다 Service와 pure contract 테스트를 우선한다.

### Phase D — 저장 결과 계약

현재 SafeLocal 계층은 데이터 손상 위험을 크게 낮췄다. 다음 단계에서는 저장 성공/실패를 호출자에게 구조적으로 전달해 사용자가 중요한 데이터 저장 실패를 알 수 있도록 개선한다.

예시 방향:

```csharp
public sealed record SaveResult(bool Success, string? ErrorCode = null);
```

민감한 데이터 내용이나 전체 사용자 경로를 로그에 노출하지 않는 원칙은 유지한다.

---

## 6. 개발 우선순위

### P0 — 계속 유지해야 하는 계약

- Local-Only / 번호 우선
- 단일 파일 배포
- v3.0.9 이후 안전한 updater 연속성
- 위젯 lifecycle
- NEIS 최종 저장 수동 확인
- 듀얼 모니터 fallback

### P1 — 다음 구조 개선

- MainWindow 기능 영역 분리
- Window/Popup 공통 launcher 구조
- 저장 결과 계약
- Service 테스트 확대

### P2 — 이후 기능 확장

새로운 수업 도구나 학급 운영 기능은 P0/P1 계약을 깨지 않는 범위에서 추가한다.

---

## 7. 완료의 정의

코드 작성만으로 완료가 아니다. 관련 작업은 다음을 만족해야 한다.

1. 요구사항이 실제 코드에 반영됨
2. 기존 사용자 데이터와 호환됨
3. Local-Only 원칙을 유지함
4. 관련 테스트가 존재하거나 기존 테스트가 통과함
5. Windows Release build가 성공함
6. `dist-net/놀티쳐.exe` 한 파일 계약을 유지함
7. 문서가 실제 동작과 충돌하지 않음
8. 배포가 필요한 변경은 GitHub Release까지 검증됨
9. v3.0.9 이후 자동 업데이트 연속성을 깨는 변경은 허용하지 않음

실제 구현 상태가 계획 문서보다 우선하며, 계획과 구현이 달라지면 문서를 다시 맞춘다.
