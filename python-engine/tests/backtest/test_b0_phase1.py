"""Phase 1 technical readiness for the original B0: frozen timing, no previous-day dependency, the strict runner,
the price-basis archive and the rejection accounting (synthetic data; no database, no real reference table)."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.backtest import b0_run, loader
from app.backtest.approval import RunApproval
from app.backtest.b0_accounting import classify_all, reconcile
from app.backtest.b0_eligibility import (
    FROZEN_TIMING_NOT_APPLICABLE,
    B0Reference,
    PriceBasis,
    instrument_session_eligibility,
)
from app.backtest.exclusions import Exclusion
from app.backtest.reference_tables import (
    REVIEWED,
    UNREVIEWED,
    EventTable,
    LoadedTable,
    ReferenceTableError,
    file_sha256,
    load_price_basis,
    session_table_from,
)
from app.backtest.replay import SessionSpec, SymbolData
from app.backtest.run import SessionInput
from app.backtest.slippage import SlippageModel
from app.backtest.strategy_run import strategy_analyse
from app.domain.session import DailyLevels
from app.domain.ticks import TickRow, TickTable
from app.domain.types import Bar
from app.ingestion.session import IST
from app.rulesets import load_ruleset

from ..trading._session import CLOSE, OPEN, mk
from .b0_support import INDEPENDENT_RD, ctx

D = Decimal
REPO = Path(__file__).resolve().parents[3]
EVIDENCE = REPO / "docs/research/evidence/od8"
P6 = load_ruleset("pa-intraday", "0.6.0")
REG = {"effective_from": "2024-01-01", "effective_to": "2026-07-31", "session_open": "09:15",
       "continuous_end": "15:30", "last_expected_bar_start": "15:25", "expected_bar_count": 75,
       "source": "T", "confidence": "HIGH"}  # fmt: skip
CAS = {**REG, "effective_from": "2026-08-03", "effective_to": None, "continuous_end": "15:15",
       "last_expected_bar_start": "15:10", "expected_bar_count": 72}  # fmt: skip
SESSION_TABLE = session_table_from(LoadedTable("session_table", "t", "x", REVIEWED, [REG, CAS]))


def _bars(day: date, n: int = 4) -> list[Bar]:
    s = datetime.combine(day, time(9, 15), IST)
    return [
        Bar(
            s + timedelta(minutes=5 * i),
            s + timedelta(minutes=5 * i + 5),
            D("100.00"),
            D("100.50"),
            D("99.50"),
            D("100.20"),
        )
        for i in range(n)
    ]


def _ref(days: list[date]) -> B0Reference:
    return B0Reference(
        TickTable([TickRow("AAA", date(2024, 1, 1), None, D("0.05"), "T")]),
        EventTable([]),
        SESSION_TABLE,
        {("AAA", d): PriceBasis.TRADED_SCALE_VERIFIED for d in days},
        dict(INDEPENDENT_RD),
        RunApproval("INDEPENDENTLY_REVIEWED", None, (), {"tick": "INDEPENDENTLY_REVIEWED"}),
        ctx(P6),
    )


# --- AMB-1: the frozen cutoff and exit are never moved --------------------------------------------------------------


def test_a_shortened_session_cannot_apply_the_frozen_timing_and_is_excluded_not_moved() -> None:
    cas, regular = date(2026, 8, 4), date(2026, 7, 31)
    ref = _ref([cas, regular])
    e = instrument_session_eligibility(ref, "AAA", cas, _bars(cas), datetime.combine(cas, time(9, 15), IST))
    assert (e.eligible, e.reason) == (False, FROZEN_TIMING_NOT_APPLICABLE)
    ok = instrument_session_eligibility(
        ref, "AAA", regular, _bars(regular), datetime.combine(regular, time(9, 15), IST)
    )
    assert ok.eligible


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    days = [date(2026, 7, 30), date(2026, 7, 31), date(2026, 8, 3), date(2026, 8, 4)]

    def load_bars(_c, _s, _i, tf, _f, _l):  # type: ignore[no-untyped-def]
        return [b for d in days for b in _bars(d)] if tf == "5m" else []

    def boom(*_a: object, **_k: object) -> None:
        raise AssertionError("legacy default read on the B0 path")

    monkeypatch.setattr(loader, "load_bars", load_bars)
    monkeypatch.setattr(loader, "tick_and_lot", boom)
    monkeypatch.setattr(loader, "session_spec", boom)
    return days


def test_the_loader_reports_shortened_sessions_separately_and_keeps_the_regular_close(
    store: list[date],
) -> None:
    ex: list[Exclusion] = []
    out = loader.load_backtest_inputs(
        None,
        uuid.uuid4(),
        {"AAA": uuid.uuid4()},
        store[0],
        store[-1],
        2,
        exclusions=ex,
        b0=_ref(store),  # type: ignore[arg-type]
    )
    assert [s.spec.session_date for s in out] == store[:2]  # the 15:15 sessions never reach the replay
    assert all(s.spec.session_close.astimezone(IST).time() == time(15, 30) for s in out)
    assert ex == [
        Exclusion(date(2026, 8, 3), None, FROZEN_TIMING_NOT_APPLICABLE),
        Exclusion(date(2026, 8, 4), None, FROZEN_TIMING_NOT_APPLICABLE),
    ]


# --- AMB-3: no previous-day 1D bar is needed by B0 --------------------------------------------------------------------


def test_b0_needs_no_previous_day_bar_but_other_strategies_keep_the_requirement(
    store: list[date], monkeypatch: pytest.MonkeyPatch
) -> None:
    ex: list[Exclusion] = []
    out = loader.load_backtest_inputs(
        None,
        uuid.uuid4(),
        {"AAA": uuid.uuid4()},
        store[0],
        store[1],
        2,
        exclusions=ex,
        b0=_ref(store),
        daily_levels={},  # type: ignore[arg-type]
    )
    assert len(out) == 2 and ex == [] and all(s.symbols[0].prev_day is None for s in out)
    # Without b0 (every other strategy) the same empty daily-level map still excludes (existing behaviour).
    ex2: list[Exclusion] = []
    monkeypatch.setattr(loader, "tick_and_lot", lambda *_: (D("0.05"), 1))
    monkeypatch.setattr(
        loader,
        "session_spec",
        lambda _c, day, prev: SessionSpec(
            day, datetime.combine(day, time(9, 15), IST), datetime.combine(day, time(15, 30), IST)
        ),
    )
    other = loader.load_backtest_inputs(
        None,
        uuid.uuid4(),
        {"AAA": uuid.uuid4()},
        store[0],
        store[1],
        2,
        exclusions=ex2,
        daily_levels={},  # type: ignore[arg-type]
    )
    assert {e.reason for e in ex2} == {"MISSING_PREV_DAY_LEVELS"} and all(not s.symbols for s in other)


def test_b0_refuses_the_legacy_skip_list_and_still_fails_closed_on_missing_bars(
    store: list[date], monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(ValueError, match="session table"):
        loader.load_backtest_inputs(
            None,
            uuid.uuid4(),
            {"AAA": uuid.uuid4()},
            store[0],
            store[1],
            2,
            skip_days={store[0]},
            b0=_ref(store),  # type: ignore[arg-type]
        )
    short = _ref(store)
    ex: list[Exclusion] = []
    monkeypatch.setattr(
        loader,
        "load_bars",
        lambda _c, _s, _i, tf, _f, _l: [b for d in store[:2] for b in _bars(d, n=2)] if tf == "5m" else [],
    )
    out = loader.load_backtest_inputs(
        None,
        uuid.uuid4(),
        {"AAA": uuid.uuid4()},
        store[0],
        store[1],
        2,
        exclusions=ex,
        b0=short,  # type: ignore[arg-type]
    )
    assert all(not s.symbols for s in out) and {e.reason for e in ex} == {"OR_NOT_CLOSED"}


# --- price-basis archive and loader ---------------------------------------------------------------------------------

MATRIX_SHA = "33f9a1d7afaf180ecb58764c3ae23c1d82a7352f9c9716565a10a0dadfea954b"


def test_the_archived_matrix_matches_its_manifest_and_is_refused_as_unreviewed() -> None:
    csv_path = EVIDENCE / "price_scale_matrix_dev_v2.csv"
    man_path = EVIDENCE / "price_scale_matrix_dev_v2.MANIFEST.json"
    man = json.loads(man_path.read_text())
    assert file_sha256(csv_path) == MATRIX_SHA == man["sha256"]
    assert (man["status"], man["review_status"], man["data_class"]) == (
        "DEVELOPMENT_ONLY",
        "UNREVIEWED",
        "DEVELOPMENT",
    )
    assert (
        "NOT independently reviewed" in man["statement"]
        and "NOT approved for backtesting" in man["statement"]
    )
    with pytest.raises(ReferenceTableError, match="independent human review"):
        load_price_basis(csv_path, man_path, MATRIX_SHA)
    rows, table = load_price_basis(csv_path, man_path, MATRIX_SHA, require_reviewed=False)  # test only
    assert table.review_status == UNREVIEWED and len(rows) == man["rows"] == 32500
    counts = {c: sum(1 for v in rows.values() if v == c) for c in set(rows.values())}
    assert counts == man["class_counts"]


def test_the_price_basis_loader_rejects_a_wrong_hash_a_foreign_manifest_and_unknown_classes(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "m.csv"
    csv_path.write_text("symbol,date,scale_class\nAAA,2025-01-01,TRADED_SCALE_VERIFIED\n")
    h = file_sha256(csv_path)
    man = tmp_path / "m.MANIFEST.json"
    man.write_text(json.dumps({"kind": "price_basis_matrix", "sha256": h, "review_status": REVIEWED}))
    assert load_price_basis(csv_path, man, h)[0] == {("AAA", date(2025, 1, 1)): "TRADED_SCALE_VERIFIED"}
    with pytest.raises(ReferenceTableError, match="pinned"):
        load_price_basis(csv_path, man, "0" * 64)
    man.write_text(json.dumps({"kind": "price_basis_matrix", "sha256": "1" * 64, "review_status": REVIEWED}))
    with pytest.raises(ReferenceTableError, match="does not describe"):
        load_price_basis(csv_path, man, h)
    bad = tmp_path / "b.csv"
    bad.write_text("symbol,date,scale_class\nAAA,2025-01-01,MAYBE\n")
    man.write_text(
        json.dumps({"kind": "price_basis_matrix", "sha256": file_sha256(bad), "review_status": REVIEWED})
    )
    with pytest.raises(ReferenceTableError, match="unknown scale_class"):
        load_price_basis(bad, man, file_sha256(bad))
    dup = tmp_path / "d.csv"
    dup.write_text(
        "symbol,date,scale_class\nAAA,2025-01-01,PROVIDER_ADJUSTED\nAAA,2025-01-01,PROVIDER_ADJUSTED\n"
    )
    man.write_text(
        json.dumps({"kind": "price_basis_matrix", "sha256": file_sha256(dup), "review_status": REVIEWED})
    )
    with pytest.raises(ReferenceTableError, match="duplicate"):
        load_price_basis(dup, man, file_sha256(dup))


# --- the strict runner ----------------------------------------------------------------------------------------------


def _write_tables(tmp: Path, status: str = REVIEWED) -> b0_run.B0Pins:
    def w(name: str, kind: str, rows: list[dict]) -> b0_run.TablePin:
        p = tmp / f"{name}.json"
        p.write_text(json.dumps({"kind": kind, "version": "t1", "review_status": status, "rows": rows}))
        return b0_run.TablePin(p, file_sha256(p))

    csv_path = tmp / "pb.csv"
    csv_path.write_text("symbol,date,scale_class\nAAA,2025-03-05,TRADED_SCALE_VERIFIED\n")
    man = tmp / "pb.MANIFEST.json"
    man.write_text(
        json.dumps({"kind": "price_basis_matrix", "sha256": file_sha256(csv_path), "review_status": status})
    )
    return b0_run.B0Pins(
        w(
            "tick",
            "tick_table",
            [{"symbol": "AAA", "effective_from": "2024-01-01", "tick": "0.05", "basis": "T"}],
        ),
        w("events", "event_table", []),
        w("sessions", "session_table", [REG]),
        b0_run.TablePin(csv_path, file_sha256(csv_path)),
        man,
    )


def test_the_runner_builds_reference_data_with_every_hash_and_the_resolver_version(tmp_path: Path) -> None:
    ref = b0_run.build_reference(_write_tables(tmp_path))
    assert {"tick_table_sha256", "tick_resolver_version", "event_table_sha256", "session_table_sha256",
            "price_basis_sha256"} <= set(ref.hashes)  # fmt: skip
    assert ref.hashes["tick_resolver_version"] == "tick-resolver-1.0.0"


def test_the_runner_refuses_unreviewed_tables_a_hash_mismatch_and_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(b0_run.B0RunRefused, match="independent human review"):
        b0_run.build_reference(_write_tables(tmp_path, UNREVIEWED))
    pins = _write_tables(tmp_path)
    wrong = b0_run.B0Pins(b0_run.TablePin(pins.tick.path, "0" * 64), pins.events, pins.sessions,
                          pins.price_basis_csv, pins.price_basis_manifest)  # fmt: skip
    with pytest.raises(b0_run.B0RunRefused, match="pinned"):
        b0_run.build_reference(wrong)
    gone = b0_run.B0Pins(b0_run.TablePin(tmp_path / "none.json", "0" * 64), pins.events, pins.sessions,
                         pins.price_basis_csv, pins.price_basis_manifest)  # fmt: skip
    with pytest.raises(b0_run.B0RunRefused):
        b0_run.build_reference(gone)


def test_the_runner_accepts_only_the_released_0_6_0_and_the_b0_detector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    b0_run.check_b0_ruleset(P6)
    for other in ("0.5.0", "0.1.0"):
        with pytest.raises(b0_run.B0RunRefused):
            b0_run.check_b0_ruleset(load_ruleset("pa-intraday", other))
    from dataclasses import replace

    tampered = replace(P6, values={**P6.values, "orb.target_k": 3.0})
    with pytest.raises(b0_run.B0RunRefused, match="content hash"):
        b0_run.check_b0_ruleset(tampered)
    from app.domain import strategies
    from app.domain.setups.opening_range import detect_opening_range

    monkeypatch.setitem(strategies.STRATEGY_DETECTORS, "orb_b0", (detect_opening_range,))
    with pytest.raises(b0_run.B0RunRefused, match="B0 detector alone"):
        b0_run.check_b0_ruleset(P6)


OR3 = [("1002", "1005", "1000", "1003"), ("1003", "1004", "1001", "1002"), ("1002", "1003", "1000.5", "1001")]
QUIET, BREAK = ("1003", "1004", "1001", "1003"), ("1003", "1007", "1002", "1006")
PREV = DailyLevels(D("1100"), D("990"), D("1000"))


def _spec() -> SessionSpec:
    return SessionSpec(OPEN.date(), OPEN, CLOSE)


def _small():  # type: ignore[no-untyped-def]
    from dataclasses import replace

    return replace(P6, values={**P6.values, "analysis.min_bars_5m": 5, "analysis.min_bars_15m": 5})


def _sym(name: str, rows: list[tuple[str, str, str, str]]) -> SymbolData:
    b = mk(rows)
    return SymbolData(name, b, b, None, D("0.05"))


def test_run_b0_is_pinned_and_records_the_reference_hashes() -> None:
    ref = _ref([OPEN.date()])
    flat_open = [*OR3, QUIET, BREAK, ("1005", "1020", "1004", "1019")]
    inputs = [SessionInput(_spec(), [_sym("A", flat_open)])]
    # `_small` changes values, so the released-hash check refuses it: the strict runner takes only 0.6.0 as released.
    with pytest.raises(b0_run.B0RunRefused):
        b0_run.run_b0(
            inputs, _small(), ref, "4a", D("100000"), "e", "d", "u", SlippageModel.legacy(D("0.05"))
        )
    r = b0_run.run_b0(
        inputs, P6, ref, "4a", D("100000"), "e", "d", "u", SlippageModel.uniform(D("0.05"), "u")
    )
    assert r.record.reference_data["tick_table_sha256"] == "a" * 64 and r.record.strategy_id == "orb_b0"
    assert r.record.ruleset_hash == b0_run.B0_RULESET_HASH


def test_run_b0_needs_the_table_hashes() -> None:
    ref = B0Reference(TickTable([]), EventTable([]), SESSION_TABLE, {}, {})
    with pytest.raises(b0_run.B0RunRefused, match="table hashes"):
        b0_run.run_b0([], P6, ref, "4a", D("100000"), "e", "d", "u", SlippageModel.uniform(D("0"), "u"))


# --- GAP-2: rejection accounting ------------------------------------------------------------------------------------


def _rows_for_each_outcome() -> dict[str, list[tuple[str, str, str, str]]]:
    narrow = [("1000", "1002", "1000", "1000.5")] * 3 + [QUIET] * 3
    wide = [("1000", "1030", "1000", "1000.5")] * 3 + [QUIET] * 3
    return {
        "NARROW": narrow,
        "WIDE": wide,
        "WHIPSAW": OR3 + [("1001", "1002", "998", "999")] + [QUIET] * 2,
        "NO_BREAK": OR3 + [QUIET] * 6,
        "EXPIRED": OR3 + [QUIET] * 13,
        "SIGNAL": [*OR3, QUIET, BREAK, ("1005", "1020", "1004", "1019")],
        "SKIPPED": [*OR3, QUIET, BREAK, ("1006", "1020", "1005", "1019")],
    }


@pytest.mark.usefixtures("small_b0_hash")
def test_every_evaluated_instrument_session_gets_exactly_one_measured_outcome_and_reconciles() -> None:
    rows = _rows_for_each_outcome()
    syms = [_sym(k, v) for k, v in rows.items()]
    sessions = [SessionInput(_spec(), syms)]
    p = _small()
    fn = strategy_analyse("orb_b0")
    outcomes = classify_all(sessions, p, fn)
    got = {o.symbol: o.outcome for o in outcomes}
    assert got == {
        "NARROW": "OR_TOO_NARROW", "WIDE": "OR_TOO_WIDE", "WHIPSAW": "WHIPSAW", "NO_BREAK": "NO_BREAKOUT",
        "EXPIRED": "WINDOW_EXPIRED", "SIGNAL": "SIGNAL_CANDIDATE", "SKIPPED": "SIGNAL_CANDIDATE",
    }  # fmt: skip
    # Replay the same sessions and reconcile the pieces.
    from app.backtest.costs import CostSchedule
    from app.backtest.strategy_run import run_strategy_backtest

    res = run_strategy_backtest(
        "orb_b0",
        "4a",
        sessions,
        p,
        D("100000"),
        CostSchedule(),
        "e",
        "d",
        "u",
        slippage=SlippageModel.uniform(D("0.05"), "u"),
        reference_data=INDEPENDENT_RD,
        b0_context=ctx(p),
    )
    elig = {(s.symbol, OPEN.date()): _elig_ok() for s in syms}
    acc = reconcile(outcomes, res, elig, [])
    assert acc.reconciles, acc.problems
    assert (acc.evaluated, acc.candidates, acc.filled) == (7, 2, 1)
    assert acc.skipped == {"SKIPPED_RR_DEGRADED": 1}  # F-1: a flat open does not fill
    assert sum(acc.outcomes.values()) == acc.evaluated


def _elig_ok():  # type: ignore[no-untyped-def]
    from app.backtest.b0_eligibility import Eligibility, TickStatus

    return Eligibility(
        True, None, (), TickStatus.TICK_VERIFIED_PASS, D("0.05"), PriceBasis.TRADED_SCALE_VERIFIED, ()
    )


@pytest.mark.usefixtures("small_b0_hash")
def test_accounting_detects_a_mismatch_instead_of_inferring_counts() -> None:
    syms = [_sym("SIGNAL", _rows_for_each_outcome()["SIGNAL"])]
    sessions = [SessionInput(_spec(), syms)]
    p = _small()
    outcomes = classify_all(sessions, p, strategy_analyse("orb_b0"))
    from app.backtest.costs import CostSchedule
    from app.backtest.strategy_run import run_strategy_backtest

    res = run_strategy_backtest("orb_b0", "4a", sessions, p, D("100000"), CostSchedule(), "e", "d", "u",
                                slippage=SlippageModel.uniform(D("0.05"), "u"), reference_data=INDEPENDENT_RD, b0_context=ctx(p))  # fmt: skip
    elig = {("SIGNAL", OPEN.date()): _elig_ok(), ("GHOST", OPEN.date()): _elig_ok()}
    acc = reconcile(outcomes, res, elig, [])
    assert not acc.reconciles and any("differ from the eligible set" in x for x in acc.problems)
    assert acc.excluded == {} and acc.excluded_sessions == {}


# --- the runner script (never executed against a database here) ----------------------------------------------------


def test_the_runner_script_requires_every_pin_and_refuses_before_reading_data(tmp_path: Path) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("run_orb_b0", REPO / "python-engine/scripts/run_orb_b0.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with pytest.raises(SystemExit):  # a missing pin is an argparse error: there are no defaults for tables
        mod.parser().parse_args(["--from", "2024-01-01", "--to", "2024-01-31", "--members-on", "2024-01-31",
                                 "--experiment", "4a", "--data-class", "DEVELOPMENT"])  # fmt: skip
    pins = _write_tables(tmp_path, UNREVIEWED)
    argv = ["--from", "2024-01-01", "--to", "2024-01-31", "--members-on", "2024-01-31", "--experiment", "4a",
            "--data-class", "DEVELOPMENT", "--tick-table", str(pins.tick.path), "--tick-sha256", pins.tick.sha256,
            "--event-table", str(pins.events.path), "--event-sha256", pins.events.sha256,
            "--session-table", str(pins.sessions.path), "--session-sha256", pins.sessions.sha256,
            "--price-basis", str(pins.price_basis_csv.path), "--price-basis-manifest", str(pins.price_basis_manifest),
            "--price-basis-sha256", pins.price_basis_csv.sha256,
            "--variant-ledger", str(tmp_path / "l.json"), "--out-dir", str(tmp_path / "out")]  # fmt: skip
    assert mod.main(argv) == 3  # unreviewed tables: refused with no database access
    assert not (tmp_path / "out").exists() and not (tmp_path / "l.json").exists()
    existing = tmp_path / "out"
    existing.mkdir()
    (existing / "orb_b0_4a_development.json").write_text("{}")
    assert mod.main(argv) == 2 and (existing / "orb_b0_4a_development.json").read_text() == "{}"
