# Terminal UI Design & Interaction Guidelines — Downloader

**Project:** Universal Social Media Downloader  
**Document:** TUI Design System & Interaction Spec  
**Status:** Authoritative  

---

## 1. Design Philosophy & Aesthetic Identity

The **Universal Social Media Downloader** adheres to a **Minimalist Cyberpunk / Tactical Terminal** design language.
Key principles:
1. **Zero-Lag Responsiveness**: All screen redraws are performed in-place using ANSI VT100 control sequences (`\033[2J\033[H` and `\r`). Avoid full-window flickering or delayed paints.
2. **Tactile Density**: High information density structured with clear hierarchical borders, bold accents, and dimmed context labels.
3. **Scroll-Free Viewports**: The terminal UI must never scroll vertically past the bottom edge. It behaves like a native windowed GUI within the terminal canvas.
4. **Intuitive Dual Controls**: Power users can navigate via standard arrows (`↑/↓`), Vim keys (`k/j`), or direct single-keypress numeric jumps (`1` through `9`).

---

## 2. Color Palette & ANSI Design Tokens

All colors are centralized in `src/core/console.py` using standard VT100 escape codes for maximum cross-platform fidelity:

| Token | Hex Preview | ANSI Code | Semantic Role |
| :--- | :--- | :--- | :--- |
| `BOLD_CYAN` | `#00D9FF` | `\033[1;36m` | Window headers, titles, platform tags, section dividers |
| `BOLD_YELLOW` | `#FFD700` | `\033[1;33m` | Media titles, active highlight tags, warnings, FPS |
| `BOLD_GREEN` | `#00FF66` | `\033[1;32m` | Success badges (`✔`), completed progress bars, counts |
| `BOLD_RED` | `#FF3344` | `\033[1;31m` | Errors (`✖`), cancellation states, critical alerts |
| `BOLD_MAGENTA` | `#FF007F` | `\033[1;35m` | Media types (`CAROUSEL`, `GALLERY`, `PLAYLIST`) |
| `BOLD_BLUE` | `#3399FF` | `\033[1;34m` | File system paths, output directories |
| `DIM` | `#888888` | `\033[2m` | Metadata hints, author tags, secondary info, key hints |
| `BOLD` | `#FFFFFF` | `\033[1m` | Emphasized body text, active menu cursor |
| `NC` | *Reset* | `\033[0m` | Reset code (clears attributes after every print) |

---

## 3. Screen Structure & Layout Hierarchy

Every view in the application follows a standardized layout:

```text
┌─────────────────────────────────────────────────────────────┐
│ ── Title / Section Header ────────────────────────────────  │  <- Header Line (CYAN/YELLOW)
│   Target : Video / Playlist Title (50 chars truncate)       │  <- Context Header Block
│   Author : Creator Name  |  Type: VIDEO                     │
├─────────────────────────────────────────────────────────────┤
│   ▲ More items above (3 hidden)                             │  <- Pagination Indicator (Top)
│                                                             │
│   >  1.  Option One Description                   [ACTIVE]  │  <- Active Selected Option
│          Sub-description or note (dimmed)                   │
│                                                             │
│      2.  Option Two Description                   [VALUE]   │  <- Inactive Option
│                                                             │
│   ▼ More items below (5 hidden)                             │  <- Pagination Indicator (Bottom)
├─────────────────────────────────────────────────────────────┤
│   [↑/↓] Navigate  [1-9] Quick Jump  [Enter] Select  [q] Back │  <- Standard Footer Controls
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Viewport Pagination Engine (`src/ui/menu.py`)

### Algorithm
1. **Terminal Height Detection**: Queries rows via `shutil.get_terminal_size().lines`.
2. **Reserved Space Computation**:
   - Header title + empty lines: 3 rows
   - Context `header_info` lines: $N$ rows
   - Footer instructions: 3 rows
   - Safety padding: 2 rows
   - `available_rows = terminal_lines - reserved_rows`
3. **Sliding Window Offset**:
   - Items calculate item height (single line vs multi-line with sub-descriptions).
   - If total items exceed available rows, a sliding window `[top_idx, top_idx + visible_count]` is computed.
   - Cursor movement automatically adjusts `top_idx` to keep the active item visible while rendering top/bottom indicator arrows:
     ```text
     ▲ More items above (N hidden)
     ▼ More items below (N hidden)
     ```

---

## 5. Keyboard Navigation Standards

| Keypress | Functionality | Context |
| :--- | :--- | :--- |
| `[↑]` / `[k]` | Move selection cursor up | Menu navigation |
| `[↓]` / `[j]` | Move selection cursor down | Menu navigation |
| `[1]` – `[9]` | Instant selection jump by number | Quick menu selection |
| `[Enter]` / `[Space]` | Confirm and execute active option | Selection confirmation |
| `[q]` / `[ESC]` | Return to parent menu or cancel flow | Safe exit navigation |
| `[o]` | Open download folder in Explorer/Finder | Result banner screen |
| `[p]` | Open/play downloaded media in default player | Result banner screen |

---

## 6. Real-Time Stream Progress Design

### Visual Progress Bar
```text
  [████████████████████░░░░░░░░░░]  65.4% | 15.2 MB/s | ETA 00:04
```
- **Stream Segregation**: YouTube multi-stream downloads present clear stream identities:
  ```text
  [Video Stream] Downloading 1080p stream...
  [██████████████████████████████] 100.0% | 24.1 MB/s
  [Audio Stream] Downloading best audio stream...
  [████████████░░░░░░░░░░░░░░░░░░]  42.0% | 8.3 MB/s | ETA 00:02
  ```
- **Upscaling Progress**: Hardware GPU encoding renders real-time frame rates and speeds:
  ```text
  [████████████████░░░░░░░░░░░░░░]  52.1% | 01:14 / 02:22 | 84 fps | Speed: 2.8x
  ```

---

## 7. Windows Console Hardening & UX Safety

1. **QuickEdit Mode Suppression**: On Windows, clicking inside CMD/PowerShell freezes console execution until Enter is pressed. The application automatically disables QuickEdit at startup via Windows Win32 API (`SetConsoleMode`).
2. **Safe Input Guard**: When prompting the user for URL input via `safe_input()`, the cursor is restored and Windows QuickEdit is temporarily re-enabled so users can paste links via mouse right-click or `Ctrl+V`.
3. **Keyboard Buffer Flushing**: Before rendering a new interactive menu, the standard input buffer is flushed (`msvcrt.getch()` on Windows or `termios.tcflush()` on POSIX) to prevent buffered keypresses from leaking into the next view.
