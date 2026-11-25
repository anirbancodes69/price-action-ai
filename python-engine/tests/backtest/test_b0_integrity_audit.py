"""Final B0 execution-path and evidence-integrity audit (synthetic only; AI-ASSISTED — NON-INDEPENDENT).

Static inventory of every module that can invoke B0, plus tests of what the contract does and does not guarantee:
fabricated, copied, reused and edited evidence; ruleset-hash sources and test-only overrides; chunk and merge.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import re
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType

import pytest

from app.backtest import b0_contract, b0_run, chunks
from app.backtest.b0_contract import (
    B0_RULESET_HASH,
    B0ContractError,
    B0ExecutionContext,
    issue_context,
)
from app.backtest.costs import CostSchedule
from app.backtest.evidence import EvidenceError, build_evidence, verify_evidence_for_result
from app.backtest.replay import SymbolData
from app.backtest.run import BacktestConfig, SessionInput, compute_run_digest
from app.backtest.slippage import SlippageModel
from app.backtest.strategy_run import run_strategy_backtest, strategy_config
from app.domain.params import RulesetParams
from app.rulesets import load_ruleset

from ..test_ruleset_integrity import RELEASED_HASHES
from ..trading._session import mk
from .b0_support import INDEPENDENT_RD, SOLO_RD, ctx
from .test_solo_approval import _history, _run, _spec, all_, indep, solo, write

D = Decimal
ENGINE = Path(__file__).resolve().parents[2]
P6 = load_ruleset("pa-intraday", "0.6.0")
OR3 = [("1002", "1005", "1000", "1003"), ("1003", "1004", "1001", "1002"), ("1002", "1003", "1000.5", "1001")]
ROWS = [
    *OR3,
    ("1003", "1004", "1001", "1003"),
    ("1003", "1007", "1002", "1006"),
    ("1005", "1020", "1004", "1019"),
]


def _sources(*dirs: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for d in dirs:
        for p in sorted((ENGINE / d).rglob("*.py")):
            if "__pycache__" not in p.parts:
                out[str(p.relative_to(ENGINE))] = p.read_text()
    return out


APP, SCRIPTS = _sources("app"), _sources("scripts")
ALL = {**APP, **SCRIPTS}


def _files(pattern: str, sources: dict[str, str] = ALL) -> set[str]:
    rx = re.compile(pattern, re.MULTILINE)
    return {k for k, v in sources.items() if rx.search(v)}


# --- 1. the invocation inventory is closed: a new caller fails these tests until it is audited -----------------------


def test_only_the_audited_modules_mention_the_b0_strategy_or_detector() -> None:
    assert _files(r"orb_b0|detect_orb_b0|OrbB0Setup") == {
        "app/backtest/b0_contract.py", "app/backtest/b0_run.py", "app/backtest/controls.py",
        "app/backtest/run.py", "app/domain/levels.py", "app/domain/setups/orb_b0.py",
        "app/domain/strategies.py", "scripts/run_orb_b0.py",
    }  # fmt: skip


def test_the_execution_context_is_issued_only_by_the_strict_runner_module() -> None:
    assert _files(r"issue_context\(") == {"app/backtest/b0_contract.py", "app/backtest/b0_run.py"}
    assert _files(r"B0ExecutionContext\(") == {"app/backtest/b0_contract.py"}
    assert _files(r"B0Reference\(") == {"app/backtest/b0_run.py"}


def test_configs_evidence_controls_and_chunks_have_only_the_audited_callers() -> None:
    assert _files(r"\bBacktestConfig\(") == {"app/backtest/strategy_run.py", "scripts/run_backtest.py"}
    assert _files(r"\bbuild_evidence\(") == {"app/backtest/evidence.py", "scripts/run_orb_b0.py"}
    assert _files(r"\bEvidenceRecord\(") == {"app/backtest/evidence.py"}
    assert _files(r"simulate_control_set\(") == {
        "app/backtest/controls.py"
    }  # defined, never called in app/scripts
    assert _files(r"\bsave_chunk\(|\bmerge_chunks\(") == {"app/backtest/chunks.py", "scripts/merge_backtests.py",
                                                         "scripts/run_backtest.py"}  # fmt: skip
    assert _files(r"\brun_strategy_backtest\(") == {"app/backtest/b0_run.py", "app/backtest/strategy_run.py",
                                                    "scripts/run_backtest.py"}  # fmt: skip
    assert _files(r"\bstrategy_config\(") == {"app/backtest/chunks.py", "app/backtest/controls.py",
                                              "app/backtest/strategy_run.py"}  # fmt: skip


def test_every_legacy_command_line_that_takes_a_strategy_or_ruleset_has_the_guard() -> None:
    takes = _files(r'"--ruleset"|"--strategy"', SCRIPTS)
    guarded = _files(r"legacy_refusal\(", SCRIPTS)
    assert takes == guarded, takes ^ guarded


def test_the_released_hash_has_a_single_definition_and_no_environment_override() -> None:
    assert _files(r"^B0_RULESET_HASH\s*=") == {"app/backtest/b0_contract.py"}
    for name in ("app/backtest/b0_contract.py", "app/backtest/b0_run.py", "scripts/run_orb_b0.py"):
        assert not re.search(r"os\.environ|getenv|get_settings\(\)\.\w*hash", ALL[name]), name


# --- 2. fabricated, edited and reused evidence ------------------------------------------------------------------------


def test_a_hand_built_dict_without_a_context_cannot_create_a_b0_configuration() -> None:
    for rd in (INDEPENDENT_RD, SOLO_RD):
        with pytest.raises(B0ContractError, match="execution context"):
            strategy_config("orb_b0", "4a", P6, D("1"), CostSchedule(), "e", "d", "u", reference_data=rd)


def test_a_context_cannot_be_edited_or_paired_with_other_data_or_another_ruleset() -> None:
    c = ctx(P6)
    with pytest.raises(B0ContractError, match="digest"):
        replace(c, reference_data=c.reference_data[:-1])  # edited after issue
    with pytest.raises(B0ContractError, match="digest"):
        B0ExecutionContext("orb_b0", B0_RULESET_HASH, c.reference_data, "0" * 64)  # forged digest
    with pytest.raises(B0ContractError, match="different reference data"):  # evidence from another table set
        strategy_config("orb_b0", "4a", P6, D("1"), CostSchedule(), "e", "d", "u",
                        reference_data=SOLO_RD, b0_context=c)  # fmt: skip
    other = replace(P6, values={**P6.values, "orb.target_k": 3.0})
    with pytest.raises(B0ContractError):  # context of the released ruleset on a changed one
        strategy_config("orb_b0", "4a", other, D("1"), CostSchedule(), "e", "d", "u",
                        reference_data=INDEPENDENT_RD, b0_context=c)  # fmt: skip
    with pytest.raises(B0ContractError):  # a context cannot be issued for a changed ruleset either
        issue_context(other, INDEPENDENT_RD)


def test_the_documented_limit_a_self_consistent_context_issued_by_hand_is_accepted() -> None:
    """The guarantee is consistency and accident-proofing, not runner origin: code that calls `issue_context`
    with well-formed evidence gets a context. No secret exists, and none is claimed (b0_contract docstring)."""
    forged = issue_context(P6, INDEPENDENT_RD)
    cfg = BacktestConfig(P6, D("1"), CostSchedule(), "e", "d", "u", strategy_id="orb_b0",
                         reference_data=INDEPENDENT_RD, b0_context=forged)  # fmt: skip
    assert cfg.strategy_id == "orb_b0"
    # ... but such a config still cannot carry unapproved or contradictory evidence:
    with pytest.raises(B0ContractError):
        issue_context(
            P6, {**INDEPENDENT_RD, "approval_basis": "INDEPENDENTLY_REVIEWED", "tick_review_status": ""}
        )


def test_validated_evidence_cannot_change_after_validation() -> None:
    rd = dict(INDEPENDENT_RD)
    cfg = BacktestConfig(P6, D("1"), CostSchedule(), "e", "d", "u", strategy_id="orb_b0",
                         reference_data=rd, b0_context=ctx(P6, rd))  # fmt: skip
    rd["tick_table_sha256"] = "f" * 64
    rd["result_label"] = "tampered"
    assert cfg.reference_data["tick_table_sha256"] == "a" * 64 and cfg.reference_data["result_label"] == ""
    assert isinstance(cfg.reference_data, MappingProxyType)
    with pytest.raises(TypeError):
        cfg.reference_data["result_label"] = "x"  # type: ignore[index]


def _result(tmp_path: Path, rows=None, solo_run: bool = False):  # type: ignore[no-untyped-def]
    ref = b0_run.build_reference(
        write(tmp_path, all_(solo() if solo_run else indep())), allow_solo_research=solo_run
    )
    five, fifteen = _history()
    sym = SymbolData("A", [*five, *mk(rows or ROWS)], fifteen, None, D("0.05"))
    res = b0_run.run_b0([SessionInput(_spec(), [sym])], P6, ref, "4a", D("100000"), "e", "d", "u",
                        SlippageModel.uniform(D("0.05"), "u"))  # fmt: skip
    return ref, res


def _evidence(ref, res):  # type: ignore[no-untyped-def]
    assert ref.approval is not None
    return build_evidence(
        run_kind="ORB_B0_4A", data_class="DEVELOPMENT", strategy_id="orb_b0", ruleset="pa-intraday 0.6.0",
        ruleset_hash=res.record.ruleset_hash, commit="UNKNOWN", working_tree_clean=None,
        reference_hashes=res.record.reference_data, engine_version="e", inputs_hash=res.record.inputs_hash,
        first_session=str(res.record.first_session), last_session=str(res.record.last_session), variant_number=1,
        approval=ref.approval, run_digest=res.record.run_digest,
    )  # fmt: skip


def test_evidence_is_bound_to_its_run_and_cannot_be_reused_or_attached_elsewhere(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    ref_a, res_a = _result(tmp_path / "a")
    other_rows = [
        *OR3,
        ("1003", "1004", "1001", "1003"),
        ("1003", "1008", "1002", "1007"),
        ("1006", "1020", "1005", "1019"),
    ]
    _ref_b, res_b = _result(tmp_path / "b", other_rows)
    ev_a = _evidence(ref_a, res_a)
    assert len(res_a.record.run_digest) == 64 and res_a.record.run_digest == compute_run_digest(res_a.record)
    verify_evidence_for_result(ev_a, res_a)  # its own run: fine
    assert res_a.record.inputs_hash != res_b.record.inputs_hash
    with pytest.raises(EvidenceError, match="different run"):
        verify_evidence_for_result(ev_a, res_b)  # reuse on another run's result
    with pytest.raises(EvidenceError, match="altered"):
        verify_evidence_for_result(ev_a, replace(res_a, record=replace(res_a.record, sessions=99)))
    with pytest.raises(EvidenceError, match="run digest"):
        build_evidence(**{**_kwargs(ref_a, res_a), "run_digest": ""})  # B0 evidence without a digest
    with pytest.raises(EvidenceError):
        build_evidence(**{**_kwargs(ref_a, res_a), "run_digest": "zz"})


def _kwargs(ref, res):  # type: ignore[no-untyped-def]
    return {
        "run_kind": "ORB_B0_4A", "data_class": "DEVELOPMENT", "strategy_id": "orb_b0", "ruleset": "pa-intraday 0.6.0",
        "ruleset_hash": res.record.ruleset_hash, "commit": "UNKNOWN", "working_tree_clean": None,
        "reference_hashes": res.record.reference_data, "engine_version": "e", "inputs_hash": res.record.inputs_hash,
        "first_session": None, "last_session": None, "variant_number": 1, "approval": ref.approval,
        "run_digest": res.record.run_digest,
    }  # fmt: skip


def test_a_legacy_result_cannot_be_paired_with_b0_evidence_or_look_like_one(tmp_path: Path) -> None:
    ref, res = _result(tmp_path)
    ev = _evidence(ref, res)
    legacy_cfg = strategy_config("liquidity_sweep_reversal", "4a", load_ruleset("pa-intraday", "0.3.0"), D("1"),
                                 CostSchedule(), "e", "d", "u")  # fmt: skip
    assert legacy_cfg.reference_data == {}
    legacy = run_strategy_backtest("liquidity_sweep_reversal", "4a", [], load_ruleset("pa-intraday", "0.3.0"),
                                   D("100000"), CostSchedule(), "e", "d", "u")  # fmt: skip
    assert legacy.record.run_digest == "" and legacy.record.reference_data == {}
    with pytest.raises(EvidenceError, match="strict B0 path"):
        verify_evidence_for_result(ev, legacy)


def test_solo_and_independent_runs_keep_their_labels_and_verify(tmp_path: Path) -> None:
    (tmp_path / "s").mkdir()
    (tmp_path / "i").mkdir()
    ref_s, res_s = _result(tmp_path / "s", solo_run=True)
    ref_i, res_i = _result(tmp_path / "i")
    ev_s, ev_i = _evidence(ref_s, res_s), _evidence(ref_i, res_i)
    verify_evidence_for_result(ev_s, res_s)
    verify_evidence_for_result(ev_i, res_i)
    assert (
        ev_s.result_label == "EXPLORATORY — SOLO RESEARCH — NOT INDEPENDENTLY VALIDATED"
        and ev_i.result_label is None
    )
    assert (
        res_s.record.reference_data["result_label"] == ev_s.result_label
        and res_i.record.reference_data["result_label"] == ""
    )
    assert (
        res_s.record.run_digest != res_i.record.run_digest
    )  # the approval basis is part of the run identity
    with pytest.raises(EvidenceError, match="different run"):
        verify_evidence_for_result(ev_i, res_s)


# --- 3. ruleset-hash integrity ---------------------------------------------------------------------------------------


def test_the_released_hash_agrees_across_every_source() -> None:
    seeder = json.loads((ENGINE.parent / "backend/database/seeders/data/pa-intraday-0.6.0.json").read_text())
    seeded = RulesetParams("pa-intraday", "0.6.0", seeder).content_hash
    assert B0_RULESET_HASH == RELEASED_HASHES[("pa-intraday", "0.6.0")] == P6.content_hash == seeded
    assert b0_run.B0_RULESET_HASH == B0_RULESET_HASH
    assert hashlib.sha256(b"").hexdigest() != B0_RULESET_HASH


def test_a_changed_ruleset_cannot_produce_an_apparently_valid_b0_result(tmp_path: Path) -> None:
    changed = replace(P6, values={**P6.values, "setup.breakout_buffer_pct": 0.1})
    ref = b0_run.build_reference(write(tmp_path, all_(indep())))
    with pytest.raises(b0_run.B0RunRefused, match="content hash"):
        b0_run.run_b0([], changed, ref, "4a", D("1"), "e", "d", "u", SlippageModel.uniform(D("0"), "u"))
    with pytest.raises(B0ContractError, match="content hash"):
        strategy_config("orb_b0", "4a", changed, D("1"), CostSchedule(), "e", "d", "u",
                        reference_data=INDEPENDENT_RD, b0_context=ctx(P6))  # fmt: skip
    _, res = _result(tmp_path / "x") if (tmp_path / "x").mkdir() is None else (None, None)
    assert res is not None
    with pytest.raises(EvidenceError, match="released hash"):
        build_evidence(**{**_kwargs(ref, res), "ruleset_hash": changed.content_hash})


def test_a_test_only_hash_override_never_reaches_production_validation(small_b0_hash: None) -> None:
    small = replace(P6, values={**P6.values, "analysis.min_bars_5m": 5, "analysis.min_bars_15m": 5})
    assert b0_contract.B0_RULESET_HASH == small.content_hash != B0_RULESET_HASH  # the fixture is active
    assert b0_run.B0_RULESET_HASH != b0_contract.B0_RULESET_HASH  # the runner holds its own binding
    with pytest.raises(b0_run.B0RunRefused, match="content hash"):
        b0_run.check_b0_ruleset(small)  # the strict runner still refuses the modified copy


def test_the_override_is_gone_after_the_test_and_the_released_file_still_passes() -> None:
    assert b0_contract.B0_RULESET_HASH == B0_RULESET_HASH == RELEASED_HASHES[("pa-intraday", "0.6.0")]
    b0_run.check_b0_ruleset(b0_run.load_b0_ruleset())


# --- 4. chunking and merging ---------------------------------------------------------------------------------------------


def test_b0_chunks_can_neither_be_saved_nor_merged(tmp_path: Path) -> None:
    ref = b0_run.build_reference(write(tmp_path, all_(indep())))
    res = _run(ref)
    for meta in ({"strategy_id": "orb_b0", "ruleset": "pa-intraday@0.4.0"},
                 {"strategy_id": "failed_breakout", "ruleset": "pa-intraday@0.6.0"}):  # fmt: skip
        with pytest.raises(B0ContractError, match=r"scripts/run_orb_b0\.py"):
            chunks.save_chunk(tmp_path / "c.pkl", res, meta, [])
        assert not (tmp_path / "c.pkl").exists()
        f = tmp_path / "evil.pkl"
        f.write_bytes(pickle.dumps({"meta": meta, "sessions": [], "exclusions": [], "inputs_hash": "x",
                                    "engine_version": "e"}))  # fmt: skip
        with pytest.raises(B0ContractError, match=r"scripts/run_orb_b0\.py"):
            chunks.merge_chunks([f])


# --- 5. non-B0 behaviour -----------------------------------------------------------------------------------------------


def test_non_b0_run_records_are_unchanged() -> None:
    old = load_ruleset("pa-intraday", "0.3.0")
    r = run_strategy_backtest(
        "liquidity_sweep_reversal", "4a", [], old, D("100000"), CostSchedule(), "e", "d", "u"
    )
    assert (r.record.run_digest, r.record.reference_data) == ("", {})
    cfg = BacktestConfig(old, D("1"), CostSchedule(), "e", "d", "u")
    assert (
        cfg.reference_data == {}
        and cfg.b0_context is None
        and not isinstance(cfg.reference_data, MappingProxyType)
    )
