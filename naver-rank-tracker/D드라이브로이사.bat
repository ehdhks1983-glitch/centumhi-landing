@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "TARGET=D:\자동화프로그램\순위추적기"

echo ============================================================
echo  순위추적기 - D드라이브로 옮기기
echo ============================================================
echo.

if not exist D:\ (
    echo [중단] D 드라이브를 찾을 수 없습니다.
    echo        USB나 외장하드라면 연결 상태를 확인하세요.
    echo.
    pause
    exit /b 1
)

if /i "%CD%"=="%TARGET%" (
    echo 이미 목적지에 있습니다. 옮길 필요가 없습니다.
    echo   %CD%
    echo.
    pause
    exit /b 0
)

echo  지금 위치 : %CD%
echo  옮길 위치 : %TARGET%
echo.
if exist "rank_tracker.db" (
    echo  * 그동안 쌓인 순위 데이터^(rank_tracker.db^)도 함께 옮겨집니다.
) else (
    echo  * 아직 순위 데이터가 없습니다. 프로그램 파일만 옮깁니다.
)
echo  * 설치 폴더^(.venv^)는 위치가 바뀌면 못 쓰므로 복사하지 않습니다.
echo    옮긴 뒤 실행.bat 을 누르면 자동으로 다시 만들어집니다.
echo.

set "OK="
set /p "OK=진행할까요? (Y 입력 후 엔터): "
if /i not "!OK!"=="Y" (
    echo 취소했습니다.
    pause
    exit /b 0
)

echo.
echo 복사하는 중입니다...
robocopy "%CD%" "%TARGET%" /E /XD ".venv" "__pycache__" ".git" /XF "*.log" /NFL /NDL /NJH /NJS /NP >nul
if !ERRORLEVEL! GEQ 8 (
    echo.
    echo [실패] 복사 중 오류가 발생했습니다.
    echo        D 드라이브의 남은 공간과 쓰기 권한을 확인하세요.
    echo.
    pause
    exit /b 1
)

if not exist "%TARGET%\main.py" (
    echo.
    echo [실패] 옮겨진 파일을 확인하지 못했습니다.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  완료되었습니다.
echo ============================================================
echo.
echo  새 위치 : %TARGET%
echo.
echo  이제 새 폴더의 [실행.bat] 을 눌러 사용하세요.
echo  ^(첫 실행은 설치 때문에 1~2분 걸립니다^)
echo.
echo  새 위치에서 정상 동작을 확인한 뒤,
echo  지금 이 폴더는 직접 삭제하시면 됩니다.
echo.
start "" explorer "%TARGET%"
pause
