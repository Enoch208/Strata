"""The adapter must fail honestly rather than substituting sample data."""

import pytest

from services.api.adapters.videodb_client import (
    OCR_ANALYZER,
    SPEECH_ANALYZER,
    VISUAL_ANALYZER,
    VideoDBAdapter,
)
from services.api.config import MissingCredentialError, Settings


def make_settings(api_key: str | None) -> Settings:
    return Settings(
        videodb_api_key=api_key,
        videodb_collection_id=None,
        extraction_model="pro",
        extraction_temperature=0.0,
        clip_padding_seconds=2.0,
    )


class TestCredentialHandling:
    def test_missing_key_raises_rather_than_degrading(self) -> None:
        # PRD guardrail 6: never silently replace a failed call with sample data.
        adapter = VideoDBAdapter(settings=make_settings(None))

        with pytest.raises(MissingCredentialError) as excinfo:
            _ = adapter.connection

        assert "VIDEODB_API_KEY is not set" in str(excinfo.value)

    def test_settings_report_credential_presence(self) -> None:
        assert make_settings(None).has_credentials is False
        assert make_settings("sk-test").has_credentials is True

    def test_redacted_settings_never_expose_the_key(self) -> None:
        redacted = make_settings("sk-super-secret-value").redacted()

        assert redacted["videodb_api_key"] == "set"
        assert "sk-super-secret-value" not in str(redacted)


class TestAnalyzerDefinitions:
    def test_archive_uses_speech_ocr_and_visual_analyzers(self) -> None:
        # PRD UND-01, UND-02, UND-03. Types verified against VideoDB's docs.
        assert SPEECH_ANALYZER["type"] == "spoken_words"
        assert OCR_ANALYZER["type"] == "ocr"
        assert VISUAL_ANALYZER["type"] == "vlm"

    def test_visual_analyzer_prompt_asks_only_for_what_is_visible(self) -> None:
        assert "only what is visible" in VISUAL_ANALYZER["config"]["prompt"]
