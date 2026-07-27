"""Judge-facing proof is calculated from committed source artifacts."""

from fastapi.testclient import TestClient

from services.api.main import app


def test_proof_exposes_raw_two_arm_metrics_and_index_readiness() -> None:
    response = TestClient(app).get("/api/proof")

    assert response.status_code == 200
    payload = response.json()
    assert payload["distinct_video_ids"] == 6
    assert payload["evaluation_cases"] == 12
    assert {arm["arm"] for arm in payload["evaluation"]} == {
        "naive",
        "strata",
    }
    for arm in payload["evaluation"]:
        assert arm["retrieval_recall"]["denominator"] > 0
        assert arm["unsupported_claims"]["denominator"] > 0
    assert all(payload["index_proof"].values())
    assert payload["verification"]["tests_passed"] == 237
