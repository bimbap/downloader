# Universal Social Media Downloader

An ultra-fast, zero-lag interactive Terminal UI & CLI tool for downloading, converting, and upscaling media across **YouTube**, **X (formerly Twitter)**, **Instagram**, and **Threads**. Powered by Python 3, `yt-dlp`, `mutagen`, and bundled `imageio-ffmpeg`.

---

## Features

- ⚡ **Universal Smart Downloader**: Paste any link from YouTube, X, Instagram, or Threads. Automatically detects platform, media type, and best quality stream.
- 🚀 **Zero-Lag ANSI Terminal UI**: Smooth keyboard navigation (`↑/↓`, number jump `1-9`, `Enter`, `q`/`ESC`) with dynamic viewport pagination adapting to terminal height.
- 🔴 **YouTube Video & Playlists**: Up to 8K Ultra HD (`4320p`, `2160p`, `1440p`, `1080p`, etc.) or Auto Maximal (`best`). Supports full playlists with in-memory caching and multi-stream progress bars.
- 🎵 **Audio Extraction & Square Album Art**: Convert to MP3 (up to 320 kbps), M4A, Opus, or lossless WAV. Automatically crops 16:9 thumbnails to 1:1 square album art and embeds ID3 metadata.
- 📷 **X, Instagram & Threads**: High-res video reels, GIFs, and batch multi-photo carousel galleries.
- 🔍 **GPU Hardware Upscaling**: Upscale lower-resolution media to 2K, 4K, or 8K via NVIDIA NVENC, Intel QSV, AMD AMF, or CPU Bicubic scaling with atomic safe processing.
- 🍪 **Cookie Authentication**: Import session cookies from Chrome, Firefox, Edge, Brave, Opera, or Vivaldi for age-restricted (18+) or login-walled content.
- 🌐 **Bilingual (i18n)**: Instant switching between English 🇬🇧 and Bahasa Indonesia 🇮🇩.
- 💻 **Zero-Setup Launchers**: Native Windows launcher (`run.bat`) and POSIX launcher (`dl.sh`) with auto-install for dependencies.

---

## Quick Start

### 1. Launch Interactive TUI

```bash
# Windows (CMD / PowerShell):
.\run.bat

# Linux / macOS / WSL / Git Bash:
./dl.sh

# Or directly via Python:
python src/main.py
```

> 💡 **Auto-Setup**: Launchers automatically verify and install dependencies (`yt-dlp`, `imageio-ffmpeg`, `requests`, `mutagen`) on first run.

### 2. TUI Keyboard Shortcuts

| Key | Action | Key | Action |
| :--- | :--- | :--- | :--- |
| `↑` / `k` | Move cursor up | `Enter` / `Space` | Select / Confirm |
| `↓` / `j` | Move cursor down | `q` / `ESC` | Back / Cancel |
| `1` – `9` | Direct jump to option | `o` / `p` | Open folder / Play file |

---

## Headless CLI Usage

Run `src/main.py` directly for scripts, automated downloads, and CLI workflows:

```bash
# Universal auto-download (best quality)
python src/main.py "https://x.com/user/status/123456789"
python src/main.py "https://www.instagram.com/reel/C8..."
python src/main.py "https://www.threads.net/@user/post/C8..."

# YouTube 1080p MP4 (H.264)
python src/main.py "https://youtu.be/dQw4w9WgXcQ" -r 1080 -c h264 --container mp4

# YouTube Audio 320 kbps MP3 with album art
python src/main.py "https://youtu.be/dQw4w9WgXcQ" -a --audio-format mp3 -b 320

# Download and upscale to 1440p (2K) via GPU
python src/main.py "https://youtu.be/dQw4w9WgXcQ" -r 1440 -u

# Download entire YouTube playlist
python src/main.py "https://www.youtube.com/playlist?list=PL..." -p
```

### CLI Flags Reference

| Option | Flag | Values / Default | Description |
| :--- | :--- | :--- | :--- |
| `url` | *(pos)* | `<URL>` | Media URL to download |
| `--mode` | `-m` | `video`, `audio`, `mp3`, `m4a`, `opus`, `wav`, `best` | Target media mode |
| `--audio-only`| `-a` | *(flag)* | Download audio track only |
| `--resolution`| `-r` | `best`, `4320`, `2160`, `1440`, `1080`, `720`, `480`, `360` | Target resolution |
| `--codec` | `-c` | `h264`, `av1`, `vp9`, `auto` | Preferred video codec |
| `--container`| | `auto`, `mp4`, `webm`, `mkv` | Preferred video container |
| `--audio-format`| | `mp3`, `m4a`, `opus`, `wav`, `best` | Target audio format |
| `--audio-bitrate`| `-b`| `320`, `256`, `192`, `128`, `96` | Audio bitrate (kbps) |
| `--force-upscale`| `-u` | *(flag)* | Force GPU/Bicubic upscale |
| `--style` | `-s` | `basic`, `pretty`, `nerdy`, `classic` | Filename naming pattern |
| `--playlist` | `-p` | *(flag)* | Download entire playlist |
| `--output` | `-o` | `<path>` | Custom destination directory |

---

## Directory Structure

```text
downloader/
├── run.bat              # Native Windows launcher
├── dl.sh                # POSIX Bash launcher (Linux/macOS/WSL/Git Bash)
├── requirements.txt     # Python dependencies (yt-dlp, imageio-ffmpeg, requests, mutagen)
├── README.md            # Concise project documentation
├── docs/                # Authoritative engineering documentation
│   ├── PRD.md
│   ├── Architecture.md
│   ├── Design.md
│   └── Rules.md
├── downloads/           # Saved media organized by platform
│   ├── youtube/
│   ├── x/
│   ├── instagram/
│   └── threads/
└── src/
    ├── main.py          # Entrypoint & CLI dispatcher
    ├── core/            # Console VT100, Config, i18n, FFmpeg GPU, Progress, File Manager
    ├── extractors/      # YouTube, Twitter/X, Instagram, Threads extractors
    └── ui/              # Interactive menu engine & specialized views
```

---

## License

Personal and educational media downloading tool. Respect content creators' rights and platform terms of service.
