"""Signal and rejection accounting for the B0 run (GAP-2): every eligible instrument-session gets one outcome.

Counts are measured, never inferred from filled trades. For each evaluated instrument-session the B0
analysis is run on the full session (the same `strategy_analyse` function the replay uses, only bars closed by
then) and, if the setup confirmed, again at the confirmation bar to read the signal and its `NO_TRADE`
reasons. Fill-time and risk skips come from the replay result. `reconcile` checks that the pieces add up and
returns any problem as text; a run whose accounting does not reconcile must not be read.

Outcome codes (exclusive, one per evaluated instrument-session):
`OR_TOO_NARROW`, `OR_TOO_WIDE`, `INVALID_RANGE:<ORB-MG-02 reason>`, `RANGE_NOT_FORMED`, `WHIPSAW`,
`WINDOW_EXPIRED`, `CUTOFF_EXPIRED`, `NO_BREAKOUT`, `SIGNAL_NO_TRADE:<reasons>`, `SIGNAL_CANDIDATE`,
`SNAPSHOT_INVALID:<status>`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

from app.backtest.b0_eligibility import Eligibility
from app.backtest.exclusions import Exclusion
from app.backtest.replay import AnalyseFn, SessionSpec, SymbolData
from app.backtest.run import BacktestResult, SessionInput
from app.domain.params import RulesetParams
from app.domain.setups.signal import Signal
from app.domain.setups.types import SetupStatus
from app.domain.snapshot import SnapshotStatus


@dataclass(frozen=True, slots=True)
class SessionOutcome:
    symbol: str
    day: date
    outcome: str


def classify_instrument_session(
    sym: SymbolData, spec: SessionSpec, params: RulesetParams, analyse_fn: AnalyseFn
) -> str:
    k = len(sym.bars_5m)
    res = analyse_fn(sym, k, spec, params)
    if res.check.status is not SnapshotStatus.VALID:
        return f"SNAPSHOT_INVALID:{res.check.status.value}"
    if res.no_setup_reasons:
        r = res.no_setup_reasons[0]
        return r if r in ("OR_TOO_NARROW", "OR_TOO_WIDE") else f"INVALID_RANGE:{r}"
    if not res.setups:
        return "RANGE_NOT_FORMED"
    s = res.setups[0].setup
    if s.status is SetupStatus.ENTRY_CONFIRMED and s.confirmed_at_index is not None:
        at = analyse_fn(sym, s.confirmed_at_index + 1, spec, params)
        sig = at.signal
        if sig is not None and sig.signal is Signal.ENTRY_CONFIRMED:
            return "SIGNAL_CANDIDATE"
        reasons = ",".join(sig.reasons) if sig is not None else "NO_SIGNAL"
        return f"SIGNAL_NO_TRADE:{reasons}"
    if s.status is SetupStatus.INVALIDATED:
        return "WHIPSAW" if s.end_reason == "OR_LOW_BROKEN" else f"INVALIDATED:{s.end_reason}"
    if s.status is SetupStatus.EXPIRED:
        return {"AGED_OUT": "WINDOW_EXPIRED", "SESSION_CUTOFF": "CUTOFF_EXPIRED"}.get(
            s.end_reason or "", f"EXPIRED:{s.end_reason}"
        )
    return "NO_BREAKOUT"


def classify_all(
    sessions: Sequence[SessionInput], params: RulesetParams, analyse_fn: AnalyseFn
) -> list[SessionOutcome]:
    return [
        SessionOutcome(
            sym.symbol, s.spec.session_date, classify_instrument_session(sym, s.spec, params, analyse_fn)
        )
        for s in sorted(sessions, key=lambda x: x.spec.session_date)
        for sym in sorted(s.symbols, key=lambda x: x.symbol)
    ]


@dataclass(frozen=True, slots=True)
class B0Accounting:
    evaluated: int  # eligible instrument-sessions
    outcomes: dict[str, int]
    candidates: int  # SIGNAL_CANDIDATE
    filled: int
    skipped: dict[str, int]  # skip reasons of the replay, for candidates
    excluded: dict[
        str, int
    ]  # eligibility reasons (instrument-sessions) and whole-session exclusions, separately
    excluded_sessions: dict[str, int]  # whole-session exclusions, reported separately
    problems: tuple[str, ...] = field(default=())

    @property
    def reconciles(self) -> bool:
        return not self.problems


def reconcile(
    outcomes: Sequence[SessionOutcome],
    result: BacktestResult,
    eligibility: dict[tuple[str, date], Eligibility],
    exclusions: Sequence[Exclusion],
) -> B0Accounting:
    problems: list[str] = []
    counts = Counter(o.outcome for o in outcomes)
    evaluated = len(outcomes)
    if sum(counts.values()) != evaluated:
        problems.append("outcome counts do not add up to the evaluated instrument-sessions")
    eligible_keys = {k for k, v in eligibility.items() if v.eligible}
    if {(o.symbol, o.day) for o in outcomes} != eligible_keys:
        problems.append("evaluated instrument-sessions differ from the eligible set")
    ineligible = Counter(v.reason for v in eligibility.values() if not v.eligible)
    if evaluated + sum(ineligible.values()) != len(eligibility):
        problems.append("evaluated plus excluded instrument-sessions differ from the eligibility map")
    inst_ex = Counter(e.reason for e in exclusions if e.symbol is not None)
    if dict(inst_ex) != {str(k): v for k, v in ineligible.items()}:
        problems.append("the loader's instrument exclusions differ from the eligibility map")
    cand_keys = {(o.symbol, o.day) for o in outcomes if o.outcome == "SIGNAL_CANDIDATE"}
    trade_keys = Counter((t.symbol, t.signal_at.astimezone(_IST).date()) for t in result.trades)
    skip_keys = Counter((k.symbol, k.signal_at.astimezone(_IST).date()) for k in result.skips)
    if set(trade_keys) & set(skip_keys):
        problems.append("a signal is both filled and skipped")
    if set(trade_keys) | set(skip_keys) != cand_keys:
        problems.append("candidates differ from filled trades plus skipped signals")
    if any(v > 1 for v in list(trade_keys.values()) + list(skip_keys.values())):
        problems.append("more than one outcome for one signal")
    skipped = Counter(k.reason for k in result.skips)
    return B0Accounting(
        evaluated,
        dict(sorted(counts.items())),
        len(cand_keys),
        len(result.trades),
        dict(sorted(skipped.items())),
        {str(k): v for k, v in sorted(ineligible.items(), key=lambda kv: str(kv[0]))},
        dict(sorted(Counter(e.reason for e in exclusions if e.symbol is None).items())),
        tuple(problems),
    )


from app.ingestion.session import IST as _IST  # noqa: E402
