"""
Response Models

Defines all API response schemas used by the
Business Decision Copilot.

A single unified response contract is used for all
query types (RAG, SQL, Hybrid, Refusal).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import ConfidenceLevel, QueryType


# ==========================================================
# Citation
# ==========================================================


class Citation(BaseModel):
    """
    Represents a supporting document citation.
    """

    model_config = ConfigDict(extra="forbid")

    source: str = Field(
        ...,
        description="Document filename.",
        examples=["refund_policy.md"],
    )

    chunk_id: str = Field(
        ...,
        description="Unique chunk identifier.",
        examples=["refund_policy_chunk_004"],
    )

    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Vector similarity score.",
    )


# ==========================================================
# SQL Validation
# ==========================================================


class SQLValidationResult(BaseModel):
    """
    SQL validation outcome.
    """

    model_config = ConfigDict(extra="forbid")

    valid: bool

    reason: str | None = Field(
        default=None,
        description="Validation failure reason, if any.",
    )


# ==========================================================
# SQL Result
# ==========================================================


class SQLResult(BaseModel):
    """
    SQL execution output.
    """

    model_config = ConfigDict(extra="forbid")

    row_count: int = Field(
        default=0,
        ge=0,
    )

    columns: list[str] = Field(
        default_factory=list,
    )

    rows: list[dict[str, Any]] = Field(
        default_factory=list,
    )


# ==========================================================
# Business Insight
# ==========================================================


class BusinessInsight(BaseModel):
    """
    Structured business recommendation.
    """

    model_config = ConfigDict(extra="forbid")

    policy_summary: str | None = None

    data_summary: str | None = None

    recommendation: str | None = None

    next_steps: list[str] = Field(
        default_factory=list,
    )


# ==========================================================
# Unified API Response
# ==========================================================


class BusinessResponse(BaseModel):
    """
    Standard response returned by every endpoint.

    Unused fields remain None depending on the
    detected query type.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    # --------------------------------------------------
    # Routing
    # --------------------------------------------------

    query_type: QueryType = Field(
        ...,
        description="Detected query route.",
    )

    # --------------------------------------------------
    # Natural language answer
    # --------------------------------------------------

    answer: str = Field(
        ...,
        description="Final answer returned to the user.",
    )

    # --------------------------------------------------
    # RAG
    # --------------------------------------------------

    citations: list[Citation] = Field(
        default_factory=list,
    )

    # --------------------------------------------------
    # SQL
    # --------------------------------------------------

    generated_sql: str | None = Field(
        default=None,
        description="Generated SQL query.",
    )

    sql_validation: SQLValidationResult | None = None

    sql_result: SQLResult | None = None

    # --------------------------------------------------
    # Hybrid
    # --------------------------------------------------

    business_insight: BusinessInsight | None = None

    # --------------------------------------------------
    # Confidence
    # --------------------------------------------------

    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

    confidence_notes: str | None = None

    # --------------------------------------------------
    # Refusal
    # --------------------------------------------------

    refusal_reason: str | None = None