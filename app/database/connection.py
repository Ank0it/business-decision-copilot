"""
Database Connection Manager

Provides a centralized, thread-safe SQLite connection for the
Business Decision Copilot.

Responsibilities
----------------
- Create SQLite connections
- Enable foreign key enforcement
- Configure row factory for dictionary-like access
- Provide context-managed database sessions
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from app.core.config import settings


class DatabaseConnection:
    """
    Centralized SQLite connection manager.

    All database interactions should go through this class.
    """

    def __init__(self) -> None:
        self.database_path = Path(settings.DATABASE_PATH)

    # ---------------------------------------------------------
    # Internal Connection
    # ---------------------------------------------------------

    def connect(self) -> sqlite3.Connection:
        """
        Create and configure a SQLite connection.
        """

        connection = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
        )

        # Enable FK constraints
        connection.execute("PRAGMA foreign_keys = ON;")

        # Return rows like dictionaries
        connection.row_factory = sqlite3.Row

        return connection

    # ---------------------------------------------------------
    # Context Manager
    # ---------------------------------------------------------

    @contextmanager
    def session(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context-managed database session.

        Automatically commits on success and rolls back on error.
        """

        connection = self.connect()

        try:
            yield connection
            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    # ---------------------------------------------------------
    # Health Check
    # ---------------------------------------------------------

    def ping(self) -> bool:
        """
        Verify that the database is reachable.
        """

        try:
            with self.session() as connection:
                connection.execute("SELECT 1;")
            return True

        except Exception:
            return False


# ==========================================================
# Singleton
# ==========================================================

database = DatabaseConnection()