"""Claim-extraction prompt and strict response validation.

PRD sections 11.4 and 22. The model returns JSON only; every record is validated
against `ClaimEvent` and rejected with a logged reason if it fails. Crucially,
timestamps are clamped to the chunk the model was shown, so a hallucinated time
cannot become a citation (guardrail 5).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import ValidationError

from ..schemas.claim_event import ClaimEvent
from ..schemas.enums import Certainty, ClaimStatus, ClaimType
from ..comparison.normalize import normalize_subject
from .chunks import TranscriptChunk, render_for_prompt

_JSON_BLOCK = re.compile(r"\[.*\]|\{.*\}", re.DOTALL)

#: Minimum window kept around an extracted claim so the quotation has context.
MIN_EVENT_DURATION = 4.0

EXTRACTION_INSTRUCTIONS = """\
You extract factual claim events from a transcript of official archive footage.

Return ONLY one JSON object with an "events" array. No prose, no markdown fence,
no explanation. Example shape: {{"events": []}}

Each element of "events" must be an object with exactly these keys:
  "start"            number  - seconds, copied from a timestamp shown below
  "end"              number  - seconds, copied from a timestamp shown below
  "speaker_role"     string or null - e.g. "NASA mission official". Null if unclear.
  "speaker_name"     string or null - only if the transcript states the name.
  "subject"          string  - what the claim is about, e.g. "Artemis I launch"
  "claim_type"       string  - one of: {claim_types}
  "claim_text"       string  - the claim in one sentence, using the speaker's own facts
  "normalized_value" string or null - the comparable value: an ISO date for a launch
                                      date, a short snake_case token for a reason
                                      (e.g. "hydrogen_leak"), a number for a measurement
  "unit"             string or null - unit for a measurement, else null
  "status"           string  - one of: {statuses}
  "reason"           string or null - the stated cause, if one is given
  "certainty"        string  - one of: {certainties}

Hard rules:
- Extract ONLY what is actually said in the transcript below. Never add outside knowledge,
  never infer a cause that is not stated.
- "start" and "end" MUST come from the timestamps shown. Never invent a time.
- If the transcript states no factual claim, return {{"events": []}}.
- Do not judge whether a speaker is honest. Do not use words like lie, false,
  deception, or guilty anywhere.
- Prefer fewer, well-grounded claims over many speculative ones.

Video: {title}
Source organization: {organization}
Publication date: {source_date}
{context_block}
Transcript segments (each line is "[start - end] text"):
{transcript}
"""


@dataclass
class ExtractionOutcome:
    """Valid events plus the auditable reasons any record was rejected."""

    events: list[ClaimEvent] = field(default_factory=list)
    rejections: list[str] = field(default_factory=list)


def build_prompt(
    chunk: TranscriptChunk,
    *,
    title: str,
    organization: str,
    source_date: date,
    context: str | None = None,
) -> str:
    """Render the extraction prompt for one transcript chunk."""
    context_block = f"Nearby on-screen text and scene context:\n{context}\n" if context else ""
    return EXTRACTION_INSTRUCTIONS.format(
        claim_types=", ".join(str(value) for value in ClaimType),
        statuses=", ".join(str(value) for value in ClaimStatus),
        certainties=", ".join(str(value) for value in Certainty),
        title=title,
        organization=organization,
        source_date=source_date.isoformat(),
        context_block=context_block,
        transcript=render_for_prompt(chunk),
    )


def parse_response(raw: Any) -> tuple[list[dict[str, Any]], str | None]:
    """Coerce a sandbox-model response into a list of record dicts.

    Returns `(records, error)`. A response that is not JSON yields an error
    rather than a partial guess.
    """
    if isinstance(raw, list):
        return [row for row in raw if isinstance(row, dict)], None
    if isinstance(raw, dict):
        for key in ("events", "claims", "results", "data"):
            value = raw.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)], None
        if "output" in raw:
            output = raw["output"]
            if isinstance(output, dict) and isinstance(output.get("error"), str):
                return [], f"model returned an error: {output['error']}"
            return parse_response(output)
        return [raw], None

    if not isinstance(raw, str):
        return [], f"unexpected response type {type(raw).__name__}"

    match = _JSON_BLOCK.search(raw)
    if not match:
        return [], "response contained no JSON array or object"

    try:
        return parse_response(json.loads(match.group(0)))
    except json.JSONDecodeError as error:
        return [], f"invalid JSON: {error}"


def validate_records(
    records: list[dict[str, Any]],
    chunk: TranscriptChunk,
    *,
    video_id: str,
    source_date: date,
    source_organization: str,
    extraction_model: str,
    artifact_ids: list[str] | None = None,
) -> ExtractionOutcome:
    """Validate model records into `ClaimEvent`s, rejecting anything unsound."""
    outcome = ExtractionOutcome()

    for position, record in enumerate(records):
        event_id = f"evt_{video_id}_{chunk.index:03d}_{position:02d}"
        window = _clamp_window(record, chunk)
        if window is None:
            outcome.rejections.append(
                f"{event_id}: timestamps {record.get('start')!r}-{record.get('end')!r} "
                f"are outside the chunk window [{chunk.start:.2f}, {chunk.end:.2f}]"
            )
            continue

        start, end = window
        try:
            outcome.events.append(
                ClaimEvent(
                    event_id=event_id,
                    video_id=video_id,
                    start=start,
                    end=end,
                    source_date=source_date,
                    speaker_name=_clean(record.get("speaker_name")),
                    speaker_role=_clean(record.get("speaker_role")),
                    subject=normalize_subject(_clean(record.get("subject")) or ""),
                    claim_type=_enum(record.get("claim_type"), ClaimType, ClaimType.other),
                    claim_text=_clean(record.get("claim_text")) or "",
                    normalized_value=_clean(record.get("normalized_value")),
                    unit=_clean(record.get("unit")),
                    status=_enum(record.get("status"), ClaimStatus, ClaimStatus.unknown),
                    reason=_clean(record.get("reason")),
                    certainty=_enum(record.get("certainty"), Certainty, Certainty.uncertain),
                    source_artifact_ids=artifact_ids or [],
                    extraction_model=extraction_model,
                    source_organization=source_organization,
                )
            )
        except ValidationError as error:
            outcome.rejections.append(f"{event_id}: {_first_error(error)}")

    return outcome


def _clamp_window(record: dict[str, Any], chunk: TranscriptChunk) -> tuple[float, float] | None:
    """Confine a model-reported window to the chunk it was shown.

    A window with no overlap at all is rejected outright — that is a fabricated
    timestamp, not a rounding error.
    """
    start, end = record.get("start"), record.get("end")
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
        return None

    start, end = float(start), float(end)
    if end <= start:
        return None
    if end <= chunk.start or start >= chunk.end:
        return None

    start = max(start, chunk.start)
    end = min(end, chunk.end)
    if end - start < MIN_EVENT_DURATION:
        end = min(start + MIN_EVENT_DURATION, chunk.end)
        start = max(end - MIN_EVENT_DURATION, chunk.start)
    return (start, end) if end > start else None


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _enum(value: Any, enum_class, fallback):
    if isinstance(value, str):
        try:
            return enum_class(value.strip().lower())
        except ValueError:
            return fallback
    return fallback


def _first_error(error: ValidationError) -> str:
    first = error.errors()[0]
    location = ".".join(str(part) for part in first.get("loc", ()))
    return f"{location or 'record'}: {first.get('msg', 'invalid')}"
