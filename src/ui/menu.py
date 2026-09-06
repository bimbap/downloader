# =============================================================================
# downloader/src/ui/menu.py – Interactive Menu Navigator & Paginator
# =============================================================================
import sys
import shutil
from core.console import (
    BOLD_CYAN,
    BOLD_YELLOW,
    BOLD_GREEN,
    BOLD_RED,
    DIM,
    BOLD,
    NC,
    CLEAR_LINE,
    clear_screen,
    get_key,
)


def select_menu_option(
    title: str,
    options: list[tuple],
    current_idx: int = 0,
    header_info: list[str] | None = None,
    clear_on_start: bool = True
) -> str | None:
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
