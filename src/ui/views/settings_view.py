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
)
from core.config import (
    load_config,
    save_config,
    resolve_video_container,
)
from core.file_manager import clean_temp_files, reset_config
from core.i18n import t, get_current_language, set_current_language
from ui.menu import select_menu_option


def handle_video_settings():
    curr_idx = 0
    while True:
        cfg = load_config()
        current_res = cfg.get("default_resolution", "1080")
        current_codec = cfg.get("video_codec", "h264")
        current_container = cfg.get("video_container", "auto")
        force_upscale = cfg.get("force_upscale", False)
        disp_res = "Maksimal" if current_res in ("best", "max", "auto") else f"{current_res}p"
        eff_container = resolve_video_container(current_codec, current_container)
        upscale_disp = f"{BOLD_YELLOW}ON (GPU/Bicubic){NC}" if force_upscale else f"{DIM}OFF (Native Only){NC}"

        header = [
            f"Quality: {BOLD_GREEN}{disp_res}{NC}  |  Codec: {BOLD_CYAN}{current_codec.upper()}{NC}  |  Container: {BOLD_YELLOW}.{eff_container}{NC}",
            f"Upscale: {BOLD_YELLOW if force_upscale else DIM}{'ON (Bicubic)' if force_upscale else 'OFF'}{NC}  |  {DIM}Auto upscale lower streams to target resolution via GPU/FFmpeg{NC}"
        ]

        options = [
            (f"{'Target Resolution':<34} [{disp_res}]", "resolution", True, False),
            (f"{'Preferred Video Codec':<34} [{current_codec.upper()}]", "codec", True, False),
            (f"{'Video Container':<34} [{current_container.upper()} -> .{eff_container}]", "container", True, False),
            (f"{'Force Upscale Resolution':<34} [{upscale_disp}]", "toggle_upscale", True, False),
            (t("back_simple"), "back", False, True)
        ]

        choice = select_menu_option(t("setting_video"), options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            clear_screen()
            break

        if choice == "resolution":
            res_opts = [
                ("Auto   (Kualitas Maksimal / Best - 4K/8K)", "best", True, False),
                ("4320p  (8K Ultra HD)", "4320", True, False),
                ("2160p  (4K Ultra HD)", "2160", True, False),
                ("1440p  (2K Quad HD)", "1440", True, False),
                ("1080p  (Full HD Standard)", "1080", True, False),
                ("720p   (HD Standard)", "720", True, False),
                ("480p   (SD Standard)", "480", True, False),
                (t("back_simple"), "back", False, True)
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
                (t("back_simple"), "back", False, True)
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
                (t("back_simple"), "back", False, True)
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
        embed_thumb = cfg.get("embed_thumbnail", True)
        crop_sq = cfg.get("crop_square_thumbnail", True)
        embed_meta = cfg.get("embed_metadata", True)

        thumb_disp = f"{BOLD_GREEN}ON{NC}" if embed_thumb else f"{DIM}OFF{NC}"
        crop_disp = f"{BOLD_GREEN}ON{NC}" if crop_sq else f"{DIM}OFF{NC}"
        meta_disp = f"{BOLD_GREEN}ON{NC}" if embed_meta else f"{DIM}OFF{NC}"

        header = [
            f"Format : {BOLD_CYAN}{current_fmt.upper()}{NC}  |  Bitrate: {BOLD_YELLOW}{current_br} kbps{NC}  |  Cover Art: {thumb_disp}  |  Tags: {meta_disp}",
            f"{DIM}Auto embed 1:1 album art (Topic/Music) & artist/album tags into audio files{NC}"
        ]

        options = [
            (f"{'Audio Format':<34} [{current_fmt.upper()}]", "format", True, False),
            (f"{'Target Bitrate':<34} [{current_br}k]", "bitrate", True, False),
            (f"{'Embed Album Cover (Cover Art)':<34} [{'ON' if embed_thumb else 'OFF'}]", "toggle_thumb", True, False),
            (f"{'Crop Square Cover (Topic/Music)':<34} [{'ON' if crop_sq else 'OFF'}]", "toggle_crop", True, False),
            (f"{'Embed Song Metadata (ID3 Tags)':<34} [{'ON' if embed_meta else 'OFF'}]", "toggle_meta", True, False),
            (t("back_simple"), "back", False, True)
        ]

        choice = select_menu_option(t("setting_audio"), options, current_idx=curr_idx, header_info=header)
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
                (t("back_simple"), "back", False, True)
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
                (t("back_simple"), "back", False, True)
            ]
            b = select_menu_option("Select Bitrate", br_opts)
            if b and b != "back":
                cfg["audio_bitrate"] = b
                save_config(cfg)
            curr_idx = 1

        elif choice == "toggle_thumb":
            cfg["embed_thumbnail"] = not cfg.get("embed_thumbnail", True)
            save_config(cfg)
            curr_idx = 2

        elif choice == "toggle_crop":
            cfg["crop_square_thumbnail"] = not cfg.get("crop_square_thumbnail", True)
            save_config(cfg)
            curr_idx = 3

        elif choice == "toggle_meta":
            cfg["embed_metadata"] = not cfg.get("embed_metadata", True)
            save_config(cfg)
            curr_idx = 4


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
            (f"{'Output Folder Path':<34} [{out_dir}]", "change_dir", True, False),
            (f"{'Organize by Platform':<34} [{'ON' if org_platform else 'OFF'}]", "toggle_org", True, False),
            (f"{'Organize by Media Category':<34} [{'ON' if org_category else 'OFF'}]", "toggle_cat", True, False),
            (t("back_simple"), "back", False, True)
        ]

        choice = select_menu_option(t("setting_storage"), options, current_idx=curr_idx, header_info=header)
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


def handle_language_settings():
    """Select UI display language (Indonesian or English)."""
    curr = get_current_language()
    curr_idx = 0 if curr == "id" else 1

    lang_opts = [
        ("Bahasa Indonesia (Indonesian)", "id", True, False),
        ("English (International)", "en", True, False),
        (t("back_simple"), "back", False, True),
    ]

    header = [
        f"Active: {BOLD_GREEN}{'Bahasa Indonesia' if curr == 'id' else 'English'}{NC}",
        f"{DIM}Select your preferred application language / Pilih bahasa tampilan aplikasi.{NC}"
    ]

    choice = select_menu_option(t("lang_select_title"), lang_opts, current_idx=curr_idx, header_info=header)
    if choice and choice != "back":
        set_current_language(choice)


def handle_cookie_settings():
    """Select browser to automatically import authentication cookies for age-restricted/login posts."""
    cfg = load_config()
    current_b = (cfg.get("browser_cookies") or "none").lower()

    header = [
        t("cookies_desc"),
        f"Active: {BOLD_CYAN}{current_b.upper()}{NC}"
    ]

    cookie_opts = [
        ("None (Default / No Cookies)", "none", True, False),
        ("Google Chrome", "chrome", True, False),
        ("Mozilla Firefox", "firefox", True, False),
        ("Microsoft Edge", "edge", True, False),
        ("Brave Browser", "brave", True, False),
        ("Opera / Opera GX", "opera", True, False),
        ("Vivaldi", "vivaldi", True, False),
        (t("back_simple"), "back", False, True),
    ]

    idx = 0
    for i, (_, val, _, _) in enumerate(cookie_opts):
        if val == current_b:
            idx = i
            break

    b = select_menu_option(t("cookies_select_title"), cookie_opts, current_idx=idx, header_info=header)
    if b and b != "back":
        cfg["browser_cookies"] = b
        save_config(cfg)


def handle_clean_cache():
    """Purge temporary and broken partial files."""
    clear_screen()
    cleaned_count, freed_bytes = clean_temp_files()
    freed_mb = freed_bytes / (1024 * 1024)

    print(f"\n  {BOLD_CYAN}── {t('setting_clean')} ──────────────────────{NC}\n")
    if cleaned_count > 0:
        print(f"  {BOLD_GREEN}{t('cache_cleaned', count=cleaned_count, size=freed_mb)}{NC}\n")
    else:
        print(f"  {DIM}{t('cache_already_clean')}{NC}\n")
    safe_input(f"  {t('back_simple')} (Press Enter to continue)...")


def handle_reset_defaults():
    """Reverts configuration back to default values."""
    clear_screen()
    print(f"\n  {BOLD_RED}── {t('reset_confirm_title')} ──────────────────────{NC}\n")
    print(f"  {t('reset_confirm_msg')}\n")
    ans = safe_input(f"  {BOLD_YELLOW}{t('confirm_delete_prompt')}{NC} ").strip().upper()
    if ans in ("YES", "YA", "Y"):
        reset_config()
        print(f"\n  {BOLD_GREEN}{t('reset_success')}{NC}\n")
        safe_input(f"  {t('back_simple')} (Press Enter to continue)...")


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
        lang = cfg.get("language", "id")
        cookies = cfg.get("browser_cookies", "none")

        lang_disp = "ID" if lang == "id" else "EN"
        cookies_disp = cookies.upper() if cookies != "none" else "OFF"

        embed_thumb = cfg.get("embed_thumbnail", True)
        thumb_tag = " (Cover: ON)" if embed_thumb else ""

        header = [
            f"Video: {BOLD_GREEN}{res}p / {codec.upper()}{NC}{(' (Upscale: ON)' if upscale else '')}  |  Audio: {BOLD_CYAN}{afmt.upper()}{NC}{thumb_tag}  |  Naming: {BOLD_YELLOW}{style.upper()}{NC}",
            f"Lang : {BOLD_CYAN}{lang_disp}{NC}  |  Cookies: {BOLD_YELLOW}{cookies_disp}{NC}"
        ]

        options = [
            (f"{t('setting_video'):<38} [{res}p / {codec.upper()}]", "video", True, False),
            (f"{t('setting_audio'):<38} [{afmt.upper()} @ {cfg.get('audio_bitrate', '320')}k{' + Cover' if embed_thumb else ''}]", "audio", True, False),
            (f"{t('setting_style'):<38} [{style.upper()}]", "style", True, False),
            (f"{t('setting_storage'):<38}", "storage", True, False),
            (f"{t('setting_language'):<38} [{lang_disp}]", "language", True, False),
            (f"{t('setting_cookies'):<38} [{cookies_disp}]", "cookies", True, False),
            (f"{t('setting_clean'):<38}", "clean", True, False),
            (f"{t('setting_reset'):<38}", "reset", True, False),
            (t("back"), "back", False, True)
        ]

        choice = select_menu_option(t("settings_title"), options, current_idx=curr_idx, header_info=header)
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
                (t("back_simple"), "back", False, True)
            ]
            st = select_menu_option("Select Filename Style", style_opts)
            if st and st != "back":
                cfg["filename_style"] = st
                save_config(cfg)
            curr_idx = 2
        elif choice == "storage":
            handle_storage_settings()
            curr_idx = 3
        elif choice == "language":
            handle_language_settings()
            curr_idx = 4
        elif choice == "cookies":
            handle_cookie_settings()
            curr_idx = 5
        elif choice == "clean":
            handle_clean_cache()
            curr_idx = 6
        elif choice == "reset":
            handle_reset_defaults()
            curr_idx = 7
