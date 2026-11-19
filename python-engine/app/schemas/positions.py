"""``POST /internal/v1/positions/evaluate``: HOLD or EXIT for open positions on the latest closed 5m bar."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import ContractModel, DecimalStr


class PositionInput(ContractModel):
    id: str = Field(max_length=64, description="Caller's id, echoed back (the trade id).")
    symbol: str = Field(pattern=r"^[A-Z0-9&_-]{1,32}$")
    entry_at: datetime = Field(description="When the position was entered (ISO-8601 with offset).")
    stop: DecimalStr | None = None
    target: DecimalStr | None = None


class PositionsEvaluationRequest(ContractModel):
    data_source_id: UUID
    positions: list[PositionInput] = Field(max_length=100)
    as_of_ts: datetime | None = Field(
        default=None, description="Evaluate as of this bar end (default: latest)."
    )


class PositionSignalModel(ContractModel):
    id: str
    symbol: str
    signal: str | None = Field(description="HOLD or EXIT; null when the symbol has no stored bars.")
    reason: str | None = Field(
        description="STOP, TARGET, STRUCTURE_EXIT or SESSION_END for EXIT; NO_BARS otherwise null."
    )
    bar_end: datetime | None = Field(description="End of the closed bar on which the exit condition was met.")
    as_of_ts: datetime | None = Field(description="End of the latest closed 5m bar used.")


class PositionsEvaluation(ContractModel):
    ruleset_version: str
    positions: list[PositionSignalModel]
