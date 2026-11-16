"""``POST /internal/v1/jobs`` and ``GET /internal/v1/jobs/{id}`` (ARC-08 §5)."""

from enum import StrEnum
from typing import Any

from pydantic import Field

from app.schemas.common import ContractModel


class JobKind(StrEnum):
    INGEST_DAILY = "INGEST_DAILY"
    BACKFILL = "BACKFILL"
    INSTRUMENT_SYNC = "INSTRUMENT_SYNC"
    ANALYSE_BATCH = "ANALYSE_BATCH"
    BACKTEST = "BACKTEST"
    PAPER_EOD = "PAPER_EOD"
    EXPLAIN = "EXPLAIN"


class JobState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobCreate(ContractModel):
    """Enqueue a job. The payload shape depends on ``kind`` and is validated by the job handler."""

    kind: JobKind
    payload: dict[str, Any]


class JobAccepted(ContractModel):
    job_id: str


class JobStatusResponse(ContractModel):
    """Job state; the durable result is the referenced resource (``result_ref``)."""

    status: JobState
    progress_pct: int = Field(ge=0, le=100)
    result_ref: dict[str, str] | None = None
    error_code: str | None = None
