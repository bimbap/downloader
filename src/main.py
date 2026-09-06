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
    BOLD_CYAN,
    BOLD_YELLOW,
    BOLD_GREEN,
    BOLD_RED,
    DIM,
    NC,
)
from core.config import ensure_dependencies, load_config, get_download_path
from extractors import get_extractor_for_url, detect_platform
from ui.views.main_menu import run_main_menu


def run_cli_download(args):
    """Executes a headless CLI download without interactive TUI."""
    url = args.url.strip()
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
    print(f"  Title     : {BOLD_YELLOW}{item.title}{NC}")
    print(f"  Author    : {DIM}{item.author}{NC}")
    print(f"  Type      : {BOLD_GREEN}{item.media_type.upper()}{NC}")

    opts = {
        "mode": args.mode or ("audio" if args.audio_only else "video"),
        "resolution": args.resolution,
        "video_codec": args.codec,
        "video_container": args.container,
        "audio_format": args.audio_format,
        "audio_bitrate": args.audio_bitrate,
        "filename_style": args.style,
        "is_playlist": args.playlist,
        "force_upscale": args.force_upscale,
        "output_dir": args.output,
    }

    out_dir = get_download_path(args.output, platform=item.platform)
    print(f"  Output Dir: {DIM}{out_dir}{NC}\n")

    success, files = extractor.download(item, opts)
    if success and files:
        print(f"\n{BOLD_GREEN}✔ [SUCCESS]{NC} Downloaded {len(files)} file(s) successfully!")
        for f in files:
            print(f"  • {f.name}")
    elif success:
        print(f"\n{BOLD_GREEN}✔ [SUCCESS]{NC} Download completed successfully!")
    else:
        print(f"\n{BOLD_RED}✖ [FAILED]{NC} Download failed.\n")
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
    parser.add_argument("url", nargs="?", help="Media URL to download (YouTube, X, Instagram, Threads)")
    parser.add_argument("-m", "--mode", choices=["video", "audio", "mp3", "m4a", "opus", "wav", "best"], help="Download mode")
    parser.add_argument("-a", "--audio-only", action="store_true", help="Download audio only")
    parser.add_argument("-r", "--resolution", choices=["4320", "2160", "1440", "1080", "720", "480", "360"], help="Video quality")
    parser.add_argument("-c", "--codec", choices=["h264", "av1", "vp9", "auto"], help="Video codec")
    parser.add_argument("--container", choices=["auto", "mp4", "webm", "mkv"], help="Video container")
    parser.add_argument("--audio-format", choices=["mp3", "m4a", "opus", "wav", "best"], help="Audio format")
    parser.add_argument("-b", "--audio-bitrate", choices=["320", "256", "192", "128", "96"], help="Audio bitrate")
    parser.add_argument("-s", "--style", choices=["classic", "basic", "pretty", "nerdy"], help="Naming style")
    parser.add_argument("-p", "--playlist", action="store_true", help="Download entire playlist")
    parser.add_argument("-u", "--force-upscale", action="store_true", default=None, help="Force GPU Bicubic upscale")
    parser.add_argument("--no-force-upscale", dest="force_upscale", action="store_false", help="Disable upscaling")
    parser.add_argument("-o", "--output", help="Custom output directory")

    args = parser.parse_args()

    if args.url:
        run_cli_download(args)
    else:
        run_main_menu()


if __name__ == "__main__":
    main()
