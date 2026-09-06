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
from ui.menu import select_menu_option


def run_file_browser(target_path: Path, title: str, icon: str = "📁", can_delete_all: bool = True):
    """Browses and interacts with media files in a specific directory."""
    curr_idx = 0
    while True:
        files = scan_downloaded_files(target_path)
        if not files:
            clear_screen()
            print(f"{BOLD_CYAN}============================================================{NC}")
            print(f"{BOLD_YELLOW}{icon} {title}{NC}")
            print(f"{BOLD_CYAN}============================================================{NC}\n")
            print(f"  {DIM}Folder Path:{NC} {BOLD_BLUE}{target_path}{NC}")
            print(f"  {BOLD_YELLOW}No files remaining in this folder.{NC}\n")
            print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")
            print(f"  {DIM}[Enter/q] Back  |  [o] Open Folder in Explorer{NC}")
            print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")

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
            f"Location: {BOLD_YELLOW}{icon} {title}{NC}",
            f"Folder  : {BOLD_BLUE}{target_path}{NC}",
            f"Library : {BOLD_GREEN}{len(files)}{NC} items  |  Size: {BOLD_YELLOW}{total_size_mb:.1f} MB{NC}"
        ]

        options = []
        for idx, f in enumerate(files):
            size_mb = f.stat().st_size / (1024 * 1024)
            s = f.suffix.lower()
            f_icon = "🎬" if s in (".mp4", ".mkv", ".webm") else ("🎵" if s in (".mp3", ".m4a", ".opus", ".wav") else "📷")
            sub_tag = f"[{f.parent.name}] " if f.parent != target_path else ""
            label = f"{f_icon} {sub_tag}{f.name} ({size_mb:.1f} MB)"
            options.append((label, f"file_{idx}", True, False))

        options.append(("[Open This Folder in Explorer 📂]", "open_folder", False, True))
        if can_delete_all:
            options.append(("[Delete All Files in This Folder 🗑]", "delete_all", False, False))
        options.append(("Back", "back", False, True))

        choice = select_menu_option(f"{icon} {title}", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            clear_screen()
            break

        if choice == "open_folder":
            open_download_folder(target_path)
            curr_idx = len(options) - 3 if can_delete_all else len(options) - 2

        elif choice == "delete_all":
            clear_screen()
            print(f"{BOLD_RED}============================================================{NC}")
            print(f"{BOLD_RED}⚠ CONFIRM FOLDER DELETION{NC}")
            print(f"{BOLD_RED}============================================================{NC}\n")
            print(f"  Are you sure you want to delete ALL {BOLD_YELLOW}{len(files)}{NC} files in:")
            print(f"  {BOLD_CYAN}{title}{NC} ({BOLD_BLUE}{target_path}{NC})?\n")
            print(f"  Type {BOLD_RED}'YES'{NC} to confirm, or press Enter to cancel:")
            confirm = safe_input("  Confirm: ").strip()

            if confirm.upper() == "YES":
                deleted = delete_all_files(target_path)
                clear_screen()
                print(f"\n  {BOLD_GREEN}✔ Deleted {deleted} file(s) successfully.{NC}\n")
                return
            clear_screen()

        elif choice.startswith("file_"):
            f_idx = int(choice.split("_")[1])
            selected_file = files[f_idx]
            curr_idx = f_idx

            file_opts = [
                ("Play / View Media ▶", "play", True, False),
                ("Delete File 🗑", "delete", True, False),
                ("Back", "back", False, True)
            ]
            f_size = selected_file.stat().st_size / (1024 * 1024)
            f_header = [
                f"File : {BOLD_YELLOW}{selected_file.name}{NC}",
                f"Size : {f_size:.1f} MB  |  Location: {title}",
                f"Path : {selected_file.parent}"
            ]
            f_choice = select_menu_option("File Action", file_opts, header_info=f_header)
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
            f"Storage : {BOLD_BLUE}{current['path']}{NC}",
            f"Library : {BOLD_GREEN}{current['count']}{NC} files  |  Size: {BOLD_YELLOW}{current['size_mb']:.1f} MB{NC}"
        ]

        options = [
            (f"📂 All {current['name']} Media [{current['count']} files • {current['size_mb']:.1f} MB]", "all", True, False)
        ]
        for cat in cats:
            label = f"{cat['icon']} {cat['name']} [{cat['count']} files • {cat['size_mb']:.1f} MB]"
            options.append((label, cat["key"], True, False))

        options.append((f"[Open {current['name']} Folder in Explorer 📂]", "open_plat_folder", False, True))
        options.append(("Back to Platform Selection", "back", False, True))

        choice = select_menu_option(f"{current['icon']} {current['name']} – Select Format", options, current_idx=curr_idx, header_info=header)
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
            print(f"{BOLD_CYAN}============================================================{NC}")
            print(f"{BOLD_YELLOW}📁 Downloaded Media Manager{NC}")
            print(f"{BOLD_CYAN}============================================================{NC}\n")
            print(f"  {DIM}Storage Path:{NC} {BOLD_BLUE}{root_dir}{NC}")
            print(f"  {BOLD_YELLOW}No downloaded media files found.{NC}\n")
            print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")
            print(f"  {DIM}[Enter/q] Back to Menu  |  [o] Open Downloads Folder{NC}")
            print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")

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
            f"Storage : {BOLD_BLUE}{root_dir}{NC}",
            f"Library : {BOLD_GREEN}{total_files}{NC} items  |  Total Size: {BOLD_YELLOW}{total_size_mb:.1f} MB{NC}"
        ]

        options = []
        if len(platforms) > 1:
            options.append((f"📂 All Platforms [{total_files} files • {total_size_mb:.1f} MB]", "all_platforms", True, False))

        for p in platforms:
            label = f"{p['icon']} {p['name']} [{p['count']} files • {p['size_mb']:.1f} MB]"
            options.append((label, p["key"], True, False))

        options.append(("[Open Downloads Folder in Explorer 📂]", "open_root", False, True))
        options.append(("Return to Main Menu", "back", False, True))

        choice = select_menu_option("📁 Manage Downloads – Select Platform", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            clear_screen()
            break

        if choice == "open_root":
            open_download_folder(root_dir)
            curr_idx = len(options) - 2
        elif choice == "all_platforms":
            run_file_browser(root_dir, "All Downloaded Media", icon="📂")
            curr_idx = 0
        else:
            selected_plat = next((p for p in platforms if p["key"] == choice), None)
            if selected_plat:
                run_platform_view(selected_plat)
                curr_idx = next((i for i, p in enumerate(platforms) if p["key"] == choice), 0) + (1 if len(platforms) > 1 else 0)
