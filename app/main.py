"""
Business Decision Copilot

FastAPI application entry point.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings
from app.retrieval.vector_store import vector_store

logger = logging.getLogger(__name__)


# ==========================================================
# Application Lifecycle
# ==========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup / Shutdown lifecycle.
    """

    # ------------------------------------------------------
    # Startup
    # ------------------------------------------------------

    logger.info("=" * 60)
    logger.info("Starting Business Decision Copilot")
    logger.info("=" * 60)

    try:
        chunk_count = vector_store.count()

        logger.info(
            "Vector collection loaded "
            f"({chunk_count} chunks)"
        )

    except Exception as exc:
        logger.warning(
            f"Vector store not initialized: {exc}"
        )

    yield

    # ------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------

    logger.info("Shutting down application")


# ==========================================================
# FastAPI App
# ==========================================================

app = FastAPI(
    title="Business Decision Copilot",
    description=(
        "AI-powered assistant combining "
        "RAG + Text2SQL for business intelligence."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ==========================================================
# Routes
# ==========================================================

app.include_router(router)


# ==========================================================
# Health Check
# ==========================================================

@app.get(
    "/",
    tags=["Health"],
)
def root():
    """
    Basic health endpoint.
    """

    return {
        "name": "Business Decision Copilot",
        "status": "healthy",
        "version": "1.0.0",
    }


@app.get(
    "/health",
    tags=["Health"],
)
def health():
    """
    Extended health check.
    """

    try:
        vector_chunks = vector_store.count()

    except Exception:
        vector_chunks = None

    return {
        "status": "healthy",
        "vector_chunks": vector_chunks,
        "environment": settings.ENVIRONMENT,
    }