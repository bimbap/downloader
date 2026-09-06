#!/usr/bin/env bash
# =============================================================================
# dl.sh – Universal Social Media Downloader Launcher
# =============================================================================

export PYTHONIOENCODING=utf-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect python executable
if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
elif command -v py >/dev/null 2>&1; then
    PY_CMD="py"
else
    PY_CMD="python"
fi

# Auto-check and auto-install dependencies if missing
if ! $PY_CMD -c "import yt_dlp, imageio_ffmpeg, requests" >/dev/null 2>&1; then
    echo ""
    echo -e "\033[1;33m[!] First-time setup: Missing dependencies detected.\033[0m"
    echo -e "\033[1;36m[*] Installing requirements from requirements.txt...\033[0m"
    echo ""
    $PY_CMD -m pip install -r "$SCRIPT_DIR/requirements.txt"
    if [ $? -ne 0 ]; then
        echo -e "\033[1;31m[✗] Failed to install dependencies. Please check your internet connection or run:\033[0m"
        echo "    $PY_CMD -m pip install -r requirements.txt"
        exit 1
    fi
    echo -e "\033[1;32m[✓] Dependencies installed successfully!\033[0m"
    echo ""
fi

$PY_CMD "$SCRIPT_DIR/src/main.py" "$@"
