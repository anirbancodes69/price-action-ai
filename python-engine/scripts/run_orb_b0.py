"""Strict runner for the ORIGINAL ORB B0 historical backtest. **NOT AUTHORISED TO RUN.** From
`python-engine/`:

  .venv/bin/python scripts/run_orb_b0.py --from FIRST --to LAST --members-on DATE --experiment 4a|4b \
      --tick-table P --tick-sha256 H --event-table P --event-sha256 H --session-table P --session-sha256 H \
      --price-basis P --price-basis-manifest P --price-basis-sha256 H --variant-ledger LEDGER.json
      --out-dir DIR

Only `orb_b0` on `pa-intraday 0.6.0` (its released hash) can run. Every reference table must be pinned by
SHA-256,
carry `review_status` INDEPENDENTLY_REVIEWED (DR-7/DR-7a) and load without conflict, or the run stops
before any
candle is read. There is no default tick, session close or special-session list. The result is written only if
the signal and rejection accounting reconciles, and an existing output file is never overwritten.
Needs DATABASE_URL (engine role, read only here) and INGEST_DATA_SOURCE_ID. Simulated results, never advice.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.backtest.b0_accounting import classify_all, reconcile
from app.backtest.b0_run import (
    B0Pins,
    B0RunRefused,
    TablePin,
    build_reference,
    load_b0_inputs,
    load_b0_ruleset,
    run_b0,
)
from app.backtest.evidence import VariantLedger, build_evidence, verify_evidence_for_result
from app.backtest.loader import load_daily_levels
from app.backtest.report import report_dict
from app.backtest.slippage import from_options
from app.backtest.strategy_run import strategy_analyse
from app.ingestion.universe import universe_members
from app.settings import get_settings


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--code", default="NIFTY50")
    p.add_argument("--from", dest="from_", type=date.fromisoformat, required=True)
    p.add_argument("--to", type=date.fromisoformat, required=True)
    p.add_argument("--members-on", type=date.fromisoformat, required=True)
    p.add_argument("--experiment", choices=["4a", "4b"], required=True)
    p.add_argument("--capital", type=Decimal, default=Decimal(100000))
    p.add_argument("--tie-break-seed", type=int, default=1)
    p.add_argument("--data-class", choices=["DEVELOPMENT", "RESERVE"], required=True)
    for name in ("tick", "event", "session"):
        p.add_argument(f"--{name}-table", type=Path, required=True)
        p.add_argument(f"--{name}-sha256", required=True)
    p.add_argument("--price-basis", type=Path, required=True)
    p.add_argument("--price-basis-manifest", type=Path, required=True)
    p.add_argument("--price-basis-sha256", required=True)
    p.add_argument(
        "--solo-research-exception",
        action="store_true",
        help="accept OWNER_APPROVED_SOLO_RESEARCH tables (DEC-045 / DR-12); the result then "
        "carries the label EXPLORATORY — SOLO RESEARCH — NOT INDEPENDENTLY VALIDATED. Off by default",
    )
    p.add_argument("--variant-ledger", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    return p


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout.strip()  # noqa: S603,S607


def main(argv: list[str] | None = None) -> int:
    a = parser().parse_args(argv)
    out = a.out_dir / f"orb_b0_{a.experiment}_{a.data_class.lower()}.json"
    if out.exists():
        print(f"Refusing to overwrite existing evidence: {out}", file=sys.stderr)
        return 2
    try:
        params = load_b0_ruleset()
        reference = build_reference(
            B0Pins(
                TablePin(a.tick_table, a.tick_sha256),
                TablePin(a.event_table, a.event_sha256),
                TablePin(a.session_table, a.session_sha256),
                TablePin(a.price_basis, a.price_basis_sha256),
                a.price_basis_manifest,
            ),
            allow_solo_research=a.solo_research_exception,
        )
    except B0RunRefused as e:
        print(f"B0 run refused before reading any data: {e}", file=sys.stderr)
        return 3
    s = get_settings()
    if not s.ingest_data_source_id:
        print("Set INGEST_DATA_SOURCE_ID.", file=sys.stderr)
        return 2
    source = uuid.UUID(s.ingest_data_source_id)
    slip = from_options("adverse-all", None, params.decimal("backtest.slippage_pct"))
    engine = create_engine(s.database_url.get_secret_value())
    with engine.connect() as conn:  # read only
        members = universe_members(conn, a.code, a.members_on)
        if not members:
            print("No universe members.", file=sys.stderr)
            return 2
        margin = timedelta(days=params.int_("analysis.lookback_sessions") * 2 + 14)
        daily = {i: load_daily_levels(conn, source, v, a.from_ - margin, a.to) for i, v in members.items()}
        b0 = load_b0_inputs(conn, source, members, a.from_, a.to, params, reference, daily)
    engine.dispose()
    if not b0.sessions:
        print("No eligible sessions.", file=sys.stderr)
        return 2
    data = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())
    engine_version = f"{data['project']['name']} {data['project']['version']}"
    result = run_b0(
        b0.sessions, params, reference, a.experiment, a.capital, engine_version, s.ingest_provider, a.code,
        slip, tie_break_seed=a.tie_break_seed, purpose=f"EXPLORATION:{a.data_class}",
    )  # fmt: skip
    outcomes = classify_all(b0.sessions, params, strategy_analyse("orb_b0"))
    acc = reconcile(outcomes, result, b0.eligibility, b0.exclusions)
    if not acc.reconciles:
        print(
            "Accounting does not reconcile; result NOT written: " + "; ".join(acc.problems), file=sys.stderr
        )
        return 4
    approval = reference.approval
    if approval is None:
        print("The approval basis of the tables is not established; result NOT written.", file=sys.stderr)
        return 4
    ledger = VariantLedger(a.variant_ledger)
    ev = build_evidence(
        run_kind=f"ORB_B0_{a.experiment.upper()}", data_class=a.data_class, strategy_id="orb_b0",
        ruleset="pa-intraday 0.6.0", ruleset_hash=params.content_hash,
        commit=_git("rev-parse", "HEAD") or "UNKNOWN",
        working_tree_clean=not _git("status", "--porcelain"), reference_hashes=reference.hashes,
        engine_version=engine_version, inputs_hash=result.record.inputs_hash,
        first_session=str(result.record.first_session), last_session=str(result.record.last_session),
        variant_number=ledger.register("orb_b0@pa-intraday-0.6.0"), approval=approval,
        run_digest=result.record.run_digest,
        seeds={"tie_break": a.tie_break_seed},
        parameters={"experiment": a.experiment, "capital": str(a.capital), "slippage": "adverse-all"},
    )  # fmt: skip
    verify_evidence_for_result(ev, result)  # the evidence must describe this very run
    a.out_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "result_label": ev.result_label,  # exact solo label for a solo-approved run, else null
        "evidence": json.loads(ev.to_json()),
        "result": report_dict(result),
        "accounting": {
            "evaluated": acc.evaluated, "outcomes": acc.outcomes, "candidates": acc.candidates,
            "filled": acc.filled, "skipped": acc.skipped, "excluded_instrument_sessions": acc.excluded,
            "excluded_sessions": acc.excluded_sessions,
        },
    }  # fmt: skip
    out.write_text(json.dumps(doc, indent=2, default=str))
    print(f"Written {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
