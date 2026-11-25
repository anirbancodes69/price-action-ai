"""The fail-closed guard for database-writing integration tests (D0). No database is needed or touched."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from .integration.db_guard import (
    DatabaseGuardError,
    approved_database_url,
    assert_approved_connection,
    check_database_url,
)

CI = "postgresql+psycopg://ci:ci-ephemeral@127.0.0.1:5432/priceaction_test"
TEST = "postgresql+psycopg://app_test:x@postgres:5432/priceaction_test"


@pytest.mark.parametrize(
    "url",
    [
        CI,
        TEST,
        "postgresql://app_test:x@h/priceaction_test_ci1",
        "postgresql+psycopg://t:x@h/priceaction_test_a_b2",
    ],
)
def test_approved_test_databases_pass(url: str) -> None:
    assert check_database_url(url) == url


@pytest.mark.parametrize(
    "database",
    [
        "priceaction",  # the development database
        "postgres",
        "template1",
        "priceaction_testx",  # not the approved pattern
        "priceaction_test_",
        "Priceaction_Test",
        "priceaction-test",
        "priceaction_test2",
        "xpriceaction_test",
        "",
    ],
)
def test_other_databases_are_refused(database: str) -> None:
    with pytest.raises(DatabaseGuardError):
        check_database_url(f"postgresql+psycopg://app_test:x@postgres:5432/{database}")


def test_a_url_without_a_database_is_refused() -> None:
    with pytest.raises(DatabaseGuardError):
        check_database_url("postgresql+psycopg://app_test:x@postgres:5432")


@pytest.mark.parametrize("role", ["postgres", "app_engine", "app_backend"])
def test_live_application_roles_are_refused_even_for_a_test_database(role: str) -> None:
    with pytest.raises(DatabaseGuardError):
        check_database_url(f"postgresql+psycopg://{role}:x@postgres:5432/priceaction_test")


def test_a_url_without_a_role_is_refused() -> None:
    with pytest.raises(DatabaseGuardError):
        check_database_url("postgresql+psycopg://h:5432/priceaction_test")


@pytest.mark.parametrize("query", ["dbname=priceaction", "service=dev", "options=-c%20x"])
def test_url_parameters_that_can_change_the_database_are_refused(query: str) -> None:
    with pytest.raises(DatabaseGuardError):
        check_database_url(f"{TEST}?{query}")


@pytest.mark.parametrize("url", ["mysql://u:x@h/priceaction_test", "sqlite:///priceaction_test", "not a url"])
def test_other_drivers_and_garbage_are_refused(url: str) -> None:
    with pytest.raises(DatabaseGuardError):
        check_database_url(url)


def test_messages_never_contain_the_password() -> None:
    secret = "s3cr3t-pa55"
    for url in (
        f"postgresql+psycopg://app_engine:{secret}@h/priceaction_test",
        f"postgresql+psycopg://app_test:{secret}@h/priceaction",
        f"postgresql+psycopg://app_test:{secret}@h/priceaction_test?dbname=priceaction",
    ):
        with pytest.raises(DatabaseGuardError) as exc:
            check_database_url(url)
        assert secret not in str(exc.value)


def test_no_url_means_no_database_and_no_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCHEMA_DIFF_DATABASE_URL", raising=False)
    monkeypatch.delenv("REQUIRE_SCHEMA_DIFF", raising=False)
    assert approved_database_url() is None


def test_no_url_with_require_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCHEMA_DIFF_DATABASE_URL", raising=False)
    monkeypatch.setenv("REQUIRE_SCHEMA_DIFF", "1")
    with pytest.raises(DatabaseGuardError):
        approved_database_url()


def test_an_unapproved_url_in_the_environment_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REQUIRE_SCHEMA_DIFF", raising=False)
    monkeypatch.setenv(
        "SCHEMA_DIFF_DATABASE_URL", "postgresql+psycopg://app_engine:x@postgres:5432/priceaction"
    )
    with pytest.raises(DatabaseGuardError):
        approved_database_url()


def test_an_approved_url_in_the_environment_is_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCHEMA_DIFF_DATABASE_URL", TEST)
    assert approved_database_url() == TEST


class _Result:
    def __init__(self, row: tuple[str, str]) -> None:
        self._row = row

    def one(self) -> tuple[str, str]:
        return self._row


class _Conn:
    """Duck-typed connection: answers `select current_database(), current_user` without a database."""

    def __init__(self, database: str, role: str) -> None:
        self._row = (database, role)
        self.rolled_back = False

    def execute(self, *_: Any) -> _Result:
        return _Result(self._row)

    def rollback(self) -> None:
        self.rolled_back = True


def test_live_connection_check_accepts_an_approved_database_and_role() -> None:
    conn = _Conn("priceaction_test", "app_test")
    assert_approved_connection(conn)  # type: ignore[arg-type]
    assert conn.rolled_back


@pytest.mark.parametrize(
    ("database", "role"),
    [
        ("priceaction", "app_test"),
        ("priceaction_test", "app_engine"),
        ("postgres", "app_test"),
        ("priceaction_test", "postgres"),
    ],
)
def test_live_connection_check_refuses_the_development_database_and_live_roles(
    database: str, role: str
) -> None:
    with pytest.raises(DatabaseGuardError):
        assert_approved_connection(_Conn(database, role))  # type: ignore[arg-type]


def test_every_database_writing_module_uses_the_guard_and_none_reads_the_variable_directly() -> None:
    folder = Path(__file__).parent / "integration"
    for name in ("test_ingestion_repository.py", "test_ingestion_wiring.py", "test_schema_diff.py"):
        source = (folder / name).read_text()
        assert "approved_database_url" in source, name
        assert 'os.environ.get("SCHEMA_DIFF_DATABASE_URL")' not in source, name
    for name in ("test_ingestion_repository.py", "test_ingestion_wiring.py"):
        assert "assert_approved_connection(conn)" in (folder / name).read_text(), name
