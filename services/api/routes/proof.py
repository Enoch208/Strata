"""`GET /api/proof` — reproducible evaluation and repository integrity."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

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
CASES_PATH = REPO_ROOT / "data" / "evaluation_cases.json"
VERIFICATION_PATH = REPO_ROOT / "data" / "submission_verification.json"


def _metric(numerator: int, denominator: int) -> MetricProof:
    return MetricProof(
        numerator=numerator,
        denominator=denominator,
        percentage=(
            numerator / denominator * 100.0
            if denominator
            else None
        ),
    )


def _evaluation() -> tuple[int, list[EvaluationArmProof]]:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    labels = {
        "naive": "All transcripts → LLM",
        "claimtrail": "Strata",
    }
    arms: list[EvaluationArmProof] = []
    for result in results:
        observations = {
            item["case_id"]: item
            for item in result["cases"]
        }
        found = 0
        gold = 0
        unsupported = 0
        factual = 0
        for case in cases:
            observation = observations[case["case_id"]]
            gold_units = case["expected_evidence"]
            surfaced = observation["surfaced_evidence"]
            gold += len(gold_units)
            found += sum(
                any(_overlaps(unit, candidate) for candidate in surfaced)
                for unit in gold_units
            )
            propositions = observation["propositions"]
            factual += len(propositions)
            unsupported += sum(
                not proposition["supported"]
                for proposition in propositions
            )
        arm = result["arm"]
        arms.append(
            EvaluationArmProof(
                arm=arm,
                label=labels[arm],
                retrieval_recall=_metric(found, gold),
                unsupported_claims=_metric(unsupported, factual),
            )
        )
    return len(cases), arms


def _overlaps(left: dict[str, object], right: dict[str, object]) -> bool:
    return (
        left["video_id"] == right["video_id"]
        and float(left["start"]) < float(right["end"])
        and float(right["start"]) < float(left["end"])
    )


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
