"""
API tests for the Business Decision Copilot.

Tests:
- Health endpoints
- POST /ask-business
- GET /debug/retrieval
- GET /debug/sql
- Validation errors
- Internal server errors
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ==========================================================
# Health Endpoints
# ==========================================================

def test_root():

    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Business Decision Copilot"
    assert data["status"] == "healthy"


def test_health(monkeypatch):

    monkeypatch.setattr(
        "app.main.vector_store.count",
        lambda: 70,
    )

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["vector_chunks"] == 70


# ==========================================================
# POST /ask-business
# ==========================================================

def test_ask_business_success(monkeypatch):

    monkeypatch.setattr(
        "app.api.routes.business_service.ask",
        lambda question: {
            "query_type": "rag",
            "answer": "Refunds are allowed within 30 days.",
            "citations": [
                {"source": "refund_policy.md", "chunk_id": "chunk_001", "score": 0.95}
            ],
            "business_insight": None,
            "confidence_notes": "High",
            "refusal_reason": None,
        },
    )

    response = client.post(
        "/ask-business",
        json={
            "question": "What is the refund policy?"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["query_type"] == "rag"


def test_ask_business_validation_error():

    response = client.post(
        "/ask-business",
        json={},
    )

    assert response.status_code == 422


def test_ask_business_server_error(monkeypatch):

    def raise_error(question):
        raise RuntimeError("Unexpected failure")

    monkeypatch.setattr(
        "app.api.routes.business_service.ask",
        raise_error,
    )

    response = client.post(
        "/ask-business",
        json={
            "question": "Revenue"
        },
    )

    assert response.status_code == 500


# ==========================================================
# GET /debug/retrieval
# ==========================================================

def test_debug_retrieval(monkeypatch):

    monkeypatch.setattr(
        "app.api.routes.rag_service.debug_retrieval",
        lambda question: [
            {
                "source": "refund_policy.md",
                "chunk_id": "1",
                "distance": 0.12,
                "content": "Refunds allowed."
            }
        ],
    )

    response = client.get(
        "/debug/retrieval",
        params={
            "question": "refund"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["chunks"]) == 1

    assert (
        data["chunks"][0]["source"]
        == "refund_policy.md"
    )


def test_debug_retrieval_server_error(monkeypatch):

    def raise_error(question):
        raise RuntimeError()

    monkeypatch.setattr(
        "app.api.routes.rag_service.debug_retrieval",
        raise_error,
    )

    response = client.get(
        "/debug/retrieval",
        params={
            "question": "refund"
        },
    )

    assert response.status_code == 500


# ==========================================================
# GET /debug/sql
# ==========================================================

def test_debug_sql(monkeypatch):

    class SQL:

        sql = "SELECT * FROM customers"

    monkeypatch.setattr(
        "app.api.routes.sql_generator.generate",
        lambda question: SQL(),
    )

    class Validation:

        def model_dump(self):

            return {
                "valid": True,
                "reason": None,
            }

    monkeypatch.setattr(
        "app.api.routes.sql_validator.validate",
        lambda sql: Validation(),
    )

    response = client.get(
        "/debug/sql",
        params={
            "question": "Show customers"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["generated_sql"]
        == "SELECT * FROM customers"
    )

    assert (
        data["validation"]["valid"]
        is True
    )


def test_debug_sql_refusal(monkeypatch):

    class Refusal:

        refuse = True

        def model_dump(self):

            return {
                "refuse": True,
                "reason": "Unsafe request",
            }

    monkeypatch.setattr(
        "app.api.routes.sql_generator.generate",
        lambda question: Refusal(),
    )

    response = client.get(
        "/debug/sql",
        params={
            "question": "Delete database"
        },
    )

    assert response.status_code == 200

    assert response.json()["refuse"] is True


def test_debug_sql_server_error(monkeypatch):

    def raise_error(question):
        raise RuntimeError()

    monkeypatch.setattr(
        "app.api.routes.sql_generator.generate",
        raise_error,
    )

    response = client.get(
        "/debug/sql",
        params={
            "question": "Revenue"
        },
    )

    assert response.status_code == 500


# ==========================================================
# Query Parameter Validation
# ==========================================================

def test_debug_sql_missing_query():

    response = client.get(
        "/debug/sql"
    )

    assert response.status_code == 422


def test_debug_retrieval_missing_query():

    response = client.get(
        "/debug/retrieval"
    )

    assert response.status_code == 422