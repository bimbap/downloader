# =============================================================================
# downloader/src/ui/views/main_menu.py – Main Navigation Hub
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
)
from core.config import load_config
from ui.menu import select_menu_option
from ui.views.smart_download import run_smart_download
from ui.views.youtube_view import run_youtube_view
from ui.views.social_view import (
    run_twitter_view,
    run_instagram_view,
    run_threads_view,
)
from ui.views.settings_view import run_settings_view
from ui.views.manager_view import run_manager_view


def run_main_menu():
    """Main application navigation loop."""
    curr_idx = 0
    while True:
        cfg = load_config()
        res = cfg.get("default_resolution", "1080")
        codec = cfg.get("video_codec", "h264")
        afmt = cfg.get("audio_format", "mp3")
        upscale = cfg.get("force_upscale", False)

        header = [
            f"Platforms: {BOLD_RED}YouTube{NC} • {BOLD_CYAN}X / Twitter{NC} • {BOLD_MAGENTA}Instagram{NC} • {BOLD_YELLOW}Threads{NC}",
            f"Quality  : {BOLD_GREEN}{res}p ({codec.upper()}){NC}{(' (Upscale: ON)' if upscale else '')}  |  Audio: {BOLD_CYAN}{afmt.upper()}{NC}"
        ]

        options = [
            ("⚡ Smart Download (Paste Any Social Link)", "smart", True, False),
            ("🔴 YouTube Downloader (Video, Audio, Playlist)", "youtube", True, False),
            ("🐦 X / Twitter Downloader (Video, GIF, Photos)", "twitter", True, False),
            ("📷 Instagram Downloader (Reels, Videos, Photos)", "instagram", True, False),
            ("🧵 Threads Downloader (Video, Photos)", "threads", True, False),
            ("📁 Manage Downloaded Media", "manager", True, True),
            ("⚙ Settings & Preferences", "settings", True, False),
            ("Exit Downloader", "exit", False, True)
        ]

        choice = select_menu_option("UNIVERSAL MEDIA DOWNLOADER 🚀", options, current_idx=curr_idx, header_info=header)
        if choice in ("exit", "back", None):
            clear_screen()
            print(f"\n  {BOLD_CYAN}Thank you for using Downloader. See you! 👋{NC}\n")
            break

        if choice == "smart":
            run_smart_download()
            curr_idx = 0
        elif choice == "youtube":
            run_youtube_view()
            curr_idx = 1
        elif choice == "twitter":
            run_twitter_view()
            curr_idx = 2
        elif choice == "instagram":
            run_instagram_view()
            curr_idx = 3
        elif choice == "threads":
            run_threads_view()
            curr_idx = 4
        elif choice == "manager":
            run_manager_view()
            curr_idx = 5
        elif choice == "settings":
            run_settings_view()
            curr_idx = 6
