import sys
import json
import re
from urllib.parse import urlparse, parse_qs
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def ensure_dependencies():
    """Verify that external dependencies (yt-dlp, imageio-ffmpeg) exist; auto-install if missing."""
    missing = []
    try:
        import yt_dlp
    except ImportError:
        missing.append("yt-dlp")
    try:
        import imageio_ffmpeg
    except ImportError:
        missing.append("imageio-ffmpeg")

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

CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_DOWNLOAD_DIR = BASE_DIR / "downloads"

DEFAULT_CONFIG = {
    "filename_style": "basic",      # classic, basic, pretty, nerdy
    "default_resolution": "1080",
    "video_codec": "h264",          # h264, av1, vp9, auto
    "video_container": "auto",       # auto, mp4, webm, mkv
    "audio_format": "mp3",          # mp3, m4a, opus, wav, best
    "audio_bitrate": "320",         # 320, 256, 192, 128, 96
    "download_dir": "downloads",
    "playlist_mode": "ask",          # ask, single, playlist
    "force_upscale": False          # False: native stream, True: upscale via FFmpeg if native < target
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_CONFIG, **data}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_download_path(custom_dir: str | None = None) -> Path:
    cfg = load_config()
    target_dir = custom_dir or cfg.get("download_dir", "downloads")
    p = Path(target_dir)
    if not p.is_absolute():
        p = BASE_DIR / target_dir
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_outtmpl(style: str, mode: str, output_dir: Path) -> str:
    """
    Filename styles:
    - classic:
        video -> youtube_<id>_<resolution>.mp4
        audio -> youtube_<id>_audio.mp3
    - basic:
        video -> <Title> - <Author> (<resolution>).mp4
        audio -> <Title> - <Author>.mp3
    - pretty:
        video -> <Title> - <Author> (<resolution>, youtube).mp4
        audio -> <Title> - <Author> (youtube).mp3
    - nerdy:
        video -> <Title> - <Author> (<resolution>, youtube, <id>).mp4
        audio -> <Title> - <Author> (youtube, <id>).mp3
    """
    is_audio = mode in ("mp3", "m4a", "opus", "wav", "ogg", "best", "audio") or mode.startswith("audio")

    if style == "classic":
        if is_audio:
            template = "youtube_%(id)s_audio.%(ext)s"
        else:
            template = "youtube_%(id)s_%(height)sp.%(ext)s"

    elif style == "pretty":
        if is_audio:
            template = "%(title)s - %(uploader|Unknown)s (youtube).%(ext)s"
        else:
            template = "%(title)s - %(uploader|Unknown)s (%(height)sp, youtube).%(ext)s"

    elif style == "nerdy":
        if is_audio:
            template = "%(title)s - %(uploader|Unknown)s (youtube, %(id)s).%(ext)s"
        else:
            template = "%(title)s - %(uploader|Unknown)s (%(height)sp, youtube, %(id)s).%(ext)s"

    else:  # basic
        if is_audio:
            template = "%(title)s - %(uploader|Unknown)s.%(ext)s"
        else:
            template = "%(title)s - %(uploader|Unknown)s (%(height)sp).%(ext)s"

    return str(output_dir / template)


def resolve_video_container(codec: str = "h264", container: str = "auto") -> str:
    """
    Resolves effective video file container:
    - If user explicitly set mp4, webm, or mkv -> use that container.
    - If 'auto':
        h264 -> mp4 (standard universal container)
        vp9  -> webm (native container for VP9 + Opus)
        av1  -> webm (native container for AV1 + Opus)
        auto -> mp4
    """
    if container and container != "auto":
        return container.lower()
    if codec == "h264":
        return "mp4"
    elif codec in ("vp9", "av1"):
        return "webm"
    return "mp4"


def get_video_format_selector(resolution: str | None = None, codec: str = "h264") -> str:
    """
    Builds robust yt-dlp format selector ladder with fallback.
    - h264: H.264 video + AAC audio -> fallback to H.264 + any audio -> bestvideo + bestaudio
    - av1:  AV1 video + Opus audio  -> fallback to AV1 + any audio  -> bestvideo + bestaudio
    - vp9:  VP9 video + Opus audio  -> fallback to VP9 + any audio  -> bestvideo + bestaudio
    - auto: bestvideo + bestaudio
    """
    res_part = f"[height<={resolution}]" if resolution else ""

    if codec == "h264":
        # YouTube uses avc1 for H.264, mp4a for AAC
        return (
            f"bestvideo[vcodec^=avc1]{res_part}+bestaudio[acodec^=mp4a]/"
            f"bestvideo[vcodec^=avc1]{res_part}+bestaudio/"
            f"bestvideo{res_part}+bestaudio/best{res_part}/best"
        )
    elif codec == "av1":
        # YouTube uses av01 for AV1, opus for Opus
        return (
            f"bestvideo[vcodec^=av01]{res_part}+bestaudio[acodec^=opus]/"
            f"bestvideo[vcodec^=av01]{res_part}+bestaudio/"
            f"bestvideo{res_part}+bestaudio/best{res_part}/best"
        )
    elif codec == "vp9":
        # YouTube uses vp9/vp09 for VP9, opus for Opus
        return (
            f"bestvideo[vcodec^=vp09]{res_part}+bestaudio[acodec^=opus]/"
            f"bestvideo[vcodec^=vp9]{res_part}+bestaudio[acodec^=opus]/"
            f"bestvideo[vcodec^=vp09]{res_part}+bestaudio/"
            f"bestvideo[vcodec^=vp9]{res_part}+bestaudio/"
            f"bestvideo{res_part}+bestaudio/best{res_part}/best"
        )
    else:  # auto
        return (
            f"bestvideo{res_part}+bestaudio/best{res_part}/best"
        )


YOUTUBE_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "gaming.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
    "youtu.be",
    "www.youtu.be"
}


def validate_youtube_url(raw_url: str) -> tuple[bool, str, str]:
    """
    Validates if the provided string is a genuine YouTube URL.
    Returns: (is_valid: bool, normalized_url: str, reason: str)
    """
    if not raw_url or not isinstance(raw_url, str):
        return False, "", "URL cannot be empty."

    s = raw_url.strip()
    if not s:
        return False, "", "URL cannot be empty."

    # If scheme is missing, prepend https://
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', s):
        s = "https://" + s

    try:
        parsed = urlparse(s)
    except Exception as e:
        return False, raw_url, f"Malformed URL: {e}"

    if parsed.scheme not in ("http", "https"):
        return False, raw_url, f"Invalid scheme '{parsed.scheme}://'. Only http:// and https:// are supported."

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False, raw_url, "No hostname found in URL."

    # Check hostname strictly belongs to youtube.com, youtu.be, or youtube-nocookie.com
    is_yt = False
    if hostname in YOUTUBE_DOMAINS:
        is_yt = True
    elif (hostname.endswith(".youtube.com") or 
          hostname.endswith(".youtu.be") or 
          hostname.endswith(".youtube-nocookie.com")):
        is_yt = True

    if not is_yt:
        return False, raw_url, f"Domain '{hostname}' is not a recognized YouTube domain."

    path = parsed.path.rstrip("/")
    query = parse_qs(parsed.query)

    # 1. youtu.be short link: https://youtu.be/<VIDEO_ID>
    if hostname == "youtu.be" or hostname.endswith(".youtu.be"):
        parts = [p for p in path.split("/") if p]
        if not parts:
            return False, raw_url, "Missing video ID in youtu.be link."
        video_id = parts[0]
        if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
            return False, raw_url, f"Invalid YouTube video ID '{video_id}' in youtu.be link (expected 11 characters)."
        return True, s, "OK"

    # 2. youtube.com domains
    # 2a. /watch or /watch_popup: ?v=<VIDEO_ID> or ?list=<PLAYLIST_ID>
    if path in ("/watch", "/watch_popup", "") and (query.get("v") or query.get("list")):
        v_ids = query.get("v", [])
        list_ids = query.get("list", [])
        if v_ids:
            vid = v_ids[0]
            if not re.match(r'^[a-zA-Z0-9_-]{11}$', vid):
                return False, raw_url, f"Invalid YouTube video ID '{vid}' in ?v= parameter."
            return True, s, "OK"
        elif list_ids:
            lid = list_ids[0]
            if not re.match(r'^[a-zA-Z0-9_-]{10,}$', lid):
                return False, raw_url, "Invalid YouTube playlist ID in ?list= parameter."
            return True, s, "OK"

    # 2b. /shorts/<VIDEO_ID>, /live/<VIDEO_ID>, /embed/<VIDEO_ID>, /v/<VIDEO_ID>, /e/<VIDEO_ID>
    prefixes = ("/shorts/", "/live/", "/embed/", "/v/", "/e/")
    for prefix in prefixes:
        if path.startswith(prefix):
            parts = [p for p in path[len(prefix):].split("/") if p]
            if not parts or not re.match(r'^[a-zA-Z0-9_-]{11}$', parts[0]):
                name = prefix.strip("/")
                return False, raw_url, f"Invalid or missing 11-character video ID in YouTube {name} link."
            return True, s, "OK"

    # 2c. /playlist?list=<PLAYLIST_ID>
    if path == "/playlist":
        list_ids = query.get("list", [])
        if not list_ids or not re.match(r'^[a-zA-Z0-9_-]{10,}$', list_ids[0]):
            return False, raw_url, "Invalid or missing '?list=' playlist ID parameter."
        return True, s, "OK"

    # 2d. /clip/<CLIP_ID>
    if path.startswith("/clip/"):
        parts = [p for p in path[len("/clip/"):].split("/") if p]
        if not parts or not re.match(r'^[a-zA-Z0-9_-]+$', parts[0]):
            return False, raw_url, "Invalid or missing YouTube Clip ID."
        return True, s, "OK"

    # 2e. Channel / User / Handle
    if re.match(r'^/(?:@|channel/|c/|user/)[a-zA-Z0-9_.-]+', path):
        return True, s, "OK"

    # If it's just /watch without query or homepage
    if path in ("/watch", ""):
        return False, raw_url, "Missing video ID (?v=...) or playlist ID (?list=...)."

    return False, raw_url, f"Unrecognized YouTube URL path format ('{path}')."


def get_media_title(url: str, prefer_playlist: bool = False) -> str:
    """
    Quickly resolves video or playlist title using YouTube official oEmbed API (~150ms).
    Falls back gracefully to yt-dlp extract_flat if oEmbed fails.
    """
    if not url:
        return ""

    target_url = url
    if prefer_playlist and "list=" in url:
        parsed = urlparse(url)
        q = parse_qs(parsed.query)
        lid = q.get("list", [None])[0]
        if lid:
            target_url = f"https://www.youtube.com/playlist?list={lid}"

    # 1. Fast path: YouTube oEmbed endpoint (zero-overhead JSON, no API key needed)
    try:
        import urllib.request
        oembed_url = f"https://www.youtube.com/oembed?url={target_url}&format=json"
        req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("title"):
                return str(data["title"]).strip()
    except Exception:
        pass

    # 2. Fallback: yt-dlp extract_flat
    try:
        import yt_dlp
        ydl_opts = {"quiet": True, "extract_flat": True, "skip_download": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            title = info.get("title")
            if title:
                return str(title).strip()
    except Exception:
        pass

    return ""

