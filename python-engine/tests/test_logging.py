import json
import logging

from app.logging import REDACTED, JsonFormatter, redact


def test_redact_nested_sensitive_keys() -> None:
    payload = {
        "access_token": "abc",
        "nested": {"api_key": "k", "Authorization": "Bearer x", "symbol": "RELIANCE"},
        "items": [{"request_token": "t", "qty": 167}],
    }
    out = redact(payload)
    assert out["access_token"] == REDACTED
    assert out["nested"] == {"api_key": REDACTED, "Authorization": REDACTED, "symbol": "RELIANCE"}
    assert out["items"] == [{"request_token": REDACTED, "qty": 167}]


def test_formatter_emits_json_and_redacts_extras() -> None:
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "token_fetched", None, None)
    record.access_token = "super-secret"
    record.request_id = "req-1"
    line = JsonFormatter("engine").format(record)
    data = json.loads(line)
    assert data["service"] == "engine"
    assert data["event"] == "token_fetched"
    assert data["request_id"] == "req-1"
    assert data["access_token"] == REDACTED
    assert "super-secret" not in line
