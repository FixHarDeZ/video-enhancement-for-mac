#!/usr/bin/env bash
# run.sh — launch Video Enhancer

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

if [[ ! -d "$VENV" ]]; then
  echo "Virtual environment not found. Run ./install.sh first." >&2
  exit 1
fi

cd "$SCRIPT_DIR"
exec "$VENV/bin/python" -m src.main "$@"
