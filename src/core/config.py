# =============================================================================
# downloader/src/core/config.py – Configuration & Path Management
# =============================================================================
import sys
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_DOWNLOAD_DIR = BASE_DIR / "downloads"

DEFAULT_CONFIG = {
    "language": "id",                     # id, en
    "browser_cookies": "none",            # none, chrome, firefox, edge, brave, opera, vivaldi
    "filename_style": "basic",            # classic, basic, pretty, nerdy
    "default_resolution": "1080",
    "video_codec": "h264",                # h264, av1, vp9, auto
    "video_container": "auto",            # auto, mp4, webm, mkv
    "audio_format": "mp3",                # mp3, m4a, opus, wav, best
    "audio_bitrate": "320",               # 320, 256, 192, 128, 96
    "embed_thumbnail": True,              # True: embed album cover art into audio (MP3/M4A/FLAC/etc.)
    "embed_metadata": True,               # True: embed track, artist, album, date tags into audio
    "crop_square_thumbnail": True,        # True: crop 16:9 thumbnails to 1:1 square for Topic/music tracks
    "download_dir": "downloads",
    "organize_by_platform": True,         # downloads/youtube, downloads/x, etc.
    "organize_by_category": True,         # downloads/platform/photo, downloads/platform/video, etc.
    "playlist_mode": "ask",               # ask, single, playlist
    "force_upscale": False,               # False: native stream, True: upscale via GPU/FFmpeg if native < target
}


def ensure_dependencies():
    """Verify that external dependencies exist; auto-install if missing."""
    missing = []
    try:
        import yt_dlp
    except ImportError:
        missing.append("yt-dlp")
    try:
        import imageio_ffmpeg
    except ImportError:
        missing.append("imageio-ffmpeg")
    try:
        import requests
    except ImportError:
        missing.append("requests")
    try:
        import mutagen
    except ImportError:
        missing.append("mutagen")

    if missing:
        import subprocess
        import time
        print("\n\033[1;33m[!] First-time setup: Missing dependencies detected.\033[0m")
        print(f"\033[1;36m[*] Automatically installing required packages: {', '.join(missing)}...\033[0m\n")
        req_file = BASE_DIR / "requirements.txt"
        try:
            if req_file.exists():
                cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
            else:
                cmd = [sys.executable, "-m", "pip", "install"] + missing
            subprocess.check_call(cmd)
            print("\n\033[1;32m[✓] All dependencies installed successfully! Launching...\033[0m\n")
            time.sleep(1)
        except Exception as e:
            print(f"\n\033[1;31m[✗] Failed to auto-install dependencies: {e}\033[0m")
            print(f"Please run manually: pip install -r {req_file}\n")
            sys.exit(1)


def load_config() -> dict:
    """Load configuration from JSON file with fallback to defaults."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_CONFIG, **data}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """Persist configuration dictionary to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_download_path(
    custom_dir: str | None = None,
    platform: str | None = None,
    media_type: str | None = None
) -> Path:
    """Resolve download path, optionally routed into platform and media category subfolders."""
    cfg = load_config()
    target_dir = custom_dir or cfg.get("download_dir", "downloads")
    p = Path(target_dir)
    if not p.is_absolute():
        p = BASE_DIR / target_dir

    if platform and cfg.get("organize_by_platform", True):
        norm_plat = platform.lower()
        if norm_plat in ("twitter", "x"):
            norm_plat = "x"
        p = p / norm_plat

        if media_type and cfg.get("organize_by_category", True):
            m = media_type.lower()
            if m in ("audio", "mp3", "m4a", "opus", "wav", "flac", "ogg"):
                category = "audio"
            elif m in ("image", "photo", "gallery", "slide", "slides", "picture"):
                category = "photo"
            elif m in ("video", "reel", "reels", "gif", "tv", "clip", "playlist"):
                category = "video"
            else:
                category = m
            p = p / category

    p.mkdir(parents=True, exist_ok=True)
    return p


def get_outtmpl(style: str, mode: str, output_dir: Path, platform: str = "youtube") -> str:
    """Generates filename output template for yt-dlp based on selected style."""
    is_audio = mode in ("mp3", "m4a", "opus", "wav", "ogg", "best", "audio") or mode.startswith("audio")
    tag = platform.lower()

    if style == "classic":
        if is_audio:
            template = f"{tag}_%(id)s_audio.%(ext)s"
        else:
            template = f"{tag}_%(id)s_%(height)sp.%(ext)s"

    elif style == "pretty":
        if is_audio:
            template = f"%(title)s - %(uploader|Unknown)s ({tag}).%(ext)s"
        else:
            template = f"%(title)s - %(uploader|Unknown)s (%(height)sp, {tag}).%(ext)s"

    elif style == "nerdy":
        if is_audio:
            template = f"%(title)s - %(uploader|Unknown)s ({tag}, %(id)s).%(ext)s"
        else:
            template = f"%(title)s - %(uploader|Unknown)s (%(height)sp, {tag}, %(id)s).%(ext)s"

    else:  # basic
        if is_audio:
            template = "%(title)s - %(uploader|Unknown)s.%(ext)s"
        else:
            template = "%(title)s - %(uploader|Unknown)s (%(height)sp).%(ext)s"

    return str(output_dir / template)


def resolve_video_container(codec: str = "h264", container: str = "auto") -> str:
    """Resolves effective container (mp4, webm, mkv)."""
    if container and container != "auto":
        return container.lower()
    c = codec.lower()
    if c in ("vp9", "av1"):
        return "webm"
    return "mp4"


def get_video_format_selector(resolution: str | None, codec: str | None = None) -> str:
    """Builds a robust format selector string for yt-dlp."""
    c = (codec or "h264").lower()
    vcodec_filter = ""
    if c == "h264":
        vcodec_filter = "[vcodec^=avc1]"
    elif c == "av1":
        vcodec_filter = "[vcodec^=av01]"
    elif c == "vp9":
        vcodec_filter = "[vcodec^=vp9]"

    if not resolution or str(resolution).lower() in ("best", "max", "auto"):
        if vcodec_filter:
            return f"bestvideo{vcodec_filter}+bestaudio/bestvideo+bestaudio/best"
        return "bestvideo+bestaudio/best"

    res_limit = f"[height<={resolution}]"
    if vcodec_filter:
        return f"bestvideo{vcodec_filter}{res_limit}+bestaudio/bestvideo{res_limit}+bestaudio/best{res_limit}/best"
    return f"bestvideo{res_limit}+bestaudio/best{res_limit}/best"


def get_cookie_opts() -> dict:
    """Returns yt-dlp cookie options based on configured browser (Chrome, Firefox, etc.)."""
    cfg = load_config()
    b = (cfg.get("browser_cookies") or "none").lower().strip()
    if b and b != "none":
        return {"cookiesfrombrowser": (b, None, None, None)}
    return {}

