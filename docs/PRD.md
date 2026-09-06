# Product Requirements Document (PRD) — Universal Social Media Downloader

**Project:** Universal Social Media Downloader (CLI & TUI)  
**Version:** 2.1.0  
**Status:** Active / Production-Ready  
**Language:** Python 3.10+  
**Target Platforms:** Windows 10/11, macOS, Linux, WSL, Git Bash  

---

## 1. Executive Summary & Vision

The **Universal Social Media Downloader** is a unified, zero-lag media ingestion, conversion, and hardware-upscaling application designed to download audio, video, animated GIFs, and photo carousels from mainstream social media platforms (**YouTube**, **X / Twitter**, **Instagram**, **Meta Threads**).

It bridges the gap between raw CLI tools (like `yt-dlp` and `ffmpeg`) and bloated GUI downloaders by providing:
1. An **ultra-responsive ANSI VT100 interactive Terminal User Interface (TUI)** with dynamic viewport pagination and keyboard navigation.
2. A **scriptable, headless Command-Line Interface (CLI)** for automation, webhooks, and power users.
3. An **embedded, self-contained runtime** utilizing `imageio-ffmpeg` static binaries to eliminate external dependency installation.

---

## 2. Problem Statement

Existing media download solutions suffer from distinct shortcomings:
- **Web-based converters**: Filled with intrusive ads, privacy risks, bandwidth throttling, and frequent domain takedowns.
- **Raw CLI tools (`yt-dlp`)**: Powerful but verbose, requiring extensive command-line argument memorization for everyday operations (e.g., choosing codecs, extracting audio, cropping square album art, or handling playlists).
- **Desktop GUI apps**: Heavy resource usage (Electron-based), sluggish start times, and rigid interfaces lacking headless automation capabilities.
- **Missing Hardware Upscaling**: Downloaders pull native streams as-is; users seeking higher resolutions for legacy or low-res clips must run secondary editing software.

---

## 3. Platform & Media Feature Matrix

| Platform | Supported Formats | Specific Capabilities |
| :--- | :--- | :--- |
| **YouTube** | Videos (up to 8K), Shorts, Audio (MP3, M4A, Opus, WAV), Playlists | Multi-stream video/audio muxing, custom resolution selection (8K to 360p), Auto Maximal (`best`), square album art cropping, ID3 tag embedding, playlist in-memory caching. |
| **X (Twitter)** | Videos, Animated GIFs, Multi-photo galleries | Highest-bitrate MP4 selection, original photo resolution (`:orig`), batch gallery downloader. |
| **Instagram** | Reels, Video posts, Carousel slide decks, Single photos | High-res MP4 reel/video extraction, multi-slide carousel extraction with full or selective slide downloading. |
| **Meta Threads** | Videos, Single photos, Carousel galleries | Supports web posts and `/share/` redirect links with tracking parameter normalization. |

---

## 4. Key Functional Requirements

### 4.1 Universal Smart Link Ingestion
- Accepts any raw URL via interactive input or positional CLI argument.
- Normalizes URL variants (mobile `m.`, shortlinks `youtu.be`, `/shorts/`, `/reel/`, `/share/` redirects, tracking query strings like `?igsh=...`, `?t=...`, `?s=...`).
- Automatically routes the URL to the matching platform extractor with zero user configuration.

### 4.2 Interactive Zero-Lag Terminal UI (TUI)
- ANSI VT100 / Xterm-compliant terminal rendering.
- Complete keyboard-driven navigation (`↑/k`, `↓/j`, numeric direct jump `1-9`, `Enter`/`Space`, `q`/`ESC`).
- **Dynamic Viewport Pagination**: Adapts menu lists to the current terminal height dynamically to prevent scroll overflow, cursor jump, and duplicate headers.
- Real-time multi-stream progress bars tracking download speed (MB/s), percentage, and ETA.

### 4.3 Audio Transcoding & Square Album Art Embedding
- Converts audio into user-specified formats: MP3 (up to 320 kbps), M4A (AAC), Opus, lossless WAV, or preserves raw best stream.
- **Auto Square Thumbnail (1:1)**: For Music and Topic tracks, crops 16:9 YouTube thumbnails to pure 1:1 square album art via FFmpeg, removing black letterbox/pillarbox bars.
- Injects comprehensive ID3 / container metadata (Title, Artist/Uploader, Album, Cover Art) using `mutagen`.

### 4.4 GPU Hardware-Accelerated Upscaling Engine
- Supports upscaling native video streams to target heights: 1440p (2K), 2160p (4K), and 4320p (8K).
- Autodetects hardware GPU acceleration (NVIDIA NVENC `h264_nvenc`, Intel QSV `h264_qsv`, AMD AMF `h264_amf`) with automated fallback to CPU Bicubic scaling (`libx264`).
- Atomic processing: Writes to temporary hidden files (`.temp_upscale_<name>`) and swaps on successful completion, protecting the original download if cancelled.

### 4.5 Media Manager & Built-in File Browser
- In-terminal file navigator for `downloads/` directory.
- Instant preview/launch via system default media player (`start`, `open`, or `xdg-open`).
- Safe deletion with interactive confirmation guards.

### 4.6 Browser Cookie Integration
- Authenticates requests using local browser session cookies (Chrome, Firefox, Edge, Brave, Opera, Vivaldi).
- Bypasses age-restricted YouTube videos (18+) and login-restricted Instagram/X posts.

### 4.7 Internationalization (i18n)
- Runtime language switching between English 🇬🇧 and Bahasa Indonesia 🇮🇩 without application restarts.

---

## 5. Non-Functional Requirements

1. **Zero External Runtime Installation**: Bundles FFmpeg via `imageio-ffmpeg` static binaries. Does not require FFmpeg on system `PATH`.
2. **Launch Performance**: Cold start TUI launch time under 300ms.
3. **Terminal Safety**: Suppresses Windows console QuickEdit mode to prevent accidental terminal freezes while maintaining seamless clipboard paste functionality.
4. **Cross-Platform Launcher Parity**: Identical launcher behavior across Windows (`run.bat`) and POSIX Bash (`dl.sh`).
5. **Data Resilience**: Atomic writes, temporary cleanup routines (`.part`, `.ytdl`, `.tmp`), and zero unhandled crash loops.
