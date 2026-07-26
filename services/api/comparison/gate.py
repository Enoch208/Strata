"""The evidence gate.

PRD section 13. A finding may only be displayed when every event behind it is
real, timestamped, and playable. This runs *before* any summary is generated
(guardrail 7), so an ungrounded finding never reaches the language stage at all.

Rejections are returned rather than raised: the product shows an honest
insufficient-evidence state, and the rejection reasons stay auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..schemas.claim_event import ClaimEvent
from ..schemas.enums import MULTI_EVENT_LABELS
from ..schemas.finding import TimelineFinding
from ..schemas.packet import EvidenceShot


@dataclass(frozen=True)
class Rejection:
    """One finding the gate refused, and why."""

    finding_id: str
    reason: str


@dataclass
class GateResult:
    """Findings that passed, and the auditable reasons the rest did not."""

    accepted: list[TimelineFinding] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)

    @property
    def rejected_finding_ids(self) -> list[str]:
        return [rejection.finding_id for rejection in self.rejections]


def check_finding(
    finding: TimelineFinding,
    events_by_id: dict[str, ClaimEvent],
    shots_by_event_id: dict[str, EvidenceShot],
) -> str | None:
    """Return the reason `finding` fails the gate, or `None` if it passes."""
    if not finding.event_ids:
        return "finding cites no events"

    if finding.label in MULTI_EVENT_LABELS and len(set(finding.event_ids)) < 2:
        return (
            f"label '{finding.label}' requires at least two distinct events, "
            f"got {len(set(finding.event_ids))}"
        )

    for event_id in finding.event_ids:
        event = events_by_id.get(event_id)
        if event is None:
            return f"event {event_id} is not present in the retrieved evidence"

        if not event.video_id:
            return f"event {event_id} has no video ID"

        # Redundant with ClaimEvent's own validator, but the gate is the last line
        # before display and does not assume upstream construction was validated.
        if event.end <= event.start:
            return (
                f"event {event_id} has a non-positive window "
                f"({event.start} to {event.end})"
            )

        shot = shots_by_event_id.get(event_id)
        if shot is None:
            return f"event {event_id} has no retrieved source shot"

        if not shot.is_playable:
            return f"event {event_id} did not produce a playable stream"

    return None


def apply_gate(
    findings: list[TimelineFinding],
    events: list[ClaimEvent],
    shots: list[EvidenceShot],
) -> GateResult:
    """Filter `findings` down to those whose evidence is real and playable."""
    events_by_id = {event.event_id: event for event in events}
    shots_by_event_id = {shot.event_id: shot for shot in shots}

    result = GateResult()
    for finding in findings:
        reason = check_finding(finding, events_by_id, shots_by_event_id)
        if reason is None:
            result.accepted.append(finding)
        else:
            result.rejections.append(Rejection(finding_id=finding.finding_id, reason=reason))
    return result


def accepted_video_ids(
    findings: list[TimelineFinding],
    events: list[ClaimEvent],
) -> list[str]:
    """Distinct source videos behind `findings`, in chronological first-seen order.

    Feeds the challenge pass's source-novelty check (PRD CTR-07).
    """
    supporting = {event_id for finding in findings for event_id in finding.event_ids}
    ordered: list[str] = []
    for event in sorted(events, key=lambda e: (e.source_date, e.start)):
        if event.event_id in supporting and event.video_id not in ordered:
            ordered.append(event.video_id)
    return ordered
