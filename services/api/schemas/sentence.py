"""Source-locked summary sentences.

Mirrors PRD section 12.5. Every factual sentence the product displays must name
the event IDs that support it; a paragraph-level citation is not sufficient.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import NOT_ESTABLISHED_TEXT, SupportStatus


class SourcedSentence(BaseModel):
    """One sentence of generated summary, locked to its supporting events."""

    model_config = ConfigDict(extra="forbid")

    sentence_id: str
    text: str = Field(min_length=1)
    supported_by_event_ids: list[str] = Field(default_factory=list)
    support_status: SupportStatus
    #: True when the sentence compares two moments and therefore needs >= 2 events.
    is_comparative: bool = False
    #: Why the sentence failed the lock, when it did. Auditable, never displayed raw.
    lock_reason: str | None = None

    @model_validator(mode="after")
    def _supported_sentences_cite_events(self) -> SourcedSentence:
        if self.support_status is SupportStatus.supported and not self.supported_by_event_ids:
            raise ValueError(
                f"sentence {self.sentence_id} is marked supported but cites no events"
            )
        return self

    @model_validator(mode="after")
    def _comparative_sentences_need_two_events(self) -> SourcedSentence:
        # PRD section 13: "Require at least two event IDs for a sentence that
        # compares two moments."
        if (
            self.support_status is SupportStatus.supported
            and self.is_comparative
            and len(set(self.supported_by_event_ids)) < 2
        ):
            raise ValueError(
                f"comparative sentence {self.sentence_id} requires at least two "
                f"distinct event IDs, got {self.supported_by_event_ids!r}"
            )
        return self

    @model_validator(mode="after")
    def _not_established_uses_visible_copy(self) -> SourcedSentence:
        # PRD section 13: a not_established sentence must use the uncertainty message
        # rather than a rewritten assertion.
        if self.support_status is SupportStatus.not_established and self.text != NOT_ESTABLISHED_TEXT:
            raise ValueError(
                f"sentence {self.sentence_id} is not_established and must read "
                f"{NOT_ESTABLISHED_TEXT!r}, got {self.text!r}"
            )
        return self

    @property
    def is_displayable(self) -> bool:
        """Only `supported` sentences may render as ordinary summary text."""
        return self.support_status is SupportStatus.supported

    @classmethod
    def not_established(cls, sentence_id: str, lock_reason: str) -> SourcedSentence:
        """Build the honest replacement for a sentence the archive cannot support."""
        return cls(
            sentence_id=sentence_id,
            text=NOT_ESTABLISHED_TEXT,
            supported_by_event_ids=[],
            support_status=SupportStatus.not_established,
            lock_reason=lock_reason,
        )
