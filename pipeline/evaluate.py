"""Locked comparative-evaluation utilities.

This module does not invent gold windows or model results. It validates the
12-case evaluation set, builds the naive all-transcripts prompt, and scores
explicit adjudications for both arms. Live archive runs are only possible after
ingest has populated real VideoDB IDs and transcript artifacts.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from services.api.config import EVALUATION_CASES_PATH
from services.api.schemas.enums import FindingLabel

EVALUATION_CASE_COUNT = 12


class EvidenceUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    video_id: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(gt=0)

    @model_validator(mode="after")
    def _positive_window(self) -> EvidenceUnit:
        if self.end <= self.start:
            raise ValueError("evidence end must be greater than start")
        return self

    def overlaps(self, other: EvidenceUnit) -> bool:
        return (
            self.video_id == other.video_id
            and self.start < other.end
            and other.start < self.end
        )


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    expected_evidence: list[EvidenceUnit] = Field(default_factory=list)
    expected_min_events: int = Field(ge=0)
    allowed_labels: list[FindingLabel] = Field(min_length=1)
    disallowed_unsupported_claims: list[str] = Field(default_factory=list)
    run_challenge: bool = False
    require_novel_challenge_source: bool = False
    require_source_lock_rejection: bool = False


class AtomicProposition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    supported: bool


class CaseAdjudication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    surfaced_evidence: list[EvidenceUnit] = Field(default_factory=list)
    propositions: list[AtomicProposition] = Field(default_factory=list)


class ArmAdjudication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    arm: str = Field(pattern=r"^(naive|claimtrail)$")
    model: str = Field(min_length=1)
    transcript_revision: str = Field(min_length=1)
    temperature: float
    max_answer_tokens: int = Field(gt=0)
    cases: list[CaseAdjudication]


@dataclass(frozen=True)
class LockedEvaluationConfig:
    """Configuration that must be identical across both evaluation arms."""

    model: str
    transcript_revision: str
    manifest_version: str
    temperature: float = 0.0
    max_answer_tokens: int = 600


@dataclass(frozen=True)
class Metric:
    numerator: int
    denominator: int

    @property
    def percentage(self) -> float | None:
        if self.denominator == 0:
            return None
        return self.numerator / self.denominator * 100.0


@dataclass(frozen=True)
class ArmMetrics:
    relevant_event_recall: Metric
    unsupported_claim_rate: Metric


@dataclass(frozen=True)
class TranscriptDocument:
    video_id: str
    title: str
    source_date: date
    segments: tuple[tuple[float, float, str], ...]


def load_cases(path: Path = EVALUATION_CASES_PATH) -> list[EvaluationCase]:
    cases = [
        EvaluationCase.model_validate(item)
        for item in json.loads(path.read_text(encoding="utf-8"))
    ]
    if len(cases) != EVALUATION_CASE_COUNT:
        raise ValueError(
            f"evaluation set must contain exactly {EVALUATION_CASE_COUNT} cases, "
            f"got {len(cases)}"
        )
    ids = [case.case_id for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("evaluation case IDs must be unique")
    return cases


def concatenate_transcripts(documents: list[TranscriptDocument]) -> str:
    """Render the naive baseline input without retrieval or chunk selection."""
    sections: list[str] = []
    for document in sorted(documents, key=lambda item: (item.source_date, item.video_id)):
        lines = [
            f"VIDEO ID: {document.video_id}",
            f"TITLE: {document.title}",
            f"SOURCE DATE: {document.source_date.isoformat()}",
        ]
        lines.extend(
            f"[{start:.2f} - {end:.2f}] {text}"
            for start, end, text in document.segments
        )
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def build_baseline_prompt(question: str, transcript_corpus: str) -> str:
    """One locked, all-transcripts prompt for the naive comparison arm."""
    return (
        "Answer only from the complete timestamped archive below. "
        "Return an answer plus every video ID and time range relied on. "
        "Do not use outside knowledge and do not invent timestamps.\n\n"
        f"QUESTION:\n{question}\n\n"
        f"COMPLETE ARCHIVE:\n{transcript_corpus}"
    )


def score_arm(
    cases: list[EvaluationCase],
    adjudication: ArmAdjudication,
) -> ArmMetrics:
    """Calculate corpus-level recall and unsupported-claim rate."""
    by_id = {case.case_id: case for case in cases}
    observations = {item.case_id: item for item in adjudication.cases}
    if set(observations) != set(by_id):
        missing = sorted(set(by_id) - set(observations))
        extra = sorted(set(observations) - set(by_id))
        raise ValueError(
            f"adjudication cases do not match evaluation set; missing={missing}, extra={extra}"
        )

    found = 0
    gold = 0
    unsupported = 0
    factual = 0
    for case_id, case in by_id.items():
        observation = observations[case_id]
        gold += len(case.expected_evidence)
        found += sum(
            any(unit.overlaps(surface) for surface in observation.surfaced_evidence)
            for unit in case.expected_evidence
        )
        factual += len(observation.propositions)
        unsupported += sum(
            not proposition.supported for proposition in observation.propositions
        )

    return ArmMetrics(
        relevant_event_recall=Metric(found, gold),
        unsupported_claim_rate=Metric(unsupported, factual),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Score adjudicated Strata evaluation runs.")
    parser.add_argument("adjudication", type=Path)
    parser.add_argument("--cases", type=Path, default=EVALUATION_CASES_PATH)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    raw = json.loads(args.adjudication.read_text(encoding="utf-8"))
    arms = [ArmAdjudication.model_validate(item) for item in raw]
    if {arm.arm for arm in arms} != {"naive", "claimtrail"}:
        raise ValueError("adjudication must contain exactly the naive and claimtrail arms")

    for arm in arms:
        metrics = score_arm(cases, arm)
        recall = metrics.relevant_event_recall
        unsupported = metrics.unsupported_claim_rate
        print(
            f"{arm.arm}: recall {recall.numerator}/{recall.denominator} "
            f"({_format_percentage(recall)}); unsupported "
            f"{unsupported.numerator}/{unsupported.denominator} "
            f"({_format_percentage(unsupported)})"
        )
    return 0


def _format_percentage(metric: Metric) -> str:
    return "n/a" if metric.percentage is None else f"{metric.percentage:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
