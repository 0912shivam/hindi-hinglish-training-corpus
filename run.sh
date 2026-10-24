#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: ./run.sh <raw_dir> <out_dir>" >&2
  exit 1
fi

RAW_DIR="$1"
OUT_DIR="$2"

if [ ! -d "$RAW_DIR" ]; then
  echo "Raw directory does not exist: $RAW_DIR" >&2
  exit 1
fi

PYTHON="python"
if [ -f ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
elif [ -f ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"
fi

PYTHONPATH=src "$PYTHON" -m flam_pipeline.cli "$RAW_DIR" "$OUT_DIR"
