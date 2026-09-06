# Universal Social Media Downloader — Interactive Terminal UI & CLI

An ultra-fast, zero-lag interactive Terminal UI & CLI for downloading, converting, and upscaling media across **YouTube**, **X (formerly Twitter)**, **Instagram**, and **Meta Threads**, powered by a modular Python engine, `yt-dlp`, and bundled `imageio-ffmpeg`.

---

## Highlights

- ⚡ **Universal Smart Downloader**: Paste any link from YouTube, X, Instagram, or Threads — the engine automatically detects the platform, extracts the media type (video, audio, photo, carousel gallery), and downloads with optimal quality.
- 🚀 **Zero-Lag ANSI Terminal UI**: Smooth keyboard-driven navigation (`↑/↓`, number jump `1-9`, `Enter`, `q`/`ESC`) with instant in-place buffer redraws.
- 📐 **Dynamic Viewport Pagination**: Sliding-window pagination automatically adapts to any terminal height, preventing vertical scroll overflow and eliminating duplicate header spam.
- 🔴 **YouTube Mastery**:
  - Video downloads up to 8K Ultra HD (`4320p`, `2160p`, `1440p`, `1080p`, `720p`, etc.).
  - True Playlist Intelligence: Resolves playlist titles, counts, and itemized listings with instant in-memory caching.
  - Multi-Stream ANSI Progress: Distinct tracking for Video and Audio streams with live `MB/s` speed formatting.
  - Comprehensive Audio Transcoding: Convert to MP3 (up to 320 kbps), M4A (AAC), Opus, WAV (lossless PCM), or preserve the original best stream.
- 🐦 **X / Twitter Downloader**:
  - Video & animated GIF downloads with highest available bitrate.
  - Multi-photo galleries: downloads all original-resolution images (`:orig`) with batch progress tracking.
- 📷 **Instagram Downloader**:
  - Download Reels, single video posts, and IGTV videos.
  - High-resolution photo posts and carousel galleries.
- 🧵 **Meta Threads Downloader**:
  - High-speed video and photo downloads directly from Threads posts.
- 🔍 **GPU-Accelerated Upscale Engine**: Native support for upscaling lower-resolution sources to 1440p (2K), 2160p (4K), and 4320p (8K) via hardware GPU acceleration (NVIDIA NVENC, Intel QSV, AMD AMF) or optimized CPU Bicubic scaling with real-time streaming progress bars and ETA.
- 🌐 **Bilingual Interface (i18n)**: Seamless language switching between English 🇬🇧 and Bahasa Indonesia 🇮🇩 with instant in-memory translation updates.
- 🍪 **Browser Cookie Authentication**: Directly import local session cookies from Chrome, Firefox, Edge, Brave, Opera, or Vivaldi to bypass YouTube age restrictions (18+) and download login-restricted Instagram and X posts.
- 🧹 **1-Click Temp & Cache Cleaner**: Instant scanning and purging of broken partial downloads (`.part`, `.ytdl`, `.tmp`) to recover disk space.
- 🔄 **Factory Reset & Recovery**: Effortlessly restore settings to factory defaults with interactive confirmation guards.
- 📁 **Organized Media Storage**: Automatically routes downloads into clean subfolders (`downloads/platform/category`) or a unified directory.
- 📂 **Built-in Media Manager**: Browse downloaded files with active cursor memory, play in the system default media player, or delete items with confirmation guards.
- 📦 **Bundled FFmpeg Runtime**: Uses `imageio-ffmpeg` static binaries — zero manual PATH setup or external FFmpeg installation required.
- 💻 **Cross-Platform Dual Launchers**: Native Windows launcher (`run.bat`) and universal POSIX Bash launchers (`dl.sh`, `yt.sh`) for Linux, macOS, WSL, and Git Bash.

---

## Directory Structure

```text
downloader/
├── run.bat                          # Windows CMD / PowerShell launcher
├── dl.sh                            # POSIX Bash launcher (Linux / macOS / WSL / Git Bash)
├── yt.sh                            # Backwards-compatible launcher alias
├── requirements.txt                 # Python dependencies (yt-dlp, imageio-ffmpeg, requests)
├── README.md                        # Documentation & CLI guide
├── .gitignore                       # Git ignore rules
│
├── config/                          # Persistent user preferences
│   └── config.json                  # Configuration file (JSON format)
│
├── downloads/                       # Destination for downloaded media
│   ├── youtube/                     # YouTube videos & audio
│   ├── x/                           # X / Twitter videos, GIFs, photos
│   ├── instagram/                   # Instagram Reels & photos
│   └── threads/                     # Threads videos & photos
│
└── src/                             # Modular application source code
    ├── __init__.py                  # Package marker
    ├── main.py                      # Main entrypoint & CLI dispatcher
    │
    ├── core/                        # Shared foundational engine
    │   ├── console.py               # VT100 ANSI, QuickEdit toggle, safe_input, key reader
    │   ├── config.py                # Configuration loader & persistent storage
    │   ├── i18n.py                  # Bilingual localization engine (Indonesian & English)
    │   ├── ffmpeg_engine.py         # Hardware GPU acceleration (NVENC), Bicubic scaler
    │   ├── progress.py              # Universal live progress bars & stream tracking
    │   └── file_manager.py          # File browser, default player launcher, safe deletion
    │
    ├── extractors/                  # Modular platform media extractors
    │   ├── base.py                  # BaseExtractor contract & MediaItem dataclass
    │   ├── youtube.py               # YouTube video, audio, playlist & upscale
    │   ├── twitter.py               # X / Twitter videos, GIFs, and photo galleries
    │   ├── instagram.py             # Instagram Reels, videos, and photo carousels
    │   └── threads.py               # Threads videos & photos
    │
    └── ui/                          # Modular Terminal UI views
        ├── menu.py                  # Interactive menu navigator with viewport pagination
        └── views/
            ├── main_menu.py         # Main navigation hub
            ├── smart_download.py    # Universal auto-detecting link downloader
            ├── youtube_view.py      # Dedicated YouTube menus & quality options
            ├── social_view.py       # X, Instagram & Threads interactive flows
            ├── settings_view.py     # Settings Hub (Video, Audio, Engine, Storage)
            └── manager_view.py      # Media manager & library browser
```

---

## Installation

### Prerequisites
- **Python 3.10+** installed on your system.

### Setup (Zero-Config)
Clone the repository and run immediately:

```bash
git clone https://github.com/bimbap/downloader.git
cd downloader
```

> 💡 **Auto-Setup / Zero-Config**: Launchers (`run.bat` and `dl.sh`) automatically detect and install missing dependencies (`yt-dlp`, `imageio-ffmpeg`, `requests`) on first run. You can also install them manually:
> ```bash
> pip install -r requirements.txt
> ```

---

## Quick Start

### 1. Interactive TUI Mode

#### Windows (CMD / PowerShell):
```powershell
.\run.bat
```

#### Linux / macOS / WSL / Git Bash:
```bash
./dl.sh
# or using the backwards-compatible alias:
./yt.sh
```

#### Python Direct:
```bash
python src/main.py
```

### 2. TUI Keyboard Controls

| Key | Action |
| :--- | :--- |
| `[↑]` / `[k]` | Move selection cursor up |
| `[↓]` / `[j]` | Move selection cursor down |
| `[1]` – `[9]` | Quick jump directly to numbered option |
| `[Enter]` / `[Space]` | Confirm / Select option |
| `[q]` / `[ESC]` | Return to previous menu / Exit |
| `[o]` | Open download destination folder in Explorer / Finder |
| `[p]` | Open/play downloaded media in default system player |

---

## Headless CLI Mode

Use `src/main.py` directly for scripts, automated jobs, and terminal power-users:

### 1. Universal Smart Download
```bash
# Auto-detects platform and downloads best available quality
python src/main.py "https://x.com/user/status/123456789"
python src/main.py "https://www.instagram.com/reel/C8..."
python src/main.py "https://www.threads.net/@user/post/C8..."
```

### 2. YouTube Specific Options
```bash
# Download 1080p MP4 with h264 codec
python src/main.py "https://youtu.be/dQw4w9WgXcQ" -r 1080 -c h264 --container mp4

# Download and upscale to 1440p (2K) via GPU Bicubic engine
python src/main.py "https://youtu.be/dQw4w9WgXcQ" -r 1440 -u

# Extract audio as 320 kbps MP3
python src/main.py "https://youtu.be/dQw4w9WgXcQ" -a --audio-format mp3 -b 320

# Download entire playlist
python src/main.py "https://www.youtube.com/playlist?list=PL..." -p
```

### 3. CLI Options Reference

| Flag | Long Option | Argument | Description |
| :--- | :--- | :--- | :--- |
| *(pos)* | `url` | `<URL>` | Media URL (YouTube, X, Instagram, Threads) |
| `-m` | `--mode` | `video`, `audio`, `mp3`, `m4a`, `opus`, `wav`, `best` | Download mode |
| `-a` | `--audio-only` | *(Flag)* | Download audio only |
| `-r` | `--resolution` | `4320`, `2160`, `1440`, `1080`, `720`, `480`, `360` | Video target resolution |
| `-c` | `--codec` | `h264`, `av1`, `vp9`, `auto` | Preferred video codec |
| | `--container` | `auto`, `mp4`, `webm`, `mkv` | Video container encapsulation |
| `-s` | `--style` | `basic`, `pretty`, `nerdy`, `classic` | Filename naming style |
| `-b` | `--audio-bitrate` | `320`, `256`, `192`, `128`, `96` | Audio bitrate in kbps |
| `-u` | `--force-upscale` | *(Flag)* | Enable GPU/FFmpeg Bicubic upscale if native < target |
| | `--no-force-upscale` | *(Flag)* | Disable upscale (native stream only) |
| `-o` | `--output` | `<path>` | Custom output directory path |
| `-p` | `--playlist` | *(Flag)* | Download entire playlist |

---

## Technical Highlights

1. **Clean Modular Architecture**:
   Completely separated core utilities (`src/core/`), platform extractors (`src/extractors/`), and user interface components (`src/ui/`), making adding new platforms trivial.
2. **Safe Atomic GPU Upscaling**:
   Hardware-accelerated Bicubic upscaling encodes to a hidden file (`.temp_upscale_<name>`) with live percentage/ETA progress and renames it atomically upon completion. If interrupted, the original downloaded file remains unharmed.
3. **Sliding-Window Viewport Pagination**:
   Terminal menus dynamically compute available rows to prevent vertical scrolling and eliminate ANSI header duplication.
4. **Cross-Platform Console Hardening**:
   Disables Windows QuickEdit to prevent window freezes and clipboard wipes, while re-enabling safe input prompts during link pasting.

---

## License

This project is open-source and intended for personal media downloading and archiving. Please respect the copyright and terms of service of any media content you download.
