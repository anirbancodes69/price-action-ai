"""DEC-045 / DR-12: the owner-approved solo-research status, its enforcement and the result label (synthetic only)."""

from __future__ import annotations

import itertools
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from app.backtest import b0_run
from app.backtest.approval import (
    INDEPENDENT,
    SOLO,
    SOLO_RESULT_LABEL,
    ApprovalError,
    RunApproval,
    TableApproval,
    parse_approval,
    summarise_approvals,
    validate_run_approval,
)
from app.backtest.b0_eligibility import instrument_session_eligibility
from app.backtest.evidence import EvidenceError, EvidenceRecord, build_evidence
from app.backtest.reference_tables import file_sha256, load_price_basis, load_table
from app.backtest.replay import SessionSpec, SymbolData
from app.backtest.run import SessionInput
from app.backtest.slippage import SlippageModel
from app.domain.types import Bar
from app.ingestion.session import IST
from app.rulesets import load_ruleset

from ..trading._session import CLOSE, OPEN, mk

D = Decimal
P6 = load_ruleset("pa-intraday", "0.6.0")
LABEL = "EXPLORATORY — SOLO RESEARCH — NOT INDEPENDENTLY VALIDATED"
OWNER = {"approved_by": "owner", "approved_on": "2026-11-25", "record": "owner decision DEC-045 (synthetic)"}
REG = {"effective_from": "2024-01-01", "effective_to": "2026-07-31", "session_open": "09:15",
       "continuous_end": "15:30", "last_expected_bar_start": "15:25", "expected_bar_count": 75,
       "source": "T", "confidence": "HIGH"}  # fmt: skip
TICK = {"symbol": "AAA", "effective_from": "2024-01-01", "tick": "0.05", "basis": "CIRC-T"}


def solo(ref: str = "DEC-045", **over: Any) -> dict[str, Any]:
    return {"review_status": SOLO, "decision_ref": ref, "owner_approval": dict(OWNER), **over}


def indep() -> dict[str, Any]:
    return {"review_status": INDEPENDENT}


def write(
    tmp: Path, meta: dict[str, dict[str, Any]], rows: dict[str, list[dict]] | None = None
) -> b0_run.B0Pins:
    """Synthetic tables; `meta` gives each table's approval metadata (keys tick, event, session, price_basis)."""
    rows = rows or {}

    def w(name: str, kind: str, default: list[dict]) -> b0_run.TablePin:
        p = tmp / f"{name}.json"
        p.write_text(
            json.dumps({"kind": kind, "version": "t1", **meta[name], "rows": rows.get(name, default)})
        )
        return b0_run.TablePin(p, file_sha256(p))

    csv_path = tmp / "pb.csv"
    csv_path.write_text("symbol,date,scale_class\nAAA,2025-03-05,TRADED_SCALE_VERIFIED\n")
    man = tmp / "pb.MANIFEST.json"
    man.write_text(json.dumps({"kind": "price_basis_matrix", "sha256": file_sha256(csv_path),
                               "artifact": "synthetic", **meta["price_basis"]}))  # fmt: skip
    return b0_run.B0Pins(w("tick", "tick_table", [TICK]), w("event", "event_table", []),
                         w("session", "session_table", [REG]),
                         b0_run.TablePin(csv_path, file_sha256(csv_path)), man)  # fmt: skip


def all_(m: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {k: dict(m) for k in ("tick", "event", "session", "price_basis")}


# 1 -------------------------------------------------------------------------------------------------------------------


def test_independent_review_behaves_as_before(tmp_path: Path) -> None:
    ref = b0_run.build_reference(write(tmp_path, all_(indep())))
    assert (
        ref.approval is not None and ref.approval.basis == INDEPENDENT and ref.approval.result_label is None
    )
    assert ref.hashes["approval_basis"] == INDEPENDENT and ref.hashes["result_label"] == ""
    assert set(ref.approval.table_status.values()) == {INDEPENDENT}
    # the solo opt-in does not change an independently reviewed run
    again = b0_run.build_reference(write(tmp_path, all_(indep())), allow_solo_research=True)
    assert (
        again.approval is not None
        and again.approval.basis == INDEPENDENT
        and again.approval.result_label is None
    )


# 2, 3, 4 ----------------------------------------------------------------------------------------------------------


def test_valid_solo_approval_is_accepted_only_with_the_explicit_opt_in(tmp_path: Path) -> None:
    pins = write(tmp_path, {"tick": solo("DEC-045"), "event": solo("DR-12"), "session": solo("DEC-045"),
                            "price_basis": solo("DR-12")})  # fmt: skip
    with pytest.raises(b0_run.B0RunRefused, match="not enabled for this load"):
        b0_run.build_reference(pins)  # no automatic approval just because DEC-045 exists
    ref = b0_run.build_reference(pins, allow_solo_research=True)
    a = ref.approval
    assert (
        a is not None
        and a.basis == SOLO
        and a.result_label == LABEL
        and a.decision_refs == ("DEC-045", "DR-12")
    )
    assert set(a.table_status.values()) == {SOLO}
    assert ref.hashes["approval_basis"] == SOLO and ref.hashes["result_label"] == LABEL
    assert ref.hashes["tick_review_status"] == SOLO and ref.hashes["tick_table_sha256"]  # hashes kept


@pytest.mark.parametrize("bad", [None, "", "DEC-044", "DR-11", "dec-045", "DR-12 ", "DEC-045,DR-12", 45])
def test_a_missing_or_unknown_decision_reference_is_rejected(bad: object) -> None:
    meta = solo()
    if bad is None:
        del meta["decision_ref"]
    else:
        meta["decision_ref"] = bad
    with pytest.raises(ApprovalError, match="decision_ref"):
        parse_approval(meta, name="t", allow_solo=True)


@pytest.mark.parametrize("drop", ["approved_by", "approved_on", "record"])
def test_owner_approval_evidence_is_required_complete_and_the_owners(drop: str) -> None:
    meta = solo()
    del meta["owner_approval"][drop]
    with pytest.raises(ApprovalError, match=f"owner_approval.{drop}"):
        parse_approval(meta, name="t", allow_solo=True)
    no_ev = solo()
    del no_ev["owner_approval"]
    with pytest.raises(ApprovalError, match="owner_approval evidence"):
        parse_approval(no_ev, name="t", allow_solo=True)
    for who in ("claude", "AI", "reviewer-1", ""):
        with pytest.raises(ApprovalError):
            parse_approval(solo(owner_approval={**OWNER, "approved_by": who}), name="t", allow_solo=True)
    with pytest.raises(ApprovalError, match="ISO date"):
        parse_approval(solo(owner_approval={**OWNER, "approved_on": "yesterday"}), name="t", allow_solo=True)


# 5, 7 -------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status",
    [None, "", "UNREVIEWED", "REVIEWED", "owner_approved_solo_research", "AI_REVIEWED", "AI-ASSISTED — NON-INDEPENDENT",
     "INDEPENDENT", "OWNER_APPROVED", 7, ["INDEPENDENTLY_REVIEWED"]],
)  # fmt: skip
def test_missing_unknown_or_ai_assisted_statuses_never_pass_under_either_policy(status: object) -> None:
    meta = {"review_status": status} if status is not None else {}
    for allow in (False, True):
        with pytest.raises(ApprovalError, match="independent human review"):
            parse_approval(meta, name="t", allow_solo=allow)


def test_an_ai_assisted_review_cannot_satisfy_the_independent_status() -> None:
    with pytest.raises(ApprovalError):
        parse_approval(
            {"review_status": "AI-ASSISTED — NON-INDEPENDENT", "reviewed_by": "AI"}, name="t", allow_solo=True
        )
    # AI-assisted approval metadata inside a solo table is refused as well
    with pytest.raises(ApprovalError, match="approved_by"):
        parse_approval(
            solo(owner_approval={**OWNER, "approved_by": "AI-assisted review"}), name="t", allow_solo=True
        )


# 6 ------------------------------------------------------------------------------------------------------------------


def test_solo_approval_is_never_converted_into_or_claimed_as_independent_review(tmp_path: Path) -> None:
    assert SOLO != INDEPENDENT
    t = load_table(
        write(tmp_path, all_(solo())).tick.path,
        "tick_table",
        write(tmp_path, all_(solo())).tick.sha256,
        allow_solo=True,
    )
    assert t.review_status == SOLO and t.approval == TableApproval(SOLO, "DEC-045", OWNER)
    for claim in (
        "independent_review",
        "independently_reviewed",
        "independent_reviewer",
        "reviewer",
        "reviewed_by",
        "review_date",
    ):
        with pytest.raises(ApprovalError, match="independent-review claims"):
            parse_approval(solo(**{claim: "x"}), name="t", allow_solo=True)
    with pytest.raises(ApprovalError, match="contradictory"):
        parse_approval({**indep(), "decision_ref": "DEC-045"}, name="t", allow_solo=True)
    with pytest.raises(ApprovalError, match="contradictory"):
        parse_approval({**indep(), "owner_approval": dict(OWNER)}, name="t", allow_solo=True)
    ra = summarise_approvals({"a": TableApproval(SOLO, "DR-12", OWNER)})
    assert ra.basis == SOLO != INDEPENDENT


# 8, 9, 10 ------------------------------------------------------------------------------------------------------------


def test_checks_still_apply_to_solo_tables_hash_provenance_schema_and_coverage(tmp_path: Path) -> None:
    solo_meta = all_(solo())
    pins = write(tmp_path / "ok", solo_meta) if (tmp_path / "ok").mkdir() is None else None
    assert pins is not None
    wrong = b0_run.B0Pins(b0_run.TablePin(pins.tick.path, "0" * 64), pins.events, pins.sessions,
                          pins.price_basis_csv, pins.price_basis_manifest)  # fmt: skip
    with pytest.raises(b0_run.B0RunRefused, match="pinned"):
        b0_run.build_reference(wrong, allow_solo_research=True)
    bad_basis = b0_run.B0Pins(pins.tick, pins.events, pins.sessions, b0_run.TablePin(pins.price_basis_csv.path, "1" * 64),
                              pins.price_basis_manifest)  # fmt: skip
    with pytest.raises(b0_run.B0RunRefused, match="pinned"):
        b0_run.build_reference(bad_basis, allow_solo_research=True)
    ev = {"event_type": "SPLIT", "symbol": "AAA", "date": "2025-01-02", "source": "", "source_hash": "h",
          "confidence": "H", "status": "CONFIRMED"}  # fmt: skip
    t1, t2 = {**TICK, "effective_to": "2025-01-01"}, {**TICK, "effective_from": "2024-06-01"}
    cases: dict[str, tuple[str, list[dict]]] = {
        "missing tick provenance": ("tick", [{k: v for k, v in TICK.items() if k != "basis"}]),
        "empty tick provenance": ("tick", [{**TICK, "basis": " "}]),
        "overlapping tick rows": ("tick", [t1, t2]),
        "conflicting tick rows": ("tick", [t1, {**t2, "tick": "0.01"}]),
        "event without source": ("event", [ev]),
        "session without source": ("session", [{k: v for k, v in REG.items() if k != "source"}]),
        "overlapping session regimes": (
            "session",
            [REG, {**REG, "effective_from": "2026-07-01", "effective_to": None}],
        ),
    }
    for label, (name, rows) in cases.items():
        d = tmp_path / label.replace(" ", "_")
        d.mkdir()
        with pytest.raises(b0_run.B0RunRefused):
            b0_run.build_reference(write(d, solo_meta, {name: rows}), allow_solo_research=True)
    # a foreign price-basis manifest still fails
    man = json.loads(pins.price_basis_manifest.read_text())
    man["kind"] = "other"
    pins.price_basis_manifest.write_text(json.dumps(man))
    with pytest.raises(b0_run.B0RunRefused, match="does not describe"):
        b0_run.build_reference(pins, allow_solo_research=True)
    with pytest.raises(Exception, match="does not describe"):
        load_price_basis(
            pins.price_basis_csv.path, pins.price_basis_manifest, pins.price_basis_csv.sha256, allow_solo=True
        )


def test_date_coverage_gaps_still_exclude_under_solo_approval(tmp_path: Path) -> None:
    ref = b0_run.build_reference(write(tmp_path, all_(solo())), allow_solo_research=True)
    for day, reason in (
        (date(2023, 6, 1), "SESSION_HOURS_UNKNOWN"),
        (date(2026, 8, 3), "SESSION_HOURS_UNKNOWN"),
    ):
        s = datetime.combine(day, time(9, 15), IST)
        e = instrument_session_eligibility(ref, "AAA", day, mk([("100", "101", "99", "100")] * 3), s)
        assert (e.eligible, e.reason) == (False, reason)
    day = date(2025, 3, 5)
    bars = mk([("100.00", "100.50", "99.50", "100.20")] * 3, start=datetime.combine(day, time(9, 15), IST))
    zz = instrument_session_eligibility(ref, "ZZZ", day, bars, datetime.combine(day, time(9, 15), IST))
    assert zz.reason == "TICK_UNKNOWN"  # no tick row: unknown, never 0.05


# 11, 12 -----------------------------------------------------------------------------------------------------------


def _spec() -> SessionSpec:
    return SessionSpec(OPEN.date(), OPEN, CLOSE)


OR3 = [("1002", "1005", "1000", "1003"), ("1003", "1004", "1001", "1002"), ("1002", "1003", "1000.5", "1001")]
ROWS = [
    *OR3,
    ("1003", "1004", "1001", "1003"),
    ("1003", "1007", "1002", "1006"),
    ("1005", "1020", "1004", "1019"),
]


def _history() -> tuple[list[Bar], list[Bar]]:
    """Enough prior bars for the released 0.6.0 snapshot minimums (150 x 5m, 75 x 15m) before the session."""
    start = OPEN - timedelta(days=3)
    five = mk([("1000", "1001", "999", "1000")] * 160, start=start)
    fifteen = [
        Bar(start + timedelta(minutes=15 * i), start + timedelta(minutes=15 * i + 15), D("1000"), D("1001"),
            D("999"), D("1000"))
        for i in range(80)
    ]  # fmt: skip
    return five, fifteen


def _run(ref):  # type: ignore[no-untyped-def]
    five, fifteen = _history()
    b = [*five, *mk(ROWS)]
    inputs = [SessionInput(_spec(), [SymbolData("A", b, fifteen, None, D("0.05"))])]
    return b0_run.run_b0(
        inputs, P6, ref, "4a", D("100000"), "e", "d", "u", SlippageModel.uniform(D("0.05"), "u")
    )


def test_a_solo_run_always_carries_the_exact_label_and_the_basis_in_its_record(tmp_path: Path) -> None:
    ref = b0_run.build_reference(write(tmp_path, all_(solo())), allow_solo_research=True)
    r = _run(ref)
    rd = r.record.reference_data
    assert (
        rd["result_label"] == LABEL
        and rd["approval_basis"] == SOLO
        and rd["approval_decision_refs"] == "DEC-045"
    )
    assert rd["tick_review_status"] == SOLO and len(rd["tick_table_sha256"]) == 64
    assert ref.approval is not None
    ev = build_evidence(
        run_kind="ORB_B0_4A", data_class="DEVELOPMENT", strategy_id="orb_b0", ruleset="pa-intraday 0.6.0",
        ruleset_hash=r.record.ruleset_hash, commit="UNKNOWN", working_tree_clean=None, reference_hashes=rd,
        engine_version="e", inputs_hash=r.record.inputs_hash, first_session="x", last_session="y",
        variant_number=1, approval=ref.approval, run_digest=r.record.run_digest,
    )  # fmt: skip
    doc = json.loads(ev.to_json())
    assert doc["result_label"] == LABEL == SOLO_RESULT_LABEL and doc["approval_basis"] == SOLO
    assert doc["approval_decision_refs"] == ["DEC-045"] and set(doc["table_review_status"].values()) == {SOLO}
    assert doc["reference_hashes"]["tick_table_sha256"] == rd["tick_table_sha256"]


def test_an_independently_reviewed_run_is_not_labelled_as_solo_research(tmp_path: Path) -> None:
    ref = b0_run.build_reference(write(tmp_path, all_(indep())))
    r = _run(ref)
    rd = r.record.reference_data
    assert rd["approval_basis"] == INDEPENDENT and rd["result_label"] == ""
    assert ref.approval is not None
    ev = build_evidence(
        run_kind="X", data_class="DEVELOPMENT", strategy_id="orb_b0", ruleset="pa-intraday 0.6.0",
        ruleset_hash=b0_run.B0_RULESET_HASH,
        commit="UNKNOWN", working_tree_clean=None, reference_hashes=rd, engine_version="e", inputs_hash="i",
        first_session=None, last_session=None, variant_number=1, approval=ref.approval, run_digest=r.record.run_digest,
    )  # fmt: skip
    assert ev.result_label is None and LABEL not in ev.to_json()


def _record(**over: Any) -> EvidenceRecord:
    base: dict[str, Any] = {
        "run_kind": "X", "data_class": "DEVELOPMENT", "strategy_id": "demo_strategy", "ruleset": "r",
        "ruleset_hash": "a" * 64, "commit": "UNKNOWN", "working_tree_clean": None, "reference_hashes": {},
        "engine_version": "e", "inputs_hash": "i", "first_session": None, "last_session": None,
        "variant_number": 1, "evaluated_at_utc": "t", "approval_basis": SOLO, "approval_decision_refs": ("DEC-045",),
        "table_review_status": {"tick": SOLO}, "result_label": LABEL, "run_digest": "",
    }  # fmt: skip
    base.update(over)
    return EvidenceRecord(**base)


def test_contradictory_or_stripped_metadata_cannot_form_a_record_or_a_run() -> None:
    assert _record().result_label == LABEL
    for bad in (
        {"result_label": None},  # label omitted on a solo run
        {"result_label": "EXPLORATORY"},  # label replaced
        {"result_label": LABEL.lower()},
        {"approval_decision_refs": ()},
        {"approval_decision_refs": ("DEC-044",)},
        {"table_review_status": {"tick": INDEPENDENT}},  # solo basis, no solo table
        {"approval_basis": INDEPENDENT},  # independent basis with the solo label and a solo table
        {"approval_basis": "UNKNOWN"},
        {"table_review_status": {}},
        {"reference_hashes": {"approval_basis": INDEPENDENT}},
        {"reference_hashes": {"result_label": "something else"}},
        {"reference_hashes": {"tick_review_status": INDEPENDENT}},
    ):
        with pytest.raises(EvidenceError):
            _record(**bad)
    with pytest.raises(EvidenceError, match="solo label"):
        _record(
            approval_basis=INDEPENDENT, table_review_status={"tick": INDEPENDENT}, approval_decision_refs=()
        )
    with pytest.raises(ApprovalError):
        validate_run_approval(RunApproval(INDEPENDENT, LABEL, (), {"tick": INDEPENDENT}))


def test_the_runner_refuses_a_run_whose_record_contradicts_the_tables_approval(tmp_path: Path) -> None:
    from dataclasses import replace

    ref = b0_run.build_reference(write(tmp_path, all_(solo())), allow_solo_research=True)
    bad_label = replace(ref, hashes={**ref.hashes, "result_label": ""})
    with pytest.raises(b0_run.B0RunRefused, match="differs from the tables"):
        _run(bad_label)
    bad_basis = replace(ref, hashes={**ref.hashes, "approval_basis": INDEPENDENT})
    with pytest.raises(b0_run.B0RunRefused, match="differs from the tables"):
        _run(bad_basis)
    with pytest.raises(b0_run.B0RunRefused, match="not established"):
        _run(replace(ref, approval=None))


# 13 -----------------------------------------------------------------------------------------------------------------


def test_d1_and_dr_11_are_unchanged_and_cannot_be_used_as_an_approval_status() -> None:
    for status in ("DR-11", "AI_ASSISTED_PLUS_OWNER_REVIEW", "NON-INDEPENDENT", "OWNER_SELF_REVIEW"):
        with pytest.raises(ApprovalError):
            parse_approval({"review_status": status}, name="t", allow_solo=True)
    row = next(
        ln for ln in (Path(__file__).resolve().parents[3] / "docs/development/orb-data-remediation.md").read_text().splitlines()
        if ln.startswith("| DR-11 |")
    )  # fmt: skip
    assert (
        "For **D1 only**" in row and "DR-12" not in row and "D2-D6" in row
    )  # DR-11's scope is not broadened


# 14 -----------------------------------------------------------------------------------------------------------------


def test_mixed_statuses_use_the_weakest_basis_deterministically_and_keep_each_status() -> None:
    ind, sol = TableApproval(INDEPENDENT, None, None), TableApproval(SOLO, "DR-12", OWNER)
    tables = {"tick": ind, "event": sol, "session": ind, "price_basis": ind}
    results = [summarise_approvals(dict(p)) for p in itertools.permutations(tables.items())]
    assert all(r == results[0] for r in results)
    ra = results[0]
    assert ra.basis == SOLO and ra.result_label == LABEL and ra.decision_refs == ("DR-12",)
    assert dict(ra.table_status) == {
        "tick": INDEPENDENT,
        "event": SOLO,
        "session": INDEPENDENT,
        "price_basis": INDEPENDENT,
    }
    all_ind = summarise_approvals(dict.fromkeys(tables, ind))
    assert all_ind.basis == INDEPENDENT and all_ind.result_label is None and all_ind.decision_refs == ()
    with pytest.raises(ApprovalError):
        summarise_approvals({})
    with pytest.raises(ApprovalError):
        summarise_approvals({"x": TableApproval("UNREVIEWED", None, None)})


def test_a_mixed_run_end_to_end_is_labelled_solo_and_keeps_per_table_status(tmp_path: Path) -> None:
    meta = {"tick": solo(), "event": indep(), "session": indep(), "price_basis": indep()}
    ref = b0_run.build_reference(write(tmp_path, meta), allow_solo_research=True)
    rd = _run(ref).record.reference_data
    assert rd["approval_basis"] == SOLO and rd["result_label"] == LABEL
    assert (rd["tick_review_status"], rd["event_review_status"]) == (SOLO, INDEPENDENT)


def test_the_approval_basis_never_changes_the_trades(tmp_path: Path) -> None:
    a = (
        b0_run.build_reference(write(tmp_path / "a", all_(indep())))
        if (tmp_path / "a").mkdir() is None
        else None
    )
    b = (
        b0_run.build_reference(write(tmp_path / "b", all_(solo())), allow_solo_research=True)
        if (tmp_path / "b").mkdir() is None
        else None
    )
    assert a is not None and b is not None
    ra, rb = _run(a), _run(b)
    assert ra.trades == rb.trades and len(ra.trades) == 1 and ra.record.inputs_hash == rb.record.inputs_hash
    assert timedelta(0) == timedelta(0)
