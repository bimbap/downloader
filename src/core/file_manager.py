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
    Recursively scans the target directory for supported media files,
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


def migrate_flat_downloads(root_dir: Path | None = None) -> int:
    """
    Migrates any legacy flat files sitting directly in platform folders
    (e.g., downloads/instagram/*.jpg) into appropriate category subfolders
    (downloads/instagram/photo/*.jpg). Returns count of moved files.
    """
    base = root_dir or get_download_path()
    if not base.exists():
        return 0

    moved_count = 0
    platforms = ["instagram", "youtube", "x", "twitter", "threads"]
    for plat in platforms:
        plat_dir = base / plat
        if not plat_dir.exists() or not plat_dir.is_dir():
            continue

        for f in plat_dir.iterdir():
            if f.is_file() and not f.name.startswith("."):
                s = f.suffix.lower()
                if s in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                    cat = "photo"
                elif s in (".mp4", ".mkv", ".webm", ".mov", ".avi"):
                    cat = "video"
                elif s in (".mp3", ".m4a", ".opus", ".wav", ".flac"):
                    cat = "audio"
                else:
                    cat = "other"

                dest_dir = plat_dir / cat
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / f.name
                try:
                    f.rename(dest)
                    moved_count += 1
                except Exception:
                    pass

    return moved_count


def get_category_overview(root_dir: Path | None = None) -> list[dict]:
    """
    Returns list of categories across all platforms with file count, size, and folder path.
    """
    migrate_flat_downloads(root_dir)
    base = root_dir or get_download_path()

    definitions = [
        {"key": "all", "platform": "all", "category": "all", "label": "All Downloads (Semua File)", "icon": "📂", "path": base},
        {"key": "ig_photo", "platform": "instagram", "category": "photo", "label": "Instagram / Photo (Carousel, Feed)", "icon": "📷", "path": base / "instagram" / "photo"},
        {"key": "ig_video", "platform": "instagram", "category": "video", "label": "Instagram / Video (Reels, Clips)", "icon": "🎬", "path": base / "instagram" / "video"},
        {"key": "yt_video", "platform": "youtube", "category": "video", "label": "YouTube / Video (MP4, MKV, WebM)", "icon": "🔴", "path": base / "youtube" / "video"},
        {"key": "yt_audio", "platform": "youtube", "category": "audio", "label": "YouTube / Audio (MP3, M4A, Opus)", "icon": "🎵", "path": base / "youtube" / "audio"},
        {"key": "x_photo", "platform": "x", "category": "photo", "label": "X (Twitter) / Photo (Images)", "icon": "🐦", "path": base / "x" / "photo"},
        {"key": "x_video", "platform": "x", "category": "video", "label": "X (Twitter) / Video (Clips, GIFs)", "icon": "🎬", "path": base / "x" / "video"},
        {"key": "th_photo", "platform": "threads", "category": "photo", "label": "Threads / Photo", "icon": "🧵", "path": base / "threads" / "photo"},
        {"key": "th_video", "platform": "threads", "category": "video", "label": "Threads / Video", "icon": "🎬", "path": base / "threads" / "video"},
    ]

    overview = []
    for d in definitions:
        p = d["path"]
        files = scan_downloaded_files(p) if d["key"] != "all" else scan_downloaded_files(base)
        total_size = sum(f.stat().st_size for f in files)
        overview.append({
            **d,
            "files": files,
            "count": len(files),
            "size_bytes": total_size,
            "size_mb": total_size / (1024 * 1024),
        })

    return overview


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
    """Deletes all media files in the specified directory."""
    files = scan_downloaded_files(Path(folder_path) if folder_path else None)
    deleted_count = 0
    for f in files:
        if delete_file(f):
            deleted_count += 1
    return deleted_count
