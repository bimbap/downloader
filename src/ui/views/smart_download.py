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
    sanitize_terminal_text,
)
from core.file_manager import open_download_folder, open_file_in_player, save_caption_file
from core.config import load_config, get_download_path
from core.batch import parse_batch_input, validate_batch_urls, execute_batch_download
from core.i18n import t
from extractors import get_extractor_for_url, detect_platform
from extractors.youtube import YouTubeExtractor
from ui.menu import select_menu_option


def render_caption_viewer(item):
    """Displays the full sanitized post caption/description in a clean screen."""
    clear_screen()
    safe_title = sanitize_terminal_text(getattr(item, "title", ""))
    safe_author = sanitize_terminal_text(getattr(item, "author", ""))
    raw_cap = (getattr(item, "caption", "") or "").strip()
    safe_lines = [sanitize_terminal_text(ln) for ln in raw_cap.splitlines()]

    print(f"{BOLD_CYAN}── {BOLD_YELLOW}{t('caption_viewer_title')}{BOLD_CYAN} ─────────────────────────────{NC}\n")
    print(f"  {t('author')} : {BOLD_YELLOW}{safe_author}{NC}")
    if safe_title:
        print(f"  {t('title')}  : {BOLD}{safe_title}{NC}")
    print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")
    for ln in safe_lines:
        print(f"  {ln}" if ln else "")
    print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")
    print(f"  {DIM}[Enter / q] {t('back_simple')}{NC}")

    while True:
        k = get_key()
        if k in ("ENTER", "Q", "ESC", "BACKSPACE"):
            break


def render_download_result(success: bool, downloaded_files: list[Path], output_dir: Path, item=None):
    """Renders final result and interactive actions (Open folder, Play, View Caption)."""
    caption_path = None
    has_caption = bool(item and (getattr(item, "caption", "") or "").strip())
    if success and has_caption and load_config().get("save_caption", True):
        caption_path = save_caption_file(item, downloaded_files, fallback_dir=output_dir)

    while True:
        if success:
            clear_screen()
        print(f"\n{BOLD_CYAN}------------------------------------------------------------{NC}")
        if success and downloaded_files:
            print(f"  {BOLD_GREEN}✔ [{t('success')}]{NC} {t('download_success')}")
            print(f"  {t('destination')}: {BOLD_BLUE}{output_dir}{NC}")
            for idx, f in enumerate(downloaded_files[:4], 1):
                print(f"    {DIM}{idx}.{NC} {sanitize_terminal_text(f.name)}")
            if len(downloaded_files) > 4:
                print(f"    {DIM}... and {len(downloaded_files) - 4} more files{NC}")
            if caption_path:
                print(f"    {BOLD_CYAN}📝 {t('caption_saved', filename=caption_path.name)}{NC}")
        elif success:
            print(f"  {BOLD_GREEN}✔ [{t('success')}]{NC} {t('download_success')}")
            print(f"  {t('folder')}: {BOLD_BLUE}{output_dir}{NC}")
            if caption_path:
                print(f"    {BOLD_CYAN}📝 {t('caption_saved', filename=caption_path.name)}{NC}")
        else:
            print(f"  {BOLD_RED}✖ [{t('failed')}]{NC} {t('download_failed')}")

        print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")
        hint_key = "return_hint_caption" if has_caption else "return_hint"
        print(f"  {DIM}{t(hint_key)}{NC}")
        print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")

        while True:
            k = get_key()
            if k in ("ENTER", "Q", "ESC", "BACKSPACE"):
                clear_screen()
                return
            elif k == "O":
                open_download_folder(output_dir)
                clear_screen()
                return
            elif k == "P" and downloaded_files:
                open_file_in_player(downloaded_files[0])
                clear_screen()
                return
            elif k == "C" and has_caption:
                render_caption_viewer(item)
                break


def collect_multiline_urls() -> list[str]:
    """Collects multiple URLs entered line-by-line until an empty line is submitted."""
    print(f"\n  {BOLD_CYAN}{t('batch_multiline_prompt')}{NC}\n")
    collected: list[str] = []
    while True:
        line = safe_input(f"  [{len(collected) + 1}] URL: ").strip()
        if not line:
            break
        collected.extend(parse_batch_input(line))
    return list(dict.fromkeys(collected))


def render_batch_result(summary: dict, output_dir: Path):
    """Renders final batch summary with open-folder shortcut."""
    clear_screen()
    ok_count = len(summary["succeeded"])
    total = summary["total"]
    fail_list = summary["failed"]
    files = summary["files"]

    print(f"\n{BOLD_CYAN}------------------------------------------------------------{NC}")
    if ok_count > 0:
        print(f"  {BOLD_GREEN}✔ [{t('success')}]{NC} {t('batch_summary', ok=ok_count, total=total)}")
    else:
        print(f"  {BOLD_RED}✖ [{t('failed')}]{NC} {t('batch_summary', ok=ok_count, total=total)}")

    print(f"  {t('destination')}: {BOLD_BLUE}{output_dir}{NC}")
    for idx, f in enumerate(files[:5], 1):
        print(f"    {DIM}{idx}.{NC} {sanitize_terminal_text(f.name)}")
    if len(files) > 5:
        print(f"    {DIM}... and {len(files) - 5} more file(s){NC}")

    if fail_list:
        print(f"\n  {BOLD_RED}{t('failed')} ({len(fail_list)}):{NC}")
        for entry in fail_list[:5]:
            print(f"    {BOLD_RED}✖{NC} {sanitize_terminal_text(entry['url'])} ({entry['reason']})")

    print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")
    print(f"  {DIM}[Enter] {t('back_simple')}  |  [o] {t('open_folder')}{NC}")
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


def run_batch_download_flow(
    raw_urls: list[str],
    extractor_cls: type | None = None,
    title_prefix: str = "Batch Download"
):
    """Validates, confirms, and executes a batch download with per-item screen clearing."""
    valid_targets, invalid_entries = validate_batch_urls(raw_urls, extractor_cls=extractor_cls)
    if not valid_targets:
        print(f"\n  {BOLD_RED}✖ [{t('error')}]{NC} {t('batch_no_valid')}")
        print(f"\n  {DIM}[Enter] {t('back_simple')}{NC}")
        get_key()
        clear_screen()
        return

    cfg = load_config()
    has_youtube = any(isinstance(ext, YouTubeExtractor) for ext, _ in valid_targets)
    res_tag = "Auto/Max" if cfg.get("default_resolution", "1080") in ("best", "max", "auto") else f"{cfg.get('default_resolution', '1080')}p"
    audio_fmt = cfg.get("audio_format", "mp3").upper()

    header = [
        f"Valid Links : {BOLD_GREEN}{len(valid_targets)}{NC} link(s)" + (f"  |  {BOLD_YELLOW}{t('batch_invalid_skipped', count=len(invalid_entries))}{NC}" if invalid_entries else ""),
        f"Destination : {BOLD_BLUE}{get_download_path()}{NC}"
    ]

    if has_youtube:
        options = [
            (t("batch_start_video", res=res_tag), "video", True, False),
            (t("batch_start_audio", fmt=audio_fmt), "audio", True, False),
            (t("cancel"), "cancel", False, True),
        ]
    else:
        options = [
            (t("batch_start", count=len(valid_targets)), "video", True, False),
            (t("cancel"), "cancel", False, True),
        ]

    choice = select_menu_option(f"{title_prefix} – {t('batch_ready')}", options, header_info=header)
    if choice in ("cancel", None):
        clear_screen()
        return

    batch_opts = {"mode": choice}

    def on_item_start(idx: int, total: int, _ext, norm_url: str):
        clear_screen()
        print(f"{BOLD_CYAN}── {BOLD_YELLOW}{t('batch_progress', idx=idx, total=total)}{BOLD_CYAN} ─────────────────────────────{NC}")
        print(f"  {DIM}URL:{NC} {sanitize_terminal_text(norm_url)}\n")

    summary = execute_batch_download(valid_targets, options=batch_opts, on_item_start=on_item_start)
    final_dir = summary["files"][0].parent if summary["files"] else get_download_path()
    render_batch_result(summary, final_dir)


def run_smart_download(prefilled_url: str | None = None):
    """Prompts for single or batch social media URLs, auto-detects platform, and downloads."""
    clear_screen()
    print(f"{BOLD_CYAN}── {BOLD_YELLOW}{t('smart_title')}{BOLD_CYAN} ─────────────────────────────{NC}")
    print(f"  {DIM}Platforms: YouTube • X / Twitter • Instagram • Threads{NC}\n")

    if prefilled_url:
        raw_input = prefilled_url.strip()
        print(f"  Target URL: {BOLD_GREEN}{raw_input}{NC}\n")
    else:
        print(f"  {DIM}{t('smart_paste')}{NC}")
        raw_input = safe_input("  URL: ").strip()

    if not raw_input:
        clear_screen()
        return

    if raw_input.lower() in ("batch", "b"):
        urls = collect_multiline_urls()
        if not urls:
            clear_screen()
            return
        run_batch_download_flow(urls, title_prefix=t("smart_title"))
        return

    urls = parse_batch_input(raw_input)
    if not urls:
        clear_screen()
        return
    if len(urls) > 1:
        run_batch_download_flow(urls, title_prefix=t("smart_title"))
        return

    url = urls[0]

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

    # Social media (X, Instagram, Threads) confirmation flow
    from core.config import get_download_path
    target_out = get_download_path(platform=item.platform)
    platform_name = {
        "twitter": "X / Twitter",
        "instagram": "Instagram",
        "threads": "Threads",
    }.get(item.platform, item.platform.capitalize())

    safe_title = sanitize_terminal_text(item.title)
    safe_author = sanitize_terminal_text(item.author)
    caption_disp = (safe_title[:50] + "…") if len(safe_title) > 50 else safe_title
    info_header = [
        f"Platform    : {BOLD_CYAN}{platform_name}{NC}",
        f"{t('author')}      : {BOLD_YELLOW}{safe_author}{NC}",
        f"{t('caption')}     : {BOLD}{caption_disp}{NC}",
        f"{t('media_type')}  : {BOLD_MAGENTA}{item.media_type.upper()}{NC}" + (f" ({len(item.items)} files)" if item.items else ""),
        f"{t('destination')} : {BOLD_BLUE}{target_out}{NC}"
    ]

    download_opts = {}
    if len(item.items) > 1:
        from ui.views.social_view import prompt_slide_selection
        options = [
            (t("download_all_slides", count=len(item.items)), "all", True, False),
            (t("select_specific_slides"), "select", False, False),
            (t("cancel"), "cancel", False, True)
        ]
        choice = select_menu_option(f"{platform_name} – {t('ready_to_download')}", options, header_info=info_header)
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
        choice = select_menu_option(f"{platform_name} – {t('ready_to_download')}", options, header_info=info_header)
        if choice != "download":
            clear_screen()
            return
        clear_screen()
        print(f"\n  {BOLD_CYAN}{t('downloading_media')}{NC}\n")

    success, files = extractor.download(item, options=download_opts)

    final_out = files[0].parent if files else target_out
    render_download_result(success, files, final_out, item=item)
