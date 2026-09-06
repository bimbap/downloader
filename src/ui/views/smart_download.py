# =============================================================================
# downloader/src/ui/views/smart_download.py – Universal Smart Download View
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
from core.file_manager import open_download_folder, open_file_in_player
from core.config import load_config
from core.i18n import t
from extractors import get_extractor_for_url, detect_platform
from ui.menu import select_menu_option


def render_download_result(success: bool, downloaded_files: list[Path], output_dir: Path):
    """Renders final result and interactive actions (Open folder, Play)."""
    print(f"\n{BOLD_CYAN}------------------------------------------------------------{NC}")
    if success and downloaded_files:
        print(f"  {BOLD_GREEN}✔ [{t('success')}]{NC} {t('download_success')}")
        print(f"  {t('destination')}: {BOLD_BLUE}{output_dir}{NC}")
        for idx, f in enumerate(downloaded_files[:4], 1):
            print(f"    {DIM}{idx}.{NC} {f.name}")
        if len(downloaded_files) > 4:
            print(f"    {DIM}... and {len(downloaded_files) - 4} more files{NC}")
    elif success:
        print(f"  {BOLD_GREEN}✔ [{t('success')}]{NC} {t('download_success')}")
        print(f"  {t('folder')}: {BOLD_BLUE}{output_dir}{NC}")
    else:
        print(f"  {BOLD_RED}✖ [{t('failed')}]{NC} {t('download_failed')}")

    print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")
    print(f"  {DIM}{t('return_hint')}{NC}")
    print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")

    while True:
        k = get_key()
        if k in ("ENTER", "Q", "ESC", "BACKSPACE"):
            clear_screen()
            break
        elif k == "O":
            open_download_folder(output_dir)
            clear_screen()
            break
        elif k == "P" and downloaded_files:
            open_file_in_player(downloaded_files[0])
            clear_screen()
            break


def run_smart_download(prefilled_url: str | None = None):
    """Prompts for any social media URL, auto-detects platform, and downloads."""
    clear_screen()
    print(f"{BOLD_CYAN}============================================================{NC}")
    print(f"{BOLD_YELLOW}{t('smart_title')}{NC}")
    print(f"{BOLD_CYAN}============================================================{NC}\n")
    print(f"  {DIM}Supported Platforms:{NC}")
    print(f"  • {BOLD_RED}YouTube{NC}   (Videos up to 8K, Audio 320k, Playlists, GPU Upscale)")
    print(f"  • {BOLD_CYAN}X/Twitter{NC} (Videos, GIFs, Full-Res Photo Galleries)")
    print(f"  • {BOLD_MAGENTA}Instagram{NC} (Reels, Videos, Photo Carousels)")
    print(f"  • {BOLD_YELLOW}Threads{NC}   (Videos, Photos)\n")

    if prefilled_url:
        url = prefilled_url.strip()
        print(f"  Target URL: {BOLD_GREEN}{url}{NC}\n")
    else:
        print(f"  {DIM}{t('smart_paste')}{NC}")
        url = safe_input("  URL: ").strip()

    if not url:
        clear_screen()
        return

    extractor = get_extractor_for_url(url)
    if not extractor:
        print(f"\n  {BOLD_RED}✖ [{t('error')}]{NC} {t('invalid_url')}")
        print(f"  {DIM}{t('invalid_url_hint')}{NC}")
        print(f"\n  {DIM}[Enter] {t('back_simple')}{NC}")
        get_key()
        clear_screen()
        return

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

    cfg = load_config()

    # YouTube specific routing if user wants specific audio/video/playlist options
    if item.platform == "youtube":
        from ui.views.youtube_view import run_youtube_download_flow
        run_youtube_download_flow(item)
        return

    # Social media (X, Instagram, Threads) direct confirmation
    clear_screen()
    platform_name = {
        "twitter": "X / Twitter",
        "instagram": "Instagram",
        "threads": "Threads",
    }.get(item.platform, item.platform.capitalize())

    print(f"{BOLD_CYAN}============================================================{NC}")
    print(f"{BOLD_YELLOW}Downloading Media from {platform_name}{NC}")
    print(f"{BOLD_CYAN}============================================================{NC}\n")
    print(f"  Platform    : {BOLD_CYAN}{platform_name}{NC}")
    print(f"  {t('author')}      : {BOLD_YELLOW}{item.author}{NC}")
    print(f"  {t('caption')}     : {BOLD}{item.title}{NC}")
    print(f"  {t('media_type')}  : {BOLD_MAGENTA}{item.media_type.upper()}{NC}")
    if item.items:
        print(f"  {t('items')} Count : {BOLD_GREEN}{len(item.items)} File(s){NC}")
    print(f"  {t('source_url')}  : {DIM}{item.url}{NC}")
    print("-" * 60 + "\n")

    download_opts = {}
    if len(item.items) > 1:
        from ui.views.social_view import prompt_slide_selection
        options = [
            (t("download_all_slides", count=len(item.items)), "all", True, False),
            (t("select_specific_slides"), "select", False, False),
            (t("cancel"), "cancel", False, True)
        ]
        choice = select_menu_option(t("confirm"), options, clear_on_start=False)
        if choice == "cancel" or not choice:
            clear_screen()
            return
        elif choice == "select":
            selected = prompt_slide_selection(len(item.items))
            download_opts["selected_indices"] = selected
            print(f"\n  {BOLD_CYAN}{t('downloading_slides', count=len(selected))}{NC}")
        else:
            download_opts["selected_indices"] = list(range(1, len(item.items) + 1))
            print(f"\n  {BOLD_CYAN}{t('downloading_all_slides', count=len(item.items))}{NC}")
    else:
        options = [
            (t("download_media"), "download", True, False),
            (t("cancel"), "cancel", False, True)
        ]
        choice = select_menu_option(t("ready_to_download"), options, clear_on_start=False)
        if choice != "download":
            clear_screen()
            return
        print(f"\n  {BOLD_CYAN}{t('downloading_media')}{NC}")

    success, files = extractor.download(item, options=download_opts)

    from core.config import get_download_path
    target_out = files[0].parent if files else get_download_path(platform=item.platform)
    render_download_result(success, files, target_out)
