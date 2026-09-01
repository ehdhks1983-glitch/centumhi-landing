@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -3 move_to_d.py) || (python move_to_d.py)
if errorlevel 1 (
    echo.
    echo   If Python is missing, install it from https://python.org first.
    echo.
)
pause
