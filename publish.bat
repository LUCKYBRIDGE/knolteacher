@echo off
chcp 65001 > nul
echo ========================================================
echo   [놀티쳐 .NET] 차세대 초고속 단일 실행 파일 빌드 시작
echo ========================================================
echo.

set DOTNET_EXE="C:\Program Files\dotnet\dotnet.exe"
set PROJ_PATH=src\KnolTeacher.Desktop\KnolTeacher.Desktop.csproj
set OUT_DIR=dist-net

echo [0/2] 기존 실행 중인 프로세스 종료 중...
powershell -Command "Get-Process -Name 'KnolTeacher.Desktop' -ErrorAction SilentlyContinue | Stop-Process -Force"

if not exist %OUT_DIR% (
    mkdir %OUT_DIR%
)

echo [1/2] Release Single-File ReadyToRun 빌드 진행 중...
%DOTNET_EXE% publish %PROJ_PATH% -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:PublishReadyToRun=true -p:IncludeNativeLibrariesForSelfExtract=true -o %OUT_DIR%

if %ERRORLEVEL% equ 0 (
    echo.
    echo ========================================================
    echo   [빌드 성공!]
    echo   출력 파일: %OUT_DIR%\KnolTeacher.Desktop.exe
    echo ========================================================
) else (
    echo.
    echo [빌드 실패] 에러 코드를 확인해 주세요.
)
pause
