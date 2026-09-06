# =============================================================================
# downloader/src/extractors/instagram.py – Instagram Platform Extractor
# =============================================================================
import re
import urllib.request
import json
from pathlib import Path
from typing import Any

from extractors.base import BaseExtractor, MediaItem
from core.config import get_download_path, load_config
from core.progress import create_ytdlp_progress_hook, download_file_with_progress

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


class InstagramExtractor(BaseExtractor):
    """Extractor for Instagram Reels, Videos, and Photos."""

    INSTAGRAM_REGEX = re.compile(
        r"^(https?://)?(www\.)?instagram\.com/(p|reel|tv|reels)/([a-zA-Z0-9_-]+)"
    )

    @classmethod
    def is_suitable(cls, url: str) -> bool:
        return bool(cls.INSTAGRAM_REGEX.match(url.strip()))

    def validate_url(self, url: str) -> tuple[bool, str, str]:
        url = url.strip()
        m = self.INSTAGRAM_REGEX.match(url)
        if not m:
            return False, "", "Not a valid Instagram post/reel URL (expected format: https://www.instagram.com/reel/CODE/)"
        post_type = m.group(3)
        code = m.group(4)
        clean_url = f"https://www.instagram.com/{post_type}/{code}/"
        return True, clean_url, ""

    def fetch_metadata(self, url: str) -> MediaItem | None:
        m = self.INSTAGRAM_REGEX.match(url.strip())
        code = m.group(4) if m else "media"
        post_type = "Reel" if (m and m.group(3) in ("reel", "reels")) else "Post"

        # 1. Try oEmbed for quick preview
        title = f"Instagram {post_type} ({code})"
        author = "Instagram Creator"
        try:
            oembed_url = f"https://api.instagram.com/oembed/?url={urllib.parse.quote(url)}"
            req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                author = data.get("author_name", author)
                title = data.get("title") or f"{post_type} by {author}"
        except Exception:
            pass

        # 2. Extract with yt-dlp
        if yt_dlp:
            try:
                ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        uploader = info.get("uploader") or author
                        raw_title = info.get("title") or title
                        media_type = "video" if info.get("vcodec") != "none" else "image"
                        return MediaItem(
                            platform="instagram",
                            url=url,
                            title=raw_title[:60],
                            author=uploader,
                            media_type=media_type,
                            duration=float(info.get("duration") or 0.0),
                            thumbnail=info.get("thumbnail"),
                            raw_info=info
                        )
            except Exception:
                pass

        return MediaItem(
            platform="instagram",
            url=url,
            title=title,
            author=author,
            media_type="video" if "reel" in url.lower() else "image"
        )

    def download(self, item: MediaItem, options: dict[str, Any]) -> tuple[bool, list[Path]]:
        out_dir = get_download_path(options.get("output_dir"), platform="instagram")
        m = self.INSTAGRAM_REGEX.match(item.url)
        code = m.group(4) if m else "ig_media"

        downloaded_files = []

        # Try yt-dlp first
        if yt_dlp:
            hook = create_ytdlp_progress_hook(item.title)
            out_template = str(out_dir / f"instagram_%(uploader|creator)s_%(id)s_%(title).40s.%(ext)s")
            ydl_opts = {
                "outtmpl": out_template,
                "progress_hooks": [hook],
                "quiet": True,
                "noprogress": True,
                "no_warnings": True,
                "windowsfilenames": True,
            }
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

        # Direct OpenGraph fallback for photos
        try:
            req = urllib.request.Request(
                item.url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", "ignore")
                
                # Check og:video first
                v_match = re.search(r'<meta property="og:video" content="([^"]+)"', html)
                if v_match:
                    v_url = v_match.group(1).replace("&amp;", "&")
                    dest = out_dir / f"instagram_{code}.mp4"
                    if download_file_with_progress(v_url, dest):
                        downloaded_files.append(dest)
                        return True, downloaded_files

                # Check og:image
                img_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                if img_match:
                    img_url = img_match.group(1).replace("&amp;", "&")
                    dest = out_dir / f"instagram_{code}.jpg"
                    if download_file_with_progress(img_url, dest):
                        downloaded_files.append(dest)
                        return True, downloaded_files
        except Exception:
            pass

        return False, []
