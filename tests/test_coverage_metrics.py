"""Aggregation of the published evidence-coverage metrics.

These numbers appear in the README comparison table, so the arithmetic behind
them is pinned here.
"""

from __future__ import annotations

import json

from pipeline.coverage_metrics import COVERAGE_PATH, CaseObservation, aggregate


def observation(
    case_id: str = "case",
    *,
    findings: int = 0,
    playable: int = 0,
    sentences: int = 0,
    mapped: int = 0,
    challenge_ran: bool = False,
    novel: bool = False,
) -> CaseObservation:
    return CaseObservation(
        case_id=case_id,
        state="complete",
        findings=findings,
        findings_with_playable_evidence=playable,
        displayed_sentences=sentences,
        displayed_sentences_with_events=mapped,
        challenge_ran=challenge_ran,
        challenge_found_novel_source=novel,
    )


class TestAggregate:
    def test_sums_across_cases(self) -> None:
        metrics = aggregate(
            [
                observation("a", findings=3, playable=3, sentences=4, mapped=4),
                observation("b", findings=2, playable=2, sentences=1, mapped=1),
            ]
        )

        assert metrics["playable_citation_coverage"].numerator == 5
        assert metrics["playable_citation_coverage"].denominator == 5
        assert metrics["auditable_sentence_mapping"].numerator == 5
        assert metrics["auditable_sentence_mapping"].denominator == 5

    def test_an_unplayable_finding_lowers_coverage(self) -> None:
        metrics = aggregate([observation("a", findings=4, playable=3)])

        assert metrics["playable_citation_coverage"].render() == "3 / 4 (75.0%)"

    def test_an_unmapped_sentence_lowers_mapping(self) -> None:
        metrics = aggregate([observation("a", sentences=4, mapped=2)])

        assert metrics["auditable_sentence_mapping"].render() == "2 / 4 (50.0%)"

    def test_only_cases_that_ran_a_challenge_count_toward_novelty(self) -> None:
        # A case whose first pass found insufficient evidence has no conclusion
        # to challenge, so it must not be scored as a novelty failure.
        metrics = aggregate(
            [
                observation("ran", challenge_ran=True, novel=True),
                observation("not_applicable", challenge_ran=False),
            ]
        )

        assert metrics["challenge_source_novelty"].render() == "1 / 1 (100.0%)"

    def test_a_challenge_without_a_novel_source_is_counted_as_a_miss(self) -> None:
        metrics = aggregate([observation("ran", challenge_ran=True, novel=False)])

        assert metrics["challenge_source_novelty"].numerator == 0
        assert metrics["challenge_source_novelty"].denominator == 1

    def test_empty_denominator_renders_as_not_available(self) -> None:
        # Never render a 0/0 metric as 0%, which would read as a real failure.
        metrics = aggregate([observation("a")])

        assert metrics["playable_citation_coverage"].render() == "0 / 0 (n/a)"
        assert metrics["playable_citation_coverage"].percentage is None


class TestPublishedCoverageArtifact:
    def test_committed_metrics_are_internally_consistent(self) -> None:
        payload = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
        strata = payload["arms"]["strata"]

        assert strata["basis"] == "measured"
        for name in (
            "playable_citation_coverage",
            "auditable_sentence_mapping",
            "challenge_source_novelty",
        ):
            metric = strata[name]
            assert metric["numerator"] <= metric["denominator"]

    def test_naive_zeros_are_labelled_structural_not_measured(self) -> None:
        # The naive arm's zeros follow from its design; presenting them as an
        # observed run would overstate what was actually tested.
        payload = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))

        assert payload["arms"]["naive"]["basis"] == "structural"
        assert "not an" in payload["arms"]["naive"]["note"]

    def test_observations_cover_the_whole_frozen_case_set(self) -> None:
        payload = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))

        assert payload["case_count"] == 12
        assert len(payload["observations"]) == 12
