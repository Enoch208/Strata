"""Measure the evidence-quality metrics that recall alone does not capture.

Retrieval recall says how much of the gold evidence an answer surfaced. It says
nothing about whether the answer can be *checked*, which is the property Strata
is built for. This harness measures three such properties over the frozen
12-case set, from real investigation responses:

- **Playable citation coverage** — displayed findings whose supporting events all
  resolve to a playable timestamped clip.
- **Auditable sentence mapping** — displayed factual sentences that carry the
  event IDs supporting them.
- **Challenge source novelty** — challenge cases that accepted evidence from a
  source video the first pass never used.

The naive transcript-dump arm scores zero on all three by construction, not by
measurement: it emits prose with no clips, no per-sentence event mapping, and has
no second retrieval pass. That is recorded as a structural zero and labelled as
such, never presented as an observed run.

    ./.venv/bin/python -m pipeline.coverage_metrics --base-url https://strata-api-eight.vercel.app
"""

from __future__ import annotations

import argparse
import json
import logging
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from services.api.config import DATA_DIR

from .evaluate import Metric, load_cases

logger = logging.getLogger("pipeline.coverage_metrics")

COVERAGE_PATH = DATA_DIR / "coverage_metrics.json"
ARCHIVE_ID = "artemis-i-2022"
REQUEST_TIMEOUT_SECONDS = 300


@dataclass
class CaseObservation:
    case_id: str
    state: str
    findings: int = 0
    findings_with_playable_evidence: int = 0
    displayed_sentences: int = 0
    displayed_sentences_with_events: int = 0
    challenge_ran: bool = False
    challenge_found_novel_source: bool = False
    novel_video_ids: list[str] = field(default_factory=list)
    error: str | None = None


@lru_cache(maxsize=1)
def _ssl_context() -> ssl.SSLContext:
    """Verified TLS context, using certifi's roots when the platform lacks them."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _post(base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    context = _ssl_context() if base_url.startswith("https://") else None
    with urllib.request.urlopen(
        request, timeout=REQUEST_TIMEOUT_SECONDS, context=context
    ) as response:
        return json.loads(response.read())


def observe_case(base_url: str, case) -> CaseObservation:
    """Run one evaluation case and measure what its answer exposes."""
    try:
        investigation = _post(
            base_url,
            "/api/investigations",
            {"query": case.question, "archive_id": ARCHIVE_ID},
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        return CaseObservation(case_id=case.case_id, state="request_failed", error=str(error))

    observation = CaseObservation(
        case_id=case.case_id, state=str(investigation.get("state"))
    )

    playable_event_ids = {
        shot["event_id"]
        for shot in investigation.get("shots", [])
        if shot.get("stream_url")
    }

    findings = investigation.get("findings", [])
    observation.findings = len(findings)
    observation.findings_with_playable_evidence = sum(
        bool(finding.get("event_ids"))
        and all(event_id in playable_event_ids for event_id in finding["event_ids"])
        for finding in findings
    )

    # Only sentences the product actually displays are auditable subjects; a
    # withheld "not established" sentence is not a claim being made.
    displayed = [
        sentence
        for sentence in investigation.get("summary_sentences", [])
        if sentence.get("support_status") == "supported"
    ]
    observation.displayed_sentences = len(displayed)
    observation.displayed_sentences_with_events = sum(
        bool(sentence.get("supported_by_event_ids")) for sentence in displayed
    )

    if not case.run_challenge:
        return observation

    challenge_path = f"/api/investigations/{investigation['investigation_id']}/challenge"
    try:
        challenge = _post(
            base_url,
            challenge_path,
            {
                "instruction": "Challenge this conclusion",
                "query": case.question,
                "archive_id": ARCHIVE_ID,
            },
        )
    except urllib.error.HTTPError as error:
        if error.code == 409:
            # The first pass returned insufficient evidence, so there is no
            # conclusion to challenge. This case is excluded from the novelty
            # denominator rather than counted as a novelty failure.
            observation.error = (
                "challenge not applicable: the first pass returned "
                f"{observation.state}, so there is no conclusion to challenge"
            )
            return observation
        if error.code != 422:
            observation.error = f"challenge failed: {error}"
            return observation
        # An older deployment rejects the rebuild fields it does not know about.
        # Retry without them so the harness can measure either version.
        try:
            challenge = _post(
                base_url, challenge_path, {"instruction": "Challenge this conclusion"}
            )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as retry_error:
            observation.error = f"challenge failed: {retry_error}"
            return observation
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        observation.error = f"challenge failed: {error}"
        return observation

    observation.challenge_ran = True
    observation.novel_video_ids = list(challenge.get("novel_accepted_video_ids") or [])
    observation.challenge_found_novel_source = bool(observation.novel_video_ids)
    return observation


def aggregate(observations: list[CaseObservation]) -> dict[str, Metric]:
    """Reduce per-case observations to the three published coverage metrics."""
    return {
        "playable_citation_coverage": Metric(
            numerator=sum(o.findings_with_playable_evidence for o in observations),
            denominator=sum(o.findings for o in observations),
        ),
        "auditable_sentence_mapping": Metric(
            numerator=sum(o.displayed_sentences_with_events for o in observations),
            denominator=sum(o.displayed_sentences for o in observations),
        ),
        "challenge_source_novelty": Metric(
            numerator=sum(o.challenge_found_novel_source for o in observations),
            denominator=sum(o.challenge_ran for o in observations),
        ),
    }


def run(base_url: str) -> int:
    cases = load_cases()
    observations = [observe_case(base_url, case) for case in cases]
    for observation in observations:
        logger.info(
            "%-40s state=%-22s findings=%d/%d sentences=%d/%d challenge_novel=%s",
            observation.case_id,
            observation.state,
            observation.findings_with_playable_evidence,
            observation.findings,
            observation.displayed_sentences_with_events,
            observation.displayed_sentences,
            observation.challenge_found_novel_source if observation.challenge_ran else "-",
        )
        if observation.error:
            logger.warning("  %s: %s", observation.case_id, observation.error)

    metrics = aggregate(observations)
    payload = {
        "coverage_version": "coverage-metrics-v1",
        "base_url": base_url,
        "case_count": len(cases),
        "arms": {
            "naive": {
                "basis": "structural",
                "note": (
                    "A single all-transcripts prompt returns prose with no clips, "
                    "no per-sentence event mapping, and no second retrieval pass. "
                    "These zeros follow from the arm's design; they are not an "
                    "observed run."
                ),
                "playable_citation_coverage": {"numerator": 0, "denominator": 0},
                "auditable_sentence_mapping": {"numerator": 0, "denominator": 0},
                "challenge_source_novelty": {"numerator": 0, "denominator": 0},
            },
            "strata": {
                "basis": "measured",
                **{name: metric.model_dump() for name, metric in metrics.items()},
            },
        },
        "observations": [observation.__dict__ for observation in observations],
    }
    COVERAGE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    logger.info("--- coverage metrics ---")
    for name, metric in metrics.items():
        logger.info("%-32s %s", name, metric.render())
    logger.info("wrote %s", COVERAGE_PATH)

    failed = [o for o in observations if o.state == "request_failed"]
    return 1 if failed else 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Measure Strata evidence-coverage metrics.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    return run(args.base_url)


if __name__ == "__main__":
    sys.exit(main())
