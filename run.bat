@echo off
setlocal
set PYTHONIOENCODING=utf-8
set SCRIPT_DIR=%~dp0

rem Check if dependencies are installed
python -c "import yt_dlp, imageio_ffmpeg" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] First-time setup: Missing dependencies detected.
    echo [*] Installing required packages from requirements.txt...
    echo.
    python -m pip install -r "%SCRIPT_DIR%requirements.txt"
    if %errorlevel% neq 0 (
        echo.
        echo [X] Failed to install dependencies. Please check your internet or run:
        echo     pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo.
    echo [V] Dependencies installed successfully!
    echo.
)

if "%~1"=="" (
    python "%SCRIPT_DIR%src\tui.py"
) else (
    python "%SCRIPT_DIR%src\downloader.py" %*
)
