"""Main application window for Video Enhancer (Apple Silicon)."""

from __future__ import annotations

import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from src.processor import VideoProcessor, build_ffmpeg_command, get_video_info

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")

SUPPORTED_EXT = {
    ".mp4", ".mov", ".avi", ".mkv", ".m4v",
    ".wmv", ".flv", ".webm", ".ts", ".mts", ".m2ts",
}

VERSION = "1.1.0"

# ---------------------------------------------------------------------------
# Translations
# ---------------------------------------------------------------------------

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "queue":            "Queue",
        "btn_add_file":     "+ File",
        "btn_add_folder":   "+ Folder",
        "btn_clear":        "Clear",
        "btn_remove":       "Remove Selected",
        "no_files":         "No files added",
        "sec_deinterlace":  "1  Deinterlace",
        "sec_denoise":      "2  Denoise",
        "sec_upscale":      "3  Upscale",
        "sec_sharpen":      "4  Sharpen",
        "sec_output":       "Output Settings",
        "deint_enable":     "Enable  (remove interlace combing from old footage)",
        "deint_method":     "Method:",
        "denoise_enable":   "Enable  (reduce film grain / digital noise)",
        "denoise_strength": "Strength:",
        "scale_label":      "Scale:",
        "algo_label":       "Algorithm:",
        "sharp_enable":     "Enable sharpening",
        "sharp_amount":     "Amount:",
        "codec_label":      "Codec:",
        "quality_label":    "Quality:",
        "output_label":     "Output:",
        "suffix_label":     "Suffix:",
        "recommend_prompt": "Not sure what settings to use?",
        "recommend_btn":    "Smart Recommend",
        "preview_btn":      "Preview FFmpeg Command",
        "browse_btn":       "Browse",
        "start_btn":        "  Start Enhancement",
        "cancel_btn":       "  Cancel",
        "ready":            "Ready",
    },
    "th": {
        "queue":            "คิวไฟล์",
        "btn_add_file":     "+ ไฟล์",
        "btn_add_folder":   "+ โฟลเดอร์",
        "btn_clear":        "ล้าง",
        "btn_remove":       "ลบที่เลือก",
        "no_files":         "ยังไม่มีไฟล์",
        "sec_deinterlace":  "1  ดีอินเตอร์เลซ",
        "sec_denoise":      "2  ลดสัญญาณรบกวน",
        "sec_upscale":      "3  เพิ่มความละเอียด",
        "sec_sharpen":      "4  เพิ่มความคมชัด",
        "sec_output":       "ตั้งค่าเอาต์พุต",
        "deint_enable":     "เปิดใช้  (ลบเส้นขอบหวีจากฟุตเทจเก่า)",
        "deint_method":     "วิธี:",
        "denoise_enable":   "เปิดใช้  (ลดเกรน / สัญญาณรบกวน)",
        "denoise_strength": "ความแรง:",
        "scale_label":      "ขนาด:",
        "algo_label":       "อัลกอริทึม:",
        "sharp_enable":     "เปิดใช้การเพิ่มความคมชัด",
        "sharp_amount":     "ระดับ:",
        "codec_label":      "โคเดก:",
        "quality_label":    "คุณภาพ:",
        "output_label":     "เอาต์พุต:",
        "suffix_label":     "ต่อท้าย:",
        "recommend_prompt": "ไม่แน่ใจจะปรับค่าอะไร?",
        "recommend_btn":    "แนะนำอัตโนมัติ",
        "preview_btn":      "ดูคำสั่ง FFmpeg",
        "browse_btn":       "เลือก",
        "start_btn":        "  เริ่มปรับปรุงวิดีโอ",
        "cancel_btn":       "  ยกเลิก",
        "ready":            "พร้อม",
    },
}

WIZARD_STEPS: dict[str, list[dict]] = {
    "en": [
        {
            "id": "source",
            "title": "Step 1 / 4  —  Video Source",
            "question": "Where does this video come from?",
            "options": [
                ("old_tape", "Old tape / broadcast footage  (VHS, Betamax, VCR)"),
                ("dvd",      "DVD or older digital footage"),
                ("modern",   "Standard digital video  (camera, phone, online)"),
            ],
        },
        {
            "id": "goal",
            "title": "Step 2 / 4  —  Main Goal",
            "question": "What do you mainly want to improve?",
            "options": [
                ("sharpen", "Make it sharper  (Sharpen)"),
                ("denoise", "Reduce noise / grain  (Denoise)"),
                ("upscale", "Increase resolution  (Upscale 2×)"),
                ("full",    "Improve everything  (Recommended)"),
            ],
        },
        {
            "id": "usage",
            "title": "Step 3 / 4  —  Output Destination",
            "question": "What will this file be used for?",
            "options": [
                ("streaming",    "Upload to YouTube / Streaming"),
                ("archive",      "Personal archive / backup"),
                ("professional", "Professional editing  (ProRes)"),
            ],
        },
        {
            "id": "priority",
            "title": "Step 4 / 4  —  Speed vs Quality",
            "question": "What do you want to prioritise?",
            "options": [
                ("quality",  "Best quality  (slower)"),
                ("balanced", "Balanced  (Recommended)"),
                ("fast",     "Fastest  (moderate quality)"),
            ],
        },
    ],
    "th": [
        {
            "id": "source",
            "title": "ขั้นที่ 1 / 4  —  ประเภทวิดีโอ",
            "question": "วิดีโอนี้มาจากแหล่งใด?",
            "options": [
                ("old_tape", "เทป / ออกอากาศทีวีเก่า  (VHS, Betamax, VCR)"),
                ("dvd",      "DVD หรือฟุตเทจดิจิทัลเก่า"),
                ("modern",   "วิดีโอดิจิทัลทั่วไป  (กล้อง, มือถือ, ออนไลน์)"),
            ],
        },
        {
            "id": "goal",
            "title": "ขั้นที่ 2 / 4  —  เป้าหมายหลัก",
            "question": "ต้องการปรับปรุงอะไรเป็นหลัก?",
            "options": [
                ("sharpen", "ทำให้คมชัดขึ้น  (Sharpen)"),
                ("denoise", "ลดสัญญาณรบกวน / เกรน  (Denoise)"),
                ("upscale", "เพิ่มความละเอียด  (Upscale 2×)"),
                ("full",    "ปรับปรุงทุกด้าน  (แนะนำ)"),
            ],
        },
        {
            "id": "usage",
            "title": "ขั้นที่ 3 / 4  —  การใช้งานปลายทาง",
            "question": "ไฟล์นี้จะใช้ทำอะไร?",
            "options": [
                ("streaming",    "อัปโหลด YouTube / Streaming"),
                ("archive",      "เก็บไว้ดูส่วนตัว / สำรองข้อมูล"),
                ("professional", "ตัดต่อมืออาชีพ  (ProRes)"),
            ],
        },
        {
            "id": "priority",
            "title": "ขั้นที่ 4 / 4  —  ความเร็ว vs คุณภาพ",
            "question": "ต้องการเน้นด้านใด?",
            "options": [
                ("quality",  "คุณภาพดีที่สุด  (ใช้เวลานานกว่า)"),
                ("balanced", "สมดุล  (แนะนำ)"),
                ("fast",     "เร็วที่สุด  (คุณภาพปานกลาง)"),
            ],
        },
    ],
}


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
# Smart Recommend wizard
# ---------------------------------------------------------------------------

class RecommendWizard(ctk.CTkToplevel):
    """4-step wizard that asks simple questions and recommends settings."""

    def __init__(self, parent: ctk.CTk, lang: str, on_apply: Callable[[dict], None]) -> None:
        super().__init__(parent)
        self._lang = lang
        self._steps = WIZARD_STEPS[lang]
        self.title("Smart Recommend" if lang == "en" else "แนะนำอัตโนมัติ")
        self.geometry("560x400")
        self.resizable(False, False)
        self.grab_set()

        self._on_apply = on_apply
        self._step = 0
        self._radio_vars: list[ctk.StringVar] = [
            ctk.StringVar(value=s["options"][0][0]) for s in self._steps
        ]

        self._build()
        self._show_step(0)

    def _build(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._prog = ctk.CTkProgressBar(self, height=6)
        self._prog.grid(row=0, column=0, sticky="ew")

        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.grid(row=1, column=0, sticky="nsew", padx=36, pady=20)
        self._content.grid_columnconfigure(0, weight=1)

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 20))
        nav.grid_columnconfigure(1, weight=1)

        back_text = "← Back" if self._lang == "en" else "← ย้อนกลับ"
        self._back_btn = ctk.CTkButton(
            nav, text=back_text, width=110, height=34,
            fg_color="transparent", border_width=1,
            border_color=("gray50", "gray60"),
            text_color=("gray10", "gray90"),
            command=self._prev,
        )
        self._back_btn.grid(row=0, column=0)

        self._next_btn = ctk.CTkButton(
            nav, text="", width=150, height=34,
            command=self._next,
        )
        self._next_btn.grid(row=0, column=2)

    def _show_step(self, idx: int) -> None:
        for w in self._content.winfo_children():
            w.destroy()

        step = self._steps[idx]

        ctk.CTkLabel(
            self._content, text=step["title"],
            font=ctk.CTkFont(size=11), text_color="gray",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        ctk.CTkLabel(
            self._content, text=step["question"],
            font=ctk.CTkFont(size=16, weight="bold"),
            wraplength=480, anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(0, 16))

        var = self._radio_vars[idx]
        for r, (val, label) in enumerate(step["options"]):
            ctk.CTkRadioButton(
                self._content, text=label,
                variable=var, value=val,
                font=ctk.CTkFont(size=13),
            ).grid(row=2 + r, column=0, sticky="w", pady=5)

        self._prog.set((idx + 1) / len(self._steps))
        self._back_btn.configure(state="normal" if idx > 0 else "disabled")

        is_last = idx == len(self._steps) - 1
        next_text = (
            ("Apply Settings" if self._lang == "en" else "ใช้การตั้งค่า") if is_last
            else ("Next →" if self._lang == "en" else "ถัดไป →")
        )
        self._next_btn.configure(
            text=next_text,
            fg_color=(["#2ecc71", "#27ae60"] if is_last else ["#3B8ED0", "#1F6AA5"]),
            hover_color=(["#27ae60", "#1e8449"] if is_last else ["#36719F", "#144870"]),
        )

    def _prev(self) -> None:
        if self._step > 0:
            self._step -= 1
            self._show_step(self._step)

    def _next(self) -> None:
        if self._step < len(self._steps) - 1:
            self._step += 1
            self._show_step(self._step)
        else:
            answers = {s["id"]: self._radio_vars[i].get()
                       for i, s in enumerate(self._steps)}
            self._on_apply(self._compute(answers))
            self.destroy()

    @staticmethod
    def _compute(answers: dict) -> dict:
        source   = answers["source"]
        goal     = answers["goal"]
        usage    = answers["usage"]
        priority = answers["priority"]
        rec: dict = {}

        rec["deinterlace"] = source in ("old_tape", "dvd")
        if source == "old_tape" and priority == "quality":
            rec["deinterlace_method"] = "bwdif  (High Quality)"
        elif rec["deinterlace"]:
            rec["deinterlace_method"] = "yadif  (Standard)"

        # Only denoise when the user actually asks (or clearly noisy source).
        # "full" no longer force-denoises clean input — that softened it.
        rec["denoise"] = goal == "denoise" or source == "old_tape"
        if rec["denoise"]:
            if source == "old_tape" or goal == "denoise":
                rec["denoise_strength"] = 3.0
            elif source == "dvd":
                rec["denoise_strength"] = 2.0
            else:
                rec["denoise_strength"] = 1.5

        if goal in ("upscale", "full"):
            rec["upscale"] = "2×  Upscale"
            rec["upscale_algo"] = "Bicubic  (Fast)" if priority == "fast" else "Lanczos  (Best)"
        else:
            rec["upscale"] = "1×  (Original)"
            rec["upscale_algo"] = "Lanczos  (Best)"

        rec["sharpen"] = goal in ("sharpen", "full")
        if rec["sharpen"]:
            # Light by default — "full" gets a gentle crisp-up, not halos.
            if goal == "sharpen":
                rec["sharpen_amount"] = 0.8 if priority == "quality" else 0.5
            else:
                rec["sharpen_amount"] = 0.3

        if usage == "professional":
            rec["codec"] = "ProRes 422"
            rec["quality"] = 85
        elif usage == "streaming":
            rec["codec"] = "H.264  (VideoToolbox)"
            rec["quality"] = 75
        else:
            rec["codec"] = "H.265 HEVC  (VideoToolbox)"
            rec["quality"] = 80

        return rec


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
        self._settings_widgets: list = []
        self._lang = "en"
        self._i18n: list[tuple] = []  # (widget, string_key)

        self._build_ui()
        self._check_ffmpeg()

    # -----------------------------------------------------------------------
    # i18n helpers
    # -----------------------------------------------------------------------

    def _s(self, key: str) -> str:
        return STRINGS.get(self._lang, STRINGS["en"]).get(key, key)

    def _set_language(self, lang: str) -> None:
        self._lang = lang
        for widget, key in self._i18n:
            widget.configure(text=self._s(key))
        self._refresh_list()
        if not self.is_processing:
            self._start_btn.configure(text=self._s("start_btn"))

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
            font=ctk.CTkFont(size=13), text_color="gray",
        ).pack(side="left", padx=(10, 0), pady=(5, 0))

        # right controls
        ctrl = ctk.CTkFrame(header, fg_color="transparent")
        ctrl.pack(side="right")

        self._lang_seg = ctk.CTkSegmentedButton(
            ctrl, values=["EN", "TH"], width=80, height=28,
            command=lambda v: self._set_language("en" if v == "EN" else "th"),
        )
        self._lang_seg.set("EN")
        self._lang_seg.pack(side="right", padx=(8, 0))

        ctk.CTkOptionMenu(
            ctrl, values=["System", "Dark", "Light"],
            width=100, height=28,
            command=lambda m: ctk.set_appearance_mode(m),
        ).pack(side="right")

        self._build_file_panel()
        self._build_settings_panel()
        self._build_bottom_panel()

    # -----------------------------------------------------------------------

    def _build_file_panel(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=1, column=0, sticky="nsew", padx=(20, 8), pady=8)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(frame, fg_color="transparent")
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 6))

        _queue_lbl = ctk.CTkLabel(hdr, text=self._s("queue"),
                                   font=ctk.CTkFont(size=15, weight="bold"))
        _queue_lbl.pack(side="left")
        self._i18n.append((_queue_lbl, "queue"))

        btn_row = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_row.pack(side="right")

        _btn_file = ctk.CTkButton(btn_row, text=self._s("btn_add_file"),
                                   width=72, height=28, command=self._add_files)
        _btn_file.pack(side="left", padx=(0, 4))
        self._i18n.append((_btn_file, "btn_add_file"))

        _btn_folder = ctk.CTkButton(btn_row, text=self._s("btn_add_folder"),
                                     width=80, height=28, command=self._add_folder)
        _btn_folder.pack(side="left", padx=(0, 4))
        self._i18n.append((_btn_folder, "btn_add_folder"))

        _btn_clear = ctk.CTkButton(
            btn_row, text=self._s("btn_clear"), width=60, height=28,
            fg_color="transparent", border_width=1,
            border_color=("gray50", "gray60"), text_color=("gray10", "gray90"),
            command=self._clear_files,
        )
        _btn_clear.pack(side="left")
        self._i18n.append((_btn_clear, "btn_clear"))

        self._count_lbl = ctk.CTkLabel(frame, text=self._s("no_files"),
                                        text_color="gray", font=ctk.CTkFont(size=11))
        self._count_lbl.grid(row=1, column=0, columnspan=2, sticky="w", padx=14)

        lb_frame = ctk.CTkFrame(frame, fg_color="transparent")
        lb_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=12, pady=6)
        lb_frame.grid_rowconfigure(0, weight=1)
        lb_frame.grid_columnconfigure(0, weight=1)

        self._listbox = tk.Listbox(
            lb_frame, selectmode=tk.EXTENDED,
            font=("Menlo", 11), activestyle="none",
            relief="flat", bd=0, highlightthickness=0,
        )
        self._listbox.grid(row=0, column=0, sticky="nsew")
        self._apply_listbox_theme()

        sb = ctk.CTkScrollbar(lb_frame, command=self._listbox.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._listbox.configure(yscrollcommand=sb.set)

        _btn_remove = ctk.CTkButton(
            frame, text=self._s("btn_remove"), height=28,
            fg_color="transparent", border_width=1,
            border_color=("gray50", "gray60"), text_color=("gray10", "gray90"),
            command=self._remove_selected,
        )
        _btn_remove.grid(row=3, column=0, columnspan=2, padx=12, pady=(0, 12))
        self._i18n.append((_btn_remove, "btn_remove"))

    # -----------------------------------------------------------------------

    def _apply_listbox_theme(self) -> None:
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            self._listbox.configure(bg="#1e1e1e", fg="#e0e0e0",
                                     selectbackground="#1F6AA5", selectforeground="white")
        else:
            self._listbox.configure(bg="#f5f5f5", fg="#111111",
                                     selectbackground="#3B8ED0", selectforeground="white")

    # -----------------------------------------------------------------------

    def _build_settings_panel(self) -> None:
        outer = ctk.CTkScrollableFrame(self, label_text="Enhancement Settings",
                                       label_font=ctk.CTkFont(size=14, weight="bold"))
        outer.grid(row=1, column=1, sticky="nsew", padx=(8, 20), pady=8)
        outer.grid_columnconfigure(0, weight=1)

        sw = self._settings_widgets
        pad = {"padx": 12, "pady": 6}

        # ── Smart Recommend ─────────────────────────────────────────────
        rec_frame = ctk.CTkFrame(outer, fg_color=("gray92", "gray17"))
        rec_frame.grid(row=0, column=0, sticky="ew", **pad)

        _rec_prompt = ctk.CTkLabel(rec_frame, text=self._s("recommend_prompt"),
                                    font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        _rec_prompt.pack(side="left", padx=14, pady=10)
        self._i18n.append((_rec_prompt, "recommend_prompt"))

        _rec_btn = ctk.CTkButton(rec_frame, text=self._s("recommend_btn"),
                                  width=160, height=30, command=self._open_recommend_wizard)
        _rec_btn.pack(side="right", padx=14, pady=10)
        sw.append(_rec_btn)
        self._i18n.append((_rec_btn, "recommend_btn"))

        # ── 1. Deinterlace ──────────────────────────────────────────────
        s1 = self._section(outer, "sec_deinterlace")
        s1.grid(row=1, column=0, sticky="ew", **pad)

        self._deint_var = ctk.BooleanVar(value=False)
        _cb1 = ctk.CTkCheckBox(s1, text=self._s("deint_enable"),
                                variable=self._deint_var, command=self._sync_deint)
        _cb1.pack(anchor="w", padx=12, pady=(10, 4))
        sw.append(_cb1)
        self._i18n.append((_cb1, "deint_enable"))

        row = ctk.CTkFrame(s1, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 10))
        _lbl_method = ctk.CTkLabel(row, text=self._s("deint_method"), width=80)
        _lbl_method.pack(side="left")
        self._i18n.append((_lbl_method, "deint_method"))
        self._deint_method = ctk.CTkOptionMenu(
            row, values=["yadif  (Standard)", "yadif bob  (Smooth)", "bwdif  (High Quality)"],
            width=220,
        )
        self._deint_method.pack(side="left", padx=6)
        self._deint_method.set("yadif  (Standard)")
        sw.append(self._deint_method)
        self._sync_deint()

        # ── 2. Denoise ──────────────────────────────────────────────────
        s2 = self._section(outer, "sec_denoise")
        s2.grid(row=2, column=0, sticky="ew", **pad)

        self._denoise_var = ctk.BooleanVar(value=False)
        _cb2 = ctk.CTkCheckBox(s2, text=self._s("denoise_enable"),
                                variable=self._denoise_var, command=self._sync_denoise)
        _cb2.pack(anchor="w", padx=12, pady=(10, 4))
        sw.append(_cb2)
        self._i18n.append((_cb2, "denoise_enable"))

        self._denoise_row = ctk.CTkFrame(s2, fg_color="transparent")
        self._denoise_row.pack(fill="x", padx=12, pady=(0, 10))
        _lbl_str = ctk.CTkLabel(self._denoise_row, text=self._s("denoise_strength"), width=80)
        _lbl_str.pack(side="left")
        self._i18n.append((_lbl_str, "denoise_strength"))
        self._denoise_str = ctk.DoubleVar(value=4.0)
        _sl2 = ctk.CTkSlider(self._denoise_row, from_=1, to=10,
                              variable=self._denoise_str, width=160)
        _sl2.pack(side="left", padx=6)
        sw.append(_sl2)
        self._denoise_lbl = ctk.CTkLabel(self._denoise_row, text="4.0", width=36)
        self._denoise_lbl.pack(side="left")
        self._denoise_str.trace_add("write", lambda *_: self._denoise_lbl.configure(
            text=f"{self._denoise_str.get():.1f}"))
        self._sync_denoise()

        # ── 3. Upscale ──────────────────────────────────────────────────
        s3 = self._section(outer, "sec_upscale")
        s3.grid(row=3, column=0, sticky="ew", **pad)

        row3a = ctk.CTkFrame(s3, fg_color="transparent")
        row3a.pack(fill="x", padx=12, pady=(10, 4))
        _lbl_scale = ctk.CTkLabel(row3a, text=self._s("scale_label"), width=80)
        _lbl_scale.pack(side="left")
        self._i18n.append((_lbl_scale, "scale_label"))
        self._scale_var = ctk.StringVar(value="1×  (Original)")
        _om3a = ctk.CTkOptionMenu(
            row3a, values=["1×  (Original)", "2×  Upscale", "4×  Upscale"],
            variable=self._scale_var, width=180,
        )
        _om3a.pack(side="left", padx=6)
        sw.append(_om3a)

        row3b = ctk.CTkFrame(s3, fg_color="transparent")
        row3b.pack(fill="x", padx=12, pady=(0, 10))
        _lbl_algo = ctk.CTkLabel(row3b, text=self._s("algo_label"), width=80)
        _lbl_algo.pack(side="left")
        self._i18n.append((_lbl_algo, "algo_label"))
        self._algo_var = ctk.StringVar(value="Lanczos  (Best)")
        _om3b = ctk.CTkOptionMenu(
            row3b, values=["Lanczos  (Best)", "Bicubic  (Fast)", "Bilinear  (Fastest)"],
            variable=self._algo_var, width=180,
        )
        _om3b.pack(side="left", padx=6)
        sw.append(_om3b)

        # ── 4. Sharpen ──────────────────────────────────────────────────
        s4 = self._section(outer, "sec_sharpen")
        s4.grid(row=4, column=0, sticky="ew", **pad)

        self._sharp_var = ctk.BooleanVar(value=False)
        _cb4 = ctk.CTkCheckBox(s4, text=self._s("sharp_enable"),
                                variable=self._sharp_var, command=self._sync_sharp)
        _cb4.pack(anchor="w", padx=12, pady=(10, 4))
        sw.append(_cb4)
        self._i18n.append((_cb4, "sharp_enable"))

        self._sharp_row = ctk.CTkFrame(s4, fg_color="transparent")
        self._sharp_row.pack(fill="x", padx=12, pady=(0, 10))
        _lbl_amt = ctk.CTkLabel(self._sharp_row, text=self._s("sharp_amount"), width=80)
        _lbl_amt.pack(side="left")
        self._i18n.append((_lbl_amt, "sharp_amount"))
        self._sharp_amt = ctk.DoubleVar(value=1.0)
        _sl4 = ctk.CTkSlider(self._sharp_row, from_=0.1, to=3.0,
                              variable=self._sharp_amt, width=160)
        _sl4.pack(side="left", padx=6)
        sw.append(_sl4)
        self._sharp_lbl = ctk.CTkLabel(self._sharp_row, text="1.0", width=36)
        self._sharp_lbl.pack(side="left")
        self._sharp_amt.trace_add("write", lambda *_: self._sharp_lbl.configure(
            text=f"{self._sharp_amt.get():.1f}"))
        self._sync_sharp()

        # ── Output Settings ──────────────────────────────────────────────
        s5 = self._section(outer, "sec_output")
        s5.grid(row=5, column=0, sticky="ew", **pad)

        rc = ctk.CTkFrame(s5, fg_color="transparent")
        rc.pack(fill="x", padx=12, pady=(10, 4))
        _lbl_codec = ctk.CTkLabel(rc, text=self._s("codec_label"), width=80)
        _lbl_codec.pack(side="left")
        self._i18n.append((_lbl_codec, "codec_label"))
        self._codec_var = ctk.StringVar(value="H.265 HEVC  (VideoToolbox)")
        _om5c = ctk.CTkOptionMenu(
            rc,
            values=[
                "H.265 HEVC  (VideoToolbox)",
                "H.264  (VideoToolbox)",
                "ProRes 422",
                "H.264  (Software / libx264)",
            ],
            variable=self._codec_var, width=240,
        )
        _om5c.pack(side="left", padx=6)
        sw.append(_om5c)

        rq = ctk.CTkFrame(s5, fg_color="transparent")
        rq.pack(fill="x", padx=12, pady=(0, 4))
        _lbl_quality = ctk.CTkLabel(rq, text=self._s("quality_label"), width=80)
        _lbl_quality.pack(side="left")
        self._i18n.append((_lbl_quality, "quality_label"))
        self._quality_var = ctk.IntVar(value=80)
        _sl5q = ctk.CTkSlider(rq, from_=0, to=100, variable=self._quality_var, width=160)
        _sl5q.pack(side="left", padx=6)
        sw.append(_sl5q)
        self._quality_lbl = ctk.CTkLabel(rq, text="80", width=36)
        self._quality_lbl.pack(side="left")
        self._quality_var.trace_add("write", lambda *_: self._quality_lbl.configure(
            text=str(self._quality_var.get())))

        ro = ctk.CTkFrame(s5, fg_color="transparent")
        ro.pack(fill="x", padx=12, pady=(0, 4))
        _lbl_output = ctk.CTkLabel(ro, text=self._s("output_label"), width=80)
        _lbl_output.pack(side="left")
        self._i18n.append((_lbl_output, "output_label"))
        self._out_folder = ctk.StringVar(value="Same folder  (enhanced/)")
        _ent5o = ctk.CTkEntry(ro, textvariable=self._out_folder, width=190)
        _ent5o.pack(side="left", padx=6)
        sw.append(_ent5o)
        _btn5b = ctk.CTkButton(ro, text=self._s("browse_btn"), width=70, height=28,
                               command=self._browse_output)
        _btn5b.pack(side="left")
        sw.append(_btn5b)
        self._i18n.append((_btn5b, "browse_btn"))

        rs = ctk.CTkFrame(s5, fg_color="transparent")
        rs.pack(fill="x", padx=12, pady=(0, 12))
        _lbl_suffix = ctk.CTkLabel(rs, text=self._s("suffix_label"), width=80)
        _lbl_suffix.pack(side="left")
        self._i18n.append((_lbl_suffix, "suffix_label"))
        self._suffix_var = ctk.StringVar(value="_enhanced")
        _ent5s = ctk.CTkEntry(rs, textvariable=self._suffix_var, width=120)
        _ent5s.pack(side="left", padx=6)
        sw.append(_ent5s)

        # Preview command button — explicit border/text color so it's visible in light mode
        _btn_prev = ctk.CTkButton(
            outer, text=self._s("preview_btn"),
            height=30, fg_color="transparent", border_width=1,
            border_color=("gray50", "gray60"),
            text_color=("gray10", "gray90"),
            command=self._show_command,
        )
        _btn_prev.grid(row=6, column=0, sticky="ew", padx=12, pady=(0, 8))
        sw.append(_btn_prev)
        self._i18n.append((_btn_prev, "preview_btn"))

    # -----------------------------------------------------------------------

    def _build_bottom_panel(self) -> None:
        bar = ctk.CTkFrame(self)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 16))
        bar.grid_columnconfigure(1, weight=1)

        self._start_btn = ctk.CTkButton(
            bar, text=self._s("start_btn"),
            width=200, height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._toggle_processing,
        )
        self._start_btn.grid(row=0, column=0, padx=16, pady=14)

        prog_box = ctk.CTkFrame(bar, fg_color="transparent")
        prog_box.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=14)
        prog_box.grid_columnconfigure(0, weight=1)

        self._status_lbl = ctk.CTkLabel(prog_box, text=self._s("ready"), anchor="w",
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

    def _section(self, parent: ctk.CTkScrollableFrame, key: str) -> ctk.CTkFrame:
        f = ctk.CTkFrame(parent)
        lbl = ctk.CTkLabel(f, text=self._s(key),
                           font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        lbl.pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkFrame(f, height=1, fg_color="gray40").pack(fill="x", padx=12)
        self._i18n.append((lbl, key))
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

    def _set_settings_locked(self, locked: bool) -> None:
        state = "disabled" if locked else "normal"
        for w in self._settings_widgets:
            try:
                w.configure(state=state)
            except Exception:
                pass
        if not locked:
            self._sync_deint()
            self._sync_denoise()
            self._sync_sharp()

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
        if n == 0:
            self._count_lbl.configure(text=self._s("no_files"))
        elif self._lang == "th":
            self._count_lbl.configure(text=f"{n} ไฟล์ในคิว")
        else:
            self._count_lbl.configure(text=f"{n} file{'s' if n != 1 else ''} queued")

    def _browse_output(self) -> None:
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self._out_folder.set(folder)

    # -----------------------------------------------------------------------
    # Settings extraction
    # -----------------------------------------------------------------------

    _CODEC_MAP = {
        "H.265 HEVC  (VideoToolbox)":  "hevc_videotoolbox",
        "H.264  (VideoToolbox)":       "h264_videotoolbox",
        "ProRes 422":                  "prores_ks",
        "H.264  (Software / libx264)": "libx264",
    }
    _DEINT_MAP = {
        "yadif  (Standard)":     "yadif",
        "yadif bob  (Smooth)":   "yadif_bob",
        "bwdif  (High Quality)": "bwdif",
    }
    _ALGO_MAP = {
        "Lanczos  (Best)":     "lanczos",
        "Bicubic  (Fast)":     "bicubic",
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
    # Smart Recommend
    # -----------------------------------------------------------------------

    def _open_recommend_wizard(self) -> None:
        RecommendWizard(self, self._lang, self._apply_recommendations)

    def _apply_recommendations(self, rec: dict) -> None:
        if "deinterlace" in rec:
            self._deint_var.set(rec["deinterlace"])
        if "deinterlace_method" in rec:
            self._deint_method.set(rec["deinterlace_method"])
        self._sync_deint()

        if "denoise" in rec:
            self._denoise_var.set(rec["denoise"])
        if "denoise_strength" in rec:
            self._denoise_str.set(rec["denoise_strength"])
        self._sync_denoise()

        if "upscale" in rec:
            self._scale_var.set(rec["upscale"])
        if "upscale_algo" in rec:
            self._algo_var.set(rec["upscale_algo"])

        if "sharpen" in rec:
            self._sharp_var.set(rec["sharpen"])
        if "sharpen_amount" in rec:
            self._sharp_amt.set(rec["sharpen_amount"])
        self._sync_sharp()

        if "codec" in rec:
            self._codec_var.set(rec["codec"])
        if "quality" in rec:
            self._quality_var.set(rec["quality"])

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
        self._set_settings_locked(True)
        self._start_btn.configure(text=self._s("cancel_btn"),
                                  fg_color="#c0392b", hover_color="#922b21")
        threading.Thread(target=self._run_queue, daemon=True).start()

    def _set_start_idle(self) -> None:
        self._start_btn.configure(
            text=self._s("start_btn"),
            fg_color=["#3B8ED0", "#1F6AA5"],
            hover_color=["#36719F", "#144870"],
        )
        self._set_settings_locked(False)

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
