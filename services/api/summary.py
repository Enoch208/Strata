"""Source-locked summary construction.

PRD section 13: the summary may only use accepted timeline findings, and never
the user's query or unfiltered search results. Sentences are built from the
findings' own wording — which already came from the events — and every sentence
is then independently verified by the source lock before it can be displayed.

Deterministic by choice. A model could phrase this more gracefully, but each
sentence would then need to survive the same verification anyway, and a template
cannot introduce a fact the events do not contain.
"""

from __future__ import annotations

from .comparison.source_lock import lock_sentence
from .schemas.claim_event import ClaimEvent
from .schemas.enums import NOT_ESTABLISHED_TEXT, SupportStatus
from .schemas.finding import TimelineFinding
from .schemas.sentence import SourcedSentence


def build_summary_sentences(
    findings: list[TimelineFinding],
    events: list[ClaimEvent],
    *,
    prefix: str = "sentence",
    start_index: int = 1,
) -> list[SourcedSentence]:
    """Turn accepted findings into verified, source-locked sentences.

    Each finding yields exactly one sentence carrying that finding's supporting
    event IDs. A sentence that fails verification is replaced with the visible
    uncertainty message rather than dropped silently, so the gap stays visible.
    """
    by_id = {event.event_id: event for event in events}
    sentences: list[SourcedSentence] = []

    for position, finding in enumerate(findings, start=start_index):
        supporting = [by_id[event_id] for event_id in finding.event_ids if event_id in by_id]
        sentence_id = f"{prefix}_{position:03d}"

        if not supporting:
            sentences.append(
                SourcedSentence.not_established(
                    sentence_id,
                    f"finding {finding.finding_id} cites events absent from the retrieved evidence",
                )
            )
            continue

        sentences.append(lock_sentence(sentence_id, finding.summary, supporting))

    return sentences


def build_headline(
    findings: list[TimelineFinding],
    events: list[ClaimEvent],
    *,
    sentence_id: str = "sentence_000",
) -> SourcedSentence:
    """A single opening sentence describing the shape of what was found.

    Deliberately counts rather than characterizes: how many moments, across how
    many sources, over what span. Those are facts about the retrieval itself, so
    they cannot misdescribe the footage.
    """
    if not findings or not events:
        return SourcedSentence.not_established(
            sentence_id, "no findings passed the evidence gate"
        )

    cited = {event_id for finding in findings for event_id in finding.event_ids}
    supporting = [event for event in events if event.event_id in cited]
    if not supporting:
        return SourcedSentence.not_established(
            sentence_id, "accepted findings cite no retrieved events"
        )

    videos = {event.video_id for event in supporting}
    dates = sorted(event.source_date for event in supporting)
    span = (
        f"{dates[0].isoformat()}"
        if dates[0] == dates[-1]
        else f"{dates[0].isoformat()} to {dates[-1].isoformat()}"
    )

    text = (
        f"This answer rests on {len(supporting)} timestamped "
        f"{'moment' if len(supporting) == 1 else 'moments'} across "
        f"{len(videos)} source {'video' if len(videos) == 1 else 'videos'}, {span}."
    )

    # Counts describe the retrieval, not the footage, so this sentence is
    # supported by construction — but it still carries its event IDs so the
    # sentence-to-event map covers every displayed sentence.
    return SourcedSentence(
        sentence_id=sentence_id,
        text=text,
        supported_by_event_ids=[event.event_id for event in supporting],
        support_status=SupportStatus.supported,
        is_comparative=False,
    )


def insufficient_evidence_sentence(reason: str) -> SourcedSentence:
    """The honest result when nothing survived the evidence gate."""
    return SourcedSentence.not_established("sentence_001", reason)


def summary_text(sentences: list[SourcedSentence]) -> str:
    """Render only the displayable sentences, for logs and the packet."""
    displayable = [sentence.text for sentence in sentences if sentence.is_displayable]
    return " ".join(displayable) if displayable else NOT_ESTABLISHED_TEXT
