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
from core.progress import download_file_with_progress, safe_urlopen


class ThreadsExtractor(BaseExtractor):
    """Extractor for Meta Threads Posts (Videos, Photos, and Carousels/Slides)."""

    THREADS_REGEX = re.compile(
        r"^(?:https?://)?(?:www\.)?threads\.(?:net|com)/(?:@([a-zA-Z0-9._]+)/)?(?:post|t|share)/([a-zA-Z0-9_-]+)(?:[/?#].*)?$",
        re.IGNORECASE
    )

    BROWSER_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }

    @classmethod
    def is_suitable(cls, url: str) -> bool:
        return bool(cls.THREADS_REGEX.search(url.strip()))

    def validate_url(self, url: str) -> tuple[bool, str, str]:
        url = url.strip()
        m = self.THREADS_REGEX.search(url)
        if not m:
            return False, "", "Not a valid Threads URL (expected format: https://www.threads.net/@user/post/ID, /t/ID, or /share/ID)"
        user = m.group(1)
        post_id = m.group(2)
        if "/share/" in url.lower():
            clean_url = f"https://www.threads.net/share/{post_id}/"
        elif user:
            clean_url = f"https://www.threads.net/@{user}/post/{post_id}"
        else:
            clean_url = f"https://www.threads.net/t/{post_id}"
        return True, clean_url, ""

    @staticmethod
    def _collect_posts(node: Any, out: list[dict]):
        """Recursively traverses embedded json tree to collect all thread post/media objects."""
        if not node or not isinstance(node, (dict, list)):
            return
        if isinstance(node, dict):
            if "code" in node and isinstance(node.get("code"), str) and (
                "user" in node or "caption" in node or "image_versions2" in node or "video_versions" in node or "carousel_media" in node
            ):
                out.append(node)
            if "thread_items" in node and isinstance(node["thread_items"], list):
                for item in node["thread_items"]:
                    if isinstance(item, dict) and "post" in item and isinstance(item["post"], dict):
                        if item["post"].get("code"):
                            out.append(item["post"])
            for v in node.values():
                ThreadsExtractor._collect_posts(v, out)
        elif isinstance(node, list):
            for item in node:
                ThreadsExtractor._collect_posts(item, out)

    @staticmethod
    def _collect_self_thread(target_post: dict, all_posts: list[dict], author_name: str) -> list[dict]:
        """Collects the author's continuous self-reply thread starting from target_post."""
        root_code = target_post.get("code")
        root_time = target_post.get("taken_at") or 0
        by_code: dict[str, dict] = {}
        for p in all_posts:
            c = p.get("code")
            if not c or c == root_code or c in by_code:
                continue
            p_user = (p.get("user") or {}).get("username")
            tp = p.get("text_post_app_info") or {}
            reply_to = (tp.get("reply_to_author") or {}).get("username")
            p_time = p.get("taken_at") or 0
            if p_user == author_name and reply_to == author_name and p_time >= root_time:
                by_code[c] = p

        continuations = sorted(by_code.values(), key=lambda x: x.get("taken_at") or 0)
        return [target_post, *continuations]

    @staticmethod
    def _extract_post_media(post_obj: dict) -> list[dict]:
        """Extracts normalized media dicts (without final index) from a single Threads post object."""
        found: list[dict] = []
        carousel = post_obj.get("carousel_media") or []
        if carousel:
            for itm in carousel:
                v_ver = itm.get("video_versions") or []
                v_url = v_ver[0].get("url") if v_ver else None
                i_ver = itm.get("image_versions2", {}).get("candidates") or []
                i_url = i_ver[0].get("url") if i_ver else None
                m_type = "video" if v_url else "image"
                m_url = v_url if v_url else i_url
                if m_url:
                    found.append({"type": m_type, "media_type": m_type, "url": m_url, "thumbnail": i_url})
        elif post_obj.get("video_versions"):
            v_url = post_obj["video_versions"][0].get("url")
            if v_url:
                found.append({"type": "video", "media_type": "video", "url": v_url})
        elif post_obj.get("image_versions2", {}).get("candidates"):
            i_url = post_obj["image_versions2"]["candidates"][0].get("url")
            if i_url:
                found.append({"type": "image", "media_type": "image", "url": i_url, "thumbnail": i_url})
        elif post_obj.get("giphy_media_info"):
            gif_url = post_obj["giphy_media_info"].get("images", {}).get("fixed_height", {}).get("url")
            if gif_url:
                found.append({"type": "image", "media_type": "image", "url": gif_url, "thumbnail": gif_url})
        return found

    def fetch_metadata(self, url: str) -> MediaItem | None:
        m = self.THREADS_REGEX.search(url.strip())
        if not m:
            return None
        user = m.group(1) or "threads"
        post_id = m.group(2)

        try:
            with safe_urlopen(url, headers=self.BROWSER_HEADERS, timeout=10) as resp:
                final_url = resp.geturl()
                raw_html = resp.read().decode("utf-8", "ignore")

                # If redirected (e.g. from /share/ or /t/), re-extract user and post_id from final_url
                final_m = self.THREADS_REGEX.search(final_url)
                if final_m:
                    if final_m.group(1):
                        user = final_m.group(1)
                    if final_m.group(2):
                        post_id = final_m.group(2)

                canonical_url = f"https://www.threads.net/@{user}/post/{post_id}" if user != "threads" else url

                # 1. Primary: Extract from embedded data-sjs JSON blocks (full carousel/media support)
                sjs_blocks = re.findall(
                    r'<script[^>]*type="application/json"[^>]*\bdata-sjs\b[^>]*>(.*?)</script>',
                    raw_html,
                    re.DOTALL
                )

                posts = []
                for block in sjs_blocks:
                    try:
                        parsed = json.loads(block)
                        self._collect_posts(parsed, posts)
                    except Exception:
                        pass

                target_post = next((p for p in posts if p.get("code") == post_id), None)

                if target_post:
                    author_name = target_post.get("user", {}).get("username") or user
                    caption = (target_post.get("caption", {}).get("text", "") or "").strip()
                    title = caption.split("\n")[0][:60] if caption else f"Threads post by @{author_name}"
                    item_url = f"https://www.threads.net/@{author_name}/post/{post_id}"

                    # Collect continuous self-reply thread chain (e.g. 1/11 -> 11/11)
                    chain_posts = self._collect_self_thread(target_post, posts, author_name)
                    if len(chain_posts) > 1:
                        total_parts = len(chain_posts)
                        formatted_parts = []
                        for p_idx, cp in enumerate(chain_posts, 1):
                            cp_text = ((cp.get("caption") or {}).get("text") or "").strip()
                            if cp_text:
                                formatted_parts.append(f"[{p_idx}/{total_parts}]\n{cp_text}")
                        if formatted_parts:
                            caption = "\n\n".join(formatted_parts)
                        target_post["_thread_chain_count"] = total_parts

                    all_media: list[dict] = []
                    for cp in chain_posts:
                        for m_itm in self._extract_post_media(cp):
                            m_itm["index"] = len(all_media) + 1
                            all_media.append(m_itm)

                    if len(all_media) > 1:
                        return MediaItem(
                            platform="threads",
                            url=item_url,
                            title=title,
                            author=f"@{author_name}",
                            media_type="gallery",
                            thumbnail=next((x.get("thumbnail") for x in all_media if x.get("thumbnail")), None),
                            caption=caption,
                            items=all_media,
                            raw_info=target_post
                        )

                    elif len(all_media) == 1:
                        single = all_media[0]
                        return MediaItem(
                            platform="threads",
                            url=item_url,
                            title=title,
                            author=f"@{author_name}",
                            media_type=single["media_type"],
                            thumbnail=single.get("thumbnail"),
                            caption=caption,
                            items=all_media,
                            raw_info=target_post
                        )

                    elif caption:
                        return MediaItem(
                            platform="threads",
                            url=item_url,
                            title=title,
                            author=f"@{author_name}",
                            media_type="text",
                            caption=caption,
                            items=[],
                            raw_info=target_post
                        )

                # 2. Fallback: Meta OpenGraph extraction
                desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', raw_html)
                full_og_desc = html.unescape(desc_match.group(1)).strip() if desc_match else ""
                title = full_og_desc.split("\n")[0][:60] if full_og_desc else f"Threads post by @{user}"

                vid_match = re.search(r'<meta property="og:video" content="([^"]+)"', raw_html)
                img_match = re.search(r'<meta property="og:image" content="([^"]+)"', raw_html)

                if vid_match:
                    v_url = html.unescape(vid_match.group(1))
                    return MediaItem(
                        platform="threads",
                        url=canonical_url,
                        title=title,
                        author=f"@{user}",
                        media_type="video",
                        caption=full_og_desc,
                        items=[{"index": 1, "type": "video", "media_type": "video", "url": v_url}],
                    )
                elif img_match:
                    i_url = html.unescape(img_match.group(1))
                    return MediaItem(
                        platform="threads",
                        url=canonical_url,
                        title=title,
                        author=f"@{user}",
                        media_type="image",
                        thumbnail=i_url,
                        caption=full_og_desc,
                        items=[{"index": 1, "type": "image", "media_type": "image", "url": i_url}],
                    )

        except Exception:
            pass

        return MediaItem(
            platform="threads",
            url=url,
            title=f"Threads post by @{user}",
            author=f"@{user}",
            media_type="video"
        )

    def download(self, item: MediaItem, options: dict[str, Any]) -> tuple[bool, list[Path]]:
        m = self.THREADS_REGEX.search(item.url)
        user = (m.group(1) if m and m.group(1) else None) or "threads"
        post_id = m.group(2) if m else "media"

        downloaded_files = []
        author_clean = re.sub(r'[\\/*?:"<>|@]', "", item.author.replace(" ", "_")).strip() or user
        selected_indices = options.get("selected_indices")
        link_folder = f"@{author_clean}_{post_id}"

        # Multi-item / slide download
        if item.items and len(item.items) > 1:
            targets = [
                itm for itm in item.items
                if (not selected_indices or itm.get("index") in selected_indices)
            ]
            types_set = {
                "video" if (itm.get("media_type") or itm.get("type", "image")) == "video" else "photo"
                for itm in targets
            }
            bundle_cat = "gallery" if len(types_set) > 1 else (next(iter(types_set)) if types_set else "photo")
            target_dir = get_download_path(options.get("output_dir"), platform="threads", media_type=bundle_cat, subfolder=link_folder)

            for itm in targets:
                idx = itm.get("index", 1)
                m_url = itm.get("url")
                if not m_url:
                    continue

                m_type = itm.get("media_type") or itm.get("type", "image")
                is_vid = m_type == "video"
                ext = ".mp4" if is_vid else ".jpg"

                filename = f"@{author_clean}_{post_id}_slide_{idx}{ext}"
                dest = target_dir / filename

                disp_type = "Video" if is_vid else "Image"
                print(f"  Downloading Slide {idx}/{len(item.items)} ({disp_type})...")
                if download_file_with_progress(m_url, dest):
                    downloaded_files.append(dest)

            if downloaded_files:
                return True, downloaded_files

        # Single item download
        if item.items:
            itm = item.items[0]
            m_url = itm.get("url")
            m_type = itm.get("media_type") or itm.get("type", "image")
            is_vid = m_type == "video"
            category = "video" if is_vid else "photo"
            ext = ".mp4" if is_vid else ".jpg"

            target_dir = get_download_path(options.get("output_dir"), platform="threads", media_type=category, subfolder=link_folder)
            clean_title = re.sub(r'[\x00-\x1f\x7f\\/*?:"<>|]', "", item.title[:35]).strip()
            filename = f"@{author_clean}_{post_id}_{clean_title}{ext}" if clean_title else f"@{author_clean}_{post_id}{ext}"
            dest = target_dir / filename

            disp_type = "Video" if is_vid else "Photo"
            print(f"  Downloading Threads {disp_type}...")
            if m_url and download_file_with_progress(m_url, dest):
                downloaded_files.append(dest)
                return True, downloaded_files

        if item.media_type == "text" and item.caption:
            get_download_path(options.get("output_dir"), platform="threads", media_type="posts", subfolder=link_folder)
            return True, []

        return False, []
