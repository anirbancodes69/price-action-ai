"""``POST /internal/v1/analysis`` (T-I80): one instrument's analysis for chart overlays and setups."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import ContractModel, DecimalStr


class AnalysisDetailRequest(ContractModel):
    data_source_id: UUID
    symbol: str = Field(pattern=r"^[A-Z0-9&_-]{1,32}$")
    as_of_ts: datetime | None = None


class PivotModel(ContractModel):
    kind: str
    bar_start: datetime
    price: DecimalStr
    label: str
    confirmed_at: datetime = Field(description="Show the pivot only from this moment on (no repainting).")


class EventModel(ContractModel):
    type: str
    direction: str
    level: DecimalStr
    level_bar_start: datetime = Field(description="Bar start of the pivot whose level was broken.")
    break_bar_start: datetime
    close: DecimalStr
    close_inside_buffer: bool


class ZoneModel(ContractModel):
    role: str = Field(description="SUPPORT, RESISTANCE or INSIDE relative to the last close.")
    low: DecimalStr
    high: DecimalStr
    touches: int
    strength: int
    strength_bucket: str
    status: str
    role_reversed: bool
    htf_member: bool
    formed_at: datetime = Field(description="End of the bar at which the zone became known.")


class PoolModel(ContractModel):
    type: str
    level: DecimalStr


class PaqsComponentModel(ContractModel):
    name: str
    points: int
    maximum: int
    missing: bool


class SetupModel(ContractModel):
    type: str
    direction: str
    informational: bool
    status: str
    detected_at: datetime
    trigger_price: DecimalStr
    entry: DecimalStr | None
    stop: DecimalStr | None
    target: DecimalStr | None
    target_source: str | None
    rr: DecimalStr | None
    rr_below_min: bool | None
    paqs: int | None
    paqs_version: str | None
    paqs_components: list[PaqsComponentModel]
    end_reason: str | None


class SessionLevelsModel(ContractModel):
    pdh: DecimalStr | None
    pdl: DecimalStr | None
    pdc: DecimalStr | None
    or_high: DecimalStr | None
    or_low: DecimalStr | None
    session_high: DecimalStr | None
    session_low: DecimalStr | None


class SignalModel(ContractModel):
    signal: str
    reasons: list[str]
    signal_at: datetime
    valid_until: datetime | None


class AnalysisDetail(ContractModel):
    symbol: str
    session_date: str
    as_of_ts: datetime
    status: str
    problems: list[str]
    ruleset_version: str
    state_5m: str | None
    protected_low_5m: DecimalStr | None
    protected_high_5m: DecimalStr | None
    transition_direction_5m: str | None
    state_15m: str | None
    levels: SessionLevelsModel | None
    pivots: list[PivotModel]
    events: list[EventModel]
    zones: list[ZoneModel]
    pools: list[PoolModel]
    setups: list[SetupModel]
    signal: SignalModel | None
    no_setup_reasons: list[str]
