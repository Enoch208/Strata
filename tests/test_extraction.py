"""Claim schema validation and chunking (PRD section 19, required tests)."""

from datetime import date

import pytest

from pipeline.extract_claims import ContextScene, context_for_chunk
from services.api.extraction.chunks import (
    TranscriptSegment,
    chunk_transcript,
    parse_segments,
    render_for_prompt,
)
from services.api.extraction.prompt import build_prompt, parse_response, validate_records
from services.api.schemas.claim_event import CLAIM_EVENT_INDEX_FIELDS
from services.api.schemas.enums import Certainty, ClaimStatus, ClaimType


def segments(count: int = 40, *, chars: int = 120) -> list[TranscriptSegment]:
    return [
        TranscriptSegment(start=float(i * 5), end=float(i * 5 + 5), text="word " * (chars // 5))
        for i in range(count)
    ]


class TestArtifactContext:
    def test_only_overlapping_ocr_and_visual_scenes_are_rendered(self) -> None:
        scenes = [
            ContextScene("onscreen_text", 0, 5, "too early"),
            ContextScene("onscreen_text", 10, 20, "LAUNCH STATUS"),
            ContextScene("scene_context", 15, 25, "A mission official is speaking."),
        ]

        context = context_for_chunk(scenes, 12, 22)

        assert context is not None
        assert "LAUNCH STATUS" in context
        assert "mission official" in context
        assert "too early" not in context

    def test_empty_overlap_returns_none(self) -> None:
        scenes = [ContextScene("onscreen_text", 0, 5, "old")]
        assert context_for_chunk(scenes, 10, 20) is None


def test_claim_index_exposes_every_required_filter_field() -> None:
    assert {
        "source_date",
        "subject",
        "claim_type",
        "status",
        "certainty",
    }.issubset(CLAIM_EVENT_INDEX_FIELDS["filter"])


class TestParseSegments:
    def test_valid_rows_are_kept(self) -> None:
        rows = [{"start": 0.0, "end": 2.0, "text": "Good afternoon."}]
        assert parse_segments(rows) == [TranscriptSegment(0.0, 2.0, "Good afternoon.")]

    @pytest.mark.parametrize(
        "row",
        [
            {"start": None, "end": 2.0, "text": "hi"},
            {"start": 0.0, "end": None, "text": "hi"},
            {"start": 2.0, "end": 1.0, "text": "hi"},
            {"start": 0.0, "end": 2.0, "text": "   "},
            {"start": 0.0, "end": 2.0},
            "not a dict",
        ],
    )
    def test_unusable_rows_are_dropped_not_defaulted(self, row: object) -> None:
        # Guardrail 5: never invent a timestamp where the artifact has none.
        assert parse_segments([row]) == []

    def test_rows_are_sorted_by_time(self) -> None:
        rows = [{"start": 5.0, "end": 6.0, "text": "b"}, {"start": 1.0, "end": 2.0, "text": "a"}]
        assert [s.text for s in parse_segments(rows)] == ["a", "b"]


class TestChunking:
    def test_empty_transcript_yields_no_chunks(self) -> None:
        assert chunk_transcript([]) == []

    def test_chunks_carry_true_segment_bounds(self) -> None:
        chunks = chunk_transcript(segments(), chunk_chars=600, overlap_chars=120)

        assert chunks
        for chunk in chunks:
            assert chunk.start == chunk.segments[0].start
            assert chunk.end == chunk.segments[-1].end
            assert chunk.end > chunk.start

    def test_chunks_overlap_so_boundary_claims_survive(self) -> None:
        chunks = chunk_transcript(segments(), chunk_chars=600, overlap_chars=200)

        assert len(chunks) > 1
        for earlier, later in zip(chunks, chunks[1:]):
            assert later.start < earlier.end

    def test_whole_transcript_is_covered(self) -> None:
        source = segments()
        chunks = chunk_transcript(source, chunk_chars=600, overlap_chars=120)

        assert chunks[0].start == source[0].start
        assert chunks[-1].end == source[-1].end

    def test_overlap_must_be_smaller_than_the_chunk(self) -> None:
        with pytest.raises(ValueError):
            chunk_transcript(segments(), chunk_chars=100, overlap_chars=100)

    def test_rendered_prompt_shows_real_timestamps(self) -> None:
        chunk = chunk_transcript(segments(3), chunk_chars=10_000)[0]
        rendered = render_for_prompt(chunk)

        assert rendered.startswith("[0.00 - 5.00]")


class TestParseResponse:
    def test_accepts_a_bare_array(self) -> None:
        records, error = parse_response('[{"start": 1, "end": 2}]')
        assert error is None
        assert records == [{"start": 1, "end": 2}]

    def test_accepts_an_already_decoded_list(self) -> None:
        records, error = parse_response([{"start": 1}])
        assert error is None and records == [{"start": 1}]

    def test_unwraps_a_keyed_object(self) -> None:
        records, error = parse_response({"events": [{"start": 1}]})
        assert error is None and records == [{"start": 1}]

    def test_unwraps_the_sdk_output_envelope(self) -> None:
        records, error = parse_response({"output": {"events": [{"start": 1}]}})
        assert error is None and records == [{"start": 1}]

    def test_surfaces_a_model_error_envelope(self) -> None:
        records, error = parse_response({"output": {"error": "bad schema"}})
        assert records == []
        assert error == "model returned an error: bad schema"

    def test_extracts_json_from_surrounding_prose(self) -> None:
        records, error = parse_response('Here you go:\n[{"start": 1}]\nHope that helps.')
        assert error is None and records == [{"start": 1}]

    def test_non_json_is_an_error_not_a_guess(self) -> None:
        records, error = parse_response("I could not find any claims.")
        assert records == [] and error is not None

    def test_malformed_json_is_reported(self) -> None:
        records, error = parse_response('[{"start": 1,]')
        assert records == []
        assert error is not None and "invalid JSON" in error


class TestValidateRecords:
    @pytest.fixture
    def chunk(self):
        return chunk_transcript(segments(10), chunk_chars=10_000)[0]

    def kwargs(self) -> dict:
        return {
            "video_id": "m-123",
            "source_date": date(2022, 9, 3),
            "source_organization": "NASA",
            "extraction_model": "pro",
        }

    def test_valid_record_becomes_a_claim_event(self, chunk) -> None:
        records = [
            {
                "start": 10.0,
                "end": 25.0,
                "speaker_role": "NASA mission official",
                "subject": "Artemis I launch",
                "claim_type": "delay_reason",
                "claim_text": "The attempt was waved off after a hydrogen leak.",
                "normalized_value": "hydrogen_leak",
                "status": "scrubbed",
                "certainty": "explicit",
            }
        ]

        outcome = validate_records(records, chunk, **self.kwargs())

        assert outcome.rejections == []
        event = outcome.events[0]
        assert event.claim_type is ClaimType.delay_reason
        assert event.status is ClaimStatus.scrubbed
        assert event.certainty is Certainty.explicit
        assert event.source_organization == "NASA"

    def test_timestamp_outside_the_chunk_is_rejected(self, chunk) -> None:
        # A window the model was never shown is a fabricated citation.
        records = [{"start": 9_000.0, "end": 9_010.0, "claim_text": "Something."}]

        outcome = validate_records(records, chunk, **self.kwargs())

        assert outcome.events == []
        assert "outside the chunk window" in outcome.rejections[0]

    def test_timestamps_are_clamped_to_the_chunk(self, chunk) -> None:
        records = [{"start": -50.0, "end": 99_999.0, "claim_text": "Something."}]

        outcome = validate_records(records, chunk, **self.kwargs())

        event = outcome.events[0]
        assert event.start >= chunk.start
        assert event.end <= chunk.end

    def test_missing_timestamps_are_rejected(self, chunk) -> None:
        outcome = validate_records([{"claim_text": "No times."}], chunk, **self.kwargs())

        assert outcome.events == []
        assert outcome.rejections

    def test_empty_claim_text_is_rejected_with_a_reason(self, chunk) -> None:
        records = [{"start": 10.0, "end": 25.0, "claim_text": "   "}]

        outcome = validate_records(records, chunk, **self.kwargs())

        assert outcome.events == []
        assert "claim_text" in outcome.rejections[0]

    def test_unknown_enum_values_fall_back_rather_than_crash(self, chunk) -> None:
        records = [
            {
                "start": 10.0,
                "end": 25.0,
                "claim_text": "A statement.",
                "claim_type": "wild_guess",
                "status": "invented",
                "certainty": "vibes",
            }
        ]

        outcome = validate_records(records, chunk, **self.kwargs())

        event = outcome.events[0]
        assert event.claim_type is ClaimType.other
        assert event.status is ClaimStatus.unknown
        assert event.certainty is Certainty.uncertain

    def test_event_ids_are_unique_within_a_chunk(self, chunk) -> None:
        records = [
            {"start": 10.0, "end": 25.0, "claim_text": "One."},
            {"start": 26.0, "end": 40.0, "claim_text": "Two."},
        ]

        outcome = validate_records(records, chunk, **self.kwargs())

        assert len({event.event_id for event in outcome.events}) == 2


class TestPrompt:
    def test_prompt_forbids_outside_knowledge_and_invented_times(self) -> None:
        chunk = chunk_transcript(segments(3), chunk_chars=10_000)[0]

        prompt = build_prompt(
            chunk, title="A briefing", organization="NASA", source_date=date(2022, 9, 3)
        )

        assert "Never invent a time" in prompt
        assert "never add outside knowledge" in prompt.lower()
        assert "lie, false" in prompt
        assert "[0.00 - 5.00]" in prompt
        assert '{"events": []}' in prompt

    def test_prompt_lists_only_controlled_enum_values(self) -> None:
        chunk = chunk_transcript(segments(3), chunk_chars=10_000)[0]

        prompt = build_prompt(
            chunk, title="A briefing", organization="NASA", source_date=date(2022, 9, 3)
        )

        assert "delay_reason" in prompt
        assert "rolled_back" in prompt
