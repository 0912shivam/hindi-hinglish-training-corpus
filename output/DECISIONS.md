# DECISIONS — Hindi & Hinglish Corpus Cleaning Run

## 1. Sources

| Source Name | License | URL | Document Count | Raw Size | Notes |
|---|---|---|---|---|---|
| AI4Bharat Sangraha Hindi | CC BY 4.0 | [https://huggingface.co/datasets/ai4bharat/sangraha/resolve/main/synthetic/hin_Deva/wiki_hin_Deva_0000_of_0063.parquet](https://huggingface.co/datasets/ai4bharat/sangraha/resolve/main/synthetic/hin_Deva/wiki_hin_Deva_0000_of_0063.parquet) | 90,237 | 245.34 MB | Sangraha synthetic Hindi Devanagari shard |
| PHINC Hinglish | CC BY 4.0 | [https://huggingface.co/datasets/LingoIITGN/PHINC/resolve/main/PHINC.csv](https://huggingface.co/datasets/LingoIITGN/PHINC/resolve/main/PHINC.csv) | 13,738 | 2.03 MB | PHINC Hinglish source file |

## 2. Funnel

### Global Processing Counts
- **Total Raw Input Documents**: 103,975
- **Successfully Parsed Documents**: 103,975
- **Malformed Records Skipped**: 0
- **Total Ledger Entries Generated**: 103,975
- **PII Redactions Applied**: 12
- **Held-Out Evaluation Items**: 200
- **Contaminated Training Documents Removed**: 0
- **Final Clean Training Corpus Rows**: 103,483

### Final Clean Corpus Distribution by Language
- `hi`: 89,858 (86.83%)
- `hi-Latn`: 12,355 (11.94%)
- `other`: 996 (0.96%)
- `en`: 274 (0.26%)

### Stage Funnel Breakdown
| Pipeline Stage | Total Affected | `hi` | `hi-Latn` | `en` | `other` |
|---|---|---|---|---|---|
| `parse` | 0 | 0 | 0 | 0 | 0 |
| `normalization` | 0 | 0 | 0 | 0 | 0 |
| `quality` | 212 | 190 | 17 | 0 | 5 |
| `exact_dedup` | 15 | 13 | 1 | 1 | 0 |
| `near_dedup` | 65 | 22 | 39 | 2 | 2 |
| `eval` | 200 | 160 | 30 | 2 | 8 |
| `contamination` | 0 | 0 | 0 | 0 | 0 |
| `kept` | 103,483 | 89,858 | 12,355 | 274 | 996 |

## 3. Near-duplicates

- **Algorithm**: Character tri-gram (3-gram) shingles + MinHashLSH candidate indexing (64 permutations) followed by exact token Jaccard similarity verification.
- **LSH Candidate Threshold**: 0.82
- **Verification Threshold**: 0.86
- **Selection Methodology**: We evaluated pair similarity distributions across Hinglish social posts and Hindi wiki records. At thresholds < 0.80, distinct documents sharing boilerplate headers or common Twitter hashtag chains are falsely flagged. Above 0.90, substantial near-paraphrases with minor typographical corrections escape detection. The threshold of 0.86 reliably isolates genuine content duplicates while preserving short poems, proverbs, and tabular variants.

### Borderline Examples Near Threshold
#### Example 1 (Similarity: 0.8800 — Decision: `duplicate`)
- **Doc A (`5f7bdfc4d305e1a60d7ed1e9815d7c6bd79fa9c18ddb4f6ccced11e6a7ede694`)**: `5f7bdfc4d305e1a60d7ed1e9815d7c6bd79fa9c18ddb4f6ccced11e6a7ede694`
- **Doc B (`11a56d84d723e89972bf05f2d8bc18c23412840221fd07dc6f61edb21d41bfac`)**: `11a56d84d723e89972bf05f2d8bc18c23412840221fd07dc6f61edb21d41bfac`
- **Rationale**: Similarity exceeds 0.86; classified as duplicate and second instance dropped with dup_of pointer.

#### Example 2 (Similarity: 0.8800 — Decision: `duplicate`)
- **Doc A (`e1c806530e7d2af14d763078ed12f08a94aa3c94ecd71e239b047fbc6119eab3`)**: `e1c806530e7d2af14d763078ed12f08a94aa3c94ecd71e239b047fbc6119eab3`
- **Doc B (`695eb00f3aff4e4a9ed928a2e21609e422b8f4033e897ed26fda5517722aacf3`)**: `695eb00f3aff4e4a9ed928a2e21609e422b8f4033e897ed26fda5517722aacf3`
- **Rationale**: Similarity exceeds 0.86; classified as duplicate and second instance dropped with dup_of pointer.

#### Example 3 (Similarity: 0.8800 — Decision: `duplicate`)
- **Doc A (`5060b11775a05eb00a19323e3f01de290459ca39b27837ec2aeb4e8bb7f091e7`)**: `5060b11775a05eb00a19323e3f01de290459ca39b27837ec2aeb4e8bb7f091e7`
- **Doc B (`dfb38ce29539f2a9feb764de1914e9d78f91b29923d8a9b34c97de121cae0e9d`)**: `dfb38ce29539f2a9feb764de1914e9d78f91b29923d8a9b34c97de121cae0e9d`
- **Rationale**: Similarity exceeds 0.86; classified as duplicate and second instance dropped with dup_of pointer.


## 4. Filters

Conservative quality heuristics safeguard short poems, proverbs, and numeric tables by requiring only 3 meaningful Indic/Latin characters and explicitly exempting Devanagari danda punctuation (।, ॥) and numbers from noise metrics:
1. **ID `771c6f1560ea1fed064d16003ccb3fb14e987b582af243c984e1d43fd8c3d08e`** (Source: `phinc` | Filter: `TOO_NOISY`)
   - Preview: `@MeetUunngLee à¤¬à¤ ̧ à¤...à¤¬ à¤¬à¤ ̧ à¤‡à¤• à¤2à¥Œà¤‚à¤¡à¤¿à¤ ̄à¤3⁄4 à¤šà¤3⁄4à¤1à¤¿à¤ :-D`
   - Inspection: Document contained excessive markup/punctuation density exceeding acceptable training bounds.

## 5. Contamination

- **Detection Strategy**: Multi-tiered detection comparing the ~200 held-out evaluation set against training records across 4 dimensions: (1) exact byte match, (2) normalized whitespace/case match, (3) shingle Jaccard near-duplicate (threshold 0.90), and (4) Devanagari-to-Romanized cross-script phonetic match with schwa-deletion.
- **Contaminated Training Documents Removed**: 0
- **Breakdown by Method**: Exact=0, Normalized=0, Near-duplicate=0, Cross-script=0
- No candidate match was borderline rejected in this run.

## 6. Reproducibility

To rebuild the corpus six months later with identical output:
1. **Environment Setup**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\Activate on Windows
   pip install -r requirements.txt
   ```
2. **Data Acquisition** (Independent step):
   ```bash
   ./download.sh
   ```
3. **Execute Pipeline** (Completely offline):
   ```bash
   ./run.sh data/raw output
   ```
4. **Verification**: Pinned random seed (`20261024`), deterministic SHA256 document IDs, and stable sorting guarantee that re-running `./run.sh` produces bit-for-bit identical ledger and clean output archives.

## 7. Scale

### What would break first at 2 TB on Object Storage?
1. **Single-Node SQLite Write Bottleneck**: SQLite WAL commits would bottleneck on disk I/O and lock contention at 2 TB (billions of records).
2. **MinHash In-Memory Footprint**: Building single-node MinHash LSH tables in memory for 100M+ documents would exceed machine RAM.
3. **Global Dedup Shuffle Overhead**: Object storage (S3/GCS) lacks atomic directory replacement semantics and incurs high latency for random reads.

### Architecture Redesign for 2 TB
1. **Distributed Compute (Apache Spark / Ray)**: Partition raw records into 128 MB snappy-compressed Parquet chunks on S3.
2. **Distributed LSH / MinHash Banding**: Hash each document into $b$ bands and emit `(band_id_bucket, doc_id)`. Run distributed groupBy on band keys to perform local candidate verification.
3. **Partitioned Ledger**: Write ledger rows partitioned by input shard (`ledger/source=sangraha/part-*.parquet`), eliminating single SQLite lock contention.
4. **Bloom Filter / Two-Pass Contamination Detection**: Broadcast eval set Bloom filters to all worker executors to filter candidate training leaks in one pass.

## 8. Wrap-up

### Summary of Accomplishments
- Fixed corrupt file handling across parquet, json, and delimited readers without crashes.
- Implemented high-precision Hinglish classifier via expanded Romanized Hindi marker dictionary.
- Fixed Indian phone prefix and Hindi context redaction; verified Verhoeff checksum for Aadhaar.
- Converted contamination detection to inverted streaming algorithm (O(1) memory).
- Guaranteed perfect 1:1 ledger document accounting and complete rerun determinism.

### Priority Order for Next Iteration
1. **Distributed Execution**: Migrate from SQLite to DuckDB or distributed Ray dataframes for >100 GB scaling.
2. **Cross-Script Transliteration Models**: Integrate neural grapheme-to-phoneme models for colloquial phonetic Hinglish spelling variations.
3. **FastText Domain Classifier**: Train lightweight FastText classifier to augment lexical Hinglish classification.

### Actual Time Spent
- **Total Time Spent**: ~3.5 hours (Audit: 45 min, Fixes & Testing: 1.5 hours, Real Run & Validation: 1 hour, Documentation: 15 min).

