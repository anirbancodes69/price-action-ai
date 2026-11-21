"""Isolation proof on stored real bars (independent backtesting standards §3). Run from `python-engine/`:

  uv run python scripts/check_strategy_isolation.py --strategy liquidity_sweep_reversal \
      --ruleset pa-intraday@0.3.0 --sessions 3 --symbols 8 [--to 2026-11-19] [--members-on 2026-11-19]

For each chosen session and symbol, at every 5m bar, the strategy's setups from the single-strategy run (only
its detector) must equal the same strategy's setups from the combined run (every detector), including levels.
Exit code 1 on any difference. Needs DATABASE_URL (engine role) and INGEST_DATA_SOURCE_ID.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.backtest.loader import load_backtest_inputs
from app.backtest.replay import SessionSpec, SymbolData
from app.domain.analyse import analyse
from app.domain.strategies import strategy_detectors
from app.ingestion.universe import universe_members
from app.rulesets import load_ruleset
from app.settings import get_settings

# Setup type names per strategy id (the combined run's setups are filtered to the strategy's own type).
STRATEGY_TYPE = {"liquidity_sweep_reversal": "LIQUIDITY_SWEEP_REVERSAL"}


def _run(sym: SymbolData, k: int, spec: SessionSpec, params, **kw):  # type: ignore[no-untyped-def]
    b5 = list(sym.bars_5m[:k])
    b15 = [b for b in sym.bars_15m if b.end <= b5[-1].end]
    return analyse(
        b5, b15, spec.session_open, sym.prev_day, params, spec.previous_session_open, sym.tick,
        spec.session_close, sym.zone_cache, **kw,
    )  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--strategy", required=True, choices=sorted(STRATEGY_TYPE))
    p.add_argument("--ruleset", default="pa-intraday@0.3.0")
    p.add_argument("--code", default="NIFTY50")
    p.add_argument("--to", type=date.fromisoformat, default=date(2026, 11, 19))
    p.add_argument("--members-on", type=date.fromisoformat, default=date(2026, 11, 19))
    p.add_argument("--sessions", type=int, default=3)
    p.add_argument("--symbols", type=int, default=8)
    a = p.parse_args(argv)
    s = get_settings()
    if not s.ingest_data_source_id:
        print("Set INGEST_DATA_SOURCE_ID.", file=sys.stderr)
        return 2
    code, version = a.ruleset.split("@")
    params = load_ruleset(code, version)
    engine = create_engine(s.database_url.get_secret_value())
    with engine.connect() as conn:
        members = universe_members(conn, a.code, a.members_on)
        first = date.fromordinal(a.to.toordinal() - 3 * a.sessions - 4)
        inputs = load_backtest_inputs(
            conn, uuid.UUID(s.ingest_data_source_id), members, first, a.to,
            params.int_("analysis.lookback_sessions"),
        )  # fmt: skip
    engine.dispose()
    inputs = inputs[-a.sessions :]
    detectors, stype = strategy_detectors(a.strategy), STRATEGY_TYPE[a.strategy]
    checked = candidates = bad = 0
    for inp in inputs:
        for sym in sorted(inp.symbols, key=lambda x: x.symbol)[: a.symbols]:
            idx = [
                i
                for i, b in enumerate(sym.bars_5m)
                if inp.spec.session_open <= b.start < inp.spec.session_close
            ]
            for i in idx:
                alone = _run(sym, i + 1, inp.spec, params, detectors=detectors, isolated=True)
                both = _run(sym, i + 1, inp.spec, params)
                if alone.setups is None or both.setups is None:
                    continue
                want = [(x.setup, x.levels) for x in both.setups if x.setup.type.value == stype]
                got = [(x.setup, x.levels) for x in alone.setups]
                checked += 1
                candidates += len(got)
                if got != want:
                    bad += 1
                    print(f"DIFFERENT {inp.spec.session_date} {sym.symbol} bar {i}", file=sys.stderr)
    print(
        f"{a.strategy} {a.ruleset}: {len(inputs)} sessions, {checked} analyses, "
        f"{candidates} setups, {bad} differences"
    )
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
