<p align="center">
  <img src="docs/assets/banner.svg" alt="Universal Social Media Downloader" width="100%" />
</p>
<!-- 
<h1 align="center">Universal Social Media Downloader</h1> -->

<p align="center">
  <strong>Zero-lag interactive Terminal UI &amp; headless CLI for YouTube, X (Twitter), Instagram, and Threads.</strong><br/>
  Powered by Python 3, <code>yt-dlp</code>, <code>mutagen</code>, and bundled <code>imageio-ffmpeg</code>.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-MIT-10B981?style=flat-square" alt="MIT License" />
  <img src="https://img.shields.io/badge/Interface-ANSI%20TUI%20%26%20CLI-06B6D4?style=flat-square" alt="ANSI TUI & CLI" />
  <img src="https://img.shields.io/badge/Platforms-YouTube%20%E2%80%A2%20X%20%E2%80%A2%20IG%20%E2%80%A2%20Threads-F59E0B?style=flat-square" alt="Platforms" />
</p>

---

## Features

- ⚡ **Single & Batch Smart Downloader**: Paste 1 link, multiple links (space/comma-separated), a `.txt` batch file, or type `batch` for multi-line input. Auto-detects platform and media type.
- 🚀 **Zero-Lag ANSI Terminal UI**: Smooth keyboard navigation (`↑/↓`, number jump `1-9`, `Enter`, `q`/`ESC`, `Ctrl+C` clean exit) inside an isolated Alternate Screen Buffer with zero scrollback clutter.
- 🔴 **YouTube Videos, Playlists & Community Posts**: Up to 8K (`4320p`, `2160p`, `1440p`, `1080p`, `best`), full playlists, plus YouTube Community Posts (`/post/` & `?lb=`) including attached videos, images, and post text.
- 🎵 **Audio Extraction & 1:1 Square Album Art**: Convert to MP3 (up to 320 kbps), M4A, Opus, WAV, or original stream (`best`). Automatically crops 16:9 Topic thumbnails to 1:1 square cover art and embeds ID3 metadata.
- 📷 **X, Instagram & Threads Carousels**: High-res `?name=orig` X photos (`FxTwitter` + `VxTwitter` fallback), Instagram Reels/carousels, and Threads `/share/` & multi-slide posts with selective slide picking.
- 📁 **Per-Link Bundle Folders & `caption.txt`**: Organizes each link cleanly into its own subfolder alongside `caption.txt` (with `[c] View Caption` in TUI and auto-cleanup of empty folders on delete).
- 🔍 **GPU Hardware Upscaling**: Upscale lower-resolution video to 2K, 4K, or 8K via NVIDIA NVENC, Intel QSV, AMD AMF, or CPU Bicubic scaling with atomic safe processing.
- 🍪 **Cookie Authentication**: Import session cookies from Chrome, Firefox, Edge, Brave, Opera, or Vivaldi for age-restricted (18+) or login-walled posts.
- 🌐 **Bilingual (i18n) & Zero-Setup Launchers**: Instant switching between English 🇬🇧 and Bahasa Indonesia 🇮🇩, with `run.bat` (Windows) and `dl.sh` (POSIX) auto-installing dependencies.

---

## Installation

Clone the repository and enter the directory:

```bash
git clone https://github.com/bimbap/downloader.git
cd downloader
```

> 💡 **Zero-Config Setup**: Launchers automatically verify and install all dependencies (`yt-dlp`, `imageio-ffmpeg`, `requests`, `mutagen`) on first run. You can also run `pip install -r requirements.txt` manually.

---

## How to Download

### Option 1: Interactive TUI (Recommended)

1. **Launch the App**:
   ```bash
   # Windows (CMD / PowerShell):
   .\run.bat

   # Linux / macOS / WSL / Git Bash:
   ./dl.sh
   ```
2. **Paste Media URL**: Select **`1. Universal Smart Download`** (or choose a specific platform) and paste your URL.
3. **Select Format & Quality**:
   - **Video**: Choose target resolution (Auto Maximal, 4K, 1080p, etc.) and preferred codec/container.
   - **Audio**: Choose MP3, M4A, Opus, or WAV (cover art is automatically cropped to 1:1 square).
4. **Done**: Downloaded files are saved to `downloads/<platform>/`. Press `[p]` to play immediately in your default player or `[o]` to open the destination folder!

#### TUI Keyboard Shortcuts

| Key | Action | Key | Action |
| :--- | :--- | :--- | :--- |
| `↑` / `k` | Move cursor up | `Enter` / `Space` | Select / Confirm |
| `↓` / `j` | Move cursor down | `q` / `ESC` / `Ctrl+C` | Back / Clean Exit |
| `1` – `9` | Direct jump to option | `o` / `p` / `c` | Open folder / Play / View caption |

---

### Option 2: Headless CLI (Fast & Scriptable)

Download media directly in one command without entering the interactive menu:

```bash
# Auto-detect platform and download best quality
python src/main.py "https://x.com/user/status/123456789"
python src/main.py "https://www.instagram.com/reel/C8..."
python src/main.py "https://www.threads.net/@user/post/C8..."

# YouTube: 1080p MP4 (H.264)
python src/main.py "https://youtu.be/dQw4w9WgXcQ" -r 1080 -c h264 --container mp4

# YouTube: 320 kbps MP3 with album art
python src/main.py "https://youtu.be/dQw4w9WgXcQ" -a --audio-format mp3 -b 320

# Download and upscale to 1440p (2K) via GPU
python src/main.py "https://youtu.be/dQw4w9WgXcQ" -r 1440 -u

# Download entire YouTube playlist
python src/main.py "https://www.youtube.com/playlist?list=PL..." -p

# Batch download multiple URLs or from a .txt file
python src/main.py "https://youtu.be/dQw4w9WgXcQ" "https://x.com/user/status/123456789"
python src/main.py -f urls.txt
```

#### CLI Flags Reference

| Option | Flag | Values / Default | Description |
| :--- | :--- | :--- | :--- |
| `urls` | *(pos)* | `<URL...>` | One or more media URLs to download |
| `--batch` | `-f` | `<path.txt>` | Text file containing URLs (one per line) |
| `--mode` | `-m` | `video`, `audio`, `mp3`, `m4a`, `opus`, `wav`, `best` | Target media mode |
| `--audio-only`| `-a` | *(flag)* | Download audio track only |
| `--resolution`| `-r` | `best`, `4320`, `2160`, `1440`, `1080`, `720`, `480`, `360` | Target resolution |
| `--codec` | `-c` | `h264`, `av1`, `vp9`, `auto` | Preferred video codec |
| `--container`| | `auto`, `mp4`, `webm`, `mkv` | Preferred video container |
| `--audio-format`| | `mp3`, `m4a`, `opus`, `wav`, `best` | Target audio format |
| `--audio-bitrate`| `-b`| `320`, `256`, `192`, `128`, `96` | Audio bitrate (kbps) |
| `--force-upscale`| `-u` | *(flag)* | Force GPU/Bicubic upscale |
| `--caption` / `--no-caption` | | *(flag)* | Save post caption as `caption.txt` (default: ON) |
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
│   ├── assets/          # Repository banner & visual assets
│   ├── PRD.md
│   ├── Architecture.md
│   ├── Design.md
│   └── Rules.md
├── downloads/           # Saved media organized by platform & category
│   ├── youtube/
│   ├── x/
│   ├── instagram/
│   └── threads/
└── src/
    ├── main.py          # Entrypoint & CLI dispatcher
    ├── core/            # Console, Config, Batch, i18n, FFmpeg GPU, Progress, File Manager
    ├── extractors/      # YouTube, Twitter/X, Instagram, Threads extractors
    └── ui/              # Interactive menu engine & specialized views
```

---

## License

This project is licensed under the MIT License. See [LICENSE.md](LICENSE.md) for details.
