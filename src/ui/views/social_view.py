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
from core.i18n import t
from extractors.base import MediaItem
from extractors.twitter import TwitterExtractor
from extractors.instagram import InstagramExtractor
from extractors.threads import ThreadsExtractor
from ui.menu import select_menu_option
from ui.views.smart_download import render_download_result


def prompt_slide_selection(total_slides: int) -> list[int]:
    """Prompts user to select specific slide numbers (e.g. 1, 3 or 1-2). Returns list of 1-based indices."""
    print(f"\n  {BOLD_YELLOW}{t('slide_selection_prompt')}{NC}")
    print(f"  {DIM}{t('slide_selection_hint')}{NC}")
    user_input = safe_input(f"  {t('slide_numbers', total=total_slides)}").strip()
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
    print(f"{BOLD_CYAN}── {color_code}{platform_title}{BOLD_CYAN} ─────────────────────────────{NC}")
    print(f"  {DIM}{t('paste_link')} (e.g. {example_url}):{NC}\n")
    url = safe_input("  URL: ").strip()

    if not url:
        clear_screen()
        return

    extractor = extractor_cls()
    is_valid, norm_url, reason = extractor.validate_url(url)
    if not is_valid:
        print(f"\n  {BOLD_RED}✖ [{t('error')}]{NC} {reason}")
        print(f"\n  {DIM}[Enter] {t('back_simple')}{NC}")
        get_key()
        clear_screen()
        return

    print(f"\n  {DIM}{t('fetching_meta')}{NC}")
    item = extractor.fetch_metadata(norm_url)
    if not item:
        print(f"\n  {BOLD_RED}✖ [{t('error')}]{NC} Could not retrieve media details.")
        print(f"\n  {DIM}[Enter] {t('back_simple')}{NC}")
        get_key()
        clear_screen()
        return

    out_dir = get_download_path(platform=platform_key)
    caption_disp = (item.title[:50] + "…") if len(item.title) > 50 else item.title
    info_header = [
        f"{t('author')}      : {BOLD_YELLOW}{item.author}{NC}",
        f"{t('caption')}     : {BOLD}{caption_disp}{NC}",
        f"{t('media_type')}  : {BOLD_MAGENTA}{item.media_type.upper()}{NC}" + (f" ({len(item.items)} files)" if item.items else ""),
        f"{t('destination')} : {BOLD_BLUE}{out_dir}{NC}"
    ]

    download_opts = {}
    if len(item.items) > 1:
        options = [
            (t("download_all_slides", count=len(item.items)), "all", True, False),
            (t("select_specific_slides"), "select", False, False),
            (t("cancel"), "cancel", False, True)
        ]
        choice = select_menu_option(f"{platform_title} – {t('ready_to_download')}", options, header_info=info_header)
        if choice == "cancel" or not choice:
            clear_screen()
            return
        elif choice == "select":
            selected = prompt_slide_selection(len(item.items))
            download_opts["selected_indices"] = selected
            clear_screen()
            print(f"\n  {BOLD_CYAN}{t('downloading_slides', count=len(selected))}{NC}\n")
        else:
            download_opts["selected_indices"] = list(range(1, len(item.items) + 1))
            clear_screen()
            print(f"\n  {BOLD_CYAN}{t('downloading_all_slides', count=len(item.items))}{NC}\n")
    else:
        options = [
            (t("download_media"), "download", True, False),
            (t("cancel"), "cancel", False, True)
        ]
        choice = select_menu_option(f"{platform_title} – {t('ready_to_download')}", options, header_info=info_header)
        if choice != "download":
            clear_screen()
            return
        clear_screen()
        print(f"\n  {BOLD_CYAN}{t('downloading_media')}{NC}\n")

    success, files = extractor.download(item, options=download_opts)
    target_out = files[0].parent if files else out_dir
    render_download_result(success, files, target_out)


def run_twitter_view():
    run_platform_flow(
        TwitterExtractor,
        "X / Twitter Downloader",
        "x",
        BOLD_CYAN,
        "https://x.com/username/status/123..."
    )


def run_instagram_view():
    run_platform_flow(
        InstagramExtractor,
        "Instagram Downloader",
        "instagram",
        BOLD_MAGENTA,
        "https://www.instagram.com/reel/CODE/ or /p/CODE/"
    )


def run_threads_view():
    run_platform_flow(
        ThreadsExtractor,
        "Threads Downloader",
        "threads",
        BOLD_YELLOW,
        "https://www.threads.net/@user/post/ID or /share/ID"
    )
