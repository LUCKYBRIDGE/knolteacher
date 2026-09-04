# 🏫 놀티쳐 (KnolTeacher) v2.7.0

> **대한민국 선생님들을 위한 고성능 스마트 올인원 교실 수업·학급경영·스마트보드 데스크**  
> *.NET 8 WPF 기반 완전 무설치 독립형 단일 실행 파일(`놀티쳐.exe`)로 나이스(NEIS) 학생 평어 엑셀 1초 일괄입력, 실시간 QR 생성기 및 학생 기기 공유, 17개 시도 K-에듀파인 교육청 업무포털, 핑키네 교실자료실, 멀티 위젯 대형 수업 보드, 실물화상기, 수업 예비령 카운트다운(모니터 2 전자칠판 권장), 화면 판서를 완벽하게 지원합니다.*

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

## 🌟 v2.7.0 주요 기능 소개

### 1. 📝 나이스(NEIS) 행동특성 및 학기말 종합의견 평어 엑셀 일괄입력 도구
* **표준 엑셀 양식 다운로드 (`.xlsx`)**: 번호, 성명, 평어 예시가 포함된 엑셀 템플릿을 1초 만에 생성.
* **엑셀 파일 열기 & 클립보드 바로 붙여넣기**: 엑셀에서 표 범위를 `Ctrl+C` 복사 후 버튼 클릭만으로 즉시 파싱.
* **4세대 나이스 규격(한글 UTF-8 3Byte, 줄바꿈 2Byte) 바이트 자동 검사**: 1,500 Byte 초과 시 ⚠️ 실시간 경고로 나이스 저장 거부 사전 방지.
* **[방식 1] 🚀 나이스 1초 일괄입력 코드 복사 (추천)**:
  - 4세대 나이스 웹 화면에서 `F12` 누르고 콘솔(`Console`)에 붙여넣기 후 `Enter`!
  - 학생 번호 1:1 매칭으로 전교생 평어가 1초 만에 오차(순서 밀림) 없이 자동 입력.
  - 자동 저장은 하지 않아 교사가 검토 후 최종 [저장]을 누르는 안전장치 완비.
* **[방식 2] 🖱️ 플로팅 순차 입력 도우미**:
  - 나이스 창 위에 떠 있는 컴팩트 플로팅 창으로 스페이스바나 클릭으로 번호별 순차 복사 지원.

### 2. 📱 실시간 QR코드 생성기 & 교육 콘텐츠 태블릿 공유
* **URL & 텍스트 즉시 QR 변환**: 학생들에게 나눠줄 웹 링크나 텍스트를 고화질 QR코드로 생성.
* **원클릭 공유 버튼**: 17개 시도 K-에듀파인 업무포털, 핑키네 교실자료실, 11개 주요 교육 사이트 카드마다 `[📱 QR]` 버튼 탑재 -> 학생 태블릿/크롬북 즉시 스캔 가능.
* **QR 이미지 클립보드 복사 & PNG 저장** 지원.
* **놀티쳐 보드 실시간 QR 위젯** 및 상단 스마트 독 탑재 (`Alt+Q` 전역 단축키).

### 3. ⏰ 수업 예비령 카운트다운 타이머 (모니터 2 전자칠판/TV 권장)
* 수업 시작 5분 전 ~ 3분 전 등 쉬는 시간 종료 예비령 알람 지원.
* 교실 환경(1번: 교사 PC, 2번: 전자칠판/대형 TV)에 맞춰 **모니터 2를 기본 권장 디스플레이로 자동 설정**.
* 사전 설정 완료 문구 및 알람 차임음 재생.

### 4. 🌐 유용한 교육 사이트 모음 & 17개 시도 K-에듀파인 업무포털
* 강원, 서울, 경기, 부산 등 17개 시도 교육청 업무포털 기억 및 원클릭 접속.
* 놀퀴즈, 아이스크림, T셀파, M티처, 두클래스, 인디스쿨, 띵커벨, 에듀넷 티-클리어 등 주요 교육 사이트 기본 탑재 및 사용자 맞춤 추가.

### 5. 📋 학생용 인터랙티브 놀티쳐 보드 (`F2`)
* 위젯 자유 크기 조절 & 배치, 위젯 내 글자 크기 ± 조절 버튼, 수기 숫자 입력 지원, 메인 앱 양방향 동기화.

### 6. ⌨️ 전역 단축키 센터 (`Alt+1` ~ `Alt+9`, `Alt+Q`, `F2`)
* 선생님 맞춤형 전역 단축키 등록 및 관리.

---

## 📜 라이선스 & 저작권
**Copyright 2026. 교사 서정완. All rights reserved.**  
*본 프로그램은 대한민국 교원들의 편리하고 스마트한 교육 환경을 위해 개발되었습니다.*
