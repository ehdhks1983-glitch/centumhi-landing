@echo off
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo Python이 설치되어 있지 않습니다.
    echo https://python.org 에서 설치할 때 "Add Python to PATH"를 꼭 체크하세요.
    pause
    exit /b 1
)

if not exist .venv (
    echo 최초 실행: 가상환경을 만들고 패키지를 설치합니다 ^(1~2분^)...
    py -3 -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -q -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

echo 서버를 시작합니다. 브라우저가 자동으로 열립니다.
echo 종료하려면 이 창에서 Ctrl+C 를 누르거나 창을 닫으세요.
start "" http://localhost:8000
python main.py
pause
