@echo off
cd /d "%~dp0"

set "PY=py -3"
where py >nul 2>nul || set "PY=python"
%PY% --version >nul 2>nul
if errorlevel 1 (
    echo.
    echo   [ERROR] Python not found.
    echo   Install Python from https://python.org
    echo   IMPORTANT: check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo.
    echo   First run - installing packages. This takes 1-2 minutes...
    echo.
    %PY% -m venv .venv
    call ".venv\Scripts\activate.bat"
    python -m pip install -q --upgrade pip
    pip install -q -r requirements.txt
) else (
    call ".venv\Scripts\activate.bat"
)

python main.py
pause
