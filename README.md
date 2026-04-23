# Video Enhancer for Mac

A simple, focused video enhancement app for **Apple Silicon Macs** (M1 / M2 / M3 / M4).
Wraps FFmpeg with a clean UI to apply a classic restoration pipeline to old or low-quality footage.

---

## Enhancement Pipeline

```
Input video
    │
    ▼
1. Deinterlace   — removes horizontal combing lines (for VHS / broadcast footage)
    │
    ▼
2. Denoise       — reduces film grain and digital noise (hqdn3d)
    │
    ▼
3. Upscale       — 1× / 2× / 4× with Lanczos / Bicubic / Bilinear
    │
    ▼
4. Sharpen       — unsharp mask to recover edge detail after upscaling
    │
    ▼
Output video (H.265 / H.264 / ProRes — hardware-encoded via VideoToolbox)
```

---

## Requirements

| Requirement | Version |
|---|---|
| macOS | Ventura 13+ recommended |
| Apple Silicon | M1 or newer |
| Python | 3.11+ |
| FFmpeg | Any recent Homebrew build |

---

## Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/video-enhancement-for-mac.git
cd video-enhancement-for-mac

# Run the one-time setup (installs FFmpeg via Homebrew + Python venv)
./install.sh
```

---

## Running

```bash
./run.sh
```

---

## Usage

1. Click **+ File** to add individual video files, or **+ Folder** to add all supported videos in a folder.
2. **Not sure what settings to use?** Click **Smart Recommend** at the top of the settings panel — answer 4 quick questions and settings are applied automatically.
3. Or configure the enhancement steps manually on the right panel — enable only what you need.
4. Choose an output codec and quality.
5. Click **Start Enhancement**. Files are processed one by one and saved to the `enhanced/` subfolder (or a custom folder).

### Smart Recommend

Click **Smart Recommend** in the settings panel to open a 4-step wizard:

| Step | Question | Affects |
|---|---|---|
| 1 | Video source (tape / DVD / digital) | Deinterlace, Denoise |
| 2 | Main goal (sharpen / denoise / upscale / all) | All filters |
| 3 | Output destination (streaming / archive / pro edit) | Codec, quality |
| 4 | Speed vs quality priority | Algorithm choices, sharpen amount |

After answering, click **Apply Settings** and all controls are updated automatically.

### Supported input formats

`.mp4`, `.mov`, `.avi`, `.mkv`, `.m4v`, `.wmv`, `.flv`, `.webm`, `.ts`, `.mts`, `.m2ts`

### Output formats

| Codec | Extension | Best for |
|---|---|---|
| H.265 HEVC (VideoToolbox) | `.mp4` | General use, best compression |
| H.264 (VideoToolbox) | `.mp4` | Max compatibility |
| ProRes 422 | `.mov` | Editing / post-production |
| H.264 (Software) | `.mp4` | When hardware encoder unavailable |

---

## Settings Reference

### Deinterlace
| Method | FFmpeg filter | Notes |
|---|---|---|
| yadif (Standard) | `yadif=mode=1` | Best balance |
| yadif bob (Smooth) | `yadif=mode=bob` | Doubles frame rate |
| bwdif (High Quality) | `bwdif=mode=1` | Best quality, slowest |

### Denoise (hqdn3d)
Strength 1–10. Higher = more aggressive noise removal.  
Recommended: 3–5 for moderate noise, 6–9 for heavy grain.

### Upscale
Uses bicubic/lanczos scaling. For AI upscaling, consider a separate tool and then run this app for noise/sharpen only.

### Sharpen (unsharp mask)
Amount 0.1–3.0. Recommended: 0.5–1.5 after upscaling.

### Quality slider
- VideoToolbox codecs: maps to `-q:v` (0 = best, 100 = lowest; slider is inverted to show higher = better)
- libx264: maps to CRF (higher slider = lower CRF = better quality)

---

## Tips

- **Old VHS / DVD**: Enable Deinterlace + Denoise (strength 5–7), Upscale 2×, Sharpen 0.8
- **Noisy digital video**: Denoise only (strength 3–5)
- **Blu-ray upscale**: Skip Deinterlace, Denoise 2–3, Upscale 2×, Sharpen 1.0
- **Archive to ProRes**: Disable upscale, use ProRes 422 codec, quality 80
- **Not sure?** Use **Smart Recommend** — just answer the wizard questions

---

## License

MIT
