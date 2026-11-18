"""Account state supplied by the owner (the engine does not store trades yet; TRD-05 §8.1)."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.domain.risk.account import AccountState, ClosedTrade, OpenPosition, derive_account_state


@dataclass(frozen=True, slots=True)
class AccountInput:
    capital: Decimal
    closed_today: tuple[ClosedTrade, ...] = ()
    open_positions: tuple[OpenPosition, ...] = ()
    pending_fills: int = 0
    losing_streak: int | None = None  # caller-supplied streak when the individual trades are not known

    def state(self) -> AccountState:
        st = derive_account_state(self.closed_today, self.open_positions, self.pending_fills)
        return st if self.losing_streak is None else replace(st, losing_streak=self.losing_streak)


def parse_account(data: dict[str, Any]) -> AccountInput:
    """`{"capital": "100000", "closed_today": [{"net_pnl": "-300"}], "open_positions":
    [{"entry_fill": "100", "stop": "98", "qty": 10}], "pending_fills": 0}`. Money: strings or numbers."""
    return AccountInput(
        Decimal(str(data["capital"])),
        tuple(ClosedTrade(Decimal(str(t["net_pnl"]))) for t in data.get("closed_today", [])),
        tuple(
            OpenPosition(Decimal(str(p["entry_fill"])), Decimal(str(p["stop"])), int(p["qty"]))
            for p in data.get("open_positions", [])
        ),
        int(data.get("pending_fills", 0)),
    )


def read_account(path: Path) -> AccountInput:
    return parse_account(json.loads(path.read_text(encoding="utf-8")))
