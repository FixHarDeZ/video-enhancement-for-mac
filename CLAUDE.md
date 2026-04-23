# Video Enhancer for Mac — Claude Guide

## Project Overview

A desktop video enhancement app built in Python (customtkinter) targeting Apple Silicon Macs.
Runs FFmpeg under the hood with a 4-step pipeline: Deinterlace → Denoise → Upscale → Sharpen.

## File Structure

```
.
├── src/
│   ├── __init__.py
│   ├── main.py         # Entry point + platform check
│   ├── app.py          # customtkinter UI (VideoEnhancerApp)
│   └── processor.py    # FFmpeg subprocess wrapper + filter builder
├── install.sh          # One-time setup (Homebrew + venv + deps)
├── run.sh              # Launch the app
├── requirements.txt    # Python deps (customtkinter, Pillow)
├── pyproject.toml      # Project metadata
├── CLAUDE.md           # This file
└── README.md
```

## Architecture

### `src/processor.py`
- `get_video_info(path)` — ffprobe → dict with fps, duration, total_frames
- `build_filter_chain(settings)` — assembles -vf string from user settings
- `build_ffmpeg_command(in, out, settings)` — full ffmpeg argv list
- `VideoProcessor` — thread-safe class wrapping FFmpeg subprocess
  - `.process(in, out, settings, on_progress)` — blocking, call from worker thread
  - `.cancel()` — terminates ffmpeg, deletes partial output

### `src/app.py`
- Single `VideoEnhancerApp(ctk.CTk)` class
- UI updates from worker thread MUST go through `self.after(0, ...)` 
- `_run_queue()` is the worker thread function; it calls `processor.process()` per file

### Enhancement pipeline (FFmpeg filter chain order)
1. **Deinterlace** — `yadif=mode=1` / `yadif=mode=bob` / `bwdif=mode=1`
2. **Denoise** — `hqdn3d=ls:cs:lt:ct` (strength 1–10)
3. **Upscale** — `scale=iw*N:ih*N:flags=algo`
4. **Sharpen** — `unsharp=5:5:amount:5:5:0.0`

### Codec mapping
| UI label | FFmpeg codec | Notes |
|---|---|---|
| H.265 HEVC (VideoToolbox) | `hevc_videotoolbox` | Hardware, M-series default |
| H.264 (VideoToolbox) | `h264_videotoolbox` | Hardware |
| ProRes 422 | `prores_ks -profile:v 2` | Post-production |
| H.264 Software | `libx264 -preset slow` | Fallback |

Quality slider (0–100) maps to `-q:v` for VideoToolbox codecs and to CRF for libx264.

## Development

```bash
# First-time setup
./install.sh

# Run
./run.sh

# Run directly (with venv active)
python -m src.main
```

## Dependencies

- Python ≥ 3.11
- FFmpeg (with VideoToolbox support) — install via `brew install ffmpeg`
- `customtkinter` ≥ 5.2.2
- `Pillow` ≥ 10.0.0

## Version

Version string lives in `src/app.py` as `VERSION = "x.y.z"`. Update this before each release. The release skill (`/release`) will prompt you to bump it.

## Release Process

Use the `/release` skill (`.claude/skills/release.md`) to:
1. Bump the version in `src/app.py`
2. Commit all staged changes
3. Tag the release
4. Push tag to remote
