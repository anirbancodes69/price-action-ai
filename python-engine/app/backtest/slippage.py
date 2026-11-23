"""Execution-specific slippage assumptions (Phase 1 D-4, DEC-024).

Slippage here is always an **assumption**, never measured. A model gives one adverse percentage per execution
type: a buy fills higher, a sell fills lower. Two named models exist:

- `legacy-stop-only`: the original behaviour (entry and stop exits only). Kept so every earlier backtest is
  reproducible exactly.
- `adverse-all`: the same percentage on the entry and on every exit type (stop, target, session end,
  structure). The default for new runs started from `scripts/run_backtest.py`.

Measured slippage needs actual execution data and does not exist yet; reports say so.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

EXEC_TYPES = ("entry", "stop", "target", "session_end", "structure")
BASIS = "ASSUMED"  # never "MEASURED" until real fills exist

_REASON_KIND = {
    "STOP": "stop",
    "STOP_GAP": "stop",
    "STOP_COLLISION": "stop",
    "TARGET": "target",
    "TARGET_GAP": "target",
    "SESSION_END": "session_end",
    "STRUCTURE_EXIT": "structure",
}  # END_OF_DATA, HORIZON and any other reason: not an execution, no slippage


def kind_for_reason(reason: str) -> str | None:
    return _REASON_KIND.get(reason)


@dataclass(frozen=True, slots=True)
class SlippageModel:
    id: str
    entry: Decimal
    stop: Decimal
    target: Decimal
    session_end: Decimal
    structure: Decimal
    basis: str = BASIS

    def pct(self, kind: str) -> Decimal:
        if kind not in EXEC_TYPES:
            raise ValueError(f"unknown execution type {kind!r}")
        return Decimal(getattr(self, kind))

    def entry_price(self, reference: Decimal) -> Decimal:
        return reference * (1 + self.entry / 100)

    def exit_price(self, kind: str, reference: Decimal) -> Decimal:
        return reference * (1 - self.pct(kind) / 100)

    def cost(self, entry_fill: Decimal, exit_price: Decimal, qty: int, reason: str) -> Decimal:
        """Rupees lost to slippage on one round trip, recovered from the filled prices."""
        c = (entry_fill - entry_fill / (1 + self.entry / 100)) * qty
        kind = kind_for_reason(reason)
        if kind is not None and self.pct(kind) != 0:
            c += (exit_price / (1 - self.pct(kind) / 100) - exit_price) * qty
        return c

    @classmethod
    def legacy(cls, pct: Decimal) -> SlippageModel:
        z = Decimal(0)
        return cls("legacy-stop-only", pct, pct, z, z, z)

    @classmethod
    def uniform(cls, pct: Decimal, model_id: str = "adverse-all") -> SlippageModel:
        return cls(model_id, pct, pct, pct, pct, pct)

    @classmethod
    def parse(cls, spec: str, default: Decimal) -> SlippageModel:
        """`entry=0.05,stop=0.1,...` (unnamed types take `default`): a custom model for sensitivity work."""
        vals = dict.fromkeys(EXEC_TYPES, default)
        for part in filter(None, (p.strip() for p in spec.split(","))):
            k, _, v = part.partition("=")
            if k.strip() not in EXEC_TYPES or not v:
                raise ValueError(f"bad slippage item {part!r}; use {'/'.join(EXEC_TYPES)}=percent")
            vals[k.strip()] = Decimal(v)
        return cls(
            "custom", vals["entry"], vals["stop"], vals["target"], vals["session_end"], vals["structure"]
        )

    def describe(self) -> str:
        v = ", ".join(f"{k} {self.pct(k)}%" for k in EXEC_TYPES)
        return f"{self.id} ({v}); {self.basis}, not measured"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "basis": self.basis, **{k: str(self.pct(k)) for k in EXEC_TYPES}}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SlippageModel:
        v = {k: Decimal(d[k]) for k in EXEC_TYPES}
        return cls(
            d["id"],
            v["entry"],
            v["stop"],
            v["target"],
            v["session_end"],
            v["structure"],
            d.get("basis", BASIS),
        )


def from_options(model: str, custom: str | None, ruleset_pct: Decimal) -> SlippageModel:
    """The model a run uses. `model` is `legacy` or `adverse-all`; `custom` (per-type list) overrides both.

    The percentage for `legacy` and `adverse-all` is the ruleset's `backtest.slippage_pct`.
    """
    if custom:
        return SlippageModel.parse(custom, ruleset_pct)
    if model == "legacy":
        return SlippageModel.legacy(ruleset_pct)
    if model == "adverse-all":
        return SlippageModel.uniform(ruleset_pct)
    raise ValueError(f"unknown slippage model {model!r}")
