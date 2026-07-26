"""Archive metadata and live aggregate statistics.

Mirrors PRD section 14 (`GET /api/archive`). Every number here is derived from a
VideoDB `aggregate()` call or the versioned collection manifest — PRD AGG-06
forbids hard-coding any of them.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ArchiveStats(BaseModel):
    """Live counts. Never literals — see AGG-01 through AGG-04."""

    model_config = ConfigDict(extra="forbid")

    claim_event_count: int = Field(ge=0)
    status_change_count: int = Field(ge=0)
    video_count: int = Field(ge=0)
    indexed_duration_seconds: int = Field(ge=0)


class StatsSources(BaseModel):
    """Provenance for each number above, so the header is auditable."""

    model_config = ConfigDict(extra="forbid")

    claim_events: str
    status_changes: str
    media: str


class DateRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: date
    end: date


class VideoSummary(BaseModel):
    """One ingested source, as the frontend needs it."""

    model_config = ConfigDict(extra="forbid")

    video_id: str
    slug: str
    title: str
    source_organization: str
    source_url: str
    source_date: date
    duration_seconds: float | None = None
    index_status: str


class ArchiveResponse(BaseModel):
    """Payload for `GET /api/archive`."""

    model_config = ConfigDict(extra="forbid")

    archive_id: str
    title: str
    stats: ArchiveStats
    stats_sources: StatsSources
    stats_generated_at: datetime
    date_range: DateRange
    index_status: str
    videos: list[VideoSummary] = Field(default_factory=list)
    acknowledgement: str
    #: Index and manifest versions the snapshot was derived from, so a cache can be
    #: invalidated when either changes (PRD AGG-05).
    index_version: str | None = None
    manifest_version: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def indexed_duration_label(self) -> str:
        """`4h12m`, as the archive header renders it (PRD section 8, step 1)."""
        total = self.stats.indexed_duration_seconds
        hours, remainder = divmod(total, 3600)
        minutes = remainder // 60
        return f"{hours}h{minutes:02d}m" if hours else f"{minutes}m"
