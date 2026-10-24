from __future__ import annotations

from dataclasses import dataclass
import re

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
AADHAAR_RE = re.compile(r"\b(?:\d{4}[ -]\d{4}[ -]\d{4}|\d{12})\b")
AADHAAR_CONTEXT_RE = re.compile(r"\b(aadhaar|aadhar|uidai|uid|आधार)\b", re.IGNORECASE)
PHONE_CONTEXT_RE = re.compile(
    r"\b(phone|mobile|mob|contact|tel|call|whatsapp|ph|no|num|number|फ़ोन|फोन|मोबाइल|सम्पर्क|संपर्क|कॉल|नंबर)\b",
    re.IGNORECASE,
)
PHONE_CANDIDATE_RE = re.compile(
    r"(?<!\d)(?:\+91[ -]?)?(?:0[ -]?)?([6-9]\d(?:[ -]?\d){8})(?!\d)"
)


@dataclass(frozen=True)
class PiiResult:
    text: str
    redaction_count: int
    by_type: dict[str, int]


# Verhoeff tables for Aadhaar checksum validation.
_D_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_P_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_INV_TABLE = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def redact_pii(text: str) -> PiiResult:
    by_type: dict[str, int] = {"EMAIL": 0, "PAN": 0, "AADHAAR": 0, "PHONE": 0}

    def repl_email(match: re.Match[str]) -> str:
        by_type["EMAIL"] += 1
        return "<EMAIL>"

    def repl_pan(match: re.Match[str]) -> str:
        by_type["PAN"] += 1
        return "<PAN>"

    def repl_aadhaar(match: re.Match[str]) -> str:
        raw = re.sub(r"[ -]", "", match.group(0))
        if len(raw) == 12 and raw[0] not in ("0", "1") and _verhoeff_is_valid(raw):
            # Formatted Aadhaar (xxxx xxxx xxxx) is distinct; continuous 12-digit numbers
            # require Aadhaar context to avoid over-redacting random 12-digit integers.
            if " " in match.group(0) or "-" in match.group(0):
                by_type["AADHAAR"] += 1
                return "<AADHAAR>"
            start, end = match.span()
            snippet = text[max(0, start - 30) : min(len(text), end + 30)]
            if AADHAAR_CONTEXT_RE.search(snippet):
                by_type["AADHAAR"] += 1
                return "<AADHAAR>"
        return match.group(0)

    text = EMAIL_RE.sub(repl_email, text)
    text = PAN_RE.sub(repl_pan, text)
    text = AADHAAR_RE.sub(repl_aadhaar, text)

    # For phone numbers, require either explicit context nearby or country-code/prefix formatting.
    redacted_parts: list[str] = []
    last = 0
    for match in PHONE_CANDIDATE_RE.finditer(text):
        start, end = match.span()
        digits = re.sub(r"\D", "", match.group(1))
        if len(digits) != 10:
            continue
        snippet_start = max(0, start - 30)
        snippet_end = min(len(text), end + 30)
        context = text[snippet_start:snippet_end]
        has_context = bool(PHONE_CONTEXT_RE.search(context))
        matched_str = match.group(0).strip()
        has_prefix = (
            matched_str.startswith("+91")
            or matched_str.startswith("0")
            or text[max(0, start - 4) : start].strip().startswith("+91")
            or text[max(0, start - 2) : start].strip() == "0"
        )

        if has_context or has_prefix:
            redacted_parts.append(text[last:start])
            redacted_parts.append("<PHONE>")
            last = end
            by_type["PHONE"] += 1

    if by_type["PHONE"] > 0:
        redacted_parts.append(text[last:])
        text = "".join(redacted_parts)

    total = sum(by_type.values())
    return PiiResult(text=text, redaction_count=total, by_type=by_type)


def _verhoeff_is_valid(number: str) -> bool:
    if not number.isdigit() or len(number) != 12:
        return False
    c = 0
    for i, item in enumerate(reversed(number)):
        c = _D_TABLE[c][_P_TABLE[i % 8][int(item)]]
    return c == 0
