"""Evidence-gate rejection (PRD section 19, required tests)."""

from datetime import date

from services.api.comparison.gate import accepted_video_ids, apply_gate, check_finding
from services.api.schemas.enums import Confidence, FindingLabel
from services.api.schemas.finding import TimelineFinding
from services.api.schemas.packet import EvidenceShot

from .factories import make_event

EVENT_A = make_event("evt_a", video_id="vid_sep03", source_date="2022-09-03", start=86.0, end=101.0)
EVENT_B = make_event("evt_b", video_id="vid_sep30", source_date="2022-09-30", start=115.0, end=139.0)


def make_shot(event_id: str, video_id: str, *, stream_url: str | None = "https://x/s.m3u8") -> EvidenceShot:
    return EvidenceShot(
        event_id=event_id,
        video_id=video_id,
        video_title="A NASA briefing",
        source_url="https://images.nasa.gov/details/x",
        source_date=date(2022, 9, 3),
        start=86.0,
        end=101.0,
        stream_url=stream_url,
    )


def make_finding(
    finding_id: str = "finding_1",
    *,
    label: FindingLabel = FindingLabel.confirmed_change,
    event_ids: list[str] | None = None,
) -> TimelineFinding:
    return TimelineFinding(
        finding_id=finding_id,
        label=label,
        title="A change in the stated reason",
        summary="The stated reason differs between the two sources.",
        event_ids=event_ids if event_ids is not None else ["evt_a", "evt_b"],
        confidence=Confidence.high,
    )


class TestCheckFinding:
    def test_fully_grounded_finding_passes(self) -> None:
        reason = check_finding(
            make_finding(),
            {"evt_a": EVENT_A, "evt_b": EVENT_B},
            {"evt_a": make_shot("evt_a", "vid_sep03"), "evt_b": make_shot("evt_b", "vid_sep30")},
        )
        assert reason is None

    def test_missing_event_is_rejected(self) -> None:
        reason = check_finding(
            make_finding(),
            {"evt_a": EVENT_A},
            {"evt_a": make_shot("evt_a", "vid_sep03")},
        )
        assert reason is not None
        assert "evt_b" in reason

    def test_missing_shot_is_rejected(self) -> None:
        reason = check_finding(
            make_finding(),
            {"evt_a": EVENT_A, "evt_b": EVENT_B},
            {"evt_a": make_shot("evt_a", "vid_sep03")},
        )
        assert reason is not None
        assert "no retrieved source shot" in reason

    def test_shot_without_stream_url_is_rejected(self) -> None:
        # A finding whose footage cannot play would render a dead Play button.
        reason = check_finding(
            make_finding(),
            {"evt_a": EVENT_A, "evt_b": EVENT_B},
            {
                "evt_a": make_shot("evt_a", "vid_sep03"),
                "evt_b": make_shot("evt_b", "vid_sep30", stream_url=None),
            },
        )
        assert reason is not None
        assert "playable stream" in reason

    def test_comparative_label_with_one_event_is_rejected(self) -> None:
        finding = make_finding(label=FindingLabel.new_information, event_ids=["evt_a"])
        # Re-label after construction to bypass the schema guard and prove the gate
        # independently enforces the same rule.
        object.__setattr__(finding, "label", FindingLabel.confirmed_change)

        reason = check_finding(
            finding,
            {"evt_a": EVENT_A},
            {"evt_a": make_shot("evt_a", "vid_sep03")},
        )

        assert reason is not None
        assert "two distinct events" in reason


class TestApplyGate:
    def test_splits_accepted_from_rejected_with_reasons(self) -> None:
        good = make_finding("finding_ok")
        bad = make_finding("finding_bad", event_ids=["evt_a", "evt_missing"])

        result = apply_gate(
            [good, bad],
            [EVENT_A, EVENT_B],
            [make_shot("evt_a", "vid_sep03"), make_shot("evt_b", "vid_sep30")],
        )

        assert [f.finding_id for f in result.accepted] == ["finding_ok"]
        assert result.rejected_finding_ids == ["finding_bad"]
        assert "evt_missing" in result.rejections[0].reason

    def test_everything_rejected_yields_no_accepted_findings(self) -> None:
        result = apply_gate([make_finding()], [], [])

        assert result.accepted == []
        assert len(result.rejections) == 1


class TestAcceptedVideoIds:
    def test_returns_distinct_videos_in_chronological_order(self) -> None:
        ids = accepted_video_ids([make_finding()], [EVENT_B, EVENT_A])
        assert ids == ["vid_sep03", "vid_sep30"]

    def test_ignores_events_not_cited_by_any_finding(self) -> None:
        ids = accepted_video_ids([make_finding(event_ids=["evt_a", "evt_b"])], [EVENT_A, EVENT_B])
        assert "vid_sep30" in ids

        unrelated = make_event("evt_other", video_id="vid_nov16", source_date="2022-11-16")
        ids = accepted_video_ids([make_finding()], [EVENT_A, EVENT_B, unrelated])
        assert "vid_nov16" not in ids
