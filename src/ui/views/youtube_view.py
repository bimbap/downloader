# =============================================================================
# downloader/src/ui/views/youtube_view.py – YouTube View Controller
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
from core.config import (
    load_config,
    get_download_path,
    resolve_video_container,
)
from core.ffmpeg_engine import FFMPEG_EXE
from core.i18n import t
from extractors.base import MediaItem
from extractors.youtube import YouTubeExtractor
from ui.menu import select_menu_option
from ui.views.smart_download import render_download_result


def run_youtube_download_flow(item: MediaItem):
    """Handles full interactive options and execution for a YouTube video or playlist."""
    cfg = load_config()
    is_playlist = (item.media_type == "playlist")

    # If it's a playlist URL, check user playlist mode
    if is_playlist:
        pl_mode = cfg.get("playlist_mode", "ask")
        if pl_mode == "ask":
            pl_options = [
                (f"Download Full Playlist ({len(item.items)} videos)", "playlist", True, False),
                ("Download First Video Only", "single", True, False),
                (t("cancel"), "cancel", False, True)
            ]
            choice = select_menu_option(
                f"Playlist Detected: {item.title[:45]}",
                pl_options,
                header_info=[f"Playlist contains {BOLD_GREEN}{len(item.items)}{NC} items."]
            )
            if choice == "cancel" or choice is None:
                clear_screen()
                return
            is_playlist = (choice == "playlist")
        elif pl_mode == "single":
            is_playlist = False
        else:
            is_playlist = True

    # Mode selection: Video vs Audio
    target_res = cfg.get("default_resolution", "1080")
    target_codec = cfg.get("video_codec", "h264")
    target_container = cfg.get("video_container", "auto")
    eff_container = resolve_video_container(target_codec, target_container)
    force_upscale = cfg.get("force_upscale", False)

    upscale_tag = f" + Upscale {target_res}p" if force_upscale else ""
    default_video_label = f"Video ({target_res}p | {target_codec.upper()} | .{eff_container}{upscale_tag})"
    audio_fmt = cfg.get("audio_format", "mp3")
    audio_br = cfg.get("audio_bitrate", "320")
    default_audio_label = f"Audio ({audio_fmt.upper()} @ {audio_br}k)"

    format_options = [
        (default_video_label, "video_default", True, False, 1),
        ("Video (Pick Custom Resolution)", "video_custom", True, False, 2),
        (default_audio_label, "audio_default", True, False, 1),
        ("Audio (Original Stream / Best)", "audio_best", True, False, 2),
        (t("cancel"), "cancel", False, True)
    ]

    title_disp = (item.title[:50] + "…") if len(item.title) > 50 else item.title
    header = [
        f"Target : {BOLD_YELLOW}{title_disp}{NC}",
        f"Author : {DIM}{item.author}{NC}  |  Type: {BOLD_CYAN}{'PLAYLIST' if is_playlist else 'VIDEO'}{NC}"
    ]

    choice = select_menu_option("Download Format", format_options, header_info=header)
    if choice in ("cancel", None):
        clear_screen()
        return

    mode = "video"
    chosen_res = target_res

    if choice == "video_default":
        mode = "video"
        chosen_res = target_res
    elif choice == "video_custom":
        res_opts = [
            ("4320p (8K Ultra HD)", "4320", True, False),
            ("2160p (4K Ultra HD)", "2160", True, False),
            ("1440p (2K Quad HD)", "1440", True, False),
            ("1080p (Full HD)", "1080", True, False),
            ("720p  (HD Standard)", "720", True, False),
            ("480p  (SD)", "480", True, False),
            ("360p  (Low)", "360", True, False),
            (t("back_simple"), "back", False, True)
        ]
        chosen_res = select_menu_option("Select Resolution", res_opts)
        if chosen_res in ("back", None):
            clear_screen()
            return
        mode = "video"
    elif choice == "audio_default":
        mode = audio_fmt
    elif choice == "audio_best":
        mode = "best"

    # Banner display before download
    clear_screen()
    banner = "Downloading Playlist" if is_playlist else "Downloading YouTube Media"
    print(f"{BOLD_CYAN}── {BOLD_YELLOW}{banner}{BOLD_CYAN} ─────────────────────────────{NC}\n")
    print(f"  Title           : {BOLD_YELLOW}{item.title}{NC}")
    print(f"  Author          : {DIM}{item.author}{NC}")
    print(f"  Format Mode     : {BOLD_CYAN}{mode.upper()}{NC} ({chosen_res}p)" if mode == "video" else f"  Format Mode     : {BOLD_CYAN}{mode.upper()}{NC}")
    out_dir = get_download_path(platform="youtube")
    print(f"  Output Folder   : {BOLD_BLUE}{out_dir}{NC}")
    if FFMPEG_EXE:
        print(f"  FFmpeg Engine   : {DIM}{Path(FFMPEG_EXE).name}{NC}")
    print("-" * 60 + "\n")

    extractor = YouTubeExtractor()
    opts = {
        "mode": mode,
        "resolution": chosen_res,
        "is_playlist": is_playlist,
        "force_upscale": force_upscale,
    }

    success, files = extractor.download(item, opts)
    target_out = files[0].parent if files else out_dir
    render_download_result(success, files, target_out)


def run_youtube_view():
    """Main entry for YouTube Downloader category."""
    clear_screen()
    print(f"{BOLD_CYAN}── {BOLD_RED}YouTube Downloader{BOLD_CYAN} ─────────────────────────────{NC}")
    print(f"  {DIM}Paste any YouTube Video, Shorts, or Playlist link:{NC}\n")
    url = safe_input("  URL: ").strip()

    if not url:
        clear_screen()
        return

    extractor = YouTubeExtractor()
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
        print(f"\n  {BOLD_RED}✖ [{t('error')}]{NC} Could not retrieve video information.")
        print(f"\n  {DIM}[Enter] {t('back_simple')}{NC}")
        get_key()
        clear_screen()
        return

    run_youtube_download_flow(item)
