"""
Unit tests for the RAG service.
"""

from __future__ import annotations

import pytest

from app.services.rag import (
    RAGService,
    RetrievedChunk,
    RAGError,
)


# ==========================================================
# Fixtures
# ==========================================================

@pytest.fixture
def rag():
    return RAGService()


# ==========================================================
# Chunk Parsing
# ==========================================================

def test_parse_chunks_success(rag):

    results = {
        "documents": [[
            "Refunds are allowed within 30 days.",
            "Premium plans are non-refundable."
        ]],
        "metadatas": [[
            {
                "source": "refund_policy.md",
                "chunk_id": "chunk-1"
            },
            {
                "source": "pricing_policy.md",
                "chunk_id": "chunk-2"
            }
        ]],
        "distances": [[0.11, 0.28]]
    }

    chunks = rag._parse_chunks(results)

    assert len(chunks) == 2

    assert chunks[0].source == "refund_policy.md"
    assert chunks[0].chunk_id == "chunk-1"
    assert chunks[0].text == "Refunds are allowed within 30 days."
    assert chunks[0].distance == 0.11


def test_parse_chunks_empty(rag):

    results = {
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }

    chunks = rag._parse_chunks(results)

    assert chunks == []


# ==========================================================
# Prompt Construction
# ==========================================================

def test_prompt_contains_question(rag):

    chunks = [
        RetrievedChunk(
            source="refund_policy.md",
            chunk_id="1",
            text="Refunds allowed within 30 days.",
            distance=0.2,
        )
    ]

    prompt = rag._build_prompt(
        question="What is the refund policy?",
        chunks=chunks,
    )

    assert "What is the refund policy?" in prompt
    assert "Refunds allowed within 30 days." in prompt
    assert "refund_policy.md" in prompt
    assert "Chunk ID" in prompt


# ==========================================================
# Successful Answer
# ==========================================================

def test_answer_success(
    rag,
    monkeypatch,
):

    monkeypatch.setattr(
        "app.services.rag.embedding_service.embed_query",
        lambda q: [0.1, 0.2],
    )

    monkeypatch.setattr(
        "app.services.rag.vector_store.search",
        lambda **kwargs: {
            "documents": [[
                "Refunds allowed within 30 days."
            ]],
            "metadatas": [[
                {
                    "source": "refund_policy.md",
                    "chunk_id": "1",
                }
            ]],
            "distances": [[0.15]],
        },
    )

    monkeypatch.setattr(
        "app.services.rag.llm.generate",
        lambda prompt: """
        {
            "answer":"Refunds are allowed within 30 days.",
            "citations":["refund_policy.md"]
        }
        """,
    )

    monkeypatch.setattr(
        "app.services.rag.parser.parse_json",
        lambda response: {
            "answer": "Refunds are allowed within 30 days.",
            "citations": ["refund_policy.md"],
        },
    )

    result = rag.answer(
        "What is the refund policy?"
    )

    assert result["answer"].startswith("Refunds")
    assert len(result["citations"]) == 1


# ==========================================================
# No Documents Retrieved
# ==========================================================

def test_answer_no_documents(
    rag,
    monkeypatch,
):

    monkeypatch.setattr(
        "app.services.rag.embedding_service.embed_query",
        lambda q: [0.1],
    )

    monkeypatch.setattr(
        "app.services.rag.vector_store.search",
        lambda **kwargs: {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        },
    )

    result = rag.answer(
        "Unknown question"
    )

    assert result["refuse"] is True
    assert "No relevant" in result["reason"]


# ==========================================================
# Parser Failure
# ==========================================================

def test_parser_failure(
    rag,
    monkeypatch,
):

    monkeypatch.setattr(
        "app.services.rag.embedding_service.embed_query",
        lambda q: [0.1],
    )

    monkeypatch.setattr(
        "app.services.rag.vector_store.search",
        lambda **kwargs: {
            "documents": [["Policy"]],
            "metadatas": [[
                {
                    "source": "policy.md",
                    "chunk_id": "1",
                }
            ]],
            "distances": [[0.2]],
        },
    )

    monkeypatch.setattr(
        "app.services.rag.llm.generate",
        lambda prompt: "INVALID JSON",
    )

    def raise_parser(_):
        from app.utils.parser import ParserError
        raise ParserError("Invalid JSON")

    monkeypatch.setattr(
        "app.services.rag.parser.parse_json",
        raise_parser,
    )

    with pytest.raises(RAGError):
        rag.answer("Test")


# ==========================================================
# Debug Retrieval
# ==========================================================

def test_debug_retrieval(
    rag,
    monkeypatch,
):

    monkeypatch.setattr(
        "app.services.rag.embedding_service.embed_query",
        lambda q: [0.1],
    )

    monkeypatch.setattr(
        "app.services.rag.vector_store.search",
        lambda **kwargs: {
            "documents": [["Policy"]],
            "metadatas": [[
                {
                    "source": "policy.md",
                    "chunk_id": "42",
                }
            ]],
            "distances": [[0.12]],
        },
    )

    results = rag.debug_retrieval(
        "refund"
    )

    assert len(results) == 1

    assert results[0]["source"] == "policy.md"
    assert results[0]["chunk_id"] == "42"
    assert results[0]["distance"] == 0.12
    assert results[0]["content"] == "Policy"