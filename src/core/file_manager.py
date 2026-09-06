# =============================================================================
# downloader/src/core/file_manager.py – Media File Management & Playback
# =============================================================================
import os
import sys
import subprocess
from pathlib import Path
from core.config import get_download_path

SUPPORTED_EXTENSIONS = {
    # Video
    ".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv",
    # Audio
    ".mp3", ".m4a", ".opus", ".wav", ".ogg", ".flac",
    # Images
    ".jpg", ".jpeg", ".png", ".webp", ".gif"
}


def scan_downloaded_files(root_dir: Path | None = None) -> list[Path]:
    """
    Recursively scans the download directory for supported media files,
    sorted by last modified time (newest first).
    """
    base = root_dir or get_download_path()
    if not base.exists():
        return []

    files = []
    for item in base.rglob("*"):
        if item.is_file() and not item.name.startswith("."):
            if item.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(item)

    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def open_file_in_player(filepath: Path | str) -> bool:
    """Opens a media file in the user's default system player."""
    p = Path(filepath).resolve()
    if not p.exists():
        return False
    try:
        if os.name == "nt":
            os.startfile(str(p))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(p)], check=True)
        else:
            subprocess.run(["xdg-open", str(p)], check=True)
        return True
    except Exception:
        return False


def open_download_folder(folder_path: Path | str | None = None):
    """Opens the download directory in the system file explorer."""
    p = Path(folder_path).resolve() if folder_path else get_download_path()
    p.mkdir(parents=True, exist_ok=True)
    try:
        if os.name == "nt":
            os.startfile(str(p))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(p)])
        else:
            subprocess.run(["xdg-open", str(p)])
    except Exception:
        pass


def delete_file(filepath: Path | str) -> bool:
    """Safely deletes a single media file."""
    p = Path(filepath)
    if p.exists():
        try:
            p.unlink()
            return True
        except Exception:
            return False
    return False


def delete_all_files(folder_path: Path | str | None = None) -> int:
    """Deletes all media files in the download directory."""
    files = scan_downloaded_files(Path(folder_path) if folder_path else None)
    deleted_count = 0
    for f in files:
        if delete_file(f):
            deleted_count += 1
    return deleted_count
