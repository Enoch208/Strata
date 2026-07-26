"""Create and populate the custom claim-event and accepted-finding indexes.

PRD sections 10.3 and 11.5. Extracted claim events are pushed to VideoDB as
user-supplied temporal records, grouped per source video, with the semantic /
filter / sort / aggregate field configuration the archive header depends on.

    ./.venv/bin/python -m pipeline.build_index
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys

from services.api.adapters.videodb_client import VideoDBAdapter, VideoDBUnavailableError
from services.api.comparison.diff import compare_events
from services.api.comparison.gate import apply_gate
from services.api.config import MissingCredentialError, get_settings
from services.api.manifest import ArchiveManifest, ManifestVideo, load_manifest, save_manifest
from services.api.retrieval.shots import hydrate_shots
from services.api.schemas.claim_event import CLAIM_EVENT_INDEX_FIELDS, ClaimEvent
from services.api.schemas.finding import (
    TIMELINE_FINDING_INDEX_FIELDS,
    TimelineFinding,
)

from .extract_claims import CLAIM_EVENTS_PATH

logger = logging.getLogger("pipeline.build_index")

INDEX_TIMEOUT_SECONDS = 1800


def load_events() -> list[ClaimEvent]:
    if not CLAIM_EVENTS_PATH.exists():
        raise FileNotFoundError(
            f"{CLAIM_EVENTS_PATH} does not exist — run pipeline.extract_claims first"
        )
    raw = json.loads(CLAIM_EVENTS_PATH.read_text(encoding="utf-8"))
    return [ClaimEvent.model_validate(record) for record in raw]


def run(index_name: str | None = None) -> int:
    manifest = load_manifest()
    adapter = VideoDBAdapter(collection_id=manifest.collection_id)
    claim_index_name = index_name or manifest.index_names.claim_events

    events = load_events()
    if not events:
        logger.error("no claim events to index")
        return 1

    by_video: dict[str, list[ClaimEvent]] = {}
    for event in events:
        by_video.setdefault(event.video_id, []).append(event)

    failures = 0
    for video_id, video_events in by_video.items():
        records = [event.to_index_record() for event in video_events]
        video = manifest.by_video_id(video_id)
        if video is None or not _ensure_index(
            adapter,
            video,
            records=records,
            name=claim_index_name,
            fields=CLAIM_EVENT_INDEX_FIELDS,
        ):
            failures += 1

    accepted_findings: list[TimelineFinding] = []
    if failures == 0:
        accepted_findings = _accepted_findings(adapter, manifest, events)
        if not accepted_findings:
            logger.error("no timeline findings passed the evidence gate")
            failures += 1
        else:
            failures += _index_findings(
                adapter,
                manifest,
                events,
                accepted_findings,
            )

    logger.info("--- index report ---")
    logger.info(
        "claim videos=%d findings=%d failures=%d",
        len(by_video),
        len(accepted_findings),
        failures,
    )
    if failures == 0:
        manifest.index_version = _index_version(events, accepted_findings)
    save_manifest(manifest)
    return 1 if failures else 0


def _ensure_index(
    adapter: VideoDBAdapter,
    video: ManifestVideo,
    *,
    records: list[dict[str, object]],
    name: str,
    fields: dict[str, list[str]],
) -> bool:
    """Create one index or reuse a ready index with the same name."""
    assert video.video_id
    try:
        existing = next(
            (
                index
                for index in adapter.list_indexes(video.video_id)
                if index.name == name and index.is_successful
            ),
            None,
        )
        if existing is not None:
            video.index_ids[name] = existing.index_id
            logger.info(
                "reuse %s for %s (index_id=%s records=%s)",
                name,
                video.video_id,
                existing.index_id,
                existing.record_count,
            )
            return True

        logger.info(
            "indexing %d records for %s as %s",
            len(records),
            video.video_id,
            name,
        )
        index = adapter.create_index(
            video.video_id,
            records=records,
            name=name,
            fields=fields,
        )
    except VideoDBUnavailableError as error:
        logger.error("FAILED %s — %s", video.video_id, error)
        return False

    if index is None:
        logger.error("FAILED %s — index creation returned nothing", video.video_id)
        return False
    try:
        index.wait_until_complete(timeout=INDEX_TIMEOUT_SECONDS)
    except TimeoutError as error:
        logger.error("FAILED %s — %s", video.video_id, error)
        return False
    if not index.is_successful:
        logger.error(
            "FAILED %s — index status=%s error=%s",
            video.video_id,
            index.status,
            index.error,
        )
        return False

    video.index_ids[name] = index.index_id
    logger.info(
        "  %s ready: index_id=%s records=%s use_for=%s",
        video.video_id,
        index.index_id,
        index.record_count,
        index.use_for,
    )
    return True


def _accepted_findings(
    adapter: VideoDBAdapter,
    manifest: ArchiveManifest,
    events: list[ClaimEvent],
) -> list[TimelineFinding]:
    timeline_events = _timeline_events(manifest, events)
    logger.info(
        "materializing findings from %d/%d archive-focused events",
        len(timeline_events),
        len(events),
    )
    diff = compare_events(timeline_events)
    shot_result = hydrate_shots(
        timeline_events,
        {},
        manifest,
        adapter,
        padding_seconds=get_settings().clip_padding_seconds,
    )
    for rejection in shot_result.rejections:
        logger.warning("shot rejected %s — %s", rejection.event_id, rejection.reason)
    gate = apply_gate(diff.findings, timeline_events, shot_result.shots)
    for rejection in gate.rejections:
        logger.warning(
            "finding rejected %s — %s", rejection.finding_id, rejection.reason
        )
    return gate.accepted


def _timeline_events(
    manifest: ArchiveManifest,
    events: list[ClaimEvent],
) -> list[ClaimEvent]:
    """Select the archive's central timeline without inventing a finding.

    The custom claim index retains every validated record. The aggregate
    finding index is narrower: it materializes comparisons about the locked
    archive subject, plus explicit corrections and the manually verified
    fixture windows. This keeps evidence-gated stream verification bounded
    while every underlying claim remains searchable.
    """
    verified: list[tuple[str, float, float]] = []
    for window in manifest.verified_windows:
        video = manifest.by_slug(window.video_slug)
        if video and video.video_id:
            verified.append((video.video_id, window.start, window.end))

    return [
        event
        for event in events
        if event.subject.strip().lower() == "artemis i launch"
        or str(event.claim_type) == "correction"
        or any(
            event.video_id == video_id
            and event.start < end
            and start < event.end
            for video_id, start, end in verified
        )
    ]


def _index_findings(
    adapter: VideoDBAdapter,
    manifest: ArchiveManifest,
    events: list[ClaimEvent],
    findings: list[TimelineFinding],
) -> int:
    events_by_id = {event.event_id: event for event in events}
    grouped: dict[str, list[dict[str, object]]] = {}

    for finding in findings:
        supporting = [
            events_by_id[event_id]
            for event_id in finding.event_ids
            if event_id in events_by_id
        ]
        if not supporting:
            continue
        anchor = max(
            supporting,
            key=lambda event: (event.source_date, event.start, event.event_id),
        )
        grouped.setdefault(anchor.video_id, []).append(
            finding.to_index_record(
                anchor.source_date.isoformat(),
                anchor.start,
                anchor.end,
            )
        )

    failures = 0
    for video_id, records in grouped.items():
        video = manifest.by_video_id(video_id)
        if video is None or not _ensure_index(
            adapter,
            video,
            records=records,
            name=manifest.index_names.timeline_findings,
            fields=TIMELINE_FINDING_INDEX_FIELDS,
        ):
            failures += 1
    return failures


def _index_version(
    events: list[ClaimEvent],
    findings: list[TimelineFinding],
) -> str:
    payload = {
        "events": [
            event.model_dump(mode="json")
            for event in sorted(events, key=lambda item: item.event_id)
        ],
        "findings": [
            finding.model_dump(mode="json")
            for finding in sorted(findings, key=lambda item: item.finding_id)
        ],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return f"sha256:{digest[:16]}"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Build the custom claim-event index.")
    parser.add_argument("--index-name", help="Override the manifest's index name.")
    args = parser.parse_args()

    try:
        return run(args.index_name)
    except MissingCredentialError as error:
        logger.error("%s", error)
        return 2
    except FileNotFoundError as error:
        logger.error("%s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
