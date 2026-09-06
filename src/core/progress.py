# =============================================================================
# downloader/src/core/progress.py – Universal Live Progress Reporting
# =============================================================================
import sys
import time
from core.console import (
    BOLD_CYAN,
    BOLD_YELLOW,
    BOLD_GREEN,
    BOLD_RED,
    DIM,
    NC,
    CLEAR_LINE,
)


def create_ytdlp_progress_hook(media_title: str | None = None):
    """
    Creates a stateful yt-dlp progress hook with multi-stream tracking
    (distinct video stream, audio stream, and merge indicators).
    """
    state = {
        "current_title": None,
        "current_stream_type": None,
    }

    def hook(d):
        try:
            if d["status"] == "downloading":
                info = d.get("info_dict", {})
                raw_title = info.get("title") or media_title
                vcodec = info.get("vcodec")
                acodec = info.get("acodec")

                is_video_stream = bool(vcodec and vcodec != "none" and (not acodec or acodec == "none"))
                is_audio_stream = bool(acodec and acodec != "none" and (not vcodec or vcodec == "none"))

                stream_type = "video" if is_video_stream else ("audio" if is_audio_stream else "single")

                if raw_title and raw_title != state["current_title"]:
                    state["current_title"] = raw_title
                    state["current_stream_type"] = None
                    clean_title = (raw_title[:65] + "…") if len(raw_title) > 65 else raw_title
                    print(f"\n  {BOLD_CYAN} Downloading:{NC} {clean_title}")

                if stream_type != state["current_stream_type"]:
                    state["current_stream_type"] = stream_type
                    if is_video_stream:
                        res = info.get("resolution") or (f"{info.get('height')}p" if info.get("height") else "HD")
                        print(f"    {DIM}↳ Video Stream ({res})...{NC}")
                    elif is_audio_stream:
                        print(f"\n    {DIM}↳ Audio Stream (Source soundtrack)...{NC}")

                total = float(d.get("total_bytes") or d.get("total_bytes_estimate") or 0)
                downloaded = float(d.get("downloaded_bytes") or 0)
                speed = float(d.get("speed") or 0)

                eta_raw = d.get("eta")
                if eta_raw is not None:
                    try:
                        eta_sec = int(float(eta_raw))
                        eta_str = f"{eta_sec // 60:02d}:{eta_sec % 60:02d}" if eta_sec >= 60 else f"{eta_sec}s"
                    except Exception:
                        eta_str = f"{eta_raw}s"
                else:
                    eta_str = "--s"

                bar_len = 24
                if total > 0:
                    percent = min(100.0, max(0.0, (downloaded / total) * 100))
                    filled = max(0, min(bar_len, int(bar_len * (downloaded / total))))
                    bar = f"{BOLD_GREEN}{'█' * filled}{NC}{DIM}{'░' * (bar_len - filled)}{NC}"
                    total_mb = total / (1024 * 1024)
                    downloaded_mb = downloaded / (1024 * 1024)
                    speed_kb = speed / 1024
                    speed_str = f"{speed_kb / 1024:4.1f} MB/s" if speed_kb >= 1024 else f"{speed_kb:4.0f} KB/s"
                    sys.stdout.write(
                        f"\r  [{bar}] {BOLD_CYAN}{percent:5.1f}%{NC} | {downloaded_mb:5.1f}/{total_mb:5.1f} MB | {BOLD_YELLOW}{speed_str}{NC} | ETA: {eta_str:<5} {CLEAR_LINE}"
                    )
                    sys.stdout.flush()
                else:
                    downloaded_mb = downloaded / (1024 * 1024)
                    speed_kb = speed / 1024
                    speed_str = f"{speed_kb / 1024:4.1f} MB/s" if speed_kb >= 1024 else f"{speed_kb:4.0f} KB/s"
                    sys.stdout.write(
                        f"\r  [Downloading] {downloaded_mb:5.1f} MB | {BOLD_YELLOW}{speed_str}{NC} | ETA: {eta_str:<5} {CLEAR_LINE}"
                    )
                    sys.stdout.flush()

            elif d["status"] == "finished":
                info = d.get("info_dict", {})
                vcodec = info.get("vcodec")
                acodec = info.get("acodec")
                is_video_stream = bool(vcodec and vcodec != "none" and (not acodec or acodec == "none"))
                if is_video_stream:
                    print(f"\n    {BOLD_GREEN}✔ Video stream downloaded.{NC}")
                else:
                    print(f"\n    {BOLD_YELLOW}⚙ Merging streams with FFmpeg...{NC}")
        except Exception:
            pass

    return hook


def download_file_with_progress(url: str, output_path, headers: dict | None = None) -> bool:
    """Downloads a file directly via HTTP with live progress reporting."""
    import urllib.request
    from pathlib import Path

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    temp_p = out_p.with_name(f".temp_{out_p.name}")

    req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, headers=req_headers)
    bar_len = 24

    try:
        with urllib.request.urlopen(req, timeout=20) as resp, open(temp_p, "wb") as f:
            total_bytes = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            t_start = time.time()

            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                elapsed = max(0.01, time.time() - t_start)
                speed_kb = (downloaded / elapsed) / 1024
                speed_str = f"{speed_kb / 1024:4.1f} MB/s" if speed_kb >= 1024 else f"{speed_kb:4.0f} KB/s"

                if total_bytes > 0:
                    pct = min(100.0, (downloaded / total_bytes) * 100.0)
                    filled = max(0, min(bar_len, int(bar_len * (pct / 100.0))))
                    bar = f"{BOLD_GREEN}{'█' * filled}{NC}{DIM}{'░' * (bar_len - filled)}{NC}"
                    dl_mb = downloaded / (1024 * 1024)
                    tot_mb = total_bytes / (1024 * 1024)
                    sys.stdout.write(
                        f"\r  [{bar}] {BOLD_CYAN}{pct:5.1f}%{NC} | {dl_mb:5.1f}/{tot_mb:5.1f} MB | {BOLD_YELLOW}{speed_str}{NC} {CLEAR_LINE}"
                    )
                else:
                    dl_mb = downloaded / (1024 * 1024)
                    sys.stdout.write(
                        f"\r  [Downloading] {dl_mb:5.1f} MB | {BOLD_YELLOW}{speed_str}{NC} {CLEAR_LINE}"
                    )
                sys.stdout.flush()

        if temp_p.exists() and temp_p.stat().st_size > 0:
            if out_p.exists():
                out_p.unlink()
            temp_p.rename(out_p)
            sys.stdout.write(f"\r  {BOLD_GREEN}✔ Saved: {out_p.name}{NC} {CLEAR_LINE}\n")
            sys.stdout.flush()
            return True
        return False
    except Exception as e:
        if temp_p.exists():
            try:
                temp_p.unlink()
            except Exception:
                pass
        sys.stdout.write(f"\r  {BOLD_RED}✖ Download failed: {e}{NC} {CLEAR_LINE}\n")
        sys.stdout.flush()
        return False
