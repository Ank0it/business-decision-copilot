"""
Refusal Service

Centralizes all refusal responses used throughout the
Business Decision Copilot.

Responsibilities
----------------
- Handle unsafe SQL requests
- Handle unsupported business questions
- Handle ambiguous questions
- Handle missing evidence
- Handle missing documents
- Handle missing SQL results
- Provide consistent refusal payloads
"""

from __future__ import annotations

from typing import Any


class RefusalService:
    """
    Factory for standardized refusal responses.
    """

    # ---------------------------------------------------------
    # Generic
    # ---------------------------------------------------------

    @staticmethod
    def unsupported(
        reason: str = (
            "This request is not supported by the Business Decision Copilot."
        ),
    ) -> dict[str, Any]:
        return {
            "refuse": True,
            "reason": reason,
        }

    # ---------------------------------------------------------
    # Unsafe SQL
    # ---------------------------------------------------------

    @staticmethod
    def unsafe_sql(
        reason: str = (
            "Only read-only SELECT queries are permitted."
        ),
    ) -> dict[str, Any]:
        return {
            "refuse": True,
            "reason": reason,
        }

    # ---------------------------------------------------------
    # Ambiguous Question
    # ---------------------------------------------------------

    @staticmethod
    def ambiguous_question() -> dict[str, Any]:
        return {
            "refuse": True,
            "reason": (
                "The question is ambiguous. Please provide more specific details."
            ),
        }

    # ---------------------------------------------------------
    # Missing Policy Evidence
    # ---------------------------------------------------------

    @staticmethod
    def missing_documents() -> dict[str, Any]:
        return {
            "refuse": True,
            "reason": (
                "No relevant business documents were found to answer this question."
            ),
        }

    # ---------------------------------------------------------
    # Missing SQL Evidence
    # ---------------------------------------------------------

    @staticmethod
    def missing_data() -> dict[str, Any]:
        return {
            "refuse": True,
            "reason": (
                "The requested business data is unavailable or returned no results."
            ),
        }

    # ---------------------------------------------------------
    # Hybrid Evidence
    # ---------------------------------------------------------

    @staticmethod
    def insufficient_hybrid_evidence() -> dict[str, Any]:
        return {
            "refuse": True,
            "reason": (
                "Insufficient policy and/or business data to produce a grounded recommendation."
            ),
        }

    # ---------------------------------------------------------
    # SQL Validation Failure
    # ---------------------------------------------------------

    @staticmethod
    def sql_validation(
        reason: str,
    ) -> dict[str, Any]:
        return {
            "refuse": True,
            "reason": reason,
        }

    # ---------------------------------------------------------
    # Database Error
    # ---------------------------------------------------------

    @staticmethod
    def database_error() -> dict[str, Any]:
        return {
            "refuse": True,
            "reason": (
                "The database could not process the request."
            ),
        }

    # ---------------------------------------------------------
    # LLM Error
    # ---------------------------------------------------------

    @staticmethod
    def llm_error() -> dict[str, Any]:
        return {
            "refuse": True,
            "reason": (
                "The language model failed to generate a valid response."
            ),
        }

    # ---------------------------------------------------------
    # Internal Error
    # ---------------------------------------------------------

    @staticmethod
    def internal_error() -> dict[str, Any]:
        return {
            "refuse": True,
            "reason": (
                "An internal error occurred while processing the request."
            ),
        }


# ==========================================================
# Singleton
# ==========================================================

refusal_service = RefusalService()