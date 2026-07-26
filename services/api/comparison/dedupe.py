"""Duplicate claim-event removal.

PRD CLM-03 and RET-05, and the section 22 risk "duplicate claims crowd the
timeline". Deduplication is by source, time overlap, subject and normalized
value — deliberately conservative, so two genuinely different statements that
happen to sit close together both survive.
"""

from __future__ import annotations

from ..schemas.claim_event import ClaimEvent
from ..schemas.enums import Certainty

#: Ranked best-first. A more directly stated event beats an inferred one.
_CERTAINTY_RANK: dict[Certainty, int] = {
    Certainty.explicit: 0,
    Certainty.implied: 1,
    Certainty.uncertain: 2,
}


def _comparable_key(event: ClaimEvent) -> tuple[str, str, str, str]:
    """The identity a duplicate must match on, ignoring wording differences."""
    return (
        event.video_id,
        event.subject.strip().lower(),
        str(event.claim_type),
        (event.normalized_value or event.claim_text).strip().lower(),
    )


def _preference(event: ClaimEvent) -> tuple[int, float, float]:
    """Sort key choosing which of two duplicates to keep.

    Prefers the more certain event, then the longer window (more context around
    the quotation, per guardrail 11), then the earlier start for stability.
    """
    return (
        _CERTAINTY_RANK[event.certainty],
        -event.duration,
        event.start,
    )


def dedupe_events(events: list[ClaimEvent]) -> list[ClaimEvent]:
    """Drop events that restate the same claim from the same source moment.

    Two events collapse only when they share a video, subject, claim type and
    normalized value *and* their time windows overlap. Same claim repeated at a
    genuinely different moment is kept — that repetition is itself evidence.

    Returns events sorted by source date, then start time (PRD RET-04).
    """
    survivors: dict[tuple[str, str, str, str], list[ClaimEvent]] = {}

    for event in sorted(events, key=_preference):
        key = _comparable_key(event)
        bucket = survivors.setdefault(key, [])
        if any(event.overlaps(kept) for kept in bucket):
            continue
        bucket.append(event)

    kept = [event for bucket in survivors.values() for event in bucket]
    return sort_chronologically(kept)


def sort_chronologically(events: list[ClaimEvent]) -> list[ClaimEvent]:
    """Order events by source date, then in-video start time (PRD RET-04)."""
    return sorted(events, key=lambda event: (event.source_date, event.start, event.event_id))


def drop_duplicate_shots(events: list[ClaimEvent]) -> list[ClaimEvent]:
    """Remove overlapping windows from the same video, whatever the claim.

    Used for reel assembly (PRD REL-05), where two overlapping shots would replay
    the same footage twice rather than add evidence.
    """
    chosen: list[ClaimEvent] = []
    for event in sort_chronologically(events):
        if any(event.overlaps(kept) for kept in chosen):
            continue
        chosen.append(event)
    return chosen
