"""Deterministic diff rules and duplicate removal (PRD section 19)."""

from services.api.comparison.dedupe import dedupe_events, drop_duplicate_shots, sort_chronologically
from services.api.comparison.diff import compare_events, is_explicit_correction
from services.api.schemas.enums import (
    Certainty,
    ClaimStatus,
    ClaimType,
    FindingLabel,
    RelationType,
)

from .factories import make_event


class TestDeterministicDiff:
    def test_changed_launch_date_is_a_confirmed_change(self) -> None:
        events = [
            make_event(
                "evt_1",
                source_date="2022-09-02",
                claim_type=ClaimType.launch_date,
                normalized_value="2022-09-03",
            ),
            make_event(
                "evt_2",
                video_id="vid_b",
                source_date="2022-09-08",
                claim_type=ClaimType.launch_date,
                normalized_value="2022-09-23",
            ),
        ]

        result = compare_events(events)

        assert [f.label for f in result.findings] == [FindingLabel.confirmed_change]
        assert result.findings[0].event_ids == ["evt_1", "evt_2"]
        assert [r.relation_type for r in result.relations] == [RelationType.revises]

    def test_identical_value_is_a_consistent_statement(self) -> None:
        events = [
            make_event(
                "evt_1",
                source_date="2022-09-02",
                claim_type=ClaimType.launch_date,
                normalized_value="2022-09-03",
            ),
            make_event(
                "evt_2",
                video_id="vid_b",
                source_date="2022-09-08",
                claim_type=ClaimType.launch_date,
                normalized_value="2022-09-03",
            ),
        ]

        result = compare_events(events)

        assert result.findings[0].label is FindingLabel.consistent_statement
        assert result.relations[0].relation_type is RelationType.repeats

    def test_explicit_correction_outranks_a_value_change(self) -> None:
        events = [
            make_event(
                "evt_1",
                source_date="2022-09-02",
                claim_type=ClaimType.launch_date,
                normalized_value="2022-09-03",
            ),
            make_event(
                "evt_2",
                video_id="vid_b",
                source_date="2022-09-08",
                claim_type=ClaimType.launch_date,
                normalized_value="2022-09-23",
                claim_text="Earlier I said the third; I should have said the twenty-third.",
            ),
        ]

        result = compare_events(events)

        assert result.findings[0].label is FindingLabel.correction
        assert result.relations[0].relation_type is RelationType.explicitly_corrects

    def test_prose_only_difference_never_becomes_a_confirmed_change(self) -> None:
        # Guardrail 8: semantic differences may not be classified as contradictions.
        events = [
            make_event(
                "evt_1",
                source_date="2022-09-03",
                claim_type=ClaimType.delay_reason,
                claim_text="A hydrogen leak stopped the attempt.",
            ),
            make_event(
                "evt_2",
                video_id="vid_b",
                source_date="2022-09-30",
                claim_type=ClaimType.delay_reason,
                claim_text="Weather predictions drove the rollback decision.",
            ),
        ]

        result = compare_events(events)

        labels = {f.label for f in result.findings}
        assert FindingLabel.confirmed_change not in labels
        assert labels == {FindingLabel.potential_tension}
        assert result.relations[0].relation_type is RelationType.contextualizes

    def test_different_normalized_reasons_contextualize_instead_of_revise(self) -> None:
        events = [
            make_event(
                "evt_leak",
                source_date="2022-09-03",
                claim_type=ClaimType.delay_reason,
                claim_text="A hydrogen leak stopped the attempt.",
                normalized_value="hydrogen_leak",
                status=ClaimStatus.scrubbed,
            ),
            make_event(
                "evt_weather",
                video_id="vid_b",
                source_date="2022-09-30",
                claim_type=ClaimType.delay_reason,
                claim_text="Weather predictions drove a separate rollback.",
                normalized_value="hurricane_rollback",
                status=ClaimStatus.rolled_back,
            ),
        ]

        result = compare_events(events)

        assert result.findings[0].label is FindingLabel.new_information
        assert result.relations[0].relation_type is RelationType.contextualizes

    def test_single_event_group_is_new_information(self) -> None:
        result = compare_events([make_event("evt_1", status=ClaimStatus.scrubbed)])

        assert result.findings[0].label is FindingLabel.new_information
        assert result.findings[0].event_ids == ["evt_1"]

    def test_comparative_findings_always_carry_two_events(self) -> None:
        # PRD DIF-03, enforced by the schema; this guards the diff never violating it.
        events = [
            make_event("evt_1", source_date="2022-09-02", status=ClaimStatus.scheduled),
            make_event("evt_2", video_id="vid_b", source_date="2022-09-03", status=ClaimStatus.scrubbed),
        ]

        result = compare_events(events)

        for finding in result.findings:
            if finding.label is FindingLabel.new_information:
                continue
            assert len(set(finding.event_ids)) >= 2


class TestExplicitCorrection:
    def test_detects_correction_markers(self) -> None:
        event = make_event("evt_1", claim_text="A correction to what I said earlier.")
        assert is_explicit_correction(event) is True

    def test_ordinary_statement_is_not_a_correction(self) -> None:
        event = make_event("evt_1", claim_text="The team is reviewing the seal.")
        assert is_explicit_correction(event) is False


class TestDedupe:
    def test_overlapping_identical_claims_collapse(self) -> None:
        events = [
            make_event("evt_1", start=10.0, end=25.0, normalized_value="hydrogen_leak"),
            make_event("evt_2", start=12.0, end=24.0, normalized_value="hydrogen_leak"),
        ]

        kept = dedupe_events(events)

        assert len(kept) == 1

    def test_more_certain_event_survives(self) -> None:
        events = [
            make_event(
                "evt_uncertain",
                start=10.0,
                end=25.0,
                normalized_value="hydrogen_leak",
                certainty=Certainty.uncertain,
            ),
            make_event(
                "evt_explicit",
                start=12.0,
                end=24.0,
                normalized_value="hydrogen_leak",
                certainty=Certainty.explicit,
            ),
        ]

        kept = dedupe_events(events)

        assert [e.event_id for e in kept] == ["evt_explicit"]

    def test_same_claim_at_a_different_moment_is_kept(self) -> None:
        # Repetition at a distinct moment is itself evidence.
        events = [
            make_event("evt_1", start=10.0, end=25.0, normalized_value="hydrogen_leak"),
            make_event("evt_2", start=400.0, end=415.0, normalized_value="hydrogen_leak"),
        ]

        assert len(dedupe_events(events)) == 2

    def test_same_claim_in_a_different_video_is_kept(self) -> None:
        events = [
            make_event("evt_1", video_id="vid_a", normalized_value="hydrogen_leak"),
            make_event("evt_2", video_id="vid_b", normalized_value="hydrogen_leak"),
        ]

        assert len(dedupe_events(events)) == 2

    def test_output_is_chronological(self) -> None:
        events = [
            make_event("evt_late", source_date="2022-11-16", normalized_value="a"),
            make_event("evt_early", source_date="2022-09-02", normalized_value="b"),
        ]

        assert [e.event_id for e in dedupe_events(events)] == ["evt_early", "evt_late"]


class TestReelShotDedupe:
    def test_overlapping_shots_are_dropped(self) -> None:
        # PRD REL-05: overlapping shots replay the same footage rather than add evidence.
        events = [
            make_event("evt_1", start=10.0, end=30.0, normalized_value="a"),
            make_event("evt_2", start=20.0, end=40.0, normalized_value="b"),
        ]

        assert [e.event_id for e in drop_duplicate_shots(events)] == ["evt_1"]

    def test_distinct_shots_survive_in_order(self) -> None:
        events = [
            make_event("evt_2", start=100.0, end=120.0, source_date="2022-09-30"),
            make_event("evt_1", start=10.0, end=30.0, source_date="2022-09-03"),
        ]

        assert [e.event_id for e in drop_duplicate_shots(events)] == ["evt_1", "evt_2"]


class TestChronologicalOrder:
    def test_sorts_by_date_then_start(self) -> None:
        events = [
            make_event("evt_b", source_date="2022-09-03", start=200.0),
            make_event("evt_a", source_date="2022-09-03", start=10.0),
            make_event("evt_c", source_date="2022-11-16", start=5.0),
        ]

        assert [e.event_id for e in sort_chronologically(events)] == ["evt_a", "evt_b", "evt_c"]
