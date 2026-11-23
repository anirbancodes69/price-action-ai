"""Candle and volume screening runner (T-I148, docs/research/candle-volume-screening-protocol.md). Run from
`python-engine/`:

  uv run python scripts/run_candle_screen.py --out DIR [--members-on 2026-11-19]

DV-0 (volume audit), the screen of the 12 variants on the first half of the in-sample segment against
month-matched random-entry controls, mechanical promotion, confirmation of promoted variants only on the
second half (slippage 0%, 0.05%, 0.10%), and the descriptive candle-exit study. Prices and volumes are
loaded only up to the last in-sample date; out-of-sample and holdout are never read. The Gate 0 data
findings are applied.
Writes `candle_screen.json` and `candle_screen.txt` (aggregates). Hypothetical, simulated results.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `app` importable when run as a script
sys.path.insert(0, str(Path(__file__).resolve().parent))  # the shared daily screening helpers

from run_daily_screen import (
    PRIMARY,
    SLIPPAGES,
    Row,
    by_variant,
    fmt,
    stats,
    trades_from_signals,
)

from app.backtest.diagnostics.daily import DailyRules, DayBar, in_sample_last_date, month_key, segment_at
from app.backtest.diagnostics.daily_candle import (
    FAMILY,
    CVariant,
    detect_candle,
    non_comparable_sessions,
    volume_level_shifts,
)
from app.backtest.diagnostics.daily_data import (
    DAILY_SPECIAL_SESSIONS,
    KNOWN_BREAKS,
    KNOWN_DROPS,
    load_calendar,
    load_day_bars,
)
from app.backtest.diagnostics.screen import (
    CONFIRM_LEVEL,
    PROMOTE_LEVEL,
    confirmed,
    promoted,
    session_halves,
)
from app.backtest.diagnostics.stats import add, bootstrap_mean
from app.ingestion.universe import universe_members
from app.settings import get_settings

D = Decimal


def run_pass(
    series_by: dict[str, list[list[DayBar]]],
    bad_by: dict[str, list[set[int]]],
    variants: list[CVariant],
    seg: tuple[date, date],
    rules: DailyRules,
    with_alt: bool = False,
) -> tuple[list[Row], dict[str, int]]:
    counts: dict[str, int] = defaultdict(int)
    rows: list[Row] = []
    for sym, series_list in sorted(series_by.items()):
        for k, series in enumerate(series_list):
            bars = [b for b in series if b.day <= seg[1]]
            if len(bars) <= 21:
                continue
            for v in variants:
                sigs = detect_candle(v, bars, bad_by[sym][k])
                rows += trades_from_signals(v.vid, sym, bars, sigs, seg, rules, counts, with_alt)
    return rows, dict(counts)


def audit(series_by: dict[str, list[list[DayBar]]]) -> tuple[dict[str, Any], dict[str, list[set[int]]]]:
    """DV-0: split-like volume level shifts per stock, and the non-comparable sessions per series."""
    bad: dict[str, list[set[int]]] = {}
    shifts_out: dict[str, Any] = {}
    split_stocks = 0
    covered = total = 0
    for sym, series_list in sorted(series_by.items()):
        bad[sym] = []
        for series in series_list:
            sh = volume_level_shifts([b.volume for b in series])
            nc = non_comparable_sessions(sh)
            bad[sym].append(nc)
            total += len(series)
            covered += len(nc)
            if sh:
                shifts_out.setdefault(sym, []).extend(
                    {"day": str(series[d].day), "ratio": round(r, 2), "split_like": sp} for d, r, sp in sh
                )
        if any(x["split_like"] for x in shifts_out.get(sym, [])):
            split_stocks += 1
    zero = sum(1 for sl in series_by.values() for s in sl for b in s if b.volume == 0)
    return {
        "stocks_with_split_like_shift": split_stocks,
        "non_comparable_sessions": covered,
        "sessions": total,
        "zero_volume_sessions": zero,
        "shifts": shifts_out,
        "volume_variants_run": True,  # always run; split-like windows are excluded (protocol §10.1)
    }, bad


def exit_study(rows: list[Row]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for vid, rs in by_variant(rows).items():
        paired = [r for r in rs if r.alt is not None]
        if len(paired) < 100:
            continue
        res: dict[str, Any] = {"trades": len(paired)}
        for col, name in ((0, "gross_planned"), (1, "net_planned")):
            diff: dict[Any, tuple[float, int]] = {}
            base: dict[Any, tuple[float, int]] = {}
            alt: dict[Any, tuple[float, int]] = {}
            for r in paired:
                assert r.alt is not None
                add(diff, month_key(r.day), r.alt[col] - r.strat[col])
                add(base, month_key(r.day), r.strat[col])
                add(alt, month_key(r.day), r.alt[col])
            res[name] = {
                "time_stop": round(bootstrap_mean(base, resamples=1).estimate, 4),
                "candle_exit": round(bootstrap_mean(alt, resamples=1).estimate, 4),
                "difference": fmt(bootstrap_mean(diff)),
            }
        out[vid] = res
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
        screen, confirm = (in_cal[0], in_cal[half - 1]), (in_cal[half], in_cal[-1])
        names = sorted(members)[: a.smoke] if a.smoke else sorted(members)
        series_by: dict[str, list[list[DayBar]]] = {}
        for n in names:
            bars = load_day_bars(conn, source, members[n], in_last, drop[n] | skip)
            series_by[n] = segment_at(bars, breaks.get(n, []))
    engine.dispose()
    assert all(b[-1].day <= in_last for sl in series_by.values() for b in sl), "a bar past the in-sample end"
    dv0, bad_by = audit(series_by)
    print(f"DV-0: {dv0['stocks_with_split_like_shift']} stocks with a split-like volume shift", flush=True)
    variants = list(FAMILY)
    result: dict[str, Any] = {
        "data": {
            "in_sample": [str(in_cal[0]), str(in_last)],
            "screen": [str(screen[0]), str(screen[1])],
            "confirm": [str(confirm[0]), str(confirm[1])],
            "stocks": len(series_by),
            "family_size": len(FAMILY),
            "variants_run": [v.vid for v in variants],
        },
        "dv0": dv0,
        "screen": {},
        "confirm": {},
        "promoted": [],
    }
    print("Screen", flush=True)
    rows, counts = run_pass(series_by, bad_by, variants, screen, DailyRules(slippage_pct=PRIMARY), True)
    result["screen_counts"] = counts
    groups = by_variant(rows)
    promo: list[CVariant] = []
    for v in variants:
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
    result["exit_study"] = exit_study(rows)
    print(f"Promoted: {result['promoted']}", flush=True)
    if promo:
        first, second = session_halves([d for d in in_cal if confirm[0] <= d <= confirm[1]])
        for slip in SLIPPAGES:
            print(f"Confirm, slippage {slip}%", flush=True)
            crows, ccounts = run_pass(series_by, bad_by, promo, confirm, DailyRules(slippage_pct=slip))
            cg = by_variant(crows)
            for v in promo:
                st = stats(cg.get(v.vid, []), CONFIRM_LEVEL)
                e = result["confirm"].setdefault(v.vid, {"by_slippage": {}})
                e["by_slippage"][str(slip)] = st
                if slip == PRIMARY and "gross_planned" in st:
                    halves = [
                        stats([r for r in cg[v.vid] if r.day in h], CONFIRM_LEVEL) for h in (first, second)
                    ]
                    hd = [h["gross_planned"]["edge"]["est"] if "gross_planned" in h else 0.0 for h in halves]
                    ge = st["gross_planned"]["edge"]
                    e["half_edges"] = hd
                    e["confirmed"] = confirmed(st["trades"], ge["est"], ge["lo"], hd)
                    e["counts"] = {k: c for k, c in ccounts.items() if k.startswith(v.vid)}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "candle_screen.json").write_text(json.dumps(result, indent=2, default=str))
    text = render(result)
    (a.out / "candle_screen.txt").write_text(text)
    print(text)
    return 0


def line(vid: str, st: dict[str, Any]) -> str:
    if "gross_planned" not in st:
        return f"{vid} | {st['trades']} | no trades"
    g, n = st["gross_planned"], st["net_planned"]
    return (
        f"{vid} | {st['trades']} | gross {g['strategy']} / ctl {g['control']} / edge {g['edge']['est']} "
        f"[{g['edge']['lo']}, {g['edge']['hi']}] | net {n['strategy']} / ctl {n['control']}"
    )


def render(r: dict[str, Any]) -> str:
    d, v = r["data"], r["dv0"]
    L = ["Candle and volume screening (aggregates; hypothetical, simulated results)", ""]
    L.append(
        f"In-sample {d['in_sample']}; screen {d['screen']}; confirm {d['confirm']}; {d['stocks']} stocks"
    )
    L.append(
        f"DV-0: {v['stocks_with_split_like_shift']} stocks with a split-like volume shift; "
        f"{v['non_comparable_sessions']} of {v['sessions']} sessions non-comparable; zero-volume sessions "
        f"{v['zero_volume_sessions']}; volume variants run: {v['volume_variants_run']}"
    )
    L += [f"  {s}: {x}" for s, x in v["shifts"].items()]
    L += ["", "Screen (planned-risk R; 99% interval on the gross edge)"]
    L += [line(k, st) + f" | promoted {st.get('promoted')}" for k, st in r["screen"].items()]
    L += ["", f"Promoted: {r['promoted']}", ""]
    for vid, e in r["confirm"].items():
        L.append(f"Confirm {vid}: confirmed={e.get('confirmed')} half edges={e.get('half_edges')}")
        for slip, st in e["by_slippage"].items():
            L.append(f"  slippage {slip}%: {line(vid, st)}")
    L += ["", "Exit study (candle exit minus time stop, same entries, planned-risk R)"]
    for vid, e in r["exit_study"].items():
        g, n = e["gross_planned"], e["net_planned"]
        L.append(
            f"  {vid}: {e['trades']} trades; gross {g['time_stop']} -> {g['candle_exit']} "
            f"(diff {g['difference']['est']} [{g['difference']['lo']}, {g['difference']['hi']}]); "
            f"net {n['time_stop']} -> {n['candle_exit']}"
        )
    L += ["", f"Counts: {json.dumps(r['screen_counts'], sort_keys=True)}"]
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
