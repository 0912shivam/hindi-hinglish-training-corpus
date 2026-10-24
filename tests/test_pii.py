from flam_pipeline.pii import redact_pii


def test_email_redaction() -> None:
    out = redact_pii("contact me at abc.user@test.org")
    assert "<EMAIL>" in out.text


def test_pan_redaction() -> None:
    out = redact_pii("PAN is ABCDE1234F")
    assert "<PAN>" in out.text


def test_phone_redaction_with_context() -> None:
    out = redact_pii("mobile 98765 43210 par call karein")
    assert "<PHONE>" in out.text


def test_aadhaar_redaction_valid_checksum() -> None:
    # 2347 6420 1116 is valid Verhoeff.
    out = redact_pii("aadhaar: 2347 6420 1116")
    assert "<AADHAAR>" in out.text
    assert "2347 6420 1116" not in out.text


def test_phone_redaction_with_prefix_no_context() -> None:
    out = redact_pii("Dial +91-9876543210 for assistance")
    assert "<PHONE>" in out.text
    assert "9876543210" not in out.text


def test_phone_redaction_with_hindi_context() -> None:
    out = redact_pii("मेरा संपर्क नंबर 9876543210 है")
    assert "<PHONE>" in out.text
    assert "9876543210" not in out.text


def test_regular_numbers_not_redacted() -> None:
    out = redact_pii("India scored 287 in 50 overs in 2024 series with order ID 202410241234")
    assert "<PHONE>" not in out.text
    assert "<AADHAAR>" not in out.text
    assert "287" in out.text
    assert "202410241234" in out.text
