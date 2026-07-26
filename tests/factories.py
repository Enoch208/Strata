"""Test helpers for building claim events without repeating boilerplate."""

from __future__ import annotations

from datetime import date

from services.api.schemas.claim_event import ClaimEvent
from services.api.schemas.enums import Certainty, ClaimStatus, ClaimType


def make_event(
    event_id: str,
    *,
    video_id: str = "vid_a",
    start: float = 10.0,
    # Defaults to a 15s window after `start`, so callers can move `start` freely.
    end: float | None = None,
    source_date: date | str = "2022-09-03",
    subject: str = "Artemis I launch",
    claim_type: ClaimType = ClaimType.status_update,
    claim_text: str = "A statement about the launch.",
    normalized_value: str | None = None,
    status: ClaimStatus = ClaimStatus.unknown,
    reason: str | None = None,
    certainty: Certainty = Certainty.explicit,
    speaker_role: str | None = "NASA mission official",
) -> ClaimEvent:
    return ClaimEvent(
        event_id=event_id,
        video_id=video_id,
        start=start,
        end=start + 15.0 if end is None else end,
        source_date=date.fromisoformat(source_date) if isinstance(source_date, str) else source_date,
        subject=subject,
        claim_type=claim_type,
        claim_text=claim_text,
        normalized_value=normalized_value,
        status=status,
        reason=reason,
        certainty=certainty,
        speaker_role=speaker_role,
        source_organization="NASA",
    )
