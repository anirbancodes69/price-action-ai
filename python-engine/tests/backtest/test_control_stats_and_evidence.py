"""E6 statistics and E8 evidence records (pure functions; thresholds are passed in, never defaulted)."""

from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path

import pytest

from app.backtest.approval import RunApproval
from app.backtest.control_stats import (
    MonthTotals,
    average_replicates,
    chronological_thirds,
    control_sampling_error,
    edge,
    interval_calibration,
    month_block_bootstrap,
    percentile,
    stability,
    supplementary_p,
    totals_by_month,
)
from app.backtest.evidence import (
    EvidenceError,
    PreRegistration,
    VariantLedger,
    build_evidence,
    validate_for_freeze,
)

INDEP = RunApproval("INDEPENDENTLY_REVIEWED", None, (), {"tick": "INDEPENDENTLY_REVIEWED"})
H = "a" * 64
C = "b" * 40


def test_totals_edge_and_replicate_averaging() -> None:
    orb = totals_by_month([(date(2025, 1, 2), 1.0), (date(2025, 1, 3), -1.0), (date(2025, 2, 3), 2.0)])
    assert orb == {"2025-01": MonthTotals(0.0, 2.0), "2025-02": MonthTotals(2.0, 1.0)}
    reps = [totals_by_month([(date(2025, 1, 2), 1.0), (date(2025, 2, 3), 0.0)]),
            totals_by_month([(date(2025, 1, 2), 3.0), (date(2025, 2, 3), 2.0)])]  # fmt: skip
    ctl = average_replicates(reps)
    assert ctl["2025-01"] == MonthTotals(2.0, 1.0)
    assert edge(orb, ctl) == pytest.approx(2.0 / 3 - 3.0 / 2)


def test_the_percentile_rule_is_nearest_rank_and_documented() -> None:
    v = [float(i) for i in range(1, 10001)]
    assert percentile(v, 0.005) == 50.0 and percentile(v, 0.995) == 9950.0
    with pytest.raises(ValueError):
        percentile([], 0.5)


def test_the_month_block_bootstrap_is_seeded_reproducible_and_brackets_the_point_estimate() -> None:
    rng = random.Random(0)  # noqa: S311
    months = [f"2024-{m:02d}" for m in range(1, 13)]
    orb = {m: MonthTotals(rng.uniform(-3, 5), 10.0) for m in months}
    ctl = {m: MonthTotals(rng.uniform(-3, 3), 10.0) for m in months}
    a = month_block_bootstrap(orb, ctl, resamples=2000, seed=1, level=0.99)
    b = month_block_bootstrap(orb, ctl, resamples=2000, seed=1, level=0.99)
    c = month_block_bootstrap(orb, ctl, resamples=2000, seed=2, level=0.99)
    assert a == b and a != c and a.low <= a.delta <= a.high and a.months == 12 and a.undefined_resamples == 0


def test_the_bootstrap_has_zero_width_when_months_are_identical_and_rejects_empty_inputs() -> None:
    m = {f"2024-{i:02d}": MonthTotals(10.0, 10.0) for i in range(1, 4)}
    z = {k: MonthTotals(5.0, 10.0) for k in m}
    r = month_block_bootstrap(m, z, resamples=500, seed=1, level=0.99)
    assert r.low == r.high == r.delta == pytest.approx(0.5)
    with pytest.raises(ValueError, match="common months"):
        month_block_bootstrap(m, {}, resamples=10, seed=1, level=0.99)


def test_sampling_error_p_value_thirds_and_stability() -> None:
    sd, se = control_sampling_error([0.1, 0.2, 0.3, 0.4])
    assert sd == pytest.approx(0.129099, rel=1e-4) and se == pytest.approx(sd / 2)
    with pytest.raises(ValueError):
        control_sampling_error([0.1])
    assert supplementary_p(1.0, [0.0, 2.0, 1.0]) == (1 + 2) / 4
    days = [date(2025, 1, 1 + i) for i in range(10)]
    parts = chronological_thirds(days)
    assert [len(p) for p in parts] == [4, 3, 3] and parts[0][0] == days[0]
    orb = [(d, 1.0) for d in days]
    ctl = [[(d, 0.0) for d in days]]
    st = stability(orb, ctl, days, min_trades=4)
    assert [s["orb_trades"] for s in st] == [4, 3, 3] and [s["interpretable"] for s in st] == [
        True,
        False,
        False,
    ]
    assert all(s["delta"] == 1.0 for s in st)


def test_the_calibration_harness_measures_coverage_and_false_positives_without_choosing_thresholds() -> None:
    def sim(rng: random.Random, delta: float) -> float:
        return delta + rng.gauss(0, 1)

    wide = interval_calibration(sim, lambda x: (x - 4, x + 4), true_delta=0.5, simulations=200, seed=1)  # type: ignore[arg-type,return-value]
    assert wide.coverage == 1.0 and wide.false_positive == 0.0
    narrow = interval_calibration(
        sim, lambda x: (x - 0.01, x + 0.01), true_delta=0.5, simulations=200, seed=1
    )  # type: ignore[arg-type,return-value]
    assert narrow.coverage < 0.1 and narrow.false_positive > 0.9
    again = interval_calibration(sim, lambda x: (x - 0.01, x + 0.01), true_delta=0.5, simulations=200, seed=1)  # type: ignore[arg-type,return-value]
    assert again == narrow


# --- E8 --------------------------------------------------------------------------------------------------------------


def _ev(**kw):  # type: ignore[no-untyped-def]
    base = {
        "run_kind": "ORB_B0_4A", "data_class": "DEVELOPMENT", "strategy_id": "demo_strategy", "ruleset": "pa-intraday 0.1.0",
        "ruleset_hash": H, "commit": C, "working_tree_clean": False, "reference_hashes": {"tick_table_sha256": H},
        "engine_version": "e", "inputs_hash": "i", "first_session": "2024-01-01", "last_session": "2026-11-19",
        "variant_number": 1,
        "approval": INDEP, "now": "2026-11-25T00:00:00+00:00",
    }  # fmt: skip
    base.update(kw)
    return build_evidence(**base)


def test_evidence_records_carry_labels_hashes_timestamp_and_the_review_label() -> None:
    e = _ev(seeds={"tie_break": 1}, reproducibility={"python": "3.13"})
    doc = json.loads(e.to_json())
    assert doc["data_class"] == "DEVELOPMENT" and doc["variant_number"] == 1 and doc["commit"] == C
    assert doc["evaluated_at_utc"] == "2026-11-25T00:00:00+00:00"
    assert doc["ai_review_label"] == "AI-ASSISTED — NON-INDEPENDENT"
    assert doc["reference_hashes"] == {"tick_table_sha256": H} and doc["seeds"] == {"tie_break": 1}


@pytest.mark.parametrize(
    "bad",
    [{"data_class": "REAL"}, {"ruleset_hash": "xyz"}, {"commit": "abc"}, {"variant_number": 0},
     {"reference_hashes": {"tick_table_sha256": "short"}}],
)  # fmt: skip
def test_evidence_rejects_labels_hashes_and_counters_that_are_not_real(bad: dict) -> None:
    with pytest.raises(EvidenceError):
        _ev(**bad)
    assert (
        _ev(commit="UNKNOWN").commit == "UNKNOWN"
    )  # an undetermined commit is recorded as such, never invented


def test_the_variant_ledger_counts_distinct_variants_and_survives_a_restart(tmp_path: Path) -> None:
    led = VariantLedger(tmp_path / "ledger.json")
    assert led.count() == 0 and led.register("orb_b0@0.6.0") == 1 and led.register("other") == 2
    assert VariantLedger(tmp_path / "ledger.json").register("orb_b0@0.6.0") == 1  # idempotent
    assert VariantLedger(tmp_path / "ledger.json").count() == 2
    (tmp_path / "bad.json").write_text(json.dumps({"variants": ["a", "a"]}))
    with pytest.raises(EvidenceError):
        VariantLedger(tmp_path / "bad.json").count()


def test_a_draft_pre_registration_cannot_be_frozen_and_nothing_is_filled_in() -> None:
    draft = PreRegistration("ORB_B0_STAGE_A", "orb_b0", "pa-intraday 0.6.0")
    problems = validate_for_freeze(draft, actual_commit=C, actual_ruleset_hash=H)
    assert (
        len(problems) == 5 and draft.status == "DRAFT" and draft.thresholds is None and draft.commit is None
    )
    guessed = PreRegistration("X", "orb_b0", "pa-intraday 0.6.0", H, "c" * 40, {"tick_table_sha256": H},
                              {"k": "1000"}, "owner")  # fmt: skip
    assert validate_for_freeze(guessed, actual_commit=C, actual_ruleset_hash=H) == [
        "commit differs from the actual commit"
    ]
    ok = PreRegistration(
        "X", "orb_b0", "pa-intraday 0.6.0", H, C, {"tick_table_sha256": H}, {"k": "1000"}, "owner"
    )
    assert validate_for_freeze(ok, actual_commit=C, actual_ruleset_hash=H) == []
    assert ok.fingerprint() == ok.fingerprint() != guessed.fingerprint()
