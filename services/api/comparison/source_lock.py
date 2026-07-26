"""Sentence-level source locking.

PRD sections 7.5 and 13. Every factual sentence the product displays must name
the event IDs supporting it, and every material fact inside that sentence must
actually appear in those events. A sentence that fails is rewritten or replaced
with the visible uncertainty message — never quietly displayed.

This is the last defence against a fluent summary drifting away from footage, so
verification is deterministic: no model is consulted to check a model's output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..schemas.claim_event import ClaimEvent
from ..schemas.enums import SupportStatus
from ..schemas.sentence import SourcedSentence
from .normalize import normalize_date, normalize_quantity, normalize_status

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'])")

#: Wording that asserts a relationship between two moments (PRD section 13).
_COMPARATIVE_MARKERS: tuple[str, ...] = (
    "changed", "change", "earlier", "later", "while", "whereas", "however",
    "revised", "corrected", "moved from", "shifted", "no longer", "previously",
    "subsequently",
)

#: Words that open a sentence and would otherwise look like proper nouns.
_SENTENCE_OPENERS = frozenset(
    {"the", "a", "an", "on", "in", "at", "by", "later", "earlier", "both",
     "this", "that", "these", "those", "it", "they", "nasa's"}
)

_PROPER_NOUN = re.compile(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b")
_MONTHS = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b", re.IGNORECASE
)


@dataclass(frozen=True)
class MaterialFacts:
    """The checkable content of one sentence."""

    dates: frozenset[str]
    quantities: frozenset[tuple[float, str]]
    statuses: frozenset[str]
    proper_nouns: frozenset[str]

    def __bool__(self) -> bool:
        return bool(self.dates or self.quantities or self.statuses or self.proper_nouns)


def split_sentences(text: str) -> list[str]:
    """Split a generated summary into individual factual sentences."""
    stripped = text.strip()
    if not stripped:
        return []
    return [part.strip() for part in _SENTENCE_SPLIT.split(stripped) if part.strip()]


def is_comparative(sentence: str) -> bool:
    """True when a sentence asserts a relationship between two moments."""
    lowered = sentence.lower()
    return any(re.search(rf"\b{re.escape(marker)}\b", lowered) for marker in _COMPARATIVE_MARKERS)


def extract_material_facts(text: str, *, default_year: int | None = None) -> MaterialFacts:
    """Pull out the facts a sentence asserts that must be checkable against events."""
    dates: set[str] = set()
    parsed = normalize_date(text, default_year=default_year)
    if parsed:
        dates.add(parsed.isoformat())
    # A bare month reference is still material even without a resolvable day.
    dates.update(month.group(0).lower()[:3] for month in _MONTHS.finditer(text))

    quantity = normalize_quantity(text)
    quantities = {quantity} if quantity else set()

    status = normalize_status(text)
    statuses = {str(status)} if str(status) != "unknown" else set()

    proper_nouns = {
        match.group(0)
        for match in _PROPER_NOUN.finditer(text)
        if match.group(0).lower() not in _SENTENCE_OPENERS
        and not _MONTHS.fullmatch(match.group(0))
    }

    return MaterialFacts(
        dates=frozenset(dates),
        quantities=frozenset(quantities),
        statuses=frozenset(statuses),
        proper_nouns=frozenset(proper_nouns),
    )


def _event_haystack(events: list[ClaimEvent]) -> str:
    """Everything the supporting events actually say, as one searchable blob."""
    parts: list[str] = []
    for event in events:
        parts.extend(
            [
                event.claim_text,
                event.reason or "",
                event.normalized_value or "",
                event.subject,
                event.speaker_role or "",
                event.speaker_name or "",
                str(event.status),
                event.source_date.isoformat(),
                event.source_date.strftime("%B %d"),
            ]
        )
    return " ".join(parts)


def unsupported_facts(sentence: str, events: list[ClaimEvent]) -> list[str]:
    """Material facts in `sentence` that no supporting event contains."""
    if not events:
        return ["no supporting events"]

    haystack = _event_haystack(events)
    lowered = haystack.lower()
    default_year = min(event.source_date.year for event in events)
    facts = extract_material_facts(sentence, default_year=default_year)
    evidence = extract_material_facts(haystack, default_year=default_year)

    missing: list[str] = []

    for iso in facts.dates:
        if iso in lowered or iso in evidence.dates:
            continue
        missing.append(f"date '{iso}'")

    for magnitude, unit in facts.quantities:
        if (magnitude, unit) not in evidence.quantities:
            missing.append(f"quantity '{magnitude:g} {unit}'")

    for status in facts.statuses:
        if status not in evidence.statuses and status not in lowered:
            missing.append(f"status '{status}'")

    for noun in facts.proper_nouns:
        if noun.lower() not in lowered:
            missing.append(f"name '{noun}'")

    return missing


def lock_sentence(
    sentence_id: str,
    text: str,
    supporting_events: list[ClaimEvent],
) -> SourcedSentence:
    """Verify one sentence against its supporting events and label the result."""
    comparative = is_comparative(text)
    event_ids = [event.event_id for event in supporting_events]

    if not supporting_events:
        return SourcedSentence.not_established(sentence_id, "no supporting events were accepted")

    if comparative and len(set(event_ids)) < 2:
        return SourcedSentence.not_established(
            sentence_id,
            f"comparative sentence cites {len(set(event_ids))} event(s); at least two are required",
        )

    missing = unsupported_facts(text, supporting_events)
    if missing:
        return SourcedSentence.not_established(
            sentence_id,
            "supporting events do not contain: " + ", ".join(sorted(missing)),
        )

    return SourcedSentence(
        sentence_id=sentence_id,
        text=text,
        supported_by_event_ids=event_ids,
        support_status=SupportStatus.supported,
        is_comparative=comparative,
    )


def lock_summary(
    summary: str,
    supporting_events: list[ClaimEvent],
    *,
    prefix: str = "sentence",
) -> list[SourcedSentence]:
    """Split a generated summary and source-lock each sentence independently."""
    return [
        lock_sentence(f"{prefix}_{index:03d}", sentence, supporting_events)
        for index, sentence in enumerate(split_sentences(summary), start=1)
    ]
