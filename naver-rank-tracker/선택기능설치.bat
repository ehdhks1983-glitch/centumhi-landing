@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist .venv call .venv\Scripts\activate.bat
echo 선택기능^(네이버 실측 검증 + 쿠팡 차단 우회^)용 실브라우저를 설치합니다...
pip install playwright
playwright install chromium
echo 완료. 진단.bat 로 정상 설치를 확인하세요.
pause
