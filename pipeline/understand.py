"""Generate speech, OCR and visual artifacts, then index them.

PRD sections 10.2 and 11.3. Every video gets spoken-word, on-screen-text and
scene-context analyzers; each successful artifact becomes a retrieval index.
Artifact counts and failures are reported for debugging (UND-05), and a video is
only marked `ready` when its speech artifact actually succeeded.

    ./.venv/bin/python -m pipeline.understand --phase1
    ./.venv/bin/python -m pipeline.understand
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, field

from services.api.adapters.videodb_client import (
    OCR_ANALYZER,
    SPEECH_ANALYZER,
    VISUAL_ANALYZER,
    VideoDBAdapter,
    VideoDBUnavailableError,
)
from services.api.config import MissingCredentialError
from services.api.manifest import ManifestVideo, load_manifest, save_manifest

from .ingest import PHASE_1_SLUGS

logger = logging.getLogger("pipeline.understand")

ANALYZERS = [SPEECH_ANALYZER, OCR_ANALYZER, VISUAL_ANALYZER]

REQUIRED_ANALYZERS = frozenset(
    {SPEECH_ANALYZER["name"], OCR_ANALYZER["name"], VISUAL_ANALYZER["name"]}
)

UNDERSTANDING_TIMEOUT_SECONDS = 2700
INDEX_TIMEOUT_SECONDS = 1800
INDEX_ATTEMPTS = 2


@dataclass
class VideoReport:
    slug: str
    video_id: str
    succeeded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    indexed: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def is_usable(self) -> bool:
        return (
            REQUIRED_ANALYZERS.issubset(self.succeeded)
            and REQUIRED_ANALYZERS.issubset(self.indexed)
            and self.error is None
        )


def process_video(adapter: VideoDBAdapter, video: ManifestVideo) -> VideoReport:
    """Run all analyzers on one video and index each successful artifact."""
    assert video.video_id  # guaranteed by the caller's filter
    report = VideoReport(slug=video.slug, video_id=video.video_id)

    logger.info("understanding %s (%s)", video.slug, video.video_id)
    try:
        understanding = _get_or_start_understanding(adapter, video)
        understanding.wait_until_complete(timeout=UNDERSTANDING_TIMEOUT_SECONDS)
    except (VideoDBUnavailableError, TimeoutError) as error:
        logger.error("FAILED %s — %s", video.slug, error)
        report.error = str(error)
        return report

    video.understanding_id = understanding.id
    for analyzer in understanding.list_analyzers():
        label = analyzer.name or analyzer.type or "unnamed"
        if not analyzer.is_successful:
            logger.warning("  analyzer %s did not succeed (status=%s)", label, analyzer.status)
            report.failed.append(label)
            continue

        report.succeeded.append(label)
        if analyzer.id:
            video.artifact_ids[label] = analyzer.id

        existing_index_id = video.index_ids.get(label)
        if existing_index_id:
            report.indexed.append(label)
            logger.info("  reuse index %s (index_id=%s)", label, existing_index_id)
            continue

        index = _existing_successful_index(adapter, video.video_id, label)
        if index is not None:
            report.indexed.append(label)
            video.index_ids[label] = index.index_id
            logger.info("  recovered index %s (index_id=%s)", label, index.index_id)
            continue

        attempts = INDEX_ATTEMPTS
        if (
            label == SPEECH_ANALYZER["name"]
            and _failed_index_count(adapter, video.video_id, label) >= INDEX_ATTEMPTS
        ):
            attempts = 0
            logger.info(
                "  prior %s analyzer indexes failed; using bounded transcript fallback",
                label,
            )

        for attempt in range(1, attempts + 1):
            try:
                index = adapter.index_analyzer(video.video_id, analyzer, name=label)
                if index is None:
                    raise VideoDBUnavailableError("index creation returned nothing")
                index.wait_until_complete(timeout=INDEX_TIMEOUT_SECONDS)
            except (VideoDBUnavailableError, TimeoutError) as error:
                logger.warning(
                    "  index %s attempt %d/%d failed — %s",
                    label,
                    attempt,
                    INDEX_ATTEMPTS,
                    error,
                )
                index = None
            if index is not None and index.is_successful:
                break
            if index is not None:
                logger.warning(
                    "  index %s attempt %d/%d did not succeed (status=%s)",
                    label,
                    attempt,
                    INDEX_ATTEMPTS,
                    index.status,
                )

        if index is not None and index.is_successful:
            report.indexed.append(label)
            video.index_ids[label] = index.index_id
            logger.info("  indexed %s (index_id=%s)", label, index.index_id)
        elif label == SPEECH_ANALYZER["name"]:
            fallback = _index_bounded_speech(adapter, video.video_id, label)
            if fallback is not None:
                report.indexed.append(label)
                video.index_ids[label] = fallback.index_id
                logger.info(
                    "  indexed %s from bounded transcript records (index_id=%s)",
                    label,
                    fallback.index_id,
                )
            else:
                report.failed.append(f"{label}:index")
        else:
            report.failed.append(f"{label}:index")

    return report


def _get_or_start_understanding(
    adapter: VideoDBAdapter,
    video: ManifestVideo,
):
    """Reuse a complete successful run, but retry a persisted failed run."""
    assert video.video_id
    if not video.understanding_id:
        return adapter.understand(video.video_id, ANALYZERS)

    existing = adapter.get_understanding(video.video_id, video.understanding_id)
    existing.wait_until_complete(timeout=UNDERSTANDING_TIMEOUT_SECONDS)
    successful = {
        analyzer.name or analyzer.type
        for analyzer in existing.list_analyzers()
        if analyzer.is_successful
    }
    if REQUIRED_ANALYZERS.issubset(successful):
        return existing

    logger.warning(
        "  persisted understanding %s is incomplete; starting a replacement",
        video.understanding_id,
    )
    video.artifact_ids = {}
    video.index_ids = {}
    return adapter.understand(video.video_id, ANALYZERS)


def _existing_successful_index(
    adapter: VideoDBAdapter,
    video_id: str,
    name: str,
):
    """Recover a ready index when a prior run ended before saving the manifest."""
    try:
        return next(
            (
                index
                for index in adapter.list_indexes(video_id)
                if index.name == name and index.is_successful
            ),
            None,
        )
    except VideoDBUnavailableError as error:
        logger.warning("  could not list indexes for %s — %s", name, error)
        return None


def _failed_index_count(
    adapter: VideoDBAdapter,
    video_id: str,
    name: str,
) -> int:
    try:
        return sum(
            index.name == name and index.status == "failed"
            for index in adapter.list_indexes(video_id)
        )
    except VideoDBUnavailableError:
        return 0


def _index_bounded_speech(
    adapter: VideoDBAdapter,
    video_id: str,
    name: str,
):
    """Fallback for analyzer scenes too large for the embedding service.

    The records remain the real VideoDB transcript with its original sentence
    timestamps. Only the index source shape changes from a large analyzer
    artifact to bounded user-supplied temporal records.
    """
    try:
        rows = adapter.transcript_segments(video_id)
        records = [
            {
                "start": float(row["start"]),
                "end": float(row["end"]),
                "text": str(row["text"]).strip(),
                # Analyzer-backed speech indexes use this stable scene shape.
                # Keeping the field (even when sentence segmentation omits
                # word objects) lets the collection accept the shared name.
                "words": row.get("words", []),
            }
            for row in rows
            if _usable_transcript_row(row)
        ]
        if not records:
            logger.warning("  bounded speech fallback produced no records")
            return None
        index = adapter.create_index(
            video_id,
            records=records,
            name=name,
            fields={
                "semantic": ["text"],
                "sort": ["start"],
            },
            use_for=["semantic", "query"],
        )
        if index is None:
            return None
        index.wait_until_complete(timeout=INDEX_TIMEOUT_SECONDS)
        if not index.is_successful:
            logger.warning(
                "  bounded speech index did not succeed (status=%s)", index.status
            )
            return None
        return index
    except (KeyError, TypeError, ValueError, VideoDBUnavailableError, TimeoutError) as error:
        logger.warning("  bounded speech fallback failed — %s", error)
        return None


def _usable_transcript_row(row: object) -> bool:
    if not isinstance(row, dict):
        return False
    start = row.get("start")
    end = row.get("end")
    text = row.get("text")
    return (
        isinstance(start, (int, float))
        and not isinstance(start, bool)
        and isinstance(end, (int, float))
        and not isinstance(end, bool)
        and end > start
        and isinstance(text, str)
        and bool(text.strip())
    )


def run(slugs: tuple[str, ...] | None = None) -> int:
    manifest = load_manifest()
    adapter = VideoDBAdapter(collection_id=manifest.collection_id)

    targets = [
        video
        for video in manifest.videos
        if video.is_ingested and (slugs is None or video.slug in slugs)
    ]
    if not targets:
        logger.error(
            "no ingested videos matched %s — run pipeline.ingest first", slugs or "all"
        )
        return 1

    reports: list[VideoReport] = []
    try:
        for video in targets:
            report = process_video(adapter, video)
            reports.append(report)
            video.index_status = "ready" if report.is_usable else "failed"
    finally:
        save_manifest(manifest)
        logger.info("manifest saved")

    _report(reports)
    return 0 if all(report.is_usable for report in reports) else 1


def _report(reports: list[VideoReport]) -> None:
    logger.info("--- understanding report ---")
    for report in reports:
        logger.info(
            "%-42s ok=%-28s failed=%-20s indexed=%s",
            report.slug,
            ",".join(report.succeeded) or "-",
            ",".join(report.failed) or "-",
            ",".join(report.indexed) or "-",
        )
        if report.error:
            logger.error("  %s: %s", report.slug, report.error)
    usable = sum(1 for report in reports if report.is_usable)
    logger.info("usable videos: %d/%d", usable, len(reports))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Run understanding analyzers over the archive.")
    parser.add_argument("--phase1", action="store_true", help="Only the two critical-path sources.")
    parser.add_argument("--slug", action="append", help="Process a specific manifest slug.")
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
