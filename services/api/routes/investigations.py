"""Investigation, challenge, reel, and Evidence Packet routes."""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from ..adapters.videodb_client import VideoDBUnavailableError
from ..config import MissingCredentialError
from ..investigation_engine import (
    InvestigationConflictError,
    InvestigationEngine,
    InvestigationNotFoundError,
)
from ..schemas.challenge import ChallengeResult
from ..schemas.packet import Investigation, ReelRef

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


class CreateInvestigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2000)
    archive_id: str = Field(min_length=1)


class ChallengeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction: str = Field(
        default="Challenge this conclusion",
        min_length=1,
        max_length=1000,
    )


class ReelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_ids: list[str] = Field(min_length=1, max_length=50)


@lru_cache(maxsize=1)
def get_investigation_engine() -> InvestigationEngine:
    return InvestigationEngine()


def engine_dependency() -> InvestigationEngine:
    return get_investigation_engine()


@router.post("", response_model=Investigation)
def create_investigation(
    request: CreateInvestigationRequest,
    engine: InvestigationEngine = Depends(engine_dependency),
) -> Investigation:
    try:
        return engine.create(request.query, request.archive_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{investigation_id}", response_model=Investigation)
def get_investigation(
    investigation_id: str,
    engine: InvestigationEngine = Depends(engine_dependency),
) -> Investigation:
    try:
        return engine.get(investigation_id)
    except InvestigationNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation {investigation_id!r} was not found.",
        ) from error


@router.post("/{investigation_id}/challenge", response_model=ChallengeResult)
def challenge_investigation(
    investigation_id: str,
    request: ChallengeRequest,
    engine: InvestigationEngine = Depends(engine_dependency),
) -> ChallengeResult:
    try:
        return engine.challenge(investigation_id, request.instruction)
    except InvestigationNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation {investigation_id!r} was not found.",
        ) from error
    except InvestigationConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (MissingCredentialError, VideoDBUnavailableError) as error:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "videodb_unavailable",
                "message": str(error),
            },
        ) from error


@router.post("/{investigation_id}/reel", response_model=ReelRef)
def generate_reel(
    investigation_id: str,
    request: ReelRequest,
    engine: InvestigationEngine = Depends(engine_dependency),
) -> ReelRef:
    try:
        return engine.generate_reel(investigation_id, request.event_ids)
    except InvestigationNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation {investigation_id!r} was not found.",
        ) from error


@router.get("/{investigation_id}/packet")
def get_packet(
    investigation_id: str,
    engine: InvestigationEngine = Depends(engine_dependency),
) -> Response:
    try:
        packet = engine.packet(investigation_id)
    except InvestigationNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation {investigation_id!r} was not found.",
        ) from error

    return Response(
        content=packet.model_dump_json(indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="strata-{investigation_id}.json"'
            )
        },
    )
