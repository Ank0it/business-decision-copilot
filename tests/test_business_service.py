"""
Unit tests for BusinessService orchestration.

Tests the dispatch, normalization, and error-handling logic
of the central BusinessService without requiring a real LLM.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.constants import ConfidenceLevel, QueryType
from app.models.response import (
    BusinessInsight,
    BusinessResponse,
    Citation,
    SQLValidationResult,
)
from app.services.business_service import BusinessService
from app.services.sql_executor import SQLExecutionError
from app.models.sql import SQLExecutionResult, SQLGeneration, SQLRefusal
from app.services.sql_validator import SQLValidator


# ==========================================================
# Fixtures
# ==========================================================

@pytest.fixture
def service():
    return BusinessService()


def _mock_router(monkeypatch, route: QueryType, reason: str = "test"):
    """Patch router.classify to return a deterministic decision."""
    decision = MagicMock()
    decision.route = route
    decision.reason = reason
    monkeypatch.setattr(
        "app.services.business_service.router.classify",
        lambda question: decision,
    )


# ==========================================================
# RAG Dispatch
# ==========================================================

def test_rag_dispatch_success(service, monkeypatch):
    _mock_router(monkeypatch, QueryType.RAG)

    monkeypatch.setattr(
        "app.services.business_service.rag_service.answer",
        lambda question: {
            "answer": "Refunds are allowed within 30 days.",
            "citations": [
                {"source": "refund_policy.md", "chunk_id": "chunk_001"}
            ],
        },
    )

    response = service.ask("What is the refund policy?")

    assert isinstance(response, BusinessResponse)
    assert response.query_type == QueryType.RAG
    assert response.answer == "Refunds are allowed within 30 days."
    assert len(response.citations) == 1
    assert response.citations[0].source == "refund_policy.md"
    assert response.confidence == ConfidenceLevel.MEDIUM


def test_rag_dispatch_refusal(service, monkeypatch):
    _mock_router(monkeypatch, QueryType.RAG)

    monkeypatch.setattr(
        "app.services.business_service.rag_service.answer",
        lambda question: {
            "refuse": True,
            "reason": "No relevant documents found.",
        },
    )

    response = service.ask("Unknown topic")

    assert response.query_type == QueryType.RAG
    assert response.refusal_reason == "No relevant documents found."
    assert response.confidence == ConfidenceLevel.LOW


def test_rag_dispatch_string_citations(service, monkeypatch):
    _mock_router(monkeypatch, QueryType.RAG)

    monkeypatch.setattr(
        "app.services.business_service.rag_service.answer",
        lambda question: {
            "answer": "Policy found.",
            "citations": ["refund_policy.md"],
        },
    )

    response = service.ask("Policy question")

    assert len(response.citations) == 1
    assert response.citations[0].source == "refund_policy.md"
    assert response.citations[0].chunk_id is None


# ==========================================================
# SQL Dispatch
# ==========================================================

def test_sql_dispatch_success(service, monkeypatch):
    _mock_router(monkeypatch, QueryType.SQL)

    monkeypatch.setattr(
        "app.services.business_service.sql_generator.generate",
        lambda question: SQLGeneration(sql="SELECT * FROM customers"),
    )

    monkeypatch.setattr(
        "app.services.business_service.sql_validator.validate",
        lambda sql: SQLValidator().validate(sql),
    )

    execution = SQLExecutionResult(
        row_count=10,
        columns=["customer_id", "customer_city"],
        rows=[{"customer_id": "1", "customer_city": "NYC"}],
    )

    monkeypatch.setattr(
        "app.services.business_service.sql_executor.execute",
        lambda sql: execution,
    )

    response = service.ask("How many customers are there?")

    assert response.query_type == QueryType.SQL
    assert "10 rows" in response.answer
    assert response.generated_sql == "SELECT * FROM customers"
    assert response.sql_result is not None
    assert response.sql_result.row_count == 10
    assert response.confidence == ConfidenceLevel.HIGH


def test_sql_dispatch_generator_refusal(service, monkeypatch):
    _mock_router(monkeypatch, QueryType.SQL)

    monkeypatch.setattr(
        "app.services.business_service.sql_generator.generate",
        lambda question: SQLRefusal(reason="Unsafe request"),
    )

    response = service.ask("Delete all data")

    assert response.query_type == QueryType.SQL
    assert response.refusal_reason == "Unsafe request"
    assert response.confidence == ConfidenceLevel.LOW


def test_sql_dispatch_validation_failure(service, monkeypatch):
    _mock_router(monkeypatch, QueryType.SQL)

    monkeypatch.setattr(
        "app.services.business_service.sql_generator.generate",
        lambda question: SQLGeneration(sql="DROP TABLE customers"),
    )

    response = service.ask("Drop the customers table")

    assert response.query_type == QueryType.SQL
    assert "safety validation" in response.answer
    assert response.refusal_reason is not None
    assert response.confidence == ConfidenceLevel.LOW


def test_sql_dispatch_execution_error(service, monkeypatch):
    _mock_router(monkeypatch, QueryType.SQL)

    monkeypatch.setattr(
        "app.services.business_service.sql_generator.generate",
        lambda question: SQLGeneration(sql="SELECT * FROM customers"),
    )

    monkeypatch.setattr(
        "app.services.business_service.sql_validator.validate",
        lambda sql: SQLValidator().validate(sql),
    )

    monkeypatch.setattr(
        "app.services.business_service.sql_executor.execute",
        lambda sql: (_ for _ in ()).throw(SQLExecutionError("DB down")),
    )

    with pytest.raises(SQLExecutionError):
        service.ask("How many customers?")


# ==========================================================
# Hybrid Dispatch
# ==========================================================

def test_hybrid_dispatch_success(service, monkeypatch):
    _mock_router(monkeypatch, QueryType.HYBRID)

    monkeypatch.setattr(
        "app.services.business_service.hybrid_service.answer",
        lambda question: {
            "policy_summary": "Late deliveries are refundable.",
            "data_summary": "15% of orders were delivered late.",
            "recommendation": "Review carrier performance.",
            "next_steps": ["Audit carriers", "Update SLA"],
            "confidence_notes": "Medium confidence.",
        },
    )

    response = service.ask(
        "Based on our refund policy, how many orders were delivered late?"
    )

    assert response.query_type == QueryType.HYBRID
    assert response.answer == "Review carrier performance."
    assert response.business_insight is not None
    assert response.business_insight.policy_summary == "Late deliveries are refundable."
    assert response.business_insight.data_summary == "15% of orders were delivered late."
    assert response.business_insight.next_steps == ["Audit carriers", "Update SLA"]
    assert response.confidence == ConfidenceLevel.MEDIUM


def test_hybrid_dispatch_refusal(service, monkeypatch):
    _mock_router(monkeypatch, QueryType.HYBRID)

    monkeypatch.setattr(
        "app.services.business_service.hybrid_service.answer",
        lambda question: {
            "refuse": True,
            "reason": "Insufficient evidence.",
        },
    )

    response = service.ask("Hybrid question")

    assert response.query_type == QueryType.HYBRID
    assert response.refusal_reason == "Insufficient evidence."
    assert response.confidence == ConfidenceLevel.LOW


# ==========================================================
# Refusal Dispatch
# ==========================================================

def test_refusal_dispatch(service, monkeypatch):
    _mock_router(monkeypatch, QueryType.REFUSAL, "Unsafe request")

    response = service.ask("Hack the payment system")

    assert response.query_type == QueryType.REFUSAL
    assert response.refusal_reason == "Unsafe request"
    assert response.confidence == ConfidenceLevel.LOW
    assert response.answer == "I cannot process this request."


# ==========================================================
# Citation Builder
# ==========================================================

def test_build_citations_dicts(service):
    raw = [
        {"source": "policy.md", "chunk_id": "c1", "score": 0.9},
        {"source": "terms.md", "chunk_id": "c2"},
    ]

    citations = service._build_citations(raw)

    assert len(citations) == 2
    assert citations[0].source == "policy.md"
    assert citations[0].chunk_id == "c1"
    assert citations[0].score == 0.9
    assert citations[1].score is None


def test_build_citations_strings(service):
    raw = ["policy.md", "terms.md"]

    citations = service._build_citations(raw)

    assert len(citations) == 2
    assert citations[0].source == "policy.md"
    assert citations[0].chunk_id is None
    assert citations[0].score is None


def test_build_citations_mixed(service):
    raw = [
        {"source": "policy.md", "chunk_id": "c1"},
        "terms.md",
    ]

    citations = service._build_citations(raw)

    assert len(citations) == 2
    assert citations[0].chunk_id == "c1"
    assert citations[1].source == "terms.md"
    assert citations[1].chunk_id is None


def test_build_citations_empty(service):
    citations = service._build_citations([])

    assert citations == []


# ==========================================================
# Router Validation
# ==========================================================

def test_router_returns_valid_route(service, monkeypatch):
    from app.services.router import RoutingDecision

    decision = RoutingDecision(
        route=QueryType.SQL,
        reason="Analytics question",
    )
    monkeypatch.setattr(
        "app.services.business_service.router.classify",
        lambda question: decision,
    )

    monkeypatch.setattr(
        "app.services.business_service.sql_generator.generate",
        lambda question: SQLGeneration(sql="SELECT * FROM customers"),
    )

    monkeypatch.setattr(
        "app.services.business_service.sql_validator.validate",
        lambda sql: SQLValidator().validate(sql),
    )

    execution = SQLExecutionResult(
        row_count=1,
        columns=["cnt"],
        rows=[{"cnt": 1}],
    )

    monkeypatch.setattr(
        "app.services.business_service.sql_executor.execute",
        lambda sql: execution,
    )

    response = service.ask("Total revenue")

    assert response.query_type == QueryType.SQL


def test_router_unknown_route_falls_back_to_refusal(service, monkeypatch):
    """If the router somehow returns an unknown route, BusinessService
    should safely fall back to refusal rather than crash."""

    class BadDecision:
        route = "invalid_route"
        reason = "unexpected route"

    monkeypatch.setattr(
        "app.services.business_service.router.classify",
        lambda question: BadDecision(),
    )

    response = service.ask("Test question")

    assert response.query_type == QueryType.REFUSAL
    assert response.refusal_reason == "unexpected route"
