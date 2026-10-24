from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator
import csv
import json
import logging
import re

import pyarrow.parquet as pq

try:
    import ijson  # type: ignore
except Exception:  # pragma: no cover - fallback path
    ijson = None

from .models import RawRecord
from .utils import iter_files, maybe_open_text

LOGGER = logging.getLogger(__name__)

TEXT_FIELD_HINTS = (
    "text",
    "content",
    "body",
    "sentence",
    "comment",
    "message",
    "post",
    "caption",
    "description",
    "headline",
    "title",
    "article",
)


class MalformedRecordError(Exception):
    pass


def stream_raw_records(raw_dir: Path) -> Iterator[RawRecord]:
    for file_path in iter_files(raw_dir):
        source_name = file_path.parent.name or "unknown"
        suffixes = "".join(file_path.suffixes[-2:]).lower()
        lower_name = file_path.name.lower()

        try:
            if lower_name.endswith(".jsonl") or lower_name.endswith(".jsonl.gz"):
                yield from _iter_jsonl(file_path, source_name)
            elif lower_name.endswith(".json") or lower_name.endswith(".json.gz"):
                yield from _iter_json(file_path, source_name)
            elif lower_name.endswith(".parquet"):
                yield from _iter_parquet(file_path, source_name)
            elif lower_name.endswith(".csv") or lower_name.endswith(".csv.gz"):
                yield from _iter_delimited(file_path, source_name, delimiter=",")
            elif lower_name.endswith(".tsv") or lower_name.endswith(".tsv.gz"):
                yield from _iter_delimited(file_path, source_name, delimiter="\t")
            elif lower_name.endswith(".txt") or lower_name.endswith(".txt.gz") or ".xml" in suffixes:
                yield from _iter_text_lines(file_path, source_name)
            else:
                LOGGER.info("Skipping unsupported file format: %s", file_path)
        except Exception as e:
            LOGGER.warning("Unexpected error reading file %s: %s", file_path, e)
            yield RawRecord(
                source_name=source_name,
                file_path=file_path,
                line_no=None,
                record_index=1,
                payload={"__malformed__": True, "error": str(e)},
            )


def _iter_jsonl(file_path: Path, source_name: str) -> Iterator[RawRecord]:
    with maybe_open_text(file_path) as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as e:
                payload = {"__malformed__": True, "raw_line": line, "error": str(e)}
            yield RawRecord(source_name=source_name, file_path=file_path, line_no=i, record_index=i, payload=payload)


def _iter_json(file_path: Path, source_name: str) -> Iterator[RawRecord]:
    if ijson is not None:
        try:
            with maybe_open_text(file_path) as f:
                try:
                    first = next(ijson.parse(f))
                    f.seek(0)
                except Exception:
                    first = None
                    f.seek(0)

                if first and first[1] == "start_array":
                    for i, payload in enumerate(ijson.items(f, "item"), start=1):
                        yield RawRecord(source_name=source_name, file_path=file_path, line_no=None, record_index=i, payload=payload)
                    return

                if first and first[1] == "start_map":
                    obj = next(ijson.items(f, ""), None)
                    if isinstance(obj, dict):
                        records = obj.get("data") or obj.get("records")
                        if isinstance(records, list):
                            for i, payload in enumerate(records, start=1):
                                yield RawRecord(source_name=source_name, file_path=file_path, line_no=None, record_index=i, payload=payload)
                            return
                        yield RawRecord(source_name=source_name, file_path=file_path, line_no=None, record_index=1, payload=obj)
                        return
        except Exception as e:
            LOGGER.warning("ijson parse error in %s: %s", file_path, e)
            yield RawRecord(
                source_name=source_name,
                file_path=file_path,
                line_no=None,
                record_index=1,
                payload={"__malformed__": True, "error": str(e)},
            )
            return

    # Fallback for environments where ijson is unavailable.
    try:
        with maybe_open_text(file_path) as f:
            data = json.load(f)
    except Exception as e:
        LOGGER.warning("Malformed JSON file %s: %s", file_path, e)
        yield RawRecord(
            source_name=source_name,
            file_path=file_path,
            line_no=None,
            record_index=1,
            payload={"__malformed__": True, "error": str(e)},
        )
        return

    iterable: list[Any]
    if isinstance(data, dict):
        records = data.get("data") if isinstance(data.get("data"), list) else data.get("records")
        if isinstance(records, list):
            iterable = records
        else:
            iterable = [data]
    elif isinstance(data, list):
        iterable = data
    else:
        iterable = [{"text": str(data)}]

    for i, payload in enumerate(iterable, start=1):
        yield RawRecord(source_name=source_name, file_path=file_path, line_no=None, record_index=i, payload=payload)


def _iter_parquet(file_path: Path, source_name: str) -> Iterator[RawRecord]:
    try:
        pf = pq.ParquetFile(str(file_path))
    except Exception as e:
        LOGGER.warning("Malformed or corrupted parquet file %s: %s", file_path, e)
        yield RawRecord(
            source_name=source_name,
            file_path=file_path,
            line_no=None,
            record_index=1,
            payload={"__malformed__": True, "error": str(e)},
        )
        return

    idx = 0
    try:
        for batch in pf.iter_batches(batch_size=1024):
            rows = batch.to_pylist()
            for payload in rows:
                idx += 1
                yield RawRecord(source_name=source_name, file_path=file_path, line_no=None, record_index=idx, payload=payload)
    except Exception as e:
        LOGGER.warning("Error reading parquet batch in %s: %s", file_path, e)
        idx += 1
        yield RawRecord(
            source_name=source_name,
            file_path=file_path,
            line_no=None,
            record_index=idx,
            payload={"__malformed__": True, "error": str(e)},
        )


def _iter_delimited(file_path: Path, source_name: str, delimiter: str) -> Iterator[RawRecord]:
    try:
        with maybe_open_text(file_path) as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for i, row in enumerate(reader, start=1):
                if row is None:
                    yield RawRecord(
                        source_name=source_name,
                        file_path=file_path,
                        line_no=i,
                        record_index=i,
                        payload={"__malformed__": True, "raw_line": ""},
                    )
                    continue
                yield RawRecord(source_name=source_name, file_path=file_path, line_no=i, record_index=i, payload=row)
    except Exception as e:
        LOGGER.warning("Error reading delimited file %s: %s", file_path, e)
        yield RawRecord(
            source_name=source_name,
            file_path=file_path,
            line_no=None,
            record_index=1,
            payload={"__malformed__": True, "error": str(e)},
        )


def _iter_text_lines(file_path: Path, source_name: str) -> Iterator[RawRecord]:
    try:
        with maybe_open_text(file_path) as f:
            for i, line in enumerate(f, start=1):
                text = line.strip()
                if not text:
                    continue
                yield RawRecord(
                    source_name=source_name,
                    file_path=file_path,
                    line_no=i,
                    record_index=i,
                    payload={"text": _collapse_xml_like(text)},
                )
    except Exception as e:
        LOGGER.warning("Error reading text file %s: %s", file_path, e)
        yield RawRecord(
            source_name=source_name,
            file_path=file_path,
            line_no=None,
            record_index=1,
            payload={"__malformed__": True, "error": str(e)},
        )


def discover_text(payload: Any) -> str:
    if payload is None:
        return ""

    if isinstance(payload, str):
        return payload

    if isinstance(payload, (int, float, bool)):
        return str(payload)

    if isinstance(payload, list):
        candidates = [discover_text(x) for x in payload]
        return "\n".join([c for c in candidates if c.strip()])

    if isinstance(payload, dict):
        if payload.get("__malformed__"):
            return ""

        # Priority 1: field-name hints sorted by relevance and key name.
        keyed: list[tuple[int, str, str]] = []
        for k, v in payload.items():
            if not isinstance(v, str):
                continue
            lk = k.lower()
            score = 0
            for idx, hint in enumerate(TEXT_FIELD_HINTS):
                if hint in lk:
                    score = 100 - idx
                    break
            keyed.append((score, k, v))

        keyed.sort(key=lambda x: (-x[0], x[1]))
        for score, _, value in keyed:
            if score > 0 and _is_reasonable_text_candidate(value):
                return value

        # Priority 2: longest meaningful string value.
        string_values = [v for v in payload.values() if isinstance(v, str)]
        string_values.sort(key=len, reverse=True)
        for value in string_values:
            if _is_reasonable_text_candidate(value):
                return value

    return ""


def _is_reasonable_text_candidate(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) < 2:
        return False
    letters = sum(ch.isalpha() for ch in stripped)
    digits = sum(ch.isdigit() for ch in stripped)
    return letters >= 2 or (letters >= 1 and digits >= 2)


def _collapse_xml_like(text: str) -> str:
    # Keep text content while dropping simple tags.
    text_no_tags = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text_no_tags).strip()
