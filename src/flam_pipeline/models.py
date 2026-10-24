from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceMetadata:
    name: str
    url: str
    license: str
    download_date: str
    local_path: str
    notes: str = ""


@dataclass(frozen=True)
class RawRecord:
    source_name: str
    file_path: Path
    line_no: int | None
    record_index: int
    payload: Any


@dataclass(frozen=True)
class ParsedDocument:
    id: str
    source: str
    raw_text: str
    raw_record_ref: str


@dataclass(frozen=True)
class CleanDocument:
    id: str
    text: str
    lang: str
    source: str


@dataclass(frozen=True)
class LedgerRow:
    id: str
    status: str
    stage: str
    reason: str
    dup_of: str = ""


@dataclass
class PipelineStats:
    input_records: int = 0
    parsed_records: int = 0
    kept_records: int = 0
    malformed_records: int = 0
    pii_redactions: int = 0
    exact_dedup_drops: int = 0
    near_dedup_drops: int = 0
    contamination_drops: int = 0
    by_language: dict[str, int] = field(default_factory=dict)
    by_stage: dict[str, int] = field(default_factory=dict)
    by_source: dict[str, int] = field(default_factory=dict)

    def bump_lang(self, lang: str) -> None:
        self.by_language[lang] = self.by_language.get(lang, 0) + 1

    def bump_stage(self, stage: str) -> None:
        self.by_stage[stage] = self.by_stage.get(stage, 0) + 1

    def bump_source(self, source: str) -> None:
        self.by_source[source] = self.by_source.get(source, 0) + 1
