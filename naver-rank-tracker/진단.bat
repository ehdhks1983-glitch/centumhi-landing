@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist .venv call .venv\Scripts\activate.bat
python doctor.py
pause
