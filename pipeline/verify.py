"""Strict submission-readiness gate.

The command is expected to fail until live VideoDB ingestion and real evaluation
are complete. A red check is a blocker, not an invitation to insert sample data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from services.api.config import EVALUATION_CASES_PATH, REPO_ROOT, get_settings
from services.api.manifest import ArchiveManifest, load_manifest
from pipeline.evaluate import load_cases

EVALUATION_RESULTS_PATH = REPO_ROOT / "data" / "evaluation_results.json"
README_PATH = REPO_ROOT / "README.md"


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def readiness_checks(
    manifest: ArchiveManifest,
    *,
    has_credentials: bool,
    evaluation_cases_path: Path = EVALUATION_CASES_PATH,
    evaluation_results_path: Path = EVALUATION_RESULTS_PATH,
    readme_path: Path = README_PATH,
) -> list[Check]:
    video_ids = [video.video_id for video in manifest.videos if video.video_id]
    ready = [video for video in manifest.videos if video.is_ready]
    try:
        evaluation_cases = load_cases(evaluation_cases_path)
        challenge_cases = [
            case
            for case in evaluation_cases
            if case.require_novel_challenge_source
        ]
        evaluation_windows_ready = bool(challenge_cases) and all(
            len(case.expected_evidence) >= 2
            and len({unit.video_id for unit in case.expected_evidence}) >= 2
            for case in challenge_cases
        )
    except (OSError, ValueError):
        evaluation_windows_ready = False

    return [
        Check(
            "VideoDB credential configured",
            has_credentials,
            "VIDEODB_API_KEY is set" if has_credentials else "VIDEODB_API_KEY is missing",
        ),
        Check(
            "six-source manifest",
            len(manifest.videos) == 6,
            f"{len(manifest.videos)} source videos declared",
        ),
        Check(
            "all videos indexed",
            len(ready) == 6 and len(set(video_ids)) == 6,
            f"{len(ready)}/6 ready with {len(set(video_ids))} distinct VideoDB IDs",
        ),
        Check(
            "evaluation-only challenge windows",
            evaluation_windows_ready,
            "novel-source gold windows exist only in the frozen evaluation set",
        ),
        _json_count_check(
            "12 frozen evaluation cases",
            evaluation_cases_path,
            expected=12,
        ),
        _evaluation_result_check(evaluation_results_path),
        Check(
            "repository README",
            readme_path.is_file() and readme_path.stat().st_size > 500,
            str(readme_path),
        ),
    ]


def _json_count_check(name: str, path: Path, *, expected: int) -> Check:
    if not path.is_file():
        return Check(name, False, f"{path} is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return Check(name, False, f"cannot parse {path}: {error}")
    count = len(payload) if isinstance(payload, list) else -1
    return Check(name, count == expected, f"{count} cases found")


def _evaluation_result_check(path: Path) -> Check:
    if not path.is_file():
        return Check("two-arm real evaluation", False, f"{path} is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return Check("two-arm real evaluation", False, f"cannot parse {path}: {error}")
    arms = {
        item.get("arm")
        for item in payload
        if isinstance(item, dict) and isinstance(item.get("arm"), str)
    } if isinstance(payload, list) else set()
    passed = arms == {"naive", "claimtrail"}
    return Check("two-arm real evaluation", passed, f"arms present: {sorted(arms)}")


def main() -> int:
    checks = readiness_checks(
        load_manifest(),
        has_credentials=get_settings().has_credentials,
    )
    for check in checks:
        mark = "PASS" if check.passed else "FAIL"
        print(f"[{mark}] {check.name}: {check.detail}")
    failed = sum(not check.passed for check in checks)
    print(f"\n{len(checks) - failed}/{len(checks)} readiness checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
