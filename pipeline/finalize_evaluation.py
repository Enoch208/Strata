"""Validate a manually adjudicated worksheet and publish evaluation results."""

from __future__ import annotations

import json
from pathlib import Path

from .evaluate import (
    ArmAdjudication,
    AtomicProposition,
    CaseAdjudication,
    EvidenceUnit,
    load_cases,
    score_arm,
)
from .run_evaluation import WORKSHEET_PATH

RESULTS_PATH = Path(__file__).resolve().parents[1] / "data" / "evaluation_results.json"


def run() -> int:
    worksheet = json.loads(WORKSHEET_PATH.read_text(encoding="utf-8"))
    cases = load_cases()
    arms: list[ArmAdjudication] = []
    for raw_arm in worksheet["arms"]:
        observations: list[CaseAdjudication] = []
        for item in raw_arm["cases"]:
            propositions = item.get("propositions", [])
            unset = [p["text"] for p in propositions if p.get("supported") is None]
            if unset:
                raise ValueError(
                    f"{raw_arm['arm']}/{item['case_id']} has unadjudicated propositions"
                )
            observations.append(
                CaseAdjudication(
                    case_id=item["case_id"],
                    surfaced_evidence=[
                        EvidenceUnit.model_validate(unit)
                        for unit in item["surfaced_evidence"]
                    ],
                    propositions=[
                        AtomicProposition.model_validate(proposition)
                        for proposition in propositions
                    ],
                )
            )
        arms.append(
            ArmAdjudication(
                arm=raw_arm["arm"],
                model=worksheet["model"],
                transcript_revision=worksheet["transcript_revision"],
                temperature=worksheet["temperature"],
                max_answer_tokens=worksheet["max_answer_tokens"],
                cases=observations,
            )
        )

    if {arm.arm for arm in arms} != {"naive", "strata"}:
        raise ValueError("worksheet must contain naive and strata arms")
    for arm in arms:
        # score_arm returns the metrics; they must be attached to the arm or the
        # published results file carries an adjudication with no numbers in it.
        arm.metrics = score_arm(cases, arm)
    RESULTS_PATH.write_text(
        json.dumps([arm.model_dump(mode="json") for arm in arms], indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
