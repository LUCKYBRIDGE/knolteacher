# 🏫 놀티쳐 (KnolTeacher) v2.6.0

> **대한민국 선생님들을 위한 고성능 스마트 올인원 교실 수업·학급경영·스마트보드 데스크**  
> *.NET 8 WPF 기반 완전 무설치 독립형 단일 실행 파일(`놀티쳐.exe`)로 초등·중등·고등학교 선생님들의 일과 관리, 17개 시도 K-에듀파인 교육청 업무포털, 핑키네 교실자료실, 나이스 시간표/급식 연동, 멀티 위젯 대형 수업 보드, 실물화상기, 집중 타이머, 화면 판서를 완벽하게 지원합니다.*

<div align="center">

[![최신 버전 다운로드](https://img.shields.io/badge/📥_최신_버전_다운로드-놀티쳐.exe-0284c7?style=for-the-badge&logo=windows)](https://github.com/LUCKYBRIDGE/knolteacher/releases/latest)
[![GitHub Release](https://img.shields.io/github/v/release/LUCKYBRIDGE/knolteacher?color=orange&label=Release&style=for-the-badge)](https://github.com/LUCKYBRIDGE/knolteacher/releases)
[![Platform](https://img.shields.io/badge/Platform-Windows_10_/_11-blue.svg?style=for-the-badge)](https://github.com/LUCKYBRIDGE/knolteacher)
[![Framework](https://img.shields.io/badge/.NET-8.0_WPF_Native-512BD4.svg?style=for-the-badge&logo=dotnet)](https://dotnet.microsoft.com/)

</div>

---

## 📥 다운로드 및 빠른 시작 (Quick Start)

### 1️⃣ 선생님용: 100% 무설치 단일 실행 파일 (`놀티쳐.exe`)
* 👉 **[🚀 최신 버전 놀티쳐.exe 다운로드하기 (GitHub Releases)](https://github.com/LUCKYBRIDGE/knolteacher/releases/latest)**
* 다운로드받은 **`놀티쳐.exe`**를 바탕화면에 두고 더블 클릭하시면 즉시 실행됩니다.
* **추가 설치 불필요**: .NET 8 런타임, 웹뷰(WebView2), OpenCV 그래픽스 등이 하나의 파일 내부에 완전히 번들링되어 있어, 타 PC에 별도 프로그램 설치 없이 파일 하나만 전달해도 바로 작동합니다.

### 2️⃣ 개발자용: .NET 8 솔루션 빌드
```bash
git clone https://github.com/LUCKYBRIDGE/knolteacher.git
cd knolteacher
dotnet build KnolTeacher.sln -c Release
```
단일 독립형 바이너리 패키징:
```bash
dotnet publish src/KnolTeacher.Desktop/KnolTeacher.Desktop.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -p:EnableCompressionInSingleFile=true -o dist-net
```

---

## 🌟 v2.6.0 주요 기능 소개

### 1. 🌐 유용한 교육 사이트 모음 & 17개 시도 K-에듀파인 업무포털
* **17개 시도 교육청 나이스/K-에듀파인 원클릭 접속**:
  - 강원, 서울, 경기, 부산, 대구, 인천, 광주, 대전, 울산, 세종, 충북, 충남, 전북, 전남, 경북, 경남, 제주
  - 소속 지역을 한 번 선택하면 기억하여, 매일 1초 만에 업무포털을 열 수 있습니다.
* **필수 교육 사이트 엄선 탑재**:
  - 🎯 **놀퀴즈 (KnolQuiz)**: 학생 참여형 실시간 퀴즈 및 게임
  - 🍦 **아이스크림 (i-Scream)**: 초등 교과수업 및 창체 대표 포털
  - 🎒 **T셀파 (티셀파)**: 천재교육 교과서 및 에듀테크 지원
  - 📚 **M티처 (엠티처)**: 미래엔 디지털 교과 수업자료
  - 🏫 **두클래스 (douclass)**: 동아출판 맞춤형 스마트 교수학습
  - 🍎 **인디스쿨 (indischool)**: 대한민국 초등교사 커뮤니티
  - 🔔 **띵커벨 (ThinkerBell)**: 워크시트 및 실시간 퀴즈
  - 🏛️ **에듀넷 티-클리어**: 교육부 국가 교육정보 포털
  - 🎨 **미리캔버스 / 캔바**: 프레젠테이션 및 학습지 제작
* **선생님 맞춤형 즐겨찾기 추가/삭제**: 자주 방문하시는 사이트를 자유롭게 추가하고 관리할 수 있습니다.

### 2. 🌸 핑키네 교실자료실 연동 배너 (`pinky-ne.com`)
* 메인 화면 사이드바 및 상단 배너를 통해 선생님 무료 학습지, 계절별 활동지, 교육자료가 풍부한 **핑키네 교실자료실**로 손쉽게 접속할 수 있습니다.

### 3. 🔄 실시간 최신 버전 확인 및 자동 업데이트 버튼
* 메인 창 우측 상단의 `[ 🔄 최신 상태 확인 (v2.6.0) ]` 버튼을 클릭하면, GitHub 공식 릴리스 API와 실시간 통신하여 현재 버전과 최신 버전을 비교하고 원클릭으로 최신 릴리스 페이지로 안내합니다.

### 4. 📋 학생용 인터랙티브 놀티쳐 보드 (`F2`)
* **위젯 자유 크기 조절 & 이동**: 타이머, 시간표, 급식, 주사위, 자리배치, 판서 등 여러 수업 도구 위젯을 보드 위에서 자유자재로 띄우고 배치.
* **위젯별 글자 크기 ± 미세 조절 버튼 탑재**: 창 크기를 바꾸지 않아도 위젯 안의 글씨와 숫자를 손쉽게 확대/축소.
* **수기 숫자 입력 지원**: 프리셋 버튼뿐만 아니라 원하는 분/초를 키보드로 직접 입력 가능.
* **앱 전체 양방향 실시간 동기화**: 보드 위젯에서 수정한 시간표, 타이머 설정이 메인 앱과 즉각 동기화됩니다.

### 5. 🎨 칠판 & 골든 스타 & 연필 신규 직관적 아이콘
* 교실 칠판, 배움의 별, 연필 모티브의 단순하고 산뜻한 고해상도 벡터 스타일 아이콘 적용.
* 작업표시줄과 바탕화면에서 대한민국 교사용 소프트웨어의 정체성을 한눈에 보여줍니다.

### 6. ⌨️ 전역 단축키 센터 (`Alt+1` ~ `Alt+9`, `F2`)
* `Alt+1` (돋보기), `Alt+2` (판서), `Alt+3` (타이머), `Alt+4` (실물화상기), `Alt+5` (녹화), `Alt+6` (캡처), `F2` (놀티쳐 보드)
* 선생님의 수업 스타일에 맞춰 단축키 커스텀 설정 가능.

### 7. ⏰ 수업 시간표 & 맞춤형 대형 카운트다운 알람
* NEIS 및 커스텀 시간표 지원.
* 수업 시작 전(예: 5분 전~3분 전) 설정한 모니터 화면에 대형 카운트다운 타이머가 표시되며, 종료음 및 사전 설정 문구를 표출합니다.

---

## 📜 라이선스 & 저작권
**Copyright 2026. 교사 서정완. All rights reserved.**  
*본 프로그램은 대한민국 교원들의 편리하고 스마트한 교육 환경을 위해 개발되었습니다.*
