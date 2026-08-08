"""
Vector Store

Wrapper around ChromaDB used for document retrieval.

Responsibilities:
- Create and manage the ChromaDB collection
- Store embedded document chunks
- Retrieve relevant chunks using semantic search
- Hide ChromaDB implementation details from the rest of the application
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from app.core.config import settings


class VectorStore:
    """
    ChromaDB wrapper.
    """

    COLLECTION_NAME = "business_documents"

    def __init__(self) -> None:
        persist_directory = Path(settings.CHROMA_DIR)

        persist_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.client = chromadb.PersistentClient(
            path=str(persist_directory)
        )

        self.collection: Collection = (
            self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={
                    "description": "Business Decision Copilot documents"
                },
            )
        )

    # ---------------------------------------------------------
    # Insert Documents
    # ---------------------------------------------------------

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """
        Insert document chunks into ChromaDB.
        """

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    # ---------------------------------------------------------
    # Semantic Search
    # ---------------------------------------------------------

    def search(
        self,
        embedding: list[float],
        top_k: int = 3,
    ) -> dict[str, Any]:
        """
        Retrieve the most relevant chunks.
        """

        return self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
        )

    # ---------------------------------------------------------
    # Utilities
    # ---------------------------------------------------------

    def count(self) -> int:
        """
        Return number of indexed chunks.
        """

        return self.collection.count()

    def reset(self) -> None:
        """
        Delete and recreate the collection.
        Useful during development and re-ingestion.
        """

        self.client.delete_collection(self.COLLECTION_NAME)

        self.collection = (
            self.client.get_or_create_collection(
                name=self.COLLECTION_NAME
            )
        )


# ==========================================================
# Singleton
# ==========================================================

vector_store = VectorStore()