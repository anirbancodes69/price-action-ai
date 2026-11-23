"""RulesetParams (ENG-04 §5, PE-06): the only source of thresholds.

Pure: the JSON file is read by `app.rulesets`, not here.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from app.domain.types import Timeframe


def _pct(value: object) -> Decimal:
    """Percent registry value -> fraction, exactly (0.05 -> 0.0005)."""
    return Decimal(str(value)) / Decimal(100)


@dataclass(frozen=True, slots=True)
class RulesetParams:
    code: str
    version: str
    values: Mapping[str, object]

    @property
    def content_hash(self) -> str:
        """SHA-256 of the canonical JSON values (the seeder hash form): identifies the configuration."""
        return hashlib.sha256(
            json.dumps(dict(self.values), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()

    def get(self, key: str) -> object:
        try:
            return self.values[key]
        except KeyError:
            raise KeyError(f"ruleset {self.code} {self.version} has no parameter {key!r}") from None

    def int_(self, key: str) -> int:
        v = self.get(key)
        if isinstance(v, bool) or not isinstance(v, int):
            raise TypeError(f"parameter {key!r} is not an integer: {v!r}")
        return v

    def pivot_left(self, tf: Timeframe) -> int:
        return self.int_(f"pivot.left_bars_{tf}")

    def pivot_right(self, tf: Timeframe) -> int:
        return self.int_(f"pivot.right_bars_{tf}")

    def break_buffer(self, tf: Timeframe) -> Decimal:
        """`structure.break_buffer_pct_<tf>` as a fraction."""
        return _pct(self.get(f"structure.break_buffer_pct_{tf}"))

    def equal_tolerance(self) -> Decimal:
        """`structure.equal_level_tolerance_pct` as a fraction."""
        return _pct(self.get("structure.equal_level_tolerance_pct"))

    def decimal(self, key: str) -> Decimal:
        """Any numeric parameter as an exact `Decimal` (percent values are NOT converted)."""
        v = self.get(key)
        if isinstance(v, bool) or not isinstance(v, int | float | str):
            raise TypeError(f"parameter {key!r} is not numeric: {v!r}")
        return Decimal(str(v))

    def pct(self, key: str) -> Decimal:
        """A `*_pct` parameter as a fraction (0.15 -> 0.0015)."""
        return _pct(self.get(key))
