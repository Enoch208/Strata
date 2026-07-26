"""Runtime configuration.

Credentials are read from the environment only, never from the manifest and
never sent to the browser (PRD guardrail 4). Nothing here logs a secret.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
MANIFEST_PATH = DATA_DIR / "archive_manifest.json"
EVALUATION_CASES_PATH = DATA_DIR / "evaluation_cases.json"

# Local developer overrides are loaded first. Existing process variables still
# win because python-dotenv's default is ``override=False``; values from
# ``.env.local`` then take precedence over the shared ``.env`` defaults.
load_dotenv(REPO_ROOT / ".env.local")
load_dotenv(REPO_ROOT / ".env")


class MissingCredentialError(RuntimeError):
    """Raised when a live VideoDB call is attempted with no API key configured.

    Callers surface this as an honest unavailable state rather than falling back
    to sample data (PRD guardrail 6).
    """


@dataclass(frozen=True)
class Settings:
    """Server-side settings. `videodb_api_key` never leaves this process."""

    videodb_api_key: str | None
    videodb_collection_id: str | None
    #: Sandbox text model used for claim extraction and summary drafting.
    extraction_model: str
    extraction_temperature: float
    #: Padding kept around every evidence clip so quotations are not misleading
    #: (PRD guardrail 11).
    clip_padding_seconds: float

    @property
    def has_credentials(self) -> bool:
        return bool(self.videodb_api_key)

    def require_api_key(self) -> str:
        if not self.videodb_api_key:
            raise MissingCredentialError(
                "VIDEODB_API_KEY is not set. Copy .env.example to .env and add the key; "
                "no sample data will be substituted."
            )
        return self.videodb_api_key

    def redacted(self) -> dict[str, object]:
        """Safe-to-log view of the configuration."""
        return {
            "videodb_api_key": "set" if self.videodb_api_key else "missing",
            "videodb_collection_id": self.videodb_collection_id or "unset",
            "extraction_model": self.extraction_model,
            "extraction_temperature": self.extraction_temperature,
            "clip_padding_seconds": self.clip_padding_seconds,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        videodb_api_key=os.getenv("VIDEODB_API_KEY") or None,
        videodb_collection_id=os.getenv("VIDEODB_COLLECTION_ID") or None,
        extraction_model=os.getenv(
            "STRATA_EXTRACTION_MODEL",
            os.getenv("CLAIMTRAIL_EXTRACTION_MODEL", "pro"),
        ),
        extraction_temperature=float(
            os.getenv(
                "STRATA_EXTRACTION_TEMPERATURE",
                os.getenv("CLAIMTRAIL_EXTRACTION_TEMPERATURE", "0"),
            )
        ),
        clip_padding_seconds=float(
            os.getenv(
                "STRATA_CLIP_PADDING_SECONDS",
                os.getenv("CLAIMTRAIL_CLIP_PADDING_SECONDS", "2.0"),
            )
        ),
    )
