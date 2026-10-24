from __future__ import annotations

from dataclasses import dataclass
import re

from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

from .eval_holdout import EvalItem
from .models import CleanDocument


@dataclass(frozen=True)
class ContaminationRow:
    eval_id: str
    train_ids: list[str]
    method: str


_WORD_RE = re.compile(r"[a-zA-Z\u0900-\u097f]+")



def detect_contamination(
    eval_items: list[EvalItem],
    training_docs: Iterable[CleanDocument],
    near_threshold: float = 0.90,
) -> tuple[list[ContaminationRow], set[str], dict[str, int], dict[str, str] | None]:
    """
    Streaming contamination detector.
    Indexes the ~200 held-out evaluation items (exact, normalized, character 3-grams,
    and Romanized cross-script equivalents) and streams training documents past the index.
    This avoids loading the entire training corpus into memory while executing in O(N_train).
    """
    eval_by_exact: dict[str, list[str]] = {}
    eval_by_norm: dict[str, list[str]] = {}
    eval_shingles: dict[str, set[str]] = {}
    eval_inverted: dict[str, set[str]] = {}

    cross_eval_info: dict[str, tuple[str, set[str]]] = {}
    cross_inverted: dict[str, set[str]] = {}

    for item in eval_items:
        eid = item.eval_id
        eval_by_exact.setdefault(item.text, []).append(eid)
        norm = _simple_norm(item.text)
        eval_by_norm.setdefault(norm, []).append(eid)

        sh = _shingles(item.text, k=3)
        eval_shingles[eid] = sh
        for s in sh:
            eval_inverted.setdefault(s, set()).add(eid)

        if item.lang == "hi":
            roman = _romanize_hindi(item.text)
            r_shingles = _shingles(roman, k=3)
            cross_eval_info[eid] = (item.text, r_shingles)
            for s in r_shingles:
                cross_inverted.setdefault(s, set()).add(eid)

    eval_lengths = {eid: len(sh) for eid, sh in eval_shingles.items()}
    cross_lengths = {eid: len(r_sh) for eid, (_, r_sh) in cross_eval_info.items()}

    matches: dict[str, dict[str, list[str]]] = {}
    rejected_candidate: dict[str, str] | None = None

    for doc in training_docs:
        # 1. Exact copy check
        exact_eids = eval_by_exact.get(doc.text)
        if exact_eids:
            for eid in exact_eids:
                matches.setdefault(eid, {}).setdefault("exact", []).append(doc.id)

        # 2. Normalized copy check
        doc_norm = _simple_norm(doc.text)
        norm_eids = eval_by_norm.get(doc_norm)
        if norm_eids:
            for eid in norm_eids:
                matches.setdefault(eid, {}).setdefault("normalized", []).append(doc.id)

        # 3. Near-duplicate check via candidate shingle lookup
        t_shingles = _shingles(doc.text, k=3)
        t_len = len(t_shingles)
        candidate_eids: set[str] = set()
        for s in t_shingles:
            matched_eids = eval_inverted.get(s)
            if matched_eids:
                candidate_eids.update(matched_eids)

        for eid in candidate_eids:
            e_len = eval_lengths[eid]
            if not e_len or min(t_len, e_len) / max(t_len, e_len) < near_threshold:
                continue
            sim = _jaccard(t_shingles, eval_shingles[eid])
            if sim >= near_threshold:
                matches.setdefault(eid, {}).setdefault("near_duplicate", []).append(doc.id)

        # 4. Cross-script check: Latin training text against Romanized Hindi eval items
        if doc.lang in {"hi-Latn", "other"} and cross_eval_info:
            doc_roman = _simple_norm(doc.text)
            doc_sh_roman = _shingles(doc_roman, k=3)
            d_len = len(doc_sh_roman)
            candidate_cross_eids: set[str] = set()
            for s in doc_sh_roman:
                matched_cross = cross_inverted.get(s)
                if matched_cross:
                    candidate_cross_eids.update(matched_cross)

            for eid in candidate_cross_eids:
                orig_text, r_shingles = cross_eval_info[eid]
                r_len = cross_lengths[eid]
                if not r_len or min(d_len, r_len) / max(d_len, r_len) < 0.70:
                    continue
                sim = _jaccard(doc_sh_roman, r_shingles)
                if sim >= 0.80:
                    matches.setdefault(eid, {}).setdefault("cross_script", []).append(doc.id)
                elif rejected_candidate is None and sim >= 0.70:
                    rejected_candidate = {
                        "eval_text": orig_text[:160],
                        "train_id": doc.id,
                        "train_text": doc.text[:160],
                        "similarity": f"{sim:.4f}",
                        "reason": "Below conservative cross-script threshold",
                    }

    rows: list[ContaminationRow] = []
    contaminated_train_ids: set[str] = set()
    for item in eval_items:
        eid = item.eval_id
        if eid not in matches:
            continue
        for method in sorted(matches[eid].keys()):
            train_ids = sorted(set(matches[eid][method]))
            for tid in train_ids:
                contaminated_train_ids.add(tid)
            rows.append(ContaminationRow(eval_id=eid, train_ids=train_ids, method=method))

    counts = {
        "exact": sum(1 for r in rows if r.method == "exact"),
        "normalized": sum(1 for r in rows if r.method == "normalized"),
        "near_duplicate": sum(1 for r in rows if r.method == "near_duplicate"),
        "cross_script": sum(1 for r in rows if r.method == "cross_script"),
        "affected_eval_items": len({r.eval_id for r in rows}),
    }
    return rows, contaminated_train_ids, counts, rejected_candidate


def _simple_norm(text: str) -> str:
    return " ".join(text.lower().split())


def _shingles(text: str, k: int = 3) -> set[str]:
    t = _simple_norm(text)
    if len(t) < k:
        return {t} if t else set()
    return {t[i : i + k] for i in range(len(t) - k + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _romanize_hindi(text: str) -> str:
    try:
        out = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS).lower()
    except Exception:
        out = text.lower()
    words = _WORD_RE.findall(out)
    norm_words: list[str] = []
    for w in words:
        if len(w) > 2 and w.endswith("a") and not w.endswith("aa"):
            w = w[:-1]
        norm_words.append(w)
    return " ".join(norm_words)
