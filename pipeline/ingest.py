"""Ingest archive videos into one VideoDB collection.

PRD sections 10.1 and 11.2. Idempotent by design (guardrail 12): existing video
IDs are reused, a second run creates no duplicates, and failures are reported
rather than silently skipped. API keys are never written to the manifest.

    ./.venv/bin/python -m pipeline.ingest --phase1   # 3 Sep + 30 Sep only
    ./.venv/bin/python -m pipeline.ingest            # all six
"""

from __future__ import annotations

import argparse
import logging
import sys

from services.api.adapters.videodb_client import VideoDBAdapter, VideoDBUnavailableError
from services.api.config import MissingCredentialError, get_settings
from services.api.manifest import ArchiveManifest, ManifestVideo, load_manifest, save_manifest

logger = logging.getLogger("pipeline.ingest")

#: The two sources that must work before anything else is built (PRD section 23).
PHASE_1_SLUGS = ("sep03-post-scrub-news-conference", "sep30-this-week-at-nasa-rollback")

COLLECTION_NAME = "Strata — Artemis I Launch Archive"
COLLECTION_DESCRIPTION = (
    "Official NASA Artemis I archive footage from the delayed 2022 launch campaign, "
    "indexed for source-locked temporal investigation."
)


def ensure_collection(adapter: VideoDBAdapter, manifest: ArchiveManifest) -> str:
    """Reuse the manifest's collection, or create one and record its ID."""
    if manifest.collection_id:
        collection = adapter.collection(manifest.collection_id)
        logger.info("reusing collection %s", collection.id)
        return str(collection.id)

    settings = get_settings()
    if settings.videodb_collection_id:
        collection = adapter.collection(settings.videodb_collection_id)
        logger.info("using collection %s from environment", collection.id)
        return str(collection.id)

    collection = adapter.create_collection(COLLECTION_NAME, COLLECTION_DESCRIPTION)
    logger.info("created collection %s", collection.id)
    return str(collection.id)


def ingest_video(
    adapter: VideoDBAdapter,
    video: ManifestVideo,
    collection_id: str,
    archive_id: str,
) -> bool:
    """Upload one source if it is not already ingested. Returns True on success."""
    if video.is_ingested:
        logger.info("skip %s — already ingested as %s", video.slug, video.video_id)
        return True

    upload_url = video.ingest_url or video.source_url
    logger.info("uploading %s from %s", video.slug, upload_url)
    try:
        uploaded = adapter.upload(
            upload_url,
            collection_id=collection_id,
            name=video.title,
            description=(
                f"Archive: {archive_id}. Topic: Artemis I launch campaign. "
                f"Source: {video.source_organization}. Published: {video.source_date}. "
                f"Purpose: {video.purpose}. Canonical source: {video.source_url}"
            ),
        )
    except VideoDBUnavailableError as error:
        # Reported, not swallowed: a partial archive must be visible.
        logger.error("FAILED %s — %s", video.slug, error)
        video.index_status = "failed"
        return False

    video.video_id = uploaded.video_id
    video.duration_seconds = uploaded.duration_seconds
    video.index_status = "uploaded"
    logger.info(
        "ingested %s as %s (%.1fs)",
        video.slug,
        uploaded.video_id,
        uploaded.duration_seconds or 0.0,
    )
    return True


def run(slugs: tuple[str, ...] | None = None) -> int:
    manifest = load_manifest()
    adapter = VideoDBAdapter(collection_id=manifest.collection_id)

    targets = [v for v in manifest.videos if slugs is None or v.slug in slugs]
    if not targets:
        logger.error("no manifest videos matched %s", slugs)
        return 1

    collection_id = ensure_collection(adapter, manifest)
    manifest.collection_id = collection_id

    failures = 0
    try:
        for video in targets:
            if not ingest_video(adapter, video, collection_id, manifest.archive_id):
                failures += 1
    finally:
        # Persist whatever succeeded, so a partial run is never lost and a rerun
        # resumes rather than re-uploading.
        save_manifest(manifest)
        logger.info("manifest saved")

    _report(manifest, targets, failures)
    return 1 if failures else 0


def _report(manifest: ArchiveManifest, targets: list[ManifestVideo], failures: int) -> None:
    logger.info("--- ingest report ---")
    for video in targets:
        logger.info("%-42s %-12s %s", video.slug, video.index_status, video.video_id or "-")
    logger.info("collection: %s", manifest.collection_id)
    logger.info("ingested: %d/%d, failures: %d", len(targets) - failures, len(targets), failures)

    ingested_ids = [v.video_id for v in targets if v.video_id]
    if len(set(ingested_ids)) != len(ingested_ids):
        # PRD section 23 requires the two phase-1 sources to be distinct videos;
        # a collision would silently break the challenge source-novelty check.
        logger.error("DUPLICATE video IDs detected across sources: %s", ingested_ids)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Ingest the Strata archive into VideoDB.")
    parser.add_argument(
        "--phase1",
        action="store_true",
        help="Ingest only the two verified critical-path sources (3 Sep and 30 Sep).",
    )
    parser.add_argument("--slug", action="append", help="Ingest a specific manifest slug.")
    args = parser.parse_args()

    slugs: tuple[str, ...] | None = None
    if args.phase1:
        slugs = PHASE_1_SLUGS
    elif args.slug:
        slugs = tuple(args.slug)

    try:
        return run(slugs)
    except MissingCredentialError as error:
        logger.error("%s", error)
        return 2


if __name__ == "__main__":
    sys.exit(main())
