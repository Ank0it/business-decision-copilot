"""
Application-wide constants.

The database schema in schema.sql is the source of truth.
"""

from __future__ import annotations

from enum import Enum


class QueryType(str, Enum):
    """Supported execution routes."""

    RAG = "rag"
    SQL = "sql"
    HYBRID = "hybrid"
    REFUSAL = "refusal"


class ConfidenceLevel(str, Enum):
    """Confidence labels for business recommendations."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ==========================================================
# Canonical Olist Tables
# ==========================================================

SUPPORTED_TABLES = {
    "customers",
    "sellers",
    "products",
    "orders",
    "order_items",
    "payments",
    "reviews",
    "product_categories",
    "order_summary",
}


# ==========================================================
# Read-only SQL policy
# ==========================================================

BLOCKED_SQL_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "REPLACE",
    "MERGE",
    "EXEC",
    "EXECUTE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "VACUUM",
    "GRANT",
    "REVOKE",
    "LOAD_EXTENSION",
}


BLOCKED_SQL_OPERATORS = {
    "--",
    "/*",
    "*/",
}


# ==========================================================
# SQL clauses that are not needed for the benchmark
# and can introduce unnecessary complexity.
# ==========================================================

BLOCKED_SQL_CLAUSES = {
    "UNION",
    "INTERSECT",
    "EXCEPT",
}


# ==========================================================
# Business document sources
# ==========================================================

DOCUMENT_TYPES = {
    "refund_policy",
    "pricing_policy",
    "subscription_terms",
    "shipping_returns",
    "finance_guidelines",
    "support_sop",
    "warranty_policy",
    "escalation_matrix",
}