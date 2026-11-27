# =============================================================================
# downloader/src/extractors/youtube.py – YouTube Platform Extractor
# =============================================================================
import re
import urllib.request
import json
from urllib.parse import urlparse, parse_qs, quote
from pathlib import Path
from typing import Any

from extractors.base import BaseExtractor, MediaItem
from core.config import (
    load_config,
    get_download_path,
    get_outtmpl,
    resolve_video_container,
    get_video_format_selector,
    get_cookie_opts,
)
from core.ffmpeg_engine import FFMPEG_EXE, FFmpegUpscalePP, FFmpegSquareCropThumbnailPP
from core.progress import create_ytdlp_progress_hook, download_file_with_progress, safe_urlopen

try:
    import yt_dlp
    from yt_dlp.postprocessor.embedthumbnail import EmbedThumbnailPP

    class SafeEmbedThumbnailPP(EmbedThumbnailPP):
        """Safely embeds thumbnail into audio container without failing the download on unsupported containers."""
        def run(self, info):
            try:
                return super().run(info)
            except Exception:
                return [], info
except ImportError:
    yt_dlp = None
    EmbedThumbnailPP = None
    SafeEmbedThumbnailPP = None


class YouTubeExtractor(BaseExtractor):
    """Extractor for YouTube Videos, Shorts, Audio, and Playlists."""

    YOUTUBE_REGEX = re.compile(
        r"^(https?://)?(www\.|m\.)?(youtube\.com/(watch\?.*v=|shorts/|embed/|playlist\?.*list=|post/|[^/]+/(?:community|posts)\?.*lb=)|youtu\.be/)([a-zA-Z0-9_-]+)"
    )

    _SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

    @classmethod
    def is_suitable(cls, url: str) -> bool:
        return bool(cls.YOUTUBE_REGEX.match(url.strip()))

    def validate_url(self, url: str) -> tuple[bool, str, str]:
        url = url.strip()
        if not url:
            return False, "", "URL cannot be empty."

        if url.startswith("//"):
            return False, "", "Not a recognized YouTube video or playlist URL."

        candidate = url if "://" in url else f"https://{url}"
        parsed = urlparse(candidate)
        if parsed.scheme.lower() not in ("http", "https"):
            return False, "", "Not a recognized YouTube video or playlist URL."

        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        if netloc.startswith("m."):
            netloc = netloc[2:]

        if netloc == "youtu.be":
            vid_id = parsed.path.strip("/").split("/")[0]
            if not vid_id or len(vid_id) < 6 or not self._SAFE_ID_RE.fullmatch(vid_id):
                return False, "", "Invalid youtu.be video ID."
            qs = parse_qs(parsed.query)
            clean_url = f"https://youtu.be/{vid_id}"
            if "list" in qs and self._SAFE_ID_RE.fullmatch(qs["list"][0]):
                clean_url += f"?list={qs['list'][0]}"
            return True, clean_url, ""

        if netloc == "youtube.com":
            path = parsed.path
            qs = parse_qs(parsed.query)

            if path.startswith("/shorts/"):
                vid_id = path.split("/")[2] if len(path.split("/")) > 2 else ""
                if not vid_id or not self._SAFE_ID_RE.fullmatch(vid_id):
                    return False, "", "Invalid YouTube Shorts URL."
                return True, f"https://www.youtube.com/shorts/{vid_id}", ""

            if path == "/watch":
                vid_id = qs.get("v", [""])[0]
                if not vid_id or not self._SAFE_ID_RE.fullmatch(vid_id):
                    return False, "", "Missing or invalid video ID (?v= parameter)."
                clean_url = f"https://www.youtube.com/watch?v={vid_id}"
                if "list" in qs and self._SAFE_ID_RE.fullmatch(qs["list"][0]):
                    clean_url += f"&list={qs['list'][0]}"
                return True, clean_url, ""

            if path == "/playlist":
                list_id = qs.get("list", [""])[0]
                if not list_id or not self._SAFE_ID_RE.fullmatch(list_id):
                    return False, "", "Missing or invalid playlist ID (?list= parameter)."
                return True, f"https://www.youtube.com/playlist?list={list_id}", ""

            if path.startswith("/post/"):
                post_id = path.split("/")[2] if len(path.split("/")) > 2 else ""
                if not post_id or not self._SAFE_ID_RE.fullmatch(post_id):
                    return False, "", "Invalid YouTube Community Post ID."
                return True, f"https://www.youtube.com/post/{post_id}", ""

            if path.endswith("/community") or path.endswith("/posts"):
                lb_id = qs.get("lb", [""])[0]
                if not lb_id or not self._SAFE_ID_RE.fullmatch(lb_id):
                    return False, "", "Missing or invalid Community Post ID (?lb= parameter)."
                return True, f"https://www.youtube.com/post/{lb_id}", ""

        return False, "", "Not a recognized YouTube video, playlist, or post URL."

    def is_playlist_url(self, url: str) -> bool:
        return "list=" in url and not url.startswith("https://www.youtube.com/watch?v=")

    @staticmethod
    def _find_json_key(node: Any, target_key: str) -> Any:
        if isinstance(node, dict):
            if target_key in node:
                return node[target_key]
            for v in node.values():
                res = YouTubeExtractor._find_json_key(v, target_key)
                if res is not None:
                    return res
        elif isinstance(node, list):
            for item in node:
                res = YouTubeExtractor._find_json_key(item, target_key)
                if res is not None:
                    return res
        return None

    def _fetch_community_post(self, url: str) -> MediaItem | None:
        """Extracts text, images, or attached video from a YouTube Community Post."""
        post_id = url.rstrip("/").split("/")[-1]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            with safe_urlopen(url, headers=headers, timeout=10) as resp:
                raw_html = resp.read().decode("utf-8", "ignore")
            m = re.search(r"var ytInitialData\s*=\s*(\{.*?\});</script>", raw_html)
            if not m:
                return None
            data = json.loads(m.group(1))
            bpr = self._find_json_key(data, "backstagePostRenderer")
            if not bpr or not isinstance(bpr, dict):
                return None

            author_runs = (bpr.get("authorText") or {}).get("runs") or []
            author = author_runs[0].get("text", "YouTube Creator") if author_runs else "YouTube Creator"
            content_runs = (bpr.get("contentText") or {}).get("runs") or []
            caption = "".join(r.get("text", "") for r in content_runs).strip()
            title = caption.split("\n")[0][:60] if caption else f"YouTube Post ({post_id})"

            att = bpr.get("backstageAttachment") or {}
            items = []
            media_type = "text"
            raw_info: dict[str, Any] = {"id": post_id, "is_community_post": True}

            if "postMultiImageRenderer" in att:
                imgs = att["postMultiImageRenderer"].get("images") or []
                for idx, img_wrap in enumerate(imgs, 1):
                    thumbs = ((img_wrap.get("backstageImageRenderer") or {}).get("image") or {}).get("thumbnails") or []
                    if thumbs:
                        items.append({"index": idx, "media_type": "image", "url": thumbs[-1]["url"]})
                media_type = "gallery" if len(items) > 1 else ("image" if items else "text")
            elif "backstageImageRenderer" in att:
                thumbs = (att["backstageImageRenderer"].get("image") or {}).get("thumbnails") or []
                if thumbs:
                    items.append({"index": 1, "media_type": "image", "url": thumbs[-1]["url"]})
                    media_type = "image"
            elif "videoRenderer" in att:
                vid_id = att["videoRenderer"].get("videoId")
                if vid_id:
                    media_type = "video"
                    raw_info["attached_video_url"] = f"https://www.youtube.com/watch?v={vid_id}"
                    vid_title_runs = ((att["videoRenderer"].get("title") or {}).get("runs") or [])
                    if vid_title_runs:
                        title = vid_title_runs[0].get("text", title)

            return MediaItem(
                platform="youtube",
                url=url,
                title=title,
                author=author,
                media_type=media_type,
                caption=caption,
                items=items,
                raw_info=raw_info,
            )
        except Exception:
            return None

    def fetch_metadata(self, url: str) -> MediaItem | None:
        """Fetches title and structure for YouTube URL."""
        if "/post/" in url:
            return self._fetch_community_post(url)

        is_pl = "list=" in url

        # Quick oEmbed title check
        title = "YouTube Media"
        try:
            oembed_url = f"https://www.youtube.com/oembed?url={quote(url)}&format=json"
            with safe_urlopen(oembed_url, timeout=3) as resp:
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
            ydl_opts.update(get_cookie_opts())
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None

                real_title = info.get("title") or title
                uploader = info.get("uploader") or author
                duration = float(info.get("duration") or 0.0)
                desc = (info.get("description") or "").strip()

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
                    caption=desc,
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
        """Downloads YouTube media (videos, audio, playlists, or Community Posts) based on options."""
        is_post = isinstance(item.raw_info, dict) and item.raw_info.get("is_community_post")
        if is_post and item.media_type in ("image", "gallery", "text"):
            post_id = item.raw_info.get("id", "post")
            link_folder = f"{item.author[:30]} [{post_id}]"
            if item.media_type == "text" or not item.items:
                post_dir = get_download_path(options.get("output_dir"), platform="youtube", media_type="posts", subfolder=link_folder)
                return True, []

            selected_indices = options.get("selected_indices")
            targets = [
                itm for itm in item.items
                if (not selected_indices or itm.get("index") in selected_indices)
            ]
            photo_dir = get_download_path(options.get("output_dir"), platform="youtube", media_type="photo", subfolder=link_folder)
            downloaded = []
            is_multi = len(item.items) > 1
            for itm in targets:
                m_url = itm.get("url")
                if not m_url:
                    continue
                idx = itm.get("index", 1)
                fname = f"post_{post_id}_slide_{idx}.jpg" if is_multi else f"post_{post_id}.jpg"
                dest = photo_dir / fname
                if is_multi:
                    print(f"  Downloading Slide {idx}/{len(item.items)} (Image)...")
                if download_file_with_progress(m_url, dest):
                    downloaded.append(dest)
            return len(downloaded) > 0, downloaded

        if not yt_dlp:
            return False, []

        target_url = (item.raw_info.get("attached_video_url") if is_post else None) or item.url

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

        media_cat = "audio" if (mode in ("audio", "mp3", "m4a", "opus", "wav", "flac", "best") or mode.startswith("audio")) else "video"
        vid_id = (item.raw_info.get("id") if isinstance(item.raw_info, dict) else None) or ""
        link_folder = f"{item.title[:50]} [{vid_id}]" if vid_id else item.title[:60]
        output_dir = get_download_path(options.get("output_dir"), platform="youtube", media_type=media_cat, subfolder=link_folder)
        out_template = get_outtmpl(style, target_audio_fmt if mode in ("audio", "best") else mode, output_dir, platform="youtube")

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
        ydl_opts.update(get_cookie_opts())

        if FFMPEG_EXE:
            ydl_opts["ffmpeg_location"] = FFMPEG_EXE

        embed_thumb = options.get("embed_thumbnail", cfg.get("embed_thumbnail", True)) and bool(FFMPEG_EXE)
        embed_meta = options.get("embed_metadata", cfg.get("embed_metadata", True)) and bool(FFMPEG_EXE)
        crop_square = options.get("crop_square_thumbnail", cfg.get("crop_square_thumbnail", True))

        is_audio_mode = mode in ("audio", "mp3", "m4a", "opus", "wav", "best")
        if is_audio_mode:
            actual_fmt = target_audio_fmt if mode == "audio" else mode
            ydl_opts["format"] = "bestaudio/best"

            postprocessors = []
            if actual_fmt == "wav":
                postprocessors.append({
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                })
            elif actual_fmt == "best":
                postprocessors.append({
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "best",
                })
            else:
                postprocessors.append({
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": actual_fmt,
                    "preferredquality": target_audio_br,
                })

            if embed_meta:
                postprocessors.append({
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                })

            if embed_thumb:
                ydl_opts["writethumbnail"] = True
                postprocessors.append({
                    "key": "FFmpegThumbnailsConvertor",
                    "format": "jpg",
                })

            if postprocessors:
                ydl_opts["postprocessors"] = postprocessors
        else:  # video
            format_str = get_video_format_selector(resolution, target_codec)
            ydl_opts.update({
                "format": format_str,
                "merge_output_format": effective_container,
            })

        downloaded_files = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if is_audio_mode and embed_thumb:
                    if crop_square:
                        ydl.add_post_processor(FFmpegSquareCropThumbnailPP(ydl), when="post_process")
                    if SafeEmbedThumbnailPP:
                        ydl.add_post_processor(SafeEmbedThumbnailPP(ydl, already_have_thumbnail=False), when="post_process")

                if is_upscale and mode == "video" and resolution and FFMPEG_EXE:
                    ydl.add_post_processor(
                        FFmpegUpscalePP(ydl, target_height=resolution, codec=target_codec),
                        when="post_process"
                    )
                info = ydl.extract_info(target_url, download=True)
                self._collect_downloaded_files(info, downloaded_files)
            return len(downloaded_files) > 0, downloaded_files
        except Exception:
            return False, []

    @classmethod
    def _collect_downloaded_files(cls, info: dict | None, out: list[Path]):
        """Recursively collects downloaded file paths from single or playlist yt-dlp info dicts."""
        if not info or not isinstance(info, dict):
            return
        if "entries" in info and isinstance(info["entries"], list):
            for entry in info["entries"]:
                cls._collect_downloaded_files(entry, out)
        if "requested_downloads" in info:
            for rd in info["requested_downloads"]:
                if rd.get("filepath"):
                    out.append(Path(rd["filepath"]))
        elif info.get("filepath"):
            out.append(Path(info["filepath"]))
