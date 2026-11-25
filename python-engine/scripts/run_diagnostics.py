"""Framework diagnosis runner (T-I144, docs/research/framework-diagnosis-plan.md). Run from `python-engine/`:

  uv run python scripts/run_diagnostics.py --s01 DIR --s02 DIR --out DIR [--members-on 2026-11-19]

Reads the saved 4a in-sample chunk files of Strategy 01 and Strategy 02 (`DIR/*.pkl`) and the stored 5m bars,
runs DX-1 (drift), DX-2 (forward returns), DX-3 (R decomposition), DX-4 (matched random-entry controls),
DX-5 (exit-model bounds, Strategy 01) and DX-7 (simulator spot check) on the in-sample sessions only, and
writes `diagnostics.json` and `diagnostics.txt` (aggregates, plus the trades of the spot check) to `--out`.
It changes no ruleset, detector or replay behaviour. Needs the same environment as `run_backtest.py`.
Hypothetical, simulated results (TRD-06 BT-06).
"""

from __future__ import annotations

import argparse
import glob
import json
import pickle
import random
import sys
import uuid
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `app` importable when run as a script

from app.backtest.b0_contract import legacy_refusal
from app.backtest.costs import CostSchedule
from app.backtest.diagnostics.decompose import (
    BUCKETS,
    Decomposition,
    bucket_of,
    decompose,
    stop_of,
    stop_pct_of,
    verify_trade,
)
from app.backtest.diagnostics.sim import (
    HORIZONS,
    TARGET_R,
    draw_control,
    eligible_signal_bars,
    exit_config,
    exit_price_at,
    forward_returns,
    rules_from,
    session_times,
    simulate,
)
from app.backtest.diagnostics.stats import Interval, Sums, add, bootstrap_mean
from app.backtest.exclusions import SPECIAL_SESSIONS
from app.backtest.loader import load_bars
from app.backtest.trade import Trade
from app.ingestion.session import IST
from app.ingestion.universe import universe_members
from app.rulesets import load_ruleset
from app.settings import get_settings

D = Decimal
SEEDS = (1, 2, 3, 4, 5)
FWD_KEYS = [f"h{h}" for h in HORIZONS] + ["session"]
SESSION_BARS = 75  # 09:15..15:25 on a normal day
SCHED = CostSchedule()


def load_trades(directory: Path) -> dict[str, list[Trade]]:
    """Trades by symbol from the chunk files of one 4a run (own harness files, see app/backtest/chunks.py)."""
    out: dict[str, list[Trade]] = defaultdict(list)
    for f in sorted(glob.glob(str(directory / "*.pkl"))):
        payload = pickle.loads(Path(f).read_bytes())  # noqa: S301 - own harness files
        for s in payload["sessions"]:
            for t in s.trades:
                out[t.symbol].append(t)
    return out


def _day(t: Trade) -> date:
    return t.fill_at.astimezone(IST).date()


class Acc:
    """Per-session sums for every statistic, so the bootstrap can resample whole sessions."""

    def __init__(self) -> None:
        self.s: dict[str, dict[Any, tuple[float, int]]] = defaultdict(dict)
        self.counts: dict[str, int] = defaultdict(int)
        self.rows: dict[str, list[Decomposition]] = defaultdict(list)

    def add(self, name: str, session: Any, value: float) -> None:
        add(self.s[name], session, value)

    def bump(self, name: str, n: int = 1) -> None:
        self.counts[name] += n


def interval(acc: Acc, name: str, other: str | None = None) -> Interval:
    b: Sums | None = acc.s[other] if other else None
    return bootstrap_mean(acc.s[name], b)


def process_symbol(
    symbol: str,
    bars_by_day: dict[date, list[Any]],
    trades: dict[str, list[Trade]],
    rules: Any,
    acc: Acc,
    spot: set[tuple[str, datetime]],
    spot_results: list[dict[str, Any]],
) -> None:
    for day, bars in bars_by_day.items():
        if len(bars) < SESSION_BARS:
            acc.bump("missing_bar_sessions")
        or_end, cutoff, exit_time = session_times(bars, rules)
        month = day.strftime("%Y-%m")
        # DX-1: drift from the first bar after the opening range, and from a seeded random bar
        first = next((b for b in bars if b.start >= or_end), None)
        if first is not None and first.start < cutoff:
            end = exit_price_at(bars, exit_time)
            acc.add("dx1_open", day, float((end - first.open) / first.open * 100))
            acc.add(f"dx1_open_{month}", day, float((end - first.open) / first.open * 100))
            pool = eligible_signal_bars(bars, or_end, cutoff)
            if pool:
                s = random.Random(f"1|{symbol}|{day}|drift").choice(pool)  # noqa: S311
                px = bars[s + 1].open
                acc.add("dx1_random", day, float((end - px) / px * 100))
    idx_by_day = {d: {b.start: k for k, b in enumerate(bs)} for d, bs in bars_by_day.items()}
    for sid, by_symbol in trades.items():
        mine = sorted(by_symbol.get(symbol, []), key=lambda t: t.fill_at)
        last_exit = dict.fromkeys(SEEDS, (None, 0))  # seed -> (day, exit bar index) of its last control
        for n, t in enumerate(mine):
            day = _day(t)
            bars = bars_by_day.get(day)
            if bars is None or t.fill_at not in idx_by_day[day]:
                acc.bump(f"{sid}_no_bars")
                continue
            i = idx_by_day[day][t.fill_at]
            _, cutoff, exit_time = session_times(bars, rules)
            stop = stop_of(t)
            pct = stop_pct_of(t)
            # DX-3
            dec = decompose(t, bars[i], bars[i - 1].close if i else None, rules.slippage_pct)
            acc.rows[sid].append(dec)
            acc.add(f"{sid}_recorded_gross", day, float(t.r_gross))
            acc.add(f"{sid}_recorded_net", day, float(t.r_net))
            # common exit on the strategy's own entry
            tgt = t.entry + TARGET_R * (t.entry - stop)
            cfg = exit_config(rules, exit_time)
            common = simulate(bars, i, symbol, t.entry, stop, t.qty, tgt, cfg, SCHED)
            acc.add(f"{sid}_common_gross", day, float(common.r_gross))
            acc.add(f"{sid}_common_net", day, float(common.r_net))
            for key, (p, u) in forward_returns(bars, i, t.entry, stop, exit_time).items():
                acc.add(f"{sid}_fwd_pct_{key}", day, p)
                acc.add(f"{sid}_fwd_units_{key}", day, u)
            # DX-5 on Strategy 01 entries
            if sid == "s01":
                variants = {
                    "optimistic_collision": simulate(
                        bars, i, symbol, t.entry, stop, t.qty, tgt, cfg, SCHED, optimistic=True
                    ),
                    "no_stop_slippage": simulate(
                        bars,
                        i,
                        symbol,
                        t.entry,
                        stop,
                        t.qty,
                        tgt,
                        exit_config(rules, exit_time, stop_slippage=False),
                        SCHED,
                    ),
                    "hold_6_bars": simulate(
                        bars, i, symbol, t.entry, stop, t.qty, tgt, cfg, SCHED, horizon=6
                    ),
                    "hold_12_bars": simulate(
                        bars, i, symbol, t.entry, stop, t.qty, tgt, cfg, SCHED, horizon=12
                    ),
                    "hold_to_session_exit": simulate(
                        bars, i, symbol, t.entry, stop, t.qty, tgt * 1000, cfg, SCHED
                    ),
                }
                for name, vt in variants.items():
                    acc.add(f"dx5_{name}_gross", day, float(vt.r_gross))
                    acc.add(f"dx5_{name}_net", day, float(vt.r_net))
                if (symbol, t.fill_at) in spot:
                    mism = verify_trade(bars, t, rules.slippage_pct, exit_time)
                    spot_results.append(
                        {
                            "symbol": symbol,
                            "fill_at": t.fill_at.isoformat(),
                            "reason": t.reason,
                            "mismatches": mism,
                        }
                    )
            # DX-4 / DX-2 controls: same symbol and session, same stop distance, same exit and fill rule
            for seed in SEEDS:
                prev_day, after = last_exit[seed]
                after = after if prev_day == day else 0
                rng = random.Random(f"{seed}|{sid}|{symbol}|{day}|{n}")  # noqa: S311
                c = draw_control(bars, symbol, pct, rng, rules, SCHED, after_index=after)
                if c is None:
                    acc.bump(f"{sid}_control_missing")
                    continue
                acc.bump(f"{sid}_control_redraws", c.redraws)
                acc.bump(f"{sid}_controls")
                acc.add(f"{sid}_control_gross", day, float(c.trade.r_gross))
                acc.add(f"{sid}_control_net", day, float(c.trade.r_net))
                for key, (p, u) in c.forward.items():
                    acc.add(f"{sid}_ctlfwd_pct_{key}", day, p)
                    acc.add(f"{sid}_ctlfwd_units_{key}", day, u)
                ex_idx = idx_by_day[day].get(c.trade.exit_at, len(bars))
                last_exit[seed] = (day, ex_idx)
            acc.bump(f"{sid}_trades")


def fmt(i: Interval, nd: int = 3) -> dict[str, float]:
    return {"est": round(i.estimate, nd), "lo": round(i.low, nd), "hi": round(i.high, nd), "n": i.n}


def summarise(acc: Acc, spot_results: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"counts": dict(acc.counts), "dx1": {}, "dx3": {}, "dx4": {}, "dx2": {}, "dx5": {}}
    for name in ("dx1_open", "dx1_random"):
        out["dx1"][name] = fmt(interval(acc, name), 4)
    months = sorted({k.split("_", 2)[2] for k in acc.s if k.startswith("dx1_open_")})
    out["dx1"]["by_month_open"] = {m: fmt(interval(acc, f"dx1_open_{m}"), 4) for m in months}
    for sid in ("s01", "s02"):
        rows = acc.rows[sid]
        buckets: dict[str, Any] = {}
        for k in [*range(len(BUCKETS)), -1]:
            lo_hi = f"{BUCKETS[k][0]}-{BUCKETS[k][1]}%" if k >= 0 else "outside"
            sel = [r for r in rows if bucket_of(D(str(r.stop_pct))) == k]
            if not sel:
                continue
            m = len(sel)
            buckets[lo_hi] = {
                "trades": m,
                "avg_stop_pct": round(sum(r.stop_pct for r in sel) / m, 3),
                **{
                    name: round(sum(getattr(r, name) for r in sel) / m, 3)
                    for name in (
                        "r_gross",
                        "r_net",
                        "before_friction",
                        "entry_slip",
                        "stop_slip",
                        "charges",
                        "fill_gap",
                    )
                },
            }
        tot = len(rows) or 1
        out["dx3"][sid] = {
            "buckets": buckets,
            "all": {
                name: round(sum(getattr(r, name) for r in rows) / tot, 3)
                for name in (
                    "r_gross",
                    "r_net",
                    "before_friction",
                    "entry_slip",
                    "stop_slip",
                    "charges",
                    "fill_gap",
                )
            },
        }
        d4: dict[str, Any] = {}
        for kind in ("gross", "net"):
            d4[f"recorded_{kind}"] = fmt(interval(acc, f"{sid}_recorded_{kind}"))
            d4[f"strategy_common_{kind}"] = fmt(interval(acc, f"{sid}_common_{kind}"))
            d4[f"control_{kind}"] = fmt(interval(acc, f"{sid}_control_{kind}"))
            diff = interval(acc, f"{sid}_common_{kind}", f"{sid}_control_{kind}")
            d4[f"diff_{kind}"] = {**fmt(diff), "material": diff.material(0.05)}
        out["dx4"][sid] = d4
        d2: dict[str, Any] = {}
        for key in FWD_KEYS:
            for unit, thr in (("pct", 0.02), ("units", 0.05)):
                diff = interval(acc, f"{sid}_fwd_{unit}_{key}", f"{sid}_ctlfwd_{unit}_{key}")
                d2[f"{key}_{unit}"] = {
                    "strategy": fmt(interval(acc, f"{sid}_fwd_{unit}_{key}"), 4),
                    "control": fmt(interval(acc, f"{sid}_ctlfwd_{unit}_{key}"), 4),
                    "diff": {**fmt(diff, 4), "material": diff.material(thr)},
                }
        out["dx2"][sid] = d2
    names = (
        "optimistic_collision",
        "no_stop_slippage",
        "hold_6_bars",
        "hold_12_bars",
        "hold_to_session_exit",
    )
    for kind in ("gross", "net"):
        for name in names:
            diff = interval(acc, f"dx5_{name}_{kind}", f"s01_common_{kind}")
            out["dx5"][f"{name}_{kind}"] = {
                "mean": fmt(interval(acc, f"dx5_{name}_{kind}")),
                "vs_common_exit": {**fmt(diff), "material": diff.material(0.05)},
            }
    out["dx7"] = {
        "sample": len(spot_results),
        "agree": sum(1 for r in spot_results if not r["mismatches"]),
        "results": spot_results,
    }
    return out


def render(res: dict[str, Any]) -> str:
    L: list[str] = ["Framework diagnosis, in-sample (aggregates; hypothetical, simulated results)", ""]
    L.append(f"Counts: {json.dumps(res['counts'], sort_keys=True)}")
    L += [
        "",
        "DX-1 drift (% per instrument-session, buy 09:30 open or random bar, sell 15:15 open, no costs)",
    ]
    for k, v in res["dx1"].items():
        if k != "by_month_open":
            L.append(f"  {k}: {v}")
    L.append(
        "  by month (open): " + ", ".join(f"{m} {v['est']}" for m, v in res["dx1"]["by_month_open"].items())
    )
    for sid in ("s01", "s02"):
        L += ["", f"DX-3 {sid}: R decomposition by stop distance (averages per trade, R)"]
        L.append(f"  all: {res['dx3'][sid]['all']}")
        for b, v in res["dx3"][sid]["buckets"].items():
            L.append(f"  {b}: {v}")
        L += ["", f"DX-4 {sid}: strategy vs matched random-entry controls (common 2.5R exit)"]
        for k, v in res["dx4"][sid].items():
            L.append(f"  {k}: {v}")
        L += ["", f"DX-2 {sid}: forward return, strategy vs random bars"]
        for k, v in res["dx2"][sid].items():
            L.append(
                f"  {k}: strategy {v['strategy']['est']}  control {v['control']['est']}  diff {v['diff']}"
            )
    L += ["", "DX-5 s01: exit-model variants (R, same entries)"]
    for k, v in res["dx5"].items():
        L.append(f"  {k}: mean {v['mean']['est']}  vs common exit {v['vs_common_exit']}")
    L += ["", f"DX-7 spot check: {res['dx7']['agree']}/{res['dx7']['sample']} trades agree"]
    for r in res["dx7"]["results"]:
        L.append(f"  {r['symbol']} {r['fill_at']} {r['reason']}: {r['mismatches'] or 'ok'}")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--s01", required=True, type=Path)
    p.add_argument("--s02", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--code", default="NIFTY50")
    p.add_argument("--members-on", type=date.fromisoformat, default=date(2026, 11, 19))
    p.add_argument("--ruleset", default="pa-intraday@0.4.0")
    p.add_argument(
        "--symbols", type=int, help="smoke test: only the first N symbols (results not meaningful)"
    )
    a = p.parse_args(argv)
    s = get_settings()
    if not s.ingest_data_source_id:
        print("Set INGEST_DATA_SOURCE_ID.", file=sys.stderr)
        return 2
    source = uuid.UUID(s.ingest_data_source_id)
    refusal = legacy_refusal(None, a.ruleset)
    if refusal:
        print(refusal, file=sys.stderr)
        return 2
    code, version = a.ruleset.split("@")
    rules = rules_from(load_ruleset(code, version))
    trades = {"s01": load_trades(a.s01), "s02": load_trades(a.s02)}
    all_days = [_day(t) for sid in trades.values() for ts in sid.values() for t in ts]
    first, last = min(all_days), max(all_days)
    s01_all = sorted(
        ((sym, t.fill_at) for sym, ts in trades["s01"].items() for t in ts), key=lambda x: (x[1], x[0])
    )
    spot = set(random.Random(1).sample(s01_all, 20))  # noqa: S311
    acc = Acc()
    spot_results: list[dict[str, Any]] = []
    engine = create_engine(s.database_url.get_secret_value())
    with engine.connect() as conn:
        members = universe_members(conn, a.code, a.members_on)
        for k, (sym, iid) in enumerate(sorted(members.items())[: a.symbols], 1):
            by_day: dict[date, list[Any]] = defaultdict(list)
            for b in load_bars(conn, source, iid, "5m", first, last):
                d = b.start.astimezone(IST).date()
                if d not in SPECIAL_SESSIONS:
                    by_day[d].append(b)
            process_symbol(sym, dict(by_day), trades, rules, acc, spot, spot_results)
            print(f"{k}/{len(members)} {sym}", flush=True)
    engine.dispose()
    res = summarise(acc, spot_results)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "diagnostics.json").write_text(json.dumps(res, indent=2, default=str))
    text = render(res)
    (a.out / "diagnostics.txt").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
