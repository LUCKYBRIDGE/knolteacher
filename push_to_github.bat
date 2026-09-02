@echo off
chcp 65001 > nul
echo ===================================================
echo [티처메이트] GitHub 저장소(LUCKYBRIDGE/teachermate)에 소스코드 업로드
echo ===================================================
echo.

if not exist ".git" (
    echo [1/4] Git 저장소를 초기화합니다...
    git init
    git branch -M main
    git remote add origin https://github.com/LUCKYBRIDGE/teachermate.git
)

echo [2/4] 변경된 파일들을 추가합니다...
git add .

echo [3/4] 최신 커밋을 생성합니다...
git commit -m "Update TeacherMate Pro v5.7 - Auto-Updater and UI Polish"

echo [4/4] GitHub로 푸시합니다...
git push -u origin main

echo.
echo ===================================================
echo [완료] GitHub 업로드가 완료되었습니다!
echo 저장소 확인: https://github.com/LUCKYBRIDGE/teachermate
echo ===================================================
pause
