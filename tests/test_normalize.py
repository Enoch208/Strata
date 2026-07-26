"""Date, number, unit and status normalization (PRD section 19, required tests)."""

from datetime import date

import pytest

from services.api.comparison.normalize import (
    normalize_date,
    normalize_quantity,
    normalize_status,
    normalize_subject,
)
from services.api.schemas.enums import ClaimStatus


class TestNormalizeDate:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("the 2022-09-03 attempt", date(2022, 9, 3)),
            ("September 3, 2022", date(2022, 9, 3)),
            ("Sept. 27, 2022", date(2022, 9, 27)),
            ("3 September 2022", date(2022, 9, 3)),
            ("27 Sep 2022", date(2022, 9, 27)),
            ("launched on November 16, 2022", date(2022, 11, 16)),
        ],
    )
    def test_parses_explicit_dates(self, text: str, expected: date) -> None:
        assert normalize_date(text) == expected

    def test_bare_date_uses_default_year(self) -> None:
        assert normalize_date("we scrubbed on September 3", default_year=2022) == date(2022, 9, 3)

    def test_bare_date_without_default_year_refuses_to_guess(self) -> None:
        # Guessing a year here would silently fabricate a comparable value.
        assert normalize_date("we scrubbed on September 3") is None

    def test_explicit_year_wins_over_default(self) -> None:
        assert normalize_date("September 3, 2021", default_year=2022) == date(2021, 9, 3)

    @pytest.mark.parametrize("text", ["", "no date at all", "the leak was fixed"])
    def test_returns_none_when_absent(self, text: str) -> None:
        assert normalize_date(text, default_year=2022) is None

    def test_impossible_date_is_rejected(self) -> None:
        assert normalize_date("February 30, 2022") is None


class TestNormalizeQuantity:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("a 3 hour hold", (3.0, "hours")),
            ("held at 60 psi", (60.0, "psi")),
            ("two weeks of work", (2.0, "weeks")),
            ("12.5 percent margin", (12.5, "percent")),
            ("delayed 45 mins", (45.0, "minutes")),
        ],
    )
    def test_parses_quantities(self, text: str, expected: tuple[float, str]) -> None:
        assert normalize_quantity(text) == expected

    def test_units_are_canonicalized(self) -> None:
        assert normalize_quantity("3 hrs")== normalize_quantity("3 hours")

    @pytest.mark.parametrize("text", ["", "no numbers here", "several days later"])
    def test_returns_none_when_absent(self, text: str) -> None:
        assert normalize_quantity(text) is None


class TestNormalizeStatus:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("the attempt was scrubbed", ClaimStatus.scrubbed),
            ("managers waved off the launch", ClaimStatus.scrubbed),
            ("we will roll back to the VAB", ClaimStatus.rolled_back),
            ("the vehicle is under repair", ClaimStatus.under_repair),
            ("a tanking test is planned", ClaimStatus.testing),
            ("the launch slipped again", ClaimStatus.delayed),
            ("Artemis I lifted off", ClaimStatus.launched),
            ("we are targeting November 14", ClaimStatus.scheduled),
        ],
    )
    def test_maps_phrases_to_enum(self, text: str, expected: ClaimStatus) -> None:
        assert normalize_status(text) == expected

    def test_longest_phrase_wins(self) -> None:
        # "rolled back" must not be shadowed by a shorter accidental match.
        assert normalize_status("the stack rolled back to the VAB") == ClaimStatus.rolled_back

    @pytest.mark.parametrize("text", ["", "the briefing continues", "good afternoon"])
    def test_unmatched_text_is_unknown(self, text: str) -> None:
        assert normalize_status(text) == ClaimStatus.unknown


class TestNormalizeSubject:
    @pytest.mark.parametrize(
        "text",
        ["Artemis 1 mission", "Artemis I launch date", "the SLS rocket"],
    )
    def test_artemis_aliases_share_one_subject(self, text: str) -> None:
        assert normalize_subject(text) == "Artemis I launch"

    def test_unknown_subject_is_preserved_without_extra_whitespace(self) -> None:
        assert normalize_subject("  Orion   heat shield  ") == "Orion heat shield"
