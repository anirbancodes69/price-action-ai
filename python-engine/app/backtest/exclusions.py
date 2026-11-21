"""Sessions and instrument-sessions a research run does not replay, with the reason (standards §7, D-7).

`SPECIAL_SESSIONS` are the sessions in the stored history that are not a normal 09:15-15:30 day (L-4): two
partial Saturday sessions, the Muhurat evening sessions and one short session. They are removed from the
replay *and* from the lookback window and the previous-day lookup, so no result is computed from a partial
session. The three full-length weekend sessions are kept. The list is a research-harness constant until the
verified holiday and special-session calendar exists (T-I137); every run reports what it excluded.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

SPECIAL_SESSIONS: dict[date, str] = {
    date(2024, 3, 2): "SPECIAL_SESSION_PARTIAL_SATURDAY",
    date(2024, 5, 18): "SPECIAL_SESSION_PARTIAL_SATURDAY",
    date(2024, 11, 1): "SPECIAL_SESSION_MUHURAT_EVENING",
    date(2025, 10, 21): "SPECIAL_SESSION_SHORT_MUHURAT",
    date(2026, 11, 8): "SPECIAL_SESSION_MUHURAT_EVENING",
}

MISSING_PREV_DAY_LEVELS = "MISSING_PREV_DAY_LEVELS"
# The previous day's 1D bar does not contain that day's 5m range (for example a corporate-action break).
INCONSISTENT_PREV_DAY_LEVELS = "INCONSISTENT_PREV_DAY_LEVELS"


@dataclass(frozen=True, slots=True)
class Exclusion:
    """`symbol is None` excludes the whole session."""

    day: date
    symbol: str | None
    reason: str


def summarise(exclusions: list[Exclusion]) -> dict[str, int]:
    """Counts by reason (sessions for whole-session exclusions, instrument-sessions otherwise)."""
    out: dict[str, int] = {}
    for e in exclusions:
        out[e.reason] = out.get(e.reason, 0) + 1
    return out
