"""
SQL Result Interpreter

Converts structured SQL execution results into natural-language
business answers.

Responsibilities:
- Deterministic formatting for simple single-row aggregate results
- LLM-based synthesis for complex multi-row results
- Fallback handling for empty or malformed results
"""

from __future__ import annotations

import json
from typing import Any

from app.core.prompts import prompts
from app.models.sql import SQLExecutionResult
from app.utils.llm import llm
from app.utils.parser import parser, ParserError


class SQLInterpretationError(RuntimeError):
    """Raised when SQL result interpretation fails."""


class SQLInterpreter:
    """
    Interprets SQL execution results into business-friendly answers.
    """

    def __init__(self) -> None:
        self.prompt_template = prompts.sql_interpreter()

    # ---------------------------------------------------------

    def interpret(
        self,
        question: str,
        sql: str,
        result: SQLExecutionResult,
    ) -> str:
        """
        Convert a SQL execution result into a natural-language answer.

        Parameters
        ----------
        question:
            Original business question.
        sql:
            Generated SQL query.
        result:
            SQL execution result.

        Returns
        -------
        str
            Natural-language answer.
        """

        if result.row_count == 0:
            return "The query returned no results."

        if result.row_count == 1 and len(result.columns) == 1:
            return self._interpret_single_value(
                question=question,
                sql=sql,
                result=result,
            )

        try:
            return self._interpret_with_llm(
                question=question,
                sql=sql,
                result=result,
            )
        except SQLInterpretationError:
            return (
                f"Query returned {result.row_count} rows."
                if result.row_count > 0
                else "Query executed successfully but returned no rows."
            )

    # ---------------------------------------------------------

    def _interpret_single_value(
        self,
        question: str,
        sql: str,
        result: SQLExecutionResult,
    ) -> str:
        """
        Deterministic formatting for single-row, single-column results.
        """

        column = result.columns[0]
        value = result.rows[0][column]

        if value is None:
            return "The query returned no results."

        label = self._column_to_label(column)
        formatted_value = self._format_value(value)
        metric_type = self._column_to_metric_type(column)

        if formatted_value == "0":
            return f"No {label} found."

        templates = {
            "count": f"{formatted_value} {label}.",
            "sum": f"Total {label} is {formatted_value}.",
            "avg": f"Average {label} is {formatted_value}.",
            "min": f"Lowest {label} is {formatted_value}.",
            "max": f"Highest {label} is {formatted_value}.",
        }

        template = templates.get(metric_type, f"{formatted_value} {label}.")
        return template

    # ---------------------------------------------------------

    def _column_to_metric_type(self, column: str) -> str:
        """
        Determine the metric type from the column name.
        """

        column_lower = column.lower()

        if any(key in column_lower for key in ["_count", "count", "_cnt", "cnt"]):
            return "count"

        if any(key in column_lower for key in ["total_", "_sum", "sum", "total"]):
            return "sum"

        if any(key in column_lower for key in ["avg_", "average_", "_avg", "average", "avg"]):
            return "avg"

        if any(key in column_lower for key in ["min_", "lowest_", "_min", "lowest", "min"]):
            return "min"

        if any(key in column_lower for key in ["max_", "highest_", "_max", "highest", "max"]):
            return "max"

        return "generic"

    # ---------------------------------------------------------

    def _column_to_label(self, column: str) -> str:
        """
        Map a SQL column name to a human-readable label.
        """

        column_lower = column.lower()

        mappings = {
            "order_count": "orders",
            "refund_count": "refunds",
            "customer_count": "customers",
            "product_count": "products",
            "seller_count": "sellers",
            "payment_count": "payments",
            "review_count": "reviews",
            "cnt": "records",
            "count": "records",
            "total_revenue": "revenue",
            "revenue": "revenue",
            "sum": "total",
            "total": "total",
            "average_order_value": "order value",
            "average_score": "score",
            "avg_score": "score",
            "average": "average",
            "avg": "average",
            "highest_payment": "payment",
            "max_value": "maximum value",
            "max": "maximum",
            "lowest_price": "price",
            "min_value": "minimum value",
            "min": "minimum",
        }

        for key, label in mappings.items():
            if key in column_lower:
                return label

        return column.replace("_", " ")

    # ---------------------------------------------------------

    def _format_value(self, value: Any) -> str:
        """
        Format a SQL result value for display.
        """

        if isinstance(value, float):
            if value == int(value):
                return f"{int(value):,}"
            return f"{value:,.2f}"

        if isinstance(value, int):
            return f"{value:,}"

        return str(value)

    # ---------------------------------------------------------

    def _interpret_with_llm(
        self,
        question: str,
        sql: str,
        result: SQLExecutionResult,
    ) -> str:
        """
        Use the LLM to synthesize a natural-language answer for
        complex multi-row results.
        """

        sql_results = {
            "columns": result.columns,
            "rows": result.rows,
            "row_count": result.row_count,
        }

        prompt = (
            f"{self.prompt_template}\n\n"
            f"User Question:\n{question}\n\n"
            f"Generated SQL:\n{sql}\n\n"
            f"SQL Results:\n{json.dumps(sql_results, indent=2, ensure_ascii=False)}\n\n"
            "Return ONLY the plain text answer."
        )

        try:
            response = llm.generate(prompt)

        except Exception as exc:
            raise SQLInterpretationError(
                f"Failed to interpret SQL result: {exc}"
            ) from exc

        if not response or not response.strip():
            return "The query returned results, but the answer could not be generated."

        return response.strip()


# ==========================================================
# Singleton
# ==========================================================

sql_interpreter = SQLInterpreter()
