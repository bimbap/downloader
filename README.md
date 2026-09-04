# YouTube Downloader — Interactive Terminal UI (TUI) & CLI

An ultra-fast, zero-lag interactive Terminal UI for downloading, converting, and upscaling YouTube videos and audio with customizable filename styles, powered by `yt-dlp` and `imageio-ffmpeg`.

---

## Highlights

- 🚀 **Zero-Lag ANSI Terminal UI**: Smooth keyboard-driven navigation (`↑/↓`, number jump `1-9`, `Enter`, `q`/`ESC`) with instant response.
- 📐 **Dynamic Viewport Pagination**: Sliding-window pagination automatically adapts to any terminal height, preventing vertical scroll overflow and eliminating duplicate header spam.
- 🔍 **Smart Upscale Engine**: Native support for upscaling lower-resolution sources to 1440p (2K), 2160p (4K), and 4320p (8K) via FFmpeg's high-precision Lanczos filter (`scale=-2:H:flags=lanczos`).
- 🎵 **Comprehensive Audio Transcoding**: Convert to MP3 (up to 320 kbps), M4A (AAC), Opus, WAV (lossless PCM), or preserve the original best audio stream.
- 🎬 **Granular Video Settings**: Select target resolutions (144p to 8K), video codecs (`h264`, `av1`, `vp9`, `auto`), and containers (`mp4`, `webm`, `mkv`, `auto`).
- 🏷️ **Custom Filename Styles**: Choose between `basic`, `pretty`, `nerdy`, and `classic` naming conventions.
- 📂 **Media Management**: Browse files with active cursor memory, play in the system default media player, or delete items individually (1 by 1) with safe confirmation prompts.
- 📦 **Bundled FFmpeg Runtime**: Uses `imageio-ffmpeg` static binaries — zero manual PATH setup or external FFmpeg installation required.
- 💻 **Cross-Platform Dual Launchers**: Native Windows launcher (`run.bat`) and universal POSIX Bash launcher (`yt.sh`) for Linux, macOS, WSL, and Git Bash.
- ⚡ **Headless CLI Mode**: Full command-line argument support for scripts, automation, and background jobs.

---

## Directory Structure

```text
yt-downloader/
├── yt.sh                  # Universal POSIX Bash launcher (Linux / macOS / WSL / Git Bash)
├── run.bat                # Windows CMD / PowerShell / Git Bash hybrid launcher
├── requirements.txt       # Python dependencies (yt-dlp, imageio-ffmpeg)
├── README.md              # Project documentation
├── .gitignore             # Git ignore definitions
│
├── config/                # Persistent user preferences
│   └── config.json        # Configuration file (JSON format)
│
├── src/                   # Application source code
│   ├── __init__.py        # Package marker
│   ├── tui.py             # Interactive Terminal UI engine
│   ├── downloader.py      # Core CLI download & upscale engine
│   └── config_helper.py   # Settings manager & filename template generator
│
└── downloads/             # Default destination for downloaded media
    └── .gitkeep           # Directory tracking marker
```

---

## Installation

### Prerequisites
- **Python 3.10+** installed on your system.

### Setup (Zero-Config)
Clone the repository and run immediately:

```bash
git clone <repo-url>
cd yt-downloader
```

> 💡 **Auto-Setup / Zero-Config**: Launchers (`run.bat` and `yt.sh`) and python entrypoints **automatically detect and install missing dependencies** (`yt-dlp`, `imageio-ffmpeg`) on first run. You can also install them manually if desired:
> ```bash
> pip install -r requirements.txt
> ```

> **Note**: You do not need to install FFmpeg manually. The bundled `imageio-ffmpeg` package provides cross-platform static FFmpeg binaries automatically.

---

## Quick Start

### 1. Interactive TUI Mode

Run the launcher appropriate for your operating system or shell:

#### Windows (CMD / PowerShell):
```powershell
.\run.bat
```

#### Linux / macOS / WSL / Git Bash:
```bash
./yt.sh
```

#### Python Direct:
```bash
python src/tui.py
```

### 2. TUI Keyboard Controls

| Key | Action |
| :--- | :--- |
| `[↑]` / `[k]` | Move selection cursor up |
| `[↓]` / `[j]` | Move selection cursor down |
| `[1]` – `[9]` | Quick jump directly to numbered option |
| `[Enter]` / `[Space]` | Confirm / Select option |
| `[q]` / `[ESC]` | Return to previous menu / Exit |

---

## Menu System Overview

The interactive TUI is organized into 3 clear operational modules:

```text
┌─────────────────────────────────────────────────────────┐
│              YouTube Downloader & Transcoder            │
│  [↑/↓] Navigate   [1-4] Number   [Enter] Select   [q]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ▸ 1. 🚀 Download Media                                 │
│    2. 📂 Directory & Files                              │
│    3. ⚙  Settings & Preferences                         │
│                                                         │
│    4. ✕ Exit                                            │
└─────────────────────────────────────────────────────────┘
```

### 1. 🚀 Download Media
- **Strict YouTube URL Validation**: Instant syntax and domain validation prevents invalid or spoofed links (supports standard watch URLs, `youtu.be`, Shorts, Live streams, Clips, and Playlists).
- **Interactive Playlist Support**: When a playlist is detected, choose between:
  - **Download Entire Playlist (All Videos)**: Downloads all items sequentially.
  - **Pick a Specific Video from this Playlist**: Fetches metadata and opens an interactive browser displaying titles, durations, and indices so you can select and download any single video.
  - *Seamless Navigation*: Backing out of the format/quality selection returns right back to the playlist options without re-entering the URL.
- Options:
  - **Download with Default Settings**: Instant download using your saved preferences.
  - **Custom / On-the-fly Override**: Select resolution, codec, container, or audio format specifically for this download.
- Real-time ANSI progress bar displays download percentage, transfer speed, downloaded/total size, and ETA.

### 2. 📂 Directory & Files
- **Browse & Manage Media Files**: Lists all completed audio and video files with file sizes. Selecting any file presents a dedicated action menu:
  - **▶ Open in Default Media Player**: Plays the selected file in your system player (e.g., VLC, Windows Media Player, mpv). Returning preserves your cursor position.
  - **🗑 Delete this File**: Prompts for confirmation `(y/N)` and permanently deletes the individual file.
  - *Clean File Listing*: Automatically filters out hidden temporary files (`.temp_*`).
- **Delete File 🗑**: Centralized deletion hub with two options:
  - **Delete File Individually (1 by 1) 🗑**: Dedicated browser to pick and delete specific files one at a time with safety confirmation `(y/N)`.
  - **Delete All Files in Downloads Folder ⚠️**: Bulk cleanup option with file count and total storage confirmation prompt.
- **Open in File Explorer ↗**: Instantly launches the download folder in Windows Explorer (`explorer.exe`), macOS Finder (`open`), or Linux file managers (`xdg-open`).

### 3. ⚙ Settings & Preferences
Centralized settings management with dedicated submenus:
- **🎬 Video Settings**:
  - **Target Resolution**: `4320p` (8K), `2160p` (4K), `1440p` (2K), `1080p`, `720p`, `480p`, `360p`, `240p`, `144p`.
  - **Preferred Codec**: `h264 + aac` (Universal max 1080p), `av1 + opus` (High-efficiency 8K/HDR), `vp9 + opus` (Web standard), `auto`.
  - **File Container**: `auto` (mp4 for h264, webm for vp9/av1), `mp4`, `webm`, `mkv`.
  - **Force Upscale (Lanczos)**: Toggle `ON/OFF`. If the native YouTube video resolution is lower than your target resolution (e.g., requesting 1440p on a 1080p source), FFmpeg automatically upscales the video using the Lanczos scaling filter.
- **🎵 Audio Settings**:
  - **Active Format**: `mp3`, `m4a`, `opus`, `wav`, `best`.
  - **Target Bitrate**: `320k`, `256k`, `192k`, `128k`, `96k`.
- **🏷️ Filename Style**: `basic`, `pretty`, `nerdy`, `classic`.
- **📋 Playlist Handling**: `Ask on Detect`, `Always Single Video`, `Always Full Playlist`.
- **📁 Output Folder**: Configure a custom download path.

---

## Filename Styles Reference

Customizable filename templates keep your media library organized:

| Style | Video Format Pattern | Audio Format Pattern |
| :--- | :--- | :--- |
| **`basic`** *(Default)* | `Title - Channel (1080p).mp4` | `Title - Channel.mp3` |
| **`pretty`** | `Title - Channel (1080p, youtube).mp4` | `Title - Channel (youtube).mp3` |
| **`nerdy`** | `Title - Channel (1080p, youtube, dQw4w9WgXcQ).mp4` | `Title - Channel (youtube, dQw4w9WgXcQ).mp3` |
| **`classic`** | `youtube_dQw4w9WgXcQ_1080p.mp4` | `youtube_dQw4w9WgXcQ_audio.mp3` |

---

## Headless CLI Commands

For automated workflows, shell scripts, or quick one-off downloads without the TUI, pass arguments directly to the launcher:

```bash
# Syntax
./yt.sh "<URL>" [OPTIONS]
# or on Windows
run.bat "<URL>" [OPTIONS]
```

### Examples

```bash
# 1. Download best quality video using basic style (default)
./yt.sh "https://youtu.be/dQw4w9WgXcQ"

# 2. Download 1080p MP4 with h264 codec
./yt.sh "https://youtu.be/dQw4w9WgXcQ" -r 1080 -c h264 --container mp4

# 3. Download and upscale to 1440p (2K) via Lanczos filter
./yt.sh "https://youtu.be/dQw4w9WgXcQ" -r 1440 -u

# 4. Extract audio as 320 kbps MP3
./yt.sh "https://youtu.be/dQw4w9WgXcQ" -f mp3 -b 320

# 5. Extract lossless WAV audio with pretty filename
./yt.sh "https://youtu.be/dQw4w9WgXcQ" -f wav -s pretty

# 6. Download entire playlist to custom directory
./yt.sh "https://www.youtube.com/playlist?list=..." -p -o "/path/to/music"
```

### CLI Options Table

| Flag | Long Argument | Choices / Values | Description |
| :--- | :--- | :--- | :--- |
| `-f` | `--format` | `video`, `audio`, `mp3`, `m4a`, `opus`, `wav`, `best` | Target output format type |
| `-r` | `--res` | `4320`, `2160`, `1440`, `1080`, `720`, `480`, `360`, `240`, `144` | Video resolution ceiling |
| `-c` | `--codec` | `h264`, `av1`, `vp9`, `auto` | Preferred video codec |
| | `--container` | `auto`, `mp4`, `webm`, `mkv` | Video container encapsulation |
| `-s` | `--style` | `basic`, `pretty`, `nerdy`, `classic` | Filename naming style |
| `-b` | `--bitrate` | `320`, `256`, `192`, `128`, `96` | Audio bitrate in kbps |
| `-u` | `--force-upscale` | *(Flag)* | Enable FFmpeg Lanczos upscale if native < target |
| | `--no-force-upscale` | *(Flag)* | Disable upscale (native stream only) |
| `-o` | `--output` | `<path>` | Custom output directory path |
| `-p` | `--playlist` | *(Flag)* | Download entire playlist |
| | `--config` | *(Flag)* | Open interactive settings menu |

---

## Configuration Reference (`config/config.json`)

Settings modified via the TUI are persistently stored in `config/config.json`:

```json
{
  "filename_style": "basic",
  "default_resolution": "1080",
  "video_codec": "h264",
  "video_container": "auto",
  "audio_format": "mp3",
  "audio_bitrate": "320",
  "download_dir": "downloads",
  "playlist_mode": "ask",
  "force_upscale": false
}
```

---

## Technical Highlights

1. **Sliding-Window Viewport Pagination**:
   Terminal file browsing dynamically computes available rows:
   ```python
   max_visible = min(8, max(3, term_rows - header_count - 3))
   ```
   Combined with a strict `term_rows - 1` output guard, the screen never triggers vertical scrolling, completely preventing ANSI header duplication.
2. **Safe Atomic Upscaling**:
   FFmpeg Lanczos upscaling encodes to a hidden file (`.temp_upscale_<name>`) and renames it atomically upon completion. If an upscale process is interrupted, the original downloaded file remains unharmed.
3. **Cross-Platform Path Resolution**:
   Relative and absolute download paths are normalized safely across Windows (`M:\...`), POSIX (`/home/...`), and Git Bash (`/m/...`).

---

## License

This project is open-source and intended for personal media downloading and archiving. Please respect the copyright and terms of service of any media content you download.
