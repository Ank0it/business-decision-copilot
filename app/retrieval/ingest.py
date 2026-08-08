"""
Document Ingestion Pipeline

Reads business documents, chunks them, generates embeddings,
and stores them in ChromaDB.

Run manually whenever the document corpus changes.

Example:
    python -m app.retrieval.ingest
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.retrieval.chunker import chunker
from app.retrieval.embeddings import embedding_service
from app.retrieval.vector_store import vector_store


class DocumentIngestor:
    """
    Ingests business documents into the vector database.
    """

    def __init__(
        self,
        reset_collection: bool = True,
    ) -> None:
        self.reset_collection = reset_collection

    # ---------------------------------------------------------

    def ingest(self) -> None:
        """
        Execute the ingestion pipeline.
        """

        documents_path = Path(settings.DOCUMENTS_PATH)

        if not documents_path.exists():
            raise FileNotFoundError(
                f"Documents directory not found: {documents_path}"
            )

        if self.reset_collection:
            vector_store.reset()

        chunks = chunker.chunk_directory(documents_path)

        if not chunks:
            raise RuntimeError(
                "No documents were found for ingestion."
            )

        ids = []
        texts = []
        metadatas = []

        for chunk in chunks:

            ids.append(chunk.chunk_id)

            texts.append(chunk.text)

            metadatas.append(
                {
                    "source": chunk.source,
                    "chunk_id": chunk.chunk_id,
                    "chunk_index": chunk.chunk_index,
                }
            )

        embeddings = embedding_service.embed_documents(texts)

        vector_store.add_documents(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        print("=" * 60)
        print("Business Decision Copilot")
        print("Document Ingestion Complete")
        print("=" * 60)
        print(f"Documents Indexed : {len(chunks)}")
        print(f"Collection Size   : {vector_store.count()}")
        print("=" * 60)


# ==========================================================
# CLI
# ==========================================================

if __name__ == "__main__":
    DocumentIngestor().ingest()