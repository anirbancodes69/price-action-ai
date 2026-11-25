"""D2/D5/D6: hash-pinned, review-gated reference tables (synthetic fixtures only; no real data)."""

from __future__ import annotations

import json
from datetime import date, time
from decimal import Decimal
from pathlib import Path

import pytest

from app.backtest.reference_tables import (
    REVIEWED,
    UNREVIEWED,
    EventTable,
    LoadedTable,
    ReferenceTableError,
    event_table_from,
    file_sha256,
    load_table,
    session_table_from,
    tick_table_from,
)


def _write(tmp: Path, kind: str, rows: list[dict], status: str = REVIEWED) -> tuple[Path, str]:
    p = tmp / f"{kind}.json"
    p.write_text(json.dumps({"kind": kind, "version": "t1", "review_status": status, "rows": rows}))
    return p, file_sha256(p)


TICK_ROWS = [{"symbol": "AAA", "effective_from": "2024-01-01", "tick": "0.05", "basis": "TEST"}]


def test_a_reviewed_table_loads_when_the_pinned_hash_matches(tmp_path: Path) -> None:
    p, h = _write(tmp_path, "tick_table", TICK_ROWS)
    t = load_table(p, "tick_table", h)
    assert (t.sha256, t.review_status, t.version) == (h, REVIEWED, "t1")
    assert tick_table_from(t).resolve("AAA", date(2024, 5, 1)).value == Decimal("0.05")


def test_hash_mismatch_wrong_kind_and_missing_rows_fail_the_load(tmp_path: Path) -> None:
    p, h = _write(tmp_path, "tick_table", TICK_ROWS)
    with pytest.raises(ReferenceTableError, match="does not match the pinned"):
        load_table(p, "tick_table", "0" * 64)
    with pytest.raises(ReferenceTableError, match="kind"):
        load_table(p, "event_table", h)
    p2 = tmp_path / "x.json"
    p2.write_text(json.dumps({"kind": "tick_table", "review_status": REVIEWED}))
    with pytest.raises(ReferenceTableError, match="rows missing"):
        load_table(p2, "tick_table", file_sha256(p2))


def test_an_unreviewed_table_is_refused_by_default_and_never_treated_as_reviewed(tmp_path: Path) -> None:
    """DR-7/DR-7a: an AI review is not an independent human review, so only the explicit status passes."""
    for status in (UNREVIEWED, "AI_REVIEWED", "REVIEWED", None):
        p, h = _write(tmp_path, "tick_table", TICK_ROWS, status)  # type: ignore[arg-type]
        with pytest.raises(ReferenceTableError, match="independent human review"):
            load_table(p, "tick_table", h)
    p, h = _write(tmp_path, "tick_table", TICK_ROWS, UNREVIEWED)
    assert load_table(p, "tick_table", h, require_reviewed=False).review_status == UNREVIEWED  # tests only


def test_event_rows_exclude_only_confirmed_symbol_changes_and_demergers_and_fail_closed_when_unresolved() -> (
    None
):
    def row(kind: str, status: str, day: str = "2025-01-10", sym: str = "AAA") -> dict:
        return {
            "event_type": kind,
            "symbol": sym,
            "date": day,
            "source": "s",
            "source_hash": "h",
            "confidence": "HIGH",
            "status": status,
        }

    t = event_table_from(
        LoadedTable(
            "event_table",
            "t1",
            "x",
            REVIEWED,
            [
                row("SYMBOL_CHANGE", "CONFIRMED"),
                row("DEMERGER", "CONFIRMED", sym="BBB"),
                row("SPLIT", "CONFIRMED", sym="CCC"),
                row("DEMERGER", "UNRESOLVED", sym="DDD"),
                row("DIVIDEND", "FLAGGED", sym="EEE"),
            ],
        )
    )
    d = date(2025, 1, 10)
    assert t.exclusion_reason("AAA", d) == "L6_EVENT"
    assert t.exclusion_reason("BBB", d) == "L6_EVENT"
    assert t.exclusion_reason("CCC", d) is None and t.has_event("CCC", d)  # other actions are flagged only
    assert t.exclusion_reason("DDD", d) == "L6_EVENT_UNRESOLVED"
    assert t.exclusion_reason("EEE", d) is None
    assert (
        t.exclusion_reason("AAA", date(2025, 1, 11)) is None
    )  # the instrument-session only, not the company
    assert t.exclusion_reason("ZZZ", d) is None


def test_duplicate_event_rows_fail_the_load() -> None:
    r = {
        "event_type": "SPLIT",
        "symbol": "A",
        "date": "2025-01-10",
        "source": "s",
        "source_hash": "h",
        "confidence": "HIGH",
        "status": "CONFIRMED",
    }
    with pytest.raises(ReferenceTableError, match="duplicate"):
        event_table_from(LoadedTable("event_table", "t1", "x", REVIEWED, [r, dict(r)]))
    assert EventTable([]).exclusion_reason("A", date(2025, 1, 10)) is None


SESSION_ROWS = [
    {"effective_from": "2024-01-01", "effective_to": "2026-07-31", "session_open": "09:15",
     "continuous_end": "15:30", "last_expected_bar_start": "15:25", "expected_bar_count": 75,
     "source": "TEST", "confidence": "HIGH"},
    {"effective_from": "2026-08-03", "session_open": "09:15", "continuous_end": "15:15",
     "last_expected_bar_start": "15:10", "expected_bar_count": 72, "source": "TEST", "confidence": "HIGH"},
    {"date": "2024-01-20", "session_open": "09:15", "continuous_end": "15:30",
     "last_expected_bar_start": "15:25", "expected_bar_count": 75, "source": "CONFLICT",
     "confidence": "LOW", "excluded_reason": "SPECIAL_SESSION_2024_01_20"},
]  # fmt: skip


def test_session_facts_are_dated_special_dates_win_and_unknown_dates_return_none() -> None:
    t = session_table_from(LoadedTable("session_table", "t1", "x", REVIEWED, SESSION_ROWS))
    reg, cas = t.facts(date(2025, 5, 5)), t.facts(date(2026, 8, 3))
    assert reg is not None and cas is not None
    assert (reg.continuous_end, reg.expected_bar_count) == (time(15, 30), 75)
    assert (cas.continuous_end, cas.last_expected_bar_start, cas.expected_bar_count) == (
        time(15, 15), time(15, 10), 72,
    )  # fmt: skip
    sp = t.facts(date(2024, 1, 20))
    assert sp is not None and sp.excluded_reason == "SPECIAL_SESSION_2024_01_20"
    assert t.facts(date(2023, 12, 29)) is None  # before coverage: unknown, never defaulted to 15:30
    assert t.facts(date(2026, 8, 1)) is None  # a gap between regimes is unknown too


def test_overlapping_session_regimes_and_duplicate_special_dates_fail() -> None:
    bad = [dict(SESSION_ROWS[0]), {**SESSION_ROWS[1], "effective_from": "2026-07-01"}]
    with pytest.raises(ReferenceTableError, match="overlapping"):
        session_table_from(LoadedTable("session_table", "t1", "x", REVIEWED, bad))
    with pytest.raises(ReferenceTableError, match="duplicate"):
        session_table_from(
            LoadedTable("session_table", "t1", "x", REVIEWED, [SESSION_ROWS[2], SESSION_ROWS[2]])
        )
