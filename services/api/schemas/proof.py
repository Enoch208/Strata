"""Machine-derived submission proof exposed to the judge-facing UI."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MetricProof(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    percentage: float | None = None


class EvaluationArmProof(BaseModel):
    model_config = ConfigDict(extra="forbid")

    arm: str
    label: str
    retrieval_recall: MetricProof
    unsupported_claims: MetricProof


class IndexProof(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spoken_word_ready: bool
    ocr_ready: bool
    visual_ready: bool
    claim_event_ready: bool
    timeline_finding_ready: bool


class VerificationProof(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tests_passed: int = Field(ge=0)
    generated_at: datetime | None = None
    command: str | None = None


class SubmissionProof(BaseModel):
    model_config = ConfigDict(extra="forbid")

    distinct_video_ids: int = Field(ge=0)
    index_proof: IndexProof
    evaluation_cases: int = Field(ge=0)
    evaluation: list[EvaluationArmProof]
    verification: VerificationProof
