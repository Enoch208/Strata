"""Challenge candidate filtering and outcome classification.

PRD sections 10.7 and 11.8. The challenge pass prefers footage the first answer
never used (CTR-03) without excluding stronger repeated evidence, applies the
same gates as the first pass (CTR-04), and reports the impact as unchanged,
qualified or revised (CTR-05).

The outcome is derived from the accepted relations, never asserted by a model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..schemas.claim_event import ClaimEvent
from ..schemas.challenge import RejectedCandidate
from ..schemas.enums import ChallengeOutcome, FindingLabel, RelationType
from ..schemas.finding import TimelineFinding

#: Relations that overturn the first answer outright.
_REVISING_RELATIONS = frozenset({RelationType.explicitly_corrects, RelationType.revises})
#: Relations that narrow or add limits without replacing the conclusion.
_QUALIFYING_RELATIONS = frozenset(
    {RelationType.contextualizes, RelationType.disputes, RelationType.expands}
)

#: How much a novel source is boosted when ranking challenge candidates.
NOVEL_SOURCE_BOOST = 0.35
CHALLENGE_SCORE_GAP = 0.06


@dataclass(frozen=True)
class ScoredCandidate:
    event: ClaimEvent
    relevance: float
    is_novel_source: bool

    @property
    def score(self) -> float:
        return self.relevance + (NOVEL_SOURCE_BOOST if self.is_novel_source else 0.0)


def rank_candidates(
    candidates: list[tuple[ClaimEvent, float]],
    initial_video_ids: set[str],
) -> list[ScoredCandidate]:
    """Rank challenge candidates, boosting sources the first pass never used.

    A boost rather than a filter: PRD CTR-03 requires preferring unused footage
    *without* excluding stronger repeated evidence, so a highly relevant repeat
    can still outrank a weak novel clip.
    """
    scored = [
        ScoredCandidate(
            event=event,
            relevance=relevance,
            is_novel_source=event.video_id not in initial_video_ids,
        )
        for event, relevance in candidates
    ]
    return sorted(scored, key=lambda c: (-c.score, c.event.source_date, c.event.start))


def reject_reused_events(
    candidates: list[ScoredCandidate],
    initial_event_ids: set[str],
) -> tuple[list[ScoredCandidate], list[RejectedCandidate]]:
    """Drop candidates that are literally the same moments as the first pass.

    Re-showing an identical clip is not counter-evidence. A different moment in
    an already-used *video* is still allowed through.
    """
    kept: list[ScoredCandidate] = []
    rejected: list[RejectedCandidate] = []

    for candidate in candidates:
        if candidate.event.event_id in initial_event_ids:
            rejected.append(
                RejectedCandidate(
                    event_id=candidate.event.event_id,
                    reason="already used as evidence in the initial answer",
                )
            )
            continue
        kept.append(candidate)

    return kept, rejected


def reject_redundant_reasons(
    candidates: list[ScoredCandidate],
    initial_events: list[ClaimEvent],
) -> tuple[list[ScoredCandidate], list[RejectedCandidate]]:
    """Reject a second clip that merely restates an already accepted reason.

    Counter-retrieval is looking for an omitted cause, limit, or correction.
    A different timestamp repeating the same normalized reason is useful
    corroboration, but it is not counter-evidence.
    """
    initial_reason_tokens: dict[str, set[str]] = {}
    for event in initial_events:
        if str(event.claim_type) != "delay_reason":
            continue
        tokens = _reason_tokens(event.normalized_value or event.reason or "")
        if tokens:
            initial_reason_tokens.setdefault(event.subject.strip().lower(), set()).update(
                tokens
            )

    kept: list[ScoredCandidate] = []
    rejected: list[RejectedCandidate] = []
    for candidate in candidates:
        event = candidate.event
        known = initial_reason_tokens.get(event.subject.strip().lower(), set())
        candidate_text = " ".join(
            value
            for value in (
                event.normalized_value,
                event.reason,
                event.claim_text,
            )
            if value
        )
        if known and known & _reason_tokens(candidate_text):
            rejected.append(
                RejectedCandidate(
                    event_id=event.event_id,
                    reason="restates a delay reason already accepted in the initial answer",
                )
            )
            continue
        kept.append(candidate)
    return kept, rejected


def select_relevant_candidates(
    candidates: list[ScoredCandidate],
) -> tuple[list[ScoredCandidate], list[RejectedCandidate]]:
    """Keep the strongest challenge relevance band after novelty boosting."""
    if not candidates:
        return [], []
    best = max(candidate.score for candidate in candidates)
    kept: list[ScoredCandidate] = []
    rejected: list[RejectedCandidate] = []
    for candidate in candidates:
        if candidate.score >= best - CHALLENGE_SCORE_GAP:
            kept.append(candidate)
        else:
            rejected.append(
                RejectedCandidate(
                    event_id=candidate.event.event_id,
                    reason="below the strongest counter-evidence relevance band",
                )
            )
    return kept, rejected


def _reason_tokens(value: str) -> set[str]:
    ignored = {"cause", "delay", "reason", "launch", "artemis", "attempt"}
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower().replace("_", " "))
        if len(token) >= 4 and token not in ignored
    }


def classify_outcome(
    accepted_findings: list[TimelineFinding],
    relation_types: list[RelationType],
) -> ChallengeOutcome:
    """Derive the challenge outcome from what the second pass actually found.

    Conservative by construction: a revision requires an explicit correction or a
    changed comparable value, so prose that merely sounds contradictory produces
    `qualified` at most.
    """
    if not accepted_findings:
        # PRD CTR-06: nothing found is never evidence the conclusion is true.
        return ChallengeOutcome.unchanged

    if any(relation in _REVISING_RELATIONS for relation in relation_types):
        return ChallengeOutcome.revised

    if any(finding.label is FindingLabel.correction for finding in accepted_findings):
        return ChallengeOutcome.revised

    if any(relation in _QUALIFYING_RELATIONS for relation in relation_types):
        return ChallengeOutcome.qualified

    qualifying_labels = {
        FindingLabel.new_information,
        FindingLabel.potential_tension,
        FindingLabel.confirmed_change,
    }
    if any(finding.label in qualifying_labels for finding in accepted_findings):
        return ChallengeOutcome.qualified

    # Findings that only restate the first answer leave it standing.
    return ChallengeOutcome.unchanged


def has_novel_source(
    accepted_events: list[ClaimEvent],
    initial_video_ids: set[str],
) -> bool:
    """True when at least one accepted challenge event comes from an unused video.

    The frozen evaluation uses this as a pass/fail condition: a challenge that
    only recycles first-pass footage fails source-novelty even if it reads well.
    """
    return any(event.video_id not in initial_video_ids for event in accepted_events)
