@echo off
setlocal
chcp 65001 > nul

echo ========================================================
echo   [놀티쳐 .NET] Windows x64 단일 실행 파일 빌드
echo ========================================================
echo.

where dotnet >nul 2>nul
if errorlevel 1 (
    echo [오류] dotnet CLI를 찾을 수 없습니다.
    echo .NET 8 SDK 설치 및 PATH 설정을 확인해 주세요.
    exit /b 1
)

set "PROJ_PATH=src\KnolTeacher.Desktop\KnolTeacher.Desktop.csproj"
set "OUT_DIR=dist-net"
set "RAW_EXE=%OUT_DIR%\KnolTeacher.Desktop.exe"
set "FINAL_EXE=%OUT_DIR%\놀티쳐.exe"

echo [0/3] 실행 중인 놀티쳐 프로세스 종료...
powershell -NoProfile -Command "Get-Process -Name 'KnolTeacher.Desktop','놀티쳐' -ErrorAction SilentlyContinue | Stop-Process -Force"

echo [1/3] 기존 배포 폴더 정리...
if exist "%OUT_DIR%" rmdir /s /q "%OUT_DIR%"
mkdir "%OUT_DIR%"

echo [2/3] Release / win-x64 / self-contained / single-file publish...
dotnet publish "%PROJ_PATH%" ^
  -c Release ^
  -r win-x64 ^
  --self-contained true ^
  -p:PublishSingleFile=true ^
  -p:PublishReadyToRun=true ^
  -p:IncludeNativeLibrariesForSelfExtract=true ^
  -p:EnableCompressionInSingleFile=true ^
  -o "%OUT_DIR%"

if errorlevel 1 (
    echo.
    echo [빌드 실패] dotnet publish 오류를 확인해 주세요.
    exit /b 1
)

if not exist "%RAW_EXE%" (
    echo.
    echo [빌드 실패] 예상 실행 파일을 찾을 수 없습니다: %RAW_EXE%
    exit /b 1
)

move /Y "%RAW_EXE%" "%FINAL_EXE%" >nul

echo [3/3] 사용자용 실행 파일명 정리 완료
echo.
echo ========================================================
echo   [빌드 성공]
echo   출력 파일: %FINAL_EXE%
echo ========================================================

exit /b 0
