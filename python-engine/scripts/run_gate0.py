"""Gate 0 runner (T-I146, docs/research/gate0-daily-diagnosis-plan.md). Run from `python-engine/`:

  uv run python scripts/run_gate0.py --out DIR [--members-on 2026-11-19] [--exclude FILE.json]

Reads the stored daily (1D) bars of the universe, computes the in-sample segment from the session **dates**
alone (first 60%), loads prices only up to its last date, and runs DG-0 (data audit), DG-1 (drift), DG-2
(friction), DG-3 (random-entry baseline grid), DG-4 (spot check), DG-5 (survivorship sensitivity) and DG-6
(charges sensitivity). Out-of-sample and holdout prices are never loaded. Writes `gate0.json` and
`gate0.txt` (aggregates, plus the DG-0 anomaly list) to `--out`. Hypothetical, simulated results
(TRD-06 BT-06).
The daily bars must come from one backfill run (the data version, plan section 3).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, create_engine, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `app` importable when run as a script

from app.backtest.costs import DeliverySchedule, delivery_costs
from app.backtest.diagnostics.daily import (
    POSITION_CAP,
    RISK_UNIT,
    DailyRules,
    DailyTrade,
    DayBar,
    draw_baseline,
    drift_returns,
    gap_flags,
    in_sample_last_date,
    missing_sessions,
    month_key,
    month_pool,
    ohlc_defects,
    segment_at,
    verify_daily_trade,
)
from app.backtest.diagnostics.stats import add, bootstrap_mean
from app.backtest.exclusions import SPECIAL_SESSIONS
from app.db.tables import candles
from app.ingestion.universe import universe_members
from app.settings import get_settings

D = Decimal
SEEDS = (1, 2, 3, 4, 5)
STOPS = (D(2), D(3), D(5), D(8))
TARGETS: tuple[Decimal | None, ...] = (None, D("2.5"), D(4))
HOLDS = (10, 20)
DRIFT_HOLDS = (5, 10, 20)
SLIPPAGES = (D("0.00"), D("0.05"), D("0.10"))
PRIMARY = D("0.05")
SCHED = DeliverySchedule()
VARIANTS: dict[str, DeliverySchedule] = {
    "exchange_0.00297": DeliverySchedule(exchange_pct=D("0.00297")),
    "brokerage_cap_0": DeliverySchedule(brokerage_cap=D(0)),
    "brokerage_cap_40": DeliverySchedule(brokerage_cap=D(40)),
}
FRICTION_STOPS = (D(2), D(3), D(4), D(5), D(8))
# Sessions that exist for only one or two stocks (Budget Saturday, Diwali Muhurat); found by DG-0, run 1.
DAILY_SPECIAL_SESSIONS: dict[date, str] = {
    date(2015, 2, 28): "SPECIAL_SESSION_BUDGET_SATURDAY",
    date(2016, 10, 30): "SPECIAL_SESSION_MUHURAT",
    date(2017, 10, 19): "SPECIAL_SESSION_MUHURAT",
    date(2018, 11, 7): "SPECIAL_SESSION_MUHURAT",
}
# DG-0 findings, run 1 (each checked against public records, see the Gate 0 report): provider data for these
# corporate actions is not adjusted, so the series is cut there; one bar has an unadjusted open (dropped).
KNOWN_DROPS: tuple[tuple[str, date], ...] = (("ADANIENT", date(2015, 6, 3)),)
KNOWN_BREAKS: tuple[tuple[str, date], ...] = (
    ("ADANIENT", date(2015, 6, 3)),  # demerger ex-date (Adani Ports, Adani Power, Adani Transmission)
    ("ADANIENT", date(2018, 9, 6)),  # Adani Gas demerger ex-date
    ("GRASIM", date(2017, 7, 19)),  # financial-services spin-off ex-date
)
FULL_HISTORY_SESSIONS = 5  # a stock is "full history" when it starts within this many sessions of the first


def cfg_id(stop: Decimal, target: Decimal | None, hold: int) -> str:
    return f"stop{stop}%/target{'none' if target is None else f'{target}R'}/hold{hold}"


def load_calendar(conn: Connection, source: uuid.UUID, ids: list[uuid.UUID], skip: set[date]) -> list[date]:
    """Session dates only (no prices), special sessions removed."""
    rows = conn.execute(
        select(candles.c.trade_date)
        .where(
            candles.c.data_source_id == source,
            candles.c.timeframe == "1D",
            candles.c.instrument_id.in_(ids),
        )
        .distinct()
    ).all()
    return sorted(
        r.trade_date for r in rows if r.trade_date not in SPECIAL_SESSIONS and r.trade_date not in skip
    )


def load_day_bars(
    conn: Connection, source: uuid.UUID, iid: uuid.UUID, last: date, drop: set[date]
) -> list[DayBar]:
    rows = conn.execute(
        select(candles.c.trade_date, candles.c.open, candles.c.high, candles.c.low, candles.c.close)
        .where(
            candles.c.data_source_id == source,
            candles.c.instrument_id == iid,
            candles.c.timeframe == "1D",
            candles.c.trade_date <= last,  # the in-sample guard: nothing later is read
        )
        .order_by(candles.c.trade_date)
    ).all()
    return [
        DayBar(r.trade_date, r.open, r.high, r.low, r.close)
        for r in rows
        if r.trade_date not in SPECIAL_SESSIONS and r.trade_date not in drop
    ]


def fmt(i: Any, nd: int = 4) -> dict[str, Any]:
    return {"est": round(i.estimate, nd), "lo": round(i.low, nd), "hi": round(i.high, nd), "n": i.n}


class Grid:
    """Per-configuration accumulators for the random-entry baseline (month-block sums)."""

    def __init__(self) -> None:
        self.sums: dict[str, dict[str, dict[Any, tuple[float, int]]]] = defaultdict(lambda: defaultdict(dict))
        self.exits: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.stop_r: dict[str, list[float]] = defaultdict(list)
        self.redraws: dict[str, int] = defaultdict(int)
        self.missing: dict[str, int] = defaultdict(int)
        self.near_stop: dict[str, int] = defaultdict(int)  # fills inside half the planned stop distance


def run_grid(
    bars_by: dict[str, list[DayBar]],
    full: set[str],
    slip: Decimal,
    primary: bool,
    seed1_trades: list[tuple[str, DailyTrade]],
) -> Grid:
    g = Grid()
    rules = DailyRules(slippage_pct=slip)
    for sym, bars in sorted(bars_by.items()):
        months = sorted({month_key(b.day) for b in bars})
        pools = {(m, h): month_pool(bars, h, m) for m in months for h in HOLDS}
        for month in months:
            for stop in STOPS:
                for target in TARGETS:
                    for hold in HOLDS:
                        cid = cfg_id(stop, target, hold)
                        for seed in SEEDS:
                            key = f"{seed}|{sym}|{month[0]}-{month[1]}|{cid}"
                            t, rd = draw_baseline(
                                bars, sym, month, stop, target, hold, key, rules, SCHED, pools[(month, hold)]
                            )
                            g.redraws[cid] += rd
                            if t is None:
                                g.missing[cid] += 1
                                continue
                            mk = month_key(t.fill_day)
                            gross, net = float(t.r_gross), float(t.r_net)
                            add(g.sums[cid]["gross"], mk, gross)
                            add(g.sums[cid]["net"], mk, net)
                            add(g.sums[cid]["gross_p"], mk, float(t.r_gross_planned))
                            add(g.sums[cid]["net_p"], mk, float(t.r_net_planned))
                            if t.entry - t.stop < (t.ref - t.stop) / 2:
                                g.near_stop[cid] += 1
                            if not primary:
                                continue
                            if sym.split("#")[0] in full:
                                add(g.sums[cid]["gross_full"], mk, gross)
                                add(g.sums[cid]["net_full"], mk, net)
                            for name, sch in VARIANTS.items():
                                c = delivery_costs(t.entry * t.qty, t.exit * t.qty, sch).total
                                add(g.sums[cid][f"net_{name}"], mk, float((t.gross_pnl - c) / t.risk))
                            g.exits[cid][t.reason] += 1
                            if t.reason in ("STOP", "STOP_GAP", "STOP_COLLISION"):
                                g.stop_r[cid].append(gross)
                            if seed == 1:
                                seed1_trades.append((sym, t))
    return g


def friction_table() -> list[dict[str, Any]]:
    out = []
    for stop in FRICTION_STOPS:
        pos = min(POSITION_CAP, RISK_UNIT / (stop / 100))
        charges = delivery_costs(pos, pos, SCHED).total
        slip = pos * PRIMARY / 100 * 2
        out.append(
            {
                "stop_pct": float(stop),
                "position": round(float(pos)),
                "charges": round(float(charges)),
                "slippage": round(float(slip)),
                "friction_r": round(float((charges + slip) / RISK_UNIT), 3),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--code", default="NIFTY50")
    p.add_argument("--members-on", type=date.fromisoformat, default=date(2026, 11, 19))
    p.add_argument(
        "--exclude", type=Path, help='JSON list of ["SYMBOL", "YYYY-MM-DD"] stock-sessions to drop'
    )
    p.add_argument(
        "--known-events",
        action="store_true",
        help="apply the DG-0 run-1 findings: drop the daily special sessions and one defective bar, and cut "
        "the series at the unadjusted corporate actions (KNOWN_DROPS, KNOWN_BREAKS)",
    )
    p.add_argument("--smoke", type=int, help="smoke test: only the first N symbols (results not meaningful)")
    a = p.parse_args(argv)
    s = get_settings()
    if not s.ingest_data_source_id:
        print("Set INGEST_DATA_SOURCE_ID.", file=sys.stderr)
        return 2
    source = uuid.UUID(s.ingest_data_source_id)
    drop: dict[str, set[date]] = defaultdict(set)
    if a.exclude:
        for sym, day in json.loads(a.exclude.read_text()):
            drop[sym].add(date.fromisoformat(day))
    skip: set[date] = set(DAILY_SPECIAL_SESSIONS) if a.known_events else set()
    breaks: dict[str, list[date]] = defaultdict(list)
    if a.known_events:
        for sym, day in KNOWN_DROPS:
            drop[sym].add(day)
        for sym, day in KNOWN_BREAKS:
            breaks[sym].append(day)
    engine = create_engine(s.database_url.get_secret_value())
    with engine.connect() as conn:
        members = universe_members(conn, a.code, a.members_on)
        calendar = load_calendar(conn, source, list(members.values()), skip)
        in_last = in_sample_last_date(calendar)
        print(f"{len(calendar)} sessions {calendar[0]}..{calendar[-1]}; in-sample ends {in_last}", flush=True)
        names = sorted(members)[: a.smoke] if a.smoke else sorted(members)
        bars_by = {n: load_day_bars(conn, source, members[n], in_last, drop[n] | skip) for n in names}
    engine.dispose()
    assert all(b[-1].day <= in_last for b in bars_by.values() if b), "a bar past the in-sample end was loaded"
    in_cal = [d for d in calendar if d <= in_last]
    result: dict[str, Any] = {
        "data": {"sessions_total": len(calendar), "first": str(calendar[0]), "last": str(calendar[-1])}
    }
    result["data"]["in_sample_last"] = str(in_last)
    result["data"]["in_sample_sessions"] = len(in_cal)
    result["data"]["short_history"] = len(calendar) < 1250
    result["data"]["known_events_applied"] = a.known_events
    if a.known_events:
        result["data"]["special_sessions_dropped"] = {str(k): v for k, v in DAILY_SPECIAL_SESSIONS.items()}
        result["data"]["bars_dropped"] = [f"{sy} {dy}" for sy, dy in KNOWN_DROPS]
        result["data"]["series_cut_at"] = [f"{sy} {dy}" for sy, dy in KNOWN_BREAKS]
    # DG-0 data audit
    first_dates = {n: b[0].day for n, b in bars_by.items() if b}
    cutoff = in_cal[min(FULL_HISTORY_SESSIONS, len(in_cal) - 1)]
    full = {n for n, d in first_dates.items() if d <= cutoff}
    dg0: dict[str, Any] = {
        "stocks": len(bars_by),
        "full_history_stocks": len(full),
        "per_stock": {},
        "flags": [],
    }
    for n, b in bars_by.items():
        days = [x.day for x in b]
        d = ohlc_defects(b)
        gf = gap_flags(b)
        miss = missing_sessions(in_cal, days)
        dg0["per_stock"][n] = {
            "first": str(days[0]) if days else None,
            "last": str(days[-1]) if days else None,
            "sessions": len(days),
            "missing_sessions": len(miss),
            "ohlc_defects": len(d),
            "gap_flags": len(gf),
        }
        dg0["flags"] += [{"symbol": n, "day": str(x), "gap": round(g, 4), "why": w} for x, g, w in gf]
        dg0["flags"] += [{"symbol": n, "day": str(x), "gap": None, "why": w} for x, w in d]
    result["dg0"] = dg0
    # series used by DG-1, DG-3 and DG-4: cut at the unadjusted corporate actions
    series: dict[str, list[DayBar]] = {}
    for n, b in bars_by.items():
        for k, seg in enumerate(segment_at(b, breaks.get(n, []))):
            series[n if k == 0 else f"{n}#{k + 1}"] = seg
    # DG-1 drift
    dg1: dict[str, Any] = {}
    for h in DRIFT_HOLDS:
        month_sums: dict[Any, tuple[float, int]] = {}
        by_year: dict[int, list[float]] = defaultdict(list)
        basket: dict[date, list[float]] = defaultdict(list)
        for b in series.values():
            for day, r in drift_returns(b, h):
                add(month_sums, month_key(day), r)
                by_year[day.year].append(r)
                basket[day].append(r)
        yearly_basket: dict[int, list[float]] = defaultdict(list)
        for day, rs in basket.items():
            yearly_basket[day.year].append(sum(rs) / len(rs))
        dg1[f"hold{h}"] = {
            "mean_pct": fmt(bootstrap_mean(month_sums), 4),
            "by_year_mean_pct": {y: round(sum(v) / len(v), 4) for y, v in sorted(by_year.items())},
            "basket_by_year_mean_pct": {
                y: round(sum(v) / len(v), 4) for y, v in sorted(yearly_basket.items())
            },
        }
    result["dg1"] = dg1
    result["dg2_table"] = friction_table()
    # DG-3 / DG-5 / DG-6
    seed1: list[tuple[str, DailyTrade]] = []
    grids: dict[str, Grid] = {}
    for slip in SLIPPAGES:
        print(f"DG-3 grid, slippage {slip}%", flush=True)
        grids[str(slip)] = run_grid(series, full, slip, slip == PRIMARY, seed1)
    prim = grids[str(PRIMARY)]
    dg3: dict[str, Any] = {}
    for stop in STOPS:
        for target in TARGETS:
            for hold in HOLDS:
                cid = cfg_id(stop, target, hold)
                sums = prim.sums[cid]
                row: dict[str, Any] = {
                    "trades": sum(c for _, c in sums["gross"].values()),
                    "gross": fmt(bootstrap_mean(sums["gross"])),
                    "net": fmt(bootstrap_mean(sums["net"])),
                    "gross_planned": fmt(bootstrap_mean(sums["gross_p"])),
                    "net_planned": fmt(bootstrap_mean(sums["net_p"])),
                    "near_stop_fills": prim.near_stop[cid],
                    "exits": dict(prim.exits[cid]),
                    "avg_stop_out_r": round(sum(prim.stop_r[cid]) / len(prim.stop_r[cid]), 3)
                    if prim.stop_r[cid]
                    else None,
                    "redraws": prim.redraws[cid],
                    "unfilled_draws": prim.missing[cid],
                    "slippage_sensitivity": {
                        str(sl): {
                            "gross": fmt(bootstrap_mean(grids[str(sl)].sums[cid]["gross"])),
                            "net": fmt(bootstrap_mean(grids[str(sl)].sums[cid]["net"])),
                            "gross_planned": fmt(bootstrap_mean(grids[str(sl)].sums[cid]["gross_p"])),
                            "net_planned": fmt(bootstrap_mean(grids[str(sl)].sums[cid]["net_p"])),
                        }
                        for sl in SLIPPAGES
                        if sl != PRIMARY
                    },
                    "charges_sensitivity_net": {
                        name: round(bootstrap_mean(sums[f"net_{name}"], resamples=1).estimate, 4)
                        for name in VARIANTS
                    },
                }
                if sums.get("net_full"):
                    d_net = bootstrap_mean(sums["net_full"], sums["net"])
                    row["dg5_full_history_minus_all_net"] = fmt(d_net)
                dg3[cid] = row
    result["dg3"] = dg3
    # DG-4 spot check: 20 seed-1 trades, five of them overnight gap exits when available
    rng = random.Random(1)  # noqa: S311
    gaps = [x for x in seed1 if x[1].reason == "STOP_GAP"]
    others = [x for x in seed1 if x[1].reason != "STOP_GAP"]
    picks = rng.sample(gaps, min(5, len(gaps))) + rng.sample(others, min(20 - min(5, len(gaps)), len(others)))
    checks = []
    for sym, t in picks:
        mism = verify_daily_trade(series[sym], t, PRIMARY)
        checks.append({"symbol": sym, "fill_day": str(t.fill_day), "reason": t.reason, "mismatches": mism})
    result["dg4"] = {
        "sample": len(checks),
        "agree": sum(1 for c in checks if not c["mismatches"]),
        "gap_exits_in_sample": len(gaps),
        "results": checks,
    }
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "gate0.json").write_text(json.dumps(result, indent=2, default=str))
    text = render(result)
    (a.out / "gate0.txt").write_text(text)
    print(text)
    return 0


def render(r: dict[str, Any]) -> str:
    L = ["Gate 0, daily framework diagnosis, in-sample (aggregates; hypothetical, simulated results)", ""]
    d = r["data"]
    L.append(
        f"Data: {d['sessions_total']} sessions {d['first']}..{d['last']}; "
        f"in-sample {d['in_sample_sessions']} sessions to {d['in_sample_last']}; "
        f"short_history={d['short_history']}"
    )
    g0 = r["dg0"]
    L.append("")
    L.append(
        f"DG-0: {g0['stocks']} stocks, {g0['full_history_stocks']} full-history; flags {len(g0['flags'])}"
    )
    L += [f"  {f['symbol']} {f['day']} {f['gap']} {f['why']}" for f in g0["flags"][:60]]
    L += ["", "DG-1 drift (% per hold, gross, no costs)"]
    for k, v in r["dg1"].items():
        L.append(
            f"  {k}: {v['mean_pct']} by year {v['by_year_mean_pct']} basket {v['basket_by_year_mean_pct']}"
        )
    L += ["", "DG-2 friction (delivery charges + slippage, in R)"]
    L += [f"  {x}" for x in r["dg2_table"]]
    L += ["", "DG-3 random-entry baseline grid (R)"]
    for cid, v in r["dg3"].items():
        g, n = v["gross"], v["net"]
        gp, np_ = v["gross_planned"], v["net_planned"]
        L.append(
            f"  {cid}: n={v['trades']} gross {g['est']} [{g['lo']}, {g['hi']}]"
            f" net {n['est']} [{n['lo']}, {n['hi']}]"
            f" | planned-risk gross {gp['est']} net {np_['est']} [{np_['lo']}, {np_['hi']}]"
            f" near-stop fills {v['near_stop_fills']}"
            f" exits {v['exits']} stop-out R {v['avg_stop_out_r']} redraws {v['redraws']}"
            f" unfilled {v['unfilled_draws']}"
        )
    L += ["", f"DG-4 spot check: {r['dg4']['agree']}/{r['dg4']['sample']} agree"]
    L += [
        f"  {c['symbol']} {c['fill_day']} {c['reason']}: {c['mismatches'] or 'ok'}"
        for c in r["dg4"]["results"]
    ]
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
