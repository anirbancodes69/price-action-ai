"""``POST /internal/v1/analyse`` (ARC-08 §5, ADR-015)."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import AnalysisStatus, ContractModel


class AnalyseRequest(ContractModel):
    """Analyse one instrument at one 5m bar close (5m primary, 15m and daily context).

    ``as_of_ts`` is the end of the last completed 5m bar to use; it defaults to the latest stored bar close.
    """

    data_source_id: UUID
    instrument_id: UUID
    as_of_ts: datetime | None = None
    ruleset_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$", examples=["0.1.0"])


class AnalyseResponse(ContractModel):
    """Synchronous result (within the 2 s budget)."""

    analysis_run_id: UUID
    status: AnalysisStatus
    as_of_ts: datetime


class AnalyseAccepted(ContractModel):
    """202 when the analysis does not finish within the synchronous budget."""

    job_id: str
