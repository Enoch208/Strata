"""Turn VideoDB search results back into typed claim events.

The custom `claim_events_v1` index stores each claim event as a temporal record,
so a search hit carries those fields back. This module validates them at the
trust boundary; a hit that cannot be reconstructed into a real `ClaimEvent` is
dropped with a reason rather than patched with defaults.

The exact field placement in a search hit (top-level, `metadata`, or `data`) is
not documented, so `record_from_hit` checks each and reports what it saw when it
finds nothing usable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import ValidationError

from ..schemas.claim_event import ClaimEvent
from ..schemas.enums import Certainty, ClaimStatus, ClaimType

#: Containers a hit may nest its indexed fields under.
_FIELD_CONTAINERS = ("metadata", "data", "fields", "record", "document")

#: A field every claim-event record carries, used to recognize the right container.
_MARKER_FIELD = "event_id"


@dataclass
class HydrationResult:
    """Reconstructed events, their relevance scores, and dropped-hit reasons."""

    events: list[ClaimEvent] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    hits_by_event_id: dict[str, Any] = field(default_factory=dict)
    dropped: list[str] = field(default_factory=list)

    def scored(self) -> list[tuple[ClaimEvent, float]]:
        return [(event, self.scores.get(event.event_id, 0.0)) for event in self.events]


def record_from_hit(hit: Any) -> dict[str, Any] | None:
    """Locate the indexed claim-event fields on a search hit."""
    if isinstance(hit, dict):
        if _MARKER_FIELD in hit:
            return hit
        for container in _FIELD_CONTAINERS:
            nested = hit.get(container)
            if isinstance(nested, dict) and _MARKER_FIELD in nested:
                return nested
        return None

    for container in _FIELD_CONTAINERS:
        nested = getattr(hit, container, None)
        if isinstance(nested, dict) and _MARKER_FIELD in nested:
            return nested

    return None


def hydrate_hits(hits: list[Any]) -> HydrationResult:
    """Rebuild claim events from search hits, keeping the best score per event."""
    result = HydrationResult()
    seen: dict[str, ClaimEvent] = {}

    for position, hit in enumerate(hits):
        record = record_from_hit(hit)
        if record is None:
            result.dropped.append(f"hit {position}: no claim-event fields found ({_describe(hit)})")
            continue

        event, error = event_from_record(record, hit)
        if event is None:
            result.dropped.append(f"hit {position}: {error}")
            continue

        score = _score_of(hit, record)
        if event.event_id in seen:
            result.scores[event.event_id] = max(result.scores[event.event_id], score)
            continue

        seen[event.event_id] = event
        result.events.append(event)
        result.scores[event.event_id] = score
        result.hits_by_event_id[event.event_id] = hit

    return result


def event_from_record(record: dict[str, Any], hit: Any = None) -> tuple[ClaimEvent | None, str | None]:
    """Validate one indexed record into a `ClaimEvent`."""
    start = _number(record.get("start"))
    if start is None:
        start = _number(getattr(hit, "start", None))
    end = _number(record.get("end"))
    if end is None:
        end = _number(getattr(hit, "end", None))
    if start is None or end is None:
        return None, "record has no usable start/end timestamps"

    video_id = _text(record.get("video_id")) or _text(getattr(hit, "video_id", None))
    if not video_id:
        return None, "record has no video_id"

    source_date = _date(record.get("source_date"))
    if source_date is None:
        return None, f"record has no parseable source_date ({record.get('source_date')!r})"

    try:
        event = ClaimEvent(
            event_id=_text(record.get("event_id")) or f"evt_{video_id}_{start:.0f}",
            video_id=video_id,
            start=start,
            end=end,
            source_date=source_date,
            speaker_name=_text(record.get("speaker_name")),
            speaker_role=_text(record.get("speaker_role")),
            subject=_text(record.get("subject")) or "Artemis I",
            claim_type=_enum(record.get("claim_type"), ClaimType, ClaimType.other),
            claim_text=_text(record.get("claim_text")) or "",
            normalized_value=_text(record.get("normalized_value")),
            unit=_text(record.get("unit")),
            status=_enum(record.get("status"), ClaimStatus, ClaimStatus.unknown),
            reason=_text(record.get("reason")),
            certainty=_enum(record.get("certainty"), Certainty, Certainty.uncertain),
            source_artifact_ids=_string_list(record.get("source_artifact_ids")),
            extraction_model=_text(record.get("extraction_model")),
            source_organization=_text(record.get("source_organization")),
        )
    except ValidationError as error:
        first = error.errors()[0]
        location = ".".join(str(part) for part in first.get("loc", ()))
        return None, f"{location or 'record'}: {first.get('msg', 'invalid')}"

    return event, None


def _score_of(hit: Any, record: dict[str, Any]) -> float:
    for source in (hit, record):
        for key in ("search_score", "score", "relevance"):
            value = getattr(source, key, None) if not isinstance(source, dict) else source.get(key)
            number = _number(value)
            if number is not None:
                return number
    return 0.0


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def _enum(value: Any, enum_class, fallback):
    if isinstance(value, str):
        try:
            return enum_class(value.strip().lower())
        except ValueError:
            return fallback
    return fallback


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _describe(hit: Any) -> str:
    if isinstance(hit, dict):
        return f"dict keys {sorted(hit)}"
    attrs = [name for name in dir(hit) if not name.startswith("_")][:8]
    return f"{type(hit).__name__} attrs {attrs}"
