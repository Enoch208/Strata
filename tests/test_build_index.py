"""Custom-index materialization remains deterministic and archive-focused."""

from pipeline.build_index import _index_version, _timeline_events
from services.api.manifest import load_manifest
from services.api.schemas.enums import ClaimType, Confidence, FindingLabel
from services.api.schemas.finding import TimelineFinding

from .factories import make_event


def test_timeline_materialization_keeps_subject_corrections_and_verified_windows() -> None:
    manifest = load_manifest().model_copy(deep=True)
    initial = manifest.verified_window("initial")
    source = manifest.by_slug(initial.video_slug) if initial else None
    assert initial is not None and source is not None and source.video_id

    central = make_event("central", subject="Artemis I launch")
    correction = make_event(
        "correction",
        subject="flight termination batteries",
        claim_type=ClaimType.correction,
    )
    verified = make_event(
        "verified",
        video_id=source.video_id,
        start=initial.start,
        end=initial.end,
        subject="hydrogen leak",
    )
    peripheral = make_event("peripheral", subject="press conference logistics")

    selected = _timeline_events(
        manifest,
        [central, correction, verified, peripheral],
    )

    assert [event.event_id for event in selected] == [
        "central",
        "correction",
        "verified",
    ]


def test_index_version_is_stable_and_changes_with_evidence() -> None:
    event = make_event("event")
    finding = TimelineFinding(
        finding_id="finding",
        label=FindingLabel.new_information,
        title="New status",
        summary="The archive added a status.",
        event_ids=["event"],
        confidence=Confidence.high,
    )

    first = _index_version([event], [finding])
    second = _index_version([event], [finding])
    changed = _index_version(
        [event.model_copy(update={"claim_text": "A changed statement."})],
        [finding],
    )

    assert first == second
    assert first.startswith("sha256:")
    assert changed != first
