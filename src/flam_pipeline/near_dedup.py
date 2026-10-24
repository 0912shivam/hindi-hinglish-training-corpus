from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import json
import re
import sqlite3

from datasketch import MinHash, MinHashLSH

from .config import NearDedupConfig


@dataclass(frozen=True)
class NearDedupDecision:
    keep: bool
    dup_of: str
    similarity: float


@dataclass(frozen=True)
class SimilarityExample:
    left_id: str
    right_id: str
    similarity: float
    decision: str


class NearDeduper:
    def __init__(self, db_path: Path, cfg: NearDedupConfig) -> None:
        self.cfg = cfg
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._pending = 0
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS near_docs (
                doc_id TEXT PRIMARY KEY,
                shingles_json TEXT NOT NULL,
                text_preview TEXT NOT NULL
            )
            """
        )
        self.conn.commit()
        self.lsh = MinHashLSH(threshold=cfg.lsh_threshold, num_perm=cfg.num_perm)
        self.examples: list[SimilarityExample] = []

    def check_or_add(self, doc_id: str, text: str) -> NearDedupDecision:
        shingles = _shingles(
            text,
            self.cfg.shingle_size,
            max_chars=self.cfg.max_chars_for_shingles,
            max_tokens=self.cfg.max_tokens_for_shingles,
        )
        if not shingles:
            self._insert_doc(doc_id, shingles, text)
            return NearDedupDecision(True, doc_id, 0.0)

        mh = _minhash(shingles, self.cfg.num_perm)
        candidates = sorted(self.lsh.query(mh))

        best_id = ""
        best_sim = 0.0
        for cand_id in candidates:
            cand_shingles = self._load_shingles(cand_id)
            sim = _jaccard(shingles, cand_shingles)
            if sim > best_sim:
                best_sim = sim
                best_id = cand_id

        if best_id:
            decision = "duplicate" if best_sim >= self.cfg.verify_threshold else "keep"
            self._record_example(doc_id, best_id, best_sim, decision)

        if best_id and best_sim >= self.cfg.verify_threshold:
            return NearDedupDecision(False, best_id, best_sim)

        if doc_id in self.lsh:
            return NearDedupDecision(False, doc_id, 1.0)
        self.lsh.insert(doc_id, mh, check_duplication=False)
        self._insert_doc(doc_id, shingles, text)
        return NearDedupDecision(True, doc_id, best_sim)

    def threshold_examples(self, limit: int = 20) -> list[SimilarityExample]:
        lower = max(0.50, self.cfg.verify_threshold - 0.15)
        upper = min(1.00, self.cfg.verify_threshold + 0.10)
        near = [e for e in self.examples if lower <= e.similarity <= upper]
        if len(near) < 3 and self.examples:
            near = sorted(self.examples, key=lambda e: abs(e.similarity - self.cfg.verify_threshold))
        else:
            near.sort(key=lambda e: abs(e.similarity - self.cfg.verify_threshold))
        return near[:limit]

    def _record_example(self, left: str, right: str, similarity: float, decision: str) -> None:
        self.examples.append(
            SimilarityExample(
                left_id=left,
                right_id=right,
                similarity=round(similarity, 4),
                decision=decision,
            )
        )

    def _insert_doc(self, doc_id: str, shingles: set[str], text: str) -> None:
        preview = text[:180].replace("\n", " ")
        self.conn.execute(
            "INSERT OR REPLACE INTO near_docs (doc_id, shingles_json, text_preview) VALUES (?, ?, ?)",
            (doc_id, json.dumps(sorted(shingles), ensure_ascii=False), preview),
        )
        self._pending += 1
        if self._pending >= 1000:
            self.conn.commit()
            self._pending = 0

    def _load_shingles(self, doc_id: str) -> set[str]:
        cur = self.conn.execute("SELECT shingles_json FROM near_docs WHERE doc_id = ?", (doc_id,))
        row = cur.fetchone()
        if not row:
            return set()
        return set(json.loads(str(row[0])))

    def get_preview(self, doc_id: str) -> str:
        cur = self.conn.execute("SELECT text_preview FROM near_docs WHERE doc_id = ?", (doc_id,))
        row = cur.fetchone()
        return "" if not row else str(row[0])

    def close(self) -> None:
        if self._pending:
            self.conn.commit()
            self._pending = 0
        self.conn.close()


_TOKEN_RE = re.compile(r"[A-Za-z0-9\u0900-\u097f]+", re.UNICODE)
_STRIP_CHARS = ".,;:!?\"'`()[]{}<>|/\\-_=+~`।॥"


def _shingles(text: str, size: int, max_chars: int, max_tokens: int) -> set[str]:
    normalized = " ".join(text.lower().split())
    clipped = normalized[:max_chars]
    raw_tokens = _TOKEN_RE.findall(clipped)
    tokens = [tok.strip(_STRIP_CHARS) for tok in raw_tokens]
    tokens = [tok for tok in tokens if tok]
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]

    if not tokens:
        return set()
    if len(tokens) < size:
        return {" ".join(tokens)}
    return {" ".join(tokens[i : i + size]) for i in range(len(tokens) - size + 1)}


def _minhash(shingles: Iterable[str], num_perm: int) -> MinHash:
    mh = MinHash(num_perm=num_perm)
    for shingle in shingles:
        mh.update(shingle.encode("utf-8"))
    return mh


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
