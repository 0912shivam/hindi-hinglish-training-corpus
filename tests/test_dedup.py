from pathlib import Path

from flam_pipeline.config import NearDedupConfig
from flam_pipeline.dedup_exact import ExactDeduper
from flam_pipeline.near_dedup import NearDeduper


def test_exact_dedup(tmp_path: Path) -> None:
    db = tmp_path / "exact.sqlite"
    d = ExactDeduper(db)
    ok1, c1 = d.check_or_add("h1", "doc1")
    ok2, c2 = d.check_or_add("h1", "doc2")
    d.close()
    assert ok1 and c1 == "doc1"
    assert not ok2 and c2 == "doc1"


def test_near_dedup(tmp_path: Path) -> None:
    db = tmp_path / "near.sqlite"
    cfg = NearDedupConfig(verify_threshold=0.8)
    d = NearDeduper(db, cfg)
    first = d.check_or_add("doc1", "यह एक महत्वपूर्ण हिंदी वाक्य है")
    second = d.check_or_add("doc2", "यह एक महत्वपूर्ण हिंदी वाक्य है।")
    d.close()
    assert first.keep
    assert not second.keep
