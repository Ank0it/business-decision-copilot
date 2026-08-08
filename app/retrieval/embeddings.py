"""
Embedding Service

Generates dense vector embeddings for documents and queries.

Responsibilities:
- Load the embedding model once
- Encode document chunks
- Encode user queries
- Return embeddings compatible with ChromaDB
"""

from __future__ import annotations

from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """
    Wrapper around SentenceTransformers.
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, model_name: str | None = None) -> None:
        """
        Initialize the embedding model.
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.model = SentenceTransformer(self.model_name)

    # ---------------------------------------------------------
    # Document Embeddings
    # ---------------------------------------------------------

    def embed_documents(
        self,
        documents: list[str],
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple documents.

        Parameters
        ----------
        documents:
            List of document chunks.

        Returns
        -------
        List of embedding vectors.
        """

        embeddings = self.model.encode(
            documents,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return embeddings.tolist()

    # ---------------------------------------------------------
    # Query Embedding
    # ---------------------------------------------------------

    def embed_query(
        self,
        query: str,
    ) -> list[float]:
        """
        Generate an embedding for a user query.

        Parameters
        ----------
        query:
            User's natural language question.

        Returns
        -------
        Embedding vector.
        """

        embedding = self.model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return embedding.tolist()

    # ---------------------------------------------------------
    # Generic Encoder
    # ---------------------------------------------------------

    def encode(
        self,
        texts: list[str] | str,
    ) -> list[float] | list[list[float]]:
        """
        Generic encoding helper.

        Accepts either a single string or a list of strings.
        """

        if isinstance(texts, str):
            return self.embed_query(texts)

        return self.embed_documents(texts)


# ==========================================================
# Singleton
# ==========================================================

embedding_service = EmbeddingService()