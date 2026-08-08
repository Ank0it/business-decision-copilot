"""
API Routes

Defines the REST API endpoints for the Business Decision Copilot.

Required endpoints
------------------
POST /ask-business
GET  /debug/retrieval
GET  /debug/sql
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.request import BusinessRequest
from app.models.response import BusinessResponse
from app.services.business_service import business_service
from app.services.rag import rag_service
from app.services.sql_generator import sql_generator
from app.services.sql_validator import sql_validator

router = APIRouter(tags=["Business Decision Copilot"])


# ==========================================================
# POST /ask-business
# ==========================================================

@router.post(
    "/ask-business",
    response_model=BusinessResponse,
    summary="Answer a business question",
)
def ask_business(
    request: BusinessRequest,
) -> BusinessResponse:
    """
    Main endpoint.

    Accepts a natural-language business question and returns
    a routed response (RAG, SQL, Hybrid, or Refusal).
    """

    try:
        return business_service.ask(
            request.question,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


# ==========================================================
# GET /debug/retrieval
# ==========================================================

@router.get(
    "/debug/retrieval",
    summary="Inspect retrieved document chunks",
)
def debug_retrieval(
    question: str = Query(
        ...,
        description="Business question",
    ),
):
    """
    Returns retrieved chunks without invoking the LLM.
    """

    try:
        return {
            "question": question,
            "chunks": rag_service.debug_retrieval(
                question=question,
            ),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


# ==========================================================
# GET /debug/sql
# ==========================================================

@router.get(
    "/debug/sql",
    summary="Inspect generated SQL",
)
def debug_sql(
    question: str = Query(
        ...,
        description="Business question",
    ),
):
    """
    Shows generated SQL and validation result.
    Does not execute SQL.
    """

    try:
        generated = sql_generator.generate(question)

        if hasattr(generated, "refuse") and generated.refuse:
            return generated.model_dump()

        validation = sql_validator.validate(
            generated.sql,
        )

        return {
            "question": question,
            "generated_sql": generated.sql,
            "validation": validation.model_dump(),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc