#!/usr/bin/env bash
# install.sh — one-time setup for Video Enhancer on Apple Silicon Mac

set -euo pipefail

echo "==> Video Enhancer — Setup"
echo ""

# ── Check macOS ─────────────────────────────────────────────────────────────
if [[ "$(uname)" != "Darwin" ]]; then
  echo "Error: macOS required." >&2
  exit 1
fi

# ── Check Homebrew ───────────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
  echo "Homebrew not found. Installing..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# ── Install FFmpeg ───────────────────────────────────────────────────────────
if ! command -v ffmpeg &>/dev/null; then
  echo "==> Installing FFmpeg..."
  brew install ffmpeg
else
  echo "==> FFmpeg already installed: $(ffmpeg -version 2>&1 | head -1)"
fi

# ── Install Python 3.13 + Tk (system Python has Tk 8.5 which crashes on macOS 26+)
echo "==> Installing python@3.13 and python-tk@3.13..."
brew install python@3.13 python-tk@3.13

PYTHON=/opt/homebrew/bin/python3.13

# ── Python virtual environment ───────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

if [[ -d "$VENV" ]]; then
  # Recreate if it was built with the wrong Python
  VENV_PYTHON="$VENV/bin/python"
  if ! "$VENV_PYTHON" -c "import tkinter" &>/dev/null; then
    echo "==> Recreating venv (old venv missing Tk support)..."
    rm -rf "$VENV"
  fi
fi

if [[ ! -d "$VENV" ]]; then
  echo "==> Creating Python virtual environment..."
  "$PYTHON" -m venv "$VENV"
fi

echo "==> Installing Python dependencies..."
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "Setup complete!"
echo ""
echo "Run the app with:"
echo "  ./run.sh"
