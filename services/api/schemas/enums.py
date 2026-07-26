"""Controlled vocabularies. Every label the product may display lives here.

PRD sections 9, 11.7, 12 and 13. Nothing outside these enums may reach the UI —
in particular the forbidden accusatory labels (lie, falsehood, deception, guilty)
have no representation in the type system at all.
"""

from enum import StrEnum


class FindingLabel(StrEnum):
    """PRD section 9. The only classifications a finding may carry."""

    confirmed_change = "confirmed_change"
    correction = "correction"
    potential_tension = "potential_tension"
    consistent_statement = "consistent_statement"
    new_information = "new_information"
    insufficient_evidence = "insufficient_evidence"
    needs_review = "needs_review"


#: Labels whose sum is reported as "status changes" in the archive header (AGG-02).
STATUS_CHANGE_LABELS: frozenset[FindingLabel] = frozenset(
    {FindingLabel.confirmed_change, FindingLabel.correction}
)

#: Labels that require at least two distinct timestamped events (PRD section 13).
MULTI_EVENT_LABELS: frozenset[FindingLabel] = frozenset(
    {
        FindingLabel.confirmed_change,
        FindingLabel.correction,
        FindingLabel.potential_tension,
        FindingLabel.consistent_statement,
    }
)


class RelationType(StrEnum):
    """PRD section 11.7. The only relations the comparison stage may create."""

    repeats = "repeats"
    expands = "expands"
    revises = "revises"
    explicitly_corrects = "explicitly_corrects"
    disputes = "disputes"
    contextualizes = "contextualizes"


class Confidence(StrEnum):
    """PRD section 13. No invented percentages."""

    high = "high"
    medium = "medium"
    low = "low"


class SupportStatus(StrEnum):
    """PRD section 12.5. Only `supported` may render as ordinary summary text."""

    supported = "supported"
    partially_supported = "partially_supported"
    not_established = "not_established"


class ChallengeOutcome(StrEnum):
    """PRD section 12.6. Describes the effect on the first answer, not truth."""

    unchanged = "unchanged"
    qualified = "qualified"
    revised = "revised"


class Certainty(StrEnum):
    """How directly the source states the claim."""

    explicit = "explicit"
    implied = "implied"
    uncertain = "uncertain"


class ClaimStatus(StrEnum):
    """Controlled status enum for deterministic comparison (PRD section 11.7)."""

    planned = "planned"
    scheduled = "scheduled"
    delayed = "delayed"
    scrubbed = "scrubbed"
    under_repair = "under_repair"
    testing = "testing"
    rolled_back = "rolled_back"
    ready = "ready"
    launched = "launched"
    unknown = "unknown"


class ClaimType(StrEnum):
    """What kind of assertion the event carries."""

    launch_date = "launch_date"
    delay_reason = "delay_reason"
    repair_plan = "repair_plan"
    test_plan = "test_plan"
    status_update = "status_update"
    measurement = "measurement"
    correction = "correction"
    other = "other"


#: The visible copy used whenever the archive cannot support a claim (PRD section 13).
NOT_ESTABLISHED_TEXT = "Not established by this archive."
