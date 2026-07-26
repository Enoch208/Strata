"""`GET /api/archive`.

Serves the live aggregate header. When VideoDB is unreachable or unconfigured
the route returns 503 with a reason rather than a plausible-looking zero
archive — the frontend renders a degraded header from that (guardrail 6).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ..adapters.payloads import AggregateShapeError
from ..adapters.videodb_client import VideoDBAdapter, VideoDBUnavailableError
from ..archive_stats import build_archive_response, compute_stats
from ..config import MissingCredentialError, get_settings
from ..manifest import load_manifest
from ..schemas.archive import ArchiveResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["archive"])


@router.get("/api/archive", response_model=ArchiveResponse)
def get_archive() -> ArchiveResponse:
    manifest = load_manifest()
    settings = get_settings()

    if not settings.has_credentials:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "videodb_unconfigured",
                "message": "VIDEODB_API_KEY is not set, so no live archive statistics exist yet.",
                "index_status": manifest.index_status,
                "archive_title": manifest.title,
            },
        )

    adapter = VideoDBAdapter(settings, collection_id=manifest.collection_id)
    try:
        stats = compute_stats(manifest, adapter)
    except MissingCredentialError as error:
        raise HTTPException(status_code=503, detail={"error": "videodb_unconfigured", "message": str(error)}) from error
    except VideoDBUnavailableError as error:
        logger.warning("archive stats unavailable: %s", type(error).__name__)
        raise HTTPException(
            status_code=503,
            detail={
                "error": "videodb_unavailable",
                "message": str(error),
                "index_status": manifest.index_status,
            },
        ) from error
    except AggregateShapeError as error:
        # The aggregate payload did not match any known shape. Report it loudly:
        # a guessed count is exactly what this product must not produce.
        logger.error("aggregate payload was not recognized: %s", error)
        raise HTTPException(
            status_code=502,
            detail={"error": "aggregate_shape_unrecognized", "message": str(error)},
        ) from error

    return build_archive_response(manifest, stats)
