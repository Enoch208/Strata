"""aggregate() bucket parsing and archive-header totals (PRD section 19).

The live payload shape is undocumented, so the parser accepts the plausible
envelopes and must refuse anything else loudly rather than returning zero.
"""

import pytest

from services.api.adapters.payloads import (
    AggregateShapeError,
    parse_buckets,
    sum_buckets,
    sum_selected,
)
from services.api.schemas.enums import STATUS_CHANGE_LABELS

STATUS_CHANGE_KEYS = {str(label) for label in STATUS_CHANGE_LABELS}


class TestParseBuckets:
    @pytest.mark.parametrize(
        "payload",
        [
            [{"key": "launch_date", "count": 12}, {"key": "delay_reason", "count": 9}],
            {"buckets": [{"key": "launch_date", "count": 12}, {"key": "delay_reason", "count": 9}]},
            {"results": [{"group": "launch_date", "count": 12}, {"group": "delay_reason", "count": 9}]},
            {"groups": [{"value": "launch_date", "doc_count": 12}, {"value": "delay_reason", "doc_count": 9}]},
            {"data": {"buckets": [{"_id": "launch_date", "n": 12}, {"_id": "delay_reason", "n": 9}]}},
            [{"claim_type": "launch_date", "value": 12}, {"claim_type": "delay_reason", "value": 9}],
            {"launch_date": 12, "delay_reason": 9},
        ],
    )
    def test_accepts_plausible_envelope_shapes(self, payload: object) -> None:
        assert parse_buckets(payload) == {"launch_date": 12, "delay_reason": 9}

    def test_ignores_envelope_metadata_in_flat_payloads(self) -> None:
        payload = {"launch_date": 12, "limit": 100, "warnings": [], "index_name": "claim_events_v1"}
        assert parse_buckets(payload) == {"launch_date": 12}

    def test_repeated_labels_are_summed(self) -> None:
        payload = [{"key": "correction", "count": 2}, {"key": "correction", "count": 3}]
        assert parse_buckets(payload) == {"correction": 5}

    @pytest.mark.parametrize("payload", [None, "nope", 42, {}, {"warnings": []}])
    def test_unrecognized_payloads_raise(self, payload: object) -> None:
        # Never degrade to zero: a silently wrong count is worse than an error.
        with pytest.raises(AggregateShapeError):
            parse_buckets(payload)

    def test_bucket_missing_a_count_raises_with_context(self) -> None:
        with pytest.raises(AggregateShapeError) as excinfo:
            parse_buckets([{"key": "launch_date"}])
        assert "bucket keys were ['key']" in str(excinfo.value)


class TestArchiveTotals:
    def test_claim_event_count_sums_every_claim_type_bucket(self) -> None:
        # PRD AGG-01: each event has exactly one claim_type, so the sum counts
        # each event once.
        payload = {
            "buckets": [
                {"key": "launch_date", "count": 12},
                {"key": "delay_reason", "count": 9},
                {"key": "status_update", "count": 20},
            ]
        }
        assert sum_buckets(payload) == 41

    def test_status_changes_are_confirmed_change_plus_correction(self) -> None:
        # PRD AGG-02 and section 11.5. Explicitly not the number of distinct statuses.
        payload = {
            "buckets": [
                {"key": "confirmed_change", "count": 4},
                {"key": "correction", "count": 1},
                {"key": "consistent_statement", "count": 7},
                {"key": "new_information", "count": 3},
            ]
        }
        assert sum_selected(payload, STATUS_CHANGE_KEYS) == 5

    def test_absent_buckets_count_as_zero(self) -> None:
        payload = {"buckets": [{"key": "consistent_statement", "count": 7}]}
        assert sum_selected(payload, STATUS_CHANGE_KEYS) == 0

    def test_totals_are_never_the_prd_example_literals_by_construction(self) -> None:
        # Guards AGG-06: the header numbers must move with the payload.
        payload = {"buckets": [{"key": "launch_date", "count": 1}]}
        assert sum_buckets(payload) == 1
