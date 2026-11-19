"""The ingestion job runs in the engine worker only, with the token as a read-only file (ARC-06 §5, ENG-05 §12)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

COMPOSE = Path(__file__).resolve().parents[2] / "docker-compose.yml"

pytestmark = pytest.mark.skipif(not COMPOSE.is_file(), reason="docker-compose.yml is outside this checkout")


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    return yaml.safe_load(COMPOSE.read_text())["services"]  # type: ignore[no-any-return]


def test_the_worker_gets_the_ingest_settings_and_off_is_the_default(services: dict[str, Any]) -> None:
    env = services["engine-worker"]["environment"]
    assert env["INGEST_ENABLED"] == "${INGEST_ENABLED:-false}"
    for key in ("INGEST_PROVIDER", "INGEST_DATA_SOURCE_ID", "INGEST_UNIVERSE_CODE", "KITE_API_KEY"):
        assert key in env, key
    assert env["KITE_TOKEN_FILE"] == "/run/kite/token"
    # still has the shared engine settings (database, redis, ruleset)
    assert {"DATABASE_URL", "REDIS_URL", "ACTIVE_RULESET"} <= set(env)


def test_the_token_is_a_read_only_file_mount_and_never_an_environment_value(services: dict[str, Any]) -> None:
    assert "./.kite_token:/run/kite/token:ro" in services["engine-worker"]["volumes"]
    for name, svc in services.items():
        env = svc.get("environment") or {}
        keys = set(env) if isinstance(env, dict) else {e.split("=")[0] for e in env}
        assert not {"KITE_ACCESS_TOKEN", "KITE_API_SECRET", "KITE_TOKEN"} & keys, name


def test_only_the_worker_receives_kite_settings(services: dict[str, Any]) -> None:
    for name, svc in services.items():
        env = svc.get("environment") or {}
        has_kite = any(k.startswith(("KITE_", "INGEST_")) for k in env)
        assert has_kite == (name == "engine-worker"), name
