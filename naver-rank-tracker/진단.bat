@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    python doctor.py
) else (
    where py >nul 2>nul && (py -3 doctor.py) || (python doctor.py)
)
pause
