# =============================================================================
# downloader/src/extractors/threads.py – Threads (Meta) Platform Extractor
# =============================================================================
import re
import urllib.request
import json
import html
from pathlib import Path
from typing import Any

from extractors.base import BaseExtractor, MediaItem
from core.config import get_download_path, load_config
from core.progress import download_file_with_progress


class ThreadsExtractor(BaseExtractor):
    """Extractor for Meta Threads Posts (Videos and Photos)."""

    THREADS_REGEX = re.compile(
        r"^(https?://)?(www\.)?threads\.net/@([a-zA-Z0-9._]+)/post/([a-zA-Z0-9_-]+)"
    )

    @classmethod
    def is_suitable(cls, url: str) -> bool:
        return bool(cls.THREADS_REGEX.match(url.strip()))

    def validate_url(self, url: str) -> tuple[bool, str, str]:
        url = url.strip()
        m = self.THREADS_REGEX.match(url)
        if not m:
            return False, "", "Not a valid Threads URL (expected format: https://www.threads.net/@user/post/ID)"
        user = m.group(3)
        post_id = m.group(4)
        clean_url = f"https://www.threads.net/@{user}/post/{post_id}"
        return True, clean_url, ""

    def fetch_metadata(self, url: str) -> MediaItem | None:
        m = self.THREADS_REGEX.match(url.strip())
        if not m:
            return None
        user = m.group(3)
        post_id = m.group(4)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        title = f"Threads post by @{user}"
        media_type = "image"
        video_url = None
        image_url = None

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw_html = resp.read().decode("utf-8", "ignore")

                # Extract description/caption
                desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', raw_html)
                if desc_match:
                    desc_text = html.unescape(desc_match.group(1)).strip()
                    title = desc_text.split("\n")[0][:60] if desc_text else title

                # Check og:video
                vid_match = re.search(r'<meta property="og:video" content="([^"]+)"', raw_html)
                if vid_match:
                    video_url = html.unescape(vid_match.group(1))
                    media_type = "video"

                # Check og:image
                img_match = re.search(r'<meta property="og:image" content="([^"]+)"', raw_html)
                if img_match:
                    image_url = html.unescape(img_match.group(1))

                items = []
                if video_url:
                    items.append({"type": "video", "url": video_url})
                if image_url:
                    items.append({"type": "image", "url": image_url})

                return MediaItem(
                    platform="threads",
                    url=url,
                    title=title,
                    author=f"@{user}",
                    media_type=media_type,
                    thumbnail=image_url,
                    items=items,
                    raw_info={"video_url": video_url, "image_url": image_url}
                )
        except Exception:
            return MediaItem(
                platform="threads",
                url=url,
                title=title,
                author=f"@{user}",
                media_type="video"
            )

    def download(self, item: MediaItem, options: dict[str, Any]) -> tuple[bool, list[Path]]:
        m = self.THREADS_REGEX.match(item.url)
        user = m.group(3) if m else "threads"
        post_id = m.group(4) if m else "media"

        downloaded_files = []

        # Download from discovered media items
        for itm in item.items:
            m_url = itm.get("url")
            m_type = itm.get("type", "image")
            if not m_url:
                continue

            # Skip thumbnail image if video was already downloaded
            if m_type == "image" and any(f.suffix == ".mp4" for f in downloaded_files):
                continue

            category = "video" if m_type == "video" else "photo"
            dest_dir = get_download_path(options.get("output_dir"), platform="threads", media_type=category)

            ext = ".mp4" if m_type == "video" else ".jpg"
            clean_title = re.sub(r'[\\/*?:"<>|]', "", item.title[:35]).strip()
            filename = f"@{user}_{post_id}_{clean_title}{ext}" if clean_title else f"@{user}_{post_id}{ext}"
            dest = dest_dir / filename

            print(f"  Downloading Threads {m_type.capitalize()}...")
            if download_file_with_progress(m_url, dest):
                downloaded_files.append(dest)

        return len(downloaded_files) > 0, downloaded_files
