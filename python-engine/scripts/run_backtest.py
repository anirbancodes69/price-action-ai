"""Run an intraday backtest on stored candles and print the metrics. Run from `python-engine/`:

  uv run python scripts/run_backtest.py --from 2024-01-01 --to 2024-06-30 [--code NIFTY50]
      [--capital 100000] [--sizing FIXED|COMPOUNDING] [--split all|is|oos|holdout] [--json out.json]
      [--strategy liquidity_sweep_reversal --experiment 4a|4b [--tie-break-seed 1]]

With --strategy the single-strategy run mode is used (independent backtesting standards §3-§4): only that
strategy's detector, no score gate, experiment 4a (no account limits) or 4b (project limits, seeded
tie-break).
Without it the combined engine runs and the result is flagged NOT_ISOLATED.

Needs DATABASE_URL (an engine-role URL), INGEST_DATA_SOURCE_ID and loaded candles
(`scripts/market_data_cli.py backfill`). Hypothetical, simulated results (TRD-06 BT-06).
Never prints credentials.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `app` importable when run as a script

from app.backtest.costs import CostSchedule
from app.backtest.exclusions import SPECIAL_SESSIONS, Exclusion, summarise
from app.backtest.loader import load_backtest_inputs, load_daily_levels
from app.backtest.report import format_report, report_dict
from app.backtest.run import BacktestConfig, run_backtest
from app.backtest.splits import split_sessions
from app.backtest.strategy_run import run_strategy_backtest
from app.domain.strategies import STRATEGY_DETECTORS
from app.ingestion.universe import universe_members
from app.rulesets import load_ruleset
from app.settings import get_settings


def _engine_version() -> str:
    data = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())
    return f"{data['project']['name']} {data['project']['version']}"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--code", default="NIFTY50")
    p.add_argument("--from", dest="from_", type=date.fromisoformat, required=True)
    p.add_argument("--to", type=date.fromisoformat, required=True)
    p.add_argument("--capital", type=Decimal, default=Decimal(100000))
    p.add_argument("--sizing", choices=["FIXED", "COMPOUNDING"], default="FIXED")
    p.add_argument("--split", choices=["all", "is", "oos", "holdout"], default="all")
    p.add_argument("--ruleset", default="pa-intraday@0.1.0")
    p.add_argument(
        "--members-on",
        type=date.fromisoformat,
        help="date whose universe membership is used (default --to). Membership is stored from 2026-11,\n"
        "so an "
        "older range needs a recent date; the run stays flagged survivorship_bias_risk",
    )
    p.add_argument("--json", dest="json_out", type=Path)
    p.add_argument("--strategy", choices=sorted(STRATEGY_DETECTORS))
    p.add_argument("--experiment", choices=["4a", "4b"])
    p.add_argument("--tie-break-seed", type=int, default=1)
    return p


def main(argv: list[str] | None = None) -> int:
    a = _parser().parse_args(argv)
    s = get_settings()
    if not s.ingest_data_source_id:
        print("Set INGEST_DATA_SOURCE_ID (the data source whose candles to replay).", file=sys.stderr)
        return 2
    source = uuid.UUID(s.ingest_data_source_id)
    if bool(a.strategy) != bool(a.experiment):
        print("--strategy and --experiment go together.", file=sys.stderr)
        return 2
    code, version = a.ruleset.split("@")
    params = load_ruleset(code, version)
    engine = create_engine(s.database_url.get_secret_value())
    with engine.connect() as conn:
        members = universe_members(conn, a.code, a.members_on or a.to)
        if not members:
            print(
                f"No members in universe {a.code} on {a.members_on or a.to}. "
                "Run market_data_cli.py load-universe.",
                file=sys.stderr,
            )
            return 2
        exclusions: list[Exclusion] = []
        if a.strategy:
            # D-7: previous-day levels from the official 1D bars, special sessions out of the replay.
            margin = timedelta(days=params.int_("analysis.lookback_sessions") * 2 + 14)
            daily = {
                sym: load_daily_levels(conn, source, iid, a.from_ - margin, a.to)
                for sym, iid in members.items()
            }
            inputs = load_backtest_inputs(
                conn,
                source,
                members,
                a.from_,
                a.to,
                params.int_("analysis.lookback_sessions"),
                daily_levels=daily,
                skip_days=set(SPECIAL_SESSIONS),
                exclusions=exclusions,
            )
        else:
            inputs = load_backtest_inputs(
                conn, source, members, a.from_, a.to, params.int_("analysis.lookback_sessions")
            )
    engine.dispose()
    if a.split != "all":
        sp = split_sessions([i.spec.session_date for i in inputs])
        keep = {"is": sp.in_sample, "oos": sp.out_of_sample, "holdout": sp.holdout}[a.split]
        inputs = [i for i in inputs if i.spec.session_date in set(keep)]
    if not inputs:
        print("No sessions with stored 5m bars in that range.", file=sys.stderr)
        return 2
    if a.strategy:
        result = run_strategy_backtest(
            a.strategy,
            a.experiment,
            inputs,
            params,
            a.capital,
            CostSchedule(),
            _engine_version(),
            s.ingest_provider,
            a.code,
            tie_break_seed=a.tie_break_seed,
            purpose=f"EXPLORATION:{a.split}",
        )
        print(format_report(result))
        print("Exclusions: " + (", ".join(f"{k} {v}" for k, v in summarise(exclusions).items()) or "none"))
        if a.json_out:
            out = report_dict(result)
            out["exclusions"] = [
                {"day": e.day.isoformat(), "symbol": e.symbol, "reason": e.reason} for e in exclusions
            ]
            a.json_out.write_text(json.dumps(out, indent=2))
            print(f"\nFull result written to {a.json_out}")
        return 0
    cfg = BacktestConfig(
        params,
        a.capital,
        CostSchedule(),
        _engine_version(),
        s.ingest_provider,
        a.code,
        sizing_mode=a.sizing,
        purpose=f"EXPLORATION:{a.split}",
    )
    result = run_backtest(inputs, cfg)
    print(format_report(result))
    if a.json_out:
        a.json_out.write_text(json.dumps(report_dict(result), indent=2))
        print(f"\nFull result written to {a.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
