"""``POST /internal/v1/explanations`` (ARC-08 §5, ARC-07). The LLM only explains (ADR-009)."""

from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.common import ContractModel


class ExplanationKind(StrEnum):
    SETUP_SUMMARY = "SETUP_SUMMARY"
    CHART_QA = "CHART_QA"


class ExplanationRequest(ContractModel):
    """Enqueue an explanation. A question exists exactly for ``CHART_QA`` (ARC-03 §7)."""

    analysis_run_id: UUID
    kind: ExplanationKind
    setup_id: UUID | None = None
    question: str | None = Field(default=None, min_length=3, max_length=500)

    @model_validator(mode="after")
    def _question_only_for_chart_qa(self) -> "ExplanationRequest":
        if (self.kind is ExplanationKind.CHART_QA) != (self.question is not None):
            raise ValueError("question is required for CHART_QA and not allowed otherwise")
        return self
