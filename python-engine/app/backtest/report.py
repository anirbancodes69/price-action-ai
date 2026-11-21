"""Human-readable and JSON-able backtest reports (TRD-06 §2 BT-06, §10, §11)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.backtest.metrics import GroupStats, Metrics
from app.backtest.run import BacktestResult

DISCLAIMER = "Hypothetical, simulated results. Past performance does not indicate future results."
UNVERIFIED_COSTS = "Cost schedule and slippage are UNVERIFIED assumptions (OQ-BT-02)."


def _d(v: Decimal | None, places: int = 2) -> str:
    return "n/a" if v is None else f"{v:.{places}f}"


def _pct(v: Decimal | None, places: int = 1) -> str:
    return "n/a" if v is None else f"{v * 100:.{places}f}%"


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
        f"Backtest {rec.ruleset} | {rec.universe} | {rec.data_source}"
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
        "metrics": _plain(r.metrics),
        "equity_curve": _plain(r.equity_curve),
        "trades": [_plain(t) for t in r.trades],
    }
