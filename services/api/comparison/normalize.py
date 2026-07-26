"""Deterministic normalization of dates, numbers and statuses.

PRD section 11.7: the comparison engine uses deterministic logic first. Anything
that can be reduced to a structured value is compared as a structured value, and
only genuinely unstructured explanations are handed to semantic comparison.

Every function here returns ``None`` rather than guessing. A failed parse means
the comparison falls back to semantic handling, which is conservative by design.
"""

from __future__ import annotations

import re
from datetime import date

from ..schemas.enums import ClaimStatus

_MONTHS: dict[str, int] = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_MONTH_ALTERNATION = "|".join(sorted(_MONTHS, key=len, reverse=True))

# "September 3", "Sept. 3, 2022", "Nov 12"
_MONTH_FIRST = re.compile(
    rf"\b(?P<month>{_MONTH_ALTERNATION})\.?\s+(?P<day>\d{{1,2}})(?:\s*,?\s*(?P<year>\d{{4}}))?\b",
    re.IGNORECASE,
)
# "3 September", "27 Sep 2022"
_DAY_FIRST = re.compile(
    rf"\b(?P<day>\d{{1,2}})\s+(?P<month>{_MONTH_ALTERNATION})\.?(?:\s*,?\s*(?P<year>\d{{4}}))?\b",
    re.IGNORECASE,
)
_ISO = re.compile(r"\b(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\b")

_NUMBER_WORDS: dict[str, float] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12,
}

_UNIT_ALIASES: dict[str, str] = {
    "second": "seconds", "seconds": "seconds", "sec": "seconds", "secs": "seconds",
    "minute": "minutes", "minutes": "minutes", "min": "minutes", "mins": "minutes",
    "hour": "hours", "hours": "hours", "hr": "hours", "hrs": "hours",
    "day": "days", "days": "days",
    "week": "weeks", "weeks": "weeks",
    "month": "months", "months": "months",
    "psi": "psi", "psia": "psi",
    "percent": "percent", "%": "percent",
    "degree": "degrees", "degrees": "degrees",
    "kilogram": "kg", "kilograms": "kg", "kg": "kg",
    "pound": "lb", "pounds": "lb", "lb": "lb", "lbs": "lb",
}

_UNIT_ALTERNATION = "|".join(sorted(_UNIT_ALIASES, key=len, reverse=True))
_NUMBER_WORD_ALTERNATION = "|".join(sorted(_NUMBER_WORDS, key=len, reverse=True))

_QUANTITY = re.compile(
    rf"(?P<value>\d+(?:\.\d+)?|{_NUMBER_WORD_ALTERNATION})\s*"
    rf"(?P<unit>{_UNIT_ALTERNATION})\b",
    re.IGNORECASE,
)

#: Ordered longest-phrase-first so "rolled back" wins over "back".
_STATUS_PHRASES: tuple[tuple[str, ClaimStatus], ...] = (
    ("rolled back", ClaimStatus.rolled_back),
    ("roll back", ClaimStatus.rolled_back),
    ("rollback", ClaimStatus.rolled_back),
    ("waved off", ClaimStatus.scrubbed),
    ("waived off", ClaimStatus.scrubbed),
    ("scrubbed", ClaimStatus.scrubbed),
    ("scrub", ClaimStatus.scrubbed),
    ("under repair", ClaimStatus.under_repair),
    ("repairing", ClaimStatus.under_repair),
    ("repair", ClaimStatus.under_repair),
    ("tanking test", ClaimStatus.testing),
    ("demonstration test", ClaimStatus.testing),
    ("testing", ClaimStatus.testing),
    ("delayed", ClaimStatus.delayed),
    ("postponed", ClaimStatus.delayed),
    ("slipped", ClaimStatus.delayed),
    ("launched", ClaimStatus.launched),
    ("liftoff", ClaimStatus.launched),
    ("lifted off", ClaimStatus.launched),
    ("go for launch", ClaimStatus.ready),
    ("ready", ClaimStatus.ready),
    ("scheduled", ClaimStatus.scheduled),
    ("targeting", ClaimStatus.scheduled),
    ("planned", ClaimStatus.planned),
)


def normalize_date(text: str, *, default_year: int | None = None) -> date | None:
    """Parse the first date in `text` to a `date`, or `None` if there is none.

    `default_year` supplies the year for bare references like "September 3",
    which is how officials almost always speak. Pass the source video's year.
    """
    if not text:
        return None

    iso = _ISO.search(text)
    if iso:
        return _safe_date(int(iso["year"]), int(iso["month"]), int(iso["day"]))

    for pattern in (_MONTH_FIRST, _DAY_FIRST):
        match = pattern.search(text)
        if not match:
            continue
        year_text = match.groupdict().get("year")
        year = int(year_text) if year_text else default_year
        if year is None:
            # No year anywhere and no default: refuse rather than assume one.
            return None
        month = _MONTHS[match["month"].lower().rstrip(".")]
        return _safe_date(year, month, int(match["day"]))

    return None


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def normalize_quantity(text: str) -> tuple[float, str] | None:
    """Parse the first `(value, canonical_unit)` quantity in `text`."""
    if not text:
        return None
    match = _QUANTITY.search(text)
    if not match:
        return None

    raw_value = match["value"].lower()
    value = _NUMBER_WORDS.get(raw_value)
    if value is None:
        try:
            value = float(raw_value)
        except ValueError:
            return None

    unit = _UNIT_ALIASES[match["unit"].lower()]
    return value, unit


def normalize_status(text: str) -> ClaimStatus:
    """Map free text onto the controlled status enum.

    Returns `ClaimStatus.unknown` when nothing matches — an unknown status is
    excluded from deterministic status comparison rather than guessed at.
    """
    if not text:
        return ClaimStatus.unknown
    lowered = text.lower()
    for phrase, status in _STATUS_PHRASES:
        if phrase in lowered:
            return status
    return ClaimStatus.unknown


def normalize_subject(text: str) -> str:
    """Canonicalize the archive's common Artemis I subject aliases."""
    stripped = " ".join((text or "").split())
    lowered = stripped.lower()
    if (
        re.search(r"\bartemis\s+(?:i|1|one)\b", lowered)
        or "space launch system" in lowered
        or re.search(r"\bsls\b", lowered)
    ):
        return "Artemis I launch"
    return stripped or "Artemis I launch"
