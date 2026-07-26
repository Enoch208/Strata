"""Search-result hydration at the VideoDB trust boundary."""

from services.api.retrieval.hydrate import event_from_record, hydrate_hits, record_from_hit


def record(**overrides) -> dict:
    payload = {
        "event_id": "evt_001",
        "video_id": "vid_001",
        "start": 0,
        "end": 15,
        "source_date": "2022-09-03",
        "subject": "Artemis I launch",
        "claim_type": "delay_reason",
        "claim_text": "A liquid-hydrogen leak stopped the attempt.",
        "normalized_value": "hydrogen_leak",
        "status": "scrubbed",
        "certainty": "explicit",
        "source_organization": "NASA",
    }
    payload.update(overrides)
    return payload


class Hit:
    def __init__(self, metadata: dict, *, score: float = 0.75) -> None:
        self.metadata = metadata
        self.search_score = score
        self.start = metadata.get("start")
        self.end = metadata.get("end")
        self.video_id = metadata.get("video_id")


def test_record_can_be_nested_in_shot_metadata() -> None:
    payload = record()
    assert record_from_hit(Hit(payload)) == payload


def test_zero_second_start_is_preserved() -> None:
    event, error = event_from_record(record())
    assert error is None
    assert event is not None and event.start == 0


def test_duplicate_hits_keep_the_best_score_and_first_hit() -> None:
    first = Hit(record(), score=0.25)
    second = Hit(record(), score=0.9)
    result = hydrate_hits([first, second])

    assert [event.event_id for event in result.events] == ["evt_001"]
    assert result.scores["evt_001"] == 0.9
    assert result.hits_by_event_id["evt_001"] is first


def test_invalid_hit_is_dropped_with_a_reason() -> None:
    result = hydrate_hits([{"metadata": {"not": "a claim event"}}])
    assert result.events == []
    assert "no claim-event fields found" in result.dropped[0]


def test_invalid_record_is_not_patched_with_defaults() -> None:
    event, error = event_from_record(record(source_date="not-a-date"))
    assert event is None
    assert "no parseable source_date" in (error or "")
