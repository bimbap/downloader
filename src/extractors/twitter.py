# =============================================================================
# downloader/src/extractors/twitter.py – X (formerly Twitter) Extractor
# =============================================================================
import re
import urllib.request
import json
from urllib.parse import urlparse
from pathlib import Path
from typing import Any

from extractors.base import BaseExtractor, MediaItem
from core.config import get_download_path, load_config, get_cookie_opts
from core.progress import create_ytdlp_progress_hook, download_file_with_progress
from core.ffmpeg_engine import FFMPEG_EXE

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


class TwitterExtractor(BaseExtractor):
    """Extractor for X / Twitter Videos, GIFs, and Photos."""

    TWITTER_REGEX = re.compile(
        r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)/status/([0-9]+)",
        re.IGNORECASE
    )

    @classmethod
    def is_suitable(cls, url: str) -> bool:
        return bool(cls.TWITTER_REGEX.search(url.strip()))

    def validate_url(self, url: str) -> tuple[bool, str, str]:
        url = url.strip()
        m = self.TWITTER_REGEX.search(url)
        if not m:
            return False, "", "Not a valid X/Twitter post URL (expected format: https://x.com/username/status/123...)"
        user = m.group(1)
        tweet_id = m.group(2)
        clean_url = f"https://x.com/{user}/status/{tweet_id}"
        return True, clean_url, ""

    def fetch_metadata(self, url: str) -> MediaItem | None:
        m = self.TWITTER_REGEX.search(url.strip())
        if not m:
            return None
        user = m.group(1)
        tweet_id = m.group(2)

        # 1. Query VxTwitter API for comprehensive metadata
        api_url = f"https://api.vxtwitter.com/{user}/status/{tweet_id}"
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))

                author = data.get("user_name") or user
                screen_name = data.get("user_screen_name") or user
                text = data.get("text", "").strip()
                title = text.split("\n")[0][:60] if text else f"Tweet by @{screen_name}"

                media_items = []
                media_type = "text"

                # Check media_extended
                extended = data.get("media_extended", [])
                if extended:
                    has_video = any(m.get("type") in ("video", "gif") for m in extended)
                    has_image = any(m.get("type") == "image" for m in extended)

                    if len(extended) > 1:
                        media_type = "gallery"
                    elif has_video:
                        media_type = "video"
                    elif has_image:
                        media_type = "image"

                    for idx, m_obj in enumerate(extended, 1):
                        m_type = m_obj.get("type", "image")
                        m_url = m_obj.get("url", "")
                        # For twitter images, request original resolution
                        if m_type == "image" and "pbs.twimg.com" in m_url and not m_url.endswith(":orig"):
                            m_url = f"{m_url}:orig"
                        media_items.append({
                            "index": idx,
                            "type": m_type,
                            "media_type": m_type,
                            "url": m_url,
                            "thumbnail": m_obj.get("thumbnail_url"),
                        })

                return MediaItem(
                    platform="twitter",
                    url=url,
                    title=title,
                    author=f"@{screen_name} ({author})",
                    media_type=media_type,
                    items=media_items,
                    raw_info=data
                )
        except Exception:
            pass

        # 2. Fallback to yt-dlp metadata extraction
        if yt_dlp:
            try:
                ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
                ydl_opts.update(get_cookie_opts())
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        entries = info.get("entries") or []
                        media_items = []
                        if entries:
                            for idx, entry in enumerate(entries, 1):
                                if not entry:
                                    continue
                                vformats = entry.get("formats") or []
                                thumbs = entry.get("thumbnails") or []
                                is_vid = bool(vformats)
                                best_u = None
                                if is_vid:
                                    v_cands = [f for f in vformats if f.get("vcodec") not in (None, "none")]
                                    prog = [f for f in v_cands if f.get("acodec") not in (None, "none")]
                                    best_f = prog[-1] if prog else (v_cands[-1] if v_cands else vformats[-1])
                                    best_u = best_f.get("url")
                                else:
                                    best_u = thumbs[-1].get("url") if thumbs else entry.get("url")
                                media_items.append({
                                    "index": idx,
                                    "type": "video" if is_vid else "image",
                                    "media_type": "video" if is_vid else "image",
                                    "url": best_u,
                                    "thumbnail": thumbs[-1].get("url") if thumbs else entry.get("thumbnail")
                                })

                        media_type = "gallery" if len(media_items) > 1 else (
                            media_items[0]["media_type"] if media_items else ("video" if (info.get("formats") or info.get("vcodec")) else "image")
                        )

                        return MediaItem(
                            platform="twitter",
                            url=url,
                            title=info.get("title", f"Tweet {tweet_id}"),
                            author=info.get("uploader", f"@{user}"),
                            media_type=media_type,
                            duration=float(info.get("duration") or 0.0),
                            items=media_items,
                            raw_info=info
                        )
            except Exception:
                pass

        return MediaItem(
            platform="twitter",
            url=url,
            title=f"Tweet by @{user}",
            author=f"@{user}",
            media_type="video"
        )

    def download(self, item: MediaItem, options: dict[str, Any]) -> tuple[bool, list[Path]]:
        m = self.TWITTER_REGEX.search(item.url)
        user = m.group(1) if m else "twitter"
        tweet_id = m.group(2) if m else "media"

        downloaded_files = []

        # 1. Multi-item / slide download (carousel, multiple photos/videos)
        if item.items and len(item.items) > 1:
            selected_indices = options.get("selected_indices")
            targets = [
                itm for itm in item.items
                if (not selected_indices or itm.get("index") in selected_indices)
            ]
            for itm in targets:
                m_url = itm.get("url")
                if not m_url:
                    continue
                m_type = itm.get("media_type") or itm.get("type", "image")
                is_vid = m_type in ("video", "gif")
                category = "video" if is_vid else "photo"

                if is_vid:
                    ext = ".mp4"
                elif ".png" in m_url:
                    ext = ".png"
                elif ".webp" in m_url:
                    ext = ".webp"
                else:
                    ext = ".jpg"

                target_dir = get_download_path(options.get("output_dir"), platform="x", media_type=category)
                idx = itm.get("index", 1)
                filename = f"@{user}_{tweet_id}_slide_{idx}{ext}"
                dest = target_dir / filename

                disp_type = "Video" if is_vid else "Image"
                print(f"  Downloading Slide {idx}/{len(item.items)} ({disp_type})...")
                if download_file_with_progress(m_url, dest):
                    downloaded_files.append(dest)

            if downloaded_files:
                return True, downloaded_files

        # If it's a video/gif: prefer yt-dlp for best quality
        vid_dir = get_download_path(options.get("output_dir"), platform="x", media_type="video")
        if yt_dlp:
            hook = create_ytdlp_progress_hook(item.title)
            out_template = str(vid_dir / f"@{user}_%(id)s_%(title).50s.%(ext)s")
            ydl_opts = {
                "outtmpl": out_template,
                "progress_hooks": [hook],
                "quiet": True,
                "noprogress": True,
                "no_warnings": True,
                "windowsfilenames": True,
            }
            ydl_opts.update(get_cookie_opts())
            if FFMPEG_EXE:
                ydl_opts["ffmpeg_location"] = FFMPEG_EXE
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(item.url, download=True)
                    if info:
                        if "requested_downloads" in info:
                            for rd in info["requested_downloads"]:
                                if rd.get("filepath"):
                                    downloaded_files.append(Path(rd["filepath"]))
                        elif info.get("filepath"):
                            downloaded_files.append(Path(info["filepath"]))
                if downloaded_files:
                    return True, downloaded_files
            except Exception:
                pass

        # Direct download fallback from items
        if item.items:
            for itm in item.items:
                m_url = itm.get("url")
                if m_url:
                    is_vid = itm.get("type") in ("video", "gif")
                    ext = ".mp4" if is_vid else ".jpg"
                    dest_dir = vid_dir if is_vid else get_download_path(options.get("output_dir"), platform="x", media_type="photo")
                    dest = dest_dir / f"@{user}_{tweet_id}{ext}"
                    if download_file_with_progress(m_url, dest):
                        downloaded_files.append(dest)
            return len(downloaded_files) > 0, downloaded_files

        return False, []
