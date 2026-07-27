"""Strata API.

Run locally with:

    ./.venv/bin/uvicorn services.api.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import archive, health, investigations, proof

logging.basicConfig(
    level=logging.INFO,
    # Investigation IDs and stage names are logged; secrets never are (guardrail 13).
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Strata API",
    version="0.1.0",
    description=(
        "Source-locked investigation agent for archived video. "
        "Every conclusion traces to a real archived video, exact timestamps, "
        "and a playable source clip."
    ),
)

_allowed_origins_value = os.getenv("STRATA_ALLOWED_ORIGINS") or os.getenv(
    "CLAIMTRAIL_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
_allowed_origins = [
    origin.strip()
    for origin in _allowed_origins_value.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(archive.router)
app.include_router(proof.router)
app.include_router(investigations.router)
