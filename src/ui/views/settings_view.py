# =============================================================================
# downloader/src/ui/views/settings_view.py – Settings & Preferences Hub
# =============================================================================
from pathlib import Path

from core.console import (
    BOLD_CYAN,
    BOLD_YELLOW,
    BOLD_GREEN,
    BOLD_RED,
    DIM,
    NC,
    clear_screen,
    safe_input,
    get_key,
)
from core.config import (
    load_config,
    save_config,
    resolve_video_container,
    get_download_path,
)
from ui.menu import select_menu_option


def handle_video_settings():
    curr_idx = 0
    while True:
        cfg = load_config()
        current_res = cfg.get("default_resolution", "1080")
        current_codec = cfg.get("video_codec", "h264")
        current_container = cfg.get("video_container", "auto")
        force_upscale = cfg.get("force_upscale", False)
        eff_container = resolve_video_container(current_codec, current_container)
        upscale_disp = f"{BOLD_YELLOW}ON (GPU/Bicubic){NC}" if force_upscale else f"{DIM}OFF (Native Only){NC}"

        header = [
            f"Quality: {BOLD_GREEN}{current_res}p{NC}  |  Codec: {BOLD_CYAN}{current_codec.upper()}{NC}  |  Container: {BOLD_YELLOW}.{eff_container}{NC}",
            f"Upscale: {BOLD_YELLOW if force_upscale else DIM}{'ON (Bicubic)' if force_upscale else 'OFF'}{NC}  |  {DIM}Auto upscale lower streams to target resolution via GPU/FFmpeg{NC}"
        ]

        options = [
            (f"{'Target Resolution':<34} [{current_res}p] ⚙", "resolution", True, False),
            (f"{'Preferred Video Codec':<34} [{current_codec.upper()}] ⚙", "codec", True, False),
            (f"{'Video Container':<34} [{current_container.upper()} -> .{eff_container}] ⚙", "container", True, False),
            (f"{'Force Upscale Resolution':<34} [{upscale_disp}]", "toggle_upscale", True, False),
            ("Back to Settings", "back", False, True)
        ]

        choice = select_menu_option("Video Settings 🎬", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            clear_screen()
            break

        if choice == "resolution":
            res_opts = [
                ("4320p (8K Ultra HD)", "4320", True, False),
                ("2160p (4K Ultra HD)", "2160", True, False),
                ("1440p (2K Quad HD)", "1440", True, False),
                ("1080p (Full HD)", "1080", True, False),
                ("720p  (HD Standard)", "720", True, False),
                ("480p  (SD Standard)", "480", True, False),
                ("Back", "back", False, True)
            ]
            r = select_menu_option("Select Target Resolution", res_opts)
            if r and r != "back":
                cfg["default_resolution"] = r
                save_config(cfg)
            curr_idx = 0

        elif choice == "codec":
            codec_opts = [
                ("H.264 (AVC) - Max Compatibility, up to 1080p", "h264", True, False),
                ("AV1 - Next-Gen Ultra Efficient, 4K & 8K", "av1", True, False),
                ("VP9 - Google Web Standard, 2K & 4K", "vp9", True, False),
                ("Auto - Best Available", "auto", True, False),
                ("Back", "back", False, True)
            ]
            c = select_menu_option("Select Preferred Codec", codec_opts)
            if c and c != "back":
                cfg["video_codec"] = c
                save_config(cfg)
            curr_idx = 1

        elif choice == "container":
            cnt_opts = [
                ("Auto (MP4 for H.264, WebM for VP9/AV1)", "auto", True, False),
                ("MP4  - Standard Universal Container", "mp4", True, False),
                ("MKV  - Matroska (High Flexibility)", "mkv", True, False),
                ("WebM - Open Web Media Container", "webm", True, False),
                ("Back", "back", False, True)
            ]
            cnt = select_menu_option("Select Video Container", cnt_opts)
            if cnt and cnt != "back":
                cfg["video_container"] = cnt
                save_config(cfg)
            curr_idx = 2

        elif choice == "toggle_upscale":
            cfg["force_upscale"] = not cfg.get("force_upscale", False)
            save_config(cfg)
            curr_idx = 3


def handle_audio_settings():
    curr_idx = 0
    while True:
        cfg = load_config()
        current_fmt = cfg.get("audio_format", "mp3")
        current_br = str(cfg.get("audio_bitrate", "320"))

        header = [
            f"Format : {BOLD_CYAN}{current_fmt.upper()}{NC}  |  Bitrate: {BOLD_YELLOW}{current_br} kbps{NC}"
        ]

        options = [
            (f"{'Audio Format':<34} [{current_fmt.upper()}] ⚙", "format", True, False),
            (f"{'Target Bitrate':<34} [{current_br}k] ⚙", "bitrate", True, False),
            ("Back to Settings", "back", False, True)
        ]

        choice = select_menu_option("Audio Settings 🎵", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            clear_screen()
            break

        if choice == "format":
            fmt_opts = [
                ("MP3  - MPEG Audio Layer III (Universal)", "mp3", True, False),
                ("M4A  - AAC Audio (Apple & High-Efficiency)", "m4a", True, False),
                ("Opus - High-Fidelity Web Standard", "opus", True, False),
                ("WAV  - Lossless Uncompressed PCM", "wav", True, False),
                ("Best - Keep Original Audio Stream", "best", True, False),
                ("Back", "back", False, True)
            ]
            f = select_menu_option("Select Audio Format", fmt_opts)
            if f and f != "back":
                cfg["audio_format"] = f
                save_config(cfg)
            curr_idx = 0

        elif choice == "bitrate":
            br_opts = [
                ("320 kbps (Maximum / Studio Quality)", "320", True, False),
                ("256 kbps (Very High Quality)", "256", True, False),
                ("192 kbps (Standard High Quality)", "192", True, False),
                ("128 kbps (Standard / Space Saver)", "128", True, False),
                ("Back", "back", False, True)
            ]
            b = select_menu_option("Select Bitrate", br_opts)
            if b and b != "back":
                cfg["audio_bitrate"] = b
                save_config(cfg)
            curr_idx = 1


def handle_storage_settings():
    curr_idx = 0
    while True:
        cfg = load_config()
        out_dir = cfg.get("download_dir", "downloads")
        org_platform = cfg.get("organize_by_platform", True)
        org_category = cfg.get("organize_by_category", True)

        header = [
            f"Path     : {BOLD_CYAN}{out_dir}{NC}",
            f"Platform : {BOLD_GREEN if org_platform else DIM}{'ON (youtube/, x/, etc.)' if org_platform else 'OFF'}{NC}  |  Format: {BOLD_YELLOW if org_category else DIM}{'ON (photo/, video/, audio/)' if org_category else 'OFF'}{NC}"
        ]

        options = [
            (f"{'Output Folder Path':<34} [{out_dir}] ⚙", "change_dir", True, False),
            (f"{'Organize by Platform':<34} [{'ON' if org_platform else 'OFF'}]", "toggle_org", True, False),
            (f"{'Organize by Media Category':<34} [{'ON' if org_category else 'OFF'}]", "toggle_cat", True, False),
            ("Back to Settings", "back", False, True)
        ]

        choice = select_menu_option("Storage & Folders 📁", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            clear_screen()
            break

        if choice == "change_dir":
            clear_screen()
            print(f"{BOLD_CYAN}Current Output Directory:{NC} {out_dir}\n")
            print(f"  {DIM}Enter relative (e.g. downloads) or absolute path (e.g. D:\\Media):{NC}")
            new_path = safe_input("  New Path: ").strip()
            if new_path:
                cfg["download_dir"] = new_path
                save_config(cfg)
            curr_idx = 0

        elif choice == "toggle_org":
            cfg["organize_by_platform"] = not cfg.get("organize_by_platform", True)
            save_config(cfg)
            curr_idx = 1

        elif choice == "toggle_cat":
            cfg["organize_by_category"] = not cfg.get("organize_by_category", True)
            save_config(cfg)
            curr_idx = 2


def run_settings_view():
    """Top-level Settings Menu."""
    curr_idx = 0
    while True:
        cfg = load_config()
        style = cfg.get("filename_style", "basic")
        res = cfg.get("default_resolution", "1080")
        codec = cfg.get("video_codec", "h264")
        afmt = cfg.get("audio_format", "mp3")
        upscale = cfg.get("force_upscale", False)

        header = [
            f"Video: {BOLD_GREEN}{res}p / {codec.upper()}{NC}{(' (Upscale: ON)' if upscale else '')}  |  Audio: {BOLD_CYAN}{afmt.upper()}{NC}  |  Naming: {BOLD_YELLOW}{style.upper()}{NC}"
        ]

        options = [
            (f"{'Video Settings 🎬':<36} [{res}p / {codec.upper()}] ⚙", "video", True, False),
            (f"{'Audio Settings 🎵':<36} [{afmt.upper()} @ {cfg.get('audio_bitrate', '320')}k] ⚙", "audio", True, False),
            (f"{'Filename Style 🏷':<36} [{style.upper()}] ⚙", "style", True, False),
            (f"{'Storage & Folders 📁':<36} ⚙", "storage", True, False),
            ("Return to Main Menu", "back", False, True)
        ]

        choice = select_menu_option("PENGATURAN / SETTINGS ⚙", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            clear_screen()
            break

        if choice == "video":
            handle_video_settings()
            curr_idx = 0
        elif choice == "audio":
            handle_audio_settings()
            curr_idx = 1
        elif choice == "style":
            style_opts = [
                ("Basic   - Title - Author.ext", "basic", True, False),
                ("Pretty  - Title - Author (platform).ext", "pretty", True, False),
                ("Nerdy   - Title - Author (platform, id).ext", "nerdy", True, False),
                ("Classic - platform_id_res.ext", "classic", True, False),
                ("Back", "back", False, True)
            ]
            st = select_menu_option("Select Filename Style", style_opts)
            if st and st != "back":
                cfg["filename_style"] = st
                save_config(cfg)
            curr_idx = 2
        elif choice == "storage":
            handle_storage_settings()
            curr_idx = 3
