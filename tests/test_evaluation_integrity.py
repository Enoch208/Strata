"""Frozen evaluation requirements must fail closed."""

from types import SimpleNamespace

import pytest

from pipeline.evaluate import EvaluationCase
from pipeline.run_evaluation import _validate_claimtrail_case


def test_required_challenge_novelty_fails_when_source_difference_is_empty() -> None:
    case = EvaluationCase(
        case_id="novelty",
        question="What changed?",
        expected_evidence=[],
        expected_min_events=1,
        allowed_labels=["new_information"],
        run_challenge=True,
        require_novel_challenge_source=True,
    )
    investigation = SimpleNamespace(
        events=[object()],
        challenge=SimpleNamespace(
            initial_accepted_video_ids=["video-a"],
            challenge_accepted_video_ids=["video-a"],
        ),
    )

    with pytest.raises(RuntimeError, match="difference is empty"):
        _validate_claimtrail_case(case, investigation)


def test_required_challenge_novelty_passes_for_a_new_source() -> None:
    case = EvaluationCase(
        case_id="novelty",
        question="What changed?",
        expected_evidence=[],
        expected_min_events=1,
        allowed_labels=["new_information"],
        run_challenge=True,
        require_novel_challenge_source=True,
    )
    investigation = SimpleNamespace(
        events=[object(), object()],
        challenge=SimpleNamespace(
            initial_accepted_video_ids=["video-a"],
            challenge_accepted_video_ids=["video-b"],
        ),
    )

    _validate_claimtrail_case(case, investigation)
