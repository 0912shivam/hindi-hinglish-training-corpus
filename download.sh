#!/usr/bin/env bash
set -euo pipefail

RAW_DIR="data/raw"
mkdir -p "$RAW_DIR"
mkdir -p "$RAW_DIR/sangraha_hindi" "$RAW_DIR/phinc"

# Stable URLs are pinned in one place for reproducibility.
SANGRAHA_URL="https://huggingface.co/datasets/ai4bharat/sangraha/resolve/main/synthetic/hin_Deva/wiki_hin_Deva_0000_of_0063.parquet"
PHINC_URL="https://huggingface.co/datasets/LingoIITGN/PHINC/resolve/main/PHINC.csv"

SANGRAHA_OUT="$RAW_DIR/sangraha_hindi/wiki_hin_Deva_0000_of_0063.parquet"
PHINC_OUT="$RAW_DIR/phinc/PHINC.csv"

fetch() {
  local url="$1"
  local out="$2"
  echo "Downloading: $url"
  if command -v curl >/dev/null 2>&1; then
    curl -fL "$url" -o "$out"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$out" "$url"
  else
    echo "Neither curl nor wget is available." >&2
    exit 1
  fi
}

hash_file() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{print $1}'
  else
    python - <<'PY' "$file"
import hashlib, sys
p = sys.argv[1]
h = hashlib.sha256()
with open(p, "rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        h.update(chunk)
print(h.hexdigest())
PY
  fi
}

fetch "$SANGRAHA_URL" "$SANGRAHA_OUT"
fetch "$PHINC_URL" "$PHINC_OUT"

SANGRAHA_SHA=$(hash_file "$SANGRAHA_OUT")
PHINC_SHA=$(hash_file "$PHINC_OUT")
DOWNLOAD_DATE=$(date -u +"%Y-%m-%d")

mkdir -p data
cat > data/sources.json <<EOF
[
  {
    "name": "AI4Bharat Sangraha Hindi",
    "url": "$SANGRAHA_URL",
    "license": "CC BY 4.0",
    "download_date": "$DOWNLOAD_DATE",
    "local_path": "$SANGRAHA_OUT",
    "notes": "Sangraha synthetic Hindi Devanagari shard 0"
  },
  {
    "name": "PHINC Hinglish",
    "url": "$PHINC_URL",
    "license": "CC BY 4.0",
    "download_date": "$DOWNLOAD_DATE",
    "local_path": "$PHINC_OUT",
    "notes": "PHINC Hinglish source file"
  }
]
EOF

cat > data/raw_hashes.json <<EOF
[
  {
    "path": "sangraha_hindi/wiki_hin_Deva_0000_of_0063.parquet",
    "sha256": "$SANGRAHA_SHA"
  },
  {
    "path": "phinc/PHINC.csv",
    "sha256": "$PHINC_SHA"
  }
]
EOF

echo "Download complete. Sources metadata written to data/sources.json"
