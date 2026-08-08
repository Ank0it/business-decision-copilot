"""
SQL Generator Service

Converts natural language business questions into safe,
read-only SQLite queries using the configured LLM.

Responsibilities:
- Load the SQL prompt template
- Invoke the LLM
- Parse structured JSON responses
- Return strongly typed SQL models
"""

from __future__ import annotations

from app.core.prompts import prompts
from app.models.sql import SQLGeneration, SQLRefusal
from app.utils.llm import llm
from app.utils.parser import parser, ParserError


class SQLGenerationError(RuntimeError):
    """Raised when SQL generation fails."""


class SQLGenerator:
    """
    Generates SQL from natural language business questions.
    """

    def __init__(self) -> None:
        self.prompt_template = prompts.sql()

    def generate(
        self,
        question: str,
    ) -> SQLGeneration | SQLRefusal:
        """
        Generate SQL for a business question.

        Parameters
        ----------
        question:
            Natural language business question.

        Returns
        -------
        SQLGeneration | SQLRefusal
        """

        final_prompt = (
            f"{self.prompt_template}\n\n"
            "Business Question:\n"
            f"{question}\n\n"
            "Return ONLY the required JSON object."
        )

        response = llm.generate(final_prompt)

        try:
            data = parser.parse_json(response)

        except ParserError as exc:
            raise SQLGenerationError(
                "Failed to parse SQL generation response."
            ) from exc

        # --------------------------------------------------
        # Refusal
        # --------------------------------------------------

        if data.get("refuse") is True:
            reason = data.get(
                "reason",
                "SQL generation refused.",
            )

            return SQLRefusal(reason=reason)

        # --------------------------------------------------
        # SQL Generation
        # --------------------------------------------------

        parser.require_fields(
            data,
            ["sql"],
        )

        sql = data["sql"].strip()

        if not sql:
            raise SQLGenerationError(
                "Generated SQL is empty."
            )

        return SQLGeneration(sql=sql)


# ==========================================================
# Singleton
# ==========================================================

sql_generator = SQLGenerator()
