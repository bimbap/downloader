:; export PYTHONIOENCODING=utf-8; SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"; [ -t 0 ] && command -v winpty >/dev/null 2>&1 && PY="winpty python" || PY="python"; if ! $PY -c "import yt_dlp, imageio_ffmpeg" >/dev/null 2>&1; then echo -e "\033[1;33m[!] First-time setup: Missing dependencies detected.\033[0m"; echo -e "\033[1;36m[*] Installing requirements from requirements.txt...\033[0m"; $PY -m pip install -r "$SCRIPT_DIR/requirements.txt"; fi; if [ "$#" -eq 0 ]; then $PY "$SCRIPT_DIR/src/tui.py"; else $PY "$SCRIPT_DIR/src/downloader.py" "$@"; fi; exit $?
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
