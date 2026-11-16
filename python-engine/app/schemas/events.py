"""Engine -> Laravel internal endpoints (ARC-08 §5): domain events and the just-in-time provider token."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, SecretStr

from app.schemas.common import ContractModel


class EngineEvent(ContractModel):
    """``POST /internal/v1/events``. Idempotent by ``event_id``.

    Laravel turns events into notifications and audit rows.
    """

    event_id: UUID
    type: str = Field(
        pattern=r"^[A-Z][A-Z0-9_]*$",
        description=(
            "Upper-snake event type, e.g. PLAN_TRIGGERED, PAPER_EXIT, INGESTION_COMPLETED, "
            "BACKTEST_COMPLETED."
        ),
        examples=["PLAN_TRIGGERED"],
    )
    occurred_at: datetime
    payload: dict[str, Any]


class ProviderAccessToken(ContractModel):
    """``GET /internal/v1/provider-connections/{id}/access-token``.

    Held in memory only, never logged or persisted.
    """

    access_token: SecretStr
    expires_at: datetime
