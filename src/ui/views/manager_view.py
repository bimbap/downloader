# =============================================================================
# downloader/src/ui/views/manager_view.py – Downloaded Media Manager
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
    open_file_in_player,
    open_download_folder,
    delete_file,
    delete_all_files,
)
from core.config import get_download_path
from ui.menu import select_menu_option


def run_manager_view():
    """Interactive media manager and browser."""
    curr_idx = 0
    while True:
        files = scan_downloaded_files()
        out_dir = get_download_path()

        if not files:
            clear_screen()
            print(f"{BOLD_CYAN}============================================================{NC}")
            print(f"{BOLD_YELLOW}📁 Downloaded Media Manager{NC}")
            print(f"{BOLD_CYAN}============================================================{NC}\n")
            print(f"  {DIM}Storage Path:{NC} {BOLD_BLUE}{out_dir}{NC}")
            print(f"  {BOLD_YELLOW}No downloaded media files found.{NC}\n")
            print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")
            print(f"  {DIM}[Enter/q] Back  |  [o] Open Downloads Folder{NC}")
            print(f"{BOLD_CYAN}------------------------------------------------------------{NC}")

            while True:
                k = get_key()
                if k in ("ENTER", "Q", "ESC", "BACKSPACE"):
                    clear_screen()
                    return
                elif k == "O":
                    open_download_folder(out_dir)
                    clear_screen()
                    break
            continue

        total_size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
        header = [
            f"Location: {BOLD_BLUE}{out_dir}{NC}",
            f"Library : {BOLD_GREEN}{len(files)}{NC} items  |  Total Size: {BOLD_YELLOW}{total_size_mb:.1f} MB{NC}"
        ]

        options = []
        for idx, f in enumerate(files):
            size_mb = f.stat().st_size / (1024 * 1024)
            icon = "🎬" if f.suffix.lower() in (".mp4", ".mkv", ".webm") else ("🎵" if f.suffix.lower() in (".mp3", ".m4a", ".opus", ".wav") else "📷")
            parent_tag = f"[{f.parent.name}] " if f.parent != out_dir else ""
            label = f"{icon} {parent_tag}{f.name} ({size_mb:.1f} MB)"
            options.append((label, f"file_{idx}", True, False))

        options.append(("[Open Downloads Folder in Explorer 📂]", "open_folder", False, True))
        options.append(("[Delete All Downloaded Files 🗑]", "delete_all", False, False))
        options.append(("Return to Main Menu", "back", False, True))

        choice = select_menu_option("Downloaded Media Manager 📁", options, current_idx=curr_idx, header_info=header)
        if choice in ("back", None):
            clear_screen()
            break

        if choice == "open_folder":
            open_download_folder(out_dir)
            curr_idx = len(options) - 3

        elif choice == "delete_all":
            clear_screen()
            print(f"{BOLD_RED}============================================================{NC}")
            print(f"{BOLD_RED}⚠ CONFIRM BULK DELETION{NC}")
            print(f"{BOLD_RED}============================================================{NC}\n")
            print(f"  Are you sure you want to delete ALL {BOLD_YELLOW}{len(files)}{NC} downloaded files?")
            print(f"  This will permanently remove {BOLD_YELLOW}{total_size_mb:.1f} MB{NC} of data.\n")
            print(f"  Type {BOLD_RED}'YES'{NC} to confirm, or press Enter to cancel:")
            confirm = safe_input("  Confirm: ").strip()

            if confirm.upper() == "YES":
                deleted = delete_all_files(out_dir)
                clear_screen()
                print(f"\n  {BOLD_GREEN}✔ Deleted {deleted} file(s) successfully.{NC}\n")
                # Immediately return to Main Menu as per design rule
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
                f"Size : {f_size:.1f} MB  |  Folder: {selected_file.parent.name}"
            ]
            f_choice = select_menu_option("File Action", file_opts, header_info=f_header)
            if f_choice == "play":
                open_file_in_player(selected_file)
            elif f_choice == "delete":
                delete_file(selected_file)
                curr_idx = max(0, f_idx - 1)
