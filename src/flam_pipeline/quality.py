from __future__ import annotations

from dataclasses import dataclass
import re

from .config import QualityConfig

URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]{1,200}>")
WORD_RE = re.compile(r"[A-Za-z\u0900-\u097F]+")
SYMBOL_RE = re.compile(r"[^\w\s\u0900-\u097F]", re.UNICODE)
PUNCT_RE = re.compile(r"[\.,;:!\?\-\(\)\[\]\{\}/\\|@#%&*_+=~`'\"]")
REPEATED_CHAR_RE = re.compile(r"(.)\1{11,}")
REPLACEMENT_CHAR = "\ufffd"

SPAM_HINTS = (
    "subscribe now",
    "click here",
    "limited offer",
    "buy now",
    "free recharge",
    "visit our channel",
)


@dataclass(frozen=True)
class QualityDecision:
    keep: bool
    reason: str



def assess_quality(text: str, cfg: QualityConfig) -> QualityDecision:
    if not text.strip():
        return QualityDecision(False, "EMPTY_TEXT")

    total = len(text)
    words = WORD_RE.findall(text)
    meaningful_chars = sum(len(w) for w in words)

    if meaningful_chars < cfg.min_meaningful_chars:
        return QualityDecision(False, "NON_LANGUAGE_TEXT")

    url_count = len(URL_RE.findall(text))
    url_ratio = url_count / max(len(text.split()), 1)
    if url_ratio > cfg.max_url_ratio:
        return QualityDecision(False, "URL_HEAVY")

    symbol_ratio = len(SYMBOL_RE.findall(text)) / max(total, 1)
    if symbol_ratio > cfg.max_symbol_ratio:
        return QualityDecision(False, "TOO_NOISY")

    punct_ratio = len(PUNCT_RE.findall(text)) / max(total, 1)
    if punct_ratio > cfg.max_punct_ratio:
        return QualityDecision(False, "TOO_NOISY")

    markup_ratio = len("".join(TAG_RE.findall(text))) / max(total, 1)
    if markup_ratio > cfg.max_markup_ratio:
        return QualityDecision(False, "MARKUP_HEAVY")

    if text.count(REPLACEMENT_CHAR) > cfg.max_replacement_char_count:
        return QualityDecision(False, "GARBLED_ENCODING")

    if REPEATED_CHAR_RE.search(text):
        return QualityDecision(False, "REPEATED_CONTENT")

    lower = text.lower()
    if any(hint in lower for hint in SPAM_HINTS):
        return QualityDecision(False, "SPAM_LIKE")

    alpha_or_indic = sum(ch.isalpha() or ("\u0900" <= ch <= "\u097f") for ch in text)
    if alpha_or_indic / max(total, 1) < cfg.min_alpha_or_indic_ratio:
        # Keep short but meaningful numeric + text patterns, like proverb prefixes.
        if len(words) >= 2:
            return QualityDecision(True, "ACCEPTED")
        return QualityDecision(False, "NON_LANGUAGE_TEXT")

    return QualityDecision(True, "ACCEPTED")
