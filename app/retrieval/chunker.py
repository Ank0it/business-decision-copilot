"""
Document Chunker

Splits business documents into overlapping chunks suitable for
semantic search.

Responsibilities:
- Read markdown/text documents
- Split into overlapping chunks
- Preserve document metadata
- Generate deterministic chunk IDs
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


# ==========================================================
# Data Model
# ==========================================================


@dataclass(slots=True)
class DocumentChunk:
    """
    Represents a single document chunk.
    """

    chunk_id: str
    source: str
    text: str
    chunk_index: int


# ==========================================================
# Chunker
# ==========================================================


class DocumentChunker:
    """
    Creates overlapping text chunks.
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
    ) -> None:

        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")

        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative.")

        if chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size."
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    # ---------------------------------------------------------

    def chunk_file(
        self,
        path: str | Path,
    ) -> list[DocumentChunk]:
        """
        Read a file and split it into chunks.
        """

        path = Path(path)

        text = path.read_text(
            encoding="utf-8",
        )

        return self.chunk_text(
            text=text,
            source=path.name,
        )

    # ---------------------------------------------------------

    def chunk_text(
        self,
        text: str,
        source: str,
    ) -> list[DocumentChunk]:
        """
        Split raw text into overlapping chunks.
        """

        text = text.strip()

        if not text:
            return []

        chunks: list[DocumentChunk] = []

        start = 0
        index = 0

        while start < len(text):

            end = min(
                start + self.chunk_size,
                len(text),
            )

            # Prefer splitting at paragraph boundary
            split = text.rfind(
                "\n\n",
                start,
                end,
            )

            # Fall back to newline
            if split == -1:
                split = text.rfind(
                    "\n",
                    start,
                    end,
                )

            # Fall back to space
            if split == -1:
                split = text.rfind(
                    " ",
                    start,
                    end,
                )

            # Last resort
            if split <= start:
                split = end

            chunk = text[start:split].strip()

            if chunk:

                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{source}_{index:04}",
                        source=source,
                        text=chunk,
                        chunk_index=index,
                    )
                )

                index += 1

            old_start = start
            start = max(
                0,
                split - self.chunk_overlap,               
            )

            if start <= old_start:
                start = split

        return chunks

    # ---------------------------------------------------------

    def chunk_directory(
        self,
        directory: str | Path,
    ) -> list[DocumentChunk]:
        """
        Chunk every markdown/text file inside a directory.
        """

        directory = Path(directory)

        all_chunks: list[DocumentChunk] = []

        for file in sorted(directory.iterdir()):

            if file.suffix.lower() not in {
                ".md",
                ".txt",
            }:
                continue

            all_chunks.extend(
                self.chunk_file(file)
            )

        return all_chunks


# ==========================================================
# Singleton
# ==========================================================

chunker = DocumentChunker()