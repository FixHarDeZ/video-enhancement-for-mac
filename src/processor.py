"""FFmpeg-based video enhancement processor for Apple Silicon."""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path
from typing import Callable, Optional


def get_video_info(input_path: str) -> dict:
    """Return basic video metadata via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}

    info: dict = {}
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            info["width"] = stream.get("width", 0)
            info["height"] = stream.get("height", 0)

            r_frame_rate = stream.get("r_frame_rate", "25/1")
            try:
                num, den = r_frame_rate.split("/")
                info["fps"] = int(num) / max(int(den), 1)
            except Exception:
                info["fps"] = 25.0

            duration = 0.0
            try:
                duration = float(stream.get("duration", 0) or 0)
            except (ValueError, TypeError):
                pass
            if not duration:
                try:
                    duration = float(data.get("format", {}).get("duration", 0) or 0)
                except (ValueError, TypeError):
                    pass

            info["duration"] = duration

            nb_frames = stream.get("nb_frames")
            if nb_frames and nb_frames != "N/A":
                try:
                    info["total_frames"] = int(nb_frames)
                except (ValueError, TypeError):
                    info["total_frames"] = int(duration * info["fps"]) if duration else 0
            else:
                info["total_frames"] = int(duration * info["fps"]) if duration else 0
            break

    return info


# ---------------------------------------------------------------------------
# Filter chain building
# ---------------------------------------------------------------------------

_DEINTERLACE_MAP = {
    "yadif": "yadif=mode=1",
    "yadif_bob": "yadif=mode=bob",
    "bwdif": "bwdif=mode=1",
}

_SCALE_ALGO_MAP = {
    "lanczos": "lanczos",
    "bicubic": "bicubic",
    "bilinear": "bilinear",
}


def build_filter_chain(settings: dict) -> Optional[str]:
    """Build the -vf filter string from user settings."""
    filters: list[str] = []

    if settings.get("deinterlace"):
        method = settings.get("deinterlace_method", "yadif")
        filters.append(_DEINTERLACE_MAP.get(method, "yadif=mode=1"))

    if settings.get("denoise"):
        # ponytail: gentler than ffmpeg's hqdn3d default (4:3:6:4.5). High
        # temporal denoise smears detail/ghosts motion — clean source ends up
        # softer than the original. Keep temporal <= spatial.
        s = float(settings.get("denoise_strength", 2.0))
        ls = round(s, 1)
        cs = round(s * 0.75, 1)
        lt = round(s * 1.0, 1)
        ct = round(s * 0.75, 1)
        filters.append(f"hqdn3d={ls}:{cs}:{lt}:{ct}")

    upscale = settings.get("upscale", "1x")
    if upscale != "1x":
        # ponytail: interpolation only — adds pixels, not real detail. Not an
        # ML upscaler. Real detail recovery would need Real-ESRGAN/etc.
        factor = int(upscale[0])
        algo = _SCALE_ALGO_MAP.get(settings.get("upscale_algo", "lanczos"), "lanczos")
        filters.append(f"scale=iw*{factor}:ih*{factor}:flags={algo}")

    if settings.get("sharpen"):
        # ponytail: smaller 3x3 radius + low default — 5x5 with amount>=1.0
        # rings/halos, esp. stacked after denoise ("waxy" look).
        amount = round(float(settings.get("sharpen_amount", 0.5)), 1)
        filters.append(f"unsharp=3:3:{amount}:3:3:0.0")

    return ",".join(filters) if filters else None


# ---------------------------------------------------------------------------
# FFmpeg command building
# ---------------------------------------------------------------------------

def build_ffmpeg_command(input_path: str, output_path: str, settings: dict) -> list[str]:
    """Return the full ffmpeg argument list for the given settings."""
    cmd = ["ffmpeg", "-y", "-i", input_path]

    vf = build_filter_chain(settings)
    if vf:
        cmd += ["-vf", vf]

    codec = settings.get("codec", "hevc_videotoolbox")
    cmd += ["-c:v", codec]

    if "videotoolbox" in codec:
        # yuv420p required; allow_sw lets VT fall back instead of silently dropping video
        cmd += ["-pix_fmt", "yuv420p", "-allow_sw", "1"]
        # ponytail: VT -q:v is constant-quality (higher = better). 65 bands on
        # clean source; 80 is a sane floor before re-encode loss shows.
        quality = max(0, min(100, int(settings.get("quality", 80))))
        cmd += ["-q:v", str(quality)]
        if "hevc" in codec:
            cmd += ["-tag:v", "hvc1"]  # QuickTime requires hvc1, not hev1
    elif codec == "libx264":
        # Convert 0-100 quality → CRF 51-0 (higher quality = lower CRF)
        crf = max(0, 51 - int(settings.get("quality", 65) * 51 / 100))
        cmd += ["-crf", str(crf), "-preset", "slow"]
    elif codec == "prores_ks":
        cmd += ["-profile:v", "2"]  # ProRes 422

    cmd += ["-c:a", "copy"]
    cmd += ["-progress", "pipe:1", "-nostats"]
    cmd.append(output_path)
    return cmd


def preview_command(input_path: str, output_path: str, settings: dict) -> str:
    """Return a human-readable version of the ffmpeg command."""
    return " ".join(build_ffmpeg_command(input_path, output_path, settings))


# ---------------------------------------------------------------------------
# Processor
# ---------------------------------------------------------------------------

ProgressCallback = Callable[[float, str], None]


class VideoProcessor:
    """Thread-safe wrapper around FFmpeg subprocess."""

    def __init__(self) -> None:
        self._process: Optional[subprocess.Popen] = None
        self._cancelled = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            if self._process:
                self._process.terminate()

    # ------------------------------------------------------------------
    def process(
        self,
        input_path: str,
        output_path: str,
        settings: dict,
        on_progress: ProgressCallback,
    ) -> tuple[bool, str]:
        """
        Run FFmpeg synchronously (blocking). Returns (success, message).
        Call from a background thread; use on_progress to push updates to the UI.
        """
        with self._lock:
            self._cancelled = False

        info = get_video_info(input_path)
        total_frames = info.get("total_frames", 0)

        cmd = build_ffmpeg_command(input_path, output_path, settings)

        try:
            with self._lock:
                if self._cancelled:
                    return False, "Cancelled before start"
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )

            # Drain stderr in background so the pipe doesn't block
            stderr_lines: list[str] = []

            def _read_stderr() -> None:
                assert self._process is not None
                for line in self._process.stderr:
                    stderr_lines.append(line)

            stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
            stderr_thread.start()

            # Read stdout for -progress pipe:1 key=value pairs
            assert self._process is not None
            for line in self._process.stdout:
                with self._lock:
                    if self._cancelled:
                        break
                line = line.strip()
                if line.startswith("frame="):
                    try:
                        frame = int(line.split("=", 1)[1])
                        if frame > total_frames:
                            total_frames = frame + 1
                        if total_frames > 0:
                            progress = min(frame / total_frames, 0.99)
                            on_progress(progress, f"Frame {frame}/{total_frames}")
                        else:
                            on_progress(0.5, f"Frame {frame}")
                    except (ValueError, IndexError):
                        pass

            self._process.wait()
            stderr_thread.join(timeout=3)

            returncode = self._process.returncode

            with self._lock:
                self._process = None
                cancelled = self._cancelled

            if cancelled:
                Path(output_path).unlink(missing_ok=True)
                return False, "Cancelled"

            if returncode == 0:
                probe = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-show_streams",
                     "-select_streams", "v", output_path],
                    capture_output=True, text=True,
                )
                if "codec_name" not in probe.stdout:
                    stderr_text = "".join(stderr_lines)
                    return False, f"Output has no video stream.\n\nFFmpeg log:\n{stderr_text[-800:]}"
                return True, "Done"

            error = "".join(stderr_lines[-30:]) if stderr_lines else "Unknown error"
            return False, f"FFmpeg exited {returncode}: {error[-400:]}"

        except Exception as exc:
            with self._lock:
                self._process = None
            return False, str(exc)
