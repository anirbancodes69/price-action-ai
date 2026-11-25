"""Schema-diff: ``app.db.tables`` must match the schema the Laravel migrations produce (ENG-04 §2, ENG-10).

Needs a PostgreSQL database that the Laravel migrations have already been applied to. Set
``SCHEMA_DIFF_DATABASE_URL`` (a SQLAlchemy URL, e.g. ``postgresql+psycopg://user:pass@host/db``).
Without it the database test is skipped locally; CI sets ``REQUIRE_SCHEMA_DIFF=1`` so a missing URL fails
instead of skipping.
"""

from collections.abc import Mapping

import pytest
from sqlalchemy import Column, create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import TypeEngine

from app.db.tables import TABLES

from .db_guard import approved_database_url

ColumnFacts = tuple[str, bool]  # (compiled type, nullable)
TableFacts = tuple[Mapping[str, ColumnFacts], tuple[str, ...]]  # (columns, primary key columns)


def _compile(type_: TypeEngine[object]) -> str:
    return type_.compile(dialect=postgresql.dialect()).lower()


def declared_facts() -> dict[str, TableFacts]:
    facts: dict[str, TableFacts] = {}
    for name, table in TABLES.items():
        cols: dict[str, ColumnFacts] = {c.name: (_compile(c.type), bool(c.nullable)) for c in table.columns}
        facts[name] = (cols, tuple(sorted(c.name for c in table.primary_key.columns)))
    return facts


def compare(declared: Mapping[str, TableFacts], actual: Mapping[str, TableFacts]) -> list[str]:
    """Human-readable differences between the read model and the database; empty means they match."""
    problems: list[str] = []
    for table, (d_cols, d_pk) in sorted(declared.items()):
        if table not in actual:
            problems.append(f"{table}: table does not exist in the database")
            continue
        a_cols, a_pk = actual[table]
        problems.extend(
            f"{table}.{c}: column missing in tables.py" for c in sorted(set(a_cols) - set(d_cols))
        )
        problems.extend(
            f"{table}.{c}: column missing in the database" for c in sorted(set(d_cols) - set(a_cols))
        )
        for c in sorted(set(d_cols) & set(a_cols)):
            if d_cols[c][0] != a_cols[c][0]:
                problems.append(
                    f"{table}.{c}: type is {a_cols[c][0]} in the database but {d_cols[c][0]} in tables.py"
                )
            if d_cols[c][1] != a_cols[c][1]:
                problems.append(
                    f"{table}.{c}: nullable is {a_cols[c][1]} in the database but {d_cols[c][1]} in tables.py"
                )
        if d_pk != a_pk:
            problems.append(f"{table}: primary key is {a_pk} in the database but {d_pk} in tables.py")
    return problems


def test_compare_reports_every_kind_of_drift() -> None:
    declared: dict[str, TableFacts] = {"t": ({"id": ("uuid", False), "n": ("text", True)}, ("id",))}
    assert compare(declared, declared) == []
    actual: dict[str, TableFacts] = {
        "t": ({"id": ("uuid", False), "n": ("integer", False), "x": ("text", True)}, ("id", "n"))
    }
    problems = compare(declared, actual)
    assert "t.n: type is integer in the database but text in tables.py" in problems
    assert "t.n: nullable is False in the database but True in tables.py" in problems
    assert "t.x: column missing in tables.py" in problems
    assert any("primary key" in p for p in problems)
    assert compare(declared, {}) == ["t: table does not exist in the database"]


def test_read_model_covers_the_tables_the_engine_touches() -> None:
    # The app_engine grants of apply_role_grants() (backend/database/migrations,
    # last redefined in 2026_11_17_000001).
    expected = {
        "data_sources",
        "data_source_selections",
        "universes",
        "market_calendar",
        "ruleset_versions",
        "trading_preferences",
        "risk_profiles",
        "paper_accounts",
        "instruments",
        "instrument_provider_refs",
        "instrument_snapshots",
        "universe_memberships",
        "candles",
        "candle_revisions",
        "corporate_actions",
        "ingestion_runs",
        "data_quality_issues",
        "analysis_batches",
        "ai_explanations",
        "backtest_trades",
        "analysis_runs",
        "analysis_run_inputs",
        "swing_points",
        "structure_events",
        "price_zones",
        "liquidity_events",
        "detected_setups",
        "candle_snapshots",
        "trade_plans",
        "paper_trades",
        "paper_trade_events",
        "journal_entries",
        "backtest_runs",
        "audit_logs",
    }
    assert set(TABLES) == expected
    assert "provider_connections" not in TABLES  # tokens never reach the engine through the database (ARC-06)


def test_read_model_matches_the_migrated_schema() -> None:
    url = approved_database_url()  # fail closed: refuses any database that is not an approved test database
    if url is None:
        pytest.skip("SCHEMA_DIFF_DATABASE_URL not set (needs a database migrated by Laravel)")

    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        actual: dict[str, TableFacts] = {}
        for name in TABLES:
            if not inspector.has_table(name):
                continue
            cols: dict[str, ColumnFacts] = {}
            for col in inspector.get_columns(name):
                cols[col["name"]] = (_compile(col["type"]), bool(col["nullable"]))
            pk = tuple(sorted(inspector.get_pk_constraint(name)["constrained_columns"]))
            actual[name] = (cols, pk)
    finally:
        engine.dispose()

    assert compare(declared_facts(), actual) == []


def test_declared_columns_have_unique_names() -> None:
    for name, table in TABLES.items():
        names = [c.name for c in table.columns]
        assert len(names) == len(set(names)), name
    assert all(isinstance(c, Column) for t in TABLES.values() for c in t.columns)
