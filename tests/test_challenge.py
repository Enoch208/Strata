"""Counter-query generation, challenge filtering and outcome classification.

PRD section 19 required tests, including the seeded source-novelty assertion.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from services.api.retrieval.challenge_filter import (
    classify_outcome,
    has_novel_source,
    rank_candidates,
    reject_reused_events,
)
from services.api.retrieval.counter_queries import (
    MAX_COUNTER_QUERIES,
    MIN_COUNTER_QUERIES,
    generate_counter_queries,
)
from services.api.schemas.challenge import EMPTY_CHALLENGE_TEXT, ChallengeResult
from services.api.schemas.enums import (
    ChallengeOutcome,
    ClaimType,
    Confidence,
    FindingLabel,
    RelationType,
)
from services.api.schemas.finding import TimelineFinding

from .factories import make_event

LEAK_EVENT = make_event(
    "evt_leak",
    video_id="vid_sep03",
    source_date="2022-09-03",
    claim_type=ClaimType.delay_reason,
    normalized_value="hydrogen_leak",
)
ROLLBACK_EVENT = make_event(
    "evt_rollback",
    video_id="vid_sep30",
    source_date="2022-09-30",
    claim_type=ClaimType.status_update,
    normalized_value="hurricane_rollback",
)

LEAK_FINDING = TimelineFinding(
    finding_id="finding_leak",
    label=FindingLabel.new_information,
    title="A hydrogen leak stopped the 3 September attempt",
    summary="The attempt was waved off after a liquid-hydrogen leak.",
    event_ids=["evt_leak"],
    confidence=Confidence.high,
)


class TestCounterQueryGeneration:
    def test_produces_between_three_and_five_queries(self) -> None:
        queries = generate_counter_queries("Why did it slip?", [LEAK_FINDING], [LEAK_EVENT])

        assert MIN_COUNTER_QUERIES <= len(queries) <= MAX_COUNTER_QUERIES

    def test_queries_are_distinct(self) -> None:
        queries = generate_counter_queries("Why did it slip?", [LEAK_FINDING], [LEAK_EVENT])
        assert len(set(queries)) == len(queries)

    def test_probes_for_an_omitted_alternative_cause(self) -> None:
        # The seeded Artemis fixture turns on finding a cause the first pass missed.
        queries = generate_counter_queries("Why did it slip?", [LEAK_FINDING], [LEAK_EVENT])
        joined = " ".join(queries).lower()

        assert "different or additional reason" in joined
        assert "hydrogen leak" in joined

    def test_probes_for_consistency_not_only_for_contradictions(self) -> None:
        # A challenge that only looks for conflict is just confirmation bias
        # pointed the other way.
        queries = generate_counter_queries("Why did it slip?", [LEAK_FINDING], [LEAK_EVENT])
        assert any("stayed consistent" in query for query in queries)

    def test_still_generates_queries_with_no_findings(self) -> None:
        queries = generate_counter_queries("Why did it slip?", [], [])
        assert len(queries) >= MIN_COUNTER_QUERIES

    def test_is_reproducible(self) -> None:
        first = generate_counter_queries("Why did it slip?", [LEAK_FINDING], [LEAK_EVENT])
        second = generate_counter_queries("Why did it slip?", [LEAK_FINDING], [LEAK_EVENT])
        assert first == second


class TestRankCandidates:
    def test_novel_sources_are_boosted(self) -> None:
        ranked = rank_candidates(
            [(LEAK_EVENT, 0.80), (ROLLBACK_EVENT, 0.60)],
            initial_video_ids={"vid_sep03"},
        )

        # 0.60 + 0.35 boost beats 0.80 from an already-used source.
        assert ranked[0].event.event_id == "evt_rollback"
        assert ranked[0].is_novel_source is True

    def test_a_much_stronger_repeat_still_wins(self) -> None:
        # PRD CTR-03: prefer unused footage without excluding stronger evidence.
        ranked = rank_candidates(
            [(LEAK_EVENT, 0.99), (ROLLBACK_EVENT, 0.10)],
            initial_video_ids={"vid_sep03"},
        )

        assert ranked[0].event.event_id == "evt_leak"

    def test_novelty_is_computed_against_the_first_pass_videos(self) -> None:
        ranked = rank_candidates([(ROLLBACK_EVENT, 0.5)], initial_video_ids={"vid_sep30"})
        assert ranked[0].is_novel_source is False


class TestRejectReusedEvents:
    def test_identical_moments_are_rejected_with_a_reason(self) -> None:
        ranked = rank_candidates([(LEAK_EVENT, 0.9), (ROLLBACK_EVENT, 0.8)], set())

        kept, rejected = reject_reused_events(ranked, initial_event_ids={"evt_leak"})

        assert [c.event.event_id for c in kept] == ["evt_rollback"]
        assert rejected[0].event_id == "evt_leak"
        assert "initial answer" in rejected[0].reason

    def test_a_new_moment_in_a_used_video_is_kept(self) -> None:
        other_moment = make_event("evt_leak_2", video_id="vid_sep03", start=400.0)
        ranked = rank_candidates([(other_moment, 0.9)], set())

        kept, rejected = reject_reused_events(ranked, initial_event_ids={"evt_leak"})

        assert [c.event.event_id for c in kept] == ["evt_leak_2"]
        assert rejected == []


class TestClassifyOutcome:
    def test_no_findings_is_unchanged(self) -> None:
        assert classify_outcome([], []) is ChallengeOutcome.unchanged

    def test_contextualizing_evidence_qualifies(self) -> None:
        # The correct seeded Artemis outcome.
        outcome = classify_outcome([LEAK_FINDING], [RelationType.contextualizes])
        assert outcome is ChallengeOutcome.qualified

    def test_explicit_correction_revises(self) -> None:
        outcome = classify_outcome([LEAK_FINDING], [RelationType.explicitly_corrects])
        assert outcome is ChallengeOutcome.revised

    def test_changed_comparable_value_revises(self) -> None:
        assert classify_outcome([LEAK_FINDING], [RelationType.revises]) is ChallengeOutcome.revised

    def test_only_repeated_evidence_leaves_the_answer_unchanged(self) -> None:
        consistent = TimelineFinding(
            finding_id="finding_same",
            label=FindingLabel.consistent_statement,
            title="The account stayed the same",
            summary="Both sources give the same account.",
            event_ids=["evt_leak", "evt_rollback"],
            confidence=Confidence.high,
        )

        outcome = classify_outcome([consistent], [RelationType.repeats])

        assert outcome is ChallengeOutcome.unchanged

    def test_new_information_qualifies_rather_than_revises(self) -> None:
        # Guardrail 8: new context must not be promoted to a contradiction.
        assert classify_outcome([LEAK_FINDING], []) is ChallengeOutcome.qualified


class TestSourceNovelty:
    def test_detects_an_accepted_event_from_an_unused_video(self) -> None:
        # PRD CTR-07, the seeded fixture's pass condition.
        assert has_novel_source([ROLLBACK_EVENT], {"vid_sep03"}) is True

    def test_challenge_reusing_only_first_pass_videos_has_no_novel_source(self) -> None:
        assert has_novel_source([LEAK_EVENT], {"vid_sep03"}) is False

    def test_empty_acceptance_has_no_novel_source(self) -> None:
        assert has_novel_source([], {"vid_sep03"}) is False


class TestChallengeResultSchema:
    def make(self, **overrides) -> dict:
        payload = {
            "challenge_id": "challenge_001",
            "counter_queries": ["a", "b", "c"],
            "accepted_finding_ids": ["finding_rollback"],
            "initial_accepted_video_ids": ["vid_sep03"],
            "challenge_accepted_video_ids": ["vid_sep30"],
            "outcome": ChallengeOutcome.qualified,
            "searched_at": datetime.now(UTC),
        }
        payload.update(overrides)
        return payload

    def test_novel_video_ids_are_derived_from_the_two_sets(self) -> None:
        result = ChallengeResult(**self.make())

        assert result.novel_accepted_video_ids == ["vid_sep30"]
        assert result.found_counter_evidence is True

    def test_reused_source_yields_no_novel_video_ids(self) -> None:
        result = ChallengeResult(
            **self.make(challenge_accepted_video_ids=["vid_sep03"])
        )

        assert result.novel_accepted_video_ids == []

    def test_empty_challenge_cannot_claim_a_qualification(self) -> None:
        # PRD CTR-06.
        with pytest.raises(ValidationError):
            ChallengeResult(**self.make(accepted_finding_ids=[]))

    def test_empty_challenge_may_report_unchanged(self) -> None:
        result = ChallengeResult(
            **self.make(
                accepted_finding_ids=[],
                challenge_accepted_video_ids=[],
                outcome=ChallengeOutcome.unchanged,
            )
        )

        assert result.found_counter_evidence is False

    def test_counter_query_count_is_enforced(self) -> None:
        with pytest.raises(ValidationError):
            ChallengeResult(**self.make(counter_queries=["only one", "two"]))
        with pytest.raises(ValidationError):
            ChallengeResult(**self.make(counter_queries=["1", "2", "3", "4", "5", "6"]))

    def test_empty_challenge_copy_never_claims_proof(self) -> None:
        assert "does not prove" in EMPTY_CHALLENGE_TEXT
        assert "true" in EMPTY_CHALLENGE_TEXT
