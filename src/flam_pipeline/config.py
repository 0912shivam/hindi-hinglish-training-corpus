from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True)
class LanguageConfig:
    min_chars: int = 8
    devanagari_ratio_hi: float = 0.45
    latin_ratio_en: float = 0.70
    latin_ratio_hilatn: float = 0.55
    min_hi_lexical_hits: int = 1
    min_en_lexical_hits: int = 2


@dataclass(frozen=True)
class QualityConfig:
    min_meaningful_chars: int = 3
    max_url_ratio: float = 0.35
    max_symbol_ratio: float = 0.40
    max_punct_ratio: float = 0.55
    max_replacement_char_count: int = 3
    max_repeat_run: int = 12
    max_markup_ratio: float = 0.30
    min_alpha_or_indic_ratio: float = 0.20


@dataclass(frozen=True)
class NearDedupConfig:
    shingle_size: int = 3
    num_perm: int = 64
    lsh_threshold: float = 0.82
    verify_threshold: float = 0.86
    max_chars_for_shingles: int = 2000
    max_tokens_for_shingles: int = 200


@dataclass(frozen=True)
class EvalConfig:
    holdout_size: int = 200
    random_seed: int = 20261024
    min_hilatn_target: int = 30


@dataclass(frozen=True)
class PipelineConfig:
    version: str = "0.1.0"
    unicode_form: str = "NFKC"
    deterministic_seed: int = 20261024
    language: LanguageConfig = LanguageConfig()
    quality: QualityConfig = QualityConfig()
    near_dedup: NearDedupConfig = NearDedupConfig()
    eval: EvalConfig = EvalConfig()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_sources_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"sources metadata must be a list: {path}")
    return data
