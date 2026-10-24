from flam_pipeline.config import QualityConfig
from flam_pipeline.quality import assess_quality


def test_empty_text_dropped() -> None:
    out = assess_quality("   ", QualityConfig())
    assert not out.keep
    assert out.reason == "EMPTY_TEXT"


def test_markup_heavy_dropped() -> None:
    text = "<div><a href='x'>link</a></div> <span>menu</span>"
    out = assess_quality(text, QualityConfig())
    assert not out.keep


def test_spam_like_dropped() -> None:
    out = assess_quality("Click here buy now limited offer free recharge", QualityConfig())
    assert not out.keep


def test_short_meaningful_hindi_kept() -> None:
    out = assess_quality("सत्यमेव जयते", QualityConfig())
    assert out.keep
