# =============================================================================
# downloader/src/core/console.py – Terminal & Console Management
# =============================================================================
import os
import sys

# Force UTF-8 encoding on Windows to prevent cp1252 UnicodeEncodeError
for stream in (sys.stdout, sys.stderr, sys.stdin):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

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


def set_quick_edit_mode(enabled: bool):
    """Enable or disable QuickEdit mode on Windows console to prevent clicks from freezing execution or wiping clipboard."""
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h_in = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
        in_mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(h_in, ctypes.byref(in_mode)):
            if enabled:
                new_mode = in_mode.value | 0x0040 | 0x0080  # ENABLE_QUICK_EDIT_MODE | ENABLE_EXTENDED_FLAGS
            else:
                new_mode = (in_mode.value & ~0x0040) | 0x0080  # Disable QuickEdit
            kernel32.SetConsoleMode(h_in, new_mode)
    except Exception:
        pass


def configure_windows_console():
    """Enable VT100 ANSI mode and disable QuickEdit to prevent freeze / clipboard wipe."""
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h_out = kernel32.GetStdHandle(-11)
        out_mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(h_out, ctypes.byref(out_mode)):
            kernel32.SetConsoleMode(h_out, out_mode.value | 0x0004 | 0x0008)
    except Exception:
        pass
    try:
        os.system("")
    except Exception:
        pass
    set_quick_edit_mode(False)


def hide_cursor():
    """Hides terminal cursor."""
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor():
    """Shows terminal cursor."""
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def clear_screen():
    """Clear screen without wiping scrollback or freezing Windows CMD."""
    if os.name == "nt":
        os.system("cls")
    else:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


def safe_input(prompt_text: str = "") -> str:
    """Safely prompt for input, re-enabling cursor and QuickEdit (for pasting) during prompt."""
    set_quick_edit_mode(True)
    show_cursor()
    try:
        return input(prompt_text)
    finally:
        set_quick_edit_mode(False)
        hide_cursor()


def get_key() -> str:
    """Cross-platform zero-lag raw key reader."""
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):
            ch2 = msvcrt.getch()
            if ch2 == b"H": return "UP"
            if ch2 == b"P": return "DOWN"
            if ch2 == b"K": return "LEFT"
            if ch2 == b"M": return "RIGHT"
        if ch in (b"\r", b"\n"): return "ENTER"
        if ch == b" ": return "SPACE"
        if ch in (b"\x08", b"\x7f"): return "BACKSPACE"
        if ch in (b"q", b"Q"): return "Q"
        if ch in (b"o", b"O"): return "O"
        if ch in (b"s", b"S"): return "S"
        if ch == b"\x1b": return "ESC"
        return "UNKNOWN"
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A": return "UP"
                    if ch3 == "B": return "DOWN"
                    if ch3 == "C": return "RIGHT"
                    if ch3 == "D": return "LEFT"
                return "ESC"
            if ch in ("\r", "\n"): return "ENTER"
            if ch == " ": return "SPACE"
            if ch in ("\x7f", "\x08"): return "BACKSPACE"
            if ch in ("q", "Q"): return "Q"
            if ch in ("o", "O"): return "O"
            if ch in ("s", "S"): return "S"
            return "UNKNOWN"
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


# Initialize console on import
configure_windows_console()
