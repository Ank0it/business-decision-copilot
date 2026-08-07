"""
Application Constants

Central location for enums, constant values, SQL rules,
confidence levels, and response types.
"""

from enum import Enum


# ==========================================================
# Query Routing
# ==========================================================

class QueryType(str, Enum):
    """Supported query routing types."""

    RAG = "rag"
    SQL = "sql"
    HYBRID = "hybrid"
    REFUSAL = "refusal"


# ==========================================================
# Confidence Levels
# ==========================================================

class ConfidenceLevel(str, Enum):
    """Confidence levels returned to the client."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ==========================================================
# SQL Validation
# ==========================================================

# Only SELECT queries are allowed.
ALLOWED_SQL_COMMANDS = {
    "SELECT",
}

# Any appearance of these keywords should fail validation.
FORBIDDEN_SQL_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "REPLACE",
    "TRUNCATE",
    "ATTACH",
    "DETACH",
    "VACUUM",
    "PRAGMA",
    "GRANT",
    "REVOKE",
    "MERGE",
    "CALL",
    "EXEC",
    "EXECUTE",
    "COMMIT",
    "ROLLBACK",
    "SAVEPOINT",
}

# Characters and patterns commonly used in SQL injection.
FORBIDDEN_SQL_PATTERNS = (
    ";",
    "--",
    "/*",
    "*/",
    "xp_",
    "information_schema",
)


# ==========================================================
# Retrieval Defaults
# ==========================================================

DEFAULT_TOP_K = 4

DEFAULT_CHUNK_SIZE = 600

DEFAULT_CHUNK_OVERLAP = 120


# ==========================================================
# Supported Document Types
# ==========================================================

SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".md",
    ".txt",
}


# ==========================================================
# API Response Messages
# ==========================================================

NO_DOCUMENT_EVIDENCE = (
    "I couldn't find this information in the available business documents."
)

UNSAFE_SQL_MESSAGE = (
    "This request cannot be executed because it requires an unsafe or "
    "non-read-only database operation."
)

AMBIGUOUS_QUERY_MESSAGE = (
    "Your request is ambiguous. Please provide additional details."
)

EMPTY_RESULT_MESSAGE = (
    "The query executed successfully but returned no matching records."
)


# ==========================================================
# Hybrid Response Sections
# ==========================================================

POLICY_SECTION = "Policy"

DATA_SECTION = "Observed Data"

RECOMMENDATION_SECTION = "Business Recommendation"

CONFIDENCE_SECTION = "Confidence"


# ==========================================================
# Evaluation
# ==========================================================

EXPECTED_QUERY_TYPES = {
    QueryType.RAG,
    QueryType.SQL,
    QueryType.HYBRID,
    QueryType.REFUSAL,
}


# ==========================================================
# Supported Tables
# ==========================================================

SUPPORTED_TABLES = {
    "customers",
    "orders",
    "products",
    "refunds",
    "subscriptions",
    "payments",
}


# ==========================================================
# Supported Aggregations
# ==========================================================

SUPPORTED_AGGREGATIONS = {
    "COUNT",
    "SUM",
    "AVG",
    "MIN",
    "MAX",
}


# ==========================================================
# Logging
# ==========================================================

LOGGER_NAME = "business_copilot"