"""The submission gate must stay red until live evidence exists."""

from services.api.manifest import load_manifest
from pipeline.verify import readiness_checks


def test_uningested_archive_cannot_pass_submission_gate(tmp_path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("x" * 600, encoding="utf-8")
    manifest = load_manifest().model_copy(deep=True)
    for video in manifest.videos:
        video.video_id = None
        video.duration_seconds = None
        video.index_status = "pending"
        video.understanding_id = None
        video.artifact_ids = {}
        video.index_ids = {}

    checks = readiness_checks(
        manifest,
        has_credentials=False,
        evaluation_cases_path=tmp_path / "missing-cases.json",
        evaluation_results_path=tmp_path / "missing-results.json",
        readme_path=readme,
    )
    by_name = {check.name: check for check in checks}

    assert by_name["VideoDB credential configured"].passed is False
    assert by_name["all videos indexed"].passed is False
    assert by_name["12 frozen evaluation cases"].passed is False
    assert by_name["two-arm real evaluation"].passed is False
    assert by_name["evaluation-only challenge windows"].passed is False
