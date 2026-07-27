"""Regression checks that keep evaluation fixtures out of production retrieval."""

from __future__ import annotations

import inspect

from services.api import investigation_engine
from services.api.manifest import load_manifest


def test_production_engine_contains_no_seeded_archive_fixture() -> None:
    source = inspect.getsource(investigation_engine)
    manifest = load_manifest()

    forbidden_symbols = (
        "_apply_seeded_initial_fixture",
        "_apply_seeded_challenge_fixture",
        "_is_seeded_query",
        "verified_window(",
    )
    assert all(symbol not in source for symbol in forbidden_symbols)

    for video in manifest.videos:
        assert video.video_id not in source
        assert video.slug not in source
        assert video.source_date.isoformat() not in source

    for fixture_literal in ("86.0", "101.0", "115.0", "139.0"):
        assert fixture_literal not in source
