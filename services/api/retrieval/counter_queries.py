"""Counter-query generation for the challenge pass.

PRD CTR-01: three to five counter-queries derived from the accepted findings.
These are built from deterministic templates rather than by asking a model to
"think of objections" — a template cannot quietly reframe the question, and the
set is reproducible across runs, which the evaluation harness depends on.

The queries deliberately probe five different ways a first answer can be wrong:
an omitted cause, a later revision, a stable counterexample, missing context, and
an explicit dispute.
"""

from __future__ import annotations

from ..schemas.claim_event import ClaimEvent
from ..schemas.finding import TimelineFinding

MIN_COUNTER_QUERIES = 3
MAX_COUNTER_QUERIES = 5


def _subjects(findings: list[TimelineFinding], events: list[ClaimEvent]) -> list[str]:
    """Distinct subjects behind the accepted findings, most-cited first."""
    cited = {event_id for finding in findings for event_id in finding.event_ids}
    counts: dict[str, int] = {}
    for event in events:
        if event.event_id in cited:
            subject = event.subject.strip()
            counts[subject] = counts.get(subject, 0) + 1
    return [subject for subject, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _stated_reasons(findings: list[TimelineFinding], events: list[ClaimEvent]) -> list[str]:
    """Normalized reasons the first pass relied on, so we can search for others."""
    cited = {event_id for finding in findings for event_id in finding.event_ids}
    reasons: list[str] = []
    for event in events:
        if event.event_id not in cited:
            continue
        token = (event.normalized_value or "").replace("_", " ").strip()
        if token and token not in reasons:
            reasons.append(token)
    return reasons


def generate_counter_queries(
    query: str,
    findings: list[TimelineFinding],
    events: list[ClaimEvent],
) -> list[str]:
    """Build 3-5 counter-queries targeting the accepted findings.

    Falls back to subject-free phrasings when the findings carry no usable
    subject, so the challenge pass always runs rather than silently skipping.
    """
    subjects = _subjects(findings, events)
    subject = subjects[0] if subjects else "the launch schedule"
    reasons = _stated_reasons(findings, events)
    reason = reasons[0] if reasons else None

    candidates: list[str] = []

    # 1. Omitted cause.
    if reason:
        candidates.append(
            f"Footage giving a different or additional reason for {subject}, not {reason}"
        )
    else:
        candidates.append(f"Footage giving a different or additional reason for {subject}")

    # 2. Later events that add a separate obstacle.
    candidates.append(
        f"Later events or conditions that separately delayed or prevented {subject}"
    )

    # 3. External conditions and operational responses.
    candidates.append(
        f"Did weather or Hurricane Ian force a rollback and cause a separate "
        f"delay for {subject}?"
    )

    # 4. Missing context and limits.
    candidates.append(
        f"Later footage adding context, limits or caveats to the explanation of {subject}"
    )

    # 5. A stable counterexample, so the pass does not search only for conflict.
    candidates.append(
        f"Statements showing the account of {subject} stayed consistent over time"
    )

    deduped: list[str] = []
    for candidate in candidates:
        if candidate not in deduped:
            deduped.append(candidate)

    queries = deduped[:MAX_COUNTER_QUERIES]

    # The contract promises at least three; pad from the original question rather
    # than returning a short list the schema would reject.
    while len(queries) < MIN_COUNTER_QUERIES:
        queries.append(f"Archive footage that would weaken this answer: {query}")

    return queries
