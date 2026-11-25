"""D2: effective-dated, instrument-specific tick resolution. No default tick exists."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.domain.ticks import RESOLVER_VERSION, TickResolution, TickRow, TickTable, TickTableError

D = Decimal


def _row(sym: str, a: date, b: date | None, tick: str = "0.05") -> TickRow:
    return TickRow(sym, a, b, D(tick), "CIRC-TEST")


def test_resolves_by_symbol_and_effective_date_and_is_inclusive_at_both_ends() -> None:
    t = TickTable(
        [
            _row("AAA", date(2024, 1, 1), date(2024, 6, 9), "0.05"),
            _row("AAA", date(2024, 6, 10), None, "0.01"),
            _row("BBB", date(2024, 1, 1), None, "0.05"),
        ]
    )
    assert t.resolve("AAA", date(2024, 6, 9)) == TickResolution.resolved_as(D("0.05"), "CIRC-TEST")
    assert t.resolve("AAA", date(2024, 6, 10)).value == D("0.01")
    assert t.resolve("AAA", date(2030, 1, 1)).value == D("0.01")  # open ended
    assert t.resolve("BBB", date(2024, 6, 10)).value == D("0.05")  # instrument specific


def test_missing_coverage_is_unknown_never_0_05() -> None:
    t = TickTable([_row("AAA", date(2024, 1, 1), date(2024, 1, 31))])
    for sym, day in (("AAA", date(2023, 12, 31)), ("AAA", date(2024, 2, 1)), ("ZZZ", date(2024, 1, 15))):
        r = t.resolve(sym, day)
        assert (r.resolved, r.value, r.basis) == (False, None, None)
        assert r.reason == "NO_TICK_ROW_COVERS_DATE"
    assert not TickTable([]).resolve("AAA", date(2024, 1, 1)).resolved


def test_duplicate_overlapping_and_conflicting_rows_fail_the_load() -> None:
    with pytest.raises(TickTableError, match="duplicate"):
        TickTable([_row("A", date(2024, 1, 1), None), _row("A", date(2024, 1, 1), None, "0.01")])
    with pytest.raises(TickTableError, match="overlapping"):
        TickTable([_row("A", date(2024, 1, 1), date(2024, 3, 1)), _row("A", date(2024, 2, 1), None)])
    with pytest.raises(TickTableError, match="conflicting"):
        TickTable(
            [_row("A", date(2024, 1, 1), date(2024, 3, 1), "0.05"), _row("A", date(2024, 2, 1), None, "0.01")]
        )
    with pytest.raises(TickTableError, match="overlapping"):  # an open-ended row followed by another
        TickTable([_row("A", date(2024, 1, 1), None), _row("A", date(2024, 2, 1), None)])


@pytest.mark.parametrize("bad", ["0", "-0.05", "NaN", "Infinity"])
def test_non_positive_or_non_finite_ticks_are_rejected(bad: str) -> None:
    with pytest.raises(TickTableError):
        TickTable([_row("A", date(2024, 1, 1), None, bad)])


def test_reversed_interval_is_rejected_and_input_order_does_not_matter() -> None:
    with pytest.raises(TickTableError):
        TickTable([_row("A", date(2024, 2, 1), date(2024, 1, 1))])
    rows = [_row("A", date(2024, 6, 10), None, "0.01"), _row("A", date(2024, 1, 1), date(2024, 6, 9))]
    assert (
        TickTable(rows).resolve("A", date(2024, 3, 1)).value
        == TickTable(rows[::-1]).resolve("A", date(2024, 3, 1)).value
        == D("0.05")
    )


def test_resolver_version_is_exposed_for_the_run_record() -> None:
    assert RESOLVER_VERSION == "tick-resolver-1.0.0"
