"""
API request models.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BusinessRequest(BaseModel):
    """Request for the main business question endpoint."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural-language business question.",
    )


class RetrievalDebugRequest(BaseModel):
    """Request model for retrieval debugging."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
    )

    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
    )


class SQLDebugRequest(BaseModel):
    """Request model for SQL debugging."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=2000,
    )