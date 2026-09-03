@echo off
chcp 65001 > nul
echo ========================================================
echo   놀티쳐 (KnolTeacher) 개발 환경 자동 구축 스크립트
echo ========================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않거나 PATH에 등록되지 않았습니다.
    echo Python 3.10 이상을 설치하신 후 다시 실행해주세요.
    pause
    exit /b 1
)

echo [1/3] 가상환경(venv) 확인 및 생성 중...
if not exist "venv" (
    python -m venv venv
    echo     가상환경이 생성되었습니다.
) else (
    echo     기존 가상환경을 사용합니다.
)

echo.
echo [2/3] 필수 패키지 설치 중 (requirements.txt)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ========================================================
echo   [성공] 개발 환경 구축이 완료되었습니다!
echo   'python main.py'로 앱을 실행하거나,
echo   'python build_exe.py'로 단일 실행 파일을 빌드할 수 있습니다.
echo ========================================================
echo.
pause
