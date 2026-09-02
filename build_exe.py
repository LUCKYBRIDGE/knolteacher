import os
import sys
import subprocess

def build():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("[Build] '놀티쳐 데스크.exe' 빌드를 시작합니다...")
    
    icon_path = os.path.abspath(os.path.join("assets", "app_icon.ico"))
    if not os.path.exists(icon_path):
        print(f"[Error] 아이콘 파일이 없습니다: {icon_path}")
        return False

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name=놀티쳐 데스크",
        f"--icon={icon_path}",
        f"--add-data=assets{os.pathsep}assets",
        "--collect-all=customtkinter",
        "main.py"
    ]

    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        exe_path = os.path.abspath(os.path.join("dist", "놀티쳐 데스크.exe"))
        print("\n===========================================")
        print("[Success] 빌드가 성공적으로 완료되었습니다!")
        print(f"생성된 실행 파일 경로: {exe_path}")
        if os.path.exists(exe_path):
            print(f"파일 크기: {os.path.getsize(exe_path) / (1024*1024):.2f} MB")
        print("===========================================")
        return True
    else:
        print("[Failed] 빌드 실패!")
        return False

if __name__ == "__main__":
    build()
