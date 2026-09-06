# Development Rules & Contributor Guidelines — Downloader

**Project:** Universal Social Media Downloader  
**Document:** Contributor & Agent Coding Rules  
**Version:** 2.1.0  
**Status:** Authoritative  

---

## 1. Absolute Golden Constraints (DO NOT BREAK)

### 1.1 Zero External PATH Dependencies
- **FFmpeg Runtime**: Never assume `ffmpeg` or `ffprobe` is installed on the user's system `PATH`. Always resolve the executable via `src.core.ffmpeg_engine.FFMPEG_EXE` (backed by bundled `imageio-ffmpeg`).
- **Python Standard Library First**: Avoid pulling heavy third-party packages for utilities. Keep dependencies strictly locked to `requirements.txt` (`yt-dlp`, `imageio-ffmpeg`, `requests`, `mutagen`).

### 1.2 Path Handling & Cross-Platform Integrity
- **Mandatory `pathlib.Path`**: Never concatenate filesystem paths with raw string formatting (`+` or `f"{a}/{b}"`). Always use `pathlib.Path` objects and the `/` operator.
- **Windows Backslash Resilience**: When passing paths to subprocesses or external tools, wrap paths with `str(path.resolve())` to guarantee valid Windows and POSIX path resolution.

### 1.3 Atomic File Handling & Process Safety
- **Hidden Temp Files**: In-place operations (such as GPU Bicubic upscaling or square thumbnail cropping) MUST write to a hidden temporary file first (e.g. `.temp_upscale_<name>` or `.sq.jpg`).
- **Interruption Guard**: Handle `KeyboardInterrupt` (`Ctrl+C`) gracefully. Always clean up temporary files in `finally:` blocks or exception handlers so interrupted downloads never leave corrupted artifacts.

### 1.4 Windows QuickEdit & Terminal Safety
- Do NOT use standard `input()` directly in interactive flows. Always use `safe_input()` from `src.core.console` to ensure QuickEdit mode is toggled cleanly and terminal cursor state is preserved.
- Always call `clear_screen()` when transitioning between distinct view flows.

---

## 2. Code Conventions & Architectural Standards

### 2.1 Extractor Architecture & Contracts
- **`BaseExtractor` Compliance**: Any new social media platform MUST implement `src.extractors.base.BaseExtractor` and return normalized `MediaItem` dataclass instances.
- **No Direct UI Imports in Extractors**: Platform extractors under `src/extractors/` must NOT import from `src/ui/`. They must remain headless, scriptable, and usable in isolation by `src/main.py`.

### 2.2 Localization (i18n) Rules
- **No Hardcoded UI Strings**: All user-facing prompt titles, error labels, and common buttons MUST use the `t("key")` translation lookup from `src.core.i18n`.
- **Bilingual Parity**: Whenever adding a new string key in `src/core/i18n.py`, provide both English (`en`) and Bahasa Indonesia (`id`) translations immediately.

### 2.3 Audio Tagging & Mutagen Usage
- Mutagen is required for embedding thumbnails in non-video containers (`.mp3`, `.m4a`, `.opus`, `.flac`).
- Always wrap post-processor embedding calls in `SafeEmbedThumbnailPP` to avoid failing the overall download flow if an individual stream has corrupt ID3 tags.

---

## 3. Launcher & Execution Constraints

### 3.1 Dual-Launcher Parity
The project maintains two official launchers:
1. `run.bat`: Windows CMD & PowerShell native launcher with polyglot Git Bash fallback.
2. `dl.sh`: POSIX Bash launcher for Linux, macOS, WSL, and Git Bash.

Whenever changing dependency detection or environment variables:
- Update BOTH `run.bat` and `dl.sh` simultaneously.
- Verify that dependency installation triggers automatically when running a fresh clone.

### 3.2 Windows Execution Quirk
When executing terminal commands via tools or agent sessions on Windows, always wrap execution with `cmd /c` (e.g. `cmd /c "python src/main.py --help"`).

---

## 4. Git & Commit Guidelines

- **Language**: All git commit messages, pull request titles, and engineering documentation MUST be written in professional **English**.
- **Conventional Commits**: Format commit messages using standard prefixes:
  - `feat:` for new capabilities, platforms, or format support.
  - `fix:` for bug fixes, glitch corrections, or edge-case handling.
  - `docs:` for documentation updates, PRDs, or architecture specs.
  - `refactor:` for code restructurings without behavior alterations.
  - `chore:` for dependency, launcher, or ignore maintenance.
