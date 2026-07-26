"""Investigation state and the exportable Evidence Packet.

Mirrors PRD sections 12.7 and 14. The packet is the machine-readable record of
everything behind a displayed answer, including the full challenge trace.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .challenge import ChallengeResult
from .claim_event import ClaimEvent
from .finding import ClaimRelation, TimelineFinding
from .sentence import SourcedSentence

EVIDENCE_PACKET_VERSION = "evidence-packet-v1"


class InvestigationState(StrEnum):
    """Drives the progress copy in PRD sections 8 and 15.3."""

    searching = "searching"
    retrieving = "retrieving"
    comparing = "comparing"
    building = "building"
    complete = "complete"
    insufficient_evidence = "insufficient_evidence"
    failed = "failed"


class EvidenceShot(BaseModel):
    """A playable source moment for one claim event.

    `stream_url` comes from VideoDB; it is never synthesized. A shot without one
    fails the evidence gate rather than rendering a dead Play button.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: str
    video_id: str
    video_title: str
    source_url: str
    source_date: date
    start: float
    end: float
    stream_url: str | None = None
    player_url: str | None = None
    transcript_text: str | None = None

    @property
    def is_playable(self) -> bool:
        return bool(self.stream_url) and self.end > self.start


class ReelRef(BaseModel):
    """The compiled evidence reel, when one has been generated."""

    model_config = ConfigDict(extra="forbid")

    stream_url: str | None = None
    player_url: str | None = None
    event_ids: list[str] = Field(default_factory=list)
    duration_seconds: float | None = None
    error: str | None = None


class Investigation(BaseModel):
    """Everything behind one answer. Returned by `GET /api/investigations/{id}`."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: str
    archive_id: str
    query: str
    state: InvestigationState
    created_at: datetime
    summary_sentences: list[SourcedSentence] = Field(default_factory=list)
    findings: list[TimelineFinding] = Field(default_factory=list)
    relations: list[ClaimRelation] = Field(default_factory=list)
    events: list[ClaimEvent] = Field(default_factory=list)
    shots: list[EvidenceShot] = Field(default_factory=list)
    challenge: ChallengeResult | None = None
    reel: ReelRef = Field(default_factory=ReelRef)
    #: Populated when the evidence gate rejected everything, so the UI can explain.
    insufficient_evidence_reason: str | None = None
    error: str | None = None

    @property
    def accepted_video_ids(self) -> list[str]:
        """Distinct source videos behind the accepted findings, in first-seen order."""
        supporting = {eid for finding in self.findings for eid in finding.event_ids}
        seen: list[str] = []
        for event in self.events:
            if event.event_id in supporting and event.video_id not in seen:
                seen.append(event.video_id)
        return seen

    @property
    def displayable_sentences(self) -> list[SourcedSentence]:
        return [sentence for sentence in self.summary_sentences if sentence.is_displayable]


class EvidencePacket(BaseModel):
    """Downloadable export. PRD section 12.7 and EXP-01 through EXP-05."""

    model_config = ConfigDict(extra="forbid")

    packet_version: str = EVIDENCE_PACKET_VERSION
    investigation_id: str
    query: str
    generated_at: datetime
    archive: dict[str, object] = Field(default_factory=dict)
    summary_sentences: list[SourcedSentence] = Field(default_factory=list)
    findings: list[TimelineFinding] = Field(default_factory=list)
    relations: list[ClaimRelation] = Field(default_factory=list)
    events: list[ClaimEvent] = Field(default_factory=list)
    shots: list[EvidenceShot] = Field(default_factory=list)
    challenge: ChallengeResult | None = None
    reel: ReelRef = Field(default_factory=ReelRef)

    @classmethod
    def from_investigation(
        cls,
        investigation: Investigation,
        archive: dict[str, object],
        generated_at: datetime,
    ) -> EvidencePacket:
        return cls(
            investigation_id=investigation.investigation_id,
            query=investigation.query,
            generated_at=generated_at,
            archive=archive,
            summary_sentences=investigation.summary_sentences,
            findings=investigation.findings,
            relations=investigation.relations,
            events=investigation.events,
            shots=investigation.shots,
            challenge=investigation.challenge,
            reel=investigation.reel,
        )
