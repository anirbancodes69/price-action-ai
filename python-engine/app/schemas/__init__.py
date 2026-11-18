"""Engine contract: Pydantic models for the internal API (ARC-08 §5), exported to ``contracts/engine/``.

``scripts/export_engine_schemas.py`` writes one JSON Schema per model listed in
``EXPORTED_MODELS``; CI fails when the committed files are stale (ENG-04 §8).
Add a model here and re-export to change the contract.
"""

from pydantic import BaseModel

from app.schemas.analysis import AnalyseAccepted, AnalyseRequest, AnalyseResponse
from app.schemas.analysis_detail import AnalysisDetail, AnalysisDetailRequest
from app.schemas.common import AnalysisStatus, BookKind, Direction
from app.schemas.events import EngineEvent, ProviderAccessToken
from app.schemas.explanations import ExplanationRequest
from app.schemas.jobs import JobAccepted, JobCreate, JobKind, JobState, JobStatusResponse
from app.schemas.risk import (
    AccountState,
    LevelsValidationRequest,
    LevelsValidationResponse,
    PositionSizeRequest,
    RiskResult,
)
from app.schemas.scan import ScanAccount, ScanRequest, ScanResponse, ScanRowModel

EXPORTED_MODELS: tuple[type[BaseModel], ...] = (
    AnalyseRequest,
    AnalyseResponse,
    AnalyseAccepted,
    PositionSizeRequest,
    RiskResult,
    LevelsValidationRequest,
    LevelsValidationResponse,
    JobCreate,
    JobAccepted,
    JobStatusResponse,
    ExplanationRequest,
    EngineEvent,
    ProviderAccessToken,
    ScanRequest,
    ScanResponse,
    AnalysisDetailRequest,
    AnalysisDetail,
)
"""Models whose JSON Schema is part of the Laravel <-> engine contract, in export order."""

__all__ = [
    "EXPORTED_MODELS",
    "AccountState",
    "AnalyseAccepted",
    "AnalyseRequest",
    "AnalyseResponse",
    "AnalysisDetail",
    "AnalysisDetailRequest",
    "AnalysisStatus",
    "BookKind",
    "Direction",
    "EngineEvent",
    "ExplanationRequest",
    "JobAccepted",
    "JobCreate",
    "JobKind",
    "JobState",
    "JobStatusResponse",
    "LevelsValidationRequest",
    "LevelsValidationResponse",
    "PositionSizeRequest",
    "ProviderAccessToken",
    "RiskResult",
    "ScanAccount",
    "ScanRequest",
    "ScanResponse",
    "ScanRowModel",
]
