"""Transcript chunking for claim extraction.

PRD section 11.4: transcript artifacts are processed in bounded, overlapping
chunks. Overlap matters because a claim straddling a chunk boundary would
otherwise lose either its subject or its timestamp.

Pure functions over `{start, end, text}` segments — no SDK types, so this is
fully testable without credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

#: Target characters per chunk. Large enough to hold an exchange, small enough
#: that the model still attends to every sentence.
DEFAULT_CHUNK_CHARS = 3500
#: Characters of trailing context repeated at the head of the next chunk.
DEFAULT_OVERLAP_CHARS = 500


@dataclass(frozen=True)
class TranscriptSegment:
    """One timed transcript segment, validated at the boundary."""

    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TranscriptChunk:
    """A bounded window of transcript with its true source timestamps."""

    index: int
    start: float
    end: float
    text: str
    segments: tuple[TranscriptSegment, ...]

    @property
    def duration(self) -> float:
        return self.end - self.start


def parse_segments(raw: Iterable[Any]) -> list[TranscriptSegment]:
    """Validate raw SDK transcript rows into typed segments.

    Rows missing timestamps or text are dropped rather than defaulted — an
    invented timestamp is precisely what guardrail 5 forbids.
    """
    segments: list[TranscriptSegment] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        start, end, text = row.get("start"), row.get("end"), row.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            continue
        if end <= start:
            continue
        segments.append(TranscriptSegment(start=float(start), end=float(end), text=text.strip()))

    segments.sort(key=lambda segment: (segment.start, segment.end))
    return segments


def chunk_transcript(
    segments: list[TranscriptSegment],
    *,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[TranscriptChunk]:
    """Group segments into overlapping chunks that keep real timestamps.

    A chunk's `start`/`end` are the true bounds of the segments it contains, so
    any timestamp the model is shown is a timestamp the archive actually has.
    """
    if not segments:
        return []
    if overlap_chars >= chunk_chars:
        raise ValueError("overlap_chars must be smaller than chunk_chars")

    chunks: list[TranscriptChunk] = []
    current: list[TranscriptSegment] = []
    current_chars = 0
    index = 0

    for segment in segments:
        current.append(segment)
        current_chars += len(segment.text) + 1

        if current_chars < chunk_chars:
            continue

        chunks.append(_build_chunk(index, current))
        index += 1
        current = _overlap_tail(current, overlap_chars)
        current_chars = sum(len(segment.text) + 1 for segment in current)

    # The trailing remainder is only its own chunk when it carries new material
    # beyond the overlap already emitted.
    if current and (not chunks or _has_new_content(current, chunks[-1])):
        chunks.append(_build_chunk(index, current))

    return chunks


def _build_chunk(index: int, segments: list[TranscriptSegment]) -> TranscriptChunk:
    return TranscriptChunk(
        index=index,
        start=segments[0].start,
        end=segments[-1].end,
        text=" ".join(segment.text for segment in segments),
        segments=tuple(segments),
    )


def _overlap_tail(segments: list[TranscriptSegment], overlap_chars: int) -> list[TranscriptSegment]:
    """The trailing segments to repeat at the head of the next chunk."""
    tail: list[TranscriptSegment] = []
    total = 0
    for segment in reversed(segments):
        if total >= overlap_chars:
            break
        tail.append(segment)
        total += len(segment.text) + 1
    return list(reversed(tail))


def _has_new_content(current: list[TranscriptSegment], previous: TranscriptChunk) -> bool:
    return current[-1].end > previous.end


def render_for_prompt(chunk: TranscriptChunk) -> str:
    """Render a chunk with per-segment timestamps the model must quote back."""
    return "\n".join(
        f"[{segment.start:.2f} - {segment.end:.2f}] {segment.text}" for segment in chunk.segments
    )
