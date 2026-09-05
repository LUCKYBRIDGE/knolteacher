# KnolTeacher 개발 지침

이 문서는 저장소 전체에 적용되는 개발 기준이다.

## 1. 현재 구현 기준

- 제품: 놀티쳐 (KnolTeacher)
- 현재 기준 버전: v2.9.0
- 주력 구현: C# / .NET 8 / WPF
- 솔루션: `KnolTeacher.sln`
- 앱 프로젝트: `src/KnolTeacher.Desktop/KnolTeacher.Desktop.csproj`
- 과거 Python 구현: `legacy-python/`에 보관

작업 시작 시 문서에 적힌 버전을 그대로 신뢰하지 말고 GitHub의 현재 `main`, 최신 Release, PR, Actions와 `.csproj`의 `Version`을 먼저 확인한다.

## 2. 정보 우선순위

충돌이 있을 때 다음 순서를 따른다.

1. 현재 `main`의 실제 코드와 `KnolTeacher.Desktop.csproj`
2. 이 `AGENTS.md`
3. `docs/PROJECT_CONTEXT.md`
4. `README.md`
5. `legacy-python/`의 파일

`legacy-python/`은 현재 아키텍처의 근거로 사용하지 않는다.

## 3. Git 작업 규칙

- `main`에 직접 수정하지 않는다.
- 작업 브랜치를 만든 뒤 PR을 사용한다.
- 작업 시작 전에 `main` HEAD, 작업 브랜치 HEAD, 열린 PR, Actions 상태를 확인한다.
- 기능 수정과 무관한 대규모 포맷팅은 함께 넣지 않는다.
- 빌드 산출물은 커밋하지 않는다.
- 릴리스용 실행 파일은 GitHub Release asset으로 관리한다.

## 4. 아키텍처 경계

### Services
설정, 학생 명렬, 시간표, NEIS, QR, 스케줄, 디스플레이, 단축키 등 재사용 가능한 로직을 둔다.

### Views/Windows
독립 창과 대화상자를 둔다. 멀티 모니터 이동은 가능한 한 `DisplayManager`를 통해 일관되게 처리한다.

### Views/Controls
놀보드 위젯과 판서 수학교구처럼 재사용 가능한 UI 컴포넌트를 둔다.

### legacy-python
과거 구현 보존 전용이다. 사용자가 명시적으로 마이그레이션이나 비교를 요청하지 않는 한 신규 기능을 추가하지 않는다.

## 5. 교실 UX 원칙

- 모니터 1은 교사용 화면, 모니터 2는 학생용 전자칠판/TV를 기본 시나리오로 본다.
- 학생에게 제시하는 도구는 모니터 2 기본 배치를 유지하되 교사가 즉시 모니터를 전환할 수 있어야 한다.
- 전체화면·Topmost·전역 단축키 기능은 다른 창의 제어권을 불필요하게 빼앗지 않도록 한다.
- 단일 모니터 환경에서도 기능이 실패하지 않도록 fallback을 유지한다.

## 6. NEIS 관련 안전 원칙

- 학생 번호/행 매칭이 어긋나지 않도록 입력 대상이 화면에서 확인 가능해야 한다.
- 자동 입력 기능은 교사의 검토를 대체하지 않는다.
- 최종 저장을 자동으로 확정하지 않는 현재 안전장치를 임의로 제거하지 않는다.
- NEIS DOM이나 포커스 동작에 의존하는 기능은 실패 시 중단 가능하고 복구 가능해야 한다.
- 실제 학생 개인정보, 평어, 학교 계정 정보는 저장소·테스트 fixture에 넣지 않는다.

## 7. 버전·문서 동기화

릴리스 버전을 변경할 때 최소한 다음을 함께 점검한다.

- `KnolTeacher.Desktop.csproj`의 Version / AssemblyVersion / FileVersion
- `README.md`의 표시 버전과 변경 기능
- `docs/PROJECT_CONTEXT.md`의 기준 버전
- GitHub Release의 tag/title/asset
- 배포 파일명

문서에 특정 커밋 SHA를 장기 기준으로 고정하지 않는다. SHA는 작업 시작 시 다시 확인한다.

## 8. 검증

최소 검증:

```powershell
dotnet restore KnolTeacher.sln
dotnet build KnolTeacher.sln -c Release --no-restore
```

Windows에서 릴리스 패키징이 필요한 경우:

```bat
publish.bat
```

주요 기능을 건드렸다면 관련 smoke test를 수행한다.

- 앱 실행/종료
- 전역 단축키 등록/해제
- 단일/다중 모니터
- 놀보드 열기/닫기와 위젯
- 타이머/추첨/실물화상기
- NEIS 입력은 샘플 데이터로 dry-run
- 설정 저장 후 재실행

## 9. 배포 파일명

로컬 릴리스 산출물의 사용자용 파일명은 `놀티쳐.exe`를 기본으로 한다. 내부 프로젝트/assembly 이름 `KnolTeacher.Desktop`과 사용자용 배포 파일명을 구분한다.
