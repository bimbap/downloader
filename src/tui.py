#!/usr/bin/env python3
# =============================================================================
# yt-downloader/src/tui.py – Interactive Terminal UI for YouTube Downloader
# =============================================================================
import os
import sys
import json
import re
import subprocess
import shutil
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# Ensure src directory is in path
SRC_DIR = Path(__file__).resolve().parent
BASE_DIR = SRC_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Force UTF-8 encoding on Windows to prevent cp1252 UnicodeEncodeError
for stream in (sys.stdout, sys.stderr, sys.stdin):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from config_helper import (
    load_config,
    save_config,
    get_download_path,
    get_outtmpl,
    resolve_video_container,
    get_video_format_selector,
    ensure_dependencies,
    validate_youtube_url,
    get_media_title,
)

ensure_dependencies()

# ANSI Color Definitions
CYAN = "\033[36m"
BOLD_CYAN = "\033[1;36m"
YELLOW = "\033[33m"
BOLD_YELLOW = "\033[1;33m"
GREEN = "\033[32m"
BOLD_GREEN = "\033[1;32m"
RED = "\033[31m"
BOLD_RED = "\033[1;31m"
PURPLE = "\033[35m"
BOLD_PURPLE = "\033[1;35m"
MAGENTA = "\033[35m"
BOLD_MAGENTA = "\033[1;35m"
BLUE = "\033[34m"
BOLD_BLUE = "\033[1;34m"
DIM = "\033[2m"
BOLD = "\033[1m"
NC = "\033[0m"
CLEAR_LINE = "\033[K"

if os.name == 'nt':
    os.system('')  # Enable VT100 ANSI mode on Windows console

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = None

try:
    from downloader import FFmpegUpscalePP
except ImportError:
    FFmpegUpscalePP = None


def get_key():
    """Cross-platform zero-lag raw key reader."""
    if os.name == 'nt':
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b'\x00', b'\xe0'):
            ch2 = msvcrt.getch()
            if ch2 == b'H': return 'UP'
            if ch2 == b'P': return 'DOWN'
            if ch2 == b'K': return 'LEFT'
            if ch2 == b'M': return 'RIGHT'
        if ch in (b'\r', b'\n'): return 'ENTER'
        if ch == b' ': return 'SPACE'
        if ch in (b'\x08', b'\x7f'): return 'BACKSPACE'
        if ch in (b'q', b'Q'): return 'Q'
        if ch in (b'o', b'O'): return 'O'
        if ch == b'\x1b': return 'ESC'
        try:
            return ch.decode('utf-8')
        except Exception:
            return ''
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                import select
                r, _, _ = select.select([sys.stdin], [], [], 0.05)
                if r:
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        ch3 = sys.stdin.read(1)
                        if ch3 == 'A': return 'UP'
                        if ch3 == 'B': return 'DOWN'
                        if ch3 == 'C': return 'RIGHT'
                        if ch3 == 'D': return 'LEFT'
                return 'ESC'
            if ch in ('\r', '\n'): return 'ENTER'
            if ch == ' ': return 'SPACE'
            if ch in ('\x08', '\x7f'): return 'BACKSPACE'
            if ch in ('q', 'Q'): return 'Q'
            if ch in ('o', 'O'): return 'O'
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def clear_screen():
    # Pure ANSI clear: move home, clear visible screen, clear entire scrollback
    sys.stdout.write("\033[H\033[2J\033[3J")
    sys.stdout.flush()


def select_menu_option(title, options, current_idx=0, header_info=None, clear_on_start=True):
    """
    Interactive TUI menu navigator (arrow keys, 1-N digits, Enter/Space, q/ESC to back).
    options: list of tuples (label, value, is_numbered, separator_before, [optional_custom_num])
    Includes dynamic sliding-window pagination to prevent terminal viewport overflow/scrolling.
    Supports non-selectable section headers (value="header").
    """
    if clear_on_start:
        clear_screen()

    first_selectable = next((i for i, opt in enumerate(options) if opt[1] != "header"), 0)
    last_selectable = max((i for i, opt in enumerate(options) if opt[1] != "header"), default=0)

    selected_idx = current_idx if (0 <= current_idx < len(options)) else first_selectable
    if 0 <= selected_idx < len(options) and options[selected_idx][1] == "header":
        selected_idx = first_selectable

    scroll_offset = 0
    sys.stdout.write("\033[?25l")

    try:
        while True:
            term_cols, term_rows = shutil.get_terminal_size((80, 24))

            # Pre-compute numbering map for each option
            numbered_indices = {}
            n_count = 1
            has_custom_nums = False
            for i, opt in enumerate(options):
                val = opt[1]
                if val == "header":
                    continue
                is_n = opt[2] if len(opt) > 2 else (val not in ("back", "exit"))
                if is_n:
                    numbered_indices[i] = n_count
                    n_count += 1
                if len(opt) > 4 and opt[4] is not None:
                    has_custom_nums = True
            total_num_items = n_count - 1

            # Determine fixed header lines count
            header_count = 2  # Title + nav hint
            if header_info:
                header_count += len(header_info) + 1  # info lines + gap
            else:
                header_count += 1  # gap

            def calc_lines(start_i, end_i):
                used = header_count
                if start_i > 0:
                    used += 1  # Above indicator
                if end_i < len(options):
                    used += 1  # Below indicator
                for i in range(start_i, end_i):
                    used += 1
                    if (options[i][3] if len(options[i]) > 3 else False) or options[i][1] in ("back", "exit"):
                        if i > start_i:
                            used += 1
                return used

            max_allowed_lines = max(5, term_rows - 1)

            # Adjust scroll_offset: if at or near top, always keep index 0 in view
            if selected_idx <= first_selectable:
                scroll_offset = 0
            else:
                eff_min = selected_idx
                if selected_idx > 0 and options[selected_idx - 1][1] == "header":
                    eff_min = selected_idx - 1

                if eff_min < scroll_offset:
                    scroll_offset = eff_min

            # Ensure selected_idx is in the visible window
            while True:
                test_end = scroll_offset
                while test_end < len(options) and calc_lines(scroll_offset, test_end + 1) <= max_allowed_lines:
                    test_end += 1
                if selected_idx < test_end or scroll_offset >= selected_idx:
                    visible_end = test_end
                    break
                scroll_offset += 1

            visible_end = max(scroll_offset + 1, min(len(options), visible_end))

            # Build lines
            lines = []
            pad = max(2, min(54, term_cols - 6) - len(title))
            lines.append(f"{BOLD_CYAN}── {BOLD_YELLOW}{title}{BOLD_CYAN} " + ("─" * pad) + f"{NC}")

            if has_custom_nums:
                num_hint = "   [1-3] Video   [1-2] Audio"
            elif total_num_items > 1:
                num_hint = f"   [1-{total_num_items}] Number"
            elif total_num_items == 1:
                num_hint = "   [1] Number"
            else:
                num_hint = ""

            pos_hint = f"   [{selected_idx + 1}/{len(options)}]" if (scroll_offset > 0 or visible_end < len(options)) else ""
            lines.append(f"{DIM}   [↑/↓] Navigate{num_hint}{pos_hint}   [Enter] Select   [q] Back{NC}")

            if header_info:
                for line in header_info:
                    lines.append(f"  {line}")
                lines.append("")
            else:
                lines.append("")

            # Scroll indicator: Above
            if scroll_offset > 0:
                lines.append(f"{DIM}   ▲ ... {scroll_offset} more item{'s' if scroll_offset != 1 else ''} above (scroll ↑){NC}")

            for idx in range(scroll_offset, visible_end):
                item = options[idx]
                label = item[0]
                val = item[1]
                is_num = idx in numbered_indices
                num_counter = item[4] if (len(item) > 4 and item[4] is not None) else numbered_indices.get(idx, 1)
                sep = item[3] if len(item) > 3 else False

                if (sep or val in ("back", "exit")) and idx > scroll_offset:
                    if lines and lines[-1] != "":
                        lines.append("")

                if val == "header":
                    lines.append(f"  {label}")
                elif idx == selected_idx:
                    sel_label = label if "\033[" in label else f"{BOLD_GREEN}{label}{NC}"
                    if is_num:
                        lines.append(f"  {BOLD}▸ {num_counter}. {sel_label}{NC}")
                    else:
                        lines.append(f"  {BOLD}▸ {sel_label}{NC}")
                else:
                    if is_num:
                        lines.append(f"    {num_counter}. {label}")
                    else:
                        lines.append(f"    {label}")

            # Scroll indicator: Below
            remaining_below = len(options) - visible_end
            if remaining_below > 0:
                lines.append(f"{DIM}   ▼ ... {remaining_below} more item{'s' if remaining_below != 1 else ''} below (scroll ↓){NC}")

            # In-place redraw: Move cursor to home and clear each line
            buf = "\033[H"
            for idx, ln in enumerate(lines):
                if idx < len(lines) - 1:
                    buf += ln + CLEAR_LINE + "\n"
                else:
                    buf += ln + CLEAR_LINE
            buf += "\033[J"
            sys.stdout.write(buf)
            sys.stdout.flush()

            k = get_key()

            if k in ("Q", "ESC"):
                return "back"
            elif k == "UP":
                if selected_idx == first_selectable:
                    if scroll_offset > 0:
                        scroll_offset = 0
                    else:
                        selected_idx = last_selectable
                else:
                    new_idx = selected_idx - 1
                    while new_idx >= 0 and options[new_idx][1] == "header":
                        new_idx -= 1
                    if new_idx < 0:
                        selected_idx = last_selectable
                    else:
                        selected_idx = new_idx
            elif k == "DOWN":
                if selected_idx == last_selectable:
                    selected_idx = first_selectable
                    scroll_offset = 0
                else:
                    new_idx = selected_idx + 1
                    while new_idx < len(options) and options[new_idx][1] == "header":
                        new_idx += 1
                    if new_idx >= len(options):
                        selected_idx = first_selectable
                        scroll_offset = 0
                    else:
                        selected_idx = new_idx
            elif k in ("ENTER", "SPACE"):
                if 0 <= selected_idx < len(options) and options[selected_idx][1] != "header":
                    return options[selected_idx][1]
            elif k.isdigit() and int(k) > 0:
                v_num = int(k)
                curr_header_idx = None
                for i in range(selected_idx, -1, -1):
                    if options[i][1] == "header":
                        curr_header_idx = i
                        break

                candidates = [
                    i for i, opt in enumerate(options)
                    if len(opt) > 4 and opt[4] == v_num
                ]
                matched_idx = None
                if candidates:
                    if curr_header_idx is not None:
                        same_section = [c for c in candidates if c > curr_header_idx]
                        if same_section:
                            matched_idx = same_section[0]
                    if matched_idx is None:
                        matched_idx = candidates[0]
                if matched_idx is not None:
                    return options[matched_idx][1]

                for idx, num_c in numbered_indices.items():
                    if num_c == v_num:
                        return options[idx][1]
    finally:
        sys.stdout.write("\033[?25h")



_current_download_title = None
_current_stream_type = None


def progress_hook(d):
    """Visual ANSI progress bar with safe type casting and multi-stream tracking."""
    global _current_download_title, _current_stream_type
    try:
        if d['status'] == 'downloading':
            info = d.get('info_dict', {})
            title = info.get('title')
            vcodec = info.get('vcodec')
            acodec = info.get('acodec')

            is_video_stream = bool(vcodec and vcodec != 'none' and (not acodec or acodec == 'none'))
            is_audio_stream = bool(acodec and acodec != 'none' and (not vcodec or vcodec == 'none'))
            stream_label = "video" if is_video_stream else ("audio" if is_audio_stream else "media")

            if title and (title != _current_download_title or stream_label != _current_stream_type):
                is_new_item = (title != _current_download_title)
                _current_download_title = title
                _current_stream_type = stream_label

                idx = info.get('playlist_index')
                count = info.get('n_entries') or info.get('playlist_count')
                prefix = f"[{idx}/{count}] " if idx and count else ""

                if is_new_item:
                    print(f"\n  {BOLD_CYAN}▶ {prefix}Downloading:{NC} {title}")
                    if is_video_stream:
                        res = info.get('resolution') or (f"{info.get('height')}p" if info.get('height') else "HD")
                        print(f"    {DIM}↳ Video Stream ({res})...{NC}")
                elif is_audio_stream:
                    print(f"\n    {DIM}↳ Audio Stream (Source soundtrack)...{NC}")

            total = float(d.get('total_bytes') or d.get('total_bytes_estimate') or 0)
            downloaded = float(d.get('downloaded_bytes') or 0)
            speed = float(d.get('speed') or 0)

            eta_raw = d.get('eta')
            if eta_raw is not None:
                try:
                    eta_sec = int(float(eta_raw))
                    eta_str = f"{eta_sec // 60:02d}:{eta_sec % 60:02d}" if eta_sec >= 60 else f"{eta_sec}s"
                except Exception:
                    eta_str = f"{eta_raw}s"
            else:
                eta_str = "--s"

            bar_len = 24
            if total > 0:
                percent = min(100.0, max(0.0, (downloaded / total) * 100))
                filled = max(0, min(bar_len, int(bar_len * (downloaded / total))))
                bar = f"{BOLD_GREEN}{'█' * filled}{NC}{DIM}{'░' * (bar_len - filled)}{NC}"
                total_mb = total / (1024 * 1024)
                downloaded_mb = downloaded / (1024 * 1024)
                speed_kb = speed / 1024
                speed_str = f"{speed_kb / 1024:4.1f} MB/s" if speed_kb >= 1024 else f"{speed_kb:4.0f} KB/s"
                sys.stdout.write(
                    f"\r  [{bar}] {BOLD_CYAN}{percent:5.1f}%{NC} | {downloaded_mb:5.1f}/{total_mb:5.1f} MB | {BOLD_YELLOW}{speed_str}{NC} | ETA: {eta_str:<5} {CLEAR_LINE}"
                )
                sys.stdout.flush()
            else:
                downloaded_mb = downloaded / (1024 * 1024)
                speed_kb = speed / 1024
                speed_str = f"{speed_kb / 1024:4.1f} MB/s" if speed_kb >= 1024 else f"{speed_kb:4.0f} KB/s"
                sys.stdout.write(
                    f"\r  [Downloading] {downloaded_mb:5.1f} MB | {BOLD_YELLOW}{speed_str}{NC} | ETA: {eta_str:<5} {CLEAR_LINE}"
                )
                sys.stdout.flush()
        elif d['status'] == 'finished':
            info = d.get('info_dict', {})
            vcodec = info.get('vcodec')
            acodec = info.get('acodec')
            is_video_stream = bool(vcodec and vcodec != 'none' and (not acodec or acodec == 'none'))
            if is_video_stream:
                print(f"\n    {BOLD_GREEN}✔ Video stream downloaded.{NC}")
            else:
                print(f"\n    {BOLD_YELLOW}⚙ Merging & processing with FFmpeg...{NC}")
    except Exception:
        pass


def execute_download(
    url: str,
    mode: str,
    resolution: str | None = None,
    is_playlist: bool = False,
    audio_format: str | None = None,
    audio_bitrate: str | None = None,
    video_codec: str | None = None,
    video_container: str | None = None,
    media_title: str | None = None,
    playlist_items: list[str] | None = None,
):
    global _current_download_title, _current_stream_type
    _current_download_title = None
    _current_stream_type = None

    cfg = load_config()
    style = cfg.get("filename_style", "basic")
    out_dir = get_download_path(cfg.get("download_dir"))

    # Determine audio settings if downloading audio
    target_audio_fmt = audio_format or cfg.get("audio_format", "mp3")
    target_audio_br = audio_bitrate or str(cfg.get("audio_bitrate", "320"))

    # Determine video settings if downloading video
    target_video_codec = video_codec or cfg.get("video_codec", "h264")
    target_video_container = video_container or cfg.get("video_container", "auto")
    effective_container = resolve_video_container(target_video_codec, target_video_container)

    format_display = mode.upper()
    is_upscale = cfg.get("force_upscale", False)
    if mode == "video":
        res_label = f"{resolution}p" if resolution else "Best Quality"
        upscale_note = f" | Upscale: ON ({resolution}p)" if (is_upscale and resolution) else ""
        format_display = f"VIDEO ({res_label} | {target_video_codec.upper()} | {effective_container.upper()}{upscale_note})"
    elif mode in ("audio", "mp3", "m4a", "opus", "wav", "best"):
        format_display = f"AUDIO ({target_audio_fmt.upper()} @ {target_audio_br}k)" if target_audio_fmt != "best" else "AUDIO (ORIGINAL STREAM)"

    clear_screen()
    banner_name = "Downloading Playlist with yt-dlp" if is_playlist else "Downloading Media with yt-dlp"
    print(f"{BOLD_CYAN}============================================================{NC}")
    print(f"{BOLD_YELLOW}{banner_name}{NC}")
    print(f"{BOLD_CYAN}============================================================{NC}\n")

    if is_playlist:
        pl_name = media_title or "YouTube Playlist"
        item_count_str = f" ({len(playlist_items)} Videos)" if playlist_items else ""
        print(f"  Playlist Name   : {BOLD_YELLOW}{pl_name}{NC}{item_count_str}")
        print(f"  Target URL      : {BOLD_GREEN}{url}{NC}")
        print(f"  Download Format : {BOLD_CYAN}{format_display}{NC}")
        print(f"  Filename Style  : {BOLD_MAGENTA}{style.upper()}{NC}")
        print(f"  Output Folder   : {BOLD_BLUE}{out_dir}{NC}")
        if FFMPEG_EXE:
            print(f"  FFmpeg Engine   : {DIM}{Path(FFMPEG_EXE).name}{NC}")
        if playlist_items:
            print(f"\n  {BOLD_CYAN}Playlist Items ({len(playlist_items)}):{NC}")
            max_show = 6
            for i, itm in enumerate(playlist_items[:max_show], 1):
                disp_itm = (itm[:60] + "…") if len(itm) > 60 else itm
                print(f"    {DIM}{i:2d}.{NC} {disp_itm}")
            if len(playlist_items) > max_show:
                print(f"    {DIM}... and {len(playlist_items) - max_show} more videos{NC}")
    else:
        if media_title:
            print(f"  Media Title     : {BOLD_YELLOW}{media_title}{NC}")
        print(f"  Target URL      : {BOLD_GREEN}{url}{NC}")
        print(f"  Download Format : {BOLD_CYAN}{format_display}{NC}")
        print(f"  Filename Style  : {BOLD_MAGENTA}{style.upper()}{NC}")
        print(f"  Output Folder   : {BOLD_BLUE}{out_dir}{NC}")
        if FFMPEG_EXE:
            print(f"  FFmpeg Engine   : {DIM}{Path(FFMPEG_EXE).name}{NC}")
    print("-" * 60 + "\n")

    out_template = get_outtmpl(style, mode if mode != "audio" else target_audio_fmt, out_dir)

    ydl_opts = {
        "outtmpl": out_template,
        "progress_hooks": [progress_hook],
        "noplaylist": not is_playlist,
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "windowsfilenames": True,
    }

    if FFMPEG_EXE:
        ydl_opts["ffmpeg_location"] = FFMPEG_EXE

    is_audio_mode = mode in ("audio", "mp3", "m4a", "opus", "wav", "best")
    if is_audio_mode:
        actual_fmt = target_audio_fmt if mode == "audio" else mode
        if actual_fmt == "best":
            ydl_opts["format"] = "bestaudio/best"
        elif actual_fmt == "wav":
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                }],
            })
        else:  # mp3, m4a, opus
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": actual_fmt,
                    "preferredquality": target_audio_br,
                }],
            })
    else:  # video
        format_str = get_video_format_selector(resolution, target_video_codec)
        ydl_opts.update({
            "format": format_str,
            "merge_output_format": effective_container,
        })

    download_success = False
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if is_upscale and mode == "video" and resolution and FFMPEG_EXE and FFmpegUpscalePP:
                ydl.add_post_processor(
                    FFmpegUpscalePP(ydl, target_height=resolution, codec=target_video_codec),
                    when="post_process"
                )
            ydl.download([url])
        download_success = True
    except Exception as e:
        print(f"\n  {BOLD_RED}✖ [ERROR]{NC} Download failed: {e}\n")

    if download_success:
        print(f"\n  {BOLD_GREEN}✔ [SUCCESS]{NC} Media downloaded & saved successfully!")
        print(f"  Output: {BOLD_BLUE}{out_dir}{NC}\n")

    print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")
    print(f"  {DIM}[Enter] Return to Menu  |  [o] Open Downloads Folder{NC}")
    print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")

    while True:
        k = get_key()
        if k in ("ENTER", "Q", "ESC"):
            clear_screen()
            break
        elif k == "O":
            open_download_folder()
            clear_screen()
            break


# =============================================================================
# 1. CATEGORY: DOWNLOAD (Direct Run)
# =============================================================================
def fetch_playlist_metadata(url: str, cached_data: dict) -> tuple[str, list[dict]]:
    """
    Fetches playlist title and flat entries, caching them in cached_data.
    """
    entries = cached_data.get("entries")
    pl_title = cached_data.get("pl_title")
    if entries is not None and pl_title is not None:
        return pl_title, entries

    parsed = urlparse(url)
    q = parse_qs(parsed.query)
    list_id = q.get("list", [None])[0]
    lookup_url = f"https://www.youtube.com/playlist?list={list_id}" if list_id else url

    clear_screen()
    print(f"{BOLD_CYAN}============================================================{NC}")
    print(f"{BOLD_YELLOW}Fetching Playlist Info...{NC}")
    print(f"{BOLD_CYAN}============================================================{NC}\n")
    print(f"  {DIM}Retrieving playlist metadata and video list...{NC}\n")

    entries = []
    pl_title = ""
    try:
        ydl_opts = {
            "extract_flat": "in_playlist",
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(lookup_url, download=False)
            pl_title = info.get("title") or ""
            entries = list(info.get("entries", []))
    except Exception:
        pass

    if not pl_title:
        pl_title = get_media_title(lookup_url, prefer_playlist=True) or "YouTube Playlist"

    cached_data["pl_title"] = pl_title
    cached_data["entries"] = entries
    return pl_title, entries


def handle_playlist_selection(url: str, playlist_mode: str, cached_data: dict | None = None) -> tuple[str, bool, str, list[str]] | None:
    """
    Handles playlist detection. Allows user to download entire playlist,
    or pick a specific video from the playlist.
    Returns: (effective_url, is_playlist, media_title, playlist_items) or None if cancelled/backed out.
    """
    if cached_data is None:
        cached_data = {"entries": None, "pl_title": None}

    if playlist_mode == "playlist":
        pl_title, entries = fetch_playlist_metadata(url, cached_data)
        item_titles = [e.get("title") or f"Video {i}" for i, e in enumerate(entries, 1)]
        return url, True, pl_title, item_titles

    while True:
        opts = [
            ("Download Entire Playlist (All Videos) 📑", "all", True, False),
            ("Pick a Specific Video from this Playlist 🎯", "pick", True, False),
            ("Back to Main Menu", "back", False, True)
        ]

        choice = select_menu_option(
            "Playlist Detected — Choose Action",
            opts,
            current_idx=0,
            header_info=[
                f"Target URL : {BOLD_GREEN}{url}{NC}",
                f"{DIM}Select whether to download all videos or pick an individual video.{NC}"
            ]
        )

        if choice in ("back", None):
            return None

        if choice == "all":
            pl_title, entries = fetch_playlist_metadata(url, cached_data)
            item_titles = [e.get("title") or f"Video {i}" for i, e in enumerate(entries, 1)]
            return url, True, pl_title, item_titles

        if choice == "pick":
            pl_title, entries = fetch_playlist_metadata(url, cached_data)

            if not entries:
                print(f"\n  {BOLD_RED}✖ No videos found in this playlist.{NC}\n")
                print(f"  {DIM}Press any key to return...{NC}")
                get_key()
                continue

            # Build video selection options and title lookup
            video_opts = []
            title_map = {}
            for idx, entry in enumerate(entries, 1):
                vid_title = entry.get("title") or f"Video {idx}"
                vid_id = entry.get("id") or entry.get("url")
                title_map[vid_id] = vid_title
                dur = entry.get("duration")
                dur_str = f"[{int(dur // 60)}:{int(dur % 60):02d}] " if dur else ""
                disp_title = (vid_title[:52] + "…") if len(vid_title) > 52 else vid_title
                label = f"{dur_str}{disp_title}"
                is_num = (idx <= 9)
                video_opts.append((label, vid_id, is_num, False))

            video_opts.append(("Back to Playlist Options", "back", False, True))

            v_choice = select_menu_option(
                f"Select Video ({len(entries)} items in playlist)",
                video_opts,
                current_idx=0,
                header_info=[
                    f"Playlist : {BOLD_CYAN}{pl_title}{NC} ({len(entries)} items)",
                    f"{DIM}Use [↑/↓] or numbers to pick which video to download.{NC}"
                ]
            )

            if v_choice in ("back", None):
                continue

            selected_url = f"https://www.youtube.com/watch?v={v_choice}"
            selected_title = title_map.get(v_choice, "")
            return selected_url, False, selected_title, []


def prompt_download_flow():
    """Category 1: Download - Prompts URL and starts directly."""
    cfg = load_config()
    curr_style = cfg.get("filename_style", "basic")
    playlist_mode = cfg.get("playlist_mode", "ask")
    cfg_audio_fmt = cfg.get("audio_format", "mp3").upper()
    cfg_audio_br = cfg.get("audio_bitrate", "320")

    err_msg = ""
    while True:
        clear_screen()
        sys.stdout.write("\033[?25h")
        print(f"{BOLD_CYAN}============================================================{NC}")
        print(f"{BOLD_YELLOW}Enter YouTube URL{NC}")
        print(f"{BOLD_CYAN}============================================================{NC}\n")
        print(f"  {DIM}Paste or enter video/playlist link. Leave empty or type 'q' to cancel.{NC}")
        print(f"  {DIM}Supported: youtube.com/watch, youtu.be, shorts, playlists, live, channels{NC}\n")

        if err_msg:
            print(f"  {BOLD_RED}✖ Error: {err_msg}{NC}")
            print(f"  {DIM}Please enter a genuine YouTube video, shorts, or playlist URL.{NC}\n")
            err_msg = ""

        raw_url = input(f"  {BOLD_CYAN}URL ➔  {NC}").strip()
        sys.stdout.write("\033[?25l")
        if not raw_url or raw_url.lower() in ("q", "quit", "cancel", "back"):
            return

        is_valid, norm_url, reason = validate_youtube_url(raw_url)
        if not is_valid:
            err_msg = reason
            continue

        url = norm_url
        break

    # Determine playlist behavior according to settings
    is_playlist_url = "list=" in url
    cached_pl_data = {"entries": None, "pl_title": None}

    while True:
        effective_url = url
        is_playlist = False
        media_title = ""

        if is_playlist_url:
            pl_result = handle_playlist_selection(url, playlist_mode, cached_pl_data)
            if pl_result is None:
                return  # user cancelled / backed out to main menu
            effective_url, is_playlist, media_title, playlist_items = pl_result
        else:
            is_playlist = False
            playlist_items = []
            media_title = get_media_title(effective_url)

        if not media_title:
            media_title = get_media_title(effective_url, prefer_playlist=is_playlist)

        cfg_res = cfg.get("default_resolution", "1080")
        cfg_upscale = cfg.get("force_upscale", False)
        cfg_v_codec = cfg.get("video_codec", "h264").upper()
        cfg_v_cnt = cfg.get("video_container", "auto").upper()
        eff_v_cnt = resolve_video_container(cfg.get("video_codec", "h264"), cfg.get("video_container", "auto")).upper()
        v_tag = f"[{cfg_v_codec} / .{eff_v_cnt.lower()}]"
        upscale_tag = f" {BOLD_YELLOW}[Upscale ON]{NC}" if cfg_upscale else ""

        audio_label_tag = f"[{cfg_audio_fmt} @ {cfg_audio_br}k / Configured]" if cfg_audio_fmt != "BEST" else "[Original Stream / Configured]"

        back_label = "Back to Playlist Options" if is_playlist_url else "Back to Main Menu"

        format_options = [
            # Video Section
            (f"{BOLD_CYAN}── Video Formats ────────────────────────────────────────{NC}", "header", False, False),
            (f"{'Video — Best Quality':<30} [Original Stream / Max Resolution] {v_tag}", "best_video", True, False, 1),
            (f"{f'Video — {cfg_res}p (Configured)':<30} [Target {cfg_res}p{upscale_tag}] {v_tag}", "cfg_video", True, False, 2),
            (f"{'Video — Other Resolutions (Pick)':<30}", "pick_video", True, False, 3),

            # Audio Section (separated by gap)
            (f"{BOLD_CYAN}── Audio Formats ────────────────────────────────────────{NC}", "header", False, True),
            (f"{f'Audio {cfg_audio_fmt} — Configured':<30} {audio_label_tag}", "audio_cfg", True, False, 1),
            (f"{'Audio — Other Formats (Pick)':<30}", "audio_pick", True, False, 2),

            # Back
            (back_label, "back", False, True)
        ]

        header = []
        if is_playlist:
            pl_name = media_title or "YouTube Playlist"
            item_count_str = f" ({len(playlist_items)} Videos)" if playlist_items else ""
            disp_pl_name = (pl_name[:55] + "…") if len(pl_name) > 55 else pl_name
            header.append(f"Playlist Name  : {BOLD_YELLOW}{disp_pl_name}{NC}{item_count_str}")
            if playlist_items:
                preview_items = " | ".join([f"{i}. {t[:22]}…" if len(t) > 22 else f"{i}. {t}" for i, t in enumerate(playlist_items[:3], 1)])
                if len(playlist_items) > 3:
                    preview_items += f" | +{len(playlist_items) - 3} more"
                header.append(f"Playlist Items : {DIM}{preview_items}{NC}")
        else:
            if media_title:
                disp_title = (media_title[:62] + "…") if len(media_title) > 65 else media_title
                header.append(f"Media Title    : {BOLD_YELLOW}{disp_title}{NC}")

        header.extend([
            f"Target URL     : {BOLD_GREEN}{effective_url}{NC}",
            f"Filename Style : {BOLD_MAGENTA}{curr_style.upper()}{NC}  |  Playlist Mode: {BOLD_CYAN}{'ON' if is_playlist else 'OFF'}{NC}",
            f"Video Engine   : Codec: {BOLD_CYAN}{cfg_v_codec}{NC}  |  Container: {BOLD_YELLOW}{cfg_v_cnt} (.{eff_v_cnt.lower()}){NC}  |  Upscale: {BOLD_YELLOW if cfg_upscale else DIM}{'ON (FFmpeg)' if cfg_upscale else 'OFF'}{NC}"
        ])

        format_curr_idx = 2  # Default selection on cfg_video
        back_to_playlist = False
        while True:
            choice = select_menu_option("Select Format / Quality", format_options, current_idx=format_curr_idx, header_info=header)
            if choice in ("back", None):
                if is_playlist_url:
                    back_to_playlist = True
                    break
                else:
                    return

            for idx_opt, opt in enumerate(format_options):
                if opt[1] == choice:
                    format_curr_idx = idx_opt
                    break

            if choice == "best_video":
                execute_download(effective_url, mode="video", resolution=None, is_playlist=is_playlist, media_title=media_title, playlist_items=playlist_items)
                return
            elif choice == "cfg_video":
                execute_download(effective_url, mode="video", resolution=cfg_res, is_playlist=is_playlist, media_title=media_title, playlist_items=playlist_items)
                return
            elif choice == "pick_video":
                pick_res_opts = [
                    (f"{'8K UHD':<10} [4320p Ultra High Definition]", "4320", True, False),
                    (f"{'4K UHD':<10} [2160p Ultra High Definition]", "2160", True, False),
                    (f"{'2K QHD':<10} [1440p Quad High Definition]", "1440", True, False),
                    (f"{'1080p FHD':<10} [Full High Definition - Standard]", "1080", True, False),
                    (f"{'720p HD':<10} [Standard High Definition]", "720", True, False),
                    (f"{'480p SD':<10} [Standard Definition / Fast]", "480", True, False),
                    (f"{'360p Low':<10} [Low Data Usage]", "360", True, False),
                    (f"{'240p LQ':<10} [Mobile Low Quality]", "240", True, False),
                    (f"{'144p Min':<10} [Minimal Bandwidth]", "144", True, False),
                    ("Back to Format Selection", "back", False, True)
                ]
                p_res = select_menu_option("Pick Specific Video Resolution", pick_res_opts, current_idx=3)
                if p_res and p_res != "back":
                    execute_download(effective_url, mode="video", resolution=p_res, is_playlist=is_playlist, media_title=media_title, playlist_items=playlist_items)
                    return
                else:
                    format_curr_idx = 3
                    continue
            elif choice == "audio_cfg":
                execute_download(effective_url, mode="audio", is_playlist=is_playlist, media_title=media_title, playlist_items=playlist_items)
                return
            elif choice == "audio_pick":
                pick_opts = [
                    (f"{'MP3 Audio':<12} [MPEG Layer-3 / 320 kbps]", "mp3", True, False),
                    (f"{'M4A Audio':<12} [AAC Audio / Mobile Friendly]", "m4a", True, False),
                    (f"{'OPUS Audio':<12} [High Efficiency Codec]", "opus", True, False),
                    (f"{'WAV Audio':<12} [Lossless Uncompressed PCM]", "wav", True, False),
                    (f"{'Best Audio':<12} [Original Stream / No Conversion]", "best", True, False),
                    ("Back to Format Selection", "back", False, True)
                ]
                p_c = select_menu_option("Pick Specific Audio Format", pick_opts, current_idx=0)
                if p_c and p_c != "back":
                    execute_download(effective_url, mode="audio", is_playlist=is_playlist, audio_format=p_c, media_title=media_title, playlist_items=playlist_items)
                    return
                else:
                    format_curr_idx = 6
                    continue

        if back_to_playlist:
            continue


# =============================================================================
# 2. CATEGORY: DIRECTORY (Files & Folder Management)
# =============================================================================
def handle_directory_menu():
    """Category 2: Directory - All folder and file management options."""
    curr_idx = 0
    while True:
        out_dir = get_download_path()
        files = sorted(
            [f for f in out_dir.iterdir() if f.is_file() and not f.name.startswith('.') and not f.name.endswith(('.part', '.ytdl'))],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        ) if out_dir.exists() else []

        total_size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024) if files else 0.0

        header = [
            f"Current Output Directory: {BOLD_BLUE}{out_dir}{NC}",
            f"Storage Statistics     : {BOLD_GREEN}{len(files)} file(s){NC}  ({total_size_mb:.1f} MB total)"
        ]

        options = [
            (f"Browse & Manage Media Files ({len(files)} files) 📄", "browse", True, False),
            ("Delete File 🗑", "delete_menu", True, False),
            ("Open Downloads Folder in File Explorer ↗", "open_dir", True, False),
            ("Back to Main Menu", "back", False, True)
        ]

        choice = select_menu_option("Directory & File Management", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            break

        for idx_opt, opt in enumerate(options):
            if opt[1] == choice:
                curr_idx = idx_opt
                break

        if choice == "browse":
            handle_browse_downloads()
        elif choice == "delete_menu":
            res = handle_delete_menu()
            if res == "main":
                break
        elif choice == "open_dir":
            open_download_folder()


def handle_delete_menu():
    """Submenu for deleting files: single (1 by 1) or all."""
    curr_idx = 0
    while True:
        out_dir = get_download_path()
        files = sorted(
            [f for f in out_dir.iterdir() if f.is_file() and not f.name.startswith('.') and not f.name.endswith(('.part', '.ytdl'))],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        ) if out_dir.exists() else []

        total_size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024) if files else 0.0

        header = [
            f"Directory: {BOLD_BLUE}{out_dir}{NC}  ({len(files)} file(s))",
            f"Storage  : {BOLD_GREEN}{total_size_mb:.1f} MB total{NC}"
        ]

        options = [
            ("Delete File Individually (1 by 1) 🗑", "single", True, False),
            ("Delete All Files in Downloads Folder ⚠️", "all", True, False),
            ("Back to Directory Menu", "back", False, True)
        ]

        choice = select_menu_option("Delete File", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            break

        for idx_opt, opt in enumerate(options):
            if opt[1] == choice:
                curr_idx = idx_opt
                break

        if choice == "single":
            handle_delete_single_file()
        elif choice == "all":
            if not files:
                clear_screen()
                print(f"{BOLD_CYAN}============================================================{NC}")
                print(f"{BOLD_YELLOW}Downloads Folder is Empty{NC}")
                print(f"{BOLD_CYAN}============================================================{NC}\n")
                print("  No downloaded files to delete.\n")
                sys.stdout.write("\033[?25h")
                input("Press Enter to continue...")
                sys.stdout.write("\033[?25l")
                continue

            clear_screen()
            sys.stdout.write("\033[?25h")
            print(f"{BOLD_CYAN}============================================================{NC}")
            print(f"{BOLD_RED}Delete All Files in Downloads Folder{NC}")
            print(f"{BOLD_CYAN}============================================================{NC}\n")
            print(f"  Are you sure you want to delete {BOLD_RED}{len(files)} files{NC} ({total_size_mb:.1f} MB)?\n")
            ans = input("  Confirm deletion? (y/N): ").strip().lower()
            sys.stdout.write("\033[?25l")
            if ans == "y":
                del_count = 0
                for f in files:
                    try:
                        f.unlink()
                        del_count += 1
                    except Exception:
                        pass
                print(f"\n  {BOLD_GREEN}✓ Deleted {del_count} file(s) successfully.{NC}")
                import time
                time.sleep(0.8)
                return "main"


def handle_delete_single_file():
    """Delete a single file from downloads folder with confirmation."""
    curr_idx = 0
    while True:
        out_dir = get_download_path()
        files = sorted(
            [f for f in out_dir.iterdir() if f.is_file() and not f.name.startswith('.') and not f.name.endswith(('.part', '.ytdl'))],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        ) if out_dir.exists() else []

        if not files:
            clear_screen()
            print(f"{BOLD_CYAN}============================================================{NC}")
            print(f"{BOLD_YELLOW}Downloads Folder is Empty{NC}")
            print(f"{BOLD_CYAN}============================================================{NC}\n")
            print("  No downloaded files to delete.\n")
            sys.stdout.write("\033[?25h")
            input("Press Enter to continue...")
            sys.stdout.write("\033[?25l")
            break

        header = [
            f"Directory: {BOLD_BLUE}{out_dir}{NC}  ({len(files)} file(s))",
            f"{DIM}Select a specific file to permanently delete from disk.{NC}"
        ]

        options = []
        for f in files:
            size_mb = f.stat().st_size / (1024 * 1024)
            ext = f.suffix.upper().replace('.', '')
            tag = f"{BOLD_RED}[{ext:<3}]{NC}"
            label = f"{tag} {f.stem[:40]:<42} {DIM}({size_mb:5.1f} MB){NC}"
            options.append((label, str(f), True, False))

        options.append(("Back to Delete Menu", "back", False, True))

        choice = select_menu_option("Delete File Individually (1 by 1)", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            break

        for idx_opt, opt in enumerate(options):
            if opt[1] == choice:
                curr_idx = idx_opt
                break

        selected_file = Path(choice)
        if selected_file.exists():
            file_size_mb = selected_file.stat().st_size / (1024 * 1024)
            clear_screen()
            sys.stdout.write("\033[?25h")
            print(f"{BOLD_CYAN}============================================================{NC}")
            print(f"{BOLD_RED}Delete File Confirmation{NC}")
            print(f"{BOLD_CYAN}============================================================{NC}\n")
            print(f"  File : {BOLD_CYAN}{selected_file.name}{NC}")
            print(f"  Size : {BOLD_YELLOW}{file_size_mb:.1f} MB{NC}\n")
            ans = input("  Are you sure you want to permanently delete this file? (y/N): ").strip().lower()
            sys.stdout.write("\033[?25l")
            if ans == "y":
                try:
                    selected_file.unlink()
                    print(f"\n  {BOLD_GREEN}✓ File deleted successfully.{NC}")
                    import time
                    time.sleep(0.6)
                    curr_idx = max(0, curr_idx - 1)
                except Exception as e:
                    print(f"\n  {BOLD_RED}✗ Error deleting file: {e}{NC}")
                    import time
                    time.sleep(1.2)


def handle_browse_downloads():
    """Browse existing downloaded files directly with file details and actions."""
    curr_idx = 0
    while True:
        out_dir = get_download_path()
        files = sorted(
            [f for f in out_dir.iterdir() if f.is_file() and not f.name.startswith('.') and not f.name.endswith(('.part', '.ytdl'))],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        ) if out_dir.exists() else []

        header = [
            f"Directory: {BOLD_BLUE}{out_dir}{NC}  ({len(files)} file(s) found)",
            f"{DIM}Select a file to play or manage.{NC}"
        ]

        if not files:
            options = [
                (f"{DIM}(No downloaded media files found in downloads/){NC}", "none", False, False),
                ("Back to Directory Menu", "back", False, True)
            ]
        else:
            options = []
            for f in files:
                size_mb = f.stat().st_size / (1024 * 1024)
                ext = f.suffix.upper().replace('.', '')
                tag = f"{BOLD_CYAN}[{ext:<3}]{NC}"
                label = f"{tag} {f.stem[:40]:<42} {DIM}({size_mb:5.1f} MB){NC}"
                options.append((label, str(f), True, False))

            options.append((f"{BOLD_YELLOW}📂 Open Directory in Explorer{NC}", "open_dir", False, True))
            options.append(("Back to Directory Menu", "back", False, True))

        choice = select_menu_option("Browse Downloaded Media Files", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", "none", None):
            break
        elif choice == "open_dir":
            curr_idx = len(options) - 2 if len(options) >= 2 else 0
            open_download_folder()
        else:
            # Remember selected index so returning preserves cursor position
            for idx_opt, opt in enumerate(options):
                if opt[1] == choice:
                    curr_idx = idx_opt
                    break

            selected_file = Path(choice)
            if not selected_file.exists():
                continue

            file_size_mb = selected_file.stat().st_size / (1024 * 1024)
            file_header = [
                f"File: {BOLD_CYAN}{selected_file.name}{NC}",
                f"Size: {BOLD_GREEN}{file_size_mb:.1f} MB{NC}  |  Format: {BOLD_YELLOW}{selected_file.suffix.upper()}{NC}"
            ]
            file_actions = [
                ("▶ Open in Default Media Player", "play", True, False),
                ("🗑 Delete this File", "delete", True, False),
                ("Back to File List", "back", False, True)
            ]

            act_choice = select_menu_option("File Actions", file_actions, header_info=file_header)
            if act_choice == "play":
                try:
                    if os.name == 'nt':
                        os.startfile(str(selected_file))
                    else:
                        subprocess.run(["xdg-open", str(selected_file)], check=False)
                except Exception as e:
                    print(f"Error opening file: {e}")
            elif act_choice == "delete":
                clear_screen()
                sys.stdout.write("\033[?25h")
                print(f"{BOLD_CYAN}============================================================{NC}")
                print(f"{BOLD_RED}Delete File Confirmation{NC}")
                print(f"{BOLD_CYAN}============================================================{NC}\n")
                print(f"  File : {BOLD_CYAN}{selected_file.name}{NC}")
                print(f"  Size : {BOLD_YELLOW}{file_size_mb:.1f} MB{NC}\n")
                ans = input("  Are you sure you want to permanently delete this file? (y/N): ").strip().lower()
                sys.stdout.write("\033[?25l")
                if ans == "y":
                    try:
                        selected_file.unlink()
                        print(f"\n  {BOLD_GREEN}✓ File deleted successfully.{NC}")
                        import time
                        time.sleep(0.6)
                        curr_idx = max(0, curr_idx - 1)
                    except Exception as e:
                        print(f"\n  {BOLD_RED}✗ Error deleting file: {e}{NC}")
                        import time
                        time.sleep(1.2)


def open_download_folder():
    out_dir = get_download_path()
    try:
        if os.name == 'nt':
            os.startfile(str(out_dir))
        else:
            subprocess.run(["xdg-open", str(out_dir)], check=False)
    except Exception as e:
        print(f"Error opening folder: {e}")


# =============================================================================
# 3. CATEGORY: SETTINGS (Separated Video & Audio Configuration)
# =============================================================================
def handle_video_resolution_select():
    """Sub-menu for Video Resolution / Quality target selection."""
    cfg = load_config()
    current_res = cfg.get("default_resolution", "1080")

    header = [
        f"Active: {BOLD_GREEN}{current_res}p{NC}  |  {DIM}Auto-fallback to next best if unavailable{NC}"
    ]

    def fmt_res(val, label):
        is_active = (current_res == val)
        icon = "●" if is_active else "○"
        color = BOLD_GREEN if is_active else DIM
        st_text = f" {BOLD_GREEN}[ACTIVE]{NC}" if is_active else ""
        return f"{color}{icon} {val:>4}p{NC}  {label:<34}{st_text}"

    r_opts = [
        (fmt_res("4320", "[8K UHD - 4320p]"), "4320", True, False),
        (fmt_res("2160", "[4K UHD - 2160p]"), "2160", True, False),
        (fmt_res("1440", "[2K QHD - 1440p]"), "1440", True, False),
        (fmt_res("1080", "[1080p FHD - Recommended]"), "1080", True, False),
        (fmt_res("720", "[720p HD - Standard]"), "720", True, False),
        (fmt_res("480", "[480p SD - Data Saver]"), "480", True, False),
        (fmt_res("360", "[360p Low - Fast]"), "360", True, False),
        (fmt_res("240", "[240p LQ - Mobile]"), "240", True, False),
        (fmt_res("144", "[144p Min - Minimal]"), "144", True, False),
        ("Back to Video Settings", "back", False, True)
    ]

    idx_map = {"4320": 0, "2160": 1, "1440": 2, "1080": 3, "720": 4, "480": 5, "360": 6, "240": 7, "144": 8}
    cur_idx = idx_map.get(current_res, 3)

    choice = select_menu_option("Video Quality / Target Resolution", r_opts, current_idx=cur_idx, header_info=header)
    if choice and choice != "back" and choice in idx_map:
        cfg["default_resolution"] = choice
        save_config(cfg)


def handle_video_codec_select():
    """Sub-menu for Preferred Video Codec selection."""
    cfg = load_config()
    current_codec = cfg.get("video_codec", "h264")

    header = [
        f"Active: {BOLD_GREEN}{current_codec.upper()}{NC}  |  {DIM}h264: 1080p max / high compat | av1: 8K/HDR | vp9: 4K/HDR{NC}"
    ]

    def fmt_codec(val, label, desc):
        is_active = (current_codec == val)
        icon = "●" if is_active else "○"
        color = BOLD_GREEN if is_active else DIM
        st_text = f" {BOLD_GREEN}[ACTIVE]{NC}" if is_active else ""
        return f"{color}{icon} {label:<14}{NC} {desc:<38}{st_text}"

    c_opts = [
        (fmt_codec("h264", "h264 + aac", "[Universal Compatibility / Max 1080p]"), "h264", True, False),
        (fmt_codec("av1", "av1 + opus", "[Best Quality & Efficiency / 8K & HDR]"), "av1", True, False),
        (fmt_codec("vp9", "vp9 + opus", "[High Quality Web Standard / 4K & HDR]"), "vp9", True, False),
        (fmt_codec("auto", "auto / best", "[Engine Optimal Auto Selection]"), "auto", True, False),
        ("Back to Video Settings", "back", False, True)
    ]

    idx_map = {"h264": 0, "av1": 1, "vp9": 2, "auto": 3}
    cur_idx = idx_map.get(current_codec, 0)

    choice = select_menu_option("Preferred YouTube Video Codec", c_opts, current_idx=cur_idx, header_info=header)
    if choice and choice != "back" and choice in idx_map:
        cfg["video_codec"] = choice
        save_config(cfg)


def handle_video_container_select():
    """Sub-menu for Video File Container selection."""
    cfg = load_config()
    current_codec = cfg.get("video_codec", "h264")
    current_container = cfg.get("video_container", "auto")
    eff_container = resolve_video_container(current_codec, current_container)

    header = [
        f"Active: {BOLD_GREEN}{current_container.upper()}{NC} (Resolves to: {BOLD_CYAN}.{eff_container}{NC})  |  {DIM}Auto: mp4 for h264, webm for vp9/av1{NC}"
    ]

    def fmt_cnt(val, label, desc):
        is_active = (current_container == val)
        icon = "●" if is_active else "○"
        color = BOLD_GREEN if is_active else DIM
        st_text = f" {BOLD_GREEN}[ACTIVE]{NC}" if is_active else ""
        return f"{color}{icon} {label:<8}{NC} {desc:<42}{st_text}"

    cnt_opts = [
        (fmt_cnt("auto", "auto", "[Auto: MP4 for H.264, WebM for VP9/AV1]"), "auto", True, False),
        (fmt_cnt("mp4", "mp4", "[Universal MP4 / Highest Media Compatibility]"), "mp4", True, False),
        (fmt_cnt("webm", "webm", "[WebM Open Container / Native VP9 & AV1]"), "webm", True, False),
        (fmt_cnt("mkv", "mkv", "[Matroska Flexible Container / All Codecs]"), "mkv", True, False),
        ("Back to Video Settings", "back", False, True)
    ]

    idx_map = {"auto": 0, "mp4": 1, "webm": 2, "mkv": 3}
    cur_idx = idx_map.get(current_container, 0)

    choice = select_menu_option("YouTube File Container", cnt_opts, current_idx=cur_idx, header_info=header)
    if choice and choice != "back" and choice in idx_map:
        cfg["video_container"] = choice
        save_config(cfg)


def handle_video_settings_menu():
    """Sub-menu for Video Settings Hub."""
    curr_idx = 0
    while True:
        cfg = load_config()
        current_res = cfg.get("default_resolution", "1080")
        current_codec = cfg.get("video_codec", "h264")
        current_container = cfg.get("video_container", "auto")
        force_upscale = cfg.get("force_upscale", False)
        eff_container = resolve_video_container(current_codec, current_container)
        codec_desc = "H.264 + AAC" if current_codec == "h264" else ("AV1 + Opus" if current_codec == "av1" else ("VP9 + Opus" if current_codec == "vp9" else "Auto"))
        upscale_disp = f"{BOLD_YELLOW}ON (FFmpeg lanczos){NC}" if force_upscale else f"{DIM}OFF (Native Only){NC}"

        header = [
            f"Quality: {BOLD_GREEN}{current_res}p{NC}  |  Codec: {BOLD_CYAN}{current_codec.upper()}{NC} ({codec_desc})  |  Container: {BOLD_YELLOW}.{eff_container}{NC}",
            f"Upscale: {BOLD_YELLOW if force_upscale else DIM}{'ON (FFmpeg)' if force_upscale else 'OFF'}{NC}  |  {DIM}Auto upscale lower streams to target resolution via FFmpeg{NC}"
        ]

        options = [
            (f"{'Video Quality / Resolution':<36} [{current_res}p] ⚙", "resolution", True, False),
            (f"{'Preferred Video Codec':<36} [{current_codec.upper()}] ⚙", "codec", True, False),
            (f"{'Video File Container':<36} [{current_container.upper()} -> .{eff_container}] ⚙", "container", True, False),
            (f"{'Force Upscale Resolution':<36} [{upscale_disp}]", "toggle_upscale", True, False),
            ("Back to Settings", "back", False, True)
        ]

        choice = select_menu_option("Video Settings 🎬", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            break

        if choice == "resolution":
            handle_video_resolution_select()
        elif choice == "codec":
            handle_video_codec_select()
        elif choice == "container":
            handle_video_container_select()
        elif choice == "toggle_upscale":
            cfg["force_upscale"] = not cfg.get("force_upscale", False)
            save_config(cfg)


def handle_audio_format_select():
    """Sub-menu for Audio Format selection."""
    cfg = load_config()
    current_fmt = cfg.get("audio_format", "mp3")

    header = [
        f"Active Format: {BOLD_GREEN}{current_fmt.upper()}{NC}  |  {DIM}Source conversion handled by FFmpeg{NC}"
    ]

    def fmt_item(val, desc):
        is_active = (current_fmt == val)
        icon = "●" if is_active else "○"
        color = BOLD_GREEN if is_active else DIM
        st_text = f" {BOLD_GREEN}[ACTIVE]{NC}" if is_active else ""
        return f"{color}{icon} {val:<6}{NC} {desc:<38}{st_text}"

    opts = [
        (fmt_item("mp3", "[MPEG Layer-3 / Universal Compatibility]"), "mp3", True, False),
        (fmt_item("m4a", "[AAC Audio / Apple & Mobile Friendly]"), "m4a", True, False),
        (fmt_item("opus", "[Opus Audio / High Efficiency Codec]"), "opus", True, False),
        (fmt_item("wav", "[Lossless Uncompressed PCM Audio]"), "wav", True, False),
        (fmt_item("best", "[Original Audio Stream / No Conversion]"), "best", True, False),
        ("Back to Audio Settings", "back", False, True)
    ]

    idx_map = {"mp3": 0, "m4a": 1, "opus": 2, "wav": 3, "best": 4}
    cur_idx = idx_map.get(current_fmt, 0)

    choice = select_menu_option("Audio Format Settings", opts, current_idx=cur_idx, header_info=header)
    if choice and choice != "back" and choice in idx_map:
        cfg["audio_format"] = choice
        save_config(cfg)


def handle_audio_bitrate_select():
    """Sub-menu for Audio Bitrate selection."""
    cfg = load_config()
    current_bitrate = str(cfg.get("audio_bitrate", "320"))

    header = [
        f"Active Bitrate: {BOLD_GREEN}{current_bitrate} kbps{NC}  |  {DIM}Applies to MP3, M4A, and Opus{NC}"
    ]

    def fmt_br(val, label):
        is_active = (current_bitrate == val)
        icon = "●" if is_active else "○"
        color = BOLD_GREEN if is_active else DIM
        st_text = f" {BOLD_GREEN}[ACTIVE]{NC}" if is_active else ""
        return f"{color}{icon} {val} kb/s{NC}  {label:<30}{st_text}"

    opts = [
        (fmt_br("320", "[Maximum Quality / 320 kbps]"), "320", True, False),
        (fmt_br("256", "[Very High Quality / 256 kbps]"), "256", True, False),
        (fmt_br("192", "[Standard High Quality / 192 kbps]"), "192", True, False),
        (fmt_br("128", "[Standard Web Quality / 128 kbps]"), "128", True, False),
        (fmt_br("96", "[Low Bitrate / Voice Optimized]"), "96", True, False),
        ("Back to Audio Settings", "back", False, True)
    ]

    idx_map = {"320": 0, "256": 1, "192": 2, "128": 3, "96": 4}
    cur_idx = idx_map.get(current_bitrate, 0)

    choice = select_menu_option("Audio Bitrate Settings", opts, current_idx=cur_idx, header_info=header)
    if choice and choice != "back" and choice in idx_map:
        cfg["audio_bitrate"] = choice
        save_config(cfg)


def handle_audio_settings_menu():
    """Sub-menu for Audio Settings (Format & Bitrate)."""
    curr_idx = 0
    while True:
        cfg = load_config()
        audio_fmt = cfg.get("audio_format", "mp3")
        audio_br = cfg.get("audio_bitrate", "320")

        header = [
            f"Format: {BOLD_GREEN}{audio_fmt.upper()}{NC}  |  Bitrate: {BOLD_GREEN}{audio_br} kbps{NC} (applicable for MP3/M4A/Opus)"
        ]

        options = [
            (f"{'Audio Format':<36} [{audio_fmt.upper()}] ⚙", "format", True, False),
            (f"{'Audio Bitrate':<36} [{audio_br} kb/s] ⚙", "bitrate", True, False),
            ("Back to Settings", "back", False, True)
        ]

        choice = select_menu_option("Audio Settings 🎵", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            break

        if choice == "format":
            handle_audio_format_select()
        elif choice == "bitrate":
            handle_audio_bitrate_select()


def handle_settings_menu():
    """Category 3: Settings - Consolidated configuration hub."""
    curr_idx = 0
    while True:
        cfg = load_config()
        style = cfg.get("filename_style", "basic")
        res = cfg.get("default_resolution", "1080")
        codec = cfg.get("video_codec", "h264")
        container = cfg.get("video_container", "auto")
        eff_container = resolve_video_container(codec, container)
        audio_fmt = cfg.get("audio_format", "mp3")
        audio_br = cfg.get("audio_bitrate", "320")
        down_dir = cfg.get("download_dir", "downloads")
        playlist_mode = cfg.get("playlist_mode", "ask")

        mode_display = {
            "ask": "Ask on Detect [Ask]",
            "playlist": "Always Full Playlist [Playlist]",
            "single": "Always Single Video [Single]"
        }
        playlist_disp = mode_display.get(playlist_mode, "Ask on Detect")

        force_upscale = cfg.get("force_upscale", False)
        upscale_lbl = f" {BOLD_YELLOW}[Upscale ON]{NC}" if force_upscale else ""
        header = [
            f"Video: {BOLD_GREEN}{res}p{NC} ({BOLD_CYAN}{codec.upper()}{NC} / {BOLD_YELLOW}.{eff_container}{NC}){upscale_lbl}  |  Audio: {BOLD_GREEN}{audio_fmt.upper()}@{audio_br}k{NC}  |  Style: {BOLD_MAGENTA}{style.upper()}{NC}",
            f"Playlist: {BOLD_CYAN}{playlist_disp}{NC}  |  Folder: {BOLD_BLUE}{down_dir}{NC}",
        ]

        options = [
            (f"{'Video Settings 🎬':<36} [{res}p / {codec.upper()}{' / Upscale' if force_upscale else ''}] ⚙", "video", True, False),
            (f"{'Audio Settings 🎵':<36} [{audio_fmt.upper()} @ {audio_br}k] ⚙", "audio", True, False),
            (f"{'Filename Style Settings':<36} [{style.upper()}] ⚙", "style", True, False),
            (f"{'Playlist Download Mode':<36} [{playlist_mode.capitalize()}]", "playlist_mode", True, False),
            (f"{'Change Download Folder Path':<36} [{down_dir}]", "dir", True, False),
            ("Back to Main Menu", "back", False, True)
        ]

        choice = select_menu_option("Settings & Preferences Hub", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            break

        if choice == "video":
            handle_video_settings_menu()
        elif choice == "audio":
            handle_audio_settings_menu()
        elif choice == "style":
            handle_filename_style_config()
        elif choice == "playlist_mode":
            p_opts = [
                (f"{'Ask on Detect (Recommended)':<32} [Prompt when playlist link is entered]", "ask", True, False),
                (f"{'Always Single Video':<32} [Never download playlist, only 1 video]", "single", True, False),
                (f"{'Always Full Playlist':<32} [Automatically download all playlist items]", "playlist", True, False),
                ("Back to Settings", "back", False, True)
            ]
            p_idx = 0 if playlist_mode == "ask" else (1 if playlist_mode == "single" else 2)
            p_choice = select_menu_option("Configure Playlist Download Mode", p_opts, current_idx=p_idx)
            if p_choice and p_choice != "back":
                cfg["playlist_mode"] = p_choice
                save_config(cfg)
        elif choice == "dir":
            clear_screen()
            sys.stdout.write("\033[?25h")
            print(f"{BOLD_CYAN}============================================================{NC}")
            print(f"{BOLD_YELLOW}Change Download Directory{NC}")
            print(f"  Current Path: {BOLD_GREEN}{down_dir}{NC}")
            print(f"{BOLD_CYAN}============================================================{NC}\n")
            val = input(f"  Enter new folder path (press Enter to keep '{down_dir}'): ").strip()
            sys.stdout.write("\033[?25l")
            if val and val.lower() not in ("q", "quit", "cancel", "back"):
                cfg["download_dir"] = val
                save_config(cfg)


def handle_filename_style_config():
    cfg = load_config()
    current_style = cfg.get("filename_style", "basic")

    header = [
        f"Active: {BOLD_GREEN}{current_style.upper()}{NC}  |  {DIM}Preview of generated filenames:{NC}"
    ]

    def format_item(name, desc_v, style_key):
        is_active = (current_style == style_key)
        icon = "●" if is_active else "○"
        color = BOLD_GREEN if is_active else DIM
        st_text = f" {BOLD_GREEN}[ACTIVE]{NC}" if is_active else ""
        return f"{color}{icon} {name:<8}{NC} {desc_v:<40}{st_text}"

    options = [
        (format_item("basic", "Title - Channel (1080p).mp4", "basic"), "basic", True, False),
        (format_item("pretty", "Title - Channel (1080p, youtube).mp4", "pretty"), "pretty", True, False),
        (format_item("nerdy", "Title - Channel (1080p, youtube, id).mp4", "nerdy"), "nerdy", True, False),
        (format_item("classic", "youtube_id_1080p.mp4", "classic"), "classic", True, False),
        ("Back to Settings", "back", False, True)
    ]

    idx_map = {"basic": 0, "pretty": 1, "nerdy": 2, "classic": 3}
    cur_idx = idx_map.get(current_style, 0)

    choice = select_menu_option("Configure Filename Style", options, current_idx=cur_idx, header_info=header)
    if choice in ("basic", "pretty", "nerdy", "classic"):
        cfg["filename_style"] = choice
        save_config(cfg)


# =============================================================================
# MAIN MENU (3 Core Categories)
# =============================================================================
def run_tui():
    """Main TUI Loop structured in 3 categories: Download, Directory, Settings."""
    try:
        clear_screen()
        sys.stdout.write("\033[?1049h\033[H\033[?25l")  # Alternate screen buffer & hide cursor
        sys.stdout.flush()
        curr_idx = 0

        while True:
            cfg = load_config()
            style = cfg.get("filename_style", "basic")
            res = cfg.get("default_resolution", "1080")
            codec = cfg.get("video_codec", "h264")
            container = cfg.get("video_container", "auto")
            eff_cnt = resolve_video_container(codec, container)
            audio_fmt = cfg.get("audio_format", "mp3")
            audio_br = cfg.get("audio_bitrate", "320")
            out_dir = get_download_path(cfg.get("download_dir"))
            playlist_mode = cfg.get("playlist_mode", "ask")

            # Count downloaded items
            existing_count = len([f for f in out_dir.iterdir() if f.is_file() and not f.name.startswith('.') and not f.name.endswith(('.part', '.ytdl'))]) if out_dir.exists() else 0

            force_upscale = cfg.get("force_upscale", False)
            upscale_lbl = f" | Upscale: {BOLD_YELLOW}ON{NC}" if force_upscale else ""
            header = [
                f"Engine Status  : {BOLD_GREEN}Ready{NC}  |  FFmpeg: {BOLD_CYAN}Active{NC} ({Path(FFMPEG_EXE).name if FFMPEG_EXE else 'None'})",
                f"Configuration  : Video: {BOLD_CYAN}{res}p/{codec.upper()}/.{eff_cnt}{NC}{upscale_lbl}  |  Audio: {BOLD_GREEN}{audio_fmt.upper()}@{audio_br}k{NC}  |  Style: {BOLD_MAGENTA}{style.upper()}{NC}"
            ]

            main_menu = [
                ("Download Media 🚀", "download", True, False),
                (f"Directory & Files ({existing_count} file{'s' if existing_count != 1 else ''}) 📂", "directory", True, False),
                ("Settings & Preferences ⚙", "settings", True, False),
                ("Exit", "exit", False, True)
            ]

            choice = select_menu_option("YouTube Downloader — Terminal Interactive UI", main_menu, current_idx=curr_idx, header_info=header)

            if choice in ("exit", "back", None):
                break
            elif choice == "download":
                prompt_download_flow()
            elif choice == "directory":
                handle_directory_menu()
            elif choice == "settings":
                handle_settings_menu()
    except KeyboardInterrupt:
        pass
    finally:
        clear_screen()
        sys.stdout.write("\033[?1049l\033[?25h")  # Restore screen buffer & cursor
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        run_tui()
    except KeyboardInterrupt:
        pass
