"""Counter-evidence pass result.

Mirrors PRD section 12.6. The challenge never overwrites the first answer; it
records what a second, adversarial retrieval pass found and how that affects the
original conclusion.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from .enums import ChallengeOutcome

CHALLENGE_SCHEMA_VERSION = "challenge-result-v1"


class RejectedCandidate(BaseModel):
    """A candidate the challenge pass considered and turned down, with the reason.

    Kept so the whole pass stays auditable (PRD guardrail 19).
    """

    model_config = ConfigDict(extra="forbid")

    event_id: str
    reason: str = Field(min_length=1)


class ChallengeResult(BaseModel):
    """The full trace of one counter-evidence pass."""

    model_config = ConfigDict(extra="forbid")

    challenge_id: str
    schema_version: str = CHALLENGE_SCHEMA_VERSION
    prompt: str = "Challenge this conclusion"
    initial_queries: list[str] = Field(default_factory=list)
    counter_queries: list[str] = Field(min_length=3, max_length=5)
    accepted_finding_ids: list[str] = Field(default_factory=list)
    rejected_candidates: list[RejectedCandidate] = Field(default_factory=list)
    initial_accepted_video_ids: list[str] = Field(default_factory=list)
    challenge_accepted_video_ids: list[str] = Field(default_factory=list)
    outcome: ChallengeOutcome
    impact_summary_sentence_ids: list[str] = Field(default_factory=list)
    searched_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def novel_accepted_video_ids(self) -> list[str]:
        """Challenge sources absent from the first pass (PRD section 11.8).

        Derived rather than stored so it can never drift from the two sets it is
        the difference of.
        """
        initial = set(self.initial_accepted_video_ids)
        return [vid for vid in self.challenge_accepted_video_ids if vid not in initial]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def found_counter_evidence(self) -> bool:
        return bool(self.accepted_finding_ids)

    @model_validator(mode="after")
    def _empty_challenge_stays_unchanged(self) -> ChallengeResult:
        # PRD CTR-06: an empty pass may never be reported as a qualification or
        # revision, and is never evidence that the conclusion is true.
        if not self.accepted_finding_ids and self.outcome is not ChallengeOutcome.unchanged:
            raise ValueError(
                f"challenge {self.challenge_id} accepted no findings and must report "
                f"outcome 'unchanged', got '{self.outcome}'"
            )
        return self


#: Shown when the second pass finds nothing (PRD section 15.4). Deliberately does
#: not claim the first conclusion was proved correct.
EMPTY_CHALLENGE_TEXT = (
    "No counter-evidence was found in this archive. "
    "This does not prove the conclusion is true."
)
