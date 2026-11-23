"""Daily screening runner (T-I147, docs/research/daily-screening-protocol.md). Run from `python-engine/`:

  uv run python scripts/run_daily_screen.py --out DIR [--members-on 2026-11-19]

One automatic pass, exactly as pre-registered: screen the 8 variants of ideas 1 to 4 on the first half of the
in-sample segment (2015 to mid 2018) against month-matched random-entry controls; promote by the protocol's
rule; confirm only the promoted variants on the second half at slippage 0%, 0.05% and 0.10%. Prices are loaded
only up to the last in-sample date (computed from session dates); out-of-sample and holdout are never read.
Writes `daily_screen.json` and `daily_screen.txt` (aggregates) to `--out`. The Gate 0 data findings (special
sessions, one dropped bar, three series cuts) are always applied. Hypothetical, simulated results
(TRD-06 BT-06).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `app` importable when run as a script

from app.backtest.costs import DeliverySchedule
from app.backtest.diagnostics.daily import (
    DailyRules,
    DailyTrade,
    DayBar,
    draw_baseline,
    in_sample_last_date,
    month_key,
    month_pool,
    run_daily,
    segment_at,
)
from app.backtest.diagnostics.daily_data import (
    DAILY_SPECIAL_SESSIONS,
    KNOWN_BREAKS,
    KNOWN_DROPS,
    load_calendar,
    load_day_bars,
)
from app.backtest.diagnostics.daily_screen import (
    FAMILY,
    HOLD,
    Signal,
    Variant,
    detect,
    passes_stop_range,
)
from app.backtest.diagnostics.screen import CONFIRM_LEVEL, PROMOTE_LEVEL, confirmed, promoted, session_halves
from app.backtest.diagnostics.stats import Sums, add, bootstrap_mean
from app.ingestion.universe import universe_members
from app.settings import get_settings

D = Decimal
SEEDS = (1, 2, 3, 4, 5)
SCHED = DeliverySchedule()
PRIMARY = D("0.05")
SLIPPAGES = (D("0.00"), D("0.05"), D("0.10"))
METRICS = ("gross_planned", "net_planned", "gross_fill", "net_fill")
Vals = tuple[float, float, float, float]  # gross and net, planned-risk basis then fill-risk basis


@dataclass(slots=True)
class Row:
    variant: str
    day: date  # the trade's fill session
    strat: Vals
    controls: list[Vals] = field(default_factory=list)
    redraws: int = 0
    missing: int = 0
    alt: Vals | None = None  # the same entry under the candle exit (exit study only)


def vals(t: DailyTrade) -> Vals:
    return float(t.r_gross_planned), float(t.r_net_planned), float(t.r_gross), float(t.r_net)


def sums_of(rows: list[Row], col: int, which: str) -> Sums:
    out: dict[Any, tuple[float, int]] = {}
    for r in rows:
        if which == "strat":
            add(out, month_key(r.day), r.strat[col])
        else:
            for c in r.controls:
                add(out, month_key(r.day), c[col])
    return out


def fmt(i: Any, nd: int = 4) -> dict[str, Any]:
    return {"est": round(i.estimate, nd), "lo": round(i.low, nd), "hi": round(i.high, nd), "n": i.n}


def stats(rows: list[Row], level: float) -> dict[str, Any]:
    out: dict[str, Any] = {
        "trades": len(rows),
        "controls": sum(len(r.controls) for r in rows),
        "redraws": sum(r.redraws for r in rows),
        "controls_missing": sum(r.missing for r in rows),
    }
    if not rows:
        return out
    for col, name in enumerate(METRICS):
        s, c = sums_of(rows, col, "strat"), sums_of(rows, col, "ctl")
        diff = bootstrap_mean(s, c, level=level)
        out[name] = {
            "strategy": round(bootstrap_mean(s, resamples=1).estimate, 4),
            "control": round(bootstrap_mean(c, resamples=1).estimate, 4),
            "edge": fmt(diff),
        }
    return out


def run_variant_on_series(
    v: Variant,
    sym: str,
    series: list[DayBar],
    seg: tuple[date, date],
    rules: DailyRules,
    counts: dict[str, int],
) -> list[Row]:
    """Trades of one variant on one stock series inside the segment (history before it is only lookback)."""
    bars = [b for b in series if b.day <= seg[1]]
    if len(bars) <= HOLD + 1:
        return []
    return trades_from_signals(v.vid, sym, bars, detect(v, bars), seg, rules, counts)


def trades_from_signals(
    vid: str,
    sym: str,
    bars: list[DayBar],
    signals: list[Signal],
    seg: tuple[date, date],
    rules: DailyRules,
    counts: dict[str, int],
    with_alt: bool = False,
) -> list[Row]:
    """Filter, fill and match `signals` (computed on `bars`, which end at the segment end). With `with_alt`
    each trade is also simulated with the candle exit (same fill), for the exit study."""
    day_idx = {b.day: k for k, b in enumerate(bars)}
    pools: dict[tuple[int, int], list[int]] = {}
    rows: list[Row] = []
    open_until = -1  # the exit session of the open trade
    for sig in signals:
        s = sig.index
        if bars[s].day < seg[0] or s > len(bars) - 1 - HOLD:
            continue  # outside the segment, or the holding window would leave it
        counts[f"{vid}_signals"] += 1
        if not passes_stop_range(sig):
            counts[f"{vid}_stop_filtered"] += 1
            continue
        if s < open_until:
            counts[f"{vid}_skipped_open"] += 1
            continue
        t = run_daily(bars, s, sym, sig.ref, sig.stop, None, HOLD, rules, SCHED)
        if t is None:
            counts[f"{vid}_fill_skipped"] += 1
            continue
        open_until = day_idx[t.exit_day]
        row = Row(vid, t.fill_day, vals(t))
        if with_alt:
            alt = run_daily(bars, s, sym, sig.ref, sig.stop, None, HOLD, rules, SCHED, candle_exit=True)
            row.alt = vals(alt) if alt is not None else None
        month = month_key(bars[s].day)
        if month not in pools:
            pools[month] = [i for i in month_pool(bars, HOLD, month) if bars[i].day >= seg[0]]
        for seed in SEEDS:
            key = f"{seed}|{vid}|{sym}|{bars[s].day}|{s}"
            c, rd = draw_baseline(bars, sym, month, sig.stop_pct, None, HOLD, key, rules, SCHED, pools[month])
            row.redraws += rd
            if c is None:
                row.missing += 1
            else:
                row.controls.append(vals(c))
        rows.append(row)
    counts[f"{vid}_trades"] += len(rows)
    return rows


def run_pass(
    series_by: dict[str, list[list[DayBar]]],
    variants: list[Variant],
    seg: tuple[date, date],
    rules: DailyRules,
) -> tuple[list[Row], dict[str, int]]:
    counts: dict[str, int] = defaultdict(int)
    rows: list[Row] = []
    for sym, series_list in sorted(series_by.items()):
        for series in series_list:
            for v in variants:
                rows += run_variant_on_series(v, sym, series, seg, rules, counts)
    return rows, dict(counts)


def by_variant(rows: list[Row]) -> dict[str, list[Row]]:
    out: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        out[r.variant].append(r)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--code", default="NIFTY50")
    p.add_argument("--members-on", type=date.fromisoformat, default=date(2026, 11, 19))
    p.add_argument("--smoke", type=int, help="smoke test: only the first N symbols (results not meaningful)")
    a = p.parse_args(argv)
    s = get_settings()
    if not s.ingest_data_source_id:
        print("Set INGEST_DATA_SOURCE_ID.", file=sys.stderr)
        return 2
    source = uuid.UUID(s.ingest_data_source_id)
    skip = set(DAILY_SPECIAL_SESSIONS)
    drop: dict[str, set[date]] = defaultdict(set)
    breaks: dict[str, list[date]] = defaultdict(list)
    for sym, day in KNOWN_DROPS:
        drop[sym].add(day)
    for sym, day in KNOWN_BREAKS:
        breaks[sym].append(day)
    engine = create_engine(s.database_url.get_secret_value())
    with engine.connect() as conn:
        members = universe_members(conn, a.code, a.members_on)
        calendar = load_calendar(conn, source, list(members.values()), skip)
        in_last = in_sample_last_date(calendar)
        in_cal = [d for d in calendar if d <= in_last]
        half = (len(in_cal) + 1) // 2
        screen = (in_cal[0], in_cal[half - 1])
        confirm = (in_cal[half], in_cal[-1])
        print(f"in-sample {in_cal[0]}..{in_last}; screen {screen}; confirm {confirm}", flush=True)
        names = sorted(members)[: a.smoke] if a.smoke else sorted(members)
        series_by: dict[str, list[list[DayBar]]] = {}
        for n in names:
            bars = load_day_bars(conn, source, members[n], in_last, drop[n] | skip)
            series_by[n] = segment_at(bars, breaks.get(n, []))
    engine.dispose()
    assert all(b[-1].day <= in_last for sl in series_by.values() for b in sl), "a bar past the in-sample end"
    result: dict[str, Any] = {
        "data": {
            "in_sample": [str(in_cal[0]), str(in_last)],
            "screen": [str(screen[0]), str(screen[1])],
            "confirm": [str(confirm[0]), str(confirm[1])],
            "stocks": len(series_by),
            "family_size": len(FAMILY),
        },
        "screen": {},
        "confirm": {},
        "promoted": [],
    }
    print("Screen", flush=True)
    rows, counts = run_pass(series_by, list(FAMILY), screen, DailyRules(slippage_pct=PRIMARY))
    result["screen_counts"] = counts
    groups = by_variant(rows)
    promo: list[Variant] = []
    for v in FAMILY:
        st = stats(groups.get(v.vid, []), PROMOTE_LEVEL)
        ok = "gross_planned" in st and promoted(
            st["trades"], st["gross_planned"]["strategy"], st["gross_planned"]["edge"]["est"],
            st["gross_planned"]["edge"]["lo"],
        )  # fmt: skip
        st["promoted"] = ok
        result["screen"][v.vid] = st
        if ok:
            promo.append(v)
    result["promoted"] = [v.vid for v in promo]
    print(f"Promoted: {result['promoted']}", flush=True)
    if promo:
        first_half, second_half = session_halves([d for d in in_cal if confirm[0] <= d <= confirm[1]])
        for slip in SLIPPAGES:
            print(f"Confirm, slippage {slip}%", flush=True)
            crows, ccounts = run_pass(series_by, promo, confirm, DailyRules(slippage_pct=slip))
            cg = by_variant(crows)
            for v in promo:
                st = stats(cg.get(v.vid, []), CONFIRM_LEVEL)
                e = result["confirm"].setdefault(v.vid, {"by_slippage": {}})
                e["by_slippage"][str(slip)] = st
                if slip == PRIMARY and "gross_planned" in st:
                    halves = [
                        stats([r for r in cg[v.vid] if r.day in h], CONFIRM_LEVEL)
                        for h in (first_half, second_half)
                    ]
                    hd = [h["gross_planned"]["edge"]["est"] if "gross_planned" in h else 0.0 for h in halves]
                    ge = st["gross_planned"]["edge"]
                    e["half_edges"] = hd
                    e["confirmed"] = confirmed(st["trades"], ge["est"], ge["lo"], hd)
                    e["counts"] = {k: c for k, c in ccounts.items() if k.startswith(v.vid)}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "daily_screen.json").write_text(json.dumps(result, indent=2, default=str))
    text = render(result)
    (a.out / "daily_screen.txt").write_text(text)
    print(text)
    return 0


def line(vid: str, st: dict[str, Any]) -> str:
    if "gross_planned" not in st:
        return f"{vid} | {st['trades']} | no trades"
    g, n = st["gross_planned"], st["net_planned"]
    ga, na = st["gross_fill"], st["net_fill"]
    return (
        f"{vid} | {st['trades']} | gross {g['strategy']} / ctl {g['control']} / edge {g['edge']['est']} "
        f"[{g['edge']['lo']}, {g['edge']['hi']}] | net {n['strategy']} / ctl {n['control']} / edge "
        f"{n['edge']['est']} | fill-risk gross {ga['strategy']} net {na['strategy']}"
    )


def render(r: dict[str, Any]) -> str:
    d = r["data"]
    L = ["Daily screening (aggregates; hypothetical, simulated results)", ""]
    L.append(
        f"In-sample {d['in_sample']}; screen {d['screen']}; confirm {d['confirm']}; {d['stocks']} stocks"
    )
    L += ["", "Screen (planned-risk R; 99% interval on the gross edge)"]
    L += [line(v, st) + f" | promoted {st.get('promoted')}" for v, st in r["screen"].items()]
    L += ["", f"Promoted: {r['promoted']}", ""]
    for vid, e in r["confirm"].items():
        L.append(f"Confirm {vid}: confirmed={e.get('confirmed')} half edges={e.get('half_edges')}")
        for slip, st in e["by_slippage"].items():
            L.append(f"  slippage {slip}%: {line(vid, st)}")
    L += ["", f"Counts: {json.dumps(r['screen_counts'], sort_keys=True)}"]
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
