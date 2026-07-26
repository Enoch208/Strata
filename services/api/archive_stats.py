"""Live archive statistics for the aggregate header.

PRD section 10.4. Claim-event and status-change counts come from VideoDB
`aggregate()`; video count and indexed duration come from the versioned
manifest. AGG-06 forbids hard-coding any of them, so there is no literal count
anywhere in this module and no default that could stand in for a real one.
"""

from __future__ import annotations

from datetime import UTC, datetime

from .adapters.videodb_client import VideoDBAdapter, VideoDBUnavailableError
from .manifest import ArchiveManifest
from .schemas.archive import (
    ArchiveResponse,
    ArchiveStats,
    DateRange,
    StatsSources,
    VideoSummary,
)
from .schemas.enums import STATUS_CHANGE_LABELS

CLAIM_EVENTS_GROUP_BY = "claim_type"
TIMELINE_FINDINGS_GROUP_BY = "label"

_STATUS_CHANGE_KEYS = frozenset(str(label) for label in STATUS_CHANGE_LABELS)


def build_stats_sources(manifest: ArchiveManifest) -> StatsSources:
    """Provenance strings so each header number is traceable to its origin."""
    return StatsSources(
        claim_events=f"aggregate:{manifest.index_names.claim_events}:{CLAIM_EVENTS_GROUP_BY}",
        status_changes=(
            f"aggregate:{manifest.index_names.timeline_findings}:{TIMELINE_FINDINGS_GROUP_BY}"
        ),
        media="collection_manifest",
    )


def compute_stats(manifest: ArchiveManifest, adapter: VideoDBAdapter) -> ArchiveStats:
    """Derive the four header numbers from live aggregates plus the manifest.

    A missing index means zero *observed* events, which is honest — but an
    unreachable VideoDB raises, so the header degrades visibly instead of
    reporting a confident zero.
    """
    claim_event_count = _safe_total(
        adapter,
        index_name=manifest.index_names.claim_events,
        group_by=CLAIM_EVENTS_GROUP_BY,
    )
    status_change_count = _safe_selected(
        adapter,
        index_name=manifest.index_names.timeline_findings,
        group_by=TIMELINE_FINDINGS_GROUP_BY,
        labels=_STATUS_CHANGE_KEYS,
    )

    return ArchiveStats(
        claim_event_count=claim_event_count,
        status_change_count=status_change_count,
        video_count=len(manifest.ready_videos),
        indexed_duration_seconds=manifest.indexed_duration_seconds,
    )


def _safe_total(adapter: VideoDBAdapter, *, index_name: str, group_by: str) -> int:
    """Aggregate total, treating a not-yet-created index as zero observed records.

    Any other failure propagates: a network or auth problem must not look like an
    empty archive.
    """
    try:
        return adapter.aggregate_total(index_name=index_name, group_by=group_by)
    except VideoDBUnavailableError as error:
        if _is_missing_index(error):
            return 0
        raise


def _safe_selected(
    adapter: VideoDBAdapter,
    *,
    index_name: str,
    group_by: str,
    labels: frozenset[str],
) -> int:
    try:
        return adapter.aggregate_selected(
            index_name=index_name, group_by=group_by, labels=labels
        )
    except VideoDBUnavailableError as error:
        if _is_missing_index(error):
            return 0
        raise


def _is_missing_index(error: Exception) -> bool:
    message = str(error).lower()
    return "not found" in message or "does not exist" in message or "no index" in message


def build_archive_response(
    manifest: ArchiveManifest,
    stats: ArchiveStats,
    *,
    generated_at: datetime | None = None,
) -> ArchiveResponse:
    """Assemble the `GET /api/archive` payload."""
    start, end = manifest.date_range
    return ArchiveResponse(
        archive_id=manifest.archive_id,
        title=manifest.title,
        stats=stats,
        stats_sources=build_stats_sources(manifest),
        stats_generated_at=generated_at or datetime.now(UTC),
        date_range=DateRange(start=start, end=end),
        index_status=manifest.index_status,
        videos=[
            VideoSummary(
                video_id=video.video_id or "",
                slug=video.slug,
                title=video.title,
                source_organization=video.source_organization,
                source_url=video.source_url,
                source_date=video.source_date,
                duration_seconds=video.duration_seconds,
                index_status=video.index_status,
            )
            for video in manifest.videos
            if video.is_ingested
        ],
        acknowledgement=manifest.acknowledgement,
        index_version=manifest.index_version,
        manifest_version=manifest.manifest_version,
    )
