"""Understanding-stage resume and retry behavior."""

from dataclasses import dataclass

from pipeline.understand import process_video
from services.api.manifest import load_manifest


@dataclass
class FakeAnalyzer:
    name: str
    status: str = "completed"
    id: str = "artifact"
    type: str = ""

    @property
    def is_successful(self) -> bool:
        return self.status == "completed"


class FakeUnderstanding:
    def __init__(self, understanding_id: str, analyzers: list[FakeAnalyzer]) -> None:
        self.id = understanding_id
        self._analyzers = analyzers

    def wait_until_complete(self, *, timeout: int) -> None:
        assert timeout > 0

    def list_analyzers(self) -> list[FakeAnalyzer]:
        return self._analyzers


class FakeIndex:
    def __init__(self, name: str, *, successful: bool = True, suffix: str = "") -> None:
        self.name = name
        self.index_id = f"index_{name}{suffix}"
        self.status = "completed" if successful else "failed"

    @property
    def is_successful(self) -> bool:
        return self.status == "completed"

    def wait_until_complete(self, *, timeout: int) -> None:
        assert timeout > 0


def analyzers() -> list[FakeAnalyzer]:
    return [
        FakeAnalyzer("speech", id="artifact_speech"),
        FakeAnalyzer("onscreen_text", id="artifact_ocr"),
        FakeAnalyzer("scene_context", id="artifact_vlm"),
    ]


def video():
    item = load_manifest().videos[0].model_copy(deep=True)
    item.video_id = "video_001"
    item.index_status = "uploaded"
    item.understanding_id = None
    item.artifact_ids = {}
    item.index_ids = {}
    return item


class RetryIndexAdapter:
    def __init__(self) -> None:
        self.index_attempts: dict[str, int] = {}

    def understand(self, video_id: str, definitions) -> FakeUnderstanding:
        assert video_id == "video_001"
        assert len(definitions) == 3
        return FakeUnderstanding("understanding_new", analyzers())

    def list_indexes(self, video_id: str) -> list[FakeIndex]:
        return []

    def index_analyzer(
        self, video_id: str, analyzer: FakeAnalyzer, *, name: str
    ) -> FakeIndex:
        attempt = self.index_attempts.get(name, 0) + 1
        self.index_attempts[name] = attempt
        return FakeIndex(name, successful=attempt > 1, suffix=f"_{attempt}")


def test_failed_analyzer_indexes_are_retried_once() -> None:
    adapter = RetryIndexAdapter()
    item = video()

    report = process_video(adapter, item)  # type: ignore[arg-type]

    assert report.is_usable is True
    assert adapter.index_attempts == {
        "speech": 2,
        "onscreen_text": 2,
        "scene_context": 2,
    }
    assert set(item.index_ids) == {"speech", "onscreen_text", "scene_context"}


class ResumeAdapter(RetryIndexAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.started = 0
        self.persisted = FakeUnderstanding(
            "understanding_old",
            [
                FakeAnalyzer("speech"),
                FakeAnalyzer("onscreen_text", status="failed"),
                FakeAnalyzer("scene_context"),
            ],
        )

    def get_understanding(
        self, video_id: str, understanding_id: str
    ) -> FakeUnderstanding:
        assert understanding_id == "understanding_old"
        return self.persisted

    def understand(self, video_id: str, definitions) -> FakeUnderstanding:
        self.started += 1
        return FakeUnderstanding("understanding_replacement", analyzers())

    def index_analyzer(
        self, video_id: str, analyzer: FakeAnalyzer, *, name: str
    ) -> FakeIndex:
        self.index_attempts[name] = self.index_attempts.get(name, 0) + 1
        return FakeIndex(name)


def test_incomplete_persisted_understanding_is_replaced() -> None:
    adapter = ResumeAdapter()
    item = video()
    item.understanding_id = "understanding_old"
    item.artifact_ids = {"stale": "artifact_old"}
    item.index_ids = {"stale": "index_old"}

    report = process_video(adapter, item)  # type: ignore[arg-type]

    assert report.is_usable is True
    assert adapter.started == 1
    assert item.understanding_id == "understanding_replacement"
    assert "stale" not in item.artifact_ids
    assert "stale" not in item.index_ids


class RecoverIndexAdapter(ResumeAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.persisted = FakeUnderstanding("understanding_old", analyzers())

    def list_indexes(self, video_id: str) -> list[FakeIndex]:
        return [FakeIndex(name) for name in ("speech", "onscreen_text", "scene_context")]

    def index_analyzer(self, *args, **kwargs) -> FakeIndex:
        raise AssertionError("ready remote indexes should be reused")


def test_ready_remote_indexes_are_recovered_after_interrupted_save() -> None:
    adapter = RecoverIndexAdapter()
    item = video()
    item.understanding_id = "understanding_old"

    report = process_video(adapter, item)  # type: ignore[arg-type]

    assert report.is_usable is True
    assert set(item.index_ids) == {"speech", "onscreen_text", "scene_context"}


class SpeechFallbackAdapter(RetryIndexAdapter):
    def index_analyzer(
        self, video_id: str, analyzer: FakeAnalyzer, *, name: str
    ) -> FakeIndex:
        self.index_attempts[name] = self.index_attempts.get(name, 0) + 1
        return FakeIndex(name, successful=name != "speech")

    def transcript_segments(self, video_id: str) -> list[dict]:
        return [
            {"start": 10.0, "end": 14.0, "text": "A real transcript sentence."},
            {"start": 14.0, "end": 14.0, "text": "Invalid zero-length row."},
        ]

    def create_index(
        self,
        video_id: str,
        *,
        records: list[dict],
        name: str,
        fields: dict,
        use_for: list[str],
    ) -> FakeIndex:
        assert name == "speech"
        assert records == [
            {
                "start": 10.0,
                "end": 14.0,
                "text": "A real transcript sentence.",
                "words": [],
            }
        ]
        assert fields["semantic"] == ["text"]
        assert use_for == ["semantic", "query"]
        return FakeIndex(name, suffix="_bounded")


def test_failed_large_speech_artifact_uses_bounded_transcript_index() -> None:
    adapter = SpeechFallbackAdapter()
    item = video()

    report = process_video(adapter, item)  # type: ignore[arg-type]

    assert report.is_usable is True
    assert item.index_ids["speech"] == "index_speech_bounded"
