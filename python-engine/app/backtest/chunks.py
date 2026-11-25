"""Save and merge the results of a long single-strategy run executed in date chunks (research harness).

A chunk is a contiguous range of sessions replayed on its own. In experiment 4a the sessions are independent
(account state resets each session, FIXED sizing, one trade per symbol, lookback bars come from before the
chunk), so the chunks joined in date order give the same trades and metrics as one run over the whole range;
`tests/backtest/test_chunks.py` checks it. Files are Python pickles written and read only by this harness
(never load one from an untrusted source).
"""

from __future__ import annotations

import hashlib
import pickle
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.backtest.b0_contract import B0ContractError, legacy_refusal
from app.backtest.costs import CostSchedule
from app.backtest.exclusions import Exclusion
from app.backtest.run import BacktestResult, assemble_result
from app.backtest.slippage import SlippageModel
from app.backtest.strategy_run import strategy_config
from app.rulesets import load_ruleset

META_KEYS = ("ruleset", "strategy_id", "experiment", "capital", "tie_break_seed", "data_source", "universe")
# Chunks saved before D-4 have no slippage entry: they were run with the legacy model.


def save_chunk(
    path: Path, result: BacktestResult, meta: dict[str, Any], exclusions: Sequence[Exclusion]
) -> None:
    _refuse_b0(meta)
    payload = {
        "sessions": result.sessions,
        "meta": meta,
        "exclusions": list(exclusions),
        "inputs_hash": result.record.inputs_hash,
        "engine_version": result.record.engine_version,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(pickle.dumps(payload))
    tmp.replace(path)  # a chunk file is complete or absent


def _refuse_b0(meta: dict[str, Any]) -> None:
    """Chunk files carry no execution context or approval evidence: a B0 run cannot be chunked or merged."""
    msg = legacy_refusal(meta.get("strategy_id"), meta.get("ruleset"))
    if msg:
        raise B0ContractError(msg)


def merge_chunks(paths: Sequence[Path]) -> tuple[BacktestResult, list[Exclusion], dict[str, Any]]:
    chunks = [pickle.loads(p.read_bytes()) for p in paths]  # noqa: S301 - own harness files
    for c in chunks:
        _refuse_b0(c["meta"])  # before anything else: chunk files cannot carry B0 evidence
    chunks.sort(key=lambda c: c["sessions"][0].spec.session_date)
    first = chunks[0]["meta"]
    for c in chunks[1:]:
        if {k: c["meta"][k] for k in META_KEYS} != {k: first[k] for k in META_KEYS} or c["meta"].get(
            "slippage"
        ) != first.get("slippage"):
            raise ValueError("chunks were run with different configurations")
    sessions = [s for c in chunks for s in c["sessions"]]
    days = [s.spec.session_date for s in sessions]
    if days != sorted(set(days)):
        raise ValueError("chunks overlap or are out of order")
    code, version = first["ruleset"].split("@")
    cfg = strategy_config(
        first["strategy_id"],
        first["experiment"],
        load_ruleset(code, version),
        Decimal(first["capital"]),
        CostSchedule(),
        chunks[0]["engine_version"],
        first["data_source"],
        first["universe"],
        tie_break_seed=first["tie_break_seed"],
        purpose=first.get("purpose", "EXPLORATION"),
        slippage=SlippageModel.from_dict(first["slippage"]) if first.get("slippage") else None,
    )
    digest = hashlib.sha256("|".join(c["inputs_hash"] for c in chunks).encode()).hexdigest()
    exclusions = [e for c in chunks for e in c["exclusions"]]
    return assemble_result(sessions, cfg, digest), exclusions, first
