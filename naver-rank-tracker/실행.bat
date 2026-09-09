@echo off
cd /d "%~dp0"

REM --- guard: running from inside a zip (only one file extracted to Temp) ---
if not exist "main.py" (
    echo.
    echo   [!] Files are missing.
    echo.
    echo   You may be running this from INSIDE a zip file.
    echo   Right-click the zip - Extract All - then open the extracted
    echo   folder and run this file again.
    echo.
    pause
    exit /b 1
)

set "PY=py -3"
where py >nul 2>nul || set "PY=python"
%PY% --version >nul 2>nul
if errorlevel 1 (
    echo.
    echo   [!] Python not found.
    echo.
    echo   1. Go to https://python.org  -  Downloads
    echo   2. Run the installer
    echo   3. IMPORTANT: check "Add Python to PATH" on the first screen
    echo   4. After install, run this file again
    echo.
    start "" https://www.python.org/downloads/
    pause
    exit /b 1
)

REM --- install only if the previous install actually finished ---
if not exist ".venv\.installed" (
    if exist ".venv" rmdir /s /q ".venv"
    echo.
    echo   First run - installing. This takes 1-3 minutes, please wait.
    echo   ^(A slow network or antivirus scan can make it longer.^)
    echo.
    %PY% -m venv .venv
    if errorlevel 1 goto :installfail
    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 goto :installfail
    echo ok> ".venv\.installed"
    echo.
    echo   Install finished.
    echo.
) else (
    call ".venv\Scripts\activate.bat"
)

python main.py
pause
exit /b 0

:installfail
echo.
echo   [!] Install failed.
echo.
echo   Check: internet connection / antivirus / company firewall.
echo   Then run this file again ^(it will retry from the start^).
echo.
if exist ".venv" rmdir /s /q ".venv"
pause
exit /b 1
