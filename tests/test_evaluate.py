"""Evaluation baseline locking and comparative metric calculation."""

import json
from datetime import date

import pytest

from pipeline.evaluate import (
    ArmAdjudication,
    AtomicProposition,
    CaseAdjudication,
    EvaluationCase,
    EvidenceUnit,
    TranscriptDocument,
    build_baseline_prompt,
    concatenate_transcripts,
    load_cases,
    score_arm,
)
from services.api.schemas.enums import FindingLabel
from services.api.manifest import load_manifest


def case(case_id: str, video_id: str = "vid_a") -> EvaluationCase:
    return EvaluationCase(
        case_id=case_id,
        question=f"Question {case_id}?",
        expected_evidence=[EvidenceUnit(video_id=video_id, start=10, end=20)],
        expected_min_events=1,
        allowed_labels=[FindingLabel.new_information],
    )


def test_baseline_concatenates_every_transcript_chronologically() -> None:
    later = TranscriptDocument(
        "vid_b", "Later", date(2022, 9, 30), ((20, 25, "later words"),)
    )
    earlier = TranscriptDocument(
        "vid_a", "Earlier", date(2022, 9, 3), ((10, 15, "earlier words"),)
    )

    corpus = concatenate_transcripts([later, earlier])

    assert corpus.index("VIDEO ID: vid_a") < corpus.index("VIDEO ID: vid_b")
    assert "[10.00 - 15.00] earlier words" in corpus
    assert "[20.00 - 25.00] later words" in corpus


def test_baseline_prompt_forbids_outside_knowledge_and_invented_times() -> None:
    prompt = build_baseline_prompt("Why?", "the corpus")
    assert "complete timestamped archive" in prompt
    assert "Do not use outside knowledge" in prompt
    assert "do not invent timestamps" in prompt


def test_metrics_report_numerators_denominators_and_percentages() -> None:
    cases = [case("one"), case("two", "vid_b")]
    arm = ArmAdjudication(
        arm="strata",
        model="locked-model",
        transcript_revision="revision-1",
        temperature=0,
        max_answer_tokens=600,
        cases=[
            CaseAdjudication(
                case_id="one",
                surfaced_evidence=[EvidenceUnit(video_id="vid_a", start=12, end=18)],
                propositions=[
                    AtomicProposition(text="supported", supported=True),
                    AtomicProposition(text="unsupported", supported=False),
                ],
            ),
            CaseAdjudication(
                case_id="two",
                surfaced_evidence=[],
                propositions=[AtomicProposition(text="supported", supported=True)],
            ),
        ],
    )

    metrics = score_arm(cases, arm)

    assert (metrics.relevant_event_recall.numerator, metrics.relevant_event_recall.denominator) == (
        1,
        2,
    )
    assert metrics.relevant_event_recall.percentage == 50.0
    assert (
        metrics.unsupported_claim_rate.numerator,
        metrics.unsupported_claim_rate.denominator,
    ) == (1, 3)


def test_case_loader_requires_exactly_twelve_unique_cases(tmp_path) -> None:
    path = tmp_path / "cases.json"
    path.write_text(json.dumps([case("only").model_dump(mode="json")]), encoding="utf-8")

    with pytest.raises(ValueError, match="exactly 12"):
        load_cases(path)


def test_frozen_repository_cases_use_real_manifest_video_ids() -> None:
    cases = load_cases()
    manifest_ids = {
        video.video_id for video in load_manifest().videos if video.video_id
    }

    assert len(cases) == 12
    assert manifest_ids
    assert all(
        unit.video_id in manifest_ids
        for item in cases
        for unit in item.expected_evidence
    )
