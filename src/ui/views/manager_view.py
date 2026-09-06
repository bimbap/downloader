# =============================================================================
# downloader/src/ui/views/manager_view.py – Downloaded Media Manager & Browser
# =============================================================================
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
from core.file_manager import (
    scan_downloaded_files,
    get_platform_hierarchy,
    open_file_in_player,
    open_download_folder,
    delete_file,
    delete_all_files,
)
from core.config import get_download_path
from core.i18n import t
from ui.menu import select_menu_option


def run_file_browser(target_path: Path, title: str, icon: str = "📁", can_delete_all: bool = True):
    """Browses and interacts with media files in a specific directory."""
    curr_idx = 0
    while True:
        files = scan_downloaded_files(target_path)
        if not files:
            clear_screen()
            print(f"{BOLD_CYAN}── {BOLD_YELLOW}{title}{BOLD_CYAN} ─────────────────────────────{NC}")
            print(f"  {DIM}{t('folder')}:{NC} {BOLD_BLUE}{target_path}{NC}")
            print(f"  {BOLD_YELLOW}{t('no_files_category')}{NC}\n")
            print(f"  {DIM}[Enter/q] {t('back_simple')}  |  [o] {t('open_folder')}{NC}\n")

            while True:
                k = get_key()
                if k in ("ENTER", "Q", "ESC", "BACKSPACE"):
                    clear_screen()
                    return
                elif k == "O":
                    open_download_folder(target_path)
                    clear_screen()
                    break
            return

        total_size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
        header = [
            f"Location: {BOLD_YELLOW}{title}{NC}",
            f"{t('folder')}  : {BOLD_BLUE}{target_path}{NC}",
            f"{t('library')} : {BOLD_GREEN}{len(files)}{NC} {t('items')}  |  {t('size')}: {BOLD_YELLOW}{total_size_mb:.1f} MB{NC}"
        ]

        options = []
        for idx, f in enumerate(files):
            size_mb = f.stat().st_size / (1024 * 1024)
            s = f.suffix.lower()
            f_icon = "🎬" if s in (".mp4", ".mkv", ".webm") else ("🎵" if s in (".mp3", ".m4a", ".opus", ".wav") else "📷")
            sub_tag = f"[{f.parent.name}] " if f.parent != target_path else ""
            label = f"{f_icon} {sub_tag}{f.name} ({size_mb:.1f} MB)"
            options.append((label, f"file_{idx}", True, False))

        options.append((t("open_this_folder"), "open_folder", False, True))
        if can_delete_all:
            options.append((t("delete_all_in_folder"), "delete_all", False, False))
        options.append((t("back_simple"), "back", False, True))

        choice = select_menu_option(title, options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            clear_screen()
            break

        if choice == "open_folder":
            open_download_folder(target_path)
            curr_idx = len(options) - 3 if can_delete_all else len(options) - 2

        elif choice == "delete_all":
            clear_screen()
            print(f"{BOLD_RED}── {BOLD_RED}{t('confirm_delete_title')}{BOLD_RED} ─────────────────────────────{NC}\n")
            print(f"  {t('confirm_delete_msg', count=len(files))}")
            print(f"  {BOLD_CYAN}{title}{NC} ({BOLD_BLUE}{target_path}{NC})?\n")
            print(f"  {t('confirm_delete_prompt')}")
            confirm = safe_input("  Confirm: ").strip().upper()

            if confirm in ("YES", "YA", "Y"):
                deleted = delete_all_files(target_path)
                clear_screen()
                print(f"\n  {BOLD_GREEN}{t('deleted_success', count=deleted)}{NC}\n")
                return
            clear_screen()

        elif choice.startswith("file_"):
            f_idx = int(choice.split("_")[1])
            selected_file = files[f_idx]
            curr_idx = f_idx

            file_opts = [
                (t("play_media"), "play", True, False),
                (t("delete_file"), "delete", True, False),
                (t("back_simple"), "back", False, True)
            ]
            f_size = selected_file.stat().st_size / (1024 * 1024)
            f_header = [
                f"File : {BOLD_YELLOW}{selected_file.name}{NC}",
                f"{t('size')} : {f_size:.1f} MB  |  Location: {title}",
                f"Path : {selected_file.parent}"
            ]
            f_choice = select_menu_option(t("file_action"), file_opts, header_info=f_header)
            if f_choice == "play":
                open_file_in_player(selected_file)
            elif f_choice == "delete":
                delete_file(selected_file)
                curr_idx = max(0, f_idx - 1)


def run_platform_view(plat_data: dict):
    """Shows non-empty format folders (photo, video, audio) for a selected platform."""
    curr_idx = 0
    while True:
        # Re-fetch hierarchy to keep file counts fresh
        platforms = get_platform_hierarchy()
        current = next((p for p in platforms if p["key"] == plat_data["key"]), None)
        if not current or not current["categories"]:
            # Platform has no files left
            return

        cats = current["categories"]

        # If only 1 format category exists, jump straight into it
        if len(cats) == 1:
            cat = cats[0]
            run_file_browser(cat["path"], f"{current['name']} / {cat['name']}", icon=cat["icon"])
            return

        # Multiple format categories exist (e.g. photo and video)
        header = [
            f"Platform: {BOLD_YELLOW}{current['icon']} {current['name']}{NC}",
            f"{t('storage')} : {BOLD_BLUE}{current['path']}{NC}",
            f"{t('library')} : {BOLD_GREEN}{current['count']}{NC} {t('files')}  |  {t('size')}: {BOLD_YELLOW}{current['size_mb']:.1f} MB{NC}"
        ]

        options = [
            (t("all_platform_media", name=current['name'], count=current['count'], size=current['size_mb']), "all", True, False)
        ]
        for cat in cats:
            label = f"{cat['icon']} {cat['name']} [{cat['count']} {t('files')} • {cat['size_mb']:.1f} MB]"
            options.append((label, cat["key"], True, False))

        options.append((t("open_platform_folder", name=current['name']), "open_plat_folder", False, True))
        options.append((t("back_simple"), "back", False, True))

        choice = select_menu_option(t("manager_select_format", icon=current['icon'], name=current['name']), options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            clear_screen()
            break

        if choice == "open_plat_folder":
            open_download_folder(current["path"])
            curr_idx = len(options) - 2
        elif choice == "all":
            run_file_browser(current["path"], f"All {current['name']} Files", icon=current["icon"])
            curr_idx = 0
        else:
            selected_cat = next((c for c in cats if c["key"] == choice), None)
            if selected_cat:
                run_file_browser(selected_cat["path"], f"{current['name']} / {selected_cat['name']}", icon=selected_cat["icon"])
                curr_idx = next((i for i, c in enumerate(cats) if c["key"] == choice), 0) + 1


def run_manager_view():
    """Top-level Platform Selector for downloaded media."""
    curr_idx = 0
    while True:
        platforms = get_platform_hierarchy()
        root_dir = get_download_path()

        if not platforms:
            clear_screen()
            print(f"{BOLD_CYAN}── {BOLD_YELLOW}{t('menu_manager')}{BOLD_CYAN} ─────────────────────────────{NC}")
            print(f"  {DIM}{t('storage')}:{NC} {BOLD_BLUE}{root_dir}{NC}")
            print(f"  {BOLD_YELLOW}{t('no_files_found')}{NC}\n")
            print(f"  {DIM}[Enter/q] {t('back')}  |  [o] {t('open_folder')}{NC}\n")

            while True:
                k = get_key()
                if k in ("ENTER", "Q", "ESC", "BACKSPACE"):
                    clear_screen()
                    return
                elif k == "O":
                    open_download_folder(root_dir)
                    clear_screen()
                    break
            continue

        total_files = sum(p["count"] for p in platforms)
        total_size_mb = sum(p["size_mb"] for p in platforms)

        header = [
            f"{t('storage')} : {BOLD_BLUE}{root_dir}{NC}",
            f"{t('library')} : {BOLD_GREEN}{total_files}{NC} {t('items')}  |  {t('size')}: {BOLD_YELLOW}{total_size_mb:.1f} MB{NC}"
        ]

        options = []
        if len(platforms) > 1:
            options.append((t("all_platforms", count=total_files, size=total_size_mb), "all_platforms", True, False))

        for p in platforms:
            label = f"{p['icon']} {p['name']} [{p['count']} {t('files')} • {p['size_mb']:.1f} MB]"
            options.append((label, p["key"], True, False))

        options.append((t("open_root_folder"), "open_root", False, True))
        options.append((t("back"), "back", False, True))

        choice = select_menu_option(t("manager_title"), options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            clear_screen()
            break

        if choice == "open_root":
            open_download_folder(root_dir)
            curr_idx = len(options) - 2
        elif choice == "all_platforms":
            run_file_browser(root_dir, t("all_media"), icon="📂")
            curr_idx = 0
        else:
            selected_plat = next((p for p in platforms if p["key"] == choice), None)
            if selected_plat:
                run_platform_view(selected_plat)
                curr_idx = next((i for i, p in enumerate(platforms) if p["key"] == choice), 0) + (1 if len(platforms) > 1 else 0)
