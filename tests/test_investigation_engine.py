"""End-to-end investigation orchestration without live network calls."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from services.api.adapters.videodb_client import StreamReference
from services.api.investigation_engine import (
    InvestigationEngine,
    _filter_low_relevance_hits,
    _set_focused_variant_match,
)
from services.api.main import app
from services.api.manifest import ArchiveManifest, load_manifest
from services.api.routes.investigations import engine_dependency
from services.api.schemas.enums import ChallengeOutcome, FindingLabel
from services.api.schemas.packet import InvestigationState


class FakeHit:
    def __init__(self, metadata: dict, *, score: float) -> None:
        self.metadata = metadata
        self.search_score = score
        self.video_id = metadata["video_id"]
        self.video_title = (
            "Post-Scrub News Conference"
            if self.video_id == "vid_leak"
            else "This Week at NASA"
        )
        self.start = metadata["start"]
        self.end = metadata["end"]
        self.text = metadata["claim_text"]
        self.stream_url = f"https://stream.example/{self.video_id}.m3u8"
        self.player_url = f"https://player.example/{self.video_id}"


LEAK_RECORD = {
    "event_id": "evt_leak",
    "video_id": "vid_leak",
    "start": 86.0,
    "end": 101.0,
    "source_date": "2022-09-03",
    "speaker_role": "NASA mission official",
    "subject": "Artemis I launch",
    "claim_type": "delay_reason",
    "claim_text": (
        "NASA waived off the attempt after a liquid-hydrogen leak during "
        "propellant loading."
    ),
    "normalized_value": "hydrogen_leak",
    "unit": "",
    "status": "scrubbed",
    "reason": "A liquid-hydrogen leak occurred during propellant loading.",
    "certainty": "explicit",
    "source_organization": "NASA",
}

WEATHER_RECORD = {
    "event_id": "evt_weather",
    "video_id": "vid_weather",
    "start": 115.0,
    "end": 139.0,
    "source_date": "2022-09-30",
    "speaker_role": "NASA narrator",
    "subject": "Artemis I launch",
    "claim_type": "delay_reason",
    "claim_text": (
        "Teams rolled Artemis I back to the VAB because of Hurricane Ian "
        "weather predictions."
    ),
    "normalized_value": "hurricane_rollback",
    "unit": "",
    "status": "rolled_back",
    "reason": "Managers chose rollback because of Hurricane Ian weather predictions.",
    "certainty": "explicit",
    "source_organization": "NASA",
}


class FakeAdapter:
    def __init__(self) -> None:
        self.searches: list[str] = []
        self.index_searches: list[tuple[str, ...]] = []
        self.compiled: list[list[tuple[str, float, float]]] = []

    def semantic_search(self, query: str, **kwargs: object) -> list[FakeHit]:
        self.searches.append(query)
        self.index_searches.append(
            tuple(kwargs.get("index_names", []))  # type: ignore[arg-type]
        )
        if any(
            marker in query.lower()
            for marker in (
                "different or additional",
                "revised or updated",
                "stayed consistent",
                "context, limits",
                "correcting, disputing",
                "weather predictions related to hurricane",
                "later events or conditions",
                "weather or external conditions",
                "weather or hurricane ian",
                "later footage adding context",
                "speaker correcting",
            )
        ):
            return [FakeHit(WEATHER_RECORD, score=0.8)]
        return [FakeHit(LEAK_RECORD, score=0.95)]

    def stream_window_ref(
        self, video_id: str, start: float, end: float
    ) -> StreamReference:
        return StreamReference(f"https://stream.example/{video_id}-{start}-{end}.m3u8")

    def compile_windows(
        self, windows: list[tuple[str, float, float]]
    ) -> StreamReference:
        self.compiled.append(windows)
        return StreamReference(
            "https://stream.example/reel.m3u8",
            "https://player.example/reel",
        )


class ReusedSourceAdapter(FakeAdapter):
    def semantic_search(self, query: str, **kwargs: object) -> list[FakeHit]:
        if "different or additional" not in query.lower() and not any(
            marker in query.lower()
            for marker in (
                "revised or updated",
                "stayed consistent",
                "context, limits",
                "correcting, disputing",
                "weather predictions related to hurricane",
                "later events or conditions",
                "weather or external conditions",
                "weather or hurricane ian",
                "later footage adding context",
                "speaker correcting",
            )
        ):
            return super().semantic_search(query, **kwargs)
        repeated = {
            **WEATHER_RECORD,
            "event_id": "evt_reused_video",
            "video_id": "vid_leak",
            "start": 200.0,
            "end": 215.0,
            "source_date": "2022-09-03",
        }
        return [FakeHit(repeated, score=0.8)]


class MixedInitialAdapter(FakeAdapter):
    def semantic_search(self, query: str, **kwargs: object) -> list[FakeHit]:
        if any(
            marker in query.lower()
            for marker in (
                "different or additional",
                "revised or updated",
                "stayed consistent",
                "context, limits",
                "correcting, disputing",
                "later events or conditions",
                "weather or external conditions",
                "weather or hurricane ian",
                "later footage adding context",
                "speaker correcting",
            )
        ):
            return [FakeHit(WEATHER_RECORD, score=0.8)]
        return [
            FakeHit(LEAK_RECORD, score=0.95),
            FakeHit(WEATHER_RECORD, score=0.94),
        ]


def ready_manifest() -> ArchiveManifest:
    source = load_manifest()
    leak = source.by_slug("sep03-post-scrub-news-conference")
    weather = source.by_slug("sep30-this-week-at-nasa-rollback")
    assert leak is not None and weather is not None
    return source.model_copy(
        update={
            "collection_id": "collection_001",
            "videos": [
                leak.model_copy(
                    update={
                        "video_id": "vid_leak",
                        "duration_seconds": 600.0,
                        "index_status": "ready",
                    }
                ),
                weather.model_copy(
                    update={
                        "video_id": "vid_weather",
                        "duration_seconds": 180.0,
                        "index_status": "ready",
                    }
                ),
            ],
        },
        deep=True,
    )


def make_engine() -> tuple[InvestigationEngine, FakeAdapter]:
    adapter = FakeAdapter()
    sequence = iter(["inv_test", "challenge_test"])
    engine = InvestigationEngine(
        manifest_provider=ready_manifest,
        adapter_factory=lambda _: adapter,  # type: ignore[arg-type]
        clock=lambda: datetime(2026, 7, 26, tzinfo=UTC),
        id_factory=lambda _: next(sequence),
    )
    return engine, adapter


def headline_query() -> str:
    return "Why was Artemis I’s September 3 launch attempt scrubbed?"


def test_first_pass_is_gated_playable_and_source_locked() -> None:
    engine, adapter = make_engine()
    investigation = engine.create(headline_query(), "artemis-i-2022")

    assert investigation.state is InvestigationState.complete
    assert [event.event_id for event in investigation.events] == ["evt_leak"]
    assert investigation.findings[0].label is FindingLabel.new_information
    assert investigation.summary_sentences[1].is_displayable is True
    assert all(
        sentence.supported_by_event_ids
        for sentence in investigation.summary_sentences
        if sentence.is_displayable
    )
    assert investigation.shots[0].is_playable is True
    assert {
        "claim_events_v1",
        "speech",
        "onscreen_text",
        "scene_context",
    }.issubset({name for indexes in adapter.index_searches for name in indexes})


def test_uncovered_query_specific_terms_return_insufficient_evidence() -> None:
    engine, _ = make_engine()

    investigation = engine.create(
        "Which NASA official said alien interference delayed Artemis I?",
        "artemis-i-2022",
    )

    assert investigation.state is InvestigationState.insufficient_evidence
    assert investigation.events == []
    assert "no relevant claim events" in (
        investigation.insufficient_evidence_reason or ""
    ).lower()


def test_focused_query_facets_survive_cross_index_score_differences() -> None:
    repair = FakeHit(
        {
            **LEAK_RECORD,
            "event_id": "evt_repair",
            "claim_type": "repair_plan",
            "claim_text": "Teams removed and replaced the quick-disconnect seals.",
            "subject": "Artemis I seal repair",
        },
        score=0.95,
    )
    cryogenic_test = FakeHit(
        {
            **WEATHER_RECORD,
            "event_id": "evt_cryo_test",
            "claim_type": "test_plan",
            "claim_text": (
                "Teams planned a cryogenic demonstration to test the repaired seals."
            ),
            "subject": "Artemis I cryogenic demonstration",
        },
        score=0.72,
    )
    _set_focused_variant_match(cryogenic_test)

    kept = _filter_low_relevance_hits(
        "How did NASA describe the seal repair and planned cryogenic test?",
        [repair, cryogenic_test],
    )

    assert {hit.metadata["event_id"] for hit in kept} == {
        "evt_repair",
        "evt_cryo_test",
    }


def test_challenge_qualifies_with_an_unused_video() -> None:
    engine, _ = make_engine()
    investigation = engine.create(headline_query(), "artemis-i-2022")
    original_findings = [finding.finding_id for finding in investigation.findings]

    challenge = engine.challenge(investigation.investigation_id)

    assert challenge.outcome is ChallengeOutcome.qualified
    assert challenge.initial_accepted_video_ids == ["vid_leak"]
    assert challenge.challenge_accepted_video_ids == ["vid_weather"]
    assert challenge.novel_accepted_video_ids == ["vid_weather"]
    assert challenge.found_counter_evidence is True
    assert challenge.initial_queries == investigation.initial_queries
    assert challenge.counter_queries
    assert [finding.finding_id for finding in investigation.findings][
        : len(original_findings)
    ] == original_findings
    assert "evt_weather" in [event.event_id for event in investigation.events]


def test_date_scoped_first_pass_leaves_later_source_for_challenge() -> None:
    adapter = MixedInitialAdapter()
    sequence = iter(["inv_test", "challenge_test"])
    engine = InvestigationEngine(
        manifest_provider=ready_manifest,
        adapter_factory=lambda _: adapter,  # type: ignore[arg-type]
        clock=lambda: datetime(2026, 7, 26, tzinfo=UTC),
        id_factory=lambda _: next(sequence),
    )

    investigation = engine.create(headline_query(), "artemis-i-2022")
    challenge = engine.challenge(investigation.investigation_id)

    assert challenge.initial_accepted_video_ids == ["vid_leak"]
    assert challenge.novel_accepted_video_ids == ["vid_weather"]


def test_challenge_reports_when_context_comes_from_an_initial_video() -> None:
    adapter = ReusedSourceAdapter()
    sequence = iter(["inv_test", "challenge_test"])
    engine = InvestigationEngine(
        manifest_provider=ready_manifest,
        adapter_factory=lambda _: adapter,  # type: ignore[arg-type]
        clock=lambda: datetime(2026, 7, 26, tzinfo=UTC),
        id_factory=lambda _: next(sequence),
    )
    investigation = engine.create(headline_query(), "artemis-i-2022")

    challenge = engine.challenge(investigation.investigation_id)

    assert challenge.outcome is ChallengeOutcome.qualified
    assert challenge.found_counter_evidence is True
    assert challenge.novel_accepted_video_ids == []


def test_reel_is_chronological_and_packet_contains_challenge_trace() -> None:
    engine, adapter = make_engine()
    investigation = engine.create(headline_query(), "artemis-i-2022")
    engine.challenge(investigation.investigation_id)

    reel = engine.generate_reel(
        investigation.investigation_id, ["evt_weather", "evt_leak"]
    )
    packet = engine.packet(investigation.investigation_id)

    assert reel.event_ids == ["evt_leak", "evt_weather"]
    assert reel.stream_url == "https://stream.example/reel.m3u8"
    assert [window[0] for window in adapter.compiled[0]] == [
        "vid_leak",
        "vid_weather",
    ]
    assert packet.challenge is not None
    assert packet.challenge.novel_accepted_video_ids == ["vid_weather"]


def test_routes_expose_the_complete_workflow_and_downloadable_packet() -> None:
    engine, _ = make_engine()
    app.dependency_overrides[engine_dependency] = lambda: engine
    client = TestClient(app)
    try:
        created = client.post(
            "/api/investigations",
            json={"query": headline_query(), "archive_id": "artemis-i-2022"},
        )
        assert created.status_code == 200
        assert created.json()["state"] == "complete"

        challenge = client.post(
            "/api/investigations/inv_test/challenge",
            json={"instruction": "Challenge this conclusion"},
        )
        assert challenge.status_code == 200
        assert challenge.json()["novel_accepted_video_ids"] == ["vid_weather"]

        reel = client.post(
            "/api/investigations/inv_test/reel",
            json={"event_ids": ["evt_weather", "evt_leak"]},
        )
        assert reel.status_code == 200
        assert reel.json()["event_ids"] == ["evt_leak", "evt_weather"]

        packet = client.get("/api/investigations/inv_test/packet")
        assert packet.status_code == 200
        assert packet.headers["content-disposition"].startswith("attachment;")
        assert packet.json()["challenge"]["outcome"] == "qualified"
    finally:
        app.dependency_overrides.clear()
