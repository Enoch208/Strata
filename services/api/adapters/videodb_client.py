"""Typed boundary around the VideoDB SDK.

Every VideoDB call the product makes goes through this adapter. Domain code
depends on these method signatures, not on `videodb` types, so an SDK change is
a one-file change and responses are validated before they reach the engine.

Signatures verified against the installed `videodb==0.5.1` source, not from
memory. No call here invents an endpoint or a parameter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import videodb
from videodb.editor import Clip, Timeline, Track, VideoAsset
from videodb.exceptions import VideodbError

from ..config import Settings, get_settings
from .payloads import parse_buckets, sum_buckets, sum_selected

logger = logging.getLogger(__name__)

#: Understanding analyzers used for the archive (PRD UND-01, UND-02, UND-03).
#: Types confirmed against the VideoDB understanding-artifacts documentation.
SPEECH_ANALYZER: dict[str, Any] = {"type": "spoken_words", "name": "speech"}
OCR_ANALYZER: dict[str, Any] = {"type": "ocr", "name": "onscreen_text"}
VISUAL_ANALYZER: dict[str, Any] = {
    "type": "vlm",
    "name": "scene_context",
    "config": {
        "prompt": (
            "Describe the setting, who is speaking and their apparent role "
            "(for example: podium, press conference, mission control, b-roll). "
            "Report only what is visible."
        )
    },
}


class VideoDBUnavailableError(RuntimeError):
    """A VideoDB call failed. Surfaced honestly; never replaced with sample data."""


@dataclass(frozen=True)
class UploadedVideo:
    """The subset of an ingested video the pipeline records in the manifest."""

    video_id: str
    title: str
    duration_seconds: float | None


@dataclass(frozen=True)
class StreamReference:
    """The two playback URLs returned by VideoDB."""

    stream_url: str
    player_url: str | None = None


class VideoDBAdapter:
    """Thin, typed wrapper over `videodb`. Construct once and reuse."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        collection_id: str | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        # An explicit collection wins over the environment, so pipeline scripts can
        # target the manifest's collection without mutating global config.
        self._default_collection_id = collection_id or self._settings.videodb_collection_id
        self._connection = None
        self._collection = None

    # -- connection ---------------------------------------------------------

    @property
    def connection(self):
        """Lazily connect. Raises `MissingCredentialError` when no key is set."""
        if self._connection is None:
            api_key = self._settings.require_api_key()
            self._connection = videodb.connect(api_key=api_key)
        return self._connection

    def collection(self, collection_id: str | None = None):
        """Return the working collection, creating nothing implicitly."""
        if self._collection is not None and collection_id is None:
            return self._collection

        target = collection_id or self._default_collection_id
        connection = self.connection
        self._collection = (
            connection.get_collection(target) if target else connection.get_collection()
        )
        return self._collection

    def create_collection(self, name: str, description: str):
        """Create a new collection. Only called explicitly by the ingest script."""
        collection = self.connection.create_collection(name=name, description=description)
        self._collection = collection
        return collection

    def ping(self) -> str:
        """One harmless read call, used by the health check.

        Returns the reachable collection's ID. Any failure raises rather than
        reporting a healthy state.
        """
        try:
            return str(self.collection().id)
        except VideodbError as error:
            raise VideoDBUnavailableError(f"VideoDB is unreachable: {error}") from error

    # -- ingest -------------------------------------------------------------

    def upload(
        self,
        url: str,
        *,
        collection_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> UploadedVideo:
        """Ingest one source URL and return its VideoDB identifiers."""
        try:
            video = self.collection(collection_id).upload(
                url=url,
                name=name,
                description=description,
            )
        except VideodbError as error:
            raise VideoDBUnavailableError(f"upload failed for {url}: {error}") from error

        if video is None or not getattr(video, "id", None):
            raise VideoDBUnavailableError(f"upload returned no video for {url}")

        return UploadedVideo(
            video_id=str(video.id),
            title=str(getattr(video, "name", "") or ""),
            duration_seconds=_as_float(getattr(video, "length", None)),
        )

    def get_video(self, video_id: str, *, collection_id: str | None = None):
        return self.collection(collection_id).get_video(video_id)

    def understand(self, video_id: str, analyzers: list[dict[str, Any]]):
        """Start an understanding run producing speech, OCR and visual artifacts."""
        video = self.get_video(video_id)
        try:
            return video.understand(analyzers=analyzers)
        except VideodbError as error:
            raise VideoDBUnavailableError(
                f"understand failed for {video_id}: {error}"
            ) from error

    def get_understanding(self, video_id: str, understanding_id: str):
        """Fetch a persisted understanding run for idempotent pipeline resumes."""
        video = self.get_video(video_id)
        try:
            return video.get_understanding(understanding_id)
        except VideodbError as error:
            raise VideoDBUnavailableError(
                f"get_understanding failed for {video_id}: {error}"
            ) from error

    def list_understandings(self, video_id: str):
        video = self.get_video(video_id)
        try:
            return list(video.list_understandings())
        except VideodbError as error:
            raise VideoDBUnavailableError(
                f"list_understandings failed for {video_id}: {error}"
            ) from error

    def understanding_output(
        self,
        video_id: str,
        understanding_id: str,
        analyzer_name: str,
    ) -> Any:
        """Fetch one timestamped analyzer output for extraction context."""
        try:
            understanding = self.get_video(video_id).get_understanding(
                understanding_id
            )
            return understanding.get_analyzer_output(analyzer_name)
        except VideodbError as error:
            raise VideoDBUnavailableError(
                f"analyzer output failed for {video_id}/{analyzer_name}: {error}"
            ) from error

    def list_indexes(self, video_id: str):
        video = self.get_video(video_id)
        try:
            return list(video.list_indexes())
        except VideodbError as error:
            raise VideoDBUnavailableError(
                f"list_indexes failed for {video_id}: {error}"
            ) from error

    def index_analyzer(
        self,
        video_id: str,
        analyzer,
        *,
        name: str,
        use_for: list[str] | None = None,
        fields: dict[str, list[str]] | None = None,
    ):
        """Build a retrieval index directly from an understanding artifact.

        The analyzer is passed by reference — VideoDB re-fetches its output
        server-side, so artifact scenes never round-trip through this process.
        """
        video = self.get_video(video_id)
        try:
            return video.index(
                source=analyzer,
                name=name,
                use_for=use_for or ["semantic", "query"],
                fields=fields,
            )
        except VideodbError as error:
            raise VideoDBUnavailableError(
                f"index failed for {video_id} analyzer {name}: {error}"
            ) from error

    def transcript_segments(self, video_id: str) -> list[dict[str, Any]]:
        """Sentence-segmented transcript rows: `{start, end, text}`.

        Sentence segmentation keeps a claim inside one row, which word-level
        segmentation would shred.
        """
        video = self.get_video(video_id)
        try:
            return list(video.get_transcript(segmenter="sentence"))
        except VideodbError as error:
            raise VideoDBUnavailableError(
                f"get_transcript failed for {video_id}: {error}"
            ) from error

    # -- indexing -----------------------------------------------------------

    def create_index(
        self,
        video_id: str,
        *,
        records: list[dict[str, Any]],
        name: str,
        fields: dict[str, list[str]],
        use_for: list[str] | None = None,
    ):
        """Index user-supplied temporal records under `name`.

        `video.index()` accepts a list of temporal records directly, which is how
        extracted claim events become a searchable custom index.
        """
        video = self.get_video(video_id)
        try:
            return video.index(
                source=records,
                name=name,
                use_for=use_for or ["semantic", "query", "aggregate"],
                fields=fields,
            )
        except VideodbError as error:
            raise VideoDBUnavailableError(
                f"index creation failed for {video_id} index {name}: {error}"
            ) from error

    # -- retrieval ----------------------------------------------------------

    def semantic_search(
        self,
        query: str,
        *,
        index_names: list[str] | None = None,
        top_k: int = 20,
        filter: list | dict | None = None,
        return_fields: list[str] | str | None = None,
    ):
        try:
            return self.collection().semantic_search(
                query=query,
                index_names=index_names,
                top_k=top_k,
                filter=filter,
                return_fields=return_fields,
            )
        except VideodbError as error:
            raise VideoDBUnavailableError(f"semantic_search failed: {error}") from error

    def structured_query(
        self,
        *,
        index_name: str,
        filter: list | dict | None = None,
        limit: int = 100,
        sort: str | list[tuple[str, str]] | None = None,
    ):
        try:
            return self.collection().query(
                index_name=index_name, filter=filter, limit=limit, sort=sort
            )
        except VideodbError as error:
            raise VideoDBUnavailableError(f"query failed on {index_name}: {error}") from error

    def aggregate_counts(self, *, index_name: str, group_by: str) -> dict[str, int]:
        """Grouped counts from an index, parsed into `{label: count}`."""
        try:
            payload = self.collection().aggregate(
                index_name=index_name, group_by=group_by, metric="count"
            )
        except VideodbError as error:
            raise VideoDBUnavailableError(
                f"aggregate failed on {index_name} by {group_by}: {error}"
            ) from error
        return parse_buckets(payload)

    def aggregate_total(self, *, index_name: str, group_by: str) -> int:
        try:
            payload = self.collection().aggregate(
                index_name=index_name, group_by=group_by, metric="count"
            )
        except VideodbError as error:
            raise VideoDBUnavailableError(
                f"aggregate failed on {index_name} by {group_by}: {error}"
            ) from error
        return sum_buckets(payload)

    def aggregate_selected(
        self, *, index_name: str, group_by: str, labels: frozenset[str] | set[str]
    ) -> int:
        try:
            payload = self.collection().aggregate(
                index_name=index_name, group_by=group_by, metric="count"
            )
        except VideodbError as error:
            raise VideoDBUnavailableError(
                f"aggregate failed on {index_name} by {group_by}: {error}"
            ) from error
        return sum_selected(payload, labels)

    # -- playback and compilation ------------------------------------------

    def stream_window(self, video_id: str, start: float, end: float) -> str:
        """Playable stream for one exact window. Never synthesized locally."""
        return self.stream_window_ref(video_id, start, end).stream_url

    def stream_window_ref(
        self, video_id: str, start: float, end: float
    ) -> StreamReference:
        """Playable HLS and fallback-player URLs for one exact window."""
        video = self.get_video(video_id)
        try:
            stream_url = video.generate_stream(timeline=[(start, end)])
        except VideodbError as error:
            raise VideoDBUnavailableError(
                f"generate_stream failed for {video_id} [{start}, {end}]: {error}"
            ) from error
        if not stream_url:
            raise VideoDBUnavailableError(
                f"generate_stream returned no stream for {video_id} [{start}, {end}]"
            )
        return StreamReference(
            stream_url=str(stream_url),
            player_url=_optional_text(getattr(video, "player_url", None)),
        )

    def compile_windows(
        self, windows: list[tuple[str, float, float]]
    ) -> StreamReference:
        """Compile chronological windows from one or more videos into one reel."""
        if not windows:
            raise VideoDBUnavailableError("cannot compile an empty evidence reel")

        timeline = Timeline(self.connection)
        track = Track()
        offset = 0.0
        for video_id, start, end in windows:
            duration = end - start
            if duration <= 0:
                raise VideoDBUnavailableError(
                    f"cannot compile non-positive window {video_id} [{start}, {end}]"
                )
            track.add_clip(
                offset,
                Clip(VideoAsset(video_id, start=start), duration=duration),
            )
            offset += duration
        timeline.add_track(track)

        try:
            stream_url = timeline.generate_stream()
        except VideodbError as error:
            raise VideoDBUnavailableError(f"evidence reel compilation failed: {error}") from error
        if not stream_url:
            raise VideoDBUnavailableError("evidence reel compilation returned no stream")
        return StreamReference(
            stream_url=str(stream_url),
            player_url=_optional_text(getattr(timeline, "player_url", None)),
        )

    def generate_text(self, prompt: str, *, response_type: str = "json") -> Any:
        """Run the configured sandbox model. Used only downstream of retrieval."""
        try:
            return self.collection().generate_text(
                prompt=prompt,
                model_name=self._settings.extraction_model,
                response_type=response_type,
                temperature=self._settings.extraction_temperature,
            )
        except VideodbError as error:
            raise VideoDBUnavailableError(f"generate_text failed: {error}") from error


def _as_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None
