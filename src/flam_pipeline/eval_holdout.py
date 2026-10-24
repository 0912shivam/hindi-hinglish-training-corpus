from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import hashlib
import heapq

from .config import EvalConfig
from .models import CleanDocument


@dataclass(frozen=True)
class EvalItem:
    eval_id: str
    text: str
    lang: str
    source: str
    train_doc_id: str



def select_eval_holdout(docs: Iterable[CleanDocument], cfg: EvalConfig) -> tuple[list[EvalItem], set[str]]:
    target = cfg.holdout_size
    hi_latn_take = cfg.min_hilatn_target
    other_take = 10
    hi_take = max(0, target - hi_latn_take - other_take)

    hi_heap: list[tuple[int, str, CleanDocument]] = []
    hl_heap: list[tuple[int, str, CleanDocument]] = []
    ot_heap: list[tuple[int, str, CleanDocument]] = []
    all_heap: list[tuple[int, str, CleanDocument]] = []

    total_seen = 0
    for doc in docs:
        total_seen += 1
        s_hex = _score(doc.id, cfg.random_seed)
        score = int(s_hex, 16)
        entry = (-score, doc.id, doc)
        _bounded_push(all_heap, entry, target)
        if doc.lang == "hi":
            _bounded_push(hi_heap, entry, hi_take)
        elif doc.lang == "hi-Latn":
            _bounded_push(hl_heap, entry, hi_latn_take)
        else:
            _bounded_push(ot_heap, entry, other_take)

    effective_target = min(target, total_seen)
    chosen_map: dict[str, CleanDocument] = {}
    for heap in (hi_heap, hl_heap, ot_heap):
        for _, _, doc in heap:
            chosen_map[doc.id] = doc

    if len(chosen_map) < effective_target:
        all_docs_sorted = sorted((d for _, _, d in all_heap), key=lambda d: _score(d.id, cfg.random_seed))
        for doc in all_docs_sorted:
            if len(chosen_map) >= effective_target:
                break
            chosen_map.setdefault(doc.id, doc)

    chosen = sorted(chosen_map.values(), key=lambda d: _score(d.id, cfg.random_seed))

    eval_items: list[EvalItem] = []
    held_out_ids: set[str] = set()
    for i, doc in enumerate(chosen, start=1):
        eval_items.append(
            EvalItem(
                eval_id=f"eval-{i:04d}",
                text=doc.text,
                lang=doc.lang,
                source=doc.source,
                train_doc_id=doc.id,
            )
        )
        held_out_ids.add(doc.id)

    return eval_items, held_out_ids


def _score(doc_id: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}:{doc_id}".encode("utf-8")).hexdigest()


def _bounded_push(heap: list[tuple[int, str, CleanDocument]], item: tuple[int, str, CleanDocument], k: int) -> None:
    if k <= 0:
        return
    if len(heap) < k:
        heapq.heappush(heap, item)
        return
    if item > heap[0]:
        heapq.heapreplace(heap, item)
