"""`GET /api/proof` — reproducible evaluation and repository integrity."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from pipeline.evaluate import ArmAdjudication, load_cases, score_arm

from ..config import REPO_ROOT
from ..manifest import load_manifest
from ..schemas.proof import (
    EvaluationArmProof,
    IndexProof,
    MetricProof,
    SubmissionProof,
    VerificationProof,
)

router = APIRouter(tags=["proof"])

RESULTS_PATH = REPO_ROOT / "data" / "evaluation_results.json"
VERIFICATION_PATH = REPO_ROOT / "data" / "submission_verification.json"


def _metric(metric: object) -> MetricProof:
    return MetricProof(
        numerator=metric.numerator,  # type: ignore[attr-defined]
        denominator=metric.denominator,  # type: ignore[attr-defined]
        percentage=metric.percentage,  # type: ignore[attr-defined]
    )


def _evaluation() -> tuple[int, list[EvaluationArmProof]]:
    cases = load_cases()
    raw = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    labels = {
        "naive": "All transcripts → LLM",
        "claimtrail": "Strata",
    }
    arms: list[EvaluationArmProof] = []
    for item in raw:
        adjudication = ArmAdjudication.model_validate(item)
        metrics = score_arm(cases, adjudication)
        arms.append(
            EvaluationArmProof(
                arm=adjudication.arm,
                label=labels[adjudication.arm],
                retrieval_recall=_metric(metrics.relevant_event_recall),
                unsupported_claims=_metric(metrics.unsupported_claim_rate),
            )
        )
    return len(cases), arms


def _verification(path: Path = VERIFICATION_PATH) -> VerificationProof:
    if not path.is_file():
        return VerificationProof(tests_passed=0)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return VerificationProof.model_validate(payload)


@router.get("/api/proof", response_model=SubmissionProof)
def get_proof() -> SubmissionProof:
    manifest = load_manifest()
    evaluation_cases, evaluation = _evaluation()
    ready = manifest.ready_videos
    return SubmissionProof(
        distinct_video_ids=len(
            {video.video_id for video in manifest.videos if video.video_id}
        ),
        index_proof=IndexProof(
            spoken_word_ready=all("speech" in video.index_ids for video in ready)
            and len(ready) == len(manifest.videos),
            ocr_ready=all("onscreen_text" in video.index_ids for video in ready)
            and len(ready) == len(manifest.videos),
            visual_ready=all("scene_context" in video.index_ids for video in ready)
            and len(ready) == len(manifest.videos),
            claim_event_ready=all(
                manifest.index_names.claim_events in video.index_ids
                for video in ready
            )
            and len(ready) == len(manifest.videos),
            timeline_finding_ready=all(
                manifest.index_names.timeline_findings in video.index_ids
                for video in ready
            )
            and len(ready) == len(manifest.videos),
        ),
        evaluation_cases=evaluation_cases,
        evaluation=evaluation,
        verification=_verification(),
    )
