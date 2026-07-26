"""Only accepted findings may become ordinary summary text."""

from services.api.schemas.enums import Confidence, FindingLabel, SupportStatus
from services.api.schemas.finding import TimelineFinding
from services.api.summary import (
    build_headline,
    build_summary_sentences,
    insufficient_evidence_sentence,
    summary_text,
)

from .factories import make_event


EVENT = make_event(
    "evt_001",
    claim_text="A liquid-hydrogen leak stopped the attempt.",
    normalized_value="hydrogen_leak",
)
FINDING = TimelineFinding(
    finding_id="finding_001",
    label=FindingLabel.new_information,
    title="The archive records a leak",
    summary="A liquid-hydrogen leak stopped the attempt.",
    event_ids=["evt_001"],
    confidence=Confidence.medium,
)


def test_finding_summary_is_locked_to_its_own_events() -> None:
    sentences = build_summary_sentences([FINDING], [EVENT])
    assert len(sentences) == 1
    assert sentences[0].support_status is SupportStatus.supported
    assert sentences[0].supported_by_event_ids == ["evt_001"]


def test_missing_finding_event_becomes_visible_uncertainty() -> None:
    sentence = build_summary_sentences([FINDING], [])[0]
    assert sentence.support_status is SupportStatus.not_established
    assert sentence.is_displayable is False


def test_headline_cites_all_supporting_events() -> None:
    headline = build_headline([FINDING], [EVENT])
    assert headline.support_status is SupportStatus.supported
    assert headline.supported_by_event_ids == ["evt_001"]


def test_empty_headline_and_summary_are_honest() -> None:
    sentence = insufficient_evidence_sentence("nothing passed")
    assert sentence.support_status is SupportStatus.not_established
    assert summary_text([sentence]) == "Not established by this archive."
