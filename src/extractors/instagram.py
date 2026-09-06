# =============================================================================
# downloader/src/extractors/instagram.py – Instagram Platform Extractor
# =============================================================================
import re
import urllib.request
import urllib.parse
import json
from pathlib import Path
from typing import Any

from extractors.base import BaseExtractor, MediaItem
from core.config import get_download_path, load_config
from core.progress import create_ytdlp_progress_hook, download_file_with_progress

try:
    import yt_dlp
    from yt_dlp.extractor.instagram import InstagramIE

    class PhotoInstagramIE(InstagramIE):
        """Custom Instagram extractor that allows photo-only posts without throwing no-formats error."""
        def raise_no_formats(self, msg, expected=False):
            pass
except ImportError:
    yt_dlp = None
    InstagramIE = None
    PhotoInstagramIE = None


class InstagramExtractor(BaseExtractor):
    """Extractor for Instagram Reels, Videos, and Photo Carousels."""

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
            return False, "", "Not a valid Instagram post/reel URL (expected format: https://www.instagram.com/p/CODE/ or /reel/CODE/)"
        post_type = m.group(3)
        code = m.group(4)
        clean_url = f"https://www.instagram.com/{post_type}/{code}/"
        return True, clean_url, ""

    def fetch_metadata(self, url: str) -> MediaItem | None:
        m = self.INSTAGRAM_REGEX.match(url.strip())
        code = m.group(4) if m else "media"
        post_type = "Reel" if (m and m.group(3) in ("reel", "reels")) else "Post"

        # 1. Primary extractor via custom PhotoInstagramIE
        if yt_dlp and PhotoInstagramIE:
            try:
                ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
                ydl = yt_dlp.YoutubeDL(ydl_opts)
                ie = PhotoInstagramIE(ydl)
                info = ie._real_extract(url)

                if info:
                    channel = info.get("channel") or info.get("uploader_id") or ""
                    uploader = info.get("uploader") or ""
                    if channel and uploader and channel != uploader:
                        author = f"@{channel} ({uploader})"
                    elif channel:
                        author = f"@{channel}"
                    elif uploader:
                        author = uploader
                    else:
                        author = "Instagram Creator"

                    raw_desc = (info.get("description") or "").strip()
                    caption_snippet = raw_desc.split("\n")[0][:60] if raw_desc else (info.get("title") or f"Instagram {post_type} ({code})")

                    # Check carousel / multi-items
                    entries = info.get("entries") or []
                    if info.get("_type") == "playlist" or len(entries) > 0:
                        slide_items = []
                        for idx, entry in enumerate(entries, 1):
                            if not entry:
                                continue
                            vformats = entry.get("formats") or []
                            thumbs = entry.get("thumbnails") or []
                            is_video = bool(vformats)
                            m_url = vformats[-1]["url"] if is_video else (thumbs[-1]["url"] if thumbs else None)
                            thumb_url = thumbs[-1]["url"] if thumbs else entry.get("thumbnail")
                            slide_items.append({
                                "index": idx,
                                "id": entry.get("id") or f"slide_{idx}",
                                "media_type": "video" if is_video else "image",
                                "url": m_url,
                                "thumbnail": thumb_url,
                            })

                        media_type = "gallery" if len(slide_items) > 1 else (
                            slide_items[0]["media_type"] if slide_items else "image"
                        )

                        return MediaItem(
                            platform="instagram",
                            url=url,
                            title=caption_snippet,
                            author=author,
                            media_type=media_type,
                            thumbnail=slide_items[0].get("thumbnail") if slide_items else info.get("thumbnail"),
                            items=slide_items,
                            raw_info=info
                        )

                    # Single post / video
                    vformats = info.get("formats") or []
                    thumbs = info.get("thumbnails") or []
                    is_video = bool(vformats)
                    m_url = vformats[-1]["url"] if is_video else (thumbs[-1]["url"] if thumbs else None)
                    thumb_url = thumbs[-1]["url"] if thumbs else info.get("thumbnail")
                    single_item = [{
                        "index": 1,
                        "id": info.get("id") or code,
                        "media_type": "video" if is_video else "image",
                        "url": m_url,
                        "thumbnail": thumb_url,
                    }]
                    return MediaItem(
                        platform="instagram",
                        url=url,
                        title=caption_snippet,
                        author=author,
                        media_type="video" if is_video else "image",
                        duration=float(info.get("duration") or 0.0),
                        thumbnail=thumb_url,
                        items=single_item,
                        raw_info=info
                    )
            except Exception:
                pass

        # 2. Fallback: oEmbed for metadata preview
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

        raw_channel = item.raw_info.get("channel") or ""
        if not raw_channel and item.author.startswith("@"):
            raw_channel = item.author.split()[0].replace("@", "")
        author_clean = re.sub(r'[\\/*?:"<>|@]', "", raw_channel) if raw_channel else "instagram"

        downloaded_files = []
        selected_indices = options.get("selected_indices")

        # 1. Download from extracted items (Carousels, Photos, Direct URLs)
        if item.items:
            targets = [
                itm for itm in item.items
                if (not selected_indices or itm.get("index") in selected_indices)
            ]
            is_multi = len(item.items) > 1

            for target in targets:
                idx = target.get("index", 1)
                m_url = target.get("url")
                m_type = target.get("media_type", "image")
                ext = ".mp4" if m_type == "video" else ".jpg"

                if is_multi:
                    filename = f"@{author_clean}_{code}_slide_{idx}{ext}"
                    print(f"  Downloading Slide {idx}/{len(item.items)} ({m_type.capitalize()})...")
                else:
                    filename = f"@{author_clean}_{code}{ext}"
                    print(f"  Downloading Instagram {m_type.capitalize()}...")

                dest = out_dir / filename
                if m_url and download_file_with_progress(m_url, dest):
                    downloaded_files.append(dest)

            if downloaded_files:
                return True, downloaded_files

        # 2. Standalone Video / Reel fallback via yt-dlp
        if yt_dlp and item.media_type == "video":
            hook = create_ytdlp_progress_hook(item.title)
            out_template = str(out_dir / f"@{author_clean}_{code}_%(title).40s.%(ext)s")
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

        # 3. OpenGraph fallback
        try:
            req = urllib.request.Request(
                item.url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", "ignore")
                
                v_match = re.search(r'<meta property="og:video" content="([^"]+)"', html)
                if v_match:
                    v_url = v_match.group(1).replace("&amp;", "&")
                    dest = out_dir / f"@{author_clean}_{code}.mp4"
                    if download_file_with_progress(v_url, dest):
                        downloaded_files.append(dest)
                        return True, downloaded_files

                img_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                if img_match:
                    img_url = img_match.group(1).replace("&amp;", "&")
                    dest = out_dir / f"@{author_clean}_{code}.jpg"
                    if download_file_with_progress(img_url, dest):
                        downloaded_files.append(dest)
                        return True, downloaded_files
        except Exception:
            pass

        return False, []
