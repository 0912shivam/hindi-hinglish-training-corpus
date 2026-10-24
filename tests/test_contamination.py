from flam_pipeline.contamination import detect_contamination
from flam_pipeline.eval_holdout import EvalItem
from flam_pipeline.models import CleanDocument


def test_detect_exact_and_cross_script_contamination() -> None:
    eval_items = [
        EvalItem(eval_id="eval-0001", text="यह बहुत अच्छा दिन है", lang="hi", source="s1", train_doc_id="x"),
    ]
    training = [
        CleanDocument(id="t1", text="यह बहुत अच्छा दिन है", lang="hi", source="s1"),
        CleanDocument(id="t2", text="yah bahut accha din hai", lang="hi-Latn", source="s2"),
    ]
    rows, contaminated, counts, _ = detect_contamination(eval_items, training, near_threshold=0.8)
    methods = {r.method for r in rows}
    assert "exact" in methods
    assert "cross_script" in methods or "near_duplicate" in methods
    assert "t1" in contaminated
    assert counts["affected_eval_items"] >= 1
