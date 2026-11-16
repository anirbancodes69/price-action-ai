"""``POST /internal/v1/analyse`` (ARC-08 §5)."""

from datetime import date
from uuid import UUID

from pydantic import Field

from app.schemas.common import AnalysisStatus, ContractModel


class AnalyseRequest(ContractModel):
    """Build a candle snapshot and analyse one instrument. ``as_of`` defaults to the latest ingested date."""

    data_source_id: UUID
    instrument_id: UUID
    as_of: date | None = None
    ruleset_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$", examples=["0.1.0"])


class AnalyseResponse(ContractModel):
    """Synchronous result (within the 2 s budget)."""

    analysis_run_id: UUID
    status: AnalysisStatus


class AnalyseAccepted(ContractModel):
    """202 when the analysis does not finish within the synchronous budget."""

    job_id: str
