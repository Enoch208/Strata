"""Timeline findings and claim relations.

Mirrors PRD sections 12.3 and 12.4. A finding is what the timeline renders; a
relation records how two specific events sit against each other.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import (
    MULTI_EVENT_LABELS,
    Confidence,
    FindingLabel,
    RelationType,
)

CLAIM_RELATION_SCHEMA_VERSION = "claim-relation-v1"


class TimelineFinding(BaseModel):
    """One accepted comparison result, backed by its supporting event IDs."""

    model_config = ConfigDict(extra="forbid")

    finding_id: str
    label: FindingLabel
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    event_ids: list[str] = Field(min_length=1)
    confidence: Confidence
    review_reason: str | None = None

    @model_validator(mode="after")
    def _enforce_multi_event_labels(self) -> TimelineFinding:
        # PRD section 13: a comparative label is meaningless with one event.
        if self.label in MULTI_EVENT_LABELS and len(set(self.event_ids)) < 2:
            raise ValueError(
                f"label '{self.label}' requires at least two distinct event_ids, "
                f"got {self.event_ids!r} for finding {self.finding_id}"
            )
        return self

    @model_validator(mode="after")
    def _low_confidence_needs_review(self) -> TimelineFinding:
        # PRD section 13: "Low: incomplete context; must also be marked Needs review."
        if self.confidence is Confidence.low and self.label is not FindingLabel.needs_review:
            raise ValueError(
                f"finding {self.finding_id} has low confidence and must carry the "
                f"'needs_review' label, got '{self.label}'"
            )
        return self

    def to_index_record(self, source_date: str, start: float, end: float) -> dict[str, object]:
        """Serialize as a temporal record for the `timeline_findings_v1` index."""
        return {
            "start": start,
            "end": end,
            "finding_id": self.finding_id,
            "label": str(self.label),
            "title": self.title,
            "summary": self.summary,
            "event_ids": self.event_ids,
            "confidence": str(self.confidence),
            "source_date": source_date,
        }


class ClaimRelation(BaseModel):
    """A directed relation between two claim events."""

    model_config = ConfigDict(extra="forbid")

    relation_id: str
    schema_version: str = CLAIM_RELATION_SCHEMA_VERSION
    from_event_id: str
    to_event_id: str
    relation_type: RelationType
    explanation: str = Field(min_length=1)
    supporting_event_ids: list[str] = Field(min_length=2)
    confidence: Confidence
    review_required: bool = False

    @model_validator(mode="after")
    def _distinct_endpoints(self) -> ClaimRelation:
        if self.from_event_id == self.to_event_id:
            raise ValueError(
                f"relation {self.relation_id} links event {self.from_event_id} to itself"
            )
        return self


#: Field-group configuration for `video.index(..., fields=...)` (PRD section 11.5).
TIMELINE_FINDING_INDEX_FIELDS: dict[str, list[str]] = {
    "semantic": ["title", "summary"],
    "filter": ["label", "confidence", "source_date"],
    "sort": ["source_date"],
    "aggregate": ["label", "source_date"],
}
