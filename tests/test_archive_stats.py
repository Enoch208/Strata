"""Archive-header totals and manifest derivation (PRD sections 10.4 and 19)."""

from datetime import date

import pytest

from services.api.archive_stats import (
    build_archive_response,
    build_stats_sources,
    compute_stats,
)
from services.api.manifest import ArchiveManifest, load_manifest
from services.api.schemas.enums import STATUS_CHANGE_LABELS

PRD_EXAMPLE_HEADER = "41 claim events · 5 status changes · 6 videos · 4h12m indexed"


class FakeAdapter:
    """Stands in for VideoDB. SDK behaviour may be mocked in unit tests only."""

    def __init__(self, claim_total: int = 0, finding_buckets: dict[str, int] | None = None):
        self._claim_total = claim_total
        self._finding_buckets = finding_buckets or {}

    def aggregate_total(self, *, index_name: str, group_by: str) -> int:
        assert group_by == "claim_type"
        return self._claim_total

    def aggregate_selected(self, *, index_name: str, group_by: str, labels) -> int:
        assert group_by == "label"
        return sum(count for label, count in self._finding_buckets.items() if label in labels)


@pytest.fixture
def manifest() -> ArchiveManifest:
    # Unit tests operate on a pristine copy; the repository manifest is mutable
    # live pipeline state and may already contain real VideoDB IDs.
    manifest = load_manifest().model_copy(deep=True)
    manifest.collection_id = None
    manifest.index_version = None
    manifest.stats_snapshot = None
    for video in manifest.videos:
        video.video_id = None
        video.duration_seconds = None
        video.index_status = "pending"
        video.understanding_id = None
        video.artifact_ids = {}
        video.index_ids = {}
    return manifest


class TestManifestDerivation:
    def test_repo_manifest_loads_and_validates(self, manifest: ArchiveManifest) -> None:
        assert manifest.archive_id == "artemis-i-2022"
        assert len(manifest.videos) == 6

    def test_date_range_spans_the_archive(self, manifest: ArchiveManifest) -> None:
        assert manifest.date_range == (date(2022, 9, 2), date(2022, 11, 16))

    def test_uningested_manifest_reports_not_ingested(self, manifest: ArchiveManifest) -> None:
        # Before ingest the header must not claim readiness.
        assert manifest.index_status == "not_ingested"
        assert manifest.indexed_duration_seconds == 0

    def test_partial_ingest_is_reported_as_partial(self, manifest: ArchiveManifest) -> None:
        manifest.videos[0].video_id = "m-1"
        manifest.videos[0].index_status = "ready"
        manifest.videos[0].duration_seconds = 600.0

        assert manifest.index_status == "partial"
        assert manifest.indexed_duration_seconds == 600

    def test_only_ready_videos_count_toward_indexed_duration(
        self, manifest: ArchiveManifest
    ) -> None:
        manifest.videos[0].video_id = "m-1"
        manifest.videos[0].index_status = "ready"
        manifest.videos[0].duration_seconds = 600.0
        manifest.videos[1].video_id = "m-2"
        manifest.videos[1].index_status = "indexing"
        manifest.videos[1].duration_seconds = 900.0

        assert manifest.indexed_duration_seconds == 600

    def test_manifest_contains_no_evaluation_windows(
        self, manifest: ArchiveManifest
    ) -> None:
        assert "verified_windows" not in manifest.model_dump(mode="json")

    def test_nasa_landing_pages_have_direct_ingest_assets(
        self, manifest: ArchiveManifest
    ) -> None:
        for slug in (
            "sep03-post-scrub-news-conference",
            "sep30-this-week-at-nasa-rollback",
        ):
            video = manifest.by_slug(slug)
            assert video is not None
            assert "images.nasa.gov/details/" in video.source_url
            assert video.ingest_url is not None
            assert video.ingest_url.endswith(".mp4")


class TestComputeStats:
    def test_status_changes_are_confirmed_change_plus_correction(
        self, manifest: ArchiveManifest
    ) -> None:
        adapter = FakeAdapter(
            claim_total=41,
            finding_buckets={
                "confirmed_change": 4,
                "correction": 1,
                "consistent_statement": 7,
                "new_information": 3,
                "needs_review": 2,
            },
        )

        stats = compute_stats(manifest, adapter)  # type: ignore[arg-type]

        assert stats.claim_event_count == 41
        assert stats.status_change_count == 5

    def test_status_changes_is_not_the_count_of_distinct_statuses(
        self, manifest: ArchiveManifest
    ) -> None:
        # PRD section 10.4 calls this out explicitly.
        buckets = {"confirmed_change": 9, "correction": 0, "consistent_statement": 1}
        stats = compute_stats(manifest, FakeAdapter(0, buckets))  # type: ignore[arg-type]

        assert stats.status_change_count == 9
        assert stats.status_change_count != len(buckets)

    def test_counts_track_the_aggregate_rather_than_any_literal(
        self, manifest: ArchiveManifest
    ) -> None:
        # AGG-06: the header must move with the data.
        stats = compute_stats(manifest, FakeAdapter(7, {"correction": 2}))  # type: ignore[arg-type]

        assert stats.claim_event_count == 7
        assert stats.status_change_count == 2

    def test_video_count_reflects_ready_videos_only(self, manifest: ArchiveManifest) -> None:
        stats = compute_stats(manifest, FakeAdapter())  # type: ignore[arg-type]
        assert stats.video_count == 0

        manifest.videos[0].video_id = "m-1"
        manifest.videos[0].index_status = "ready"
        stats = compute_stats(manifest, FakeAdapter())  # type: ignore[arg-type]
        assert stats.video_count == 1

    def test_status_change_labels_are_exactly_two(self) -> None:
        assert {str(label) for label in STATUS_CHANGE_LABELS} == {
            "confirmed_change",
            "correction",
        }


class TestArchiveResponse:
    def test_stats_sources_name_the_aggregate_calls(self, manifest: ArchiveManifest) -> None:
        sources = build_stats_sources(manifest)

        assert sources.claim_events == "aggregate:claim_events_v1:claim_type"
        assert sources.status_changes == "aggregate:timeline_findings_v1:label"
        assert sources.media == "collection_manifest"

    def test_duration_label_is_formatted_for_the_header(self, manifest: ArchiveManifest) -> None:
        manifest.videos[0].video_id = "m-1"
        manifest.videos[0].index_status = "ready"
        manifest.videos[0].duration_seconds = 15120.0

        response = build_archive_response(manifest, compute_stats(manifest, FakeAdapter()))  # type: ignore[arg-type]

        assert response.indexed_duration_label == "4h12m"

    def test_response_never_contains_the_prd_example_literals(
        self, manifest: ArchiveManifest
    ) -> None:
        response = build_archive_response(manifest, compute_stats(manifest, FakeAdapter()))  # type: ignore[arg-type]

        assert PRD_EXAMPLE_HEADER not in response.model_dump_json()

    def test_only_ingested_videos_are_listed(self, manifest: ArchiveManifest) -> None:
        response = build_archive_response(manifest, compute_stats(manifest, FakeAdapter()))  # type: ignore[arg-type]
        assert response.videos == []

        manifest.videos[0].video_id = "m-1"
        response = build_archive_response(manifest, compute_stats(manifest, FakeAdapter()))  # type: ignore[arg-type]
        assert [v.video_id for v in response.videos] == ["m-1"]

    def test_acknowledgement_is_carried_through(self, manifest: ArchiveManifest) -> None:
        response = build_archive_response(manifest, compute_stats(manifest, FakeAdapter()))  # type: ignore[arg-type]
        assert "NASA" in response.acknowledgement

    def test_index_version_changes_invalidate_snapshot_identity(
        self, manifest: ArchiveManifest
    ) -> None:
        manifest.index_version = "sha256:first"
        first = build_archive_response(manifest, compute_stats(manifest, FakeAdapter()))  # type: ignore[arg-type]
        manifest.index_version = "sha256:second"
        second = build_archive_response(manifest, compute_stats(manifest, FakeAdapter()))  # type: ignore[arg-type]

        assert first.index_version == "sha256:first"
        assert second.index_version == "sha256:second"
        assert first.index_version != second.index_version
