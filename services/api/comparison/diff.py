"""Deterministic temporal comparison.

PRD sections 11.7 and 13. Structured values are compared first and literally;
nothing here calls a model. A semantic difference may never be promoted to a
confirmed contradiction (guardrail 8), so the strongest label this module will
assign from prose alone is `potential_tension`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from ..schemas.claim_event import ClaimEvent
from ..schemas.enums import ClaimStatus, ClaimType, Confidence, FindingLabel, RelationType
from ..schemas.finding import ClaimRelation, TimelineFinding
from .dedupe import sort_chronologically
from .normalize import normalize_date, normalize_quantity

#: Phrases where a speaker explicitly replaces an earlier statement (PRD section 9).
_CORRECTION_MARKERS: tuple[str, ...] = (
    "i misspoke",
    "that was incorrect",
    "that was wrong",
    "to correct",
    "correction to",
    "a correction",
    "let me correct",
    "i want to correct",
    "earlier i said",
    "i should have said",
)


@dataclass(frozen=True)
class ComparableValue:
    """A structured value two events can be compared on, with its kind."""

    kind: str
    value: object

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ComparableValue):
            return NotImplemented
        return self.kind == other.kind and self.value == other.value

    def __hash__(self) -> int:
        return hash((self.kind, self.value))


@dataclass
class DiffResult:
    """Everything the comparison stage produced, before the evidence gate."""

    findings: list[TimelineFinding] = field(default_factory=list)
    relations: list[ClaimRelation] = field(default_factory=list)


def comparable_value(event: ClaimEvent) -> ComparableValue | None:
    """Reduce an event to a structured value, or `None` if it has none.

    An event with no structured value is never compared deterministically; it
    falls through to the conservative prose path.
    """
    year = event.source_date.year

    if event.claim_type is ClaimType.launch_date:
        parsed = normalize_date(event.normalized_value or event.claim_text, default_year=year)
        return ComparableValue("date", parsed) if parsed else None

    if event.claim_type is ClaimType.measurement:
        quantity = normalize_quantity(event.normalized_value or event.claim_text)
        return ComparableValue("quantity", quantity) if quantity else None

    if event.claim_type is ClaimType.delay_reason and event.normalized_value:
        return ComparableValue("reason", event.normalized_value.strip().lower())

    if event.status is not ClaimStatus.unknown:
        return ComparableValue("status", event.status)

    if event.normalized_value:
        return ComparableValue("token", event.normalized_value.strip().lower())

    return None


def is_explicit_correction(event: ClaimEvent) -> bool:
    """True when the speaker directly replaces an earlier statement."""
    haystack = f"{event.claim_text} {event.reason or ''}".lower()
    return any(marker in haystack for marker in _CORRECTION_MARKERS)


def _group_key(event: ClaimEvent) -> tuple[str, str]:
    return (event.subject.strip().lower(), str(event.claim_type))


def compare_events(events: list[ClaimEvent]) -> DiffResult:
    """Compare every comparable pair and emit findings plus relations.

    Events are grouped by subject and claim type, then compared in chronological
    order. Competing evidence is preserved as separate findings rather than
    merged into one statement (PRD DIF-04).
    """
    result = DiffResult()
    ordered = sort_chronologically(events)

    groups: dict[tuple[str, str], list[ClaimEvent]] = {}
    for event in ordered:
        groups.setdefault(_group_key(event), []).append(event)

    for (subject, claim_type), group in groups.items():
        if len(group) == 1:
            result.findings.append(_new_information(group[0], subject))
            continue

        for index in range(len(group) - 1):
            earlier, later = group[index], group[index + 1]
            comparison = _compare_pair(earlier, later, subject, claim_type, index)
            if comparison is None:
                continue
            finding, relation = comparison
            result.findings.append(finding)
            result.relations.append(relation)

    return result


def _compare_pair(
    earlier: ClaimEvent,
    later: ClaimEvent,
    subject: str,
    claim_type: str,
    index: int,
) -> tuple[TimelineFinding, ClaimRelation] | None:
    """Classify one earlier/later pair. `None` when nothing can be established."""
    pair_id = f"{earlier.event_id}__{later.event_id}"
    event_ids = [earlier.event_id, later.event_id]

    if is_explicit_correction(later):
        return _build(
            pair_id,
            FindingLabel.correction,
            RelationType.explicitly_corrects,
            f"A later source explicitly corrected the earlier {subject} statement",
            f"On {later.source_date} the speaker explicitly replaced the "
            f"{earlier.source_date} statement about {subject}.",
            earlier,
            later,
            Confidence.high,
        )

    earlier_value = comparable_value(earlier)
    later_value = comparable_value(later)

    if earlier_value is None or later_value is None:
        # Prose-only explanations receive a conservative lexical semantic pass.
        # It can identify repetition or potential tension, but never a confirmed
        # change or correction (guardrail 8).
        return _compare_prose(pair_id, earlier, later, subject)

    if earlier_value.kind != later_value.kind:
        return None

    # Reasons and explanations are not mutually exclusive structured states.
    # A second reason can qualify the first without replacing it, which is the
    # central distinction in multi-cause investigations. Treat differing
    # reason tokens conservatively even when extraction normalized both.
    if earlier.claim_type is ClaimType.delay_reason:
        if earlier_value == later_value:
            return _build(
                pair_id,
                FindingLabel.consistent_statement,
                RelationType.repeats,
                f"The stated reason for {subject} stayed the same",
                f"Both the {earlier.source_date} and {later.source_date} sources "
                f"give the same stated reason for {subject}.",
                earlier,
                later,
                Confidence.high,
            )
        return _build(
            pair_id,
            FindingLabel.new_information,
            RelationType.contextualizes,
            f"A later source adds context to the reason for {subject}",
            f"The {earlier.source_date} source states {earlier.claim_text.rstrip('.')}, "
            f"while the {later.source_date} source adds {later.claim_text}",
            earlier,
            later,
            Confidence.medium,
        )

    if earlier_value == later_value:
        return _build(
            pair_id,
            FindingLabel.consistent_statement,
            RelationType.repeats,
            f"The {subject} {earlier_value.kind} stayed the same",
            f"Both the {earlier.source_date} and {later.source_date} sources give "
            f"the same {earlier_value.kind} for {subject}.",
            earlier,
            later,
            Confidence.high,
        )

    return _build(
        pair_id,
        FindingLabel.confirmed_change,
        RelationType.revises,
        f"The {subject} {earlier_value.kind} changed",
        f"The {earlier.source_date} source gives {_render(earlier_value)} for "
        f"{subject}; the {later.source_date} source gives {_render(later_value)}.",
        earlier,
        later,
        Confidence.high,
    )


def _build(
    pair_id: str,
    label: FindingLabel,
    relation_type: RelationType,
    title: str,
    summary: str,
    earlier: ClaimEvent,
    later: ClaimEvent,
    confidence: Confidence,
) -> tuple[TimelineFinding, ClaimRelation]:
    event_ids = [earlier.event_id, later.event_id]
    finding = TimelineFinding(
        finding_id=f"finding_{pair_id}",
        label=label,
        title=title,
        summary=summary,
        event_ids=event_ids,
        confidence=confidence,
    )
    relation = ClaimRelation(
        relation_id=f"rel_{pair_id}",
        from_event_id=earlier.event_id,
        to_event_id=later.event_id,
        relation_type=relation_type,
        explanation=summary,
        supporting_event_ids=event_ids,
        confidence=confidence,
    )
    return finding, relation


def _compare_prose(
    pair_id: str,
    earlier: ClaimEvent,
    later: ClaimEvent,
    subject: str,
) -> tuple[TimelineFinding, ClaimRelation]:
    earlier_text = " ".join(earlier.claim_text.lower().split())
    later_text = " ".join(later.claim_text.lower().split())
    similarity = SequenceMatcher(None, earlier_text, later_text).ratio()

    if similarity >= 0.82:
        return _build(
            pair_id,
            FindingLabel.consistent_statement,
            RelationType.repeats,
            f"The recorded explanation for {subject} stayed consistent",
            f"The {earlier.source_date} and {later.source_date} sources give "
            f"materially similar explanations for {subject}.",
            earlier,
            later,
            Confidence.medium,
        )

    return _build(
        pair_id,
        FindingLabel.potential_tension,
        RelationType.contextualizes,
        f"Two sources give different context for {subject}",
        f"The {earlier.source_date} source states {earlier.claim_text.rstrip('.')}, "
        f"while the {later.source_date} source states {later.claim_text}",
        earlier,
        later,
        Confidence.medium,
    )


def _new_information(event: ClaimEvent, subject: str) -> TimelineFinding:
    """A single event with nothing comparable before it (PRD section 9)."""
    return TimelineFinding(
        finding_id=f"finding_{event.event_id}",
        label=FindingLabel.new_information,
        title=f"New {str(event.claim_type).replace('_', ' ')} about {subject}",
        # Deliberately does not claim any earlier source contradicted this.
        summary=f"On {event.source_date} the archive introduces: {event.claim_text}",
        event_ids=[event.event_id],
        confidence=Confidence.medium,
    )


def _render(value: ComparableValue) -> str:
    if value.kind == "quantity" and isinstance(value.value, tuple):
        magnitude, unit = value.value
        return f"{magnitude:g} {unit}"
    return str(value.value)
