"""The versioned archive manifest.

PRD ING-03 and section 16: a JSON manifest stores archive metadata and VideoDB
IDs, and is the source of truth for video count and indexed duration. It never
holds credentials (guardrail 4).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .config import MANIFEST_PATH


class VerifiedWindow(BaseModel):
    """A manually verified source window, checked against first-party captions.

    These pin the demo fixture (PRD section 5) so a regression in retrieval is
    visible rather than silently reworded.
    """

    model_config = ConfigDict(extra="forbid")

    pass_name: str = Field(alias="pass")
    video_slug: str
    start: float
    end: float
    establishes: str
    does_not_establish: str
    verified_against: str
    verified_on: date


class ManifestVideo(BaseModel):
    """One archive source. `video_id` is filled in by the ingest script."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    source_organization: str
    source_url: str
    #: Direct downloadable media used for VideoDB ingestion. `source_url` remains
    #: the human-facing first-party landing page shown in the evidence inspector.
    ingest_url: str | None = None
    source_media_id: str
    source_date: date
    purpose: str
    video_id: str | None = None
    duration_seconds: float | None = None
    index_status: str = "pending"
    understanding_id: str | None = None
    artifact_ids: dict[str, str] = Field(default_factory=dict)
    index_ids: dict[str, str] = Field(default_factory=dict)

    @property
    def is_ingested(self) -> bool:
        return bool(self.video_id)

    @property
    def is_ready(self) -> bool:
        return self.is_ingested and self.index_status == "ready"


class IndexNames(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_events: str
    timeline_findings: str


class ArchiveManifest(BaseModel):
    """The whole manifest, validated on load."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    manifest_version: str
    archive_id: str
    title: str
    acknowledgement: str
    collection_id: str | None = None
    videos: list[ManifestVideo]
    verified_windows: list[VerifiedWindow] = Field(default_factory=list)
    index_names: IndexNames
    index_version: str | None = None
    stats_snapshot: dict[str, object] | None = None

    @property
    def ingested_videos(self) -> list[ManifestVideo]:
        return [video for video in self.videos if video.is_ingested]

    @property
    def ready_videos(self) -> list[ManifestVideo]:
        return [video for video in self.videos if video.is_ready]

    @property
    def indexed_duration_seconds(self) -> int:
        """Total duration of videos confirmed indexed (PRD AGG-03).

        Only `ready` videos count; a pending video's footage is not yet part of
        what the archive can answer from.
        """
        return int(sum(video.duration_seconds or 0.0 for video in self.ready_videos))

    @property
    def index_status(self) -> str:
        if not self.ingested_videos:
            return "not_ingested"
        ready = len(self.ready_videos)
        if ready == len(self.videos):
            return "ready"
        if ready == 0:
            return "indexing"
        return "partial"

    @property
    def date_range(self) -> tuple[date, date]:
        dates = sorted(video.source_date for video in self.videos)
        return dates[0], dates[-1]

    def by_slug(self, slug: str) -> ManifestVideo | None:
        return next((video for video in self.videos if video.slug == slug), None)

    def by_video_id(self, video_id: str) -> ManifestVideo | None:
        return next((video for video in self.videos if video.video_id == video_id), None)

    def verified_window(self, pass_name: str) -> VerifiedWindow | None:
        return next((w for w in self.verified_windows if w.pass_name == pass_name), None)


def load_manifest(path: Path | None = None) -> ArchiveManifest:
    """Read and validate the manifest from disk."""
    target = path or MANIFEST_PATH
    return ArchiveManifest.model_validate_json(target.read_text(encoding="utf-8"))


def save_manifest(manifest: ArchiveManifest, path: Path | None = None) -> None:
    """Write the manifest back, preserving the `pass` alias on verified windows."""
    target = path or MANIFEST_PATH
    payload = manifest.model_dump(mode="json", by_alias=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
