"""
Request Models

Defines all incoming API request schemas used by the
Business Decision Copilot.
"""

from pydantic import BaseModel, Field, ConfigDict


class BusinessQuestionRequest(BaseModel):
    """
    Request payload for POST /ask-business.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natural language business question.",
        examples=[
            "Which product generated the highest revenue last month?"
        ],
    )


class RetrievalDebugRequest(BaseModel):
    """
    Request payload for retrieval debugging.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Question used for RAG retrieval debugging.",
    )

    top_k: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Number of retrieved chunks to return.",
    )


class SQLDebugRequest(BaseModel):
    """
    Request payload for SQL debugging.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Business question to translate into SQL.",
    )