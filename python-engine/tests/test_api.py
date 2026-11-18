from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.settings import Settings, get_settings


def _settings(**overrides: str) -> Settings:
    base = {"engine_service_token": "current-token", "engine_service_token_previous": "old-token"}
    return Settings(**{**base, **overrides})  # type: ignore[arg-type]


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: _settings()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_is_unauthenticated(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "engine"}


def test_internal_requires_token(client: TestClient) -> None:
    assert client.get("/internal/v1/ping").status_code == 401
    assert client.get("/internal/v1/ping", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_internal_accepts_current_and_previous_token(client: TestClient) -> None:
    for token in ("current-token", "old-token"):
        res = client.get("/internal/v1/ping", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["ruleset"] == "pa-intraday@0.1.0"


def test_internal_fails_closed_without_configured_token(client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: _settings(
        engine_service_token="", engine_service_token_previous=""
    )
    res = client.get("/internal/v1/ping", headers={"Authorization": "Bearer anything"})
    assert res.status_code == 503


def test_ready_reports_degraded_without_dependencies(client: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: _settings(
        database_url="", redis_url="redis://127.0.0.1:1/0", readiness_timeout_s="0.2"
    )
    res = client.get("/ready")
    assert res.status_code == 503
    assert res.json()["checks"] == {"database": False, "redis": False}
