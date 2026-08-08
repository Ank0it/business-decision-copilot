"""
SQL Validator Service

Validates generated SQL before execution.

Responsibilities:
- Allow only read-only SELECT queries
- Block destructive SQL operations
- Block multi-statement queries
- Ensure only approved tables are referenced
- Return structured validation results
"""

from __future__ import annotations

import re
from pathlib import Path

from app.core.config import BASE_DIR, settings
from app.models.sql import SQLValidationResult


class SQLValidator:
    """
    Validates generated SQL for safety.
    """

    # ---------------------------------------------------------
    # Dangerous Keywords
    # ---------------------------------------------------------

    BLOCKED_KEYWORDS = {
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

    # ---------------------------------------------------------
    # SQL clauses that are not needed for the benchmark
    # and can introduce unnecessary complexity.
    # ---------------------------------------------------------

    BLOCKED_CLAUSES = {
        "UNION",
        "INTERSECT",
        "EXCEPT",
    }

    # ---------------------------------------------------------
    # Initialization
    # ---------------------------------------------------------

    def __init__(self) -> None:
        self.allowed_tables = self._load_allowed_tables()

    # ---------------------------------------------------------

    def _load_allowed_tables(self) -> set[str]:
        """
        Derive the allowed table list from schema.sql.

        Falls back to a hardcoded list if the schema file cannot
        be read.
        """

        schema_path = (
            BASE_DIR / "app" / "database" / "schema.sql"
        )

        fallback = {
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

        if not schema_path.exists():
            return fallback

        try:
            text = schema_path.read_text(encoding="utf-8")

            tables: set[str] = set()

            for match in re.finditer(
                r"CREATE\s+(?:TABLE|VIEW)\s+([A-Za-z_][A-Za-z0-9_]*)",
                text,
                flags=re.IGNORECASE,
            ):
                tables.add(match.group(1).lower())

            return tables or fallback

        except Exception:
            return fallback

    # ---------------------------------------------------------

    def validate(self, sql: str) -> SQLValidationResult:
        """
        Validate generated SQL.
        """

        sql = sql.strip()

        if not sql:
            return SQLValidationResult(
                valid=False,
                reason="Empty SQL query.",
            )

        validation_checks = [
            self._validate_single_statement,
            self._validate_select_only,
            self._validate_blocked_keywords,
            self._validate_blocked_clauses,
            self._validate_allowed_tables,
        ]

        for check in validation_checks:
            result = check(sql)

            if result is not None:
                return result

        return SQLValidationResult(
            valid=True,
            reason=None,
        )

    # =========================================================
    # Validation Rules
    # =========================================================

    def _validate_single_statement(
        self,
        sql: str,
    ) -> SQLValidationResult | None:
        """
        Prevent SQL chaining.
        """

        if ";" in sql[:-1]:
            return SQLValidationResult(
                valid=False,
                reason="Multiple SQL statements are not allowed.",
            )

        return None

    # ---------------------------------------------------------

    def _validate_select_only(
        self,
        sql: str,
    ) -> SQLValidationResult | None:

        if not sql.upper().startswith("SELECT"):
            return SQLValidationResult(
                valid=False,
                reason="Only SELECT queries are allowed.",
            )

        return None

    # ---------------------------------------------------------

    def _validate_blocked_keywords(
        self,
        sql: str,
    ) -> SQLValidationResult | None:

        upper = sql.upper()

        for keyword in self.BLOCKED_KEYWORDS:

            if re.search(rf"\b{keyword}\b", upper):

                return SQLValidationResult(
                    valid=False,
                    reason=f"Blocked SQL keyword detected: {keyword}",
                )

        return None

    # ---------------------------------------------------------

    def _validate_blocked_clauses(
        self,
        sql: str,
    ) -> SQLValidationResult | None:

        upper = sql.upper()

        for clause in self.BLOCKED_CLAUSES:

            if re.search(rf"\b{clause}\b", upper):

                return SQLValidationResult(
                    valid=False,
                    reason=f"Blocked SQL clause detected: {clause}",
                )

        return None

    # ---------------------------------------------------------

    def _validate_allowed_tables(
        self,
        sql: str,
    ) -> SQLValidationResult | None:

        matches = re.findall(
            r"(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)",
            sql,
            flags=re.IGNORECASE,
        )

        for table in matches:

            if table.lower() not in self.allowed_tables:

                return SQLValidationResult(
                    valid=False,
                    reason=f"Unknown table: {table}",
                )

        return None


# =============================================================
# Singleton
# =============================================================

sql_validator = SQLValidator()