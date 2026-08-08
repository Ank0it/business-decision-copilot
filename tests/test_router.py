"""
Unit tests for QueryRouter.

Tests:
- Valid routing
- Invalid JSON
- Missing fields
- Unsupported routes
- LLM invocation
"""

from __future__ import annotations

import pytest

from app.core.constants import QueryType
from app.services.router import QueryRouter, RoutingDecision


# ==========================================================
# Fixtures
# ==========================================================

@pytest.fixture
def router():
    return QueryRouter()


# ==========================================================
# Parsing Tests
# ==========================================================

def test_parse_valid_rag(router):
    response = """
    {
        "route": "rag",
        "reason": "Policy document question"
    }
    """

    decision = router._parse_response(response)

    assert isinstance(decision, RoutingDecision)
    assert decision.route == QueryType.RAG
    assert decision.reason == "Policy document question"


def test_parse_valid_sql(router):
    response = """
    {
        "route": "sql",
        "reason": "Requires structured data"
    }
    """

    decision = router._parse_response(response)

    assert decision.route == QueryType.SQL


def test_parse_valid_hybrid(router):
    response = """
    {
        "route": "hybrid",
        "reason": "Needs policy and database"
    }
    """

    decision = router._parse_response(response)

    assert decision.route == QueryType.HYBRID


def test_parse_valid_refusal(router):
    response = """
    {
        "route": "refusal",
        "reason": "Unsafe request"
    }
    """

    decision = router._parse_response(response)

    assert decision.route == QueryType.REFUSAL


# ==========================================================
# Invalid JSON
# ==========================================================

def test_invalid_json(router):

    with pytest.raises(ValueError):

        router._parse_response(
            "this is not json"
        )


# ==========================================================
# Missing Fields
# ==========================================================

def test_missing_route(router):

    response = """
    {
        "reason":"missing route"
    }
    """

    with pytest.raises(ValueError):

        router._parse_response(response)


def test_missing_reason(router):

    response = """
    {
        "route":"rag"
    }
    """

    with pytest.raises(ValueError):

        router._parse_response(response)


# ==========================================================
# Invalid Route
# ==========================================================

def test_invalid_route(router):

    response = """
    {
        "route":"banana",
        "reason":"invalid"
    }
    """

    with pytest.raises(ValueError):

        router._parse_response(response)


# ==========================================================
# LLM Call
# ==========================================================

def test_classify_calls_llm(
    router,
    monkeypatch,
):

    expected = """
    {
        "route":"sql",
        "reason":"Revenue analytics"
    }
    """

    called = {
        "value": False
    }

    def fake_generate(prompt):

        called["value"] = True

        assert "Total revenue" in prompt

        return expected

    monkeypatch.setattr(
        "app.services.router.llm.generate",
        fake_generate,
    )

    decision = router.classify(
        "Total revenue last month"
    )

    assert called["value"] is True

    assert decision.route == QueryType.SQL


# ==========================================================
# Case Insensitive Route
# ==========================================================

@pytest.mark.parametrize(
    "route",
    [
        "RAG",
        "rag",
        "RaG",
    ],
)
def test_case_insensitive_routes(
    router,
    route,
):

    response = f"""
    {{
        "route":"{route}",
        "reason":"test"
    }}
    """

    decision = router._parse_response(
        response
    )

    assert decision.route == QueryType.RAG


# ==========================================================
# Reason Cleanup
# ==========================================================

def test_reason_strip(router):

    response = """
    {
        "route":"rag",
        "reason":"   Policy Found   "
    }
    """

    decision = router._parse_response(
        response
    )

    assert decision.reason == "Policy Found"