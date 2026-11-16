"""Shared contract types. Vocabulary follows TRD-01 §7 and ARC-03 CHECK constraints."""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer, WithJsonSchema

DECIMAL_PATTERN = r"^-?\d+(\.\d+)?$"


def _decimal_to_str(value: Decimal) -> str:
    return format(value, "f")


DecimalStr = Annotated[
    Decimal,
    PlainSerializer(_decimal_to_str, return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "pattern": DECIMAL_PATTERN}),
]
"""Money, prices, ratios: exchanged as decimal strings (ARC-04 §2.6), held as ``Decimal`` (PE-05)."""


class ContractModel(BaseModel):
    """Base for every contract model: strict, immutable, and no unknown fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Direction(StrEnum):
    """SHORT is accepted by the contract and rejected by the rules (``SHORT_NOT_SUPPORTED``, TRD-05)."""

    LONG = "LONG"
    SHORT = "SHORT"


class BookKind(StrEnum):
    """The paper and actual books are never mixed (constraint C-11)."""

    PAPER = "PAPER"
    ACTUAL = "ACTUAL"


class AnalysisStatus(StrEnum):
    """``analysis_runs.status`` (TRD-01 §7)."""

    COMPLETED = "COMPLETED"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    INVALID_INPUT = "INVALID_INPUT"
    FAILED = "FAILED"


class RoundedLevels(ContractModel):
    """Entry, stop and target after tick-size rounding (TRD-01 §5)."""

    entry: DecimalStr
    stop: DecimalStr
    target: DecimalStr


__all__ = [
    "DECIMAL_PATTERN",
    "AnalysisStatus",
    "BookKind",
    "ContractModel",
    "DecimalStr",
    "Direction",
    "RoundedLevels",
]
