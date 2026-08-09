"""
Prompt Management

Loads and caches prompt templates from the prompts/ directory.

Keeping prompts outside Python code allows prompt engineering
without modifying application logic.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.core.config import settings


class PromptManager:
    """
    Loads prompt templates from disk.

    Prompt files are cached after the first read to avoid
    unnecessary disk I/O.
    """

    @staticmethod
    @lru_cache(maxsize=None)
    def load(filename: str) -> str:
        """
        Load a prompt template.

        Args:
            filename:
                Prompt filename (e.g. "router.txt").

        Returns:
            Prompt text.

        Raises:
            FileNotFoundError:
                If the prompt file does not exist.
        """

        path: Path = settings.PROMPT_DIR / filename

        if not path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {path}"
            )

        return path.read_text(
            encoding="utf-8"
        ).strip()

    @classmethod
    def router(cls) -> str:
        return cls.load("router.txt")

    @classmethod
    def rag(cls) -> str:
        return cls.load("rag.txt")

    @classmethod
    def sql(cls) -> str:
        return cls.load("sql.txt")

    @classmethod
    def hybrid(cls) -> str:
        return cls.load("hybrid.txt")

    @classmethod
    def sql_interpreter(cls) -> str:
        return cls.load("sql_interpreter.txt")


prompts = PromptManager()