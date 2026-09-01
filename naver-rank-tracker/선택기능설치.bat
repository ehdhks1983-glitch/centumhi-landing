@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo   Run the START file first, then come back.
    echo.
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"
echo.
echo   Installing real browser for Naver verification / Coupang bypass...
echo   This downloads about 150MB and takes a few minutes.
echo.
pip install playwright
playwright install chromium
echo.
echo   Done. Run the CHECK file to confirm.
echo.
pause
