"""
Hybrid Business Reasoning Service

Combines:

1. RAG (business policies)
2. Text2SQL (business analytics)

to generate grounded business recommendations.

Responsibilities:
- Retrieve relevant policy documents
- Generate and execute SQL
- Combine both sources
- Produce a business recommendation
"""

from __future__ import annotations

import json
from typing import Any

from app.core.prompts import prompts
from app.services.rag import rag_service
from app.services.sql_executor import sql_executor
from app.services.sql_generator import sql_generator
from app.services.sql_validator import sql_validator
from app.utils.llm import llm
from app.utils.parser import ParserError, parser


class HybridServiceError(RuntimeError):
    """Raised when the hybrid pipeline fails."""


class HybridService:
    """
    Orchestrates RAG + Text2SQL.
    """

    def __init__(self) -> None:
        self.prompt_template = prompts.hybrid()

    # ---------------------------------------------------------

    def answer(
        self,
        question: str,
    ) -> dict[str, Any]:
        """
        Generate a hybrid business recommendation.

        Parameters
        ----------
        question:
            Natural language business question.

        Returns
        -------
        dict
            Structured hybrid response.
        """

        # -----------------------------------------------------
        # Step 1: Retrieve policy evidence
        # -----------------------------------------------------

        retrieval = rag_service.debug_retrieval(question)

        if not retrieval:
            return {
                "refuse": True,
                "reason": (
                    "No relevant business documents were retrieved."
                ),
            }

        # -----------------------------------------------------
        # Step 2: Generate SQL
        # -----------------------------------------------------

        sql_result = sql_generator.generate(question)

        if hasattr(sql_result, "refuse") and sql_result.refuse:
            return {
                "refuse": True,
                "reason": sql_result.reason,
            }

        # -----------------------------------------------------
        # Step 3: Validate SQL
        # -----------------------------------------------------

        validation = sql_validator.validate(sql_result.sql)

        if not validation.valid:
            return {
                "refuse": True,
                "reason": validation.reason,
            }

        # -----------------------------------------------------
        # Step 4: Execute SQL
        # -----------------------------------------------------

        execution = sql_executor.execute(sql_result.sql)

        # -----------------------------------------------------
        # Step 5: Build Prompt
        # -----------------------------------------------------

        prompt = self._build_prompt(
            question=question,
            retrieval=retrieval,
            sql=sql_result.sql,
            execution=execution.model_dump(),
        )

        # -----------------------------------------------------
        # Step 6: LLM
        # -----------------------------------------------------

        response = llm.generate(prompt)

        try:
            return parser.parse_and_validate(
                response=response,
                required_fields=[
                    "policy_summary",
                    "data_summary",
                    "recommendation",
                    "confidence_notes",
                ],
            )

        except ParserError as exc:
            raise HybridServiceError(
                "Failed to parse hybrid response."
            ) from exc

    # ---------------------------------------------------------

    def _build_prompt(
        self,
        *,
        question: str,
        retrieval: list[dict[str, Any]],
        sql: str,
        execution: dict[str, Any],
    ) -> str:
        """
        Construct the hybrid prompt.
        """

        context = []

        for chunk in retrieval:

            context.append(
                f"""
Source:
{chunk["source"]}

Chunk ID:
{chunk["chunk_id"]}

Content:
{chunk["content"]}
"""
            )

        policy_context = "\n".join(context)

        sql_results = json.dumps(
            execution,
            indent=2,
            ensure_ascii=False,
        )

        return (
            f"{self.prompt_template}\n\n"
            f"Business Question:\n{question}\n\n"
            f"Policy Context:\n{policy_context}\n\n"
            f"Generated SQL:\n{sql}\n\n"
            f"SQL Results:\n{sql_results}\n\n"
            "Return ONLY the required JSON object."
        )


# ==========================================================
# Singleton
# ==========================================================

hybrid_service = HybridService()