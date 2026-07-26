"""Runtime validation of payloads crossing the VideoDB trust boundary.

Domain logic never touches a raw SDK response. Everything arriving from the
network is parsed here first, and anything unrecognized raises rather than
degrading to a zero or an empty list — a silently wrong archive count would be
exactly the kind of confident-but-false number the product exists to avoid.

The `aggregate()` response shape is not documented and the SDK returns it
verbatim ("returns the server aggregate payload directly"), so `parse_buckets`
accepts the plausible envelope shapes and reports precisely what it saw when it
cannot find any of them.
"""

from __future__ import annotations

from typing import Any

#: Envelope keys that may wrap the list of buckets.
_LIST_KEYS = ("buckets", "results", "groups", "data", "aggregations", "rows")
#: Keys that may carry a bucket's group label.
_LABEL_KEYS = ("key", "group", "group_by", "value", "name", "label", "_id")
#: Keys that may carry a bucket's metric.
_COUNT_KEYS = ("count", "doc_count", "value", "metric", "total", "n")


class AggregateShapeError(RuntimeError):
    """The aggregate payload did not match any shape this parser understands."""


def parse_buckets(payload: Any) -> dict[str, int]:
    """Reduce an `aggregate()` response to `{group_label: count}`.

    :raises AggregateShapeError: if no recognizable bucket list can be found.
    """
    rows = _find_rows(payload)
    if rows is None:
        raise AggregateShapeError(
            "Unrecognized aggregate payload. Expected a list of buckets or a dict "
            f"containing one of {_LIST_KEYS}; got {_describe(payload)}."
        )

    buckets: dict[str, int] = {}
    for row in rows:
        label, count = _parse_row(row)
        buckets[label] = buckets.get(label, 0) + count
    return buckets


def _find_rows(payload: Any) -> list[Any] | None:
    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict):
        return None

    for key in _LIST_KEYS:
        candidate = payload.get(key)
        if isinstance(candidate, list):
            return candidate
        # One level of nesting, e.g. {"data": {"buckets": [...]}}.
        if isinstance(candidate, dict):
            nested = _find_rows(candidate)
            if nested is not None:
                return nested

    # A flat {label: count} mapping, ignoring known envelope metadata.
    ignored = {"warnings", "index_name", "index_id", "group_by", "metric", "limit", "sort"}
    flat = {
        key: value
        for key, value in payload.items()
        if key not in ignored and isinstance(value, (int, float))
    }
    if flat:
        return [{"key": key, "count": value} for key, value in flat.items()]

    return None


def _parse_row(row: Any) -> tuple[str, int]:
    if not isinstance(row, dict):
        raise AggregateShapeError(f"Expected each aggregate bucket to be a dict, got {_describe(row)}.")

    label: str | None = None
    for key in _LABEL_KEYS:
        candidate = row.get(key)
        if isinstance(candidate, str) and candidate:
            label = candidate
            break
    if label is None:
        # VideoDB's live aggregate currently returns the requested group-by
        # field as the label key, e.g. {"claim_type": "delay_reason",
        # "value": 71}. The field name is dynamic, so accept the sole
        # non-empty string value when the standard aliases are absent.
        dynamic_labels = [
            candidate
            for key, candidate in row.items()
            if key not in _COUNT_KEYS
            and isinstance(candidate, str)
            and candidate
        ]
        if len(dynamic_labels) == 1:
            label = dynamic_labels[0]

    count: int | None = None
    for key in _COUNT_KEYS:
        candidate = row.get(key)
        if isinstance(candidate, bool):
            continue
        if isinstance(candidate, (int, float)):
            count = int(candidate)
            break

    if label is None or count is None:
        raise AggregateShapeError(
            f"Aggregate bucket is missing a label or count. Looked for labels in "
            f"{_LABEL_KEYS} and counts in {_COUNT_KEYS}; bucket keys were {sorted(row)}."
        )

    return label, count


def sum_buckets(payload: Any) -> int:
    """Total across every bucket.

    Used for `claim_event_count` (PRD AGG-01): each event carries exactly one
    `claim_type`, so summing the buckets counts each event once.
    """
    return sum(parse_buckets(payload).values())


def sum_selected(payload: Any, labels: frozenset[str] | set[str]) -> int:
    """Total across only the named buckets, treating absent buckets as zero.

    Used for `status_change_count` (PRD AGG-02) = `confirmed_change` + `correction`.
    """
    buckets = parse_buckets(payload)
    return sum(count for label, count in buckets.items() if label in labels)


def _describe(value: Any) -> str:
    if isinstance(value, dict):
        return f"dict with keys {sorted(value)}"
    if isinstance(value, list):
        return f"list of {len(value)} item(s)"
    return f"{type(value).__name__} ({value!r})"
