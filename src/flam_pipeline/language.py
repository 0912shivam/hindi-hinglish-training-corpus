from __future__ import annotations

from dataclasses import dataclass
import re

from .config import LanguageConfig

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
LATIN_RE = re.compile(r"[A-Za-z]")
WORD_RE = re.compile(r"[\w\u0900-\u097F]+", re.UNICODE)

# High-frequency Romanized Hindi grammatical markers, postpositions, pronouns, verbs and adverbs.
HI_LATN_MARKERS = {
    "hai", "hain", "nahi", "nahin", "kya", "kyu", "kyun", "kyon", "tum", "aap", "mera", "meri", "mere",
    "sab", "sabko", "bahut", "bahot", "acha", "accha", "acchi", "achhe", "shukriya", "namaste", "kaise",
    "kripya", "dost", "yaar", "hum", "hume", "humara", "humari", "humare", "aur", "ka", "ki", "ke",
    "ko", "se", "me", "mein", "par", "pe", "tha", "thi", "the", "raha", "rahe", "rahi", "kar", "kare",
    "karo", "karna", "karke", "kiya", "kiye", "bhi", "yeh", "ye", "voh", "woh", "wo", "ab", "jab", "tab",
    "haan", "uske", "iski", "iska", "unka", "unki", "inke", "unke", "tujhe", "mujhe", "apne", "apna",
    "apni", "kisi", "kuch", "toh", "to", "bhai", "hoga", "hogi", "hoge", "hogaya", "hogayi", "gaya",
    "gayi", "gaye", "tak", "liye", "tera", "teri", "tere", "kaha", "kahan", "jaise", "waise", "aise",
    "mat", "sath", "saath", "lekin", "magar", "hota", "hoti", "hote", "chalo", "chal", "batao", "dekh",
    "dekho", "wale", "wali", "wala", "waala", "waali", "waale", "baat", "log", "karte", "karti", "karta",
    "bolo", "bol", "bhi", "paas", "sirf", "yahan", "wahan", "jab", "bada", "badi", "bade",
}

EN_MARKERS = {
    "the", "and", "is", "are", "of", "to", "in", "for", "that", "with", "this", "as", "on", "from",
    "at", "by", "an", "be", "was", "were", "have", "has", "had", "it", "its", "you", "your",
}


@dataclass(frozen=True)
class LangSignals:
    total_chars: int
    devanagari_chars: int
    latin_chars: int
    hi_hits: int
    en_hits: int



def classify_language(text: str, cfg: LanguageConfig) -> tuple[str, LangSignals]:
    words = [w.lower() for w in WORD_RE.findall(text)]
    total_chars = len(text)
    dev = len(DEVANAGARI_RE.findall(text))
    lat = len(LATIN_RE.findall(text))
    hi_hits = sum(1 for w in words if w in HI_LATN_MARKERS)
    en_hits = sum(1 for w in words if w in EN_MARKERS)

    if total_chars < cfg.min_chars:
        if dev > 0:
            return "hi", LangSignals(total_chars, dev, lat, hi_hits, en_hits)
        return "other", LangSignals(total_chars, dev, lat, hi_hits, en_hits)

    dev_ratio = dev / max(total_chars, 1)
    lat_ratio = lat / max(total_chars, 1)

    # Devanagari-dominant text is Hindi even with English insertion.
    if dev_ratio >= cfg.devanagari_ratio_hi:
        return "hi", LangSignals(total_chars, dev, lat, hi_hits, en_hits)

    # Latin script text can be English or Romanized Hindi.
    if lat_ratio >= cfg.latin_ratio_hilatn:
        if hi_hits >= cfg.min_hi_lexical_hits:
            return "hi-Latn", LangSignals(total_chars, dev, lat, hi_hits, en_hits)
        if en_hits >= cfg.min_en_lexical_hits and hi_hits == 0 and lat_ratio >= cfg.latin_ratio_en:
            return "en", LangSignals(total_chars, dev, lat, hi_hits, en_hits)
        if hi_hits > 0 and en_hits > 0:
            return "hi-Latn", LangSignals(total_chars, dev, lat, hi_hits, en_hits)

    if lat_ratio >= cfg.latin_ratio_en and en_hits >= cfg.min_en_lexical_hits and hi_hits == 0:
        return "en", LangSignals(total_chars, dev, lat, hi_hits, en_hits)

    if dev > 0:
        return "hi", LangSignals(total_chars, dev, lat, hi_hits, en_hits)

    return "other", LangSignals(total_chars, dev, lat, hi_hits, en_hits)
