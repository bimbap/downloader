# System Architecture — Universal Social Media Downloader

**Project:** Universal Social Media Downloader  
**Document:** Technical Architecture & System Design  
**Status:** Authoritative  

---

## 1. High-Level Architecture Overview

The system is engineered around a clean, decoupled three-tier architecture:
1. **Presentation Tier (`src/ui/`)**: Interactive ANSI terminal views, dynamic viewport pagination, input parsers, and headless CLI dispatchers.
2. **Domain & Extraction Tier (`src/extractors/`)**: Modular platform extractors adhering to a strict `BaseExtractor` contract.
3. **Core Engine Tier (`src/core/`)**: Low-level terminal abstractions (ANSI, QuickEdit), FFmpeg hardware pipeline, download progress tracking, configuration management, and file operations.

```
┌─────────────────────────────────────────────────────────────┐
│                    Entrypoints & Launchers                  │
│               run.bat (Win)  |  dl.sh (POSIX)               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│    src/main.py (CLI Dispatcher)  |  src/ui/menu.py (TUI)    │
│    src/ui/views/ (smart_download, youtube, social, settings)│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   Extractor / Domain Layer                  │
│                     BaseExtractor Contract                  │
│  YouTubeExtractor │ TwitterExtractor │ Instagram │ Threads  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      Core Engine Layer                      │
│  console.py       │ ffmpeg_engine.py    │ progress.py       │
│  config.py        │ file_manager.py     │ i18n.py           │
│  yt-dlp wrapper   │ mutagen (ID3 tags)  │ imageio-ffmpeg    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Directory Layout & Module Responsibilities

```text
downloader/
├── config/
│   └── config.json           # User persistent preferences (JSON)
├── downloads/                # Media storage sorted by platform
├── src/
│   ├── main.py               # Main CLI dispatcher & argparse router
│   ├── core/
│   │   ├── config.py         # Persistent configuration and path resolver
│   │   ├── console.py        # ANSI VT100 colors, safe_input, key reader
│   │   ├── ffmpeg_engine.py  # FFmpeg resolver, GPU detection, upscaler, crop
│   │   ├── file_manager.py   # Directory browser, default app launcher, cleanup
│   │   ├── i18n.py           # Bilingual translation engine (en/id)
│   │   └── progress.py       # Dual-stream progress bars and download hooks
│   ├── extractors/
│   │   ├── base.py           # BaseExtractor contract and MediaItem dataclass
│   │   ├── instagram.py      # Instagram Reels, posts, carousel extractors
│   │   ├── threads.py        # Threads post and video extractors
│   │   ├── twitter.py        # X/Twitter video, GIF, photo gallery extractors
│   │   └── youtube.py        # YouTube video, audio, playlist extractor
│   └── ui/
│       ├── menu.py           # Interactive menu with dynamic viewport pagination
│       └── views/            # Specialized interactive view flows
```

---

## 3. Data Model & Extractor Contract

All platform extractors inherit from `BaseExtractor` and operate on standard `MediaItem` instances.

### `MediaItem` Dataclass
```python
@dataclass
class MediaItem:
    platform: str                    # 'youtube', 'twitter', 'instagram', 'threads'
    url: str                         # Normalized original URL
    title: str                       # Video title, post caption, or tweet text
    author: str                      # Channel name, creator username, or uploader
    media_type: str                  # 'video', 'audio', 'image', 'carousel', 'playlist'
    duration: float = 0.0            # Media duration in seconds (if applicable)
    items: list[dict] = field(default_factory=list)  # Sub-items (gallery photos or playlist tracks)
    raw_info: dict = field(default_factory=dict)     # Raw metadata payload from extractor
```

### `BaseExtractor` Contract
```python
class BaseExtractor(ABC):
    @classmethod
    @abstractmethod
    def is_suitable(cls, url: str) -> bool:
        """Determines if the given URL belongs to this extractor."""
        pass

    @abstractmethod
    def validate_url(self, url: str) -> tuple[bool, str, str]:
        """Validates and normalizes URL. Returns (is_valid, normalized_url, error_message)."""
        pass

    @abstractmethod
    def fetch_metadata(self, url: str) -> MediaItem | None:
        """Retrieves media metadata without initiating download."""
        pass

    @abstractmethod
    def download(self, item: MediaItem, options: dict[str, Any]) -> tuple[bool, list[Path]]:
        """Executes download and returns (success_flag, list_of_saved_file_paths)."""
        pass
```

---

## 4. Processing Pipeline

### Phase 1: Ingestion & URL Normalization
1. Raw URL is fed into `get_extractor_for_url(url)`.
2. Extractor checks regex suitability (`is_suitable`).
3. Extractor normalizes tracking query strings (e.g. `?igsh=`, `?s=`, `/share/` redirects).

### Phase 2: Metadata Extraction
1. Fast-path check: Light oEmbed or public HTTP inspection for instantaneous title resolution.
2. Deep extraction: Flat `yt-dlp` info extraction (with `skip_download=True`).
3. A `MediaItem` instance is constructed.

### Phase 3: Format & Option Resolution
1. Resolves default settings from `config.json` against user interactive picks or CLI arguments.
2. Configures `yt-dlp` download options (`ydl_opts`): output templates, progress hooks, cookie files, and post-processors.

### Phase 4: Download & Post-Processing Pipeline
```
[Raw Streams Download]
         │
         ▼
[FFmpegExtractAudio] (If Audio Mode: MP3, M4A, Opus, WAV)
         │
         ▼
[FFmpegSquareCropThumbnailPP] (If Music/Topic track: crop 16:9 to 1:1)
         │
         ▼
[SafeEmbedThumbnailPP] (Embed square thumbnail via mutagen)
         │
         ▼
[FFmpegUpscalePP] (If Video Mode & Upscale Enabled: GPU/Bicubic scale)
         │
         ▼
[Atomic File Move & Result Dispatch]
```

---

## 5. Subsystem Details

### 5.1 FFmpeg Engine (`core/ffmpeg_engine.py`)
- **Static Binary Resolution**: Directly utilizes `imageio_ffmpeg.get_ffmpeg_exe()`, providing a fully functional FFmpeg binary across platforms without modifying system `PATH`.
- **GPU Acceleration Detection**: Tests hardware capability at startup using probe commands:
  - NVIDIA: `h264_nvenc`
  - Intel: `h264_qsv`
  - AMD: `h264_amf`
  - Fallback: `libx264` (CPU Bicubic)
- **Atomic Scaling**: Encodes to `.temp_upscale_<name>` while streaming progress via FFmpeg `pipe:1` parsing `out_time_us` and `fps`. Atomically renames to target filename on exit.

### 5.2 Audio Tagging & Mutagen Pipeline
- Uses `yt-dlp`'s `FFmpegThumbnailsConvertor` to prepare `.jpg` covers.
- `FFmpegSquareCropThumbnailPP` intercepts thumbnails before embedding, executing `ffmpeg -i <thumb> -vf "crop=ih:ih" <cropped>` for Topic tracks.
- `SafeEmbedThumbnailPP` embeds cover art using `mutagen` without throwing exceptions if container limits are reached.

### 5.3 Viewport Pagination Engine (`ui/menu.py`)
- Dynamically queries terminal dimensions using `os.get_terminal_size()`.
- Computes visible row height (`visible_count = term_height - header_rows - footer_rows - padding`).
- Uses a sliding window algorithm (`top_idx` to `top_idx + visible_count`) to keep cursor centered, completely avoiding terminal scroll overflow.

### 5.4 Cross-Platform Polyglot Launchers
- **`run.bat`**: Windows batch file with a Bash polyglot header (`: << 'BATCH_OR_BASH'`). Runs in native CMD/PowerShell while cleanly delegating to `dl.sh` if invoked in Git Bash / MSYS2.
- **`dl.sh`**: POSIX-compliant Bash launcher detecting `python3`, `py`, or `python`, with automatic upfront dependency verification and installation.
