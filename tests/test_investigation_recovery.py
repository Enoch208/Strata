"""Follow-up requests must survive losing the process that answered them.

Investigations live in process memory. Under serverless hosting a challenge or
packet request can land on an instance that never saw the first pass, which
previously produced a 404 on the demo's central action. IDs are now derived from
the question, so an investigation can be re-run deterministically from its query.
"""

from __future__ import annotations

import pytest

from services.api.investigation_engine import (
    InvestigationEngine,
    InvestigationNotFoundError,
    investigation_id_for,
)
from services.api.manifest import load_manifest
from services.api.schemas.packet import InvestigationState

QUERY = "Did the September 3 hydrogen leak fully explain why Artemis I launched in November?"
ARCHIVE_ID = "artemis-i-2022"


class StubAdapter:
    """Returns no hits, so `create` completes without any network access.

    The recovery behaviour under test is about identity and rebuild routing, not
    about retrieval quality, which the engine tests cover separately.
    """

    def semantic_search(self, *args, **kwargs):
        return []

    def structured_query(self, *args, **kwargs):
        return []


def make_engine() -> InvestigationEngine:
    manifest = load_manifest()
    for video in manifest.videos:
        video.video_id = video.video_id or f"m-{video.slug}"
        video.index_status = "ready"
        video.duration_seconds = video.duration_seconds or 600.0

    return InvestigationEngine(
        manifest_provider=lambda: manifest,
        adapter_factory=lambda _manifest: StubAdapter(),
    )


class TestInvestigationIdentity:
    def test_id_is_derived_from_the_question(self) -> None:
        assert investigation_id_for(ARCHIVE_ID, QUERY) == investigation_id_for(
            ARCHIVE_ID, QUERY
        )

    def test_surrounding_whitespace_does_not_change_the_id(self) -> None:
        assert investigation_id_for(ARCHIVE_ID, f"  {QUERY}  ") == investigation_id_for(
            ARCHIVE_ID, QUERY
        )

    def test_different_questions_get_different_ids(self) -> None:
        assert investigation_id_for(ARCHIVE_ID, QUERY) != investigation_id_for(
            ARCHIVE_ID, "Why did Artemis I roll back to the VAB?"
        )

    def test_different_archives_get_different_ids(self) -> None:
        assert investigation_id_for(ARCHIVE_ID, QUERY) != investigation_id_for(
            "boeing-737-max", QUERY
        )

    def test_created_investigation_uses_the_derived_id(self) -> None:
        engine = make_engine()

        investigation = engine.create(QUERY, ARCHIVE_ID)

        assert investigation.investigation_id == investigation_id_for(ARCHIVE_ID, QUERY)

    def test_non_investigation_ids_are_still_generated(self) -> None:
        # Deriving investigation IDs must not disable the factory that mints
        # challenge and reel IDs — doing so crashed the challenge route.
        engine = InvestigationEngine(manifest_provider=load_manifest)

        first = engine._id_factory("challenge")
        second = engine._id_factory("challenge")

        assert first.startswith("challenge_")
        assert first != second

    def test_an_injected_id_factory_still_controls_investigation_ids(self) -> None:
        engine = InvestigationEngine(
            manifest_provider=load_manifest,
            adapter_factory=lambda _manifest: StubAdapter(),
            id_factory=lambda prefix: f"{prefix}_pinned",
        )

        investigation = engine.create(QUERY, ARCHIVE_ID)

        assert investigation.investigation_id == "inv_pinned"


class TestEnsureRecovery:
    def test_stored_investigation_is_returned_without_rebuilding(self) -> None:
        engine = make_engine()
        created = engine.create(QUERY, ARCHIVE_ID)

        recovered = engine.ensure(
            created.investigation_id, query=QUERY, archive_id=ARCHIVE_ID
        )

        assert recovered is created

    def test_missing_investigation_is_rebuilt_from_its_query(self) -> None:
        # Simulates a follow-up landing on an instance that never saw the first pass.
        engine = make_engine()
        investigation_id = investigation_id_for(ARCHIVE_ID, QUERY)

        recovered = engine.ensure(
            investigation_id, query=QUERY, archive_id=ARCHIVE_ID
        )

        assert recovered.investigation_id == investigation_id
        assert recovered.query == QUERY
        assert recovered.state is not InvestigationState.failed

    def test_missing_investigation_without_a_query_still_reports_missing(self) -> None:
        # Without the question there is nothing to rebuild from, and inventing a
        # result would be worse than an honest 404.
        engine = make_engine()

        with pytest.raises(InvestigationNotFoundError):
            engine.ensure("inv_deadbeef1234", query=None, archive_id=None)

    def test_a_query_that_does_not_match_the_id_is_refused(self) -> None:
        # Rebuilding here would answer a different question under this identity.
        engine = make_engine()
        investigation_id = investigation_id_for(ARCHIVE_ID, QUERY)

        with pytest.raises(InvestigationNotFoundError):
            engine.ensure(
                investigation_id,
                query="An entirely different question about the archive",
                archive_id=ARCHIVE_ID,
            )

    def test_rebuild_is_idempotent(self) -> None:
        engine = make_engine()
        investigation_id = investigation_id_for(ARCHIVE_ID, QUERY)

        first = engine.ensure(investigation_id, query=QUERY, archive_id=ARCHIVE_ID)
        second = engine.ensure(investigation_id, query=QUERY, archive_id=ARCHIVE_ID)

        assert first.investigation_id == second.investigation_id
        assert second is first
