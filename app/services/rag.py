"""
RAG Service

Retrieval-Augmented Generation service for answering
business document questions.

Responsibilities:
- Embed the user query
- Retrieve relevant document chunks
- Build the RAG prompt
- Invoke the LLM
- Parse the response
- Return grounded answers with citations
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.prompts import prompts
from app.retrieval.embeddings import embedding_service
from app.retrieval.vector_store import vector_store
from app.utils.llm import llm
from app.utils.parser import parser, ParserError


class RAGError(RuntimeError):
    """
    Raised when the RAG pipeline fails.
    """


@dataclass(slots=True)
class RetrievedChunk:
    """
    Internal representation of a retrieved chunk.
    """

    source: str
    chunk_id: str
    text: str
    distance: float | None = None


class RAGService:
    """
    Business document retrieval service.
    """

    def __init__(self) -> None:
        self.prompt_template = prompts.rag()

    # ---------------------------------------------------------

    def answer(
        self,
        question: str,
        top_k: int = 3,
    ) -> dict[str, Any]:
        """
        Answer a document-based business question.
        """

        query_embedding = embedding_service.embed_query(question)

        results = vector_store.search(
            embedding=query_embedding,
            top_k=top_k,
        )

        chunks = self._parse_chunks(results)

        if not chunks:
            return {
                "refuse": True,
                "reason": (
                    "No relevant business documents were found."
                ),
            }

        prompt = self._build_prompt(
            question=question,
            chunks=chunks,
        )

        response = llm.generate(prompt)

        try:
            return parser.parse_json(response)

        except ParserError as exc:
            raise RAGError(
                "Failed to parse RAG response."
            ) from exc

    # ---------------------------------------------------------

    def _parse_chunks(
        self,
        results: dict[str, Any],
    ) -> list[RetrievedChunk]:
        """
        Convert ChromaDB results into RetrievedChunk objects.
        """

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        parsed: list[RetrievedChunk] = []

        for text, metadata, distance in zip(
            documents,
            metadatas,
            distances,
        ):
            parsed.append(
                RetrievedChunk(
                    source=metadata.get("source", "unknown"),
                    chunk_id=metadata.get("chunk_id", "unknown"),
                    text=text,
                    distance=distance,
                )
            )

        return parsed

    # ---------------------------------------------------------

    def _build_prompt(
        self,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> str:
        """
        Construct the final RAG prompt.
        """

        context_parts = []

        for chunk in chunks:
            context_parts.append(
                f"""
Source:
{chunk.source}

Chunk ID:
{chunk.chunk_id}

Content:
{chunk.text}
"""
            )

        context = "\n\n".join(context_parts)

        return (
            f"{self.prompt_template}\n\n"
            f"Business Question:\n{question}\n\n"
            f"Retrieved Context:\n{context}\n\n"
            "Return ONLY the required JSON object."
        )

    # ---------------------------------------------------------

    def debug_retrieval(
        self,
        question: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Return retrieved chunks without calling the LLM.

        Used by:
            GET /debug/retrieval
        """

        embedding = embedding_service.embed_query(question)

        results = vector_store.search(
            embedding=embedding,
            top_k=top_k,
        )

        chunks = self._parse_chunks(results)

        return [
            {
                "source": chunk.source,
                "chunk_id": chunk.chunk_id,
                "distance": chunk.distance,
                "content": chunk.text,
            }
            for chunk in chunks
        ]


# ==========================================================
# Singleton
# ==========================================================

rag_service = RAGService()