"""Custom-index materialization remains deterministic and archive-focused."""

from pipeline.build_index import _index_version, _timeline_events
from services.api.manifest import load_manifest
from services.api.schemas.enums import ClaimType, Confidence, FindingLabel
from services.api.schemas.finding import TimelineFinding

from .factories import make_event


def test_timeline_materialization_keeps_subject_and_corrections() -> None:
    manifest = load_manifest().model_copy(deep=True)

    central = make_event("central", subject="Artemis I launch")
    correction = make_event(
        "correction",
        subject="flight termination batteries",
        claim_type=ClaimType.correction,
    )
    peripheral = make_event("peripheral", subject="press conference logistics")

    selected = _timeline_events(
        manifest,
        [central, correction, peripheral],
    )

    assert [event.event_id for event in selected] == [
        "central",
        "correction",
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
