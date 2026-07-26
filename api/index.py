"""Vercel ASGI entrypoint for the Strata FastAPI service."""

from services.api.main import app

__all__ = ["app"]
