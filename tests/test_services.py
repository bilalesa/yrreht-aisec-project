from __future__ import annotations

import pytest

from app.services import extract_user_prompt, validate_scanner_token


def test_extract_user_prompt_uses_last_user_message() -> None:
    payload = {
        "messages": [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "answer"},
            {"role": "user", "content": "last"},
        ]
    }
    assert extract_user_prompt(payload) == "last"


def test_scanner_token_validation() -> None:
    validate_scanner_token(None, "")
    validate_scanner_token("Bearer demo", "demo")
    with pytest.raises(PermissionError):
        validate_scanner_token("Bearer wrong", "demo")


def test_ai_guard_endpoint_is_region_derived():
    from app.config import RuntimeConfig, Settings
    settings = Settings()
    runtime = RuntimeConfig(settings)
    snapshot = runtime.snapshot()
    assert snapshot["base_url"].startswith("https://api.")
    assert "xdr.trendmicro" in snapshot["base_url"]
