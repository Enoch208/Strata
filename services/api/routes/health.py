"""Health check.

PRD section 14: reports application status without exposing secrets. The
`videodb` field reflects one real read call, so a green health check means the
connection actually works rather than that the process started.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from ..adapters.videodb_client import VideoDBAdapter, VideoDBUnavailableError
from ..config import MissingCredentialError, get_settings
from ..manifest import load_manifest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    videodb: str
    archive_indexed: bool
    index_status: str
    detail: str | None = None


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    manifest = load_manifest()

    if not settings.has_credentials:
        return HealthResponse(
            status="degraded",
            videodb="unconfigured",
            archive_indexed=False,
            index_status=manifest.index_status,
            detail="VIDEODB_API_KEY is not set. No archive data can be served.",
        )

    try:
        VideoDBAdapter(settings, collection_id=manifest.collection_id).ping()
    except (VideoDBUnavailableError, MissingCredentialError) as error:
        # Log the class of failure, never the key or the full request.
        logger.warning("health check could not reach VideoDB: %s", type(error).__name__)
        return HealthResponse(
            status="degraded",
            videodb="unavailable",
            archive_indexed=False,
            index_status=manifest.index_status,
            detail=str(error),
        )

    return HealthResponse(
        status="ok",
        videodb="connected",
        archive_indexed=manifest.index_status == "ready",
        index_status=manifest.index_status,
    )
