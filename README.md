# FLAM Assignment: Clean Indic Training Corpus

This repository implements a streaming, deterministic corpus-cleaning pipeline for Hindi and Hinglish training data.

## What This Does

- Reads messy raw data from multiple common formats
- Normalizes Unicode and Indic text deterministically
- Assigns one language label per document: hi, hi-Latn, en, other
- Applies conservative quality filters with machine-readable reasons
- Redacts Indian PII (phone, email, Aadhaar, PAN)
- Runs exact dedup (SQLite-backed) and near dedup (MinHash candidate generation + exact Jaccard)
- Builds a deterministic held-out eval set (~200)
- Detects contamination (exact, normalized, near duplicate, cross-script)
- Removes contaminated training rows
- Writes clean corpus, ledger, contamination report, and manifest

## Repository Structure

- src/flam_pipeline/: pipeline package
- tests/: unit tests and synthetic fixtures
- data/raw/: raw downloaded source files (untouched)
- download.sh: data acquisition script (separate from pipeline)
- run.sh: offline pipeline entrypoint

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Download Data

```bash
./download.sh
```

Notes:
- download.sh records source metadata in data/sources.json
- raw files are stored in data/raw and not modified by pipeline

## Run Pipeline

```bash
./run.sh data/raw output
```

Positional arguments are required exactly as shown:
- raw_dir
- out_dir

## Output Files

- output/clean/train.jsonl.gz
- output/clean/sample_1000.jsonl.gz
- output/ledger.jsonl.gz
- output/eval.jsonl
- output/contamination.jsonl
- output/near_threshold_examples.jsonl
- output/manifest.json
- output/DECISIONS.md

Kept record schema:

```json
{
  "id": "...",
  "text": "...",
  "lang": "hi|hi-Latn|en|other",
  "source": "..."
}
```

Ledger schema:

```json
{
  "id": "...",
  "status": "kept|dropped",
  "stage": "...",
  "reason": "...",
  "dup_of": "..."
}
```

## Tests

```bash
pytest -q
```

## Determinism and Reruns

- Stable document IDs from deterministic hashes
- Fixed seeds for eval selection and sampling
- Ordered processing by file path and record order
- Writes to temporary run directory and atomically replaces output
- Safe reruns: no append mode on final outputs

## Licensing and Source Tracking

- Source metadata is stored in data/sources.json
- Raw input SHA-256 hashes are included in manifest.json
- Manifest records thresholds, counts, and run configuration
