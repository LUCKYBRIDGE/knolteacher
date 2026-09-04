@echo off
chcp 65001 > nul
echo ========================================================
echo   놀티쳐 (KnolTeacher) 빌드 및 바탕화면 자동 배포
echo ========================================================
echo.
python build_exe.py
echo.
pause
