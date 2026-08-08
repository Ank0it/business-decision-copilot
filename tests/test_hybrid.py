"""
Unit tests for the Hybrid Service.

Tests:
- Successful hybrid execution
- No retrieval results
- SQL generation refusal
- SQL validation failure
- Parser failure
- Prompt generation
"""

from __future__ import annotations

import pytest

from app.services.hybrid import (
    HybridService,
    HybridServiceError,
)


# ==========================================================
# Fixtures
# ==========================================================

@pytest.fixture
def hybrid():
    return HybridService()


# ==========================================================
# Prompt Builder
# ==========================================================

def test_build_prompt(hybrid):

    retrieval = [
        {
            "source": "refund_policy.md",
            "chunk_id": "12",
            "content": "Refunds are allowed within 30 days."
        }
    ]

    execution = {
        "columns": ["category", "refunds"],
        "rows": [
            {
                "category": "electronics",
                "refunds": 22,
            }
        ],
        "row_count": 1,
    }

    prompt = hybrid._build_prompt(
        question="Which product should Finance investigate?",
        retrieval=retrieval,
        sql="SELECT * FROM payments",
        execution=execution,
    )

    assert "Which product should Finance investigate?" in prompt
    assert "refund_policy.md" in prompt
    assert "SELECT * FROM payments" in prompt
    assert "electronics" in prompt


# ==========================================================
# Successful Hybrid Pipeline
# ==========================================================

def test_hybrid_success(
    hybrid,
    monkeypatch,
):

    monkeypatch.setattr(
        "app.services.hybrid.rag_service.debug_retrieval",
        lambda question: [
            {
                "source": "refund_policy.md",
                "chunk_id": "1",
                "content": "Refunds allowed."
            }
        ],
    )

    class SQLGeneration:

        sql = "SELECT * FROM payments"

    monkeypatch.setattr(
        "app.services.hybrid.sql_generator.generate",
        lambda question: SQLGeneration(),
    )

    class Validation:

        valid = True

        reason = None

    monkeypatch.setattr(
        "app.services.hybrid.sql_validator.validate",
        lambda sql: Validation(),
    )

    class Execution:

        def model_dump(self):

            return {
                "columns": ["payment_value"],
                "rows": [
                    {
                        "payment_value": 200
                    }
                ],
                "row_count": 1,
            }

    monkeypatch.setattr(
        "app.services.hybrid.sql_executor.execute",
        lambda sql: Execution(),
    )

    monkeypatch.setattr(
        "app.services.hybrid.llm.generate",
        lambda prompt: "{}",
    )

    monkeypatch.setattr(
        "app.services.hybrid.parser.parse_and_validate",
        lambda **kwargs: {
            "policy_summary": "Policy",
            "data_summary": "Data",
            "recommendation": "Investigate electronics",
            "confidence_notes": "High",
        },
    )

    result = hybrid.answer(
        "Which products should Finance investigate?"
    )

    assert result["recommendation"] == "Investigate electronics"


# ==========================================================
# No Retrieval
# ==========================================================

def test_no_retrieval(
    hybrid,
    monkeypatch,
):

    monkeypatch.setattr(
        "app.services.hybrid.rag_service.debug_retrieval",
        lambda question: [],
    )

    result = hybrid.answer(
        "Test"
    )

    assert result["refuse"] is True

    assert "No relevant" in result["reason"]


# ==========================================================
# SQL Refusal
# ==========================================================

def test_sql_generation_refusal(
    hybrid,
    monkeypatch,
):

    monkeypatch.setattr(
        "app.services.hybrid.rag_service.debug_retrieval",
        lambda question: [
            {
                "source": "policy.md",
                "chunk_id": "1",
                "content": "Policy"
            }
        ],
    )

    class Refusal:

        refuse = True

        reason = "Unsafe request"

    monkeypatch.setattr(
        "app.services.hybrid.sql_generator.generate",
        lambda question: Refusal(),
    )

    result = hybrid.answer(
        "Delete payments"
    )

    assert result["refuse"] is True

    assert result["reason"] == "Unsafe request"


# ==========================================================
# SQL Validation Failure
# ==========================================================

def test_validation_failure(
    hybrid,
    monkeypatch,
):

    monkeypatch.setattr(
        "app.services.hybrid.rag_service.debug_retrieval",
        lambda question: [
            {
                "source": "policy.md",
                "chunk_id": "1",
                "content": "Policy"
            }
        ],
    )

    class SQLGeneration:

        sql = "SELECT * FROM hackers"

    monkeypatch.setattr(
        "app.services.hybrid.sql_generator.generate",
        lambda question: SQLGeneration(),
    )

    class Validation:

        valid = False

        reason = "Unknown table"

    monkeypatch.setattr(
        "app.services.hybrid.sql_validator.validate",
        lambda sql: Validation(),
    )

    result = hybrid.answer(
        "Show hackers"
    )

    assert result["refuse"] is True

    assert result["reason"] == "Unknown table"


# ==========================================================
# Parser Failure
# ==========================================================

def test_parser_failure(
    hybrid,
    monkeypatch,
):

    monkeypatch.setattr(
        "app.services.hybrid.rag_service.debug_retrieval",
        lambda question: [
            {
                "source": "policy.md",
                "chunk_id": "1",
                "content": "Policy"
            }
        ],
    )

    class SQLGeneration:

        sql = "SELECT * FROM customers"

    monkeypatch.setattr(
        "app.services.hybrid.sql_generator.generate",
        lambda question: SQLGeneration(),
    )

    class Validation:

        valid = True

        reason = None

    monkeypatch.setattr(
        "app.services.hybrid.sql_validator.validate",
        lambda sql: Validation(),
    )

    class Execution:

        def model_dump(self):

            return {
                "columns": [],
                "rows": [],
                "row_count": 0,
            }

    monkeypatch.setattr(
        "app.services.hybrid.sql_executor.execute",
        lambda sql: Execution(),
    )

    monkeypatch.setattr(
        "app.services.hybrid.llm.generate",
        lambda prompt: "INVALID",
    )

    def raise_error(**kwargs):

        from app.utils.parser import ParserError

        raise ParserError("Invalid JSON")

    monkeypatch.setattr(
        "app.services.hybrid.parser.parse_and_validate",
        raise_error,
    )

    with pytest.raises(HybridServiceError):

        hybrid.answer(
            "Test"
        )