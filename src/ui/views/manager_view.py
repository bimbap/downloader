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
    get_category_overview,
    open_file_in_player,
    open_download_folder,
    delete_file,
    delete_all_files,
)
from core.config import get_download_path
from ui.menu import select_menu_option


def run_category_browser(cat_info: dict):
    """Browses and manages files inside a specific platform/media category."""
    cat_path = cat_info["path"]
    cat_label = cat_info["label"]
    cat_icon = cat_info["icon"]
    is_all = cat_info["key"] == "all"

    curr_idx = 0
    while True:
        files = scan_downloaded_files(None if is_all else cat_path)
        if not files:
            clear_screen()
            print(f"{BOLD_CYAN}============================================================{NC}")
            print(f"{BOLD_YELLOW}{cat_icon} {cat_label}{NC}")
            print(f"{BOLD_CYAN}============================================================{NC}\n")
            print(f"  {DIM}Folder Path:{NC} {BOLD_BLUE}{cat_path}{NC}")
            print(f"  {BOLD_YELLOW}No downloaded files found in this category.{NC}\n")
            print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")
            print(f"  {DIM}[Enter/q] Back to Categories  |  [o] Open Folder in Explorer{NC}")
            print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")

            while True:
                k = get_key()
                if k in ("ENTER", "Q", "ESC", "BACKSPACE"):
                    clear_screen()
                    return
                elif k == "O":
                    open_download_folder(cat_path)
                    clear_screen()
                    break
            return

        total_size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
        header = [
            f"Category: {BOLD_YELLOW}{cat_icon} {cat_label}{NC}",
            f"Folder  : {BOLD_BLUE}{cat_path}{NC}",
            f"Library : {BOLD_GREEN}{len(files)}{NC} items  |  Size: {BOLD_YELLOW}{total_size_mb:.1f} MB{NC}"
        ]

        options = []
        for idx, f in enumerate(files):
            size_mb = f.stat().st_size / (1024 * 1024)
            s = f.suffix.lower()
            icon = "🎬" if s in (".mp4", ".mkv", ".webm") else ("🎵" if s in (".mp3", ".m4a", ".opus", ".wav") else "📷")
            sub_tag = f"[{f.parent.name}] " if is_all and f.parent != cat_path else ""
            label = f"{icon} {sub_tag}{f.name} ({size_mb:.1f} MB)"
            options.append((label, f"file_{idx}", True, False))

        options.append(("[Open This Folder in Explorer 📂]", "open_folder", False, True))
        options.append(("[Delete All Files in This Category 🗑]", "delete_all", False, False))
        options.append(("Back to Category Selection", "back", False, True))

        choice = select_menu_option(f"{cat_icon} {cat_label}", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            clear_screen()
            break

        if choice == "open_folder":
            open_download_folder(cat_path)
            curr_idx = len(options) - 3

        elif choice == "delete_all":
            clear_screen()
            print(f"{BOLD_RED}============================================================{NC}")
            print(f"{BOLD_RED}⚠ CONFIRM CATEGORY DELETION{NC}")
            print(f"{BOLD_RED}============================================================{NC}\n")
            print(f"  Are you sure you want to delete ALL {BOLD_YELLOW}{len(files)}{NC} files in:")
            print(f"  {BOLD_CYAN}{cat_label}{NC} ({BOLD_BLUE}{cat_path}{NC})?\n")
            print(f"  Type {BOLD_RED}'YES'{NC} to confirm, or press Enter to cancel:")
            confirm = safe_input("  Confirm: ").strip()

            if confirm.upper() == "YES":
                deleted = delete_all_files(cat_path)
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
                f"Size : {f_size:.1f} MB  |  Category: {cat_label}",
                f"Path : {selected_file.parent}"
            ]
            f_choice = select_menu_option("File Action", file_opts, header_info=f_header)
            if f_choice == "play":
                open_file_in_player(selected_file)
            elif f_choice == "delete":
                delete_file(selected_file)
                curr_idx = max(0, f_idx - 1)


def run_manager_view():
    """Top-level Folder & Category Selector view."""
    curr_idx = 0
    while True:
        overview = get_category_overview()
        root_dir = get_download_path()
        all_item = overview[0]
        total_files = all_item["count"]
        total_size_mb = all_item["size_mb"]

        header = [
            f"Storage : {BOLD_BLUE}{root_dir}{NC}",
            f"Library : {BOLD_GREEN}{total_files}{NC} items  |  Total Size: {BOLD_YELLOW}{total_size_mb:.1f} MB{NC}"
        ]

        options = []
        for cat in overview:
            count = cat["count"]
            size_mb = cat["size_mb"]
            count_str = f"{count} files" if count > 0 else "empty"
            size_str = f" • {size_mb:.1f} MB" if count > 0 else ""
            label = f"{cat['icon']} {cat['label']} [{count_str}{size_str}]"
            options.append((label, cat["key"], True, False))

        options.append(("[Open Main Downloads Folder in Explorer 📂]", "open_root", False, True))
        options.append(("Return to Main Menu", "back", False, True))

        choice = select_menu_option("📁 Manage Downloads – Select Category", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            clear_screen()
            break

        if choice == "open_root":
            open_download_folder(root_dir)
            curr_idx = len(options) - 2
        else:
            # Find matching category info
            matched = next((c for c in overview if c["key"] == choice), None)
            if matched:
                run_category_browser(matched)
                # Keep cursor on the category
                curr_idx = next((i for i, c in enumerate(overview) if c["key"] == choice), 0)
