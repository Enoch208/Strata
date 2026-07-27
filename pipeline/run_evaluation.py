"""Run both live evaluation arms and write an adjudication worksheet.

The worksheet deliberately leaves ``supported`` unset. A human must review each
atomic proposition against the cited transcript windows before
``pipeline.finalize_evaluation`` can produce publishable results.

    ./.venv/bin/python -m pipeline.run_evaluation
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from services.api.adapters.videodb_client import VideoDBAdapter
from services.api.config import get_settings
from services.api.investigation_engine import InvestigationEngine
from services.api.manifest import load_manifest
from services.api.schemas.packet import InvestigationState

from .evaluate import (
    EvaluationCase,
    EvidenceUnit,
    TranscriptDocument,
    build_baseline_prompt,
    concatenate_transcripts,
    load_cases,
)

logger = logging.getLogger("pipeline.run_evaluation")

WORKSHEET_PATH = Path(__file__).resolve().parents[1] / "data" / "evaluation_worksheet.json"


class NaiveOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    evidence: list[EvidenceUnit] = Field(default_factory=list)
    propositions: list[str] = Field(default_factory=list)


def _documents(adapter: VideoDBAdapter) -> list[TranscriptDocument]:
    manifest = load_manifest()
    documents: list[TranscriptDocument] = []
    for video in manifest.videos:
        assert video.video_id
        rows = adapter.transcript_segments(video.video_id)
        documents.append(
            TranscriptDocument(
                video_id=video.video_id,
                title=video.title,
                source_date=video.source_date,
                segments=tuple(
                    (
                        float(row["start"]),
                        float(row["end"]),
                        str(row["text"]),
                    )
                    for row in rows
                ),
            )
        )
    return documents


def _naive_prompt(question: str, corpus: str) -> str:
    return (
        build_baseline_prompt(question, corpus)
        + """

Return ONLY this JSON shape:
{
  "answer": "concise answer",
  "evidence": [
    {"video_id": "exact ID above", "start": 0.0, "end": 1.0}
  ],
  "propositions": [
    "One atomic factual assertion from the answer."
  ]
}
List every factual assertion separately. If the archive does not establish an
answer, say so in "answer" and return empty evidence and propositions arrays.
"""
    )


def _unwrap(raw: Any) -> Any:
    if isinstance(raw, dict) and "output" in raw:
        return _unwrap(raw["output"])
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def _load_partial() -> dict[str, Any]:
    if not WORKSHEET_PATH.exists():
        return {"worksheet_version": "evaluation-worksheet-v1", "arms": []}
    return json.loads(WORKSHEET_PATH.read_text(encoding="utf-8"))


def _save(payload: dict[str, Any]) -> None:
    WORKSHEET_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _arm(payload: dict[str, Any], name: str) -> dict[str, Any]:
    existing = next(
        (item for item in payload["arms"] if item.get("arm") == name),
        None,
    )
    if existing is not None:
        return existing
    item = {"arm": name, "cases": []}
    payload["arms"].append(item)
    return item


def _worksheet_propositions(values: list[str]) -> list[dict[str, Any]]:
    return [{"text": value, "supported": None} for value in values if value.strip()]


def _validate_strata_case(
    case: EvaluationCase,
    investigation: Any,
) -> None:
    """Fail the run when a frozen structural requirement is not satisfied."""
    if len(investigation.events) < case.expected_min_events:
        raise RuntimeError(
            f"{case.case_id}: found {len(investigation.events)} events, "
            f"requires at least {case.expected_min_events}"
        )
    if case.require_novel_challenge_source:
        challenge = investigation.challenge
        if challenge is None:
            raise RuntimeError(f"{case.case_id}: required challenge did not run")
        initial = set(challenge.initial_accepted_video_ids)
        challenge_ids = set(challenge.challenge_accepted_video_ids)
        if not challenge_ids - initial:
            raise RuntimeError(
                f"{case.case_id}: challenge_video_ids - initial_video_ids "
                "difference is empty"
            )


def run(
    selected_arms: set[str] | None = None,
    *,
    restart_arms: set[str] | None = None,
) -> int:
    manifest = load_manifest()
    if manifest.index_status != "ready":
        raise RuntimeError("all six videos must be ready before evaluation")
    cases = load_cases()
    adapter = VideoDBAdapter(collection_id=manifest.collection_id)
    settings = get_settings()
    payload = _load_partial()
    payload["model"] = settings.extraction_model
    payload["temperature"] = settings.extraction_temperature
    payload["max_answer_tokens"] = 600
    payload["transcript_revision"] = manifest.manifest_version
    selected = selected_arms or {"naive", "strata"}
    restart = restart_arms or set()
    payload["arms"] = [
        arm for arm in payload["arms"] if arm.get("arm") not in restart
    ]

    if "naive" in selected:
        naive = _arm(payload, "naive")
        completed_naive = {item["case_id"] for item in naive["cases"]}
        documents = _documents(adapter)
        corpus = concatenate_transcripts(documents)
        for case in cases:
            if case.case_id in completed_naive:
                continue
            logger.info("naive %s", case.case_id)
            try:
                result = NaiveOutput.model_validate(
                    _unwrap(adapter.generate_text(_naive_prompt(case.question, corpus)))
                )
                item = {
                    "case_id": case.case_id,
                    "answer": result.answer,
                    "surfaced_evidence": [
                        unit.model_dump(mode="json") for unit in result.evidence
                    ],
                    "propositions": _worksheet_propositions(result.propositions),
                }
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as error:
                item = {
                    "case_id": case.case_id,
                    "answer": "",
                    "surfaced_evidence": [],
                    "propositions": [],
                    "error": str(error),
                }
            naive["cases"].append(item)
            _save(payload)

    if "strata" in selected:
        strata = _arm(payload, "strata")
        completed_strata = {item["case_id"] for item in strata["cases"]}
        engine = InvestigationEngine()
        for case in cases:
            if case.case_id in completed_strata:
                continue
            logger.info("strata %s", case.case_id)
            investigation = engine.create(case.question, manifest.archive_id)
            if case.run_challenge and investigation.state is InvestigationState.complete:
                engine.challenge(investigation.investigation_id)
            _validate_strata_case(case, investigation)
            displayable = [
                sentence.text
                for sentence in investigation.summary_sentences
                if sentence.is_displayable
            ]
            strata["cases"].append(
                {
                    "case_id": case.case_id,
                    "answer": " ".join(displayable),
                    "state": str(investigation.state),
                    "surfaced_evidence": [
                        {
                            "video_id": event.video_id,
                            "start": event.start,
                            "end": event.end,
                        }
                        for event in investigation.events
                    ],
                    "propositions": _worksheet_propositions(displayable),
                    "investigation": investigation.model_dump(mode="json"),
                }
            )
            _save(payload)

    logger.info("wrote manual adjudication worksheet to %s", WORKSHEET_PATH)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Run the live two-arm evaluation.")
    parser.add_argument(
        "--arm",
        action="append",
        choices=("naive", "strata"),
        help="Run only this arm (repeatable).",
    )
    parser.add_argument(
        "--restart-arm",
        action="append",
        choices=("naive", "strata"),
        default=[],
        help="Discard and rerun this generated worksheet arm.",
    )
    args = parser.parse_args()
    return run(
        set(args.arm) if args.arm else None,
        restart_arms=set(args.restart_arm),
    )


if __name__ == "__main__":
    raise SystemExit(main())
