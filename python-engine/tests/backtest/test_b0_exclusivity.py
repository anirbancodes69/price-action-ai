"""Strict-runner exclusivity for the original B0 (synthetic only): one authoritative execution path.

`orb_b0` and ruleset `pa-intraday 0.6.0` are reserved for `scripts/run_orb_b0.py`. The contract is enforced where a
run configuration and an evidence record are built (`BacktestConfig`, `EvidenceRecord`), and every legacy command
line refuses both names before touching settings or data.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
import uuid
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from app.api.deps import ruleset_for
from app.backtest import b0_run
from app.backtest.b0_contract import (
    B0ContractError,
    legacy_refusal,
    validate_b0_config,
    validate_b0_reference_data,
)
from app.backtest.costs import CostSchedule
from app.backtest.evidence import EvidenceError, build_evidence
from app.backtest.replay import SymbolData
from app.backtest.run import BacktestConfig, SessionInput, run_backtest
from app.backtest.slippage import SlippageModel
from app.backtest.strategy_run import run_strategy_backtest, strategy_analyse, strategy_config
from app.rulesets import load_ruleset
from app.settings import Settings

from ..trading._session import mk
from .b0_support import INDEPENDENT, LABEL, SOLO, SOLO_RD, ctx, reference_data
from .test_solo_approval import _history, _run, _spec, all_, indep, solo, write

D = Decimal
SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
P6 = load_ruleset("pa-intraday", "0.6.0")
OR3 = [("1002", "1005", "1000", "1003"), ("1003", "1004", "1001", "1002"), ("1002", "1003", "1000.5", "1001")]
ROWS = [
    *OR3,
    ("1003", "1004", "1001", "1003"),
    ("1003", "1007", "1002", "1006"),
    ("1005", "1020", "1004", "1019"),
]
RD = reference_data()


def _script(name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses with postponed annotations look the module up here
    spec.loader.exec_module(mod)
    return mod


def _sessions() -> list[SessionInput]:
    five, fifteen = _history()
    return [SessionInput(_spec(), [SymbolData("A", [*five, *mk(ROWS)], fifteen, None, D("0.05"))])]


def _strategy_run(strategy: str, params, rd, context=None):  # type: ignore[no-untyped-def]
    return run_strategy_backtest(strategy, "4a", _sessions(), params, D("100000"), CostSchedule(), "e", "d", "u",
                                 slippage=SlippageModel.uniform(D("0.05"), "u"), reference_data=rd, purpose="EXPLORATION:all",
                                 b0_context=context or ctx(params, rd))  # fmt: skip


# 1 -- the strict runner accepts a valid synthetic configuration ------------------------------------------------------


def test_the_strict_runner_accepts_a_valid_synthetic_original_b0(tmp_path: Path) -> None:
    ref = b0_run.build_reference(write(tmp_path, all_(indep())))
    r = _run(ref)
    assert r.record.strategy_id == "orb_b0" and r.record.ruleset == "pa-intraday 0.6.0"
    assert r.record.ruleset_hash == b0_run.B0_RULESET_HASH and len(r.trades) == 1


# 2, 3, 4 -- wrong strategy, ruleset or hash --------------------------------------------------------------------------


def test_ruleset_0_6_0_is_reserved_for_orb_b0_whatever_the_strategy() -> None:
    for strategy in ("opening_range_breakout", "liquidity_sweep_reversal", "failed_breakout"):
        with pytest.raises(B0ContractError, match="strict original-B0 runner"):
            _strategy_run(strategy, P6, RD)
        with pytest.raises(B0ContractError):
            strategy_config(strategy, "4a", P6, D("1"), CostSchedule(), "e", "d", "u", reference_data=RD)
    with pytest.raises(B0ContractError):  # a combined run (no strategy) on 0.6.0
        BacktestConfig(P6, D("1"), CostSchedule(), "e", "d", "u", reference_data=RD)


def test_orb_b0_cannot_run_on_another_ruleset_or_with_another_detector_under_it() -> None:
    for version in ("0.1.0", "0.5.0"):
        old = load_ruleset("pa-intraday", version)
        with pytest.raises(B0ContractError, match="strict original-B0 runner"):
            strategy_config("orb_b0", "4a", old, D("1"), CostSchedule(), "e", "d", "u", reference_data=RD)
    cfg = strategy_config("liquidity_sweep_reversal", "4a", load_ruleset("pa-intraday", "0.3.0"), D("1"),
                          CostSchedule(), "e", "d", "u")  # fmt: skip
    with pytest.raises(B0ContractError, match="another strategy"):
        run_backtest([], cfg, strategy_analyse("orb_b0"))
    with pytest.raises(b0_run.B0RunRefused):
        b0_run.check_b0_ruleset(load_ruleset("pa-intraday", "0.5.0"))


def test_a_mismatched_ruleset_hash_is_refused_by_the_config_and_the_runner() -> None:
    tampered = replace(P6, values={**P6.values, "orb.target_k": 3.0})
    with pytest.raises(B0ContractError, match="content hash"):
        strategy_config("orb_b0", "4a", tampered, D("1"), CostSchedule(), "e", "d", "u", reference_data=RD)
    with pytest.raises(b0_run.B0RunRefused, match="content hash"):
        b0_run.check_b0_ruleset(tampered)
    # without the strict evidence the released ruleset itself is refused too
    with pytest.raises(B0ContractError):
        strategy_config("orb_b0", "4a", P6, D("1"), CostSchedule(), "e", "d", "u")


# 5 -- the legacy runner and every other command line ---------------------------------------------------------------


def test_the_legacy_runner_rejects_orb_b0_and_the_reserved_ruleset_before_any_data(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _script("run_backtest")

    def no_settings() -> None:
        raise AssertionError("settings were read before the refusal")

    monkeypatch.setattr(mod, "get_settings", no_settings)
    base = ["--from", "2024-01-01", "--to", "2024-01-31"]
    for extra in (
        ["--strategy", "orb_b0", "--experiment", "4a"],
        ["--strategy", "orb_b0", "--experiment", "4a", "--ruleset", "pa-intraday@0.6.0"],
        ["--ruleset", "pa-intraday@0.6.0"],
        ["--strategy", "opening_range_breakout", "--experiment", "4b", "--ruleset", "pa-intraday@0.6.0"],
    ):
        assert mod.main([*base, *extra]) == 2
        assert "scripts/run_orb_b0.py" in capsys.readouterr().err


def test_non_b0_legacy_requests_pass_the_guard_and_behave_as_before(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for strategy, ruleset in (
        (None, None),
        ("failed_breakout", "pa-intraday@0.4.0"),
        (None, "pa-intraday@0.1.0"),
    ):
        assert legacy_refusal(strategy, ruleset) is None
    mod = _script("run_backtest")
    monkeypatch.setattr(mod, "get_settings", lambda: types.SimpleNamespace(ingest_data_source_id=""))
    argv = ["--from", "2024-01-01", "--to", "2024-01-31", "--strategy", "failed_breakout", "--experiment", "4a",
            "--ruleset", "pa-intraday@0.4.0"]  # fmt: skip
    assert (
        mod.main(argv) == 2 and "INGEST_DATA_SOURCE_ID" in capsys.readouterr().err
    )  # reached the next stage


def test_run_chunks_refuses_before_creating_anything(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    mod = _script("run_chunks")
    out = tmp_path / "chunks"
    for strategy, ruleset in (("orb_b0", "pa-intraday@0.4.0"), ("failed_breakout", "pa-intraday@0.6.0")):
        argv = ["--strategy", strategy, "--experiment", "4a", "--ruleset", ruleset, "--members-on", "2026-11-19",
                "--out-dir", str(out), "--chunk", "2024-01-01:2024-01-31"]  # fmt: skip
        assert mod.main(argv) == 2 and "scripts/run_orb_b0.py" in capsys.readouterr().err
    assert not out.exists()


# 6 -- alternative CLI, API and library paths -------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["scan", "run_screen", "run_diagnostics", "check_strategy_isolation"])
def test_other_scripts_refuse_the_reserved_ruleset(
    name: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    mod = _script(name)
    monkeypatch.setattr(mod, "get_settings",
                        lambda: types.SimpleNamespace(ingest_data_source_id=str(uuid.uuid4())))  # fmt: skip
    argv = ["--ruleset", "pa-intraday@0.6.0"]
    if name in ("run_screen", "run_diagnostics"):
        argv += ["--s01", str(tmp_path / "a"), "--s02", str(tmp_path / "b"), "--out", str(tmp_path / "o")]
    if name == "check_strategy_isolation":
        argv += ["--strategy", "failed_breakout"]
    assert mod.main(argv) == 2 and "scripts/run_orb_b0.py" in capsys.readouterr().err


def test_orb_b0_cannot_be_chosen_in_the_isolation_script_and_the_api_cannot_select_the_ruleset() -> None:
    mod = _script("check_strategy_isolation")
    with pytest.raises(SystemExit):
        mod.main(["--strategy", "orb_b0"])
    with pytest.raises(Exception, match="RULESET_NOT_LIVE"):
        ruleset_for(Settings(), "0.6.0")
    with pytest.raises(Exception, match="RULESET_NOT_LIVE"):
        ruleset_for(Settings(active_ruleset="pa-intraday@0.6.0"))


def test_chunk_merge_and_the_control_simulator_cannot_bypass_the_contract() -> None:
    from app.backtest.b0_eligibility import B0Reference
    from app.backtest.controls import ControlSet, simulate_control_set
    from app.backtest.reference_tables import EventTable, SessionFactsTable
    from app.domain.ticks import TickTable

    # merge_chunks rebuilds its configuration with strategy_config: no evidence, no B0 chunk
    with pytest.raises(B0ContractError):
        strategy_config("orb_b0", "4a", P6, D("1"), CostSchedule(), "e", "d", "u", reference_data={})
    empty = B0Reference(TickTable([]), EventTable([]), SessionFactsTable([], []), {}, {})
    with pytest.raises(B0ContractError):
        simulate_control_set(
            ControlSet(1, (), 0, 0, 0, 0), [], P6, "4a", D("1"), "e", "d", "u", object(), empty
        )


# 7, 8, 9, 10 -- evidence ----------------------------------------------------------------------------------------------


def _evidence(rd, strategy="orb_b0", ruleset="pa-intraday 0.6.0", rhash=None, approval=None):  # type: ignore[no-untyped-def]
    ra = approval or validate_b0_reference_data(rd)
    return build_evidence(
        run_kind="ORB_B0_4A", data_class="DEVELOPMENT", strategy_id=strategy, ruleset=ruleset,
        ruleset_hash=rhash or b0_run.B0_RULESET_HASH, commit="UNKNOWN", working_tree_clean=None,
        reference_hashes=rd, engine_version="e", inputs_hash="i", first_session=None, last_session=None,
        variant_number=1, approval=ra, run_digest="9" * 64,
    )  # fmt: skip


def test_b0_evidence_cannot_be_built_without_validated_approval_metadata() -> None:
    ok = _evidence(RD)
    assert (ok.strategy_id, ok.ruleset, ok.ruleset_hash) == (
        "orb_b0",
        "pa-intraday 0.6.0",
        b0_run.B0_RULESET_HASH,
    )
    ra = validate_b0_reference_data(RD)
    for bad_rd in (
        {},
        {k: v for k, v in RD.items() if k != "tick_table_sha256"},
        {**RD, "approval_basis": ""},
    ):
        with pytest.raises(EvidenceError):
            _evidence(bad_rd, approval=ra)
    with pytest.raises(TypeError):  # the approval argument is mandatory
        build_evidence(run_kind="X", data_class="DEVELOPMENT", strategy_id="orb_b0", ruleset="pa-intraday 0.6.0",
                       ruleset_hash=b0_run.B0_RULESET_HASH, commit="UNKNOWN", working_tree_clean=None,
                       reference_hashes=RD, engine_version="e", inputs_hash="i", first_session=None,
                       last_session=None, variant_number=1)  # type: ignore[call-arg]  # fmt: skip
    with pytest.raises(EvidenceError):  # wrong strategy / ruleset text / hash
        _evidence(RD, strategy="failed_breakout")
    with pytest.raises(EvidenceError):
        _evidence(RD, ruleset="pa-intraday 0.5.0")
    with pytest.raises(EvidenceError, match="released hash"):
        _evidence(RD, rhash="e" * 64)
    other = validate_b0_reference_data(SOLO_RD)
    with pytest.raises(EvidenceError):  # approval record that differs from the tables' statuses
        _evidence(RD, approval=other)


def test_solo_b0_evidence_has_the_exact_label_and_independent_evidence_does_not() -> None:
    solo_ev = _evidence(SOLO_RD)
    assert solo_ev.result_label == LABEL and json.loads(solo_ev.to_json())["result_label"] == LABEL
    assert solo_ev.approval_decision_refs == ("DEC-045",) and solo_ev.table_review_status["tick"] == SOLO
    ind = _evidence(RD)
    assert ind.result_label is None and LABEL not in ind.to_json() and ind.approval_basis == INDEPENDENT


def test_mixed_statuses_give_the_conservative_run_label_and_keep_each_table() -> None:
    mixed = reference_data({"event": SOLO, "session": SOLO})
    ra = validate_b0_reference_data(mixed)
    assert ra.basis == SOLO and ra.result_label == LABEL
    assert dict(ra.table_status) == {
        "tick": INDEPENDENT,
        "event": SOLO,
        "session": SOLO,
        "price_basis": INDEPENDENT,
    }
    ev = _evidence(mixed)
    assert ev.result_label == LABEL and dict(ev.table_review_status) == dict(ra.table_status)


# 11 -- invalid or contradictory metadata --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "change",
    [
        {"tick_table_sha256": "short"}, {"event_table_sha256": ""}, {"session_table_sha256": "Z" * 64},
        {"price_basis_sha256": "a" * 63}, {"tick_resolver_version": ""}, {"tick_review_status": ""},
        {"event_review_status": "UNREVIEWED"}, {"approval_basis": "UNKNOWN"}, {"approval_basis": INDEPENDENT,
         "tick_review_status": SOLO}, {"approval_basis": SOLO}, {"result_label": "EXPLORATORY"},
        {"approval_decision_refs": "DEC-044"}, {"approval_decision_refs": ""},
    ],
)  # fmt: skip
def test_invalid_or_contradictory_approval_metadata_is_rejected(change: dict[str, str]) -> None:
    rd = (
        {**SOLO_RD, **change}
        if "approval_basis" not in change or change["approval_basis"] != SOLO
        else {**RD, **change}
    )
    with pytest.raises(B0ContractError):
        validate_b0_reference_data(rd)
    with pytest.raises(B0ContractError):
        strategy_config("orb_b0", "4a", P6, D("1"), CostSchedule(), "e", "d", "u", reference_data=rd)


# 12, 13 -- nothing else changes -----------------------------------------------------------------------------------------


def test_non_b0_backtests_are_unaffected_by_the_contract() -> None:
    old = load_ruleset("pa-intraday", "0.3.0")
    validate_b0_config(old, "liquidity_sweep_reversal", {})  # a no-op
    validate_b0_config(old, None, {})
    cfg = strategy_config("liquidity_sweep_reversal", "4a", old, D("1"), CostSchedule(), "e", "d", "u")
    assert cfg.reference_data == {} and cfg.strategy_id == "liquidity_sweep_reversal"
    assert BacktestConfig(old, D("1"), CostSchedule(), "e", "d", "u").reference_data == {}
    assert run_backtest([], cfg, strategy_analyse("liquidity_sweep_reversal")).record.reference_data == {}


def test_the_safeguards_change_no_calculation_or_trade(tmp_path: Path) -> None:
    ref = b0_run.build_reference(write(tmp_path, all_(solo())), allow_solo_research=True)
    via_runner = _run(ref)
    direct = _strategy_run("orb_b0", P6, dict(ref.hashes), ref.context)
    assert via_runner.trades == direct.trades and len(direct.trades) == 1
    assert via_runner.record == direct.record  # same inputs, same record, same hashes
    t = direct.trades[0]
    assert (t.reason, t.anchor) == ("TARGET", "OR_HIGH")
