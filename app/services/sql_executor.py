"""
SQL Executor Service

Executes validated read-only SQL queries against the business
database and returns structured results.

Responsibilities:
- Execute validated SELECT queries
- Return rows and column names
- Convert SQLite results into JSON-serializable objects
- Never execute unsafe SQL
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.config import settings
from app.database.connection import DatabaseConnection
from app.models.sql import (
    SQLExecutionResult,
    SQLValidationResult,
)
from app.services.sql_validator import sql_validator


class SQLExecutionError(RuntimeError):
    """
    Raised when SQL execution fails.
    """


class SQLExecutor:
    """
    Executes validated SQL queries.
    """

    def __init__(self) -> None:
        self.database_path = Path(settings.DATABASE_PATH)
        self.db_connection = DatabaseConnection()

    # ---------------------------------------------------------

    def execute(
        self,
        sql: str,
    ) -> SQLExecutionResult:
        """
        Execute a validated SQL query.

        Parameters
        ----------
        sql:
            SQL SELECT statement.

        Returns
        -------
        SQLExecutionResult
        """

        validation: SQLValidationResult = sql_validator.validate(sql)

        if not validation.valid:
            raise SQLExecutionError(validation.reason or "SQL validation failed.")

        if not self.database_path.exists():
            raise SQLExecutionError(
                f"Database not found: {self.database_path}"
            )

        try:
            with self.db_connection.session() as connection:
                connection.execute(
                    f"PRAGMA busy_timeout = {settings.SQL_QUERY_TIMEOUT * 1000};"
                )
                cursor = connection.cursor()
                cursor.execute(sql)

                rows = cursor.fetchall()

                columns = [
                    description[0]
                    for description in cursor.description
                ] if cursor.description else []

                result_rows = [
                    dict(row)
                    for row in rows
                ]

                return SQLExecutionResult(
                    columns=columns,
                    rows=result_rows,
                    row_count=len(result_rows),
                )

        except sqlite3.Error as exc:
            raise SQLExecutionError(
                f"Database execution failed: {exc}"
            ) from exc


# ==========================================================
# Singleton
# ==========================================================

sql_executor = SQLExecutor()