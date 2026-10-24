from __future__ import annotations

from pathlib import Path
import re
import unicodedata

from .config import PipelineConfig
from .models import RawRecord
from .utils import deterministic_hash

# Control chars excluding line breaks and tabs.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_ZERO_WIDTH_RE = re.compile(r"[\u200B\u200C\u200D\u2060\uFEFF]")
_WS_RE = re.compile(r"[ \t\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]+")
_LINEBREAK_RE = re.compile(r"\r\n?|\u2028|\u2029")


def make_doc_id(raw: RawRecord, text_hint: str, root: Path | None = None) -> str:
    source = raw.source_name
    if root is not None:
        try:
            rel_file = raw.file_path.relative_to(root).as_posix()
        except ValueError:
            rel_file = str(raw.file_path).replace("\\", "/")
    else:
        rel_file = str(raw.file_path).replace("\\", "/")
    line = str(raw.line_no) if raw.line_no is not None else str(raw.record_index)

    record_id = ""
    if isinstance(raw.payload, dict):
        for key in ("id", "doc_id", "uuid", "guid", "record_id"):
            value = raw.payload.get(key)
            if value is not None and str(value).strip():
                record_id = str(value).strip()
                break

    if record_id:
        seed = deterministic_hash(source, rel_file, line, record_id)
    else:
        seed = deterministic_hash(source, rel_file, line, text_hint.strip()[:1024])
    return seed


def normalize_text(text: str, cfg: PipelineConfig) -> str:
    if not text:
        return ""

    text = text.replace("\ufeff", "")
    text = unicodedata.normalize(cfg.unicode_form, text)
    text = _LINEBREAK_RE.sub("\n", text)
    text = _ZERO_WIDTH_RE.sub("", text)
    text = _CONTROL_RE.sub("", text)
    text = _WS_RE.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip spaces around line breaks without removing meaningful lines.
    text = "\n".join(part.strip() for part in text.split("\n"))
    text = re.sub(r"\n[ \t]+", "\n", text)
    return text.strip()


def raw_record_ref(raw: RawRecord, root: Path | None = None) -> str:
    path = raw.file_path
    if root is not None:
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = str(path).replace("\\", "/")
    else:
        rel = str(path).replace("\\", "/")
    if raw.line_no is None:
        return f"{rel}#idx={raw.record_index}"
    return f"{rel}#line={raw.line_no}"
