"""Human-readable and JSON-able backtest reports (TRD-06 §2 BT-06, §10, §11)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.backtest.metrics import GroupStats, Metrics
from app.backtest.run import BacktestResult

DISCLAIMER = "Hypothetical, simulated results. Past performance does not indicate future results."
UNVERIFIED_COSTS = (
    "Cost schedule and slippage are UNVERIFIED assumptions (OQ-BT-02); slippage is never measured."
)


def _d(v: Decimal | None, places: int = 2) -> str:
    return "n/a" if v is None else f"{v:.{places}f}"


def _pct(v: Decimal | None, places: int = 1) -> str:
    return "n/a" if v is None else f"{v * 100:.{places}f}%"


MEASURED_NET = "NOT AVAILABLE (no actual execution data exists; measured slippage has not been taken)"


def performance_basis(r: BacktestResult) -> dict[str, Any]:
    """Gross, estimated net and measured net as three distinct figures (D-4), mean R per trade.

    - `gross_before_slippage_r`: before assumed slippage and before charges.
    - `gross_after_slippage_r`: after assumed slippage, before charges (`Metrics.avg_r_gross`).
    - `estimated_net_r`: after assumed slippage and the charge schedule. An estimate.
    - `measured_net`: never computed here; it needs real fills.
    Trades cut off by the end of the data are excluded, as in the metrics.
    """
    ts = [t for t in r.trades if not t.end_of_data]
    n = len(ts)
    before: Decimal | None = None
    if n and all(hasattr(t, "slippage_cost") for t in ts):
        before = sum(((t.gross_pnl + t.slippage_cost) / t.risk_amount for t in ts), Decimal(0)) / n
    return {
        "trades": n,
        "slippage_model": r.record.slippage,
        "slippage_basis": "ASSUMED, not measured",
        "gross_before_slippage_r": None if before is None else str(before),
        "gross_after_slippage_r": None if r.metrics.avg_r_gross is None else str(r.metrics.avg_r_gross),
        "estimated_net_r": None if r.metrics.avg_r_net is None else str(r.metrics.avg_r_net),
        "estimated_net_pnl": str(sum((t.net_pnl for t in ts), Decimal(0))),
        "measured_net": MEASURED_NET,
    }


def sensitivity_table(rows: list[BacktestResult]) -> str:
    """One line per slippage model run on the same inputs (D-4 sensitivity testing)."""
    head = (
        f"{'slippage model':<30}{'trades':>7}{'gross R':>9}{'after slip':>11}"
        f"{'est. net R':>11}{'est. net ₹':>12}"
    )
    out = ["Slippage sensitivity (assumptions, not measurements; same trades inputs and rules):", head]
    for r in rows:
        b = performance_basis(r)
        rec = r.record.slippage
        label = f"{rec.get('id', '?')} {rec.get('entry', '')}/{rec.get('stop', '')}/{rec.get('target', '')}"
        pnl = Decimal(b["estimated_net_pnl"])
        out.append(
            f"{label:<30}{b['trades']:>7}{_d(_dec(b['gross_before_slippage_r'])):>9}"
            f"{_d(_dec(b['gross_after_slippage_r'])):>11}{_d(_dec(b['estimated_net_r'])):>11}{_d(pnl, 0):>12}"
        )
    return "\n".join(out)


def _dec(v: str | None) -> Decimal | None:
    return None if v is None else Decimal(v)


def _group_lines(title: str, groups: dict[str, GroupStats]) -> list[str]:
    if not groups:
        return []
    out = ["", title, f"  {'':<26}{'trades':>7}{'win':>8}{'avg R':>8}{'net ₹':>12}"]
    for k, g in groups.items():
        out.append(
            f"  {k:<26}{g.trades:>7}{_pct(g.win_rate, 0):>8}{_d(g.avg_r_net):>8}{_d(g.net_pnl, 0):>12}"
        )
    return out


def format_report(r: BacktestResult) -> str:
    m: Metrics = r.metrics
    rec = r.record
    lines = [
        f"Backtest {rec.ruleset} [{rec.ruleset_hash[:12]}] | {rec.universe} | {rec.data_source}"
        f" | {rec.first_session} .. {rec.last_session} ({rec.sessions} sessions)",
        f"engine {rec.engine_version} | costs {rec.cost_schedule_version} | sizing {rec.sizing_mode}"
        f" | inputs {rec.inputs_hash[:12]}",
        "",
        DISCLAIMER,
        UNVERIFIED_COSTS,
    ]
    if rec.strategy_id:
        lines.insert(
            1, f"strategy {rec.strategy_id} | experiment {rec.experiment} (single-strategy run mode)"
        )
    if r.flags:
        lines.append("Flags: " + ", ".join(r.flags))
    if m.low_sample:
        lines.append("LOW SAMPLE: fewer than 30 trades or 60 sessions; do not read much into these numbers.")
    b = performance_basis(r)
    sm = rec.slippage
    desc = (
        "legacy model (before D-4)"
        if not sm
        else ", ".join(f"{k} {sm[k]}%" for k in ("entry", "stop", "target", "session_end", "structure"))
    )
    lines += [
        "",
        f"Slippage model {sm.get('id', 'n/a')}: {desc}. ASSUMED, not measured real-world slippage.",
        f"Mean R per trade: gross before slippage {_d(_dec(b['gross_before_slippage_r']))}"
        f" | after slippage, before charges {_d(_dec(b['gross_after_slippage_r']))}"
        f" | estimated net {_d(_dec(b['estimated_net_r']))} | measured net {MEASURED_NET}",
    ]
    lines += [
        "",
        f"Trades {m.trades}  (end-of-data trades excluded: {m.end_of_data_trades})",
        f"Win rate {_pct(m.win_rate)}   Avg R net {_d(m.avg_r_net)}   Avg R gross {_d(m.avg_r_gross)}"
        f"   Profit factor {_d(m.profit_factor)}",
        f"Max drawdown ₹{_d(m.max_drawdown, 0)} ({_d(m.max_drawdown_pct)}%)"
        f"   Sharpe (daily) {_d(m.sharpe_daily)}",
        f"Session P&L: mean ₹{_d(m.mean_session_pnl, 0)}  median ₹{_d(m.median_session_pnl, 0)}"
        f"  worst ₹{_d(m.worst_session_pnl, 0)}",
        f"Sessions blocked by account limits {_d(m.sessions_account_blocked_pct, 1)}%"
        f"   Exposure {_pct(m.exposure_pct)}   Avg time in trade {_d(m.avg_minutes_in_trade, 0)} min",
        f"Cost drag {_pct(m.cost_drag)} of gross P&L",
        "Exit mix: " + (", ".join(f"{k} {v}" for k, v in m.exit_mix.items()) or "none"),
        "Skips: " + (", ".join(f"{k} {v}" for k, v in m.skips.items()) or "none"),
    ]
    lines += _group_lines("By setup", m.by_setup)
    lines += _group_lines("By anchor", m.by_anchor)
    lines += _group_lines("By half hour (IST)", m.by_half_hour)
    lines += _group_lines("By 15m context", m.by_context_15m)
    lines += _group_lines("By month", m.by_month)
    return "\n".join(lines)


def _plain(v: Any) -> Any:
    """Decimals as strings, dataclasses and mappings recursively, so the result is JSON-serialisable."""
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, dict):
        return {str(k): _plain(x) for k, x in v.items()}
    if isinstance(v, list | tuple):
        return [_plain(x) for x in v]
    if hasattr(v, "__dataclass_fields__"):
        return {k: _plain(getattr(v, k)) for k in v.__dataclass_fields__}
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def report_dict(r: BacktestResult) -> dict[str, Any]:
    """Run record, flags, metrics, equity curve and every trade (skips are counted in the metrics)."""
    return {
        "disclaimer": DISCLAIMER,
        "warnings": [UNVERIFIED_COSTS],
        "record": _plain(r.record),
        "flags": list(r.flags),
        "performance_basis": performance_basis(r),
        "metrics": _plain(r.metrics),
        "equity_curve": _plain(r.equity_curve),
        "trades": [_plain(t) for t in r.trades],
    }
