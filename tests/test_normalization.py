from flam_pipeline.config import PipelineConfig
from flam_pipeline.normalize import normalize_text


def test_unicode_and_zero_width_normalization() -> None:
    cfg = PipelineConfig()
    text = "\ufeffनमस्ते\u200b\u200d  दुनिया\r\n\t"
    out = normalize_text(text, cfg)
    assert out == "नमस्ते दुनिया"


def test_whitespace_collapse() -> None:
    cfg = PipelineConfig()
    text = "hello\u00a0\u00a0world   \n\n\nnew"
    out = normalize_text(text, cfg)
    assert out == "hello world\n\nnew"
