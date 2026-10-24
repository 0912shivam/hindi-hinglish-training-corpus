# Hindi & Hinglish Training Corpus — Data Curation Pipeline

A robust, streaming data-engineering pipeline designed to curate high-quality Hindi (`hi`) and Hinglish (`hi-Latn`) pre-training and fine-tuning datasets from heterogeneous public data sources. The pipeline ingests multi-format raw dumps, normalizes complex Indic scripts and informal Romanized transliterations, redacts sensitive Indian personal identifiers, eliminates exact and near-duplicates, and extracts an uncontaminated, held-out evaluation benchmark with complete cryptographic provenance.

Indic NLP pipelines present distinct engineering challenges. Devanagari text frequently suffers from inconsistent Unicode representations, orphaned diacritics, invisible zero-width joiners/non-joiners (ZWJ/ZWNJ), and non-standard whitespace. Concurrently, Hinglish—Hindi phonetically transcribed into the Latin alphabet—exhibits non-standard colloquial spellings, code-mixing with English, and noisy social-media artifacts. This pipeline addresses these nuances with script-aware canonicalization and lexical classification without discarding valid short literary forms or numeric records.

Architected for production data curation, the system processes data strictly in streaming mode without loading complete corpora into memory. Every operational stage is fully deterministic and auditable: malformed records are safely quarantined, every document transition is recorded in a companion ledger, and final runs atomically produce reproducible clean archives alongside a cryptographically verified manifest.

---

## Key Capabilities

- **Streaming Ingestion & Fault Tolerance**: Streams records row-by-row across Parquet (batch-streamed via PyArrow), CSV/TSV, and newline-delimited JSON (`.jsonl`). Corrupted files, truncated lines, or unparseable JSON payloads never crash the pipeline; malformed inputs are logged with line references and accounted for in the ledger.
- **Unicode & Indic Normalization**: Enforces Unicode NFKC normalization, eliminates invisible control/format characters while strictly preserving semantic Devanagari ZWJ/ZWNJ conjunct markers, harmonizes Devanagari danda punctuation (`।`, `॥`), and standardizes whitespace.
- **Script-Aware Language Classification**: Identifies and categorizes documents into four disjoint labels: `hi` (Devanagari script), `hi-Latn` (Latin-script Hinglish identified via high-frequency romanized Hindi lexical markers), `en` (standard English), and `other` (noise/code/unsupported scripts).
- **Conservative Quality Filtering**: Removes URL/markup spam, repetitive token spam, and unreadable character runs. Uses calibrated token/character heuristics that safely retain short proverbs (e.g., *सत्यमेव जयते*), couplets, and numerical/financial tables.
- **Indian PII Redaction**: Detects and redacts high-risk Indian personal identifiers using regex patterns and context triggers:
  - Phone numbers (10-digit Indian mobile formats with `+91`, `0`, or standard prefixes)
  - Email addresses
  - Aadhaar numbers (12-digit format validated with the Verhoeff checksum algorithm to prevent false-positive number drops)
  - Permanent Account Number (PAN: `[A-Z]{5}[0-9]{4}[A-Z]`)
- **SQLite-Backed Exact Deduplication**: Computes deterministic SHA-256 hashes of canonicalized text to discard byte-for-byte duplicates while maintaining the canonical document identifier.
- **MinHash + LSH Near-Deduplication**: Extracts token 3-gram shingles with 64 MinHash permutations and MinHashLSH indexing (candidate threshold: 0.82) combined with exact token Jaccard similarity verification (threshold: 0.86) to drop near-paraphrases.
- **Stratified Held-Out Evaluation Set**: Selects a balanced, deterministic 200-document evaluation holdout stratified across Hindi and Hinglish subsets using pinned random scoring.
- **Multi-Tiered Contamination Detection**: Evaluates training data against held-out evaluation data across four dimensions: exact match, normalized match, token near-duplicate (Jaccard $\ge 0.90$), and Devanagari-to-Latin cross-script phonetic match with schwa-deletion. Contaminated training candidates are automatically quarantined.
- **Complete Ledger Audit Trail**: Generates a 1:1 gzipped ledger (`ledger.jsonl.gz`) tracking every input document with its final status (`kept` or `dropped`), pipeline stage, and machine-readable drop reason.
- **Deterministic Reruns**: Output artifacts are generated deterministically using seeded hash functions and stable sorting. Writes are staged in temporary isolation and swapped atomically.
- **Provenance & Manifest Audit**: Outputs `manifest.json` containing pipeline configuration, threshold parameters, raw input SHA-256 hashes, language distributions, and stage-by-stage document funnels.

---

## Pipeline Flow

```
[Raw Data Sources]
        │
        ▼
[Streaming Ingestion] (Parquet / CSV / JSONL — malformed records quarantined)
        │
        ▼
[Unicode Normalization] (NFKC, ZWJ/ZWNJ preservation, danda & whitespace cleanup)
        │
        ▼
[Language Classification] (hi, hi-Latn, en, other)
        │
        ▼
[Quality Filtering] (Spam, repetition, noise removal; preserves proverbs/tables)
        │
        ▼
[PII Redaction] (PHONE, EMAIL, AADHAAR with Verhoeff, PAN)
        │
        ▼
[Exact Deduplication] (SHA-256 hash collision detection)
        │
        ▼
[Near Deduplication] (MinHash LSH + token Jaccard verification at 0.86)
        │
        ▼
[Eval Holdout Selection] (200 stratified items held out deterministically)
        │
        ▼
[Contamination Check] (Exact, normalized, near-duplicate & cross-script filtering)
        │
        ▼
[Final Clean Training Corpus] (train.jsonl.gz + sample_1000.jsonl.gz + ledger)
```

---

## Repository Structure

```
├── .gitignore                      # Git exclusion rules (raw data, venv, caches, sqlite)
├── DECISIONS.md                    # Detailed engineering decision log and run analysis
├── README.md                       # Project documentation and engineering guide
├── download.sh                     # Offline data acquisition script
├── pytest.ini                      # Pytest test discovery configuration
├── requirements.txt                # Pinned production and testing dependencies
├── run.sh                          # Main pipeline execution entrypoint
├── data/
│   ├── raw/                        # Untouched raw input data (downloaded via download.sh)
│   ├── raw_hashes.json             # SHA-256 checksums and file sizes for raw inputs
│   └── sources.json                # Source metadata, licenses, and acquisition dates
├── output/                         # Complete verified pipeline run artifacts
│   ├── DECISIONS.md                # Run-specific decisions and metric breakdown
│   ├── contamination.jsonl         # Detailed log of contamination checks and matches
│   ├── eval.jsonl                  # 200 held-out evaluation documents
│   ├── ledger.jsonl.gz             # 1:1 audit ledger for all 103,975 processed records
│   ├── manifest.json               # Cryptographic hashes, run metadata, and stage metrics
│   ├── near_threshold_examples.jsonl # Borderline pair diagnostics near similarity threshold
│   └── clean/
│       ├── sample_1000.jsonl.gz    # Exactly 1,000 deterministic sample rows
│       └── train.jsonl.gz          # Final clean training corpus (103,483 records)
├── src/
│   └── flam_pipeline/              # Core pipeline package
│       ├── __init__.py
│       ├── cli.py                  # CLI argument parsing
│       ├── config.py               # Dataclass configurations and parameter defaults
│       ├── contamination.py        # Multi-tiered & cross-script contamination detector
│       ├── dedup_exact.py          # SQLite-backed exact SHA-256 deduplication
│       ├── eval_holdout.py         # Stratified eval holdout selector
│       ├── ingestion.py            # Streaming multi-format file readers
│       ├── language.py             # Script and lexical language classification
│       ├── models.py               # Data models and record definitions
│       ├── near_dedup.py           # MinHashLSH candidate indexing & Jaccard verification
│       ├── normalize.py            # Devanagari and Unicode text canonicalization
│       ├── pii.py                  # Regex & Verhoeff-based Indian PII redaction
│       ├── pipeline.py             # Main end-to-end streaming orchestrator
│       ├── quality.py              # Conservative quality filtering heuristics
│       └── utils.py                # Cryptographic hashing, atomic IO, and file utilities
└── tests/
    ├── conftest.py                 # Pytest environment fixtures
    ├── fixtures/                   # Synthetic malformed JSONL and TSV test cases
    │   ├── malformed.jsonl
    │   └── mixed.tsv
    ├── test_contamination.py       # Cross-script and near-duplicate contamination tests
    ├── test_dedup.py               # Exact and near deduplication unit tests
    ├── test_determinism.py         # Bit-for-bit rerun determinism tests
    ├── test_language.py            # Language identification and Hinglish detection tests
    ├── test_normalization.py       # Devanagari Unicode normalization tests
    ├── test_pii.py                 # Phone, email, Aadhaar, and PAN redaction tests
    └── test_quality.py             # Quality filters and short-text preservation tests
```

---

## Output Artifacts

All outputs conform to strict schema requirements and are stored under the specified output directory:

| Artifact Path | Format | Description |
|---|---|---|
| `output/clean/train.jsonl.gz` | Gzip JSONL | Final clean training corpus containing `id`, `text`, `lang`, and `source`. |
| `output/clean/sample_1000.jsonl.gz` | Gzip JSONL | Exactly 1,000 deterministically sampled rows from the clean corpus. |
| `output/ledger.jsonl.gz` | Gzip JSONL | Complete audit log for every input record (`id`, `status`, `stage`, `reason`, `dup_of`). |
| `output/eval.jsonl` | Plain JSONL | 200 held-out evaluation documents stratified across languages. |
| `output/contamination.jsonl` | Plain JSONL | Evaluation contamination records including method and matched IDs. |
| `output/manifest.json` | JSON | Cryptographic audit trail: raw hashes, stage counts, parameters, and timestamps. |
| `output/DECISIONS.md` | Markdown | Comprehensive report detailing all filtering and design decisions. |
| `output/near_threshold_examples.jsonl`| Plain JSONL | Diagnostics of candidate document pairs evaluated near the deduplication threshold. |

---

## Final Run Results

The following metrics are extracted directly from the verified execution manifest (`output/manifest.json`) and run ledger:

### Corpus Processing Funnel

| Metric | Value |
|---|---|
| **Total Input Documents** | **103,975** |
| Successfully Parsed Documents | 103,975 |
| Malformed Records Skipped | 0 |
| Total Dropped Documents | 492 |
| **Final Kept Training Documents** | **103,483** |
| Total Ledger Entries Generated | 103,975 (1:1 accounting) |
| Total PII Redactions Applied | 12 |
| Held-Out Evaluation Items | 200 |
| Contaminated Training Documents Removed | 0 |
| Random Clean Sample Size | 1,000 |
| Unit Test Suite Result | 23 passed (100% pass rate) |

### Clean Corpus Language Distribution

| Language Label | Document Count | Share (%) |
|---|---|---|
| `hi` (Hindi in Devanagari script) | 89,858 | 86.83% |
| `hi-Latn` (Hinglish in Latin script) | 12,355 | 11.94% |
| `other` (Preserved multilingual/specialized records) | 996 | 0.96% |
| `en` (English records) | 274 | 0.26% |
| **Total Clean Corpus** | **103,483** | **100.00%** |

### Stage-by-Stage Attrition Breakdown

| Pipeline Stage | Total Dropped | `hi` | `hi-Latn` | `en` | `other` |
|---|---|---|---|---|---|
| `parse` | 0 | 0 | 0 | 0 | 0 |
| `normalization` | 0 | 0 | 0 | 0 | 0 |
| `quality` | 212 | 190 | 17 | 0 | 5 |
| `exact_dedup` | 15 | 13 | 1 | 1 | 0 |
| `near_dedup` | 65 | 22 | 39 | 2 | 2 |
| `eval` (held out) | 200 | 160 | 30 | 2 | 8 |
| `contamination` | 0 | 0 | 0 | 0 | 0 |
| **Kept for Training** | **103,483** | **89,858** | **12,355** | **274** | **996** |

---

## Data Quality & Deduplication

1. **Exact Deduplication**: Normalized and PII-redacted text strings are hashed using SHA-256 and registered in an indexed SQLite database. If a document hash matches an existing record, the duplicate is dropped and tagged with `reason: EXACT_DUPLICATE` alongside a pointer (`dup_of`) to the canonical document ID.
2. **Near-Duplicate Detection**:
   - Token 3-grams are generated for each document (capped at 2,000 characters and 200 tokens).
   - Signatures are computed using 64-permutation MinHash and indexed into an in-memory MinHashLSH structure with a candidate threshold of 0.82.
   - For every returned candidate, the pipeline executes an exact token Jaccard similarity check. Pairs with similarity $\ge 0.86$ are flagged as near-duplicates; the newer document is dropped with `reason: NEAR_DUPLICATE` pointing to the first occurrence.
   - The 0.86 threshold was empirically selected to eliminate substantial paraphrases and reposted social commentary without dropping distinct short couplets or formulaic news headlines.

---

## Privacy & PII

The pipeline applies targeted masking to prevent confidential personal identifiers from entering language model training datasets:

- **Phone Numbers (`[PHONE]` label)**: Captures 10-digit Indian telephone formats including standard mobile prefixes (`+91`, `91`, `0`), separated digits, and bracketed STD codes. Non-PII numbers (single digits, dates, percentages, currency, table entries) are strictly preserved.
- **Email Addresses (`[EMAIL]` label)**: Standard RFC-compliant email detection replacing addresses with `[EMAIL]`.
- **Aadhaar Numbers (`[AADHAAR]` label)**: Identifies 12-digit Indian national identity numbers (formatted as `XXXX XXXX XXXX` or contiguous digits) and validates them against the **Verhoeff checksum algorithm**. Numerical runs that fail the checksum are retained as general numbers, preventing corruption of legitimate numeric data.
- **Permanent Account Number (`[PAN]` label)**: Detects Indian income tax PAN identifiers matching the standard `[A-Z]{5}[0-9]{4}[A-Z]` format.

---

## Reproducibility

The repository guarantees end-to-end deterministic reproducibility:

- **Separation of Concerns**: Network-dependent data downloading is isolated in `download.sh`. The pipeline (`run.sh`) executes completely offline without external internet calls.
- **Deterministic Document Identifiers**: Document IDs are computed via SHA-256 hashes of `source_name:file_relpath:line/record_index:canonical_text`.
- **Pinned Random Seed**: Stratified evaluation sampling and reservoir sample selection use fixed seed `20261024`.
- **Safe Reruns**: Output files are staged in an isolated temporary working directory and swapped into the destination path using atomic directory replacement. Rerunning `./run.sh` produces bit-for-bit identical ledger rows, clean archives, and checksums.

---

## Testing

The test suite thoroughly verifies each isolated component and pipeline stage. Run tests using `pytest`:

```bash
pytest -q
```

### Verified Test Suite Results

```text
.......................                                                  [100%]
23 passed in 2.18s
```

Test coverage includes:
- Ingestion parsing for valid, truncated, and malformed files across formats
- Indic Unicode normalization and ZWJ/ZWNJ preservation
- High-precision Hinglish marker classification
- Phone, Email, PAN, and Verhoeff-validated Aadhaar redaction
- Short proverb/couplet preservation under quality filtering
- Exact SHA-256 deduplication and MinHash/Jaccard near-deduplication
- Eval holdout stratification and cross-script contamination detection
- Bit-for-bit rerun determinism

---

## Quick Start

### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/0912shivam/hindi-hinglish-training-corpus.git
cd hindi-hinglish-training-corpus

# Create and activate virtual environment
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate
# On Windows PowerShell:
# .venv\Scripts\Activate.ps1

# Install pinned dependencies
pip install -r requirements.txt
```

### 2. Download Raw Datasets

Data acquisition is executed as a standalone step:

```bash
chmod +x download.sh run.sh
./download.sh
```

Downloads:
- AI4Bharat Sangraha synthetic Hindi Devanagari shard (`wiki_hin_Deva_0000_of_0063.parquet`)
- PHINC Hinglish benchmark dataset (`PHINC.csv`)

### 3. Run Pipeline

Execute the streaming pipeline with required positional arguments:

```bash
./run.sh data/raw output
```

### 4. Run Test Suite

```bash
pytest -q
```

---

## Design Notes

Key engineering trade-offs documented in [`DECISIONS.md`](DECISIONS.md):

1. **Streaming vs. In-Memory**: Processing 100k+ documents via PyArrow batch iterators and SQLite indices prevents memory exhaustion, maintaining an execution footprint under 300 MB RAM regardless of input volume.
2. **Conservative Quality Thresholds**: Strict character minimums drop noise while keeping valid 3-character Devanagari proverbs. Danda punctuation (`।`, `॥`) is exempted from noise ratios.
3. **Cross-Script Contamination**: Prevents training leaks where Hindi eval texts appear as transliterated Romanized Hinglish in training sets via ITRANS phonetic projection and length-bounded Jaccard candidate filtering.
4. **Horizontal Scaling Pathway**: At multi-terabyte scale, the architecture naturally transitions from single-node SQLite to distributed engines (Ray / Apache Spark) using distributed MinHash banding buckets and partitioned Parquet ledgers.

---

## Submission Notes

- **Repository Cleanliness**: As per assignment instructions, the repository **excludes the full raw dataset** (`data/raw/`), virtual environment (`.venv/`), and runtime state databases (`*.sqlite`).
- **Required Deliverables Included**:
  - `download.sh` and `run.sh` entrypoints
  - Full modular Python implementation under `src/`
  - Automated unit test suite under `tests/`
  - Complete `DECISIONS.md` rationale
  - `output/eval.jsonl` (200 held-out evaluation documents)
  - `output/clean/sample_1000.jsonl.gz` (exactly 1,000 deterministic sample rows)
  - `output/contamination.jsonl`, `output/manifest.json`, and `output/ledger.jsonl.gz`

---

## Tech Stack

The pipeline relies strictly on standard Python libraries and minimal pinned production dependencies:

| Component | Library / Tool | Version | Purpose |
|---|---|---|---|
| **Language & Runtime** | Python | 3.11+ | Core pipeline runtime |
| **Tabular & Columnar IO** | PyArrow | `18.0.0` | Memory-efficient streaming Parquet ingestion |
| **Streaming JSON** | ijson | `3.3.0` | Incremental parsing of large JSON structures |
| **Near-Deduplication** | datasketch | `1.6.5` | MinHash signature generation and LSH indexing |
| **Indic Transliteration**| indic-transliteration | `2.3.59` | Cross-script transliteration for contamination checks |
| **State & Exact Dedup** | SQLite3 (standard library) | Built-in | WAL-mode transactional state store and exact dedup |
| **Testing** | pytest | `8.3.3` | Comprehensive test discovery and test runner |
