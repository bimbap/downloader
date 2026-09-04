#!/usr/bin/env python3
# =============================================================================
# yt-downloader/src/downloader.py – Headless CLI Engine for YouTube Downloader
# =============================================================================
import argparse
import os
import sys
import subprocess
import re
import time
from pathlib import Path

# Ensure src directory is in path
SRC_DIR = Path(__file__).resolve().parent
BASE_DIR = SRC_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Force UTF-8 encoding on Windows to prevent cp1252 UnicodeEncodeError
for stream in (sys.stdout, sys.stderr, sys.stdin):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from config_helper import (
    load_config,
    save_config,
    get_download_path,
    get_outtmpl,
    resolve_video_container,
    get_video_format_selector,
    ensure_dependencies,
    validate_youtube_url,
    get_media_title,
)

ensure_dependencies()

try:
    import yt_dlp
except ImportError:
    print("Error: 'yt-dlp' library is not installed.")
    print("Run: pip install --user yt-dlp imageio-ffmpeg")
    sys.exit(1)

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = None

try:
    from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor
except ImportError:
    FFmpegPostProcessor = object


# ANSI Color Definitions
CYAN = "\033[36m"
BOLD_CYAN = "\033[1;36m"
YELLOW = "\033[33m"
BOLD_YELLOW = "\033[1;33m"
GREEN = "\033[32m"
BOLD_GREEN = "\033[1;32m"
RED = "\033[31m"
BOLD_RED = "\033[1;31m"
MAGENTA = "\033[35m"
BOLD_MAGENTA = "\033[1;35m"
DIM = "\033[2m"
BOLD = "\033[1m"
NC = "\033[0m"
CLEAR_LINE = "\033[K"

_ENCODER_CACHE = {}


def get_best_video_encoder(codec: str, ffmpeg_exe: str | None = None) -> tuple[str, list[str], str]:
    """Detects hardware acceleration for video encoding. Returns (encoder_name, flags, label)."""
    target_codec = (codec or "h264").lower()
    if target_codec in _ENCODER_CACHE:
        return _ENCODER_CACHE[target_codec]

    exe = ffmpeg_exe or FFMPEG_EXE or "ffmpeg"

    if target_codec in ("h264", "mp4"):
        candidates = [
            ("h264_nvenc", ["-preset", "p4", "-cq", "21"], "NVIDIA NVENC (GPU)"),
            ("h264_qsv", ["-global_quality", "21"], "Intel QSV (GPU)"),
            ("h264_amf", ["-rc", "cqp", "-qp_p", "21", "-qp_i", "21"], "AMD AMF (GPU)"),
        ]
        for enc, extra_args, label in candidates:
            try:
                res = subprocess.run(
                    [exe, "-f", "lavfi", "-i", "nullsrc=s=640x360:d=1", "-c:v", enc, "-f", "null", "-"],
                    capture_output=True,
                    timeout=3
                )
                if res.returncode == 0:
                    _ENCODER_CACHE[target_codec] = (enc, extra_args, label)
                    return _ENCODER_CACHE[target_codec]
            except Exception:
                pass
        _ENCODER_CACHE[target_codec] = ("libx264", ["-preset", "faster", "-crf", "21"], "libx264 (CPU)")
        return _ENCODER_CACHE[target_codec]

    elif target_codec in ("vp9", "webm"):
        _ENCODER_CACHE[target_codec] = (
            "libvpx-vp9",
            ["-b:v", "0", "-crf", "26", "-deadline", "good", "-cpu-used", "4"],
            "libvpx-vp9 (CPU)"
        )
        return _ENCODER_CACHE[target_codec]

    elif target_codec in ("hevc", "h265"):
        candidates = [
            ("hevc_nvenc", ["-preset", "p4", "-cq", "22"], "NVIDIA NVENC HEVC (GPU)"),
            ("hevc_qsv", ["-global_quality", "23"], "Intel QSV HEVC (GPU)"),
            ("hevc_amf", ["-rc", "cqp", "-qp_p", "22", "-qp_i", "22"], "AMD AMF HEVC (GPU)"),
        ]
        for enc, extra_args, label in candidates:
            try:
                res = subprocess.run(
                    [exe, "-f", "lavfi", "-i", "nullsrc=s=640x360:d=1", "-c:v", enc, "-f", "null", "-"],
                    capture_output=True,
                    timeout=3
                )
                if res.returncode == 0:
                    _ENCODER_CACHE[target_codec] = (enc, extra_args, label)
                    return _ENCODER_CACHE[target_codec]
            except Exception:
                pass
        _ENCODER_CACHE[target_codec] = ("libx265", ["-preset", "faster", "-crf", "22"], "libx265 (CPU)")
        return _ENCODER_CACHE[target_codec]

    _ENCODER_CACHE[target_codec] = ("libx264", ["-preset", "faster", "-crf", "20"], "libx264 (CPU)")
    return _ENCODER_CACHE[target_codec]


class FFmpegUpscalePP(FFmpegPostProcessor):
    """Post-processor that forces upscaling via FFmpeg with real-time streaming progress and GPU acceleration."""

    def __init__(self, downloader=None, target_height=None, codec="h264"):
        super().__init__(downloader)
        self.target_height = int(target_height) if target_height else None
        self.codec = codec or "h264"

    def run(self, info):
        if not self.target_height:
            return [], info

        orig_path = info.get("filepath")
        if not orig_path or not Path(orig_path).exists():
            return [], info

        orig_p = Path(orig_path)
        current_height = info.get("height")
        exe = FFMPEG_EXE or "ffmpeg"

        # Probe current resolution if not available in info
        if not current_height:
            try:
                probe = subprocess.run(
                    [exe, "-i", str(orig_p)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )
                m = re.search(r",\s*(\d{3,4})x(\d{3,4})", probe.stderr)
                if m:
                    current_height = int(m.group(2))
            except Exception:
                pass

        # Skip upscale if native height is already >= target
        if current_height and current_height >= self.target_height:
            print(f"    {DIM}↳ Native resolution ({current_height}p) already matches or exceeds target ({self.target_height}p). Upscale skipped.{NC}")
            return [], info

        curr_label = f"{current_height}p" if current_height else "Source"
        encoder, extra_args, enc_label = get_best_video_encoder(self.codec, exe)

        print(f"\n    {BOLD_CYAN}🚀 Upscaling Video ({curr_label} ➔ {self.target_height}p) via {enc_label}...{NC}")

        # Probe total duration in seconds
        total_duration = float(info.get("duration") or 0.0)
        if total_duration <= 0:
            try:
                probe = subprocess.run(
                    [exe, "-i", str(orig_p)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )
                m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", probe.stderr)
                if m:
                    total_duration = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
            except Exception:
                pass

        upscaled_path = orig_p.with_name(f".temp_upscale_{orig_p.stem}{orig_p.suffix}")
        if upscaled_path.exists():
            try:
                upscaled_path.unlink()
            except Exception:
                pass

        cmd = [
            exe, "-y",
            "-i", str(orig_p),
            "-vf", f"scale=-2:{self.target_height}:flags=bicubic",
            "-c:v", encoder,
            *extra_args,
            "-c:a", "copy",
            "-movflags", "+faststart",
            "-progress", "pipe:1",
            "-nostats",
            str(upscaled_path)
        ]

        bar_len = 24
        cur_sec = 0.0
        fps_str = "--"
        speed_str = "--x"
        proc = None

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                universal_newlines=True
            )

            for line in proc.stdout:
                line = line.strip()
                if not line or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k == "out_time_us":
                    try:
                        cur_sec = int(v) / 1_000_000
                    except ValueError:
                        pass
                elif k == "fps":
                    fps_str = v.split(".")[0]
                elif k == "speed":
                    speed_str = v.strip()
                elif k == "progress" and v in ("continue", "end"):
                    if total_duration > 0:
                        pct = min(100.0, (cur_sec / total_duration) * 100.0)
                        filled = max(0, min(bar_len, int(bar_len * (pct / 100.0))))
                        bar = f"{BOLD_GREEN}{'█' * filled}{NC}{DIM}{'░' * (bar_len - filled)}{NC}"
                        
                        try:
                            sp_val = float(speed_str.rstrip("x")) if speed_str != "--x" else 1.0
                            rem_sec = max(0, int((total_duration - cur_sec) / max(0.1, sp_val)))
                            eta_s = f"{rem_sec}s" if rem_sec < 60 else f"{rem_sec // 60}m {rem_sec % 60:02d}s"
                        except Exception:
                            eta_s = "--s"

                        cur_m, cur_s = int(cur_sec) // 60, int(cur_sec) % 60
                        tot_m, tot_s = int(total_duration) // 60, int(total_duration) % 60
                        time_str = f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}"

                        sys.stdout.write(
                            f"\r  [{bar}] {BOLD_CYAN}{pct:5.1f}%{NC} | {DIM}{time_str}{NC} | {BOLD_YELLOW}{fps_str} fps{NC} | Speed: {BOLD_YELLOW}{speed_str}{NC} | ETA: {eta_s:<6} {CLEAR_LINE}"
                        )
                        sys.stdout.flush()
                    else:
                        cur_m, cur_s = int(cur_sec) // 60, int(cur_sec) % 60
                        sys.stdout.write(
                            f"\r  [Upscaling] {cur_m:02d}:{cur_s:02d} | {BOLD_YELLOW}{fps_str} fps{NC} | Speed: {BOLD_YELLOW}{speed_str}{NC} {CLEAR_LINE}"
                        )
                        sys.stdout.flush()

            proc.wait()

            if proc.returncode != 0:
                # Hardware encoder might have failed mid-flight, attempt fallback to CPU libx264 if wasn't CPU already
                if encoder != "libx264":
                    print(f"\n    {BOLD_YELLOW}⚠ GPU encoder encountered an issue. Falling back to CPU (libx264)...{NC}")
                    cmd_fallback = [
                        exe, "-y",
                        "-i", str(orig_p),
                        "-vf", f"scale=-2:{self.target_height}:flags=bicubic",
                        "-c:v", "libx264",
                        "-preset", "faster",
                        "-crf", "21",
                        "-c:a", "copy",
                        "-movflags", "+faststart",
                        "-progress", "pipe:1",
                        "-nostats",
                        str(upscaled_path)
                    ]
                    proc = subprocess.Popen(
                        cmd_fallback,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        bufsize=1,
                        universal_newlines=True
                    )
                    for line in proc.stdout:
                        line = line.strip()
                        if not line or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        if k == "out_time_us":
                            try:
                                cur_sec = int(v) / 1_000_000
                            except ValueError:
                                pass
                        elif k == "fps":
                            fps_str = v.split(".")[0]
                        elif k == "speed":
                            speed_str = v.strip()
                        elif k == "progress" and v in ("continue", "end") and total_duration > 0:
                            pct = min(100.0, (cur_sec / total_duration) * 100.0)
                            filled = max(0, min(bar_len, int(bar_len * (pct / 100.0))))
                            bar = f"{BOLD_GREEN}{'█' * filled}{NC}{DIM}{'░' * (bar_len - filled)}{NC}"
                            cur_m, cur_s = int(cur_sec) // 60, int(cur_sec) % 60
                            tot_m, tot_s = int(total_duration) // 60, int(total_duration) % 60
                            time_str = f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d}"
                            sys.stdout.write(
                                f"\r  [{bar}] {BOLD_CYAN}{pct:5.1f}%{NC} | {DIM}{time_str}{NC} | {BOLD_YELLOW}{fps_str} fps{NC} | Speed: {BOLD_YELLOW}{speed_str}{NC} {CLEAR_LINE}"
                            )
                            sys.stdout.flush()
                    proc.wait()

            if proc.returncode == 0 and upscaled_path.exists() and upscaled_path.stat().st_size > 0:
                final_name = orig_p.name
                if current_height and f"({current_height}p)" in final_name:
                    final_name = final_name.replace(f"({current_height}p)", f"({self.target_height}p)")
                final_path = orig_p.with_name(final_name)

                for _ in range(5):
                    try:
                        if orig_p.exists() and orig_p != final_path:
                            orig_p.unlink()
                        if final_path.exists() and final_path != upscaled_path:
                            final_path.unlink()
                        upscaled_path.rename(final_path)
                        break
                    except PermissionError:
                        time.sleep(0.15)

                info["filepath"] = str(final_path)
                info["height"] = self.target_height
                if "__files_to_move" in info and orig_path in info["__files_to_move"]:
                    info["__files_to_move"][str(final_path)] = str(final_path)
                    del info["__files_to_move"][orig_path]
                print(f"\n    {BOLD_GREEN}✔ Upscale completed to {self.target_height}p ({final_path.name}){NC}")
            else:
                stderr_out = proc.stderr.read() if proc and proc.stderr else "Unknown error"
                print(f"\n    {BOLD_RED}✖ Upscale failed (FFmpeg exit code {proc.returncode}): {stderr_out.strip().splitlines()[-1] if stderr_out.strip() else 'Error'}{NC}")
                if upscaled_path.exists():
                    try:
                        upscaled_path.unlink()
                    except Exception:
                        pass
        except KeyboardInterrupt:
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
            if upscaled_path.exists():
                try:
                    upscaled_path.unlink()
                except Exception:
                    pass
            print(f"\n  {BOLD_YELLOW}⚠ Upscale cancelled by user.{NC}")
            raise
        except Exception as e:
            print(f"\n    {BOLD_RED}✖ Upscaling error: {e}{NC}")
            if upscaled_path.exists():
                try:
                    upscaled_path.unlink()
                except Exception:
                    pass

        return [], info


def progress_hook(d):
    try:
        if d['status'] == 'downloading':
            total = float(d.get('total_bytes') or d.get('total_bytes_estimate') or 0)
            downloaded = float(d.get('downloaded_bytes') or 0)
            speed = float(d.get('speed') or 0)

            eta_raw = d.get('eta')
            if eta_raw is not None:
                try:
                    eta_sec = int(float(eta_raw))
                    eta_str = f"{eta_sec // 60:02d}:{eta_sec % 60:02d}" if eta_sec >= 60 else f"{eta_sec}s"
                except Exception:
                    eta_str = f"{eta_raw}s"
            else:
                eta_str = "--s"

            if total > 0:
                percent = (downloaded / total) * 100
                total_mb = total / (1024 * 1024)
                downloaded_mb = downloaded / (1024 * 1024)
                speed_kb = speed / 1024
                sys.stdout.write(
                    f"\r[Downloading] {percent:5.1f}% | {downloaded_mb:6.1f}/{total_mb:6.1f} MB | {speed_kb:6.0f} KB/s | ETA: {eta_str}"
                )
                sys.stdout.flush()
            else:
                downloaded_mb = downloaded / (1024 * 1024)
                speed_kb = speed / 1024
                sys.stdout.write(
                    f"\r[Downloading] {downloaded_mb:6.1f} MB | {speed_kb:6.0f} KB/s | ETA: {eta_str}"
                )
                sys.stdout.flush()
        elif d['status'] == 'finished':
            print("\n[Processing] Download finished, finalizing file...")
    except Exception:
        pass


def build_ydl_opts(
    mode: str,
    resolution: str | None,
    output_dir: Path,
    filename_style: str = "basic",
    is_playlist: bool = False,
    video_codec: str | None = None,
    video_container: str | None = None,
    audio_format: str | None = None,
    audio_bitrate: str | None = None
):
    out_template = get_outtmpl(filename_style, mode, output_dir)

    ydl_opts = {
        "outtmpl": out_template,
        "progress_hooks": [progress_hook],
        "noplaylist": not is_playlist,
        "quiet": False,
        "no_warnings": False,
        "windowsfilenames": True,
        "restrictfilenames": False,
    }

    if FFMPEG_EXE:
        ydl_opts["ffmpeg_location"] = FFMPEG_EXE

    cfg = load_config()
    target_audio_fmt = audio_format or cfg.get("audio_format", "mp3")
    target_audio_br = str(audio_bitrate or cfg.get("audio_bitrate", "320"))

    is_audio_mode = mode in ("audio", "mp3", "m4a", "opus", "wav", "best")
    if is_audio_mode:
        actual_fmt = target_audio_fmt if mode == "audio" else mode
        if actual_fmt == "best":
            ydl_opts["format"] = "bestaudio/best"
        elif actual_fmt == "wav":
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                }],
            })
        else:  # mp3, m4a, opus
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": actual_fmt,
                    "preferredquality": target_audio_br,
                }],
            })
    else:  # video
        target_codec = video_codec or cfg.get("video_codec", "h264")
        target_container = video_container or cfg.get("video_container", "auto")
        effective_container = resolve_video_container(target_codec, target_container)
        format_str = get_video_format_selector(resolution, target_codec)

        ydl_opts.update({
            "format": format_str,
            "merge_output_format": effective_container,
        })

    return ydl_opts


def download_media(
    url: str,
    mode: str = "video",
    resolution: str | None = None,
    filename_style: str | None = None,
    output_dir: Path | None = None,
    is_playlist: bool = False,
    video_codec: str | None = None,
    video_container: str | None = None,
    audio_format: str | None = None,
    audio_bitrate: str | None = None,
    force_upscale: bool | None = None,
):
    is_valid, norm_url, reason = validate_youtube_url(url)
    if not is_valid:
        print(f"\n\033[1;31m✖ [ERROR] Invalid YouTube URL: {reason}\033[0m")
        print(f"\033[2mPlease provide a valid YouTube URL (e.g. https://www.youtube.com/watch?v=... or https://youtu.be/...)\033[0m\n")
        return
    url = norm_url

    cfg = load_config()
    style = filename_style or cfg.get("filename_style", "basic")

    if output_dir is None:
        output_dir = get_download_path(cfg.get("download_dir"))

    v_codec = video_codec or cfg.get("video_codec", "h264")
    v_container = video_container or cfg.get("video_container", "auto")
    eff_container = resolve_video_container(v_codec, v_container)
    a_fmt = audio_format or cfg.get("audio_format", "mp3")
    a_br = audio_bitrate or cfg.get("audio_bitrate", "320")
    is_upscale = force_upscale if force_upscale is not None else cfg.get("force_upscale", False)

    media_title = get_media_title(url)
    if media_title:
        print(f"\nMedia Title    : {media_title}")
        print(f"Target URL     : {url}")
    else:
        print(f"\nTarget URL     : {url}")
    if mode == "video":
        upscale_note = f" (Force Upscale: ON)" if (is_upscale and resolution) else ""
        print(f"Format         : VIDEO ({resolution or 'Best'}p | {v_codec.upper()} | {eff_container.upper()}){upscale_note}")
    else:
        print(f"Format         : AUDIO ({a_fmt.upper()} @ {a_br}k)")
    print(f"Filename Style : {style.upper()}")
    print(f"Output Dir     : {output_dir}")
    if FFMPEG_EXE:
        print(f"FFmpeg         : {FFMPEG_EXE}")
    else:
        print("FFmpeg         : Not detected")
    print("-" * 65)

    opts = build_ydl_opts(
        mode=mode,
        resolution=resolution,
        output_dir=output_dir,
        filename_style=style,
        is_playlist=is_playlist,
        video_codec=v_codec,
        video_container=v_container,
        audio_format=a_fmt,
        audio_bitrate=a_br,
    )

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            if is_upscale and mode == "video" and resolution and FFMPEG_EXE:
                ydl.add_post_processor(
                    FFmpegUpscalePP(ydl, target_height=resolution, codec=v_codec),
                    when="post_process"
                )
            ydl.download([url])
        print("\n[Success] Download completed successfully!")
        print(f"Saved in: {output_dir}")
    except Exception as err:
        print(f"\n[Error] Download failed: {err}")


def configure_settings():
    cfg = load_config()
    while True:
        eff_container = resolve_video_container(cfg.get("video_codec", "h264"), cfg.get("video_container", "auto"))
        print("\n" + "=" * 55)
        print("              PENGATURAN / CONFIGURATION")
        print("=" * 55)
        print(f"1. Filename Style     : [{cfg.get('filename_style', 'basic')}]")
        print(f"2. Video Quality Target: [{cfg.get('default_resolution', '1080')}p]")
        print(f"3. Preferred Codec    : [{cfg.get('video_codec', 'h264')}]")
        print(f"4. Video Container    : [{cfg.get('video_container', 'auto')} -> {eff_container}]")
        upscale_status = "ON (FFmpeg)" if cfg.get("force_upscale", False) else "OFF"
        print(f"5. Audio Format       : [{cfg.get('audio_format', 'mp3')}]")
        print(f"6. Audio Bitrate      : [{cfg.get('audio_bitrate', '320')} kbps]")
        print(f"7. Force Upscale Video: [{upscale_status}]")
        print("8. Kembali ke Menu Utama")

        choice = input("\nPilih opsi (1-8): ").strip()
        if choice == "1":
            print("\nPilih Filename Style:")
            print("1. basic   (Title - Author)")
            print("2. pretty  (Title - Author (youtube))")
            print("3. nerdy   (Title - Author (youtube, id))")
            print("4. classic (youtube_id_res)")
            s_choice = input("Pilihan (1-4): ").strip()
            style_map = {"1": "basic", "2": "pretty", "3": "nerdy", "4": "classic"}
            if s_choice in style_map:
                cfg["filename_style"] = style_map[s_choice]
                save_config(cfg)
                print(f"[OK] Filename style diubah ke: {cfg['filename_style']}")
        elif choice == "2":
            res = input("Masukkan default resolution (4320, 2160, 1440, 1080, 720, 480, 360, 240, 144): ").strip()
            if res in ["4320", "2160", "1440", "1080", "720", "480", "360", "240", "144"]:
                cfg["default_resolution"] = res
                save_config(cfg)
                print(f"[OK] Default resolution diubah ke: {res}p")
            else:
                print("Resolusi tidak valid.")
        elif choice == "3":
            print("\nPilih Preferred Video Codec:")
            print("1. h264 (H.264 + AAC - Best compatibility, max 1080p)")
            print("2. av1  (AV1 + Opus - Best quality & efficiency, 8K & HDR)")
            print("3. vp9  (VP9 + Opus - High quality, supports 4K & HDR)")
            print("4. auto (Auto stream selection)")
            c_choice = input("Pilihan (1-4): ").strip()
            c_map = {"1": "h264", "2": "av1", "3": "vp9", "4": "auto"}
            if c_choice in c_map:
                cfg["video_codec"] = c_map[c_choice]
                save_config(cfg)
                print(f"[OK] Video codec diubah ke: {cfg['video_codec']}")
        elif choice == "4":
            print("\nPilih Video Container:")
            print("1. auto (Auto: mp4 for h264, webm for vp9/av1)")
            print("2. mp4  (Universal MP4)")
            print("3. webm (WebM open media)")
            print("4. mkv  (Matroska flexible container)")
            cnt_choice = input("Pilihan (1-4): ").strip()
            cnt_map = {"1": "auto", "2": "mp4", "3": "webm", "4": "mkv"}
            if cnt_choice in cnt_map:
                cfg["video_container"] = cnt_map[cnt_choice]
                save_config(cfg)
                print(f"[OK] Video container diubah ke: {cfg['video_container']}")
        elif choice == "5":
            print("\nPilih Audio Format:")
            print("1. mp3  (MPEG Layer-3 / Universal)")
            print("2. m4a  (AAC Audio / Apple & Mobile)")
            print("3. opus (Opus / High Efficiency)")
            print("4. wav  (Lossless Uncompressed PCM)")
            print("5. best (Original Stream / No Conversion)")
            a_choice = input("Pilihan (1-5): ").strip()
            a_map = {"1": "mp3", "2": "m4a", "3": "opus", "4": "wav", "5": "best"}
            if a_choice in a_map:
                cfg["audio_format"] = a_map[a_choice]
                save_config(cfg)
                print(f"[OK] Audio format diubah ke: {cfg['audio_format']}")
        elif choice == "6":
            br = input("Masukkan audio bitrate (320, 256, 192, 128, 96): ").strip()
            if br in ["320", "256", "192", "128", "96"]:
                cfg["audio_bitrate"] = br
                save_config(cfg)
                print(f"[OK] Audio bitrate diubah ke: {br} kbps")
            else:
                print("Bitrate tidak valid.")
        elif choice == "7":
            cfg["force_upscale"] = not cfg.get("force_upscale", False)
            save_config(cfg)
            new_st = "ON" if cfg["force_upscale"] else "OFF"
            print(f"[OK] Force Upscale diubah ke: {new_st}")
        elif choice == "8":
            break


def interactive_mode():
    cfg = load_config()
    print("=" * 65)
    print("                 YOUTUBE DOWNLOADER")
    print(f"   Style: [{cfg.get('filename_style', 'basic')}] | Res: [{cfg.get('default_resolution', '1080')}p] | Codec: [{cfg.get('video_codec', 'h264')}]")
    print("=" * 65)

    print("Ketik 's' atau 'settings' untuk buka menu konfigurasi style.")
    url = input("Masukkan Link YouTube: ").strip()
    if not url:
        print("URL tidak boleh kosong!")
        return

    if url.lower() in ("s", "settings", "config"):
        configure_settings()
        return

    is_playlist_url = "list=" in url
    is_playlist = False
    if is_playlist_url:
        ans = input("Link terdeteksi sebagai Playlist. Download seluruh playlist? (y/N): ").strip().lower()
        is_playlist = (ans == "y")

    default_res = cfg.get("default_resolution", "1080")

    print("\nPilih Format:")
    print(f"1. Video - Kualitas Tertinggi (Original / 4K / 2K)")
    print(f"2. Video - 1080p (FHD) [Rekomendasi]")
    print(f"3. Video - 720p (HD)")
    print(f"4. Video - 480p (SD)")
    print(f"5. Audio Configured ({cfg.get('audio_format', 'mp3').upper()} @ {cfg.get('audio_bitrate', '320')}k)")
    print(f"6. Audio M4A (Original stream / Cepat)")

    choice = input("\nPilihan kamu (1-6) [Default: 2]: ").strip() or "2"

    mode = "video"
    resolution = default_res

    if choice == "1":
        mode = "video"
        resolution = None
    elif choice == "2":
        mode = "video"
        resolution = "1080"
    elif choice == "3":
        mode = "video"
        resolution = "720"
    elif choice == "4":
        mode = "video"
        resolution = "480"
    elif choice == "5":
        mode = "audio"
        resolution = None
    elif choice == "6":
        mode = "m4a"
        resolution = None

    download_media(
        url=url,
        mode=mode,
        resolution=resolution,
        filename_style=cfg.get("filename_style", "basic"),
        is_playlist=is_playlist
    )


def main():
    cfg = load_config()
    parser = argparse.ArgumentParser(description="Download YouTube videos or audio using yt-dlp with customizable filenames.")
    parser.add_argument("url", nargs="?", help="YouTube video or playlist URL")
    parser.add_argument("-f", "--format", choices=["video", "audio", "mp3", "m4a", "opus", "wav", "best"], default=None, help="Output format type")
    parser.add_argument("-r", "--res", choices=["4320", "2160", "1440", "1080", "720", "480", "360", "240", "144"], default=None, help="Video resolution limit")
    parser.add_argument("-c", "--codec", choices=["h264", "av1", "vp9", "auto"], default=None, help="Preferred video codec")
    parser.add_argument("--container", choices=["auto", "mp4", "webm", "mkv"], default=None, help="Video file container")
    parser.add_argument("-s", "--style", choices=["classic", "basic", "pretty", "nerdy"], default=None, help="Filename style")
    parser.add_argument("-b", "--bitrate", choices=["320", "256", "192", "128", "96"], default=None, help="Audio bitrate in kbps")
    parser.add_argument("-u", "--force-upscale", action="store_true", default=None, help="Force FFmpeg upscale if native video is lower than target resolution")
    parser.add_argument("--no-force-upscale", dest="force_upscale", action="store_false", help="Disable video upscaling (native stream only)")
    parser.add_argument("-o", "--output", help="Custom output directory")
    parser.add_argument("-p", "--playlist", action="store_true", help="Download whole playlist if present")
    parser.add_argument("--config", action="store_true", help="Open configuration settings")

    args = parser.parse_args()

    if args.config:
        configure_settings()
        return

    if not args.url:
        try:
            from tui import run_tui
            run_tui()
        except KeyboardInterrupt:
            pass
    else:
        is_valid, norm_url, reason = validate_youtube_url(args.url)
        if not is_valid:
            print(f"\n\033[1;31m✖ [ERROR] Invalid YouTube URL: {reason}\033[0m")
            print(f"\033[2mPlease provide a valid YouTube URL (e.g. https://www.youtube.com/watch?v=... or https://youtu.be/...)\033[0m\n")
            sys.exit(1)
        args.url = norm_url

        mode = args.format or "video"
        out_path = Path(args.output).resolve() if args.output else None
        download_media(
            url=args.url,
            mode=mode,
            resolution=args.res or cfg.get("default_resolution", "1080"),
            filename_style=args.style or cfg.get("filename_style", "basic"),
            output_dir=out_path,
            is_playlist=args.playlist,
            video_codec=args.codec,
            video_container=args.container,
            audio_format=args.format if args.format in ("mp3", "m4a", "opus", "wav", "best") else None,
            audio_bitrate=args.bitrate,
            force_upscale=args.force_upscale,
        )


if __name__ == "__main__":
    main()

