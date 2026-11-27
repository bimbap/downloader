#!/usr/bin/env python3
# =============================================================================
# downloader/src/main.py – Unified Downloader Entrypoint & CLI Dispatcher
# =============================================================================
import argparse
import os
import sys
from pathlib import Path

# Ensure src directory is in sys.path
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.console import (
    configure_windows_console,
    sanitize_terminal_text,
    BOLD_CYAN,
    BOLD_YELLOW,
    BOLD_GREEN,
    BOLD_RED,
    DIM,
    NC,
)
from core.config import ensure_dependencies, load_config, get_download_path
from core.file_manager import save_caption_file
from core.batch import parse_batch_input, validate_batch_urls, execute_batch_download
from extractors import get_extractor_for_url, detect_platform
from ui.views.main_menu import run_main_menu


def _build_cli_opts(args) -> dict:
    return {
        "mode": args.mode or ("audio" if args.audio_only else "video"),
        "resolution": args.resolution,
        "video_codec": args.codec,
        "video_container": args.container,
        "audio_format": args.audio_format,
        "audio_bitrate": args.audio_bitrate,
        "filename_style": args.style,
        "is_playlist": args.playlist,
        "force_upscale": args.force_upscale,
        "save_caption": args.save_caption,
        "output_dir": args.output,
    }


def run_cli_download(raw_url: str, args):
    """Executes a headless single-URL CLI download without interactive TUI."""
    url = raw_url.strip()
    extractor = get_extractor_for_url(url)
    if not extractor:
        print(f"\n{BOLD_RED}✖ [ERROR]{NC} Unsupported URL: {url}")
        print(f"Supported platforms: YouTube, X / Twitter, Instagram, Threads\n")
        sys.exit(1)

    is_valid, norm_url, reason = extractor.validate_url(url)
    if not is_valid:
        print(f"\n{BOLD_RED}✖ [ERROR]{NC} {reason}\n")
        sys.exit(1)

    print(f"\n{BOLD_CYAN}── Fetching metadata for:{NC} {norm_url}")
    item = extractor.fetch_metadata(norm_url)
    if not item:
        print(f"\n{BOLD_RED}✖ [ERROR]{NC} Could not retrieve media information.\n")
        sys.exit(1)

    print(f"  Platform  : {BOLD_CYAN}{item.platform.upper()}{NC}")
    print(f"  Title     : {BOLD_YELLOW}{sanitize_terminal_text(item.title)}{NC}")
    print(f"  Author    : {DIM}{sanitize_terminal_text(item.author)}{NC}")
    print(f"  Type      : {BOLD_GREEN}{item.media_type.upper()}{NC}")

    opts = _build_cli_opts(args)
    out_dir = get_download_path(args.output, platform=item.platform)
    print(f"  Output Dir: {DIM}{out_dir}{NC}\n")

    success, files = extractor.download(item, opts)
    if success:
        save_cap = args.save_caption if args.save_caption is not None else load_config().get("save_caption", True)
        if save_cap:
            cap_path = save_caption_file(item, files, fallback_dir=out_dir)
            if cap_path:
                print(f"  {BOLD_CYAN}📝 Caption saved:{NC} {cap_path.name}")
    if success and files:
        print(f"\n{BOLD_GREEN}✔ [SUCCESS]{NC} Downloaded {len(files)} file(s) successfully!")
        for f in files:
            print(f"  • {sanitize_terminal_text(f.name)}")
    elif success:
        print(f"\n{BOLD_GREEN}✔ [SUCCESS]{NC} Download completed successfully!")
    else:
        print(f"\n{BOLD_RED}✖ [FAILED]{NC} Download failed.\n")
        sys.exit(1)


def run_cli_batch(raw_urls: list[str], args):
    """Executes a headless batch CLI download for multiple URLs."""
    valid_targets, invalid_entries = validate_batch_urls(raw_urls)
    if invalid_entries:
        print(f"\n{BOLD_YELLOW}[!] Skipped {len(invalid_entries)} invalid/unsupported URL(s):{NC}")
        for u, reason in invalid_entries:
            print(f"  • {sanitize_terminal_text(u)}: {reason}")

    if not valid_targets:
        print(f"\n{BOLD_RED}✖ [ERROR]{NC} No valid URLs to download.\n")
        sys.exit(1)

    opts = _build_cli_opts(args)
    print(f"\n{BOLD_CYAN}── Starting Batch Download ({len(valid_targets)} URLs) ──{NC}")

    def on_start(idx: int, total: int, _ext, norm_url: str):
        print(f"\n{BOLD_CYAN}[{idx}/{total}]{NC} {sanitize_terminal_text(norm_url)}")

    summary = execute_batch_download(valid_targets, options=opts, on_item_start=on_start)
    ok_count = len(summary["succeeded"])
    fail_count = len(summary["failed"])

    print(f"\n{BOLD_CYAN}── Batch Summary ──{NC}")
    print(f"  {BOLD_GREEN}✔ Succeeded:{NC} {ok_count}/{summary['total']}")
    if fail_count:
        print(f"  {BOLD_RED}✖ Failed   :{NC} {fail_count}/{summary['total']}")
        for entry in summary["failed"]:
            print(f"    • {sanitize_terminal_text(entry['url'])} ({entry['reason']})")
        sys.exit(1)


def main():
    ensure_dependencies()
    configure_windows_console()

    parser = argparse.ArgumentParser(
        description="Universal Social Media Downloader (YouTube, X, Instagram, Threads)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch interactive TUI:
  python src/main.py

  # Download YouTube video at 1080p:
  python src/main.py "https://youtu.be/dQw4w9WgXcQ" -r 1080

  # Download X/Twitter post (video, gif, or photo gallery):
  python src/main.py "https://x.com/username/status/123456789"

  # Download Instagram Reel:
  python src/main.py "https://www.instagram.com/reel/C8..."

  # Download Threads video or photo:
  python src/main.py "https://www.threads.net/@user/post/C8..."
        """
    )
    parser.add_argument("urls", nargs="*", help="One or more media URLs to download (YouTube, X, Instagram, Threads)")
    parser.add_argument("-f", "--batch", dest="batch_file", help="Path to a .txt file containing URLs (one per line)")
    parser.add_argument("-m", "--mode", choices=["video", "audio", "mp3", "m4a", "opus", "wav", "best"], help="Download mode")
    parser.add_argument("-a", "--audio-only", action="store_true", help="Download audio only")
    parser.add_argument("-r", "--resolution", choices=["best", "max", "auto", "4320", "2160", "1440", "1080", "720", "480", "360"], help="Video quality")
    parser.add_argument("-c", "--codec", choices=["h264", "av1", "vp9", "auto"], help="Video codec")
    parser.add_argument("--container", choices=["auto", "mp4", "webm", "mkv"], help="Video container")
    parser.add_argument("--audio-format", choices=["mp3", "m4a", "opus", "wav", "best"], help="Audio format")
    parser.add_argument("-b", "--audio-bitrate", choices=["320", "256", "192", "128", "96"], help="Audio bitrate")
    parser.add_argument("-s", "--style", choices=["classic", "basic", "pretty", "nerdy"], help="Naming style")
    parser.add_argument("-p", "--playlist", action="store_true", help="Download entire playlist")
    parser.add_argument("-u", "--force-upscale", action="store_true", default=None, help="Force GPU Bicubic upscale")
    parser.add_argument("--no-force-upscale", dest="force_upscale", action="store_false", help="Disable upscaling")
    parser.add_argument("--caption", dest="save_caption", action="store_true", default=None, help="Save post caption as caption.txt")
    parser.add_argument("--no-caption", dest="save_caption", action="store_false", help="Do not save caption.txt")
    parser.add_argument("-o", "--output", help="Custom output directory")

    args = parser.parse_args()

    cli_urls: list[str] = []
    for u in args.urls:
        cli_urls.extend(parse_batch_input(u))
    if args.batch_file:
        cli_urls.extend(parse_batch_input(args.batch_file))
    cli_urls = list(dict.fromkeys(cli_urls))

    if len(cli_urls) > 1 or (args.batch_file and cli_urls):
        run_cli_batch(cli_urls, args)
    elif len(cli_urls) == 1:
        run_cli_download(cli_urls[0], args)
    elif args.batch_file:
        print(f"\n{BOLD_RED}✖ [ERROR]{NC} No valid URLs found in batch file: {args.batch_file}\n")
        sys.exit(1)
    else:
        run_main_menu()


if __name__ == "__main__":
    main()
