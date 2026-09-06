# =============================================================================
# downloader/src/ui/views/social_view.py – Social Media Views (X, IG, Threads)
# =============================================================================
import sys
from pathlib import Path

from core.console import (
    BOLD_CYAN,
    BOLD_YELLOW,
    BOLD_GREEN,
    BOLD_RED,
    BOLD_MAGENTA,
    BOLD_BLUE,
    DIM,
    BOLD,
    NC,
    clear_screen,
    safe_input,
    get_key,
)
from core.config import get_download_path
from extractors.base import MediaItem
from extractors.twitter import TwitterExtractor
from extractors.instagram import InstagramExtractor
from extractors.threads import ThreadsExtractor
from ui.menu import select_menu_option
from ui.views.smart_download import render_download_result


def run_platform_flow(extractor_cls, platform_title: str, platform_key: str, color_code: str, example_url: str):
    """Generic interactive flow for social media platforms."""
    clear_screen()
    print(f"{BOLD_CYAN}============================================================{NC}")
    print(f"{color_code}{platform_title}{NC}")
    print(f"{BOLD_CYAN}============================================================{NC}\n")
    print(f"  {DIM}Paste your link (e.g. {example_url}):{NC}")
    url = safe_input("  URL: ").strip()

    if not url:
        clear_screen()
        return

    extractor = extractor_cls()
    is_valid, norm_url, reason = extractor.validate_url(url)
    if not is_valid:
        print(f"\n  {BOLD_RED}✖ [ERROR]{NC} {reason}")
        print(f"\n  {DIM}[Enter] Return to Menu{NC}")
        get_key()
        clear_screen()
        return

    print(f"\n  {DIM}🔍 Fetching post metadata...{NC}")
    item = extractor.fetch_metadata(norm_url)
    if not item:
        print(f"\n  {BOLD_RED}✖ [ERROR]{NC} Could not retrieve media details.")
        print(f"\n  {DIM}[Enter] Return to Menu{NC}")
        get_key()
        clear_screen()
        return

    clear_screen()
    print(f"{BOLD_CYAN}============================================================{NC}")
    print(f"{color_code}{platform_title} – Ready to Download{NC}")
    print(f"{BOLD_CYAN}============================================================{NC}\n")
    print(f"  Author      : {BOLD_YELLOW}{item.author}{NC}")
    print(f"  Caption     : {BOLD}{item.title}{NC}")
    print(f"  Media Type  : {BOLD_MAGENTA}{item.media_type.upper()}{NC}")
    if item.items:
        print(f"  Files Count : {BOLD_GREEN}{len(item.items)} File(s){NC}")
    out_dir = get_download_path(platform=platform_key)
    print(f"  Destination : {BOLD_BLUE}{out_dir}{NC}")
    print(f"  Source URL  : {DIM}{item.url}{NC}")
    print("-" * 60 + "\n")

    options = [
        ("Download Media 🚀", "download", True, False),
        ("Cancel", "cancel", False, True)
    ]
    choice = select_menu_option("Confirm Download", options, clear_on_start=False)
    if choice != "download":
        clear_screen()
        return

    print(f"\n  {BOLD_CYAN}Downloading media files...{NC}")
    success, files = extractor.download(item, options={})
    render_download_result(success, files, out_dir)


def run_twitter_view():
    run_platform_flow(
        TwitterExtractor,
        "🐦 X / Twitter Media Downloader",
        "x",
        BOLD_CYAN,
        "https://x.com/username/status/123..."
    )


def run_instagram_view():
    run_platform_flow(
        InstagramExtractor,
        "📷 Instagram Reels & Photo Downloader",
        "instagram",
        BOLD_MAGENTA,
        "https://www.instagram.com/reel/CODE/ or /p/CODE/"
    )


def run_threads_view():
    run_platform_flow(
        ThreadsExtractor,
        "🧵 Threads Video & Photo Downloader",
        "threads",
        BOLD_YELLOW,
        "https://www.threads.net/@user/post/ID"
    )
