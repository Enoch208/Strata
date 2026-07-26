"""Extract timestamped claim events from transcripts.

PRD sections 10.3 and 11.4. Transcripts are chunked with overlap, a sandbox
model returns JSON only, and every record is validated before it can be indexed.
Rejections are written to the report rather than silently dropped (section 22).

Extracted events are written to `data/claim_events.json` so indexing is a
separate, independently runnable stage (guardrail 12).

    ./.venv/bin/python -m pipeline.extract_claims --phase1
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
import sys
from dataclasses import dataclass, field
from typing import Any

from services.api.adapters.videodb_client import VideoDBAdapter, VideoDBUnavailableError
from services.api.config import DATA_DIR, MissingCredentialError, get_settings
from services.api.comparison.dedupe import dedupe_events
from services.api.extraction.chunks import TranscriptChunk, chunk_transcript, parse_segments
from services.api.extraction.prompt import (
    ExtractionOutcome,
    build_prompt,
    parse_response,
    validate_records,
)
from services.api.manifest import ManifestVideo, load_manifest
from services.api.schemas.claim_event import ClaimEvent

from .ingest import PHASE_1_SLUGS

logger = logging.getLogger("pipeline.extract_claims")

CLAIM_EVENTS_PATH = DATA_DIR / "claim_events.json"
EXTRACTION_REPORT_PATH = DATA_DIR / "extraction_report.json"
MAX_EXTRACTION_WORKERS = 3


@dataclass
class ExtractionReport:
    slug: str
    video_id: str
    chunks: int = 0
    raw_records: int = 0
    accepted: int = 0
    deduped: int = 0
    rejections: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class ContextScene:
    analyzer: str
    start: float
    end: float
    text: str


@dataclass
class ChunkExtraction:
    index: int
    raw_records: int = 0
    outcome: ExtractionOutcome = field(default_factory=ExtractionOutcome)
    error: str | None = None


def extract_for_video(
    adapter: VideoDBAdapter, video: ManifestVideo
) -> tuple[list[ClaimEvent], ExtractionReport]:
    """Chunk one video's transcript and extract validated claim events."""
    assert video.video_id
    report = ExtractionReport(slug=video.slug, video_id=video.video_id)
    settings = get_settings()

    try:
        rows = adapter.transcript_segments(video.video_id)
    except VideoDBUnavailableError as error:
        logger.error("FAILED %s — %s", video.slug, error)
        report.error = str(error)
        return [], report

    segments = parse_segments(rows)
    if not segments:
        report.error = "transcript produced no usable timed segments"
        logger.error("FAILED %s — %s", video.slug, report.error)
        return [], report

    chunks = chunk_transcript(segments)
    context_scenes = load_context_scenes(adapter, video)
    report.chunks = len(chunks)
    logger.info("%s: %d segments -> %d chunks", video.slug, len(segments), len(chunks))

    # Resolve the collection once before workers share the adapter. Each model
    # job is otherwise independent and carries stable chunk/event IDs.
    adapter.collection()
    completed: dict[int, ChunkExtraction] = {}
    with ThreadPoolExecutor(max_workers=min(MAX_EXTRACTION_WORKERS, len(chunks))) as pool:
        futures = {
            pool.submit(
                _extract_chunk,
                adapter,
                video,
                chunk,
                context_for_chunk(context_scenes, chunk.start, chunk.end),
                settings.extraction_model,
            ): chunk.index
            for chunk in chunks
        }
        for future in as_completed(futures):
            result = future.result()
            completed[result.index] = result
            rejection_count = len(result.outcome.rejections) + bool(result.error)
            logger.info(
                "  chunk %d/%d: %d accepted, %d rejected",
                result.index + 1,
                len(chunks),
                len(result.outcome.events),
                rejection_count,
            )

    events: list[ClaimEvent] = []
    for index in sorted(completed):
        result = completed[index]
        report.raw_records += result.raw_records
        events.extend(result.outcome.events)
        report.rejections.extend(result.outcome.rejections)
        if result.error:
            report.rejections.append(f"chunk {index}: {result.error}")

    report.accepted = len(events)
    deduped = dedupe_events(events)
    report.deduped = len(deduped)
    logger.info("%s: %d accepted -> %d after dedupe", video.slug, len(events), len(deduped))
    return deduped, report


def _extract_chunk(
    adapter: VideoDBAdapter,
    video: ManifestVideo,
    chunk: TranscriptChunk,
    context: str | None,
    extraction_model: str,
) -> ChunkExtraction:
    prompt = build_prompt(
        chunk,
        title=video.title,
        organization=video.source_organization,
        source_date=video.source_date,
        context=context,
    )
    try:
        raw = adapter.generate_text(prompt, response_type="json")
    except VideoDBUnavailableError as error:
        return ChunkExtraction(
            index=chunk.index,
            error=f"generation failed — {error}",
        )

    records, parse_error = parse_response(raw)
    if parse_error:
        return ChunkExtraction(index=chunk.index, error=parse_error)

    return ChunkExtraction(
        index=chunk.index,
        raw_records=len(records),
        outcome=validate_records(
            records,
            chunk,
            video_id=video.video_id or "",
            source_date=video.source_date,
            source_organization=video.source_organization,
            extraction_model=extraction_model,
            artifact_ids=(
                [video.artifact_ids["speech"]]
                if video.artifact_ids.get("speech")
                else []
            ),
        ),
    )


def load_context_scenes(
    adapter: VideoDBAdapter,
    video: ManifestVideo,
) -> list[ContextScene]:
    """Load timestamped OCR/VLM scenes once for use across transcript chunks."""
    if not video.video_id or not video.understanding_id:
        return []

    scenes: list[ContextScene] = []
    for analyzer in ("onscreen_text", "scene_context"):
        try:
            output = adapter.understanding_output(
                video.video_id,
                video.understanding_id,
                analyzer,
            )
        except VideoDBUnavailableError as error:
            logger.warning("%s context unavailable — %s", analyzer, error)
            continue
        if not isinstance(output, dict):
            continue
        for raw_scene in output.get("scenes", []):
            scene = _parse_context_scene(analyzer, raw_scene)
            if scene is not None:
                scenes.append(scene)
    return sorted(scenes, key=lambda item: (item.start, item.end, item.analyzer))


def context_for_chunk(
    scenes: list[ContextScene],
    start: float,
    end: float,
    *,
    max_chars: int = 5000,
) -> str | None:
    """Render only analyzer scenes overlapping the transcript chunk."""
    lines = [
        f"[{scene.analyzer} {scene.start:.2f} - {scene.end:.2f}] {scene.text}"
        for scene in scenes
        if scene.start < end and start < scene.end
    ]
    if not lines:
        return None
    return "\n".join(lines)[:max_chars]


def _parse_context_scene(
    analyzer: str,
    raw: Any,
) -> ContextScene | None:
    if not isinstance(raw, dict):
        return None
    start = raw.get("start")
    end = raw.get("end")
    data = raw.get("data")
    text = data.get("text") if isinstance(data, dict) else None
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not isinstance(start, (int, float))
        or not isinstance(end, (int, float))
        or end <= start
        or not isinstance(text, str)
        or not text.strip()
    ):
        return None
    return ContextScene(analyzer, float(start), float(end), text.strip())


def run(slugs: tuple[str, ...] | None = None) -> int:
    manifest = load_manifest()
    adapter = VideoDBAdapter(collection_id=manifest.collection_id)

    targets = [
        video
        for video in manifest.videos
        if video.is_ready and (slugs is None or video.slug in slugs)
    ]
    if not targets:
        logger.error("no indexed videos matched %s — run pipeline.understand first", slugs or "all")
        return 1

    all_events: list[ClaimEvent] = []
    reports: list[ExtractionReport] = []
    for video in targets:
        events, report = extract_for_video(adapter, video)
        all_events.extend(events)
        reports.append(report)

    _write(all_events, reports)
    _summarize(reports)
    return 0 if all(report.error is None for report in reports) else 1


def _write(events: list[ClaimEvent], reports: list[ExtractionReport]) -> None:
    CLAIM_EVENTS_PATH.write_text(
        json.dumps([event.model_dump(mode="json") for event in events], indent=2) + "\n",
        encoding="utf-8",
    )
    EXTRACTION_REPORT_PATH.write_text(
        json.dumps([report.__dict__ for report in reports], indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info("wrote %d events to %s", len(events), CLAIM_EVENTS_PATH)
    logger.info("wrote extraction report to %s", EXTRACTION_REPORT_PATH)


def _summarize(reports: list[ExtractionReport]) -> None:
    logger.info("--- extraction report ---")
    for report in reports:
        logger.info(
            "%-42s chunks=%-3d raw=%-4d accepted=%-4d deduped=%-4d rejected=%d",
            report.slug,
            report.chunks,
            report.raw_records,
            report.accepted,
            report.deduped,
            len(report.rejections),
        )
        if report.error:
            logger.error("  %s: %s", report.slug, report.error)
        for rejection in report.rejections[:5]:
            logger.warning("  rejected — %s", rejection)
        if len(report.rejections) > 5:
            logger.warning("  ... and %d more (see report file)", len(report.rejections) - 5)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Extract claim events from archive transcripts.")
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
