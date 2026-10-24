from flam_pipeline.config import LanguageConfig
from flam_pipeline.language import classify_language


def test_pure_hindi_is_hi() -> None:
    lang, _ = classify_language("यह एक सरल हिंदी वाक्य है", LanguageConfig())
    assert lang == "hi"


def test_hindi_with_english_words_is_hi() -> None:
    lang, _ = classify_language("यह meeting बहुत अच्छी थी", LanguageConfig())
    assert lang == "hi"


def test_pure_english_is_en() -> None:
    lang, _ = classify_language("This is a clean English sentence for testing", LanguageConfig())
    assert lang == "en"


def test_hinglish_is_hilatn() -> None:
    lang, _ = classify_language("aaj meeting hai aur hum kal milenge", LanguageConfig())
    assert lang == "hi-Latn"


def test_latin_gibberish_not_hilatn() -> None:
    lang, _ = classify_language("qwrty zmxn plk", LanguageConfig())
    assert lang in {"other", "en"}


def test_short_hindi_phrase_kept_hi() -> None:
    lang, _ = classify_language("शुभ दिन", LanguageConfig())
    assert lang == "hi"
