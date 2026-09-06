# =============================================================================
# downloader/src/extractors/youtube.py – YouTube Platform Extractor
# =============================================================================
import re
import urllib.request
import json
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from typing import Any

from extractors.base import BaseExtractor, MediaItem
from core.config import (
    load_config,
    get_download_path,
    get_outtmpl,
    resolve_video_container,
    get_video_format_selector,
)
from core.ffmpeg_engine import FFMPEG_EXE, FFmpegUpscalePP
from core.progress import create_ytdlp_progress_hook

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


class YouTubeExtractor(BaseExtractor):
    """Extractor for YouTube Videos, Shorts, Audio, and Playlists."""

    YOUTUBE_REGEX = re.compile(
        r"^(https?://)?(www\.|m\.)?(youtube\.com/(watch\?.*v=|shorts/|embed/|playlist\?.*list=)|youtu\.be/)([a-zA-Z0-9_-]+)"
    )

    @classmethod
    def is_suitable(cls, url: str) -> bool:
        return bool(cls.YOUTUBE_REGEX.match(url.strip()))

    def validate_url(self, url: str) -> tuple[bool, str, str]:
        url = url.strip()
        if not url:
            return False, "", "URL cannot be empty."

        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        if netloc.startswith("m."):
            netloc = netloc[2:]

        if netloc == "youtu.be":
            vid_id = parsed.path.strip("/").split("/")[0]
            if not vid_id or len(vid_id) < 6:
                return False, "", "Invalid youtu.be video ID."
            qs = parse_qs(parsed.query)
            clean_url = f"https://youtu.be/{vid_id}"
            if "list" in qs:
                clean_url += f"?list={qs['list'][0]}"
            return True, clean_url, ""

        if netloc == "youtube.com":
            path = parsed.path
            qs = parse_qs(parsed.query)

            if path.startswith("/shorts/"):
                vid_id = path.split("/")[2] if len(path.split("/")) > 2 else ""
                if not vid_id:
                    return False, "", "Invalid YouTube Shorts URL."
                return True, f"https://www.youtube.com/shorts/{vid_id}", ""

            if path == "/watch":
                vid_id = qs.get("v", [""])[0]
                if not vid_id:
                    return False, "", "Missing video ID (?v= parameter)."
                clean_url = f"https://www.youtube.com/watch?v={vid_id}"
                if "list" in qs:
                    clean_url += f"&list={qs['list'][0]}"
                return True, clean_url, ""

            if path == "/playlist":
                list_id = qs.get("list", [""])[0]
                if not list_id:
                    return False, "", "Missing playlist ID (?list= parameter)."
                return True, f"https://www.youtube.com/playlist?list={list_id}", ""

        return False, "", "Not a recognized YouTube video or playlist URL."

    def is_playlist_url(self, url: str) -> bool:
        return "list=" in url and not url.startswith("https://www.youtube.com/watch?v=")

    def fetch_metadata(self, url: str) -> MediaItem | None:
        """Fetches title and structure for YouTube URL."""
        is_pl = "list=" in url

        # Quick oEmbed title check
        title = "YouTube Media"
        try:
            oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(url)}&format=json"
            req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                title = data.get("title", title)
                author = data.get("author_name", "Unknown")
        except Exception:
            author = "Unknown"

        if not yt_dlp:
            return MediaItem(
                platform="youtube",
                url=url,
                title=title,
                author=author,
                media_type="playlist" if is_pl else "video"
            )

        # Deep fetch with yt-dlp
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": "in_playlist" if is_pl else False,
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None

                real_title = info.get("title") or title
                uploader = info.get("uploader") or author
                duration = float(info.get("duration") or 0.0)

                items = []
                if "entries" in info:
                    media_type = "playlist"
                    for entry in info.get("entries", []):
                        if entry:
                            items.append({
                                "title": entry.get("title", "Untitled Track"),
                                "id": entry.get("id", ""),
                                "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                                "duration": float(entry.get("duration") or 0.0)
                            })
                else:
                    media_type = "video"

                return MediaItem(
                    platform="youtube",
                    url=url,
                    title=real_title,
                    author=uploader,
                    media_type=media_type,
                    duration=duration,
                    items=items,
                    raw_info=info
                )
        except Exception:
            return MediaItem(
                platform="youtube",
                url=url,
                title=title,
                author=author,
                media_type="playlist" if is_pl else "video"
            )

    def download(self, item: MediaItem, options: dict[str, Any]) -> tuple[bool, list[Path]]:
        """Downloads YouTube media based on options."""
        if not yt_dlp:
            return False, []

        cfg = load_config()
        mode = options.get("mode", "video")  # 'video', 'audio', etc.
        resolution = options.get("resolution") or cfg.get("default_resolution", "1080")
        target_codec = options.get("video_codec") or cfg.get("video_codec", "h264")
        target_container = options.get("video_container") or cfg.get("video_container", "auto")
        effective_container = resolve_video_container(target_codec, target_container)
        target_audio_fmt = options.get("audio_format") or cfg.get("audio_format", "mp3")
        target_audio_br = str(options.get("audio_bitrate") or cfg.get("audio_bitrate", "320"))
        style = options.get("filename_style") or cfg.get("filename_style", "basic")
        is_playlist = options.get("is_playlist", item.media_type == "playlist")
        is_upscale = options.get("force_upscale") if "force_upscale" in options else cfg.get("force_upscale", False)

        output_dir = get_download_path(options.get("output_dir"), platform="youtube")
        out_template = get_outtmpl(style, mode if mode != "audio" else target_audio_fmt, output_dir, platform="youtube")

        hook = create_ytdlp_progress_hook(item.title)

        ydl_opts = {
            "outtmpl": out_template,
            "progress_hooks": [hook],
            "noplaylist": not is_playlist,
            "quiet": True,
            "noprogress": True,
            "no_warnings": True,
            "windowsfilenames": True,
        }

        if FFMPEG_EXE:
            ydl_opts["ffmpeg_location"] = FFMPEG_EXE

        is_audio_mode = mode in ("audio", "mp3", "m4a", "opus", "wav", "best")
        if is_audio_mode:
            actual_fmt = target_audio_fmt if mode == "audio" else mode
            if actual_fmt == "best":
                ydl_opts["format"] = "bestaudio/best"
            elif actual_fmt == "wav":
                ydl_opts.update({
                    "format": "bestaudio/best",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "wav",
                    }],
                })
            else:
                ydl_opts.update({
                    "format": "bestaudio/best",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": actual_fmt,
                        "preferredquality": target_audio_br,
                    }],
                })
        else:  # video
            format_str = get_video_format_selector(resolution, target_codec)
            ydl_opts.update({
                "format": format_str,
                "merge_output_format": effective_container,
            })

        downloaded_files = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if is_upscale and mode == "video" and resolution and FFMPEG_EXE:
                    ydl.add_post_processor(
                        FFmpegUpscalePP(ydl, target_height=resolution, codec=target_codec),
                        when="post_process"
                    )
                info = ydl.extract_info(item.url, download=True)
                # Collect files
                if info:
                    if "requested_downloads" in info:
                        for rd in info["requested_downloads"]:
                            if rd.get("filepath"):
                                downloaded_files.append(Path(rd["filepath"]))
                    elif info.get("filepath"):
                        downloaded_files.append(Path(info["filepath"]))
            return True, downloaded_files
        except Exception as e:
            return False, []
