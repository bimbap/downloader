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


def prompt_slide_selection(total_slides: int) -> list[int]:
    """Prompts user to select specific slide numbers (e.g. 1, 3 or 1-2). Returns list of 1-based indices."""
    print(f"\n  {BOLD_YELLOW}Select Slides to Download:{NC}")
    print(f"  {DIM}Examples: '1,3' for slides 1 & 3, '1-2' for slides 1 & 2, or 'all'{NC}")
    user_input = safe_input(f"  Slide numbers [1-{total_slides}]: ").strip()
    if not user_input or user_input.lower() in ("all", "a", "*"):
        return list(range(1, total_slides + 1))
    
    selected = set()
    parts = user_input.replace(";", ",").split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) == 2 and bounds[0].isdigit() and bounds[1].isdigit():
                start, end = int(bounds[0]), int(bounds[1])
                for num in range(min(start, end), max(start, end) + 1):
                    if 1 <= num <= total_slides:
                        selected.add(num)
        elif part.isdigit():
            num = int(part)
            if 1 <= num <= total_slides:
                selected.add(num)
    
    if not selected:
        print(f"  {BOLD_YELLOW}[!] No valid slide numbers recognized. Defaulting to all slides.{NC}")
        return list(range(1, total_slides + 1))
    
    return sorted(selected)


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

    download_opts = {}
    if len(item.items) > 1:
        options = [
            (f"Download All Slides ({len(item.items)} files) 🚀", "all", True, False),
            ("Select Specific Slides 🎯", "select", False, False),
            ("Cancel", "cancel", False, True)
        ]
        choice = select_menu_option("Download Options", options, clear_on_start=False)
        if choice == "cancel" or not choice:
            clear_screen()
            return
        elif choice == "select":
            selected = prompt_slide_selection(len(item.items))
            download_opts["selected_indices"] = selected
            print(f"\n  {BOLD_CYAN}Downloading {len(selected)} selected slide(s)...{NC}")
        else:
            download_opts["selected_indices"] = list(range(1, len(item.items) + 1))
            print(f"\n  {BOLD_CYAN}Downloading all {len(item.items)} slides...{NC}")
    else:
        options = [
            ("Download Media 🚀", "download", True, False),
            ("Cancel", "cancel", False, True)
        ]
        choice = select_menu_option("Confirm Download", options, clear_on_start=False)
        if choice != "download":
            clear_screen()
            return
        print(f"\n  {BOLD_CYAN}Downloading media...{NC}")

    success, files = extractor.download(item, options=download_opts)
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
