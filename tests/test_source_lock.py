"""Sentence source-lock rejection and rewrite (PRD section 19, required tests)."""

from services.api.comparison.source_lock import (
    is_comparative,
    lock_sentence,
    lock_summary,
    split_sentences,
    unsupported_facts,
)
from services.api.schemas.enums import NOT_ESTABLISHED_TEXT, ClaimStatus, ClaimType, SupportStatus

from .factories import make_event

LEAK_EVENT = make_event(
    "evt_leak",
    video_id="vid_sep03",
    source_date="2022-09-03",
    claim_type=ClaimType.delay_reason,
    claim_text="NASA waived off the attempt after a liquid-hydrogen leak during propellant loading.",
    reason="A liquid-hydrogen leak occurred during propellant loading.",
    normalized_value="hydrogen_leak",
    status=ClaimStatus.scrubbed,
)

ROLLBACK_EVENT = make_event(
    "evt_rollback",
    video_id="vid_sep30",
    source_date="2022-09-30",
    claim_type=ClaimType.status_update,
    claim_text="Teams rolled Artemis I back to the VAB because of Hurricane Ian predictions.",
    reason="Managers chose rollback because of Hurricane Ian weather predictions.",
    normalized_value="hurricane_rollback",
    status=ClaimStatus.rolled_back,
)


class TestSplitSentences:
    def test_splits_on_terminal_punctuation(self) -> None:
        text = "The leak stopped the attempt. Later footage shows a rollback."
        assert split_sentences(text) == [
            "The leak stopped the attempt.",
            "Later footage shows a rollback.",
        ]

    def test_empty_text_yields_no_sentences(self) -> None:
        assert split_sentences("   ") == []


class TestIsComparative:
    def test_detects_comparison_wording(self) -> None:
        assert is_comparative("The explanation changed between the two briefings.") is True
        assert is_comparative("Later footage adds a weather reason.") is True

    def test_plain_statement_is_not_comparative(self) -> None:
        assert is_comparative("A hydrogen leak stopped the attempt.") is False

    def test_after_inside_one_claim_does_not_imply_two_source_moments(self) -> None:
        assert (
            is_comparative(
                "NASA waived off the attempt after a liquid-hydrogen leak."
            )
            is False
        )


class TestUnsupportedFacts:
    def test_supported_sentence_has_no_missing_facts(self) -> None:
        sentence = "A liquid-hydrogen leak occurred during propellant loading."
        assert unsupported_facts(sentence, [LEAK_EVENT]) == []

    def test_invented_name_is_caught(self) -> None:
        sentence = "Administrator Bill Nelson blamed the hydrogen leak."
        missing = unsupported_facts(sentence, [LEAK_EVENT])
        assert any("Bill Nelson" in item for item in missing)

    def test_invented_quantity_is_caught(self) -> None:
        sentence = "The leak measured 47 psi during loading."
        missing = unsupported_facts(sentence, [LEAK_EVENT])
        assert any("47 psi" in item for item in missing)

    def test_invented_date_is_caught(self) -> None:
        sentence = "The attempt was waved off on December 11, 2022."
        missing = unsupported_facts(sentence, [LEAK_EVENT])
        assert any("2022-12-11" in item for item in missing)

    def test_no_supporting_events_is_unsupported(self) -> None:
        assert unsupported_facts("Anything at all.", []) == ["no supporting events"]


class TestLockSentence:
    def test_grounded_sentence_is_supported(self) -> None:
        sentence = lock_sentence(
            "sentence_001",
            "A liquid-hydrogen leak occurred during propellant loading.",
            [LEAK_EVENT],
        )

        assert sentence.support_status is SupportStatus.supported
        assert sentence.supported_by_event_ids == ["evt_leak"]
        assert sentence.is_displayable is True

    def test_comparative_sentence_with_one_event_is_rejected(self) -> None:
        # PRD section 13: a sentence comparing two moments needs two event IDs.
        sentence = lock_sentence(
            "sentence_002",
            "The explanation changed after the earlier briefing.",
            [LEAK_EVENT],
        )

        assert sentence.support_status is SupportStatus.not_established
        assert sentence.text == NOT_ESTABLISHED_TEXT
        assert "at least two are required" in (sentence.lock_reason or "")

    def test_comparative_sentence_with_two_events_is_supported(self) -> None:
        sentence = lock_sentence(
            "sentence_003",
            "Later footage shows teams rolled Artemis I back to the VAB.",
            [LEAK_EVENT, ROLLBACK_EVENT],
        )

        assert sentence.support_status is SupportStatus.supported
        assert sentence.is_comparative is True
        assert len(sentence.supported_by_event_ids) == 2

    def test_unsupported_sentence_uses_the_visible_uncertainty_message(self) -> None:
        sentence = lock_sentence(
            "sentence_004",
            "Hurricane Ian was the sole cause of the November launch date.",
            [LEAK_EVENT],
        )

        assert sentence.support_status is SupportStatus.not_established
        assert sentence.text == NOT_ESTABLISHED_TEXT
        assert sentence.is_displayable is False

    def test_sentence_with_no_events_is_rejected(self) -> None:
        sentence = lock_sentence("sentence_005", "Anything at all.", [])

        assert sentence.support_status is SupportStatus.not_established
        assert sentence.lock_reason == "no supporting events were accepted"


class TestLockSummary:
    def test_mixed_summary_keeps_only_grounded_sentences_displayable(self) -> None:
        summary = (
            "A liquid-hydrogen leak occurred during propellant loading. "
            "Administrator Bill Nelson said the rocket was destroyed."
        )

        sentences = lock_summary(summary, [LEAK_EVENT])

        assert len(sentences) == 2
        assert sentences[0].is_displayable is True
        assert sentences[1].is_displayable is False
        assert sentences[1].text == NOT_ESTABLISHED_TEXT

    def test_sentence_ids_are_stable_and_ordered(self) -> None:
        sentences = lock_summary("One fact here. Two facts here.", [LEAK_EVENT])
        assert [s.sentence_id for s in sentences] == ["sentence_001", "sentence_002"]
