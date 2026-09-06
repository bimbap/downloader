# =============================================================================
# downloader/src/core/ffmpeg_engine.py – Hardware-Accelerated FFmpeg Engine
# =============================================================================
import os
import sys
import subprocess
import re
import time
from pathlib import Path

from core.console import (
    BOLD_CYAN,
    BOLD_YELLOW,
    BOLD_GREEN,
    BOLD_RED,
    DIM,
    NC,
    CLEAR_LINE,
)

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = None

try:
    from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor
except ImportError:
    FFmpegPostProcessor = object

_ENCODER_CACHE = {}


def get_best_video_encoder(codec: str, ffmpeg_exe: str | None = None) -> tuple[str, list[str], str]:
    """
    Detects hardware acceleration for video encoding.
    Returns (encoder_name, extra_flags, display_label).
    """
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

    _ENCODER_CACHE[target_codec] = ("libx264", ["-preset", "faster", "-crf", "21"], "libx264 (CPU)")
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
                print(f"\n    {BOLD_RED}✖ Upscale failed (FFmpeg exit code {proc.returncode}){NC}")
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
