@echo off
setlocal
chcp 65001 > nul

echo ========================================================
echo   [놀티쳐 .NET] Windows x64 올인원 단일 실행 파일 빌드
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
set "RAW_DIR=%OUT_DIR%\_publish"
set "RAW_EXE=%RAW_DIR%\KnolTeacher.Desktop.exe"
set "FINAL_EXE=%OUT_DIR%\놀티쳐.exe"

echo [0/4] 실행 중인 놀티쳐 프로세스 종료...
powershell -NoProfile -Command "Get-Process -Name 'KnolTeacher.Desktop','놀티쳐' -ErrorAction SilentlyContinue | Stop-Process -Force"

echo [1/4] 기존 배포 폴더 정리...
if exist "%OUT_DIR%" rmdir /s /q "%OUT_DIR%"
mkdir "%RAW_DIR%"

echo [2/4] Release / win-x64 / self-contained / all-in-one single-file publish...
dotnet publish "%PROJ_PATH%" ^
  -c Release ^
  -r win-x64 ^
  --self-contained true ^
  -p:PublishSingleFile=true ^
  -p:PublishReadyToRun=true ^
  -p:IncludeNativeLibrariesForSelfExtract=true ^
  -p:IncludeAllContentForSelfExtract=true ^
  -p:EnableCompressionInSingleFile=true ^
  -p:DebugType=None ^
  -p:DebugSymbols=false ^
  -o "%RAW_DIR%"

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

echo [3/4] 사용자용 단일 실행 파일 생성...
copy /Y "%RAW_EXE%" "%FINAL_EXE%" >nul
if errorlevel 1 (
    echo [빌드 실패] 사용자용 실행 파일 복사에 실패했습니다.
    exit /b 1
)

rmdir /s /q "%RAW_DIR%"

echo [4/4] 단일 파일 산출물 검증...
powershell -NoProfile -Command "$files = @(Get-ChildItem -LiteralPath '%OUT_DIR%' -File -Recurse); if ($files.Count -ne 1 -or $files[0].Name -ne '놀티쳐.exe') { Write-Error ('배포 폴더에는 놀티쳐.exe 하나만 있어야 합니다. 현재 파일 수: ' + $files.Count); exit 1 }; $hash = (Get-FileHash -LiteralPath '%FINAL_EXE%' -Algorithm SHA256).Hash.ToLowerInvariant(); Write-Host ('SHA-256: ' + $hash)"
if errorlevel 1 (
    echo [빌드 실패] 올인원 단일 파일 검증에 실패했습니다.
    exit /b 1
)

echo.
echo ========================================================
echo   [빌드 성공]
echo   출력 파일: %FINAL_EXE%
echo   이 파일 하나만으로 배포합니다.
echo ========================================================

exit /b 0
