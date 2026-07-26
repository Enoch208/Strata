"""Vercel entrypoint for the Strata FastAPI application."""

from services.api.main import app

__all__ = ["app"]
