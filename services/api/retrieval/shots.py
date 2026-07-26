"""Hydrate accepted claim events into real, playable evidence shots."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from ..adapters.videodb_client import VideoDBAdapter, VideoDBUnavailableError
from ..config import MissingCredentialError
from ..manifest import ArchiveManifest
from ..schemas.claim_event import ClaimEvent
from ..schemas.packet import EvidenceShot


@dataclass(frozen=True)
class ShotRejection:
    event_id: str
    reason: str


@dataclass
class ShotHydrationResult:
    shots: list[EvidenceShot] = field(default_factory=list)
    rejections: list[ShotRejection] = field(default_factory=list)


MAX_SHOT_WORKERS = 4


def hydrate_shots(
    events: list[ClaimEvent],
    hits_by_event_id: dict[str, Any],
    manifest: ArchiveManifest,
    adapter: VideoDBAdapter,
    *,
    padding_seconds: float,
) -> ShotHydrationResult:
    """Build one playable shot per event, rejecting any unverifiable source.

    Search-provided playback URLs are reused when present. Otherwise the exact
    event window, with the configured context padding, is rendered through
    VideoDB. Nothing is synthesized when playback generation fails.
    """
    result = ShotHydrationResult()
    if not events:
        return result

    completed: dict[int, EvidenceShot | ShotRejection] = {}
    with ThreadPoolExecutor(max_workers=min(MAX_SHOT_WORKERS, len(events))) as pool:
        futures = {
            pool.submit(
                _hydrate_one,
                event,
                hits_by_event_id.get(event.event_id),
                manifest,
                adapter,
                padding_seconds,
            ): position
            for position, event in enumerate(events)
        }
        for future in as_completed(futures):
            completed[futures[future]] = future.result()

    # Preserve the input's chronological/ranked order despite concurrent media
    # rendering, so timeline and reel behavior stays deterministic.
    for position in sorted(completed):
        item = completed[position]
        if isinstance(item, ShotRejection):
            result.rejections.append(item)
        else:
            result.shots.append(item)
    return result


def _hydrate_one(
    event: ClaimEvent,
    hit: Any,
    manifest: ArchiveManifest,
    adapter: VideoDBAdapter,
    padding_seconds: float,
) -> EvidenceShot | ShotRejection:
    source = manifest.by_video_id(event.video_id)
    if source is None:
        return ShotRejection(
            event_id=event.event_id,
            reason=f"video {event.video_id} is absent from the archive manifest",
        )

    stream_url = _text(_get(hit, "stream_url"))
    player_url = _text(_get(hit, "player_url"))
    start = _number(_get(hit, "start"))
    end = _number(_get(hit, "end"))

    if not stream_url:
        start = max(0.0, event.start - padding_seconds)
        end = event.end + padding_seconds
        try:
            stream = adapter.stream_window_ref(event.video_id, start, end)
        except (MissingCredentialError, VideoDBUnavailableError) as error:
            return ShotRejection(event_id=event.event_id, reason=str(error))
        stream_url = stream.stream_url
        player_url = stream.player_url
    else:
        start = event.start if start is None else start
        end = event.end if end is None else end

    return EvidenceShot(
        event_id=event.event_id,
        video_id=event.video_id,
        video_title=_text(_get(hit, "video_title")) or source.title,
        source_url=source.source_url,
        source_date=event.source_date,
        start=start,
        end=end,
        stream_url=stream_url,
        player_url=player_url,
        transcript_text=_text(_get(hit, "text")),
    )


def _get(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None
