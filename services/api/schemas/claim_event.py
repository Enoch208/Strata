"""Claim event: one timestamped assertion extracted from a source moment.

Mirrors PRD section 12.2. This is the unit every displayed conclusion is
ultimately traced back to, so validation here is deliberately strict.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import Certainty, ClaimStatus, ClaimType

CLAIM_EVENT_SCHEMA_VERSION = "claim-event-v1"


class ClaimEvent(BaseModel):
    """A single timestamped claim, locked to an exact window of one video."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    schema_version: str = CLAIM_EVENT_SCHEMA_VERSION
    video_id: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    source_date: date
    speaker_name: str | None = None
    speaker_role: str | None = None
    subject: str = Field(min_length=1)
    claim_type: ClaimType
    claim_text: str = Field(min_length=1)
    normalized_value: str | None = None
    unit: str | None = None
    status: ClaimStatus = ClaimStatus.unknown
    reason: str | None = None
    certainty: Certainty = Certainty.explicit
    source_artifact_ids: list[str] = Field(default_factory=list)
    extraction_model: str | None = None
    # Hydrated from the archive manifest, not from the extraction model. Kept on the
    # event so `claim_events_v1` can filter by it (PRD section 11.5).
    source_organization: str | None = None

    @model_validator(mode="after")
    def _end_after_start(self) -> ClaimEvent:
        # Part of the evidence gate (PRD section 13) enforced at parse time, so a
        # zero-length or inverted window can never reach the timeline at all.
        if self.end <= self.start:
            raise ValueError(
                f"end ({self.end}) must be greater than start ({self.start}) "
                f"for event {self.event_id}"
            )
        return self

    @property
    def duration(self) -> float:
        return self.end - self.start

    def overlaps(self, other: ClaimEvent) -> bool:
        """True when two events cover overlapping time in the same video."""
        if self.video_id != other.video_id:
            return False
        return self.start < other.end and other.start < self.end

    def to_index_record(self) -> dict[str, object]:
        """Serialize as a VideoDB temporal record for the `claim_events_v1` index.

        VideoDB's ``video.index(source=[...])`` accepts user-supplied temporal
        records carrying ``start``/``end`` plus arbitrary indexable fields.
        """
        return {
            "start": self.start,
            "end": self.end,
            "event_id": self.event_id,
            "video_id": self.video_id,
            "source_date": self.source_date.isoformat(),
            "speaker_name": self.speaker_name or "",
            "speaker_role": self.speaker_role or "",
            "subject": self.subject,
            "claim_type": str(self.claim_type),
            "claim_text": self.claim_text,
            "normalized_value": self.normalized_value or "",
            "unit": self.unit or "",
            "status": str(self.status),
            "reason": self.reason or "",
            "certainty": str(self.certainty),
            "source_artifact_ids": self.source_artifact_ids,
            "extraction_model": self.extraction_model or "",
            "source_organization": self.source_organization or "",
        }


#: Field-group configuration for `video.index(..., fields=...)` (PRD section 11.5).
CLAIM_EVENT_INDEX_FIELDS: dict[str, list[str]] = {
    "semantic": ["claim_text", "reason", "subject"],
    "filter": [
        "claim_type",
        "subject",
        "status",
        "certainty",
        "source_date",
        "source_organization",
        "video_id",
    ],
    "sort": ["source_date", "start"],
    "aggregate": ["claim_type", "status", "source_date"],
}
