from __future__ import annotations

from pathlib import Path
from typing import Iterator
import gzip
import hashlib
import json
import logging
import os
import shutil
import tempfile

LOGGER = logging.getLogger(__name__)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def iter_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def write_jsonl_gz(path: Path, rows: Iterator[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False))
            f.write("\n")


def write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_json(path: Path) -> dict | list:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def atomic_replace_dir(src_dir: Path, final_dir: Path) -> None:
    if final_dir.exists():
        backup = Path(tempfile.mkdtemp(prefix="flam_backup_", dir=str(final_dir.parent)))
        final_dir.replace(backup / final_dir.name)
        shutil.rmtree(backup, ignore_errors=True)
    src_dir.replace(final_dir)


def deterministic_hash(*parts: str) -> str:
    joined = "\u241f".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def ensure_empty_temp_out(base_out: Path) -> Path:
    base_out.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="run_", dir=str(base_out)))
    LOGGER.info("Using temporary output directory: %s", temp_dir)
    return temp_dir


def maybe_open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="")
    return path.open("r", encoding="utf-8", errors="replace", newline="")


def filesize(path: Path) -> int:
    return os.path.getsize(path)
