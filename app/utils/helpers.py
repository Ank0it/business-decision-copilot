"""
General Helper Utilities

Reusable helper functions shared across the Business Decision
Copilot.

These helpers are intentionally framework-agnostic and contain
no business logic.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any


# ==========================================================
# Text Utilities
# ==========================================================


def normalize_text(text: str) -> str:
    """
    Normalize whitespace in text.

    Example:
        " Hello   World\\n\\n"
            -> "Hello World"
    """

    return " ".join(text.strip().split())


def remove_markdown_fences(text: str) -> str:
    """
    Remove markdown code fences that LLMs occasionally return.

    Supports:

    ```json
    ...
    ```

    ```sql
    ...
    ```

    ```
    ...
    ```
    """

    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if len(lines) >= 2:
            text = "\n".join(lines[1:])

        if text.endswith("```"):
            text = text[:-3]

    return text.strip()


def truncate_text(
    text: str,
    max_length: int = 200,
) -> str:
    """
    Truncate text while preserving readability.
    """

    if len(text) <= max_length:
        return text

    return text[: max_length - 3].rstrip() + "..."


# ==========================================================
# Collection Utilities
# ==========================================================


def unique_preserve_order(
    values: Iterable[Any],
) -> list[Any]:
    """
    Remove duplicates while preserving original order.
    """

    seen = set()
    result = []

    for value in values:
        if value in seen:
            continue

        seen.add(value)
        result.append(value)

    return result


# ==========================================================
# Confidence Utilities
# ==========================================================


def confidence_from_similarity(
    similarity: float,
) -> str:
    """
    Convert a similarity score into a confidence label.

    Similarity must be between 0 and 1.
    """

    similarity = max(0.0, min(1.0, similarity))

    if similarity >= 0.90:
        return "high"

    if similarity >= 0.75:
        return "medium"

    return "low"


# ==========================================================
# SQL Utilities
# ==========================================================


def is_select_query(sql: str) -> bool:
    """
    Returns True only if the SQL begins with SELECT.

    Used as an additional safety check before validation.
    """

    sql = normalize_text(sql).lower()

    return sql.startswith("select")


# ==========================================================
# Citation Utilities
# ==========================================================


def format_citation(
    source: str,
    chunk_id: str,
) -> str:
    """
    Format a citation string.

    Example

    refund_policy.md (chunk_004)
    """

    return f"{source} ({chunk_id})"


# ==========================================================
# Filename Utilities
# ==========================================================


def safe_filename(name: str) -> str:
    """
    Convert arbitrary text into a filesystem-safe filename.
    """

    name = normalize_text(name).lower()

    name = re.sub(r"[^a-z0-9_-]+", "_", name)

    return name.strip("_")


# ==========================================================
# Miscellaneous
# ==========================================================


def chunks(
    items: list[Any],
    size: int,
) -> list[list[Any]]:
    """
    Split a list into fixed-size chunks.

    Example

    [1,2,3,4,5]

    size=2

    ->

    [[1,2],[3,4],[5]]
    """

    if size <= 0:
        raise ValueError("Chunk size must be greater than zero.")

    return [
        items[i : i + size]
        for i in range(0, len(items), size)
    ]