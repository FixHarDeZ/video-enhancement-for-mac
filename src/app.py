"""Main application window for Video Enhancer (Apple Silicon)."""

from __future__ import annotations

import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.processor import VideoProcessor, build_ffmpeg_command, get_video_info

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

SUPPORTED_EXT = {
    ".mp4", ".mov", ".avi", ".mkv", ".m4v",
    ".wmv", ".flv", ".webm", ".ts", ".mts", ".m2ts",
}

VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_size(path: Path) -> str:
    try:
        mb = path.stat().st_size / 1_048_576
        return f"{mb:.1f} MB"
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class VideoEnhancerApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Video Enhancer  v{VERSION}")
        self.geometry("1000x720")
        self.minsize(860, 640)

        self.processor = VideoProcessor()
        self.file_queue: list[Path] = []
        self.is_processing = False

        self._build_ui()
        self._check_ffmpeg()

    # -----------------------------------------------------------------------
    # Dependency check
    # -----------------------------------------------------------------------

    def _check_ffmpeg(self) -> None:
        missing = []
        for tool in ("ffmpeg", "ffprobe"):
            try:
                subprocess.run([tool, "-version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing.append(tool)
        if missing:
            messagebox.showerror(
                "Missing Dependencies",
                f"Required tool(s) not found: {', '.join(missing)}\n\n"
                "Install via Homebrew:\n"
                "  brew install ffmpeg\n\n"
                "Then restart the app.",
            )

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(1, weight=1)

        # ── Header ──────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(18, 4))

        ctk.CTkLabel(
            header, text="Video Enhancer",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(side="left")
        ctk.CTkLabel(
            header, text="for Apple Silicon",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        ).pack(side="left", padx=(10, 0), pady=(5, 0))

        # appearance toggle
        ctk.CTkOptionMenu(
            header,
            values=["System", "Dark", "Light"],
            width=100, height=28,
            command=lambda m: ctk.set_appearance_mode(m),
        ).pack(side="right")

        # ── Left: file panel ─────────────────────────────────────────────
        self._build_file_panel()

        # ── Right: settings panel ────────────────────────────────────────
        self._build_settings_panel()

        # ── Bottom: progress + controls ──────────────────────────────────
        self._build_bottom_panel()

    # -----------------------------------------------------------------------

    def _build_file_panel(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=1, column=0, sticky="nsew", padx=(20, 8), pady=8)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # header row
        hdr = ctk.CTkFrame(frame, fg_color="transparent")
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 6))

        ctk.CTkLabel(hdr, text="Queue", font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")

        btn_row = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_row.pack(side="right")
        ctk.CTkButton(btn_row, text="+ File",   width=72, height=28, command=self._add_files).pack(side="left", padx=(0, 4))
        ctk.CTkButton(btn_row, text="+ Folder", width=80, height=28, command=self._add_folder).pack(side="left", padx=(0, 4))
        ctk.CTkButton(btn_row, text="Clear",    width=60, height=28,
                      fg_color="transparent", border_width=1,
                      command=self._clear_files).pack(side="left")

        # count label
        self._count_lbl = ctk.CTkLabel(frame, text="No files added", text_color="gray",
                                       font=ctk.CTkFont(size=11))
        self._count_lbl.grid(row=1, column=0, columnspan=2, sticky="w", padx=14)

        # Listbox
        lb_frame = ctk.CTkFrame(frame, fg_color="transparent")
        lb_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=12, pady=6)
        lb_frame.grid_rowconfigure(0, weight=1)
        lb_frame.grid_columnconfigure(0, weight=1)

        self._listbox = tk.Listbox(
            lb_frame,
            selectmode=tk.EXTENDED,
            font=("Menlo", 11),
            activestyle="none",
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self._listbox.grid(row=0, column=0, sticky="nsew")
        self._apply_listbox_theme()

        sb = ctk.CTkScrollbar(lb_frame, command=self._listbox.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._listbox.configure(yscrollcommand=sb.set)

        # Remove button
        ctk.CTkButton(
            frame, text="Remove Selected", height=28,
            fg_color="transparent", border_width=1,
            command=self._remove_selected,
        ).grid(row=3, column=0, columnspan=2, padx=12, pady=(0, 12))

    # -----------------------------------------------------------------------

    def _apply_listbox_theme(self) -> None:
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            self._listbox.configure(bg="#1e1e1e", fg="#e0e0e0", selectbackground="#1F6AA5", selectforeground="white")
        else:
            self._listbox.configure(bg="#f5f5f5", fg="#111111", selectbackground="#3B8ED0", selectforeground="white")

    # -----------------------------------------------------------------------

    def _build_settings_panel(self) -> None:
        outer = ctk.CTkScrollableFrame(self, label_text="Enhancement Settings",
                                       label_font=ctk.CTkFont(size=14, weight="bold"))
        outer.grid(row=1, column=1, sticky="nsew", padx=(8, 20), pady=8)
        outer.grid_columnconfigure(0, weight=1)

        pad = {"padx": 12, "pady": 6}

        # ── 1. Deinterlace ──────────────────────────────────────────────
        s1 = self._section(outer, "1  Deinterlace")
        s1.grid(row=0, column=0, sticky="ew", **pad)

        self._deint_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(s1, text="Enable  (remove interlace combing from old footage)",
                        variable=self._deint_var,
                        command=self._sync_deint).pack(anchor="w", padx=12, pady=(10, 4))

        row = ctk.CTkFrame(s1, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(row, text="Method:", width=72).pack(side="left")
        self._deint_method = ctk.CTkOptionMenu(
            row,
            values=["yadif  (Standard)", "yadif bob  (Smooth)", "bwdif  (High Quality)"],
            width=220,
        )
        self._deint_method.pack(side="left", padx=6)
        self._deint_method.set("yadif  (Standard)")
        self._sync_deint()

        # ── 2. Denoise ──────────────────────────────────────────────────
        s2 = self._section(outer, "2  Denoise")
        s2.grid(row=1, column=0, sticky="ew", **pad)

        self._denoise_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(s2, text="Enable  (reduce film grain / digital noise)",
                        variable=self._denoise_var,
                        command=self._sync_denoise).pack(anchor="w", padx=12, pady=(10, 4))

        self._denoise_row = ctk.CTkFrame(s2, fg_color="transparent")
        self._denoise_row.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(self._denoise_row, text="Strength:", width=72).pack(side="left")
        self._denoise_str = ctk.DoubleVar(value=4.0)
        ctk.CTkSlider(self._denoise_row, from_=1, to=10,
                      variable=self._denoise_str, width=160).pack(side="left", padx=6)
        self._denoise_lbl = ctk.CTkLabel(self._denoise_row, text="4.0", width=36)
        self._denoise_lbl.pack(side="left")
        self._denoise_str.trace_add("write", lambda *_: self._denoise_lbl.configure(
            text=f"{self._denoise_str.get():.1f}"))
        self._sync_denoise()

        # ── 3. Upscale ──────────────────────────────────────────────────
        s3 = self._section(outer, "3  Upscale")
        s3.grid(row=2, column=0, sticky="ew", **pad)

        row3a = ctk.CTkFrame(s3, fg_color="transparent")
        row3a.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(row3a, text="Scale:", width=72).pack(side="left")
        self._scale_var = ctk.StringVar(value="1×  (Original)")
        ctk.CTkOptionMenu(
            row3a,
            values=["1×  (Original)", "2×  Upscale", "4×  Upscale"],
            variable=self._scale_var,
            width=180,
        ).pack(side="left", padx=6)

        row3b = ctk.CTkFrame(s3, fg_color="transparent")
        row3b.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(row3b, text="Algorithm:", width=72).pack(side="left")
        self._algo_var = ctk.StringVar(value="Lanczos  (Best)")
        ctk.CTkOptionMenu(
            row3b,
            values=["Lanczos  (Best)", "Bicubic  (Fast)", "Bilinear  (Fastest)"],
            variable=self._algo_var,
            width=180,
        ).pack(side="left", padx=6)

        # ── 4. Sharpen ──────────────────────────────────────────────────
        s4 = self._section(outer, "4  Sharpen")
        s4.grid(row=3, column=0, sticky="ew", **pad)

        self._sharp_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(s4, text="Enable sharpening",
                        variable=self._sharp_var,
                        command=self._sync_sharp).pack(anchor="w", padx=12, pady=(10, 4))

        self._sharp_row = ctk.CTkFrame(s4, fg_color="transparent")
        self._sharp_row.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(self._sharp_row, text="Amount:", width=72).pack(side="left")
        self._sharp_amt = ctk.DoubleVar(value=1.0)
        ctk.CTkSlider(self._sharp_row, from_=0.1, to=3.0,
                      variable=self._sharp_amt, width=160).pack(side="left", padx=6)
        self._sharp_lbl = ctk.CTkLabel(self._sharp_row, text="1.0", width=36)
        self._sharp_lbl.pack(side="left")
        self._sharp_amt.trace_add("write", lambda *_: self._sharp_lbl.configure(
            text=f"{self._sharp_amt.get():.1f}"))
        self._sync_sharp()

        # ── Output Settings ──────────────────────────────────────────────
        s5 = self._section(outer, "Output Settings")
        s5.grid(row=4, column=0, sticky="ew", **pad)

        # Codec
        rc = ctk.CTkFrame(s5, fg_color="transparent")
        rc.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(rc, text="Codec:", width=72).pack(side="left")
        self._codec_var = ctk.StringVar(value="H.265 HEVC  (VideoToolbox)")
        ctk.CTkOptionMenu(
            rc,
            values=[
                "H.265 HEVC  (VideoToolbox)",
                "H.264  (VideoToolbox)",
                "ProRes 422",
                "H.264  (Software / libx264)",
            ],
            variable=self._codec_var,
            width=240,
        ).pack(side="left", padx=6)

        # Quality
        rq = ctk.CTkFrame(s5, fg_color="transparent")
        rq.pack(fill="x", padx=12, pady=(0, 4))
        ctk.CTkLabel(rq, text="Quality:", width=72).pack(side="left")
        self._quality_var = ctk.IntVar(value=65)
        ctk.CTkSlider(rq, from_=0, to=100, variable=self._quality_var, width=160).pack(side="left", padx=6)
        self._quality_lbl = ctk.CTkLabel(rq, text="65", width=36)
        self._quality_lbl.pack(side="left")
        self._quality_var.trace_add("write", lambda *_: self._quality_lbl.configure(
            text=str(self._quality_var.get())))

        # Output folder
        ro = ctk.CTkFrame(s5, fg_color="transparent")
        ro.pack(fill="x", padx=12, pady=(0, 4))
        ctk.CTkLabel(ro, text="Output:", width=72).pack(side="left")
        self._out_folder = ctk.StringVar(value="Same folder  (enhanced/)")
        ctk.CTkEntry(ro, textvariable=self._out_folder, width=190).pack(side="left", padx=6)
        ctk.CTkButton(ro, text="Browse", width=70, height=28,
                      command=self._browse_output).pack(side="left")

        # Suffix
        rs = ctk.CTkFrame(s5, fg_color="transparent")
        rs.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkLabel(rs, text="Suffix:", width=72).pack(side="left")
        self._suffix_var = ctk.StringVar(value="_enhanced")
        ctk.CTkEntry(rs, textvariable=self._suffix_var, width=120).pack(side="left", padx=6)

        # Show command button
        ctk.CTkButton(
            outer, text="Preview FFmpeg Command",
            height=30, fg_color="transparent", border_width=1,
            command=self._show_command,
        ).grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 8))

    # -----------------------------------------------------------------------

    def _build_bottom_panel(self) -> None:
        bar = ctk.CTkFrame(self)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 16))
        bar.grid_columnconfigure(1, weight=1)

        self._start_btn = ctk.CTkButton(
            bar, text="  Start Enhancement",
            width=200, height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._toggle_processing,
        )
        self._start_btn.grid(row=0, column=0, padx=16, pady=14)

        prog_box = ctk.CTkFrame(bar, fg_color="transparent")
        prog_box.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=14)
        prog_box.grid_columnconfigure(0, weight=1)

        self._status_lbl = ctk.CTkLabel(prog_box, text="Ready", anchor="w",
                                        font=ctk.CTkFont(size=12))
        self._status_lbl.grid(row=0, column=0, sticky="ew")

        self._progress = ctk.CTkProgressBar(prog_box)
        self._progress.grid(row=1, column=0, sticky="ew", pady=(4, 4))
        self._progress.set(0)

        self._sub_lbl = ctk.CTkLabel(prog_box, text="", anchor="w",
                                     font=ctk.CTkFont(size=11), text_color="gray")
        self._sub_lbl.grid(row=2, column=0, sticky="ew")

    # -----------------------------------------------------------------------
    # Section helper
    # -----------------------------------------------------------------------

    @staticmethod
    def _section(parent: ctk.CTkScrollableFrame, title: str) -> ctk.CTkFrame:
        f = ctk.CTkFrame(parent)
        ctk.CTkLabel(f, text=title,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkFrame(f, height=1, fg_color="gray40").pack(fill="x", padx=12)
        return f

    # -----------------------------------------------------------------------
    # State sync helpers
    # -----------------------------------------------------------------------

    def _sync_deint(self) -> None:
        state = "normal" if self._deint_var.get() else "disabled"
        self._deint_method.configure(state=state)

    def _sync_denoise(self) -> None:
        enabled = self._denoise_var.get()
        for w in self._denoise_row.winfo_children():
            try:
                w.configure(state="normal" if enabled else "disabled")
            except Exception:
                pass

    def _sync_sharp(self) -> None:
        enabled = self._sharp_var.get()
        for w in self._sharp_row.winfo_children():
            try:
                w.configure(state="normal" if enabled else "disabled")
            except Exception:
                pass

    # -----------------------------------------------------------------------
    # File management
    # -----------------------------------------------------------------------

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=[
                ("Video files",
                 "*.mp4 *.mov *.avi *.mkv *.m4v *.wmv *.flv *.webm *.ts *.mts *.m2ts"),
                ("All files", "*.*"),
            ],
        )
        for p in paths:
            path = Path(p)
            if path not in self.file_queue:
                self.file_queue.append(path)
        self._refresh_list()

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select Folder with Videos")
        if not folder:
            return
        for ext in SUPPORTED_EXT:
            for f in Path(folder).glob(f"*{ext}"):
                if f not in self.file_queue:
                    self.file_queue.append(f)
            for f in Path(folder).glob(f"*{ext.upper()}"):
                if f not in self.file_queue:
                    self.file_queue.append(f)
        self._refresh_list()

    def _clear_files(self) -> None:
        self.file_queue.clear()
        self._refresh_list()

    def _remove_selected(self) -> None:
        for i in sorted(self._listbox.curselection(), reverse=True):
            del self.file_queue[i]
        self._refresh_list()

    def _refresh_list(self) -> None:
        self._listbox.delete(0, tk.END)
        for path in self.file_queue:
            size = _fmt_size(path)
            label = f"  {path.name}"
            if size:
                label += f"  [{size}]"
            self._listbox.insert(tk.END, label)
        n = len(self.file_queue)
        self._count_lbl.configure(
            text=f"{n} file{'s' if n != 1 else ''} queued" if n else "No files added"
        )

    def _browse_output(self) -> None:
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self._out_folder.set(folder)

    # -----------------------------------------------------------------------
    # Settings extraction
    # -----------------------------------------------------------------------

    _CODEC_MAP = {
        "H.265 HEVC  (VideoToolbox)": "hevc_videotoolbox",
        "H.264  (VideoToolbox)":      "h264_videotoolbox",
        "ProRes 422":                 "prores_ks",
        "H.264  (Software / libx264)": "libx264",
    }
    _DEINT_MAP = {
        "yadif  (Standard)":    "yadif",
        "yadif bob  (Smooth)":  "yadif_bob",
        "bwdif  (High Quality)": "bwdif",
    }
    _ALGO_MAP = {
        "Lanczos  (Best)":    "lanczos",
        "Bicubic  (Fast)":    "bicubic",
        "Bilinear  (Fastest)": "bilinear",
    }
    _SCALE_MAP = {
        "1×  (Original)": "1x",
        "2×  Upscale":    "2x",
        "4×  Upscale":    "4x",
    }

    def _get_settings(self) -> dict:
        return {
            "deinterlace":        self._deint_var.get(),
            "deinterlace_method": self._DEINT_MAP.get(self._deint_method.get(), "yadif"),
            "denoise":            self._denoise_var.get(),
            "denoise_strength":   self._denoise_str.get(),
            "upscale":            self._SCALE_MAP.get(self._scale_var.get(), "1x"),
            "upscale_algo":       self._ALGO_MAP.get(self._algo_var.get(), "lanczos"),
            "sharpen":            self._sharp_var.get(),
            "sharpen_amount":     self._sharp_amt.get(),
            "codec":              self._CODEC_MAP.get(self._codec_var.get(), "hevc_videotoolbox"),
            "quality":            self._quality_var.get(),
            "output_folder":      self._out_folder.get(),
            "suffix":             self._suffix_var.get(),
        }

    def _get_output_path(self, src: Path, settings: dict) -> Path:
        folder_str = settings["output_folder"]
        suffix = settings["suffix"] or "_enhanced"

        if folder_str == "Same folder  (enhanced/)":
            out_dir = src.parent / "enhanced"
        else:
            out_dir = Path(folder_str)

        out_dir.mkdir(parents=True, exist_ok=True)

        codec = settings["codec"]
        ext = ".mov" if "prores" in codec else ".mp4"
        return out_dir / (src.stem + suffix + ext)

    # -----------------------------------------------------------------------
    # Preview command dialog
    # -----------------------------------------------------------------------

    def _show_command(self) -> None:
        if not self.file_queue:
            messagebox.showinfo("Preview Command", "Add at least one file first.")
            return
        settings = self._get_settings()
        src = self.file_queue[0]
        out = self._get_output_path(src, settings)
        cmd = " \\\n  ".join(["ffmpeg"] + [
            f'"{a}"' if (" " in a or "/" in a) else a
            for a in build_ffmpeg_command(str(src), str(out), settings)[1:]
        ])
        dlg = ctk.CTkToplevel(self)
        dlg.title("FFmpeg Command Preview")
        dlg.geometry("700x260")
        dlg.grab_set()
        tb = ctk.CTkTextbox(dlg, font=("Menlo", 11), wrap="word")
        tb.pack(fill="both", expand=True, padx=16, pady=16)
        tb.insert("1.0", cmd)
        tb.configure(state="disabled")

    # -----------------------------------------------------------------------
    # Processing
    # -----------------------------------------------------------------------

    def _toggle_processing(self) -> None:
        if self.is_processing:
            self.processor.cancel()
            self.is_processing = False
            self._set_start_idle()
        else:
            self._start_processing()

    def _start_processing(self) -> None:
        if not self.file_queue:
            messagebox.showwarning("No Files", "Add at least one video file to the queue.")
            return
        self.is_processing = True
        self._start_btn.configure(text="  Cancel", fg_color="#c0392b", hover_color="#922b21")
        threading.Thread(target=self._run_queue, daemon=True).start()

    def _set_start_idle(self) -> None:
        self._start_btn.configure(
            text="  Start Enhancement",
            fg_color=["#3B8ED0", "#1F6AA5"],
            hover_color=["#36719F", "#144870"],
        )

    def _run_queue(self) -> None:
        settings = self._get_settings()
        total = len(self.file_queue)

        for idx, src in enumerate(self.file_queue):
            if not self.is_processing:
                break

            out = self._get_output_path(src, settings)
            self._ui_status(f"[{idx+1}/{total}]  {src.name}")
            self._ui_sub(f"→ {out}")
            self._ui_progress(idx / total)

            def on_progress(p: float, msg: str, i: int = idx) -> None:
                self._ui_progress((i + p) / total)
                self._ui_status(f"[{i+1}/{total}]  {src.name}  —  {msg}")

            ok, msg = self.processor.process(str(src), str(out), settings, on_progress)

            if not ok and self.is_processing:
                self._ui_status(f"Error on {src.name}")
                self.after(0, lambda m=msg, n=src.name: messagebox.showerror(
                    f"Error — {n}", m))

        if self.is_processing:
            self._ui_progress(1.0)
            self._ui_status(f"Done!  {total} file{'s' if total > 1 else ''} processed.")
            self._ui_sub("")

        self.is_processing = False
        self.after(0, self._set_start_idle)

    # -----------------------------------------------------------------------
    # Thread-safe UI helpers
    # -----------------------------------------------------------------------

    def _ui_status(self, text: str) -> None:
        self.after(0, lambda t=text: self._status_lbl.configure(text=t))

    def _ui_sub(self, text: str) -> None:
        self.after(0, lambda t=text: self._sub_lbl.configure(text=t))

    def _ui_progress(self, value: float) -> None:
        self.after(0, lambda v=value: self._progress.set(v))
