from __future__ import annotations

from pathlib import Path
import gzip
import json

from flam_pipeline.pipeline import run_pipeline


def _write(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def _read_gz(path: Path) -> list[str]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return f.read().splitlines()


def test_pipeline_deterministic_rerun(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    src1 = raw / "src_hi"
    src2 = raw / "src_hilatn"
    src1.mkdir(parents=True)
    src2.mkdir(parents=True)

    # Include valid records, an exact duplicate, malformed JSON, and a corrupt pseudo-parquet file
    _write(
        src1 / "a.jsonl",
        [
            json.dumps({"id": "1", "text": "यह एक परीक्षण वाक्य है"}, ensure_ascii=False),
            json.dumps({"id": "2", "text": "यह एक परीक्षण वाक्य है"}, ensure_ascii=False),
            "{bad-json",
            json.dumps({"id": "3", "text": "मोबाइल 98765 43210"}, ensure_ascii=False),
        ],
    )
    _write(
        src2 / "b.csv",
        [
            "id,text",
            "x1,aaj meeting hai",
            "x2,This is only english text",
        ],
    )
    # Write a corrupt parquet file to ensure malformed parquet does not crash pipeline
    corrupt_parquet = src1 / "corrupt.parquet"
    corrupt_parquet.write_bytes(b"NOT_A_REAL_PARQUET_FILE")

    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"

    run_pipeline(raw, out1)
    run_pipeline(raw, out2)

    # 1. Train outputs must match bit-for-bit
    t1 = _read_gz(out1 / "clean" / "train.jsonl.gz")
    t2 = _read_gz(out2 / "clean" / "train.jsonl.gz")
    assert t1 == t2

    # 2. Ledgers must match bit-for-bit
    l1 = _read_gz(out1 / "ledger.jsonl.gz")
    l2 = _read_gz(out2 / "ledger.jsonl.gz")
    assert l1 == l2

    # 3. Eval holdouts must match bit-for-bit
    e1 = (out1 / "eval.jsonl").read_text(encoding="utf-8")
    e2 = (out2 / "eval.jsonl").read_text(encoding="utf-8")
    assert e1 == e2

    # 4. Manifest output counts must match
    m1 = json.loads((out1 / "manifest.json").read_text(encoding="utf-8"))
    m2 = json.loads((out2 / "manifest.json").read_text(encoding="utf-8"))
    assert m1["output_counts"] == m2["output_counts"]
    assert m1["output_counts"]["malformed_record_count"] >= 2  # {bad-json and corrupt.parquet

    # 5. Verify every kept document in train exists with status='kept' in ledger
    ledger_records = [json.loads(line) for line in l1]
    kept_in_ledger = {r["id"] for r in ledger_records if r["status"] == "kept"}
    train_ids = {json.loads(line)["id"] for line in t1}
    assert train_ids == kept_in_ledger

    # 6. Verify total ledger rows matches total input count
    assert len(ledger_records) == m1["output_counts"]["input_records"]
