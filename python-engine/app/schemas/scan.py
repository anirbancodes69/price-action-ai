"""``POST /internal/v1/scan`` (T-I78): the scanner rows for one universe at one moment."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import ContractModel, DecimalStr


class ScanAccount(ContractModel):
    """The book's account state, supplied by the caller (the engine stores no trades yet, TRD-05 §8.1)."""

    capital: DecimalStr
    realised_net_pnl_today: DecimalStr = Decimal(0)
    open_risk: DecimalStr = Decimal(0)
    open_cost_basis: DecimalStr = Decimal(0)
    open_positions: int = Field(default=0, ge=0)
    losing_streak: int = Field(default=0, ge=0)


class ScanRequest(ContractModel):
    data_source_id: UUID
    universe_code: str = Field(default="NIFTY50", pattern=r"^[A-Z0-9_]{1,32}$")
    as_of_ts: datetime | None = Field(
        default=None, description="Replay a past moment: only bars that ended at or before it are used."
    )
    account: ScanAccount
    include_no_trade: bool = False


class ScanRowModel(ContractModel):
    symbol: str
    signal: str = Field(
        description="ENTRY_CONFIRMED, BUY_WATCH, NO_TRADE, INSUFFICIENT_HISTORY or INVALID_INPUT."
    )
    setup_type: str | None
    setup_status: str | None
    paqs: int | None
    entry: DecimalStr | None
    stop: DecimalStr | None
    target: DecimalStr | None
    target_source: str | None
    rr: DecimalStr | None
    quantity: int | None = Field(description="Sized with the account limits; null when no plan can be sized.")
    risk_amount: DecimalStr | None
    position_value: DecimalStr | None
    binding_constraint: str | None
    reasons: list[str]
    signal_at: datetime | None
    valid_until: datetime | None
    last_bar_end: datetime
    stale: bool
    htf_state: str | None


class ScanResponse(ContractModel):
    as_of_ts: datetime
    data_mode: str = Field(
        description="DEMO, PERSONAL or LICENSED (ADR-011). DEMO is never presented as live."
    )
    provider: str
    ruleset_version: str
    notice: str
    rows: list[ScanRowModel]
